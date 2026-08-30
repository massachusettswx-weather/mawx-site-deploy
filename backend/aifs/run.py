from .download import (
    download_aifs_hour,
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

from shared.execution import (
    ModelExecutionResources,
)

from shared.models import (
    get_forecast_hours,
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

import time

def _aifs_authoritative_map_plan(*, completed_inventory, expected_products, execution_regions, forecast_hour):
    plan = map_work_plan_for_hour(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)
    report = map_region_report(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)
    missing_maps = sum(len(item["missing"]) for item in report.values())
    print("AIFS " + f"f{int(forecast_hour):03d}: {missing_maps} missing region/product maps")
    return plan, report

def _aifs_map_hour_complete(*, completed_inventory, expected_products, execution_regions, forecast_hour):
    return map_hour_complete(completed=completed_inventory, products=expected_products, regions=execution_regions, forecast_hour=forecast_hour)


def _aifs_operational_forecast_hours(cycle_hour=None):
    return sorted(set(int(hour) for hour in get_forecast_hours(
        "aifs", cycle_hour=cycle_hour,
    )))

# ============================================================
# SETTINGS
# ============================================================

OVERWRITE_EXISTING = False

MIN_FREE_DISK_GB = 3.0


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
        "name": cycle[
            "id"
        ],

        "date": str(
            cycle[
                "date"
            ]
        ),

        "hour": int(
            cycle[
                "hour"
            ]
        ),
    }


# ============================================================
# AIFS STREAMING PIPELINE
# ============================================================

def run_aifs(
    cycle=None,
):

    print()
    print("=" * 70)

    print(
        "MASSACHUSETTSWX "
        "ECMWF AIFS "
        "STREAMING PIPELINE"
    )

    print("=" * 70)

    identity = (
        get_cycle_identity(
            cycle
        )
    )

    all_forecast_hours = (
        get_forecast_hours(
            "aifs",
            cycle_hour=(
                identity[
                    "hour"
                ]
            ),
        )
    )

    if identity["date"] != "latest":

        forecast_hours = (
            get_remaining_forecast_hours(
                model="aifs",
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

    instantaneous_products = (
        get_default_products_for_model(
            "aifs"
        )
    )

    sequence_products = (
        get_sequence_products_for_model(
            "aifs"
        )
    )

    download_products = (
        get_download_products_for_model(
            "aifs"
        )
    )

    cycle_output_dir = (
        build_local_output_cycle_dir(
            model="aifs",

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
        )
    )

    cycle_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Cycle: "
        f"{identity['name']}"
    )

    print(
        f"Forecast hours: "
        f"{len(all_forecast_hours)}"
    )

    print(
        f"First: "
        f"f{all_forecast_hours[0]:03d}"
    )

    print(
        f"Last: "
        f"f{all_forecast_hours[-1]:03d}"
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
            model="aifs",

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

    stopped_at_upstream_frontier = False

    # ========================================================
    # ONE-HOUR-AHEAD ECMWF AIFS DOWNLOAD PREFETCH
    # ========================================================

    def download_one_hour(
        forecast_hour,
    ):

        return (
            download_aifs_hour(
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
            model="aifs",
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
            "AIFS PREFETCH: "
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
                f"AIFS FORECAST HOUR "
                f"{index}/"
                f"{len(forecast_hours)}: "
                f"f{forecast_hour:03d}"
            )

            print("=" * 70)

            check_working_disk_space(
                MIN_FREE_DISK_GB
            )

            hour_started_at = time.monotonic()
            grib_path = None

            try:

                print(
                    f"AIFS PREFETCH: "
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
                        f"AIFS "
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
                        f"AIFS "
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
                        f"AIFS PREFETCH: "
                        f"downloading "
                        f"f{next_forecast_hour:03d} "
                        f"while "
                        f"f{forecast_hour:03d} "
                        f"is processed"
                    )

                instant_result = (
                    run_forecast_hour(
                        grib_path=(
                            grib_path
                        ),

                        model="aifs",

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
                        f"AIFS "
                        f"f{forecast_hour:03d}: "
                        f"{instantaneous_failed} "
                        f"instantaneous plots failed; "
                        f"forecast hour will NOT "
                        f"be published."
                    )

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
                        f"AIFS "
                        f"f{forecast_hour:03d}: "
                        f"{sequence_failed} "
                        f"sequence plots failed; "
                        f"forecast hour will NOT "
                        f"be published."
                    )

                expected_hour_products = (
                    products_for_forecast_hour(
                        model="aifs",
                        products=(
                            get_default_products_for_model(
                                "aifs"
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
                                "aifs"
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
                        model="aifs",

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
                    f"AIFS "
                    f"f{forecast_hour:03d}: "
                    f"PIPELINE FAILED: "
                    f"{error}"
                )

            finally:

                elapsed_seconds = (
                    time.monotonic()
                    - hour_started_at
                )

                print(
                    "AIFS "
                    f"f{forecast_hour:03d} "
                    f"elapsed={elapsed_seconds:.1f}s"
                )

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
                                f"AIFS "
                                f"f{forecast_hour:03d} "
                                f"GRIB "
                                f"({size_mb:.2f} MB)"
                            )

                    except Exception as error:

                        print(
                            f"AIFS GRIB CLEANUP "
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

    print()
    print("=" * 70)

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

    print(
        f"AIFS STREAMING PIPELINE {pipeline_status.upper()}"
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

    run_aifs()
