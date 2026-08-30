from __future__ import annotations

import os

from datetime import (
    datetime,
    timezone,
)

from shared.production_cycle import (
    publish_cycle_started,
    publish_cycle_completed,
)


MODEL = "weathernext2"


def resolve_wn2_cycle_id():
    configured = (
        os.environ.get(
            "MODEL_CYCLE_ID"
        )
    )

    if configured:
        return (
            configured
            .strip()
        )

    now = datetime.now(
        timezone.utc
    )

    cycle_hour = (
        now.hour
        //
        6
        *
        6
    )

    return (
        f"{now:%Y%m%d}_"
        f"{cycle_hour:02d}z"
    )


def run_wn2_atmospheric_production():
    """
    Stable production entrypoint for Atmospheric WeatherNext 2.

    The Zarr atmospheric processor plugs into this function.
    Publication/archive behavior is already standardized.
    """

    cycle_id = (
        resolve_wn2_cycle_id()
    )

    print(
        "=" * 70
    )

    print(
        "MASSACHUSETTSWX "
        "WEATHERNEXT 2 "
        "ATMOSPHERIC PIPELINE"
    )

    print(
        f"Cycle: {cycle_id}"
    )

    print(
        "=" * 70
    )

    publish_cycle_started(
        model=MODEL,
        cycle_id=cycle_id,
        extra={
            "pipeline": (
                "atmospheric"
            ),
            "source_format": (
                "zarr"
            ),
        },
    )

    # --------------------------------------------------------
    # Atmospheric processor integration point.
    #
    # We intentionally fail clearly instead of publishing
    # READY.json before the actual WN2 atmospheric renderer is
    # attached.
    # --------------------------------------------------------

    try:

        from wn2.atmospheric import (
            run_atmospheric_cycle,
        )

    except ImportError as error:

        raise RuntimeError(
            "WeatherNext 2 atmospheric processor "
            "has not yet been attached to the "
            "production entrypoint."
        ) from error

    result = (
        run_atmospheric_cycle(
            cycle_id=cycle_id,
        )
    )

    summary = {
        "pipeline": (
            "atmospheric"
        ),
        "source_format": (
            "zarr"
        ),
    }

    if isinstance(
        result,
        dict,
    ):
        summary.update(
            result
        )

    publish_cycle_completed(
        model=MODEL,
        cycle_id=cycle_id,
        payload=summary,
    )

    return result
