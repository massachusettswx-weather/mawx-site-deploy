from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from shared.cyclone_output import (
    normalize_cyclone_model,
)

from shared.cyclone_products import (
    get_cyclone_products,
)

from shared.cyclone_regions import (
    DEFAULT_CYCLONE_REGIONS,
)


def build_cyclone_manifest(
    *,
    model,
    date,
    hour,
    forecast_hours,
    products=None,
    regions=None,
    member_count=None,
):
    model = normalize_cyclone_model(
        model
    )

    if products is None:
        products = get_cyclone_products(
            model
        )

    if regions is None:
        regions = DEFAULT_CYCLONE_REGIONS

    forecast_hours = sorted(
        {
            int(hour_value)
            for hour_value
            in forecast_hours
        }
    )

    return {
        "schema_version": 1,

        "model": model,

        "cycle": {
            "date": str(date),
            "hour": int(hour),
            "id": (
                f"{date}_"
                f"{int(hour):02d}z"
            ),
        },

        "member_count": (
            int(member_count)
            if member_count is not None
            else None
        ),

        "products": list(
            products
        ),

        "regions": list(
            regions
        ),

        # Directly usable by the future site slider.
        "forecast_hours": (
            forecast_hours
        ),

        "first_forecast_hour": (
            forecast_hours[0]
            if forecast_hours
            else None
        ),

        "last_forecast_hour": (
            forecast_hours[-1]
            if forecast_hours
            else None
        ),

        "frame_count": len(
            forecast_hours
        ),

        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
    }
