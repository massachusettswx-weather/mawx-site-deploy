from __future__ import annotations


# ============================================================
# MASSACHUSETTSWX CYCLONE PRODUCT REGISTRY
#
# Shared by:
#   FNV3
#   FNV3-L
#
# Keep product IDs stable. The site will eventually consume
# these IDs directly.
# ============================================================

CYCLONE_PRODUCTS = {

    "track": {
        "name": "Spaghetti Track",
        "category": "track",
        "frame_based": True,
        "fnv3": True,
        "fnv3_large": True,
    },

    "intensity": {
        "name": "Intensity",
        "category": "track",
        "frame_based": True,
        "fnv3": True,
        "fnv3_large": True,
    },

    "instantaneous_track": {
        "name": "Instantaneous Track",
        "category": "track",
        "frame_based": True,
        "fnv3": True,
        "fnv3_large": True,
    },

    "instantaneous_intensity": {
        "name": "Instantaneous Intensity",
        "category": "track",
        "frame_based": True,
        "fnv3": True,
        "fnv3_large": True,
    },

    "mean_track": {
        "name": "Ensemble Mean Track",
        "category": "track",
        "frame_based": True,
        "fnv3": True,
        "fnv3_large": True,
    },

    "cyclogenesis_probability": {
        "name": "Cyclogenesis Probability",
        "category": "probability",
        "frame_based": True,
        "units": "%",
        "fnv3": True,
        "fnv3_large": True,
    },

    "wind_probability_34kt": {
        "name": "34 kt Wind Probability",
        "category": "probability",
        "frame_based": True,
        "threshold_kt": 34,
        "units": "%",
        "fnv3": True,
        "fnv3_large": True,
    },

    "wind_probability_50kt": {
        "name": "50 kt Wind Probability",
        "category": "probability",
        "frame_based": True,
        "threshold_kt": 50,
        "units": "%",
        "fnv3": True,
        "fnv3_large": True,
    },

    "wind_probability_64kt": {
        "name": "64 kt Hurricane Wind Probability",
        "category": "probability",
        "frame_based": True,
        "threshold_kt": 64,
        "units": "%",
        "fnv3": True,
        "fnv3_large": True,
    },
}


TRACK_PRODUCTS = tuple(
    name
    for name, config in CYCLONE_PRODUCTS.items()
    if config["category"] == "track"
)


PROBABILITY_PRODUCTS = tuple(
    name
    for name, config in CYCLONE_PRODUCTS.items()
    if config["category"] == "probability"
)


def get_cyclone_products(model):
    model = str(model).strip().lower()

    if model not in {
        "fnv3",
        "fnv3_large",
    }:
        raise ValueError(
            f"Unsupported cyclone model: {model}"
        )

    return tuple(
        name
        for name, config in CYCLONE_PRODUCTS.items()
        if config.get(model, False)
    )


def get_cyclone_product(name):
    return CYCLONE_PRODUCTS[
        str(name).strip().lower()
    ]


def get_wind_probability_threshold(name):
    config = get_cyclone_product(name)

    return config.get(
        "threshold_kt"
    )
# MASSWX EXTENDED CYCLONE PRODUCT CONTRACT
# Shared planner metadata only; renderers remain model-specific.

CYCLONE_PRODUCTS['intensity_distribution'] = {
    'name': 'Intensity Distribution',
    'units': 'kt',
}

CYCLONE_PRODUCTS['mslp_spaghetti'] = {
    'name': 'MSLP + Intensity Spaghetti',
    'units': 'hPa',
}



# ============================================================
# MASSWX COMPLETE FNV3 PRODUCT CONTRACT
# ============================================================
# Shared validation metadata only.
# Rendering remains model-specific.

CYCLONE_PRODUCTS['mslp_probability'] = {
    'name': 'MSLP Probability',
    'units': '%',
}

CYCLONE_PRODUCTS['track_anomaly'] = {
    'name': 'Track Anomaly',
    'units': None,
}

