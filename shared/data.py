import numpy as np
import xarray as xr

from shared.products import PRODUCTS


EARTH_RADIUS = 6_371_000.0
STANDARD_GRAVITY = 9.80665
MS_TO_KNOTS = 1.9438444924406


# ============================================================
# GRIB LOADING
# ============================================================

def open_cfgrib_field(
    grib_path,
    *,
    short_name,
    type_of_level=None,
    level=None,
):
    filter_keys = {
        "shortName": short_name,
    }

    if type_of_level is not None:
        filter_keys[
            "typeOfLevel"
        ] = type_of_level

    if level is not None:
        filter_keys[
            "level"
        ] = level

    return xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": filter_keys,
            "indexpath": "",
        },
    )


# ============================================================
# LONGITUDE NORMALIZATION
# ============================================================

def normalize_longitudes(
    values,
    lons,
):
    converted = (
        (lons + 180) % 360
    ) - 180

    order = np.argsort(
        converted
    )

    return (
        values[
            ...,
            order,
        ],
        converted[
            order
        ],
    )


# ============================================================
# CONVERSIONS
# ============================================================

def geopotential_to_height(values):
    return values / STANDARD_GRAVITY


def kelvin_to_celsius(values):
    return values - 273.15


def kelvin_to_fahrenheit(values):
    return (
        (values - 273.15)
        * 9.0 / 5.0
        + 32.0
    )


def pascal_to_hpa(values):
    return values / 100.0


def ms_to_knots(values):
    return values * MS_TO_KNOTS


def kg_m2_to_inches(values):
    return values / 25.4


def meters_water_to_inches(values):
    return values * 39.3700787402


def precip_rate_to_mm_hour(values):
    return values * 3600.0


def vorticity_display(values):
    return (
        np.abs(values)
        * 100000.0
    )


# ============================================================
# WIND
# ============================================================

def wind_speed_knots(
    u,
    v,
):
    return ms_to_knots(
        np.sqrt(
            u ** 2
            +
            v ** 2
        )
    )


# ============================================================
# RELATIVE VORTICITY
# ============================================================

def calculate_relative_vorticity(
    u,
    v,
    lats,
    lons,
):
    lat_rad = np.deg2rad(
        lats
    )

    lon_rad = np.deg2rad(
        lons
    )

    cos_lat = np.cos(
        lat_rad
    )

    dv_dlambda = np.gradient(
        v,
        lon_rad,
        axis=1,
        edge_order=2,
    )

    u_cos_lat = (
        u
        * cos_lat[:, None]
    )

    ducos_dphi = np.gradient(
        u_cos_lat,
        lat_rad,
        axis=0,
        edge_order=2,
    )

    denominator = (
        EARTH_RADIUS
        * cos_lat[:, None]
    )

    output = np.full(
        u.shape,
        np.nan,
        dtype=np.float64,
    )

    valid = (
        np.abs(
            denominator
        )
        > 1.0
    )

    np.divide(
        dv_dlambda
        -
        ducos_dphi,
        denominator,
        out=output,
        where=valid,
    )

    return output


# ============================================================
# GFS PRECIP TYPE
# ============================================================

def derive_gfs_precip_type(
    rain,
    snow,
    freezing_rain,
    ice_pellets,
):
    """
    Convert GFS categorical precip flags into the same
    display-category grid used by the plotter:

        0 = none
        1 = rain
        2 = freezing rain
        3 = snow
        4 = mixed
        5 = ice pellets

    Multiple flags active at once become mixed.
    """

    rain_flag = rain > 0.5
    snow_flag = snow > 0.5
    frz_flag = freezing_rain > 0.5
    ice_flag = ice_pellets > 0.5

    count = (
        rain_flag.astype(np.int8)
        + snow_flag.astype(np.int8)
        + frz_flag.astype(np.int8)
        + ice_flag.astype(np.int8)
    )

    output = np.zeros(
        rain.shape,
        dtype=np.int16,
    )

    output[
        rain_flag
        & (count == 1)
    ] = 1

    output[
        frz_flag
        & (count == 1)
    ] = 2

    output[
        snow_flag
        & (count == 1)
    ] = 3

    output[
        ice_flag
        & (count == 1)
    ] = 5

    output[
        count > 1
    ] = 4

    return output


# ============================================================
# METADATA CONVERSION
# ============================================================

def apply_field_conversion(
    values,
    conversion,
):
    if conversion is None:
        return values

    if (
        conversion
        == "geopotential_to_height"
    ):
        return geopotential_to_height(
            values
        )

    raise RuntimeError(
        f"Unsupported field conversion: "
        f"{conversion}"
    )


def apply_postprocess(
    values,
    operation,
):
    if operation is None:
        return values

    if operation == "vorticity_display":
        return vorticity_display(
            values
        )

    if operation == "ms_to_knots":
        return ms_to_knots(
            values
        )

    if (
        operation
        == "precip_rate_to_mm_hour"
    ):
        return precip_rate_to_mm_hour(
            values
        )

    if (
        operation
        == "kg_m2_to_inches"
    ):
        return kg_m2_to_inches(
            values
        )

    if (
        operation
        == "meters_water_to_inches"
    ):
        return meters_water_to_inches(
            values
        )

    raise RuntimeError(
        f"Unsupported postprocess: "
        f"{operation}"
    )


# ============================================================
# TIMES
# ============================================================

def get_times(ds):
    init_time = np.datetime_as_string(
        ds.time.values,
        unit="h",
    )

    if "valid_time" in ds.coords:
        valid_time = (
            np.datetime_as_string(
                ds.valid_time.values,
                unit="h",
            )
        )
    else:
        valid_time = init_time

    return (
        init_time,
        valid_time,
    )


# ============================================================
# PRODUCT UNIT CONVERSION
# ============================================================

