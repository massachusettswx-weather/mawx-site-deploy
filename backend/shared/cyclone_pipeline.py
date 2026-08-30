from __future__ import annotations

from dataclasses import (
    asdict,
)
from pathlib import Path

from shared.cyclone_adapter import (
    CycloneFrameRequest,
    discover_cyclone_inputs,
    resolve_product_input,
)

from shared.cyclone_output import (
    cyclone_local_path,
)

from shared.cyclone_products import (
    get_cyclone_products,
)

from shared.cyclone_regions import (
    DEFAULT_CYCLONE_REGIONS,
)


# ============================================================
# PRODUCTION PLAN
# ============================================================

def build_cyclone_frame_plan(
    *,
    model,
    date,
    hour,
    forecast_hours,
    products=None,
    regions=None,
):
    if products is None:
        products = get_cyclone_products(
            model
        )

    if regions is None:
        regions = (
            DEFAULT_CYCLONE_REGIONS
        )

    plan = []

    for forecast_hour in (
        forecast_hours
    ):

        for product in products:

            for region in regions:

                plan.append(
                    CycloneFrameRequest(
                        model=model,
                        date=date,
                        hour=hour,
                        forecast_hour=(
                            forecast_hour
                        ),
                        product=product,
                        region=region,
                    )
                )

    return plan


# ============================================================
# INPUT RESOLUTION
# ============================================================

def resolve_cyclone_frame(
    request,
):
    bundle = (
        discover_cyclone_inputs(
            request.model,
            date=request.date,
            hour=request.hour,
        )
    )

    source = (
        resolve_product_input(
            bundle,
            request.product,
        )
    )

    return {
        "request": request,
        "source": source,
        "bundle": bundle,
    }


# ============================================================
# OUTPUT TARGET
# ============================================================

def get_frame_output_path(
    request,
    root="/tmp/massachusettswx",
):
    return cyclone_local_path(
        root=root,
        model=request.model,
        date=request.date,
        hour=request.hour,
        product=request.product,
        region=request.region,
        forecast_hour=(
            request.forecast_hour
        ),
    )


# ============================================================
# SERIALIZABLE DEBUG/STATUS RECORD
# ============================================================

def frame_record(
    request,
):
    resolved = resolve_cyclone_frame(
        request
    )

    output = get_frame_output_path(
        request
    )

    return {
        **asdict(
            request
        ),

        "source": str(
            resolved[
                "source"
            ]
        ),

        "output": str(
            output
        ),
    }
