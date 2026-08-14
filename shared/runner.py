from pathlib import Path

from concurrent.futures import (
    ProcessPoolExecutor,
    as_completed,
)

import time


from shared.data import (
    load_product,
)

from shared.plotting import (
    render_product,
)

from shared.products import (
    PRODUCTS,
    OPERATIONAL_PRODUCTS,
    ACCUMULATION_PRODUCTS,
    WINDOWED_ACCUMULATION_PRODUCTS,
    CATEGORICAL_PRODUCTS,
)

from shared.regions import (
    REGIONS,
)

from shared.download import (
    products_for_model,
)

from shared.models import (
    MODELS,
    model_exists,
    get_model_name,
    get_model_extra_products,
    model_supports_sequences,
    get_model_workers,
)


# ============================================================
# DEFAULT REGIONS
# ============================================================

# REGIONS is the source of truth for the operational region set.
# Python dictionaries preserve insertion order, so the website/backend
# region ordering follows shared/regions.py.
OPERATIONAL_REGIONS = list(
    REGIONS.keys()
)


# ============================================================
# BACKWARD-COMPATIBLE NAME DICTIONARY
# ============================================================

MODEL_NAMES = {
    model: config[
        "name"
    ]

    for model, config
    in MODELS.items()
}


# ============================================================
# DEFAULT PRODUCTS
# ============================================================

def get_default_products_for_model(
    model,
):
    if not model_exists(
        model
    ):

        raise ValueError(
            f"Unknown model: "
            f"{model}"
        )

    common = (
        products_for_model(
            model,
            OPERATIONAL_PRODUCTS,
        )
    )

    extras = (
        get_model_extra_products(
            model
        )
    )

    final = []
    seen = set()

    for product_name in (
        common
        +
        extras
    ):

        if product_name not in PRODUCTS:
            continue

        if model not in PRODUCTS[
            product_name
        ]:
            continue

        if product_name in seen:
            continue

        if product_name in (
            ACCUMULATION_PRODUCTS
            +
            WINDOWED_ACCUMULATION_PRODUCTS
            +
            CATEGORICAL_PRODUCTS
        ):
            continue

        seen.add(
            product_name
        )

        final.append(
            product_name
        )

    return final


# ============================================================
# SEQUENCE PRODUCTS
# ============================================================

def get_sequence_products_for_model(
    model,
):
    if not model_supports_sequences(
        model
    ):

        return []

    requested = (
        ACCUMULATION_PRODUCTS
        +
        CATEGORICAL_PRODUCTS
    )

    return products_for_model(
        model,
        requested,
    )


# ============================================================
# DOWNLOAD PRODUCTS
# ============================================================

def get_download_products_for_model(
    model,
):
    instantaneous = (
        get_default_products_for_model(
            model
        )
    )

    sequence = (
        get_sequence_products_for_model(
            model
        )
    )

    final = []
    seen = set()

    for product_name in (
        instantaneous
        +
        sequence
    ):

        if product_name in seen:
            continue

        seen.add(
            product_name
        )

        final.append(
            product_name
        )

    return final


# ============================================================
# OUTPUT PATH
# ============================================================

def build_output_path(
    *,
    output_dir,
    model,
    product_name,
    region_name,
    step,
):
    forecast_hour = (
        f"{step:03d}"
    )

    product_dir = (
        Path(
            output_dir
        )
        / product_name
        / region_name
    )

    filename = (
        f"{model}_"
        f"{product_name}_"
        f"{region_name}_"
        f"f{forecast_hour}.png"
    )

    return (
        product_dir
        / filename
    )


# ============================================================
# RUN ONE PRODUCT
# ============================================================

