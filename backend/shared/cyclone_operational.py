from __future__ import annotations

from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from shared.cyclone_manifest import (
    build_cyclone_manifest,
)

from shared.cyclone_metadata import (
    publish_current,
    publish_manifest,
    publish_progress,
)

from shared.cyclone_pipeline import (
    build_cyclone_frame_plan,
    get_frame_output_path,
)

from shared.cyclone_publish import (
    frame_already_published,
    publish_cyclone_frame,
)

from shared.models import get_model_workers

from shared.cyclone_status import (
    finish_cycle,
    mark_frame_complete,
    mark_frame_failed,
    new_cycle_status,
    save_status,
    update_completed_hours,
)



# ============================================================
# MASSWX_BOUNDED_CYCLONE_FRAME_EXECUTOR
# ============================================================

def _execute_cyclone_frame(
    *,
    request,
    renderer,
    local_root,
    resume,
):
    """
    Render and upload one independent cyclone frame.

    Status/manifest mutation intentionally stays in the parent
    process. Worker processes only perform:

        existing-frame check
        render
        frame upload

    This prevents concurrent progress.json / manifest writes.
    """

    if (
        resume
        and
        frame_already_published(
            request
        )
    ):
        return {
            "state": "skipped",
            "request": request,
            "object_name": None,
        }


    output_path = (
        get_frame_output_path(
            request,
            root=local_root,
        )
    )


    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    renderer(
        request=request,
        output_path=output_path,
    )


    object_name = (
        publish_cyclone_frame(
            request=request,
            local_path=output_path,
            delete_after_upload=True,
        )
    )


    return {
        "state": "complete",
        "request": request,
        "object_name": object_name,
    }


def run_operational_cyclone_cycle(
    *,
    model,
    date,
    hour,
    forecast_hours,
    renderer,
    products,
    regions,
    member_count=None,
    local_root=(
        "/tmp/massachusettswx"
    ),
    resume=True,
):
    plan = build_cyclone_frame_plan(
        model=model,
        date=date,
        hour=hour,
        forecast_hours=forecast_hours,
        products=products,
        regions=regions,
    )

    # Operational priority:
    # publish Tropical Atlantic frames first.
    region_priority = {
        "tropical_atlantic": 0,
        "western_atlantic": 1,
        "caribbean": 2,
        "gulf_of_mexico": 3,
        "atlantic": 4,
        "central_atlantic": 5,
        "eastern_atlantic": 6,
    }

    plan = sorted(
        plan,
        key=lambda request: (
            region_priority.get(
                request.region,
                100,
            ),
            request.forecast_hour,
            request.product,
        ),
    )


    status = new_cycle_status(
        model=model,
        date=date,
        hour=hour,
        products=products,
        regions=regions,
        forecast_hours=(
            forecast_hours
        ),
        member_count=member_count,
    )

    status_path = (
        Path(local_root)
        /
        "metadata"
        /
        model
        /
        f"{date}_{int(hour):02d}z"
        /
        "progress.json"
    )

    # Publish running state immediately.
    save_status(
        status_path,
        status,
    )

    publish_progress(
        status
    )

    publish_current(
        model=model,
        date=date,
        hour=hour,
        status="running",
    )

    # ========================================================
    # BOUNDED PARALLEL FRAME EXECUTION
    # ========================================================

    workers = max(
        1,
        int(
            get_model_workers(
                model
            )
        ),
    )

    # Cyclone plotting is memory-heavy, especially FNV3-L.
    # Never allow config drift to create an unbounded pool.
    workers = min(
        workers,
        2,
        max(
            1,
            len(plan),
        ),
    )

    print()
    print(
        f"{str(model).upper()} "
        f"cyclone frame workers: "
        f"{workers}"
    )


    def record_complete(
        result,
    ):
        request = result[
            "request"
        ]

        if result[
            "state"
        ] == "skipped":
            return

        mark_frame_complete(
            status,
            product=request.product,
            region=request.region,
            forecast_hour=(
                request.forecast_hour
            ),
            object_name=(
                result[
                    "object_name"
                ]
            ),
        )

        update_completed_hours(
            status
        )

        save_status(
            status_path,
            status,
        )

        publish_progress(
            status
        )

        # Keep the website manifest synchronized with every
        # successfully uploaded cyclone PNG.
        live_manifest = build_cyclone_manifest(
            model=model,
            date=date,
            hour=hour,
            forecast_hours=forecast_hours,
            products=products,
            regions=regions,
            member_count=member_count,
        )

        publish_manifest(
            live_manifest
        )


    def record_failure(
        request,
        exc,
    ):
        mark_frame_failed(
            status,
            product=request.product,
            region=request.region,
            forecast_hour=(
                request.forecast_hour
            ),
            error=exc,
        )

        save_status(
            status_path,
            status,
        )

        publish_progress(
            status
        )


    if workers <= 1:

        for request in plan:

            try:
                result = (
                    _execute_cyclone_frame(
                        request=request,
                        renderer=renderer,
                        local_root=local_root,
                        resume=resume,
                    )
                )

                record_complete(
                    result
                )

            except Exception as exc:

                record_failure(
                    request,
                    exc,
                )


    else:

        with ProcessPoolExecutor(
            max_workers=workers
        ) as executor:

            future_map = {
                executor.submit(
                    _execute_cyclone_frame,
                    request=request,
                    renderer=renderer,
                    local_root=local_root,
                    resume=resume,
                ):
                request

                for request in plan
            }


            for future in as_completed(
                future_map
            ):

                request = future_map[
                    future
                ]

                try:

                    result = (
                        future.result()
                    )

                    record_complete(
                        result
                    )

                except Exception as exc:

                    record_failure(
                        request,
                        exc,
                    )


    finish_cycle(
        status
    )

    save_status(
        status_path,
        status,
    )

    manifest = (
        build_cyclone_manifest(
            model=model,
            date=date,
            hour=hour,
            forecast_hours=(
                forecast_hours
            ),
            products=products,
            regions=regions,
            member_count=(
                member_count
            ),
        )
    )

    publish_progress(
        status
    )

    publish_manifest(
        manifest
    )

    publish_current(
        model=model,
        date=date,
        hour=hour,
        status=status[
            "status"
        ],
    )

    # ========================================================
    # STANDARD MASSACHUSETTSWX PUBLICATION
    #
    # Cyclone-specific progress/manifest publication above is
    # retained for compatibility.
    #
    # A successfully completed cyclone cycle is also finalized
    # through shared.publish so FNV3/FNV3-L receive the same
    # READY/latest/current/archive lifecycle as the atmospheric
    # model pipelines.
    # ========================================================

    shared_publication = None

    if status.get(
        "status"
    ) == "complete":

        try:

            from shared.publish import (
                publish_cycle,
            )

            cycle = {
                "date": str(
                    date
                ),
                "hour": int(
                    hour
                ),
                "id": (
                    f"{date}_"
                    f"{int(hour):02d}z"
                ),
            }

            shared_result = {
                "status": status,
                "manifest": manifest,
                "forecast_hours": list(
                    forecast_hours
                ),
                "products": list(
                    products
                ),
                "regions": list(
                    regions
                ),
                "member_count": (
                    member_count
                ),
            }

            shared_publication = (
                publish_cycle(
                    model=model,
                    cycle=cycle,
                    result=shared_result,
                )
            )

            print(
                f"{str(model).upper()} "
                "STANDARD PUBLICATION: PASS"
            )

        except Exception as error:

            # Do not erase a successfully rendered cyclone
            # cycle merely because final metadata publication
            # encountered a problem.
            print(
                f"WARNING: "
                f"{str(model).upper()} "
                f"standard publication failed: "
                f"{type(error).__name__}: "
                f"{error}"
            )

    return {
        "status": status,
        "manifest": manifest,
        "shared_publication": (
            shared_publication
        ),
    }
