import shutil

from pathlib import Path

from .download import (
    download_ifs_hour,
)

from shared.map_completeness import (
    hour_complete as map_hour_complete,
    region_report as map_region_report,
    work_plan_for_hour as map_work_plan_for_hour,
)

from shared.inventory_seed import (
    build_work_plan,
    mark_complete,
)

from shared.operational_lifecycle import (
    FrontierSweep,
    OperationalCycleState,
    OperationalLifecycle,
)

from shared.execution import (
    ModelExecutionResources,
)

from shared.models import (
    get_forecast_hours,
)

from shared.runner import (
    run_forecast_hour,
    OPERATIONAL_REGIONS,
    get_default_products_for_model,
    get_sequence_products_for_model,
    get_download_products_for_model,
)

from shared.product_cadence import (
    products_for_forecast_hour,
)

from shared.prefetch import (
    ForecastHourPrefetcher,
)

from shared.sequence import (
    SequenceStreamProcessor,
)

from shared.resume import (
    get_remaining_forecast_hours,
)

from shared.storage import (
    get_local_root,
    delete_local,
    upload_forecast_hour_outputs,
)



# ============================================================
# AUTHORITATIVE MAP COMPLETENESS / SELECTIVE REPAIR
# ============================================================

import time

def _ifs_authoritative_map_plan(*, completed_inventory, expected_products, execution_regions, forecast_hour):
    plan = map_work_plan_for_hour(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)
    report = map_region_report(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)
    missing_maps = sum(len(item["missing"]) for item in report.values())
    print("IFS " + f"f{int(forecast_hour):03d}: {missing_maps} missing region/product maps")
    return plan, report

def _ifs_map_hour_complete(*, completed_inventory, expected_products, execution_regions, forecast_hour):
    return map_hour_complete(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)


def _ifs_operational_forecast_hours(cycle_hour=None):
    return sorted(set(int(hour) for hour in get_forecast_hours(
        "ifs", cycle_hour=cycle_hour,
    )))

# ============================================================
# SETTINGS
# ============================================================

OVERWRITE_EXISTING = False

MIN_FREE_DISK_GB = 3.0


# ============================================================
# TEMPORARY OUTPUT
# ============================================================

def get_ifs_output_root():
    """
    Rendered IFS images are temporary local files.

    Permanent products live in Google Cloud Storage.
    """

    return (
        get_local_root()
        / "output"
        / "ifs"
    )


# ============================================================
# DISK SAFETY
# ============================================================

def check_working_disk_space():
    """
    Refuse to continue if the VM filesystem becomes dangerously full.
    """

    usage = shutil.disk_usage(
        "/"
    )

    free_gb = (
        usage.free
        /
        1024
        /
        1024
        /
        1024
    )

    print(
        f"Working disk free: "
        f"{free_gb:.2f} GB"
    )

    if (
        free_gb
        <
        MIN_FREE_DISK_GB
    ):

        raise RuntimeError(
            f"IFS pipeline stopped: "
            f"only {free_gb:.2f} GB "
            f"of working disk remains."
        )


# ============================================================
# REMOVE EMPTY OUTPUT DIRECTORIES
# ============================================================

def remove_empty_directories(
    root,
):
    root = Path(
        root
    )

    if not root.exists():

        return

    directories = sorted(
        [
            path
            for path
            in root.rglob(
                "*"
            )
            if path.is_dir()
        ],
        key=lambda path: len(
            path.parts
        ),
        reverse=True,
    )

    for directory in directories:

        try:

            directory.rmdir()

        except OSError:

            pass

    try:

        root.rmdir()

    except OSError:

        pass


# ============================================================
# IFS STREAMING PIPELINE
# ============================================================

# ============================================================
# CYCLE IDENTITY
# ============================================================

def get_cycle_identity(
    cycle,
):

    if cycle is None:

        return {
            "name": "latest",
            "date": "latest",
            "hour": 0,
        }

    return {
        "name": cycle.get(
            "id",
            (
                f"{cycle.get('date', 'latest')}_"
                f"{int(cycle.get('hour', 0)):02d}z"
            ),
        ),

        "date": str(
            cycle.get(
                "date",
                "latest",
            )
        ),

        "hour": int(
            cycle.get(
                "hour",
                0,
            )
        ),
    }


