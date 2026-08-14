from shared.products import (
    PRODUCTS,
    OPERATIONAL_PRODUCTS,
)


# ============================================================
# GFS .IDX VARIABLE NAMES
# ============================================================

GFS_IDX_NAMES = {
    "gh": "HGT",
    "t": "TMP",
    "r": "RH",
    "w": "VVEL",

    "u": "UGRD",
    "v": "VGRD",

    "10u": "UGRD",
    "10v": "VGRD",

    "100u": "UGRD",
    "100v": "VGRD",

    "2t": "TMP",
    "2d": "DPT",

    "gust": "GUST",

    "prmsl": "PRMSL",

    "pwat": "PWAT",

    "cape": "CAPE",
    "cin": "CIN",

    "tcc": "TCDC",

    # GFS precipitation
    "tp": "APCP",

    # GFS categorical precip type
    "crain": "CRAIN",
    "csnow": "CSNOW",
    "cfrzr": "CFRZR",
    "cicep": "CICEP",

    # Snowpack water equivalent
    "weasd": "WEASD",
}


# ============================================================
# ECMWF PARAMETERS
# ============================================================

ECMWF_PARAMS = {
    "gh": "gh",
    "z": "z",

    "t": "t",
    "r": "r",
    "q": "q",

    "u": "u",
    "v": "v",

    "w": "w",
    "vo": "vo",

    "msl": "msl",

    "10u": "10u",
    "10v": "10v",

    "100u": "100u",
    "100v": "100v",

    "10fg": "10fg",

    "2t": "2t",
    "2d": "2d",

    "tcwv": "tcwv",
    "tcw": "tcw",

    "mucape": "mucape",

    "tcc": "tcc",

    "tprate": "tprate",
    "ptype": "ptype",
    "tp": "tp",

    "sf": "sf",
    "sd": "sd",
}


# ============================================================
# FIELD COLLECTION
# ============================================================

def collect_model_fields(
    model,
    products=None,
):
    if products is None:
        products = OPERATIONAL_PRODUCTS

    fields = []
    seen = set()

    for product_name in products:

        if product_name not in PRODUCTS:
            continue

        product = PRODUCTS[
            product_name
        ]

        if model not in product:
            continue

        model_config = product[
            model
        ]

        # Window products like qpf6 point to total_precip
        # and contain no raw field mapping themselves.
        if "fields" not in model_config:
            continue

        for logical_name, config in (
            model_config[
                "fields"
            ].items()
        ):
            short_name = config[
                "short_name"
            ]

            level = config.get(
                "level"
            )

            type_of_level = config.get(
                "type_of_level"
            )

            idx_level_text = config.get(
                "idx_level_text"
            )

            identity = (
                short_name,
                level,
                type_of_level,
                idx_level_text,
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            fields.append(
                {
                    "logical_name": logical_name,
                    "short_name": short_name,
                    "level": level,
                    "type_of_level": type_of_level,
                    "idx_level_text": idx_level_text,
                }
            )

    return fields


# ============================================================
# PRESSURE / SURFACE SPLIT
# ============================================================

def pressure_level_fields(
    model,
    products=None,
):
    return [
        field
        for field
        in collect_model_fields(
            model,
            products,
        )
        if field[
            "type_of_level"
        ] == "isobaricInhPa"
    ]


def surface_fields(
    model,
    products=None,
):
    return [
        field
        for field
        in collect_model_fields(
            model,
            products,
        )
        if field[
            "type_of_level"
        ] != "isobaricInhPa"
    ]


# ============================================================
# ECMWF REQUEST PLANS
# ============================================================

def build_ecmwf_pressure_plan(
    model,
    products=None,
):
    fields = pressure_level_fields(
        model,
        products,
    )

    parameters = set()
    levels = set()

    for field in fields:
        short_name = field[
            "short_name"
        ]

        parameter = ECMWF_PARAMS.get(
            short_name
        )

        if parameter is None:
            continue

        parameters.add(
            parameter
        )

        if field[
            "level"
        ] is not None:
            levels.add(
                int(
                    field[
                        "level"
                    ]
                )
            )

    return {
        "params": sorted(
            parameters
        ),
        "levels": sorted(
            levels,
            reverse=True,
        ),
    }


def build_ecmwf_surface_plan(
    model,
    products=None,
):
    fields = surface_fields(
        model,
        products,
    )

    parameters = set()

    for field in fields:
        short_name = field[
            "short_name"
        ]

        parameter = ECMWF_PARAMS.get(
            short_name
        )

        if parameter is None:
            continue

        parameters.add(
            parameter
        )

    return {
        "params": sorted(
            parameters
        ),
    }


# ============================================================
# GFS LEVEL TEXT
# ============================================================

def get_gfs_level_text(
    field,
):
    if field.get(
        "idx_level_text"
    ):
        return field[
            "idx_level_text"
        ]

    level = field[
        "level"
    ]

    type_of_level = field[
        "type_of_level"
    ]

    short_name = field[
        "short_name"
    ]

    if (
        type_of_level
        == "isobaricInhPa"
    ):
        return (
            f"{int(level)} mb"
        )

    if (
        type_of_level
        == "heightAboveGround"
    ):
        return (
            f"{int(level)} m "
            f"above ground"
        )

    if (
        type_of_level
        == "meanSea"
    ):
        return (
            "mean sea level"
        )

    if short_name == "pwat":
        return (
            "entire atmosphere"
        )

    if (
        type_of_level
        == "surface"
    ):
        return "surface"

    return None


# ============================================================
# GFS MATCHERS
# ============================================================

def gfs_idx_matchers(
    products=None,
):
    fields = collect_model_fields(
        "gfs",
        products,
    )

    matchers = []

    for field in fields:
        short_name = field[
            "short_name"
        ]

        idx_name = GFS_IDX_NAMES.get(
            short_name
        )

        if idx_name is None:
            continue

        matchers.append(
            {
                "idx_name": idx_name,
                "level_text": (
                    get_gfs_level_text(
                        field
                    )
                ),
                "short_name": short_name,
                "level": field[
                    "level"
                ],
                "type_of_level": field[
                    "type_of_level"
                ],
            }
        )

    return matchers


# ============================================================
# MODEL PRODUCT FILTER
# ============================================================

def products_for_model(
    model,
    products=None,
):
    if products is None:
        products = OPERATIONAL_PRODUCTS

    available = []

    for product_name in products:
        if product_name not in PRODUCTS:
            continue

        if model in PRODUCTS[
            product_name
        ]:
            available.append(
                product_name
            )

    return available


# ============================================================
# DEBUG DISPLAY
# ============================================================

def print_download_plan(
    model,
    products=None,
):
    available_products = (
        products_for_model(
            model,
            products,
        )
    )

    print()
    print("=" * 70)
    print(
        f"{model.upper()} DOWNLOAD PLAN"
    )
    print("=" * 70)

    print(
        f"Products: "
        f"{len(available_products)}"
    )

    for product_name in (
        available_products
    ):
        print(
            f"  {product_name}"
        )

    print()
    print(
        "Unique raw fields:"
    )

    fields = collect_model_fields(
        model,
        available_products,
    )

    for field in fields:
        description = (
            f"  {field['short_name']}"
        )

        if field[
            "level"
        ] is not None:
            description += (
                f" @ {field['level']}"
            )

        if field[
            "type_of_level"
        ] is not None:
            description += (
                f" "
                f"({field['type_of_level']})"
            )

        if field.get(
            "idx_level_text"
        ):
            description += (
                f" "
                f"[{field['idx_level_text']}]"
            )

        print(
            description
        )

    print("=" * 70)