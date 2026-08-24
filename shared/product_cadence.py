from __future__ import annotations


# ============================================================
# PRODUCT CADENCE CONFIGURATION
# ============================================================

MODEL_PRODUCT_CADENCE = {

    "gfs": {

        "fine": {
            "t2m",
            "td2m",

            "wind10",
            "wind100",

            "mslp",
            "mslp_wind10",

            "cloud_total",

            "sbcape",
            "mlcape",
            "mucape",

            "sbcin",
            "mlcin",
            "mucin",

            "gust10",
            "precip_rate",
        },

        "three_hourly": {
            "h5_vort",

            "jet250",
            "jet300",

            "omega700",

            "t850_hgt",
            "t925_hgt",

            "thickness_1000_500",

            "wind500_hgt",
            "wind700_hgt",
            "wind850_hgt",
            "wind925_hgt",
        },
    },

    "ifs": {

        "fine": {
            "t2m",
            "td2m",

            "wind10",
            "wind100",

            "mslp",
            "mslp_wind10",

            "cloud_total",

            "mucape",
            "gust10",
            "precip_rate",
        },

        "three_hourly": {
            "h5_vort",

            "jet250",
            "jet300",

            "omega700",

            "t850_hgt",
            "t925_hgt",

            "thickness_1000_500",

            "wind500_hgt",
            "wind700_hgt",
            "wind850_hgt",
            "wind925_hgt",
        },
    },
}


# ============================================================
# PRODUCT CADENCE DECISION
# ============================================================

def should_render_product(
    *,
    model,
    product,
    forecast_hour,
):
    """
    Return True when a product should be rendered at the supplied
    forecast hour.

    IMPORTANT:

    This does NOT alter a model's forecast-hour schedule.

    It only decides whether a specific product is rendered on a
    forecast hour that already belongs to that model's configured
    schedule.
    """

    model = (
        str(model)
        .lower()
        .strip()
    )

    product = (
        str(product)
        .lower()
        .strip()
    )

    forecast_hour = int(
        forecast_hour
    )

    cadence = (
        MODEL_PRODUCT_CADENCE.get(
            model
        )
    )

    # Models without a product-cadence configuration render every
    # configured product on every available forecast hour.
    if cadence is None:

        return True

    fine_products = (
        cadence.get(
            "fine",
            set(),
        )
    )

    three_hourly_products = (
        cadence.get(
            "three_hourly",
            set(),
        )
    )

    # Fine-cadence products follow the model's native frame schedule.
    if product in fine_products:

        return True

    # Synoptic / upper-air products use three-hour cadence while
    # hourly frames exist.
    if product in three_hourly_products:

        return (
            forecast_hour
            %
            3
            ==
            0
        )

    # Safe default:
    # New products render until explicitly classified.
    return True


# ============================================================
# FILTER PRODUCT LIST
# ============================================================

def products_for_forecast_hour(
    *,
    model,
    products,
    forecast_hour,
):
    """
    Return the subset of configured products that should render at
    this forecast hour.

    Original product ordering is preserved.
    """

    return [
        product
        for product in products
        if should_render_product(
            model=model,
            product=product,
            forecast_hour=(
                forecast_hour
            ),
        )
    ]


# ============================================================
# DISPLAY / DEBUG HELPER
# ============================================================

def describe_product_cadence(
    *,
    model,
    products,
    forecast_hour,
):
    """
    Return a concise cadence summary for production logging.
    """

    selected = (
        products_for_forecast_hour(
            model=model,
            products=products,
            forecast_hour=(
                forecast_hour
            ),
        )
    )

    return {
        "forecast_hour": int(
            forecast_hour
        ),

        "configured_products": len(
            products
        ),

        "render_products": len(
            selected
        ),

        "skipped_by_cadence": (
            len(
                products
            )
            -
            len(
                selected
            )
        ),

        "products": selected,
    }
