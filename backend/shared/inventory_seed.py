"""
MassachusettsWx operational inventory seed.

Purpose
-------
Build an in-memory completeness inventory ONCE when an
operational model cycle starts or resumes.

After startup, the live pipeline should update its in-memory
state as new frames are successfully published rather than
repeatedly performing expensive remote inventory scans.

Inventory key format:

    (
        product,
        region,
        forecast_hour,
    )

This module is deliberately model-agnostic so it can be used by
GFS, IFS, AIFS, FNV3, FNV3-L, WeatherNext, and future models.
"""

from pathlib import Path


def inventory_key(
    product,
    region,
    forecast_hour,
):
    """
    Return the canonical MassachusettsWx completeness key.
    """

    return (
        str(product),
        str(region),
        int(forecast_hour),
    )


def seed_local_inventory(
    *,
    cycle_output_dir,
    products,
    regions,
    forecast_hours,
):
    """
    Seed completeness from files already present in the local
    cycle output directory.

    This is intentionally conservative:

    - expected filename must exist
    - file must be non-empty
    - unknown files are ignored

    Returns a set of canonical inventory keys.
    """

    cycle_output_dir = Path(
        cycle_output_dir
    )

    products = list(products)
    regions = list(regions)

    wanted_hours = {
        int(hour)
        for hour in forecast_hours
    }

    inventory = set()

    if not cycle_output_dir.exists():
        return inventory

    # --------------------------------------------------------
    # We do not assume one rigid directory hierarchy here.
    #
    # Operational pipelines have changed layouts over time.
    # Scan PNGs once and infer product / region / forecast hour
    # from their path and filename.
    # --------------------------------------------------------

    for path in cycle_output_dir.rglob(
        "*.png"
    ):
        try:

            if (
                not path.is_file()
                or
                path.stat().st_size <= 0
            ):
                continue

            path_text = str(
                path
            ).lower()

            filename = (
                path.name.lower()
            )

            matched_product = None

            for product in products:

                product_text = str(
                    product
                ).lower()

                if (
                    product_text
                    in
                    path_text
                ):
                    matched_product = (
                        product
                    )
                    break

            if matched_product is None:
                continue

            matched_region = None

            for region in regions:

                region_text = str(
                    region
                ).lower()

                if (
                    region_text
                    in
                    path_text
                ):
                    matched_region = (
                        region
                    )
                    break

            if matched_region is None:
                continue

            # ------------------------------------------------
            # Forecast-hour filenames normally contain fNNN.
            # Keep this parser deliberately strict to avoid
            # accidentally marking the wrong frame complete.
            # ------------------------------------------------

            marker_position = (
                filename.rfind(
                    "_f"
                )
            )

            if marker_position < 0:

                marker_position = (
                    filename.rfind(
                        "-f"
                    )
                )

            if marker_position < 0:

                marker_position = (
                    filename.find(
                        "f"
                    )
                )

            if marker_position < 0:
                continue

            digits = []

            for char in filename[
                marker_position + 2:
            ]:

                if char.isdigit():

                    digits.append(
                        char
                    )

                elif digits:

                    break

            if not digits:
                continue

            forecast_hour = int(
                "".join(
                    digits
                )
            )

            if (
                forecast_hour
                not in
                wanted_hours
            ):
                continue

            inventory.add(
                inventory_key(
                    matched_product,
                    matched_region,
                    forecast_hour,
                )
            )

        except OSError:

            # A disappearing temporary/local file should never
            # kill an operational cycle.
            continue

    return inventory


def mark_complete(
    inventory,
    *,
    product,
    region,
    forecast_hour,
):
    """
    Mark one successfully completed frame in memory.
    """

    inventory.add(
        inventory_key(
            product,
            region,
            forecast_hour,
        )
    )


def is_complete(
    inventory,
    *,
    product,
    region,
    forecast_hour,
):
    """
    Return True when a frame is already known complete.
    """

    return (
        inventory_key(
            product,
            region,
            forecast_hour,
        )
        in
        inventory
    )


def build_work_plan(
    *,
    inventory,
    products,
    regions,
    forecast_hour,
):
    """
    Build the selective runner work plan for ONE forecast hour.

    Output:

        {
            "conus": {"mslp", "pwat"},
            "europe": {"pwat"},
        }

    Only missing product/region combinations are included.
    """

    plan = {}

    for region in regions:

        missing = set()

        for product in products:

            if not is_complete(
                inventory,
                product=product,
                region=region,
                forecast_hour=(
                    forecast_hour
                ),
            ):

                missing.add(
                    product
                )

        if missing:

            plan[
                region
            ] = missing

    return plan


def expected_count(
    *,
    products,
    regions,
    forecast_hours,
):
    """
    Expected total number of product/region/hour frames.
    """

    return (
        len(
            list(products)
        )
        *
        len(
            list(regions)
        )
        *
        len(
            list(forecast_hours)
        )
    )
