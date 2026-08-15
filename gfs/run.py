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

    sequence_processor = (
        SequenceStreamProcessor(
            model="gfs",
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

                    raise RuntimeError(
                        f"GFS "
                        f"f{forecast_hour:03d}: "
                        f"not available"
                    )

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
                            OPERATIONAL_REGIONS
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

                # ====================================================
                # GCS UPLOAD + LOCAL PNG CLEANUP
                # ====================================================

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

    print()
    print("=" * 70)
    print(
        "GFS STREAMING PIPELINE COMPLETE"
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

    print("=" * 70)

    return result


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_gfs()
