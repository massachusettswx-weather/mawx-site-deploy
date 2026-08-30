from __future__ import annotations

from shared.regions import (
    REGIONS,
)


# ============================================================
# CYCLONE-ONLY REGIONS
#
# Reuse the normal MassachusettsWx region registry wherever
# possible. Only define tropical/cyclone regions that do not
# already exist in shared.regions.
# ============================================================

CYCLONE_ONLY_REGIONS = {

    "gulf_mexico": {
        "name": "Gulf of Mexico",
        "extent": (-100, -80, 15, 32),
    },

    "caribbean": {
        "name": "Caribbean",
        "extent": (-90, -58, 8, 25),
    },

    "arabian_sea": {
        "name": "Arabian Sea",
        "extent": (42, 78, 0, 30),
    },

    "bay_bengal": {
        "name": "Bay of Bengal",
        "extent": (77, 105, 0, 30),
    },

    "southwest_indian": {
        "name": "Southwest Indian Ocean",
        "extent": (20, 80, -40, 5),
    },

    "southeast_indian": {
        "name": "Southeast Indian Ocean",
        "extent": (75, 140, -40, 5),
    },

    "southwest_pacific": {
        "name": "Southwest Pacific",
        "extent": (135, 180, -40, 5),
    },

    "southeast_pacific": {
        "name": "Southeast Pacific",
        "extent": (-180, -70, -40, 5),
    },
}


# ============================================================
# NORMALIZE EXISTING SHARED REGION FORMAT
# ============================================================

def _normalize_region(
    name,
    config,
):
    if isinstance(
        config,
        dict,
    ):

        extent = (
            config.get("extent")
            or
            config.get("bbox")
            or
            config.get("bounds")
        )

        display_name = (
            config.get("name")
            or
            config.get("label")
            or
            name.replace(
                "_",
                " ",
            ).title()
        )

    else:

        extent = config

        display_name = (
            name.replace(
                "_",
                " ",
            ).title()
        )

    return {
        "name": display_name,
        "extent": extent,
    }


# ============================================================
# BUILD CYCLONE REGION CATALOG
#
# shared.regions wins when a region already exists.
# ============================================================

CYCLONE_REGIONS = {
    name: (
        _normalize_region(
            name,
            config,
        )
    )
    for name, config
    in REGIONS.items()
}


for (
    name,
    config,
) in CYCLONE_ONLY_REGIONS.items():

    CYCLONE_REGIONS.setdefault(
        name,
        config,
    )


# ============================================================
# FNV3 / FNV3-L REGION ORDER
#
# Prefer existing operational regions first.
# ============================================================

PREFERRED_CYCLONE_REGION_ORDER = [

    # Atlantic
    "atlantic",
    "tropical_atlantic",
    "western_atlantic",
    "southwest_atlantic",
    "central_atlantic",
    "eastern_atlantic",
    "gulf_mexico",
    "caribbean",

    # Pacific
    "north_pacific",
    "east_pacific",
    "eastern_pacific",
    "central_pacific",
    "west_pacific",
    "western_pacific",
    "south_pacific",
    "southwest_pacific",
    "southeast_pacific",

    # Indian
    "north_indian",
    "indian_ocean",
    "arabian_sea",
    "bay_bengal",
    "south_indian",
    "southwest_indian",
    "southeast_indian",
]


DEFAULT_CYCLONE_REGIONS = []

seen = set()

for name in (
    PREFERRED_CYCLONE_REGION_ORDER
):

    if (
        name
        in CYCLONE_REGIONS
        and
        name
        not in seen
    ):

        DEFAULT_CYCLONE_REGIONS.append(
            name
        )

        seen.add(
            name
        )


def get_cyclone_region(
    name,
):
    name = (
        str(name)
        .strip()
        .lower()
    )

    return CYCLONE_REGIONS[
        name
    ]
