from __future__ import annotations
from fnv3_cyclone.download.forecast_client import FNV3ForecastClient

import os

from datetime import (
    datetime,
    timezone,
)

from shared.production_cycle import (
    publish_cycle_started,
    publish_cycle_completed,
)


MODEL = "fnv3"


def resolve_cycle_id():
    """
    Return newest FNV3 cycle confirmed to exist
    on the Weather Lab upstream feed.
    """
    client = FNV3ForecastClient()

    cycle = client.latest_cycle()

    print(
        "Resolved available FNV3 cycle:",
        cycle,
    )

    return cycle


def run_fnv3_production():
    """
    Run FNV3 directly through the operational frame engine.

    All ensemble members are retained. The former legacy
    rendering pass is removed so the same cyclone guidance
    is not plotted twice before f000-f360 processing.
    """

    cycle_id = resolve_cycle_id()

    os.environ[
        "MODEL_CYCLE_ID"
    ] = cycle_id

    print("=" * 70)
    print(
        "MASSACHUSETTSWX FNV3 "
        "PRODUCTION PIPELINE"
    )
    print(
        f"Cycle: {cycle_id}"
    )
    print(
        "Mode: operational-only"
    )
    print("=" * 70)

    publish_cycle_started(
        model=MODEL,
        cycle_id=cycle_id,
        extra={
            "pipeline": "cyclone",
            "mode": "operational-only",
        },
    )

    # --------------------------------------------------------
    # DOWNLOAD SOURCE DATA ONCE
    # --------------------------------------------------------
    #
    # The operational renderer consumes files from output/raw.
    # Legacy rendering was intentionally removed, but source
    # acquisition must still occur before the frame engine.
    #
    from .run import (
        run_fnv3_cyclone_cycle,
    )

    print(
        "Preparing FNV3 source data..."
    )

    run_fnv3_cyclone_cycle(
        cycle=cycle_id,
        overwrite=False,
    )

    print(
        "FNV3 source data ready."
    )

    from .operational import (
        run_fnv3_operational,
    )

    operational_result = (
        run_fnv3_operational(
            forecast_hours=list(
                range(
                    0,
                    361,
                    6,
                )
            ),
            resume=True,
        )
    )

    summary = {
        "pipeline": "cyclone",
        "mode": "operational-only",
        "forecast_hour_start": 0,
        "forecast_hour_end": 360,
        "forecast_hour_step": 6,
        "frame_count": 61,
        "all_members": True,
        "ensemble_size": 51,
    }

    publish_cycle_completed(
        model=MODEL,
        cycle_id=cycle_id,
        payload=summary,
    )

    return {
        "operational":
            operational_result,
    }