def run_product(
    *,
    grib_path,
    model,
    product_name,
    step,
    output_dir,
    regions=None,
    overwrite=False,
):
    if regions is None:

        regions = (
            OPERATIONAL_REGIONS
        )

    if not model_exists(
        model
    ):

        raise ValueError(
            f"Unknown model: "
            f"{model}"
        )

    if product_name not in PRODUCTS:

        raise ValueError(
            f"Unknown product: "
            f"{product_name}"
        )

    product = PRODUCTS[
        product_name
    ]

    if model not in product:

        return {
            "created": 0,
            "skipped": 0,
            "failed": 0,
        }

    pending = []
    skipped = 0

    for region_name in regions:

        if region_name not in REGIONS:
            continue

        output_path = (
            build_output_path(
                output_dir=output_dir,
                model=model,
                product_name=product_name,
                region_name=region_name,
                step=step,
            )
        )

        if (
            output_path.exists()
            and not overwrite
        ):

            skipped += 1

        else:

            pending.append(
                (
                    region_name,
                    output_path,
                )
            )

    if not pending:

        return {
            "created": 0,
            "skipped": skipped,
            "failed": 0,
        }

    print(
        f"f{step:03d} "
        f"loading "
        f"{product_name}"
    )

    data = load_product(
        grib_path,
        model=model,
        product_name=product_name,
    )

    created = 0
    failed = 0

    for (
        region_name,
        output_path,
    ) in pending:

        try:

            render_product(
                data=data,
                product_name=product_name,
                region_name=region_name,
                output_path=output_path,
                model_name=(
                    get_model_name(
                        model
                    )
                ),
            )

            created += 1

        except Exception as error:

            failed += 1

            print(
                f"FAILED "
                f"f{step:03d} "
                f"{product_name} "
                f"{region_name}: "
                f"{error}"
            )

    return {
        "created": created,
        "skipped": skipped,
        "failed": failed,
    }


# ============================================================
# PROCESS-POOL PRODUCT WORKER
#
# One worker handles ONE product for ONE forecast hour.
# The worker loads that product once, then renders all requested
# regions serially. This avoids repeatedly loading the same field
# for every region while still parallelizing the expensive work.
#
# Must remain top-level so multiprocessing can pickle it.
# ============================================================

def _product_worker(
    task,
):
    (
        grib_path,
        model,
        product_name,
        step,
        output_dir,
        regions,
        overwrite,
    ) = task

    result = run_product(
        grib_path=grib_path,
        model=model,
        product_name=product_name,
        step=step,
        output_dir=output_dir,
        regions=regions,
        overwrite=overwrite,
    )

    return (
        product_name,
        result,
    )


# ============================================================
# RUN ONE FORECAST HOUR
# ============================================================

