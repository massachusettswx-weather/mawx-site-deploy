import numpy as np

from shared.data import (
    load_product,
)

from shared.plotting import (
    render_product,
)

from shared.products import (
    PRODUCTS,
    ACCUMULATION_PRODUCTS,
    WINDOWED_ACCUMULATION_PRODUCTS,
    CATEGORICAL_PRODUCTS,
)

from shared.runner import (
    MODEL_NAMES,
    OPERATIONAL_REGIONS,
    build_output_path,
)


# ============================================================
# DATA COPY
# ============================================================

def clone_with_field(
    data,
    field_name,
    values,
):
    output = {
        key: value
        for key, value
        in data.items()
    }

    output[
        "fields"
    ] = {
        key: value
        for key, value
        in data[
            "fields"
        ].items()
    }

    output[
        "fields"
    ][
        field_name
    ] = values

    return output


# ============================================================
# RENDER DATASET TO REGIONS
# ============================================================

def render_regions(
    *,
    model,
    product_name,
    step,
    data,
    output_dir,
    regions,
    overwrite,
):
    created = 0
    skipped = 0
    failed = 0

    for region_name in regions:

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
            and
            not overwrite
        ):

            skipped += 1
            continue

        try:

            render_product(
                data=data,
                product_name=product_name,
                region_name=region_name,
                output_path=output_path,
                model_name=MODEL_NAMES[
                    model
                ],
            )

            created += 1

        except Exception as error:

            failed += 1

            print(
                f"SEQUENCE FAILED "
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
# WINDOW DIFFERENCE
# ============================================================

def create_window_data(
    current_data,
    previous_data,
    *,
    field_name,
    product,
):
    current = (
        current_data[
            "fields"
        ][
            field_name
        ]
    )

    previous = (
        previous_data[
            "fields"
        ][
            field_name
        ]
    )

    difference = (
        current
        -
        previous
    )

    difference = np.maximum(
        difference,
        0,
    )

    output = clone_with_field(
        current_data,
        field_name,
        difference,
    )

    output = dict(
        output
    )

    # Use the window product's rendering configuration.
    output[
        "product"
    ] = product

    return output


# ============================================================
# STREAMING SEQUENCE PROCESSOR
# ============================================================

class SequenceStreamProcessor:
    """
    Process sequence products one forecast hour at a time.

    Only the minimum amount of derived sequence state is retained.

    Raw GRIB files do NOT need to remain available after process_hour()
    returns.
    """

    def __init__(
        self,
        *,
        model,
        output_dir,
        regions=None,
        overwrite=False,
    ):
        self.model = model
        self.output_dir = output_dir

        if regions is None:
            regions = (
                OPERATIONAL_REGIONS
            )

        self.regions = list(
            regions
        )

        self.overwrite = bool(
            overwrite
        )

        # ----------------------------------------------------
        # TOTAL PRECIP STATE
        # ----------------------------------------------------

        self.precip_running_total = None

        self.precip_history = {}

        # ----------------------------------------------------
        # DETERMINE MAXIMUM WINDOW WE MUST RETAIN
        # ----------------------------------------------------

        window_hours = []

        for product_name in (
            WINDOWED_ACCUMULATION_PRODUCTS
        ):

            if (
                product_name
                not in PRODUCTS
            ):

                continue

            product = PRODUCTS[
                product_name
            ]

            if (
                self.model
                not in product
            ):

                continue

            window = product.get(
                "window_hours"
            )

            if window is not None:

                window_hours.append(
                    int(
                        window
                    )
                )

        self.max_window_hours = (
            max(
                window_hours
            )
            if window_hours
            else 0
        )


    # ========================================================
    # RESULT HELPERS
    # ========================================================

    @staticmethod
    def _empty_result():

        return {
            "created": 0,
            "skipped": 0,
            "failed": 0,
        }


    @staticmethod
    def _add_result(
        total,
        result,
    ):
        total[
            "created"
        ] += result.get(
            "created",
            0,
        )

        total[
            "skipped"
        ] += result.get(
            "skipped",
            0,
        )

        total[
            "failed"
        ] += result.get(
            "failed",
            0,
        )


    # ========================================================
    # TOTAL PRECIP
    # ========================================================

    def _process_total_precip(
        self,
        *,
        step,
        grib_path,
    ):
        result = (
            self._empty_result()
        )

        if (
            "total_precip"
            not in PRODUCTS
        ):

            return result

        product = PRODUCTS[
            "total_precip"
        ]

        if (
            self.model
            not in product
        ):

            return result

        try:

            data = load_product(
                grib_path,
                model=self.model,
                product_name="total_precip",
            )

        except Exception as error:

            print(
                f"{self.model} "
                f"total_precip "
                f"f{step:03d}: "
                f"skipped — "
                f"{error}"
            )

            return result

        model_config = product[
            self.model
        ]

        style = model_config.get(
            "accumulation_style",
            "cumulative",
        )

        field_name = product[
            "shade_field"
        ]

        values = (
            data[
                "fields"
            ][
                field_name
            ]
        )

        values = np.maximum(
            values,
            0,
        )

        # ----------------------------------------------------
        # ECMWF-STYLE CUMULATIVE
        # ----------------------------------------------------

        if style == "cumulative":

            cumulative = values

        # ----------------------------------------------------
        # GFS INTERVAL / TOTAL DETECTION
        # ----------------------------------------------------

        elif (
            style
            ==
            "gfs_interval_or_total"
        ):

            if (
                self.precip_running_total
                is None
            ):

                cumulative = values

            else:

                finite = (
                    np.isfinite(
                        values
                    )
                    &
                    np.isfinite(
                        self.precip_running_total
                    )
                )

                if np.any(
                    finite
                ):

                    fraction_ge = (
                        np.mean(
                            values[
                                finite
                            ]
                            >=
                            self.precip_running_total[
                                finite
                            ]
                        )
                    )

                else:

                    fraction_ge = 0.0

                if (
                    fraction_ge
                    >= 0.90
                ):

                    cumulative = values

                else:

                    cumulative = (
                        self.precip_running_total
                        +
                        values
                    )

            self.precip_running_total = (
                cumulative
            )

        else:

            raise RuntimeError(
                f"Unknown accumulation style: "
                f"{style}"
            )

        cumulative_data = (
            clone_with_field(
                data,
                field_name,
                cumulative,
            )
        )

        # ----------------------------------------------------
        # TOTAL PRECIP MAP
        # ----------------------------------------------------

        total_result = (
            render_regions(
                model=self.model,
                product_name="total_precip",
                step=step,
                data=cumulative_data,
                output_dir=self.output_dir,
                regions=self.regions,
                overwrite=self.overwrite,
            )
        )

        self._add_result(
            result,
            total_result,
        )

        # ----------------------------------------------------
        # SAVE DERIVED STATE
        #
        # This is MUCH smaller than retaining all raw GRIBs.
        # ----------------------------------------------------

        self.precip_history[
            int(
                step
            )
        ] = cumulative_data

        # ----------------------------------------------------
        # WINDOWED ACCUMULATIONS
        # ----------------------------------------------------

        for product_name in (
            WINDOWED_ACCUMULATION_PRODUCTS
        ):

            if (
                product_name
                not in PRODUCTS
            ):

                continue

            window_product = PRODUCTS[
                product_name
            ]

            if (
                self.model
                not in window_product
            ):

                continue

            window_hours = int(
                window_product[
                    "window_hours"
                ]
            )

            previous_step = (
                int(
                    step
                )
                -
                window_hours
            )

            if (
                previous_step
                not in self.precip_history
            ):

                continue

            previous_data = (
                self.precip_history[
                    previous_step
                ]
            )

            window_data = (
                create_window_data(
                    cumulative_data,
                    previous_data,
                    field_name=field_name,
                    product=window_product,
                )
            )

            window_result = (
                render_regions(
                    model=self.model,
                    product_name=product_name,
                    step=step,
                    data=window_data,
                    output_dir=self.output_dir,
                    regions=self.regions,
                    overwrite=self.overwrite,
                )
            )

            self._add_result(
                result,
                window_result,
            )

        # ----------------------------------------------------
        # PRUNE OLD PRECIP STATE
        # ----------------------------------------------------

        if (
            self.max_window_hours
            > 0
        ):

            oldest_needed = (
                int(
                    step
                )
                -
                self.max_window_hours
            )

            remove_steps = [
                history_step
                for history_step
                in self.precip_history
                if (
                    history_step
                    <
                    oldest_needed
                )
            ]

            for history_step in (
                remove_steps
            ):

                del self.precip_history[
                    history_step
                ]

        else:

            # No window products need history.
            self.precip_history = {
                int(
                    step
                ):
                cumulative_data
            }

        return result


    # ========================================================
    # OTHER ACCUMULATION PRODUCTS
    # ========================================================

    def _process_other_accumulations(
        self,
        *,
        step,
        grib_path,
    ):
        result = (
            self._empty_result()
        )

        for product_name in (
            ACCUMULATION_PRODUCTS
        ):

            if (
                product_name
                ==
                "total_precip"
            ):

                continue

            if (
                product_name
                not in PRODUCTS
            ):

                continue

            product = PRODUCTS[
                product_name
            ]

            if (
                self.model
                not in product
            ):

                continue

            try:

                data = load_product(
                    grib_path,
                    model=self.model,
                    product_name=product_name,
                )

            except Exception as error:

                print(
                    f"{product_name} "
                    f"f{step:03d}: "
                    f"skipped — "
                    f"{error}"
                )

                continue

            product_result = (
                render_regions(
                    model=self.model,
                    product_name=product_name,
                    step=step,
                    data=data,
                    output_dir=self.output_dir,
                    regions=self.regions,
                    overwrite=self.overwrite,
                )
            )

            self._add_result(
                result,
                product_result,
            )

        return result


    # ========================================================
    # CATEGORICAL PRODUCTS
    # ========================================================

    def _process_categorical(
        self,
        *,
        step,
        grib_path,
    ):
        result = (
            self._empty_result()
        )

        for product_name in (
            CATEGORICAL_PRODUCTS
        ):

            if (
                product_name
                not in PRODUCTS
            ):

                continue

            product = PRODUCTS[
                product_name
            ]

            if (
                self.model
                not in product
            ):

                continue

            try:

                data = load_product(
                    grib_path,
                    model=self.model,
                    product_name=product_name,
                )

            except Exception as error:

                print(
                    f"{product_name} "
                    f"f{step:03d}: "
                    f"skipped — "
                    f"{error}"
                )

                continue

            product_result = (
                render_regions(
                    model=self.model,
                    product_name=product_name,
                    step=step,
                    data=data,
                    output_dir=self.output_dir,
                    regions=self.regions,
                    overwrite=self.overwrite,
                )
            )

            self._add_result(
                result,
                product_result,
            )

        return result


    # ========================================================
    # PROCESS ONE FORECAST HOUR
    # ========================================================

    def process_hour(
        self,
        *,
        step,
        grib_path,
    ):
        print()
        print(
            f"SEQUENCE PROCESSING "
            f"f{int(step):03d}"
        )

        total = (
            self._empty_result()
        )

        precip_result = (
            self._process_total_precip(
                step=int(
                    step
                ),
                grib_path=grib_path,
            )
        )

        self._add_result(
            total,
            precip_result,
        )

        accumulation_result = (
            self._process_other_accumulations(
                step=int(
                    step
                ),
                grib_path=grib_path,
            )
        )

        self._add_result(
            total,
            accumulation_result,
        )

        categorical_result = (
            self._process_categorical(
                step=int(
                    step
                ),
                grib_path=grib_path,
            )
        )

        self._add_result(
            total,
            categorical_result,
        )

        print(
            f"SEQUENCE f{int(step):03d}: "
            f"created={total['created']}, "
            f"skipped={total['skipped']}, "
            f"failed={total['failed']}"
        )

        return total


    # ========================================================
    # FINISH
    # ========================================================

    def finish(
        self,
    ):
        self.precip_history.clear()

        self.precip_running_total = None


# ============================================================
# BACKWARD-COMPATIBLE COMPLETE-CYCLE RUNNER
# ============================================================

def run_sequence_products(
    *,
    model,
    forecast_files,
    output_dir,
    regions=None,
    overwrite=False,
):
    """
    Existing complete-cycle API.

    Internally this now uses the streaming processor rather than
    building an entire cumulative series in memory.
    """

    processor = (
        SequenceStreamProcessor(
            model=model,
            output_dir=output_dir,
            regions=regions,
            overwrite=overwrite,
        )
    )

    total = {
        "created": 0,
        "skipped": 0,
        "failed": 0,
    }

    try:

        for step, grib_path in sorted(
            forecast_files,
            key=lambda item: item[
                0
            ],
        ):

            result = (
                processor.process_hour(
                    step=step,
                    grib_path=grib_path,
                )
            )

            total[
                "created"
            ] += result[
                "created"
            ]

            total[
                "skipped"
            ] += result[
                "skipped"
            ]

            total[
                "failed"
            ] += result[
                "failed"
            ]

    finally:

        processor.finish()

    return total