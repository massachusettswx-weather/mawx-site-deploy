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


MODEL = "fnv3_large"


def resolve_cycle_id():
    """
    Resolve the newest confirmed Weather Lab
    cyclone cycle instead of guessing from UTC.
    """
    client = FNV3ForecastClient()

    cycle = client.latest_cycle()

    print(
        "Resolved available FNV3-L cycle:",
        cycle,
    )

    return cycle


def run_fnv3_large_production():
    """
    Run FNV3-L directly through the operational frame engine.

    The previous production path first rendered the complete
    legacy f360 product set and then started the operational
    f000-f360 engine. That duplicated expensive 1000-member
    plotting.

    The operational engine is now authoritative and supplies:

      * all 1000 ensemble members
      * f000-f360 / 6-hourly frames
      * cyclone regional sectors
      * ensemble-mean guidance
      * probability products
      * streaming publication
      * resume / skip-existing behavior
      * progress/current/manifest publication
    """

    cycle_id = resolve_cycle_id()

    os.environ[
        "MODEL_CYCLE_ID"
    ] = cycle_id

    print(
        "=" * 70
    )

    print(
        "MASSACHUSETTSWX FNV3-L "
        "PRODUCTION PIPELINE"
    )

    print(
        f"Cycle: {cycle_id}"
    )

    print(
        "Mode: operational-only"
    )

    print(
        "=" * 70
    )


    publish_cycle_started(
        model=MODEL,
        cycle_id=cycle_id,
        extra={
            "pipeline": "cyclone",
            "mode": "operational-only",
        },
    )


    # Delayed import prevents production/operational
    # initialization cycles.
    # ========================================================
    # SOURCE ACQUISITION
    # ========================================================
    #
    # Download native Weather Lab data ONCE in the parent
    # process before the operational frame workers start.
    #
    from pathlib import Path

    from .download.fnv3_large_downloader import (
        download_fnv3_large_cycle,
    )

    raw_dir = (
        Path(__file__).resolve().parent
        / "output"
        / "raw"
        / str(cycle_id)
    )

    print(
        "Preparing FNV3-L source data..."
    )

    source_bundle = (
        download_fnv3_large_cycle(
            cycle=cycle_id,
            output_dir=raw_dir,
            overwrite=False,
        )
    )

    ensemble_path = (
        source_bundle.get(
            "ensemble_path"
        )
    )

    mean_path = (
        source_bundle.get(
            "mean_path"
        )
    )

    probability_path = (
        source_bundle.get(
            "probability_path"
        )
    )

    if (
        ensemble_path is None
        or not Path(
            ensemble_path
        ).exists()
    ):
        raise RuntimeError(
            "FNV3-L ensemble source "
            "was not prepared."
        )

    if (
        mean_path is None
        or not Path(
            mean_path
        ).exists()
    ):
        raise RuntimeError(
            "FNV3-L mean source "
            "was not prepared."
        )

    if (
        probability_path is None
        or not Path(
            probability_path
        ).exists()
    ):
        raise RuntimeError(
            "FNV3-L probability source "
            "was not prepared."
        )

    print(
        "FNV3-L source data ready."
    )

    from .operational import (
        run_fnv3_large_operational,
    )


    operational_result = (
        run_fnv3_large_operational(
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
        "ensemble_size": 1000,
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