def run_forecast_hour(
    *,
    grib_path,
    model,
    step,
    output_dir,
    products=None,
    regions=None,
    overwrite=False,
):
    if products is None:

        products = (
            get_default_products_for_model(
                model
            )
        )

    if regions is None:

        regions = (
            OPERATIONAL_REGIONS
        )

    if not model_exists(
        model
    ):

        raise ValueError(
            f"Unknown model: "
            f"{model}"
        )

    products = list(
        products
    )

    regions = list(
        regions
    )

    workers = max(
        1,
        int(
            get_model_workers(
                model
            )
        ),
    )

    workers = min(
        workers,
        max(
            1,
            len(
                products
            ),
        ),
    )

    print()
    print(
        f"BEGIN "
        f"{get_model_name(model)} "
        f"f{step:03d}"
    )

    print(
        f"Product workers: "
        f"{workers}"
    )

    total_created = 0
    total_skipped = 0
    total_failed = 0

    # --------------------------------------------------------
    # SERIAL FALLBACK
    # --------------------------------------------------------

    if (
        workers <= 1
        or
        len(
            products
        ) <= 1
    ):

        for product_name in (
            products
        ):

            try:

                result = run_product(
                    grib_path=grib_path,
                    model=model,
                    product_name=product_name,
                    step=step,
                    output_dir=output_dir,
                    regions=regions,
                    overwrite=overwrite,
                )

                total_created += (
                    result[
                        "created"
                    ]
                )

                total_skipped += (
                    result[
                        "skipped"
                    ]
                )

                total_failed += (
                    result[
                        "failed"
                    ]
                )

            except Exception as error:

                total_failed += (
                    len(
                        regions
                    )
                )

                print(
                    f"PRODUCT FAILED "
                    f"f{step:03d} "
                    f"{product_name}: "
                    f"{error}"
                )

    # --------------------------------------------------------
    # PARALLEL PRODUCTS
    #
    # Forecast hours remain strictly sequential. Only products
    # inside the current forecast hour are processed concurrently.
    # Each worker loads one product once and renders all regions.
    # --------------------------------------------------------

    else:

        tasks = []

        for product_name in (
            products
        ):

            tasks.append(
                (
                    str(
                        grib_path
                    ),
                    model,
                    product_name,
                    int(
                        step
                    ),
                    str(
                        output_dir
                    ),
                    list(
                        regions
                    ),
                    bool(
                        overwrite
                    ),
                )
            )

        print(
            f"Starting "
            f"{workers} parallel "
            f"product workers "
            f"for f{step:03d}..."
        )

        with ProcessPoolExecutor(
            max_workers=workers
        ) as executor:

            future_map = {
                executor.submit(
                    _product_worker,
                    task,
                ):
                task[
                    2
                ]

                for task in tasks
            }

            completed = 0

            for future in as_completed(
                future_map
            ):

                product_name = (
                    future_map[
                        future
                    ]
                )

                completed += 1

                try:

                    (
                        returned_product,
                        result,
                    ) = future.result()

                except Exception as error:

                    total_failed += (
                        len(
                            regions
                        )
                    )

                    print(
                        f"PRODUCT WORKER FAILED "
                        f"f{step:03d} "
                        f"{product_name}: "
                        f"{error}"
                    )

                    continue

                total_created += (
                    result[
                        "created"
                    ]
                )

                total_skipped += (
                    result[
                        "skipped"
                    ]
                )

                total_failed += (
                    result[
                        "failed"
                    ]
                )

                print(
                    f"Product "
                    f"{completed}/"
                    f"{len(tasks)} complete "
                    f"for f{step:03d}: "
                    f"{returned_product}"
                )

    print(
        f"END f{step:03d}: "
        f"created={total_created}, "
        f"skipped={total_skipped}, "
        f"failed={total_failed}"
    )

    return {
        "created": total_created,
        "skipped": total_skipped,
        "failed": total_failed,
        "workers": workers,
    }


# ============================================================
# PROCESS-POOL WORKER
#
# Must remain top-level so it can be pickled by
# multiprocessing.
# ============================================================

def _forecast_hour_worker(
    task,
):
    (
        grib_path,
        model,
        step,
        output_dir,
        products,
        regions,
        overwrite,
    ) = task

    result = run_forecast_hour(
        grib_path=grib_path,
        model=model,
        step=step,
        output_dir=output_dir,
        products=products,
        regions=regions,
        overwrite=overwrite,
    )

    return (
        step,
        result,
    )


# ============================================================
# SERIAL MODEL CYCLE
# ============================================================

def _run_model_cycle_serial(
    *,
    model,
    forecast_files,
    output_dir,
    products,
    regions,
    overwrite,
):
    total_created = 0
    total_skipped = 0
    total_failed = 0

    for step, grib_path in (
        forecast_files
    ):

        result = run_forecast_hour(
            grib_path=grib_path,
            model=model,
            step=step,
            output_dir=output_dir,
            products=products,
            regions=regions,
            overwrite=overwrite,
        )

        total_created += (
            result[
                "created"
            ]
        )

        total_skipped += (
            result[
                "skipped"
            ]
        )

        total_failed += (
            result[
                "failed"
            ]
        )

    return {
        "created": total_created,
        "skipped": total_skipped,
        "failed": total_failed,
    }


# ============================================================
# PARALLEL MODEL CYCLE
# ============================================================

def _run_model_cycle_parallel(
    *,
    model,
    forecast_files,
    output_dir,
    products,
    regions,
    overwrite,
    workers,
):
    total_created = 0
    total_skipped = 0
    total_failed = 0

    tasks = []

    for step, grib_path in (
        forecast_files
    ):

        tasks.append(
            (
                str(
                    grib_path
                ),
                model,
                int(
                    step
                ),
                str(
                    output_dir
                ),
                list(
                    products
                ),
                list(
                    regions
                ),
                bool(
                    overwrite
                ),
            )
        )

    print()
    print(
        f"Starting "
        f"{workers} parallel "
        f"forecast-hour workers..."
    )

    with ProcessPoolExecutor(
        max_workers=workers
    ) as executor:

        future_map = {
            executor.submit(
                _forecast_hour_worker,
                task,
            ):
            task[
                2
            ]

            for task in tasks
        }

        completed = 0

        for future in as_completed(
            future_map
        ):

            step = future_map[
                future
            ]

            completed += 1

            try:

                returned_step, result = (
                    future.result()
                )

            except Exception as error:

                # Count the entire forecast-hour product/region
                # workload as failed if the worker itself dies.
                hour_failures = (
                    len(
                        products
                    )
                    *
                    len(
                        regions
                    )
                )

                total_failed += (
                    hour_failures
                )

                print(
                    f"WORKER FAILED "
                    f"f{step:03d}: "
                    f"{error}"
                )

                continue

            total_created += (
                result[
                    "created"
                ]
            )

            total_skipped += (
                result[
                    "skipped"
                ]
            )

            total_failed += (
                result[
                    "failed"
                ]
            )

            print(
                f"Forecast hour "
                f"{completed}/"
                f"{len(tasks)} complete: "
                f"f{returned_step:03d}"
            )

    return {
        "created": total_created,
        "skipped": total_skipped,
        "failed": total_failed,
    }


# ============================================================
# RUN COMPLETE MODEL CYCLE
# ============================================================

def run_model_cycle(
    *,
    model,
    forecast_files,
    output_dir,
    products=None,
    regions=None,
    overwrite=False,
):
    if not model_exists(
        model
    ):

        raise ValueError(
            f"Unknown model: "
            f"{model}"
        )

    if products is None:

        products = (
            get_default_products_for_model(
                model
            )
        )

    if regions is None:

        regions = (
            OPERATIONAL_REGIONS
        )

    output_dir = Path(
        output_dir
    )

    forecast_files = sorted(
        forecast_files,
        key=lambda item: item[
            0
        ],
    )

    workers = max(
        1,
        int(
            get_model_workers(
                model
            )
        ),
    )

    start_time = (
        time.time()
    )

    print()
    print("=" * 70)

    print(
        "MASSACHUSETTSWX "
        "MODEL PIPELINE"
    )

    print("=" * 70)

    print(
        f"Model: "
        f"{get_model_name(model)}"
    )

    print(
        f"Forecast hours: "
        f"{len(forecast_files)}"
    )

    print(
        f"Products: "
        f"{len(products)}"
    )

    print(
        f"Regions: "
        f"{len(regions)}"
    )

    print(
        f"Product workers: "
        f"{workers}"
    )

    print(
        "Forecast-hour mode: "
        "serial"
    )

    print("=" * 70)

    # ========================================================
    # FORECAST HOURS ARE ALWAYS SERIAL
    #
    # This is intentional for the streaming architecture:
    #
    #   download one hour
    #   -> render products in parallel
    #   -> sequence/upload/cleanup
    #   -> next hour
    #
    # Running forecast hours concurrently would multiply GRIB,
    # memory, and temporary-storage requirements.
    # ========================================================

    result = (
        _run_model_cycle_serial(
            model=model,
            forecast_files=forecast_files,
            output_dir=output_dir,
            products=products,
            regions=regions,
            overwrite=overwrite,
        )
    )

    elapsed = (
        time.time()
        -
        start_time
    )

    print()
    print("=" * 70)

    print(
        "MODEL PIPELINE COMPLETE"
    )

    print("=" * 70)

    print(
        f"Model: "
        f"{get_model_name(model)}"
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
        f"Runtime: "
        f"{elapsed / 60:.1f} "
        f"minutes"
    )

    print(
        f"Product workers: "
        f"{workers}"
    )

    print("=" * 70)

    result[
        "runtime_seconds"
    ] = elapsed

    result[
        "workers"
    ] = workers

    return result
