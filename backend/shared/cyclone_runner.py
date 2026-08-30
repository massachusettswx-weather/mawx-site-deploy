from __future__ import annotations

from shared.cyclone_operational import (
    run_operational_cyclone_cycle,
)

from shared.cyclone_products import (
    get_cyclone_products,
)

from shared.cyclone_regions import (
    DEFAULT_CYCLONE_REGIONS,
)

from shared.cyclone_renderer import (
    operational_products,
    render_cyclone_frame,
)


MEMBER_COUNTS = {
    "fnv3": 51,
    "fnv3_large": 1000,
}


def _load_model_renderers(
    model,
):
    if model == "fnv3":

        import fnv3_cyclone.renderers

    elif model == "fnv3_large":

        import fnv3_large_cyclone.renderers

    else:

        raise ValueError(
            f"Unsupported cyclone model: "
            f"{model}"
        )


def run_cyclone_model(
    *,
    model,
    date,
    hour,
    forecast_hours,
    products=None,
    regions=None,
    resume=True,
):
    model = (
        str(model)
        .strip()
        .lower()
    )

    _load_model_renderers(
        model
    )

    if products is None:
        products = operational_products(
            model
        )

    if regions is None:
        regions = (
            DEFAULT_CYCLONE_REGIONS
        )

    return run_operational_cyclone_cycle(
        model=model,
        date=date,
        hour=hour,
        forecast_hours=forecast_hours,
        renderer=render_cyclone_frame,
        products=products,
        regions=regions,
        member_count=(
            MEMBER_COUNTS[
                model
            ]
        ),
        resume=resume,
    )
