import os
import time

from datetime import (
    datetime,
    timezone,
)

from .download import (
    download_gfs_hour as _download_gfs_hour_once,
    resolve_gfs_cycle,
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

from shared.resume import (
    get_remaining_forecast_hours,
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

from shared.storage import (
    build_local_output_cycle_dir,
    check_working_disk_space,
    delete_local,
    remove_empty_directories,
    upload_forecast_hour_outputs,
)



# ============================================================
# AUTHORITATIVE MAP COMPLETENESS / SELECTIVE REPAIR
# ============================================================

def _gfs_authoritative_map_plan(*, completed_inventory, expected_products, execution_regions, forecast_hour):
    plan = map_work_plan_for_hour(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)
    report = map_region_report(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)
    missing_maps = sum(len(item["missing"]) for item in report.values())
    print("GFS " + f"f{int(forecast_hour):03d}: {missing_maps} missing region/product maps")
    return plan, report

def _gfs_map_hour_complete(*, completed_inventory, expected_products, execution_regions, forecast_hour):
    return map_hour_complete(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)

# ============================================================
# SETTINGS
# ============================================================

OVERWRITE_EXISTING = False


# ============================================================
# CONTINUOUS GFS DISSEMINATION WINDOW
#
# The priority/CONUS lane must not exit after one negative
# upstream probe. During active dissemination, keep the same
# warm Cloud Run execution alive and retry the next hour.
#
# Background/backfill remains single-probe so it never sits
# around waiting for future operational data.
# ============================================================

GFS_FRONTIER_POLL_SECONDS = max(
    5,
    int(
        os.environ.get(
            "GFS_FRONTIER_POLL_SECONDS",
            "10",
        )
    ),
)

GFS_FRONTIER_WAIT_SECONDS = max(
    0,
    int(
        os.environ.get(
            "GFS_FRONTIER_WAIT_SECONDS",
            "600",
        )
    ),
)


def download_gfs_hour(
    date,
    cycle,
    forecast_hour,
    products=None,
):
    """
    Download a GFS forecast hour.

    Priority lane:
        Keep probing the next forecast hour for up to the
        configured continuous dissemination window.

    Background/all lanes:
        Preserve the original single-probe behavior.

    Returning None after the wait window preserves the existing
    upstream-frontier shutdown behavior in run_gfs().
    """

    forecast_hour = int(
        forecast_hour
    )

    # Background work should never wait for future frames.
    if GFS_REGION_MODE != "priority":

        return _download_gfs_hour_once(
            date,
            cycle,
            forecast_hour,
            products,
        )


    started = time.monotonic()
    attempt = 0


    while True:

        attempt += 1

        result = _download_gfs_hour_once(
            date,
            cycle,
            forecast_hour,
            products,
        )


        if result is not None:

            if attempt > 1:

                elapsed = (
                    time.monotonic()
                    -
                    started
                )

                print(
                    f"GFS CONTINUOUS WINDOW: "
                    f"f{forecast_hour:03d} appeared "
                    f"after {elapsed:.1f}s "
                    f"({attempt} probes)"
                )

            return result


        elapsed = (
            time.monotonic()
            -
            started
        )


        if elapsed >= GFS_FRONTIER_WAIT_SECONDS:

            print(
                f"GFS CONTINUOUS WINDOW: "
                f"f{forecast_hour:03d} still unavailable "
                f"after {elapsed:.1f}s; "
                f"releasing execution"
            )

            return None


        remaining = max(
            0,
            GFS_FRONTIER_WAIT_SECONDS
            -
            elapsed,
        )

        print(
            f"GFS CONTINUOUS WINDOW: "
            f"waiting for f{forecast_hour:03d}; "
            f"retry in {GFS_FRONTIER_POLL_SECONDS}s "
            f"({remaining:.0f}s window remaining)"
        )

        time.sleep(
            min(
                GFS_FRONTIER_POLL_SECONDS,
                remaining,
            )
        )


# ============================================================
# GFS REGION MODE
#
# priority:
#     CONUS only. This is the live dissemination lane.
#
# background:
#     Every operational region except CONUS.
#
# all:
#     Legacy behavior; every operational region.
# ============================================================

GFS_REGION_MODE = (
    os.environ.get(
        "GFS_REGION_MODE",
        "all",
    )
    .strip()
    .lower()
)


def get_gfs_regions():
    """
    Return the region set for this Cloud Run execution.
    """

    if GFS_REGION_MODE == "priority":

        return [
            "conus",
        ]

    if GFS_REGION_MODE == "background":

        return [
            region
            for region in OPERATIONAL_REGIONS
            if region != "conus"
        ]

    if GFS_REGION_MODE == "all":

        return list(
            OPERATIONAL_REGIONS
        )

    raise ValueError(
        "Unknown GFS_REGION_MODE: "
        f"{GFS_REGION_MODE}"
    )



MIN_FREE_DISK_GB = 3.0


# ============================================================
# GFS REAL-TIME FORWARD SCAN
#
# NOAA real-time dissemination can temporarily contain holes.
# One missing scheduled hour must not block later hours that
# are already available.
#
# Stop only after this many CONSECUTIVE unavailable scheduled
# forecast hours.
# ============================================================

GFS_FORWARD_SCAN_MISSES = max(
    2,
    int(
        os.environ.get(
            "GFS_FORWARD_SCAN_MISSES",
            "8",
        )
    ),
)


# ============================================================
# WARM OPERATIONAL FRONTIER
#
# Keep the CURRENT Cloud Run execution alive briefly while
# upstream dissemination is active.
#
# Sleeping is bounded by OperationalLifecycle. We never leave
# a model job alive indefinitely.
# ============================================================

def wait_at_operational_frontier(
    lifecycle,
):
    lifecycle.mark_idle_poll()

    if lifecycle.should_exit():

        print(
            "GFS operational window idle/expired; "
            "execution may exit."
        )

        return False

    print(
        "GFS upstream frontier reached; "
        f"waiting {lifecycle.policy.poll_seconds}s "
        "inside current execution."
    )

    lifecycle.wait()

    return True



# ============================================================
# CYCLE DATETIME
# ============================================================

def cycle_to_datetime(
    cycle,
):

    if cycle is None:

        return None

    cycle_time = (
        datetime.fromisoformat(
            cycle[
                "datetime"
            ]
        )
    )

    if cycle_time.tzinfo is None:

        cycle_time = (
            cycle_time.replace(
                tzinfo=timezone.utc
            )
        )

    return (
        cycle_time.astimezone(
            timezone.utc
        )
    )


# ============================================================
# GFS STREAMING PIPELINE
# ============================================================

def run_gfs(
    cycle=None,
):

    print()
    print("=" * 70)
    print(
        "MASSACHUSETTSWX "
        "NCEP GFS "
        "STREAMING PIPELINE"
    )
    print("=" * 70)

    cycle_hour_hint = (
        int(
            cycle[
                "hour"
            ]
        )
        if cycle is not None
        else None
    )

    forecast_hours = (
        get_forecast_hours(
            "gfs",
            cycle_hour=(
                cycle_hour_hint
            ),
        )
    )

    instantaneous_products = (
        get_default_products_for_model(
            "gfs"
        )
    )

    sequence_products = (
        get_sequence_products_for_model(
            "gfs"
        )
    )

    download_products = (
        get_download_products_for_model(
            "gfs"
        )
    )

    requested_cycle_time = (
        cycle_to_datetime(
            cycle
        )
    )

    date, downloaded_cycle_hour = (
        resolve_gfs_cycle(
            requested_cycle_time
        )
    )

    cycle_date = (
        date.strftime(
            "%Y%m%d"
        )
    )

    cycle_name = (
        f"{cycle_date}_"
        f"{downloaded_cycle_hour:02d}z"
    )

    all_forecast_hours = list(
        forecast_hours
    )

    forecast_hours = (
        get_remaining_forecast_hours(
            model="gfs",
            cycle_date=cycle_date,
            cycle_hour=(
                downloaded_cycle_hour
            ),
            forecast_hours=(
                all_forecast_hours
            ),
        )
    )

    cycle_output_dir = (
        build_local_output_cycle_dir(
            model="gfs",
            cycle_date=(
                cycle_date
            ),
            cycle_hour=(
                downloaded_cycle_hour
            ),
        )
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
        f"Forecast frames: "
        f"{len(forecast_hours)}"
    )

    print(
        f"First: "
        f"f{forecast_hours[0]:03d}"
    )

    print(
        f"Last: "
        f"f{forecast_hours[-1]:03d}"
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
        f"Raw download products: "
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

    execution_regions = (
        get_gfs_regions()
    )

    print(
        f"GFS region mode: "
        f"{GFS_REGION_MODE}"
    )

    print(
        f"Execution regions: "
        f"{len(execution_regions)}"
    )

    print(
        "First execution regions: "
        f"{execution_regions[:10]}"
    )

    sequence_processor = (
        SequenceStreamProcessor(
            model="gfs",
            output_dir=(
                cycle_output_dir
            ),
            regions=(
                execution_regions
            ),
            overwrite=(
                OVERWRITE_EXISTING
            ),
        )
    )

    result = {
        "created": 0,
        "skipped": 0,
        "failed": 0,
        "forecast_hours_expected": (
            len(
                all_forecast_hours
            )
        ),
        "forecast_hours_downloaded": 0,
        "forecast_hours_processed": 0,
        "cloud_uploaded": 0,
        "cloud_upload_failed": 0,
        "local_png_removed": 0,
        "first_forecast_hour": (
            all_forecast_hours[
                0
            ]
        ),
        "last_forecast_hour": (
            all_forecast_hours[
                -1
            ]
        ),
    }

    stopped_at_upstream_frontier = False

    # ========================================================
    # ONE-HOUR-AHEAD DOWNLOAD PREFETCH
    #
    # Forecast-hour processing remains ordered. Only the NEXT
    # NOAA download overlaps current-hour rendering/upload.
    # ========================================================

    def download_one_hour(
        forecast_hour,
    ):

        return (
            download_gfs_hour(
                date,
                downloaded_cycle_hour,
                forecast_hour,
                download_products,
            )
        )

    prefetcher = (
        ForecastHourPrefetcher(
            download_one_hour
        )
    )

    resources = (
        ModelExecutionResources(
            model="gfs",
        )
    )

    lifecycle = (
        OperationalLifecycle(
            model="gfs",
        )
    )

    print(
        "GFS operational lifecycle:",
        lifecycle.summary(),
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
            "GFS PREFETCH: "
            f"started f{forecast_hours[0]:03d}"
        )

    consecutive_unavailable = 0

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
                f"GFS FORECAST HOUR "
                f"{index}/"
                f"{len(forecast_hours)}: "
                f"f{forecast_hour:03d}"
            )

            print("=" * 70)

            check_working_disk_space(
                MIN_FREE_DISK_GB
            )

            grib_path = None

            try:

                # ====================================================
                # DOWNLOAD ONE FORECAST HOUR
                # ====================================================

                print(
                    f"GFS PREFETCH: "
                    f"waiting for "
                    f"f{forecast_hour:03d}"
                )

                grib_path = (
                    prefetcher.get(
                        forecast_hour
                    )
                )

                if grib_path is None:

                    consecutive_unavailable += 1

                    print(
                        f"GFS "
                        f"f{forecast_hour:03d}: "
                        f"temporarily unavailable; "
                        f"forward scanning "
                        f"({consecutive_unavailable}/"
                        f"{GFS_FORWARD_SCAN_MISSES})"
                    )

                    # One missing NOAA hour is NOT sufficient
                    # evidence that we reached the real frontier.
                    #
                    # Keep moving through the scheduled forecast
                    # hours until several CONSECUTIVE misses occur.

                    if (
                        consecutive_unavailable
                        <
                        GFS_FORWARD_SCAN_MISSES
                    ):

                        # The failed prefetch has already been
                        # consumed by prefetcher.get(), which clears
                        # its internal future. Explicitly launch the
                        # NEXT scheduled forecast hour before moving
                        # the loop forward.
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
                                "GFS FORWARD SCAN: "
                                f"prefetching "
                                f"f{next_forecast_hour:03d} "
                                f"after missing "
                                f"f{forecast_hour:03d}"
                            )

                            continue

                        # No later scheduled hour exists.
                        stopped_at_upstream_frontier = True
                        break

                    print(
                        "GFS priority lane: "
                        f"{GFS_FORWARD_SCAN_MISSES} "
                        "consecutive forecast hours "
                        "unavailable; real upstream "
                        "frontier reached."
                    )

                    stopped_at_upstream_frontier = True

                    break

                lifecycle.mark_progress()

                if (
                    not grib_path.exists()
                    or
                    grib_path.stat().st_size
                    <= 0
                ):

                    raise RuntimeError(
                        f"GFS "
                        f"f{forecast_hour:03d}: "
                        f"download produced "
                        f"no usable GRIB"
                    )

                # A successfully downloaded later frame proves
                # that any previous missing hour was a temporary
                # dissemination hole rather than the true frontier.

                consecutive_unavailable = 0

                result[
                    "forecast_hours_downloaded"
                ] += 1

                # ====================================================
                # PREFETCH NEXT NOAA FORECAST HOUR
                #
                # enumerate() is 1-based, so forecast_hours[index]
                # is the NEXT scheduled frame.
                # ====================================================

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
                        f"GFS PREFETCH: "
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
                        model="gfs",
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
                            execution_regions
                        ),
                        overwrite=(
                            OVERWRITE_EXISTING
                        ),
                        executor=(
                            render_executor
                        ),
                    )
                )

                for key in (
                    "created",
                    "skipped",
                    "failed",
                ):

                    result[
                        key
                    ] += int(
                        instant_result.get(
                            key,
                            0,
                        )
                    )

                instantaneous_failed = int(
                    instant_result.get(
                        "failed",
                        0,
                    )
                )

                if instantaneous_failed > 0:

                    raise RuntimeError(
                        f"GFS "
                        f"f{forecast_hour:03d}: "
                        f"{instantaneous_failed} "
                        f"instantaneous product outputs failed; "
                        f"forecast hour will NOT be published"
                    )

                # ====================================================
                # SEQUENCE PRODUCTS
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

                for key in (
                    "created",
                    "skipped",
                    "failed",
                ):

                    result[
                        key
                    ] += int(
                        sequence_result.get(
                            key,
                            0,
                        )
                    )

                sequence_failed = int(
                    sequence_result.get(
                        "failed",
                        0,
                    )
                )

                if sequence_failed > 0:

                    raise RuntimeError(
                        f"GFS "
                        f"f{forecast_hour:03d}: "
                        f"{sequence_failed} "
                        f"sequence product outputs failed; "
                        f"forecast hour will NOT be published"
                    )

                # ====================================================
                # GCS UPLOAD + LOCAL PNG CLEANUP
                # ====================================================

                expected_hour_products = (
                    products_for_forecast_hour(
                        model="gfs",
                        products=(
                            get_default_products_for_model(
                                "gfs"
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
                                "gfs"
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
                        model="gfs",
                        cycle_date=(
                            cycle_date
                        ),
                        cycle_hour=(
                            downloaded_cycle_hour
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
                            execution_regions
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

                if (
                    upload_result[
                        "failed"
                    ]
                    > 0
                ):

                    result[
                        "failed"
                    ] += upload_result[
                        "failed"
                    ]

                result[
                    "forecast_hours_processed"
                ] += 1

            except Exception as error:

                result[
                    "failed"
                ] += 1

                print(
                    f"GFS "
                    f"f{forecast_hour:03d}: "
                    f"PIPELINE FAILED: "
                    f"{error}"
                )

            finally:

                # ====================================================
                # RAW GRIB IS NEVER KEPT AFTER THIS HOUR
                # ====================================================

                if (
                    grib_path
                    is not None
                ):

                    try:

                        if grib_path.exists():

                            size_mb = (
                                grib_path
                                .stat()
                                .st_size
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
                                f"GFS "
                                f"f{forecast_hour:03d} "
                                f"GRIB "
                                f"({size_mb:.2f} MB)"
                            )

                    except Exception as error:

                        print(
                            f"GFS GRIB CLEANUP "
                            f"FAILED "
                            f"f{forecast_hour:03d}: "
                            f"{error}"
                        )

                remove_empty_directories(
                    cycle_output_dir
                )

                check_working_disk_space(
                    MIN_FREE_DISK_GB
                )

    finally:

        resources.close()
        prefetcher.close()

        sequence_processor.finish()

        remove_empty_directories(
            cycle_output_dir
        )

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
        f"GFS STREAMING PIPELINE "
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
        f"Failures: "
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

    run_gfs()
