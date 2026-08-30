from __future__ import annotations

from fnv3_large_cyclone.production import (
    resolve_cycle_id,
)

from shared.cyclone_runner import (
    run_cyclone_model,
)


def _split_cycle(
    cycle,
):
    value = (
        str(cycle)
        .lower()
        .replace("_", "")
        .replace("z", "")
    )

    if len(value) < 10:
        raise ValueError(
            f"Invalid FNV3-L cycle: {cycle}"
        )

    return (
        value[:8],
        int(value[8:10]),
    )


def run_fnv3_large_operational(
    *,
    forecast_hours=None,
    products=None,
    regions=None,
    resume=True,
):
    cycle = resolve_cycle_id()

    date, hour = _split_cycle(
        cycle
    )

    if forecast_hours is None:
        forecast_hours = list(range(0, 361, 6))

    return run_cyclone_model(
        model="fnv3_large",
        date=date,
        hour=hour,
        forecast_hours=(
            forecast_hours
        ),
        products=products,
        regions=regions,
        resume=resume,
    )