def apply_product_units(
    product_name,
    loaded,
    model,
):
    if product_name in {
        "t925_hgt",
        "t850_hgt",
    }:
        loaded[
            "temperature"
        ] = kelvin_to_celsius(
            loaded[
                "temperature"
            ]
        )

    if product_name == "t2m":
        loaded[
            "temperature"
        ] = kelvin_to_fahrenheit(
            loaded[
                "temperature"
            ]
        )

    if product_name == "td2m":
        loaded[
            "dewpoint"
        ] = kelvin_to_fahrenheit(
            loaded[
                "dewpoint"
            ]
        )

    if "mslp" in loaded:
        loaded[
            "mslp"
        ] = pascal_to_hpa(
            loaded[
                "mslp"
            ]
        )

    if "pwat" in loaded:
        loaded[
            "pwat"
        ] = kg_m2_to_inches(
            loaded[
                "pwat"
            ]
        )

    if product_name == "total_precip":
        if model == "gfs":
            loaded[
                "total_precip"
            ] = kg_m2_to_inches(
                loaded[
                    "total_precip"
                ]
            )

        elif model in {
            "ifs",
            "aifs",
        }:
            loaded[
                "total_precip"
            ] = meters_water_to_inches(
                loaded[
                    "total_precip"
                ]
            )

    if (
        product_name
        == "snowfall_we"
        and model in {
            "ifs",
            "aifs",
        }
    ):
        loaded[
            "snowfall"
        ] = meters_water_to_inches(
            loaded[
                "snowfall"
            ]
        )

    if (
        product_name
        == "snow_depth_we"
        and model == "ifs"
    ):
        loaded[
            "snow_depth"
        ] = meters_water_to_inches(
            loaded[
                "snow_depth"
            ]
        )


    if (
        product_name
        == "snow_depth_we"
        and model == "gfs"
    ):
        # GFS SNOD is physical snow depth in metres.
        loaded[
            "snow_depth"
        ] = (
            loaded[
                "snow_depth"
            ]
            * 39.37007874015748
        )

    return loaded


# ============================================================
# LOAD PRODUCT
# ============================================================

def load_product(
    grib_path,
    model,
    product_name,
):
    if product_name not in PRODUCTS:
        raise ValueError(
            f"Unknown product: "
            f"{product_name}"
        )

    product = PRODUCTS[
        product_name
    ]

    if model not in product:
        raise ValueError(
            f"{product_name} "
            f"is not available for "
            f"{model}"
        )

    model_config = product[
        model
    ]

    # Derived-window products don't load raw fields directly.
    if "fields" not in model_config:
        raise RuntimeError(
            f"{product_name} is a derived "
            f"sequence product and cannot "
            f"be loaded directly."
        )

    fields_config = model_config[
        "fields"
    ]

    loaded = {}

    lats = None
    lons = None

    init_time = None
    valid_time = None

    for logical_name, config in (
        fields_config.items()
    ):
        print(
            f"Loading "
            f"{logical_name}: "
            f"{config['short_name']}"
        )

        ds = open_cfgrib_field(
            grib_path,
            short_name=config[
                "short_name"
            ],
            type_of_level=config.get(
                "type_of_level"
            ),
            level=config.get(
                "level"
            ),
        )

        variable_names = list(
            ds.data_vars
        )

        if not variable_names:
            ds.close()

            raise RuntimeError(
                f"No variable found for "
                f"{logical_name}"
            )

        variable_name = (
            variable_names[0]
        )

        values = (
            ds[
                variable_name
            ]
            .load()
            .values
        )

        current_lats = (
            ds.latitude.values
        )

        current_lons = (
            ds.longitude.values
        )

        values = apply_field_conversion(
            values,
            config.get(
                "conversion"
            ),
        )

        (
            values,
            current_lons,
        ) = normalize_longitudes(
            values,
            current_lons,
        )

        loaded[
            logical_name
        ] = values

        if lats is None:
            lats = current_lats

        if lons is None:
            lons = current_lons

        if init_time is None:
            (
                init_time,
                valid_time,
            ) = get_times(
                ds
            )

        ds.close()

    # ========================================================
    # DERIVATIONS
    # ========================================================

    derive = model_config.get(
        "derive"
    )

    if derive == "relative_vorticity":
        loaded[
            "vorticity"
        ] = vorticity_display(
            calculate_relative_vorticity(
                loaded["u"],
                loaded["v"],
                lats,
                lons,
            )
        )

    elif derive == "wind_speed_knots":
        loaded[
            "wind_speed"
        ] = wind_speed_knots(
            loaded["u"],
            loaded["v"],
        )

    elif derive == "thickness_1000_500":
        loaded[
            "thickness"
        ] = (
            loaded[
                "height_500"
            ]
            -
            loaded[
                "height_1000"
            ]
        )

    elif derive == "gfs_precip_type":
        loaded[
            "ptype"
        ] = derive_gfs_precip_type(
            loaded["rain"],
            loaded["snow"],
            loaded[
                "freezing_rain"
            ],
            loaded[
                "ice_pellets"
            ],
        )

    elif derive is not None:
        raise RuntimeError(
            f"Unsupported derivation: "
            f"{derive}"
        )

    # ========================================================
    # POSTPROCESS
    # ========================================================

    postprocess = model_config.get(
        "postprocess",
        {},
    )

    for field_name, operation in (
        postprocess.items()
    ):
        loaded[
            field_name
        ] = apply_postprocess(
            loaded[
                field_name
            ],
            operation,
        )

    loaded = apply_product_units(
        product_name,
        loaded,
        model,
    )

    return {
        "product": product,
        "fields": loaded,
        "lons": lons,
        "lats": lats,
        "init_time": init_time,
        "valid_time": valid_time,
    }