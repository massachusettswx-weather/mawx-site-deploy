import shutil

from pathlib import Path

from .download import (
    download_ifs_hour,
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

from shared.sequence import (
    SequenceStreamProcessor,
)

from shared.storage import (
    get_local_root,
    upload_file,
    delete_local,
)


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
# CLOUD UPLOAD + LOCAL DELETE
# ============================================================

def upload_and_remove_step_outputs(
    *,
    cycle_output_dir,
    cycle_name,
    step,
):
    """
    Upload every PNG generated for one forecast hour.

    Local PNGs are removed only AFTER the corresponding GCS upload
    succeeds.
    """

    cycle_output_dir = Path(
        cycle_output_dir
    )

    forecast_tag = (
        f"f{int(step):03d}"
    )

    png_files = sorted(
        cycle_output_dir.rglob(
            f"*{forecast_tag}.png"
        )
    )

    uploaded = 0
    failed = 0
    removed = 0

    if not png_files:

        print(
            f"f{int(step):03d}: "
            f"no PNG files found for upload"
        )

        return {
            "uploaded": 0,
            "failed": 0,
            "removed": 0,
        }

    print()
    print(
        f"Uploading "
        f"{len(png_files)} "
        f"f{int(step):03d} products..."
    )

    for local_path in (
        png_files
    ):

        relative_path = (
            local_path.relative_to(
                cycle_output_dir
            )
        )

        object_name = (
            f"products/"
            f"ifs/"
            f"{cycle_name}/"
            f"{relative_path.as_posix()}"
        )

        try:

            upload_file(
                local_path=local_path,
                object_name=object_name,
                content_type="image/png",
            )

            uploaded += 1

            # ------------------------------------------------
            # DELETE PNG ONLY AFTER SUCCESSFUL CLOUD UPLOAD
            # ------------------------------------------------

            local_path.unlink(
                missing_ok=True
            )

            removed += 1

        except Exception as error:

            failed += 1

            print(
                f"UPLOAD FAILED: "
                f"{relative_path}: "
                f"{error}"
            )

    print(
        f"f{int(step):03d} upload: "
        f"uploaded={uploaded}, "
        f"failed={failed}, "
        f"local_removed={removed}"
    )

    return {
        "uploaded": uploaded,
        "failed": failed,
        "removed": removed,
    }


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

    forecast_hours = (
        get_forecast_hours(
            "ifs",
            cycle_hour=cycle_hour,
        )
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

            grib_path = None

            try:

                # ====================================================
                # DOWNLOAD ONE HOUR
                # ====================================================

                grib_path = (
                    download_ifs_hour(
                        forecast_hour,
                        products=(
                            download_products
                        ),
                        cycle=cycle,
                    )
                )

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

                # ====================================================
                # UPLOAD THIS HOUR'S PNGs AND IMMEDIATELY REMOVE THEM
                # ====================================================

                upload_result = (
                    upload_and_remove_step_outputs(
                        cycle_output_dir=(
                            cycle_output_dir
                        ),
                        cycle_name=(
                            cycle_name
                        ),
                        step=(
                            forecast_hour
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

    print()
    print("=" * 70)
    print(
        "IFS STREAMING PIPELINE COMPLETE"
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

    print("=" * 70)

    return result


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_ifs()