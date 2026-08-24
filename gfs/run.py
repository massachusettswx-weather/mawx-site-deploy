import os

from datetime import (
    datetime,
    timezone,
)

from .download import (
    download_gfs_hour,
    resolve_gfs_cycle,
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
# SETTINGS
# ============================================================

OVERWRITE_EXISTING = False


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
        "priority",
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

                grib_path = (
                    download_gfs_hour(
                        date,
                        downloaded_cycle_hour,
                        forecast_hour,
                        download_products,
                    )
                )

                if grib_path is None:

                    print(
                        f"GFS "
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
                        f"GFS "
                        f"f{forecast_hour:03d}: "
                        f"download produced "
                        f"no usable GRIB"
                    )

                result[
                    "forecast_hours_downloaded"
                ] += 1

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