def run_ifs(
    cycle=None,
):

    print()
    print("=" * 70)
    print(
        "MASSACHUSETTSWX "
        "ECMWF IFS "
        "STREAMING PIPELINE"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # CYCLE INFORMATION
    # --------------------------------------------------------

    cycle_hour = (
        int(
            cycle[
                "hour"
            ]
        )
        if cycle is not None
        else None
    )

    if cycle is not None:

        cycle_name = (
            cycle[
                "id"
            ]
        )

    else:

        cycle_name = (
            "latest"
        )

    # --------------------------------------------------------
    # FORECAST HOURS
    # --------------------------------------------------------

    identity = (
        get_cycle_identity(
            cycle
        )
    )

    all_forecast_hours = (
        get_forecast_hours(
            "ifs",
            cycle_hour=cycle_hour,
        )
    )

    if identity["date"] != "latest":

        forecast_hours = (
            get_remaining_forecast_hours(
                model="ifs",
                cycle_date=(
                    identity["date"]
                ),
                cycle_hour=(
                    identity["hour"]
                ),
                forecast_hours=(
                    all_forecast_hours
                ),
            )
        )

    else:

        forecast_hours = (
            all_forecast_hours
        )

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    instantaneous_products = (
        get_default_products_for_model(
            "ifs"
        )
    )

    sequence_products = (
        get_sequence_products_for_model(
            "ifs"
        )
    )

    download_products = (
        get_download_products_for_model(
            "ifs"
        )
    )

    # --------------------------------------------------------
    # TEMPORARY OUTPUT
    # --------------------------------------------------------

    cycle_output_dir = (
        get_ifs_output_root()
        / cycle_name
    )

    cycle_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Cycle: "
        f"{cycle_name}"
    )

    print(
        f"Forecast hours: "
        f"{len(forecast_hours)}"
    )

    print(
        f"Instantaneous products: "
        f"{len(instantaneous_products)}"
    )

    print(
        f"Sequence products: "
        f"{len(sequence_products)}"
    )

    print(
        f"Download products: "
        f"{len(download_products)}"
    )

    print(
        f"Regions: "
        f"{len(OPERATIONAL_REGIONS)}"
    )

    print(
        f"Temporary output: "
        f"{cycle_output_dir}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # STREAMING SEQUENCE STATE
    # --------------------------------------------------------

    sequence_processor = (
        SequenceStreamProcessor(
            model="ifs",
            output_dir=(
                cycle_output_dir
            ),
            regions=(
                OPERATIONAL_REGIONS
            ),
            overwrite=(
                OVERWRITE_EXISTING
            ),
        )
    )

    # --------------------------------------------------------
    # PIPELINE COUNTERS
    # --------------------------------------------------------

    result = {
        "created": 0,
        "skipped": 0,
        "failed": 0,
        "forecast_hours_expected": (
            len(
                forecast_hours
            )
        ),
        "forecast_hours_downloaded": 0,
        "forecast_hours_processed": 0,
        "cloud_uploaded": 0,
        "cloud_upload_failed": 0,
        "local_png_removed": 0,
    }

    # ========================================================
    # PROCESS ONE FORECAST HOUR AT A TIME
    # ========================================================

    stopped_at_upstream_frontier = False

    # ========================================================
    # ONE-HOUR-AHEAD ECMWF DOWNLOAD PREFETCH
    # ========================================================

    def download_one_hour(
        forecast_hour,
    ):

        return (
            download_ifs_hour(
                forecast_hour,
                products=(
                    download_products
                ),
                cycle=cycle,
            )
        )

    prefetcher = (
        ForecastHourPrefetcher(
            download_one_hour
        )
    )

    resources = (
        ModelExecutionResources(
            model="ifs",
        )
    )

    render_executor = (
        resources.process_pool()
    )


    if forecast_hours:

        prefetcher.start(
            forecast_hours[
                0
            ]
        )

        print(
            "IFS PREFETCH: "
            f"started f{forecast_hours[0]:03d}"
        )

    try:

        for (
            index,
            forecast_hour,
        ) in enumerate(
            forecast_hours,
            start=1,
        ):

            print()
            print("=" * 70)

            print(
                f"IFS FORECAST HOUR "
                f"{index}/"
                f"{len(forecast_hours)}: "
                f"f{forecast_hour:03d}"
            )

            print("=" * 70)

            check_working_disk_space()

            hour_started_at = time.monotonic()
            grib_path = None

            try:

                # ====================================================
                # DOWNLOAD ONE HOUR
                # ====================================================

                print(
                    f"IFS PREFETCH: "
                    f"waiting for "
                    f"f{forecast_hour:03d}"
                )

                grib_path = (
                    prefetcher.get(
                        forecast_hour
                    )
                )

                if grib_path is None:

                    print(
                        f"IFS "
                        f"f{forecast_hour:03d}: "
                        f"not available upstream yet; "
                        f"stopping cleanly at upstream frontier"
                    )

                    stopped_at_upstream_frontier = True

                    break

                if (
                    not grib_path.exists()
                    or
                    grib_path.stat().st_size
                    <= 0
                ):

                    raise RuntimeError(
                        f"IFS "
                        f"f{forecast_hour:03d}: "
                        f"download produced "
                        f"no usable GRIB"
                    )

                result[
                    "forecast_hours_downloaded"
                ] += 1

                if (
                    index
                    <
                    len(
                        forecast_hours
                    )
                ):

                    next_forecast_hour = (
                        forecast_hours[
                            index
                        ]
                    )

                    prefetcher.start(
                        next_forecast_hour
                    )

                    print(
                        f"IFS PREFETCH: "
                        f"downloading "
                        f"f{next_forecast_hour:03d} "
                        f"while "
                        f"f{forecast_hour:03d} "
                        f"is processed"
                    )

                # ====================================================
                # INSTANTANEOUS PRODUCTS
                # ====================================================

                instant_result = (
                    run_forecast_hour(
                        grib_path=(
                            grib_path
                        ),
                        model="ifs",
                        step=(
                            forecast_hour
                        ),
                        output_dir=(
                            cycle_output_dir
                        ),
                        products=(
                            instantaneous_products
                        ),
                        regions=(
                            OPERATIONAL_REGIONS
                        ),
                        overwrite=(
                            OVERWRITE_EXISTING
                        ),
                        executor=(
                            render_executor
                        ),
                    )
                )

                result[
                    "created"
                ] += instant_result[
                    "created"
                ]

                result[
                    "skipped"
                ] += instant_result[
                    "skipped"
                ]

                result[
                    "failed"
                ] += instant_result[
                    "failed"
                ]

                instantaneous_failed = int(
                    instant_result.get(
                        "failed",
                        0,
                    )
                )

                if instantaneous_failed > 0:

                    raise RuntimeError(
                        f"IFS "
                        f"f{forecast_hour:03d}: "
                        f"{instantaneous_failed} "
                        f"instantaneous plots failed; "
                        f"forecast hour will NOT "
                        f"be published."
                    )

                # ====================================================
                # SEQUENCE PRODUCTS FOR THIS SAME HOUR
                # ====================================================

                sequence_result = (
                    sequence_processor.process_hour(
                        step=(
                            forecast_hour
                        ),
                        grib_path=(
                            grib_path
                        ),
                    )
                )

                result[
                    "created"
                ] += sequence_result[
                    "created"
                ]

                result[
                    "skipped"
                ] += sequence_result[
                    "skipped"
                ]

                result[
                    "failed"
                ] += sequence_result[
                    "failed"
                ]

                sequence_failed = int(
                    sequence_result.get(
                        "failed",
                        0,
                    )
                )

                if sequence_failed > 0:

                    raise RuntimeError(
                        f"IFS "
                        f"f{forecast_hour:03d}: "
                        f"{sequence_failed} "
                        f"sequence plots failed; "
                        f"forecast hour will NOT "
                        f"be published."
                    )

                # ====================================================
                # UPLOAD THIS HOUR'S PNGs AND IMMEDIATELY REMOVE THEM
                # ====================================================

                expected_hour_products = (
                    products_for_forecast_hour(
                        model="ifs",
                        products=(
                            get_default_products_for_model(
                                "ifs"
                            )
                        ),
                        forecast_hour=(
                            forecast_hour
                        ),
                    )
                )

                # Sequence products use their own cadence and
                # processing rules. Add them only when this hour's
                # sequence processor actually produced or reused
                # sequence frames.
                if (
                    int(
                        sequence_result.get(
                            "created",
                            0,
                        )
                    )
                    +
                    int(
                        sequence_result.get(
                            "skipped",
                            0,
                        )
                    )
                    > 0
                ):

                    expected_hour_products = (
                        list(
                            expected_hour_products
                        )
                        +
                        list(
                            get_sequence_products_for_model(
                                "ifs"
                            )
                        )
                    )

                expected_hour_products = list(
                    dict.fromkeys(
                        expected_hour_products
                    )
                )

                upload_result = (
                    upload_forecast_hour_outputs(
                        model="ifs",
                        cycle_date=(
                            identity[
                                "date"
                            ]
                        ),
                        cycle_hour=(
                            identity[
                                "hour"
                            ]
                        ),
                        forecast_hour=(
                            forecast_hour
                        ),
                        cycle_output_dir=(
                            cycle_output_dir
                        ),
                        delete_after_upload=True,
                        expected_products=(
                            expected_hour_products
                        ),
                        expected_regions=(
                            OPERATIONAL_REGIONS
                        ),
                    )
                )

                result[
                    "cloud_uploaded"
                ] += upload_result[
                    "uploaded"
                ]

                result[
                    "cloud_upload_failed"
                ] += upload_result[
                    "failed"
                ]

                result[
                    "local_png_removed"
                ] += upload_result[
                    "removed"
                ]

                result[
                    "forecast_hours_processed"
                ] += 1

            except Exception as error:

                print(
                    f"IFS "
                    f"f{forecast_hour:03d}: "
                    f"PIPELINE FAILED: "
                    f"{error}"
                )

                result[
                    "failed"
                ] += 1

            finally:

                elapsed_seconds = (
                    time.monotonic()
                    - hour_started_at
                )

                print(
                    "IFS "
                    f"f{forecast_hour:03d} "
                    f"elapsed={elapsed_seconds:.1f}s"
                )

                # ====================================================
                # RAW GRIB NO LONGER NEEDED
                # ====================================================

                if (
                    grib_path
                    is not None
                ):

                    try:

                        if grib_path.exists():

                            size_mb = (
                                grib_path.stat().st_size
                                /
                                1024
                                /
                                1024
                            )

                            delete_local(
                                grib_path
                            )

                            print(
                                f"Deleted raw "
                                f"f{forecast_hour:03d} "
                                f"GRIB "
                                f"({size_mb:.2f} MB)"
                            )

                    except Exception as error:

                        print(
                            f"GRIB CLEANUP FAILED "
                            f"f{forecast_hour:03d}: "
                            f"{error}"
                        )

                # ----------------------------------------------------
                # REMOVE EMPTY LOCAL DIRECTORIES
                # ----------------------------------------------------

                remove_empty_directories(
                    cycle_output_dir
                )

                check_working_disk_space()

    finally:

        resources.close()
        prefetcher.close()

        sequence_processor.finish()

        remove_empty_directories(
            cycle_output_dir
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result[
        "first_forecast_hour"
    ] = forecast_hours[
        0
    ]

    result[
        "last_forecast_hour"
    ] = forecast_hours[
        -1
    ]

    remaining_this_invocation = max(
        0,
        (
            len(
                forecast_hours
            )
            -
            result[
                "forecast_hours_processed"
            ]
        ),
    )

    if (
        result[
            "failed"
        ]
        > 0
        or
        result[
            "cloud_upload_failed"
        ]
        > 0
    ):

        pipeline_status = "failed"

    elif (
        stopped_at_upstream_frontier
        or
        remaining_this_invocation
        > 0
    ):

        pipeline_status = (
            "waiting_upstream"
        )

    else:

        pipeline_status = "complete"

    result[
        "status"
    ] = pipeline_status

    result[
        "remaining_this_invocation"
    ] = remaining_this_invocation

    result[
        "stopped_at_upstream_frontier"
    ] = stopped_at_upstream_frontier

    print()
    print("=" * 70)
    print(
        f"IFS STREAMING PIPELINE "
        f"{pipeline_status.upper()}"
    )
    print("=" * 70)

    print(
        f"Forecast hours downloaded: "
        f"{result['forecast_hours_downloaded']}/"
        f"{result['forecast_hours_expected']}"
    )

    print(
        f"Forecast hours processed: "
        f"{result['forecast_hours_processed']}/"
        f"{result['forecast_hours_expected']}"
    )

    print(
        f"Maps created: "
        f"{result['created']}"
    )

    print(
        f"Maps skipped: "
        f"{result['skipped']}"
    )

    print(
        f"Maps failed: "
        f"{result['failed']}"
    )

    print(
        f"Cloud uploads: "
        f"{result['cloud_uploaded']}"
    )

    print(
        f"Cloud upload failures: "
        f"{result['cloud_upload_failed']}"
    )

    print(
        f"Local PNGs removed: "
        f"{result['local_png_removed']}"
    )

    print(
        f"Status: "
        f"{result['status']}"
    )

    print(
        f"Remaining this invocation: "
        f"{result['remaining_this_invocation']}"
    )

    print(
        f"Stopped at upstream frontier: "
        f"{result['stopped_at_upstream_frontier']}"
    )

    print("=" * 70)

    return result


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_ifs()
