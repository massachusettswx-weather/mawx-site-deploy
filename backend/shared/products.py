# ============================================================
# MASSACHUSETTSWX SHARED PRODUCT REGISTRY
# ============================================================

PRODUCTS = {

    # ========================================================
    # UPPER AIR
    # ========================================================

    "h5_vort": {
        "name": "500 mb Height + Relative Vorticity",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "500 mb",
        "shade_field": "vorticity",
        "shading_name": "Relative Vorticity",
        "shading_units": "10⁻⁵ s⁻¹",
        "shading_levels": list(range(2, 52, 2)),
        "cmap": "YlOrRd",
        "height_interval": 60,

        "gfs": {
            "fields": {
                "height": {
                    "short_name": "gh",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                },
                "u": {
                    "short_name": "u",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                },
                "v": {
                    "short_name": "v",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                },
            },
            "derive": "relative_vorticity",
        },

        "ifs": {
            "fields": {
                "height": {
                    "short_name": "gh",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                },
                "vorticity": {
                    "short_name": "vo",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                },
            },
            "postprocess": {
                "vorticity": "vorticity_display",
            },
        },

        "aifs": {
            "fields": {
                "height": {
                    "short_name": "z",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
                "u": {
                    "short_name": "u",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                },
                "v": {
                    "short_name": "v",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                },
            },
            "derive": "relative_vorticity",
        },
    },

    "t925_hgt": {
        "name": "925 mb Temperature + Height",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "925 mb",
        "shade_field": "temperature",
        "shading_name": "Temperature",
        "shading_units": "°C",
        "shading_levels": list(range(-40, 42, 2)),
        "cmap": "coolwarm",
        "height_interval": 30,

        "gfs": {
            "fields": {
                "temperature": {
                    "short_name": "t",
                    "level": 925,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "gh",
                    "level": 925,
                    "type_of_level": "isobaricInhPa",
                },
            },
        },

        "ifs": {
            "fields": {
                "temperature": {
                    "short_name": "t",
                    "level": 925,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "gh",
                    "level": 925,
                    "type_of_level": "isobaricInhPa",
                },
            },
        },

        "aifs": {
            "fields": {
                "temperature": {
                    "short_name": "t",
                    "level": 925,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "z",
                    "level": 925,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
        },
    },

    "t850_hgt": {
        "name": "850 mb Temperature + Height",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "850 mb",
        "shade_field": "temperature",
        "shading_name": "Temperature",
        "shading_units": "°C",
        "shading_levels": list(range(-40, 42, 2)),
        "cmap": "coolwarm",
        "height_interval": 30,

        "gfs": {
            "fields": {
                "temperature": {
                    "short_name": "t",
                    "level": 850,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "gh",
                    "level": 850,
                    "type_of_level": "isobaricInhPa",
                },
            },
        },

        "ifs": {
            "fields": {
                "temperature": {
                    "short_name": "t",
                    "level": 850,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "gh",
                    "level": 850,
                    "type_of_level": "isobaricInhPa",
                },
            },
        },

        "aifs": {
            "fields": {
                "temperature": {
                    "short_name": "t",
                    "level": 850,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "z",
                    "level": 850,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
        },
    },

    "rh700_hgt": {
        "name": "700 mb Relative Humidity + Height",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "700 mb",
        "shade_field": "rh",
        "shading_name": "Relative Humidity",
        "shading_units": "%",
        "shading_levels": list(range(10, 105, 5)),
        "cmap": "YlGnBu",
        "height_interval": 30,

        "gfs": {
            "fields": {
                "rh": {
                    "short_name": "r",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "gh",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
            },
        },

        "ifs": {
            "fields": {
                "rh": {
                    "short_name": "r",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "gh",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
            },
        },
    },

    "omega700": {
        "name": "700 mb Vertical Velocity",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "700 mb",
        "shade_field": "omega",
        "shading_name": "Vertical Velocity",
        "shading_units": "Pa s⁻¹",
        "shading_levels": [
            -2.0, -1.5, -1.0, -0.75, -0.50,
            -0.30, -0.20, -0.10, -0.05,
             0.05, 0.10, 0.20, 0.30, 0.50,
             0.75, 1.0, 1.5, 2.0,
        ],
        "cmap": "coolwarm",
        "height_interval": 30,

        "gfs": {
            "fields": {
                "omega": {
                    "short_name": "w",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "gh",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
            },
        },

        "ifs": {
            "fields": {
                "omega": {
                    "short_name": "w",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "gh",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
            },
        },

        "aifs": {
            "fields": {
                "omega": {
                    "short_name": "w",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                },
                "height": {
                    "short_name": "z",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
        },
    },

    # ========================================================
    # WIND ALOFT
    # ========================================================

    "wind925_hgt": {
        "name": "925 mb Wind Speed + Height",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "925 mb",
        "shade_field": "wind_speed",
        "shading_name": "Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(10, 101, 5)),
        "cmap": "viridis",
        "height_interval": 30,

        "gfs": {
            "fields": {
                "u": {"short_name": "u", "level": 925, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 925, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 925, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "u": {"short_name": "u", "level": 925, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 925, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 925, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "u": {"short_name": "u", "level": 925, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 925, "type_of_level": "isobaricInhPa"},
                "height": {
                    "short_name": "z",
                    "level": 925,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
            "derive": "wind_speed_knots",
        },
    },

    "wind850_hgt": {
        "name": "850 mb Wind Speed + Height",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "850 mb",
        "shade_field": "wind_speed",
        "shading_name": "Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(10, 121, 5)),
        "cmap": "viridis",
        "height_interval": 30,

        "gfs": {
            "fields": {
                "u": {"short_name": "u", "level": 850, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 850, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 850, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "u": {"short_name": "u", "level": 850, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 850, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 850, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "u": {"short_name": "u", "level": 850, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 850, "type_of_level": "isobaricInhPa"},
                "height": {
                    "short_name": "z",
                    "level": 850,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
            "derive": "wind_speed_knots",
        },
    },

    "wind700_hgt": {
        "name": "700 mb Wind Speed + Height",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "700 mb",
        "shade_field": "wind_speed",
        "shading_name": "Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(10, 131, 5)),
        "cmap": "viridis",
        "height_interval": 30,

        "gfs": {
            "fields": {
                "u": {"short_name": "u", "level": 700, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 700, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 700, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "u": {"short_name": "u", "level": 700, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 700, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 700, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "u": {"short_name": "u", "level": 700, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 700, "type_of_level": "isobaricInhPa"},
                "height": {
                    "short_name": "z",
                    "level": 700,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
            "derive": "wind_speed_knots",
        },
    },

    "wind500_hgt": {
        "name": "500 mb Wind Speed + Height",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "500 mb",
        "shade_field": "wind_speed",
        "shading_name": "Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(20, 161, 5)),
        "cmap": "plasma",
        "height_interval": 60,

        "gfs": {
            "fields": {
                "u": {"short_name": "u", "level": 500, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 500, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 500, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "u": {"short_name": "u", "level": 500, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 500, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 500, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "u": {"short_name": "u", "level": 500, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 500, "type_of_level": "isobaricInhPa"},
                "height": {
                    "short_name": "z",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
            "derive": "wind_speed_knots",
        },
    },

    "jet300": {
        "name": "300 mb Jet Stream",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "300 mb",
        "shade_field": "wind_speed",
        "shading_name": "Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(40, 201, 10)),
        "cmap": "plasma",
        "height_interval": 120,

        "gfs": {
            "fields": {
                "u": {"short_name": "u", "level": 300, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 300, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 300, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "u": {"short_name": "u", "level": 300, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 300, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 300, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "u": {"short_name": "u", "level": 300, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 300, "type_of_level": "isobaricInhPa"},
                "height": {
                    "short_name": "z",
                    "level": 300,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
            "derive": "wind_speed_knots",
        },
    },

    "jet250": {
        "name": "250 mb Jet Stream",
        "category": "Upper Air",
        "renderer": "height_shading",
        "level_name": "250 mb",
        "shade_field": "wind_speed",
        "shading_name": "Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(40, 211, 10)),
        "cmap": "plasma",
        "height_interval": 120,

        "gfs": {
            "fields": {
                "u": {"short_name": "u", "level": 250, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 250, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 250, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "u": {"short_name": "u", "level": 250, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 250, "type_of_level": "isobaricInhPa"},
                "height": {"short_name": "gh", "level": 250, "type_of_level": "isobaricInhPa"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "u": {"short_name": "u", "level": 250, "type_of_level": "isobaricInhPa"},
                "v": {"short_name": "v", "level": 250, "type_of_level": "isobaricInhPa"},
                "height": {
                    "short_name": "z",
                    "level": 250,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
            "derive": "wind_speed_knots",
        },
    },

    # ========================================================
    # THICKNESS
    # ========================================================

    "thickness_1000_500": {
        "name": "1000–500 mb Thickness",
        "category": "Upper Air",
        "renderer": "scalar_contour",
        "shade_field": "thickness",
        "shading_name": "1000–500 mb Thickness",
        "shading_units": "m",
        "shading_levels": list(range(4800, 6061, 30)),
        "contour_interval": 60,
        "cmap": "coolwarm",

        "gfs": {
            "fields": {
                "height_500": {"short_name": "gh", "level": 500, "type_of_level": "isobaricInhPa"},
                "height_1000": {"short_name": "gh", "level": 1000, "type_of_level": "isobaricInhPa"},
            },
            "derive": "thickness_1000_500",
        },

        "ifs": {
            "fields": {
                "height_500": {"short_name": "gh", "level": 500, "type_of_level": "isobaricInhPa"},
                "height_1000": {"short_name": "gh", "level": 1000, "type_of_level": "isobaricInhPa"},
            },
            "derive": "thickness_1000_500",
        },

        "aifs": {
            "fields": {
                "height_500": {
                    "short_name": "z",
                    "level": 500,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
                "height_1000": {
                    "short_name": "z",
                    "level": 1000,
                    "type_of_level": "isobaricInhPa",
                    "conversion": "geopotential_to_height",
                },
            },
            "derive": "thickness_1000_500",
        },
    },

    # ========================================================
    # SURFACE
    # ========================================================

    "mslp": {
        "name": "Mean Sea Level Pressure",
        "category": "Surface",
        "renderer": "surface_pressure",

        "gfs": {
            "fields": {
                "mslp": {
                    "short_name": "prmsl",
                    "type_of_level": "meanSea",
                },
            },
        },

        "ifs": {
            "fields": {
                "mslp": {"short_name": "msl"},
            },
        },

        "aifs": {
            "fields": {
                "mslp": {"short_name": "msl"},
            },
        },
    },

    "mslp_wind10": {
        "name": "MSLP + 10 m Wind",
        "category": "Surface",
        "renderer": "pressure_wind",
        "shade_field": "wind_speed",
        "shading_name": "10 m Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(5, 81, 5)),
        "cmap": "viridis",

        "gfs": {
            "fields": {
                "mslp": {
                    "short_name": "prmsl",
                    "type_of_level": "meanSea",
                },
                "u": {
                    "short_name": "10u",
                    "level": 10,
                    "type_of_level": "heightAboveGround",
                },
                "v": {
                    "short_name": "10v",
                    "level": 10,
                    "type_of_level": "heightAboveGround",
                },
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "mslp": {"short_name": "msl"},
                "u": {"short_name": "10u"},
                "v": {"short_name": "10v"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "mslp": {"short_name": "msl"},
                "u": {"short_name": "10u"},
                "v": {"short_name": "10v"},
            },
            "derive": "wind_speed_knots",
        },
    },

    "wind10": {
        "name": "10 m Wind Speed",
        "category": "Surface",
        "renderer": "surface_shading",
        "shade_field": "wind_speed",
        "shading_name": "10 m Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(5, 81, 5)),
        "cmap": "viridis",

        "gfs": {
            "fields": {
                "u": {"short_name": "10u", "level": 10, "type_of_level": "heightAboveGround"},
                "v": {"short_name": "10v", "level": 10, "type_of_level": "heightAboveGround"},
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "u": {"short_name": "10u"},
                "v": {"short_name": "10v"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "u": {"short_name": "10u"},
                "v": {"short_name": "10v"},
            },
            "derive": "wind_speed_knots",
        },
    },

    "wind100": {
        "name": "100 m Wind Speed",
        "category": "Surface",
        "renderer": "surface_shading",
        "shade_field": "wind_speed",
        "shading_name": "100 m Wind Speed",
        "shading_units": "kt",
        "shading_levels": list(range(5, 101, 5)),
        "cmap": "viridis",

        "gfs": {
            "fields": {
                "u": {"short_name": "u", "level": 100, "type_of_level": "heightAboveGround"},
                "v": {"short_name": "v", "level": 100, "type_of_level": "heightAboveGround"},
            },
            "derive": "wind_speed_knots",
        },

        "ifs": {
            "fields": {
                "u": {"short_name": "100u"},
                "v": {"short_name": "100v"},
            },
            "derive": "wind_speed_knots",
        },

        "aifs": {
            "fields": {
                "u": {"short_name": "100u"},
                "v": {"short_name": "100v"},
            },
            "derive": "wind_speed_knots",
        },
    },

    # NOAA GFS inventory explicitly has surface GUST.
    "gust10": {
        "name": "Wind Gust",
        "category": "Surface",
        "renderer": "surface_shading",
        "shade_field": "gust",
        "shading_name": "Wind Gust",
        "shading_units": "kt",
        "shading_levels": list(range(10, 111, 5)),
        "cmap": "plasma",

        "gfs": {
            "fields": {
                "gust": {
                    "short_name": "gust",
                    "type_of_level": "surface",
                },
            },
            "postprocess": {
                "gust": "ms_to_knots",
            },
        },

        "ifs": {
            "fields": {
                "gust": {"short_name": "10fg"},
            },
            "postprocess": {
                "gust": "ms_to_knots",
            },
        },
    },

    "t2m": {
        "name": "2 m Temperature",
        "category": "Surface",
        "renderer": "surface_shading",
        "shade_field": "temperature",
        "shading_name": "2 m Temperature",
        "shading_units": "°F",
        "shading_levels": list(range(-40, 126, 5)),
        "cmap": "coolwarm",

        "gfs": {
            "fields": {
                "temperature": {"short_name": "2t", "level": 2, "type_of_level": "heightAboveGround"},
            },
        },

        "ifs": {
            "fields": {
                "temperature": {"short_name": "2t"},
            },
        },

        "aifs": {
            "fields": {
                "temperature": {"short_name": "2t"},
            },
        },
    },

    "td2m": {
        "name": "2 m Dew Point",
        "category": "Surface",
        "renderer": "surface_shading",
        "shade_field": "dewpoint",
        "shading_name": "2 m Dew Point",
        "shading_units": "°F",
        "shading_levels": list(range(-20, 86, 5)),
        "cmap": "YlGn",

        "gfs": {
            "fields": {
                "dewpoint": {"short_name": "2d", "level": 2, "type_of_level": "heightAboveGround"},
            },
        },

        "ifs": {
            "fields": {
                "dewpoint": {"short_name": "2d"},
            },
        },

        "aifs": {
            "fields": {
                "dewpoint": {"short_name": "2d"},
            },
        },
    },

    "pwat": {
        "name": "Precipitable Water",
        "category": "Moisture",
        "renderer": "surface_shading",
        "shade_field": "pwat",
        "shading_name": "Precipitable Water",
        "shading_units": "in",
        "shading_levels": [
            0.10, 0.25, 0.50, 0.75,
            1.00, 1.25, 1.50, 1.75,
            2.00, 2.25, 2.50, 3.00,
        ],
        "cmap": "YlGnBu",

        "gfs": {
            "fields": {
                "pwat": {
                    "short_name": "pwat",
                    "type_of_level": "atmosphereSingleLayer",
                },
            },
        },

        "ifs": {
            "fields": {
                "pwat": {"short_name": "tcwv"},
            },
        },
    },

    "cloud_total": {
        "name": "Total Cloud Cover",
        "category": "Clouds",
        "renderer": "surface_shading",
        "shade_field": "cloud_cover",
        "shading_name": "Total Cloud Cover",
        "shading_units": "%",
        "shading_levels": list(range(0, 105, 5)),
        "cmap": "Greys",

        "gfs": {
            "fields": {
                "cloud_cover": {
                    "short_name": "tcc",
                    "idx_level_text": "entire atmosphere",
                },
            },
        },

        "ifs": {
            "fields": {
                "cloud_cover": {"short_name": "tcc"},
            },
        },

        "aifs": {
            "fields": {
                "cloud_cover": {"short_name": "tcc"},
            },
        },
    },

    # ========================================================
    # CAPE
    # ========================================================

    "sbcape": {
        "name": "Surface-Based CAPE",
        "category": "Instability",
        "renderer": "surface_shading",
        "shade_field": "cape",
        "shading_name": "SBCAPE",
        "shading_units": "J kg⁻¹",
        "shading_levels": [
            100, 250, 500, 750, 1000, 1500,
            2000, 2500, 3000, 4000, 5000, 6000,
        ],
        "cmap": "plasma",

        "gfs": {
            "fields": {
                "cape": {
                    "short_name": "cape",
                    "type_of_level": "surface",
                    "idx_level_text": "surface",
                },
            },
        },
    },

    "mlcape": {
        "name": "Mixed-Layer CAPE",
        "category": "Instability",
        "renderer": "surface_shading",
        "shade_field": "cape",
        "shading_name": "MLCAPE",
        "shading_units": "J kg⁻¹",
        "shading_levels": [
            100, 250, 500, 750, 1000, 1500,
            2000, 2500, 3000, 4000, 5000, 6000,
        ],
        "cmap": "plasma",

        "gfs": {
            "fields": {
                "cape": {
                    "short_name": "cape",
                    "type_of_level": "pressureFromGroundLayer",
                    "level": 9000,
                    "idx_level_text": "90-0 mb above ground",
                },
            },
        },
    },

    "mucape": {
        "name": "Most-Unstable CAPE",
        "category": "Instability",
        "renderer": "surface_shading",
        "shade_field": "cape",
        "shading_name": "MUCAPE",
        "shading_units": "J kg⁻¹",
        "shading_levels": [
            100, 250, 500, 750, 1000, 1500,
            2000, 2500, 3000, 4000, 5000, 6000,
        ],
        "cmap": "plasma",

        "gfs": {
            "fields": {
                "cape": {
                    "short_name": "cape",
                    "type_of_level": "pressureFromGroundLayer",
                    "level": 25500,
                    "idx_level_text": "255-0 mb above ground",
                },
            },
        },

        "ifs": {
            "fields": {
                "cape": {"short_name": "mucape"},
            },
        },
    },

    # ========================================================
    # CIN
    # ========================================================

    "sbcin": {
        "name": "Surface-Based CIN",
        "category": "Instability",
        "renderer": "surface_shading",
        "shade_field": "cin",
        "shading_name": "SBCIN",
        "shading_units": "J kg⁻¹",
        "shading_levels": [
            -500, -400, -300, -250, -200,
            -150, -100, -75, -50, -25, -10, 0,
        ],
        "cmap": "viridis_r",

        "gfs": {
            "fields": {
                "cin": {
                    "short_name": "cin",
                    "type_of_level": "surface",
                    "idx_level_text": "surface",
                },
            },
        },
    },

    "mlcin": {
        "name": "Mixed-Layer CIN",
        "category": "Instability",
        "renderer": "surface_shading",
        "shade_field": "cin",
        "shading_name": "MLCIN",
        "shading_units": "J kg⁻¹",
        "shading_levels": [
            -500, -400, -300, -250, -200,
            -150, -100, -75, -50, -25, -10, 0,
        ],
        "cmap": "viridis_r",

        "gfs": {
            "fields": {
                "cin": {
                    "short_name": "cin",
                    "type_of_level": "pressureFromGroundLayer",
                    "level": 9000,
                    "idx_level_text": "90-0 mb above ground",
                },
            },
        },
    },

    "mucin": {
        "name": "Most-Unstable CIN",
        "category": "Instability",
        "renderer": "surface_shading",
        "shade_field": "cin",
        "shading_name": "MUCIN",
        "shading_units": "J kg⁻¹",
        "shading_levels": [
            -500, -400, -300, -250, -200,
            -150, -100, -75, -50, -25, -10, 0,
        ],
        "cmap": "viridis_r",

        "gfs": {
            "fields": {
                "cin": {
                    "short_name": "cin",
                    "type_of_level": "pressureFromGroundLayer",
                    "level": 25500,
                    "idx_level_text": "255-0 mb above ground",
                },
            },
        },
    },

    # ========================================================
    # PRECIPITATION
    # ========================================================

    "precip_rate": {
        "name": "Total Precipitation Rate",
        "category": "Precipitation",
        "renderer": "surface_shading",
        "shade_field": "precip_rate",
        "shading_name": "Precipitation Rate",
        "shading_units": "mm h⁻¹",
        "shading_levels": [
            0.1, 0.25, 0.5, 1, 2, 3,
            5, 7.5, 10, 15, 20, 30, 40, 50,
        ],
        "cmap": "turbo",

        "ifs": {
            "fields": {
                "precip_rate": {"short_name": "tprate"},
            },
            "postprocess": {
                "precip_rate": "precip_rate_to_mm_hour",
            },
        },
    },

    # ECMWF numeric PTYPE.
    "ptype": {
        "name": "Precipitation Type",
        "category": "Precipitation",
        "renderer": "categorical",
        "shade_field": "ptype",

        "ifs": {
            "fields": {
                "ptype": {"short_name": "ptype"},
            },
        },
    },

    # GFS exposes four categorical binary fields directly.
    "gfs_ptype": {
        "name": "Precipitation Type",
        "category": "Precipitation",
        "renderer": "categorical_gfs",
        "shade_field": "ptype",

        "gfs": {
            "fields": {
                "rain": {
                    "short_name": "crain",
                    "type_of_level": "surface",
                    "idx_level_text": "surface",
                },
                "snow": {
                    "short_name": "csnow",
                    "type_of_level": "surface",
                    "idx_level_text": "surface",
                },
                "freezing_rain": {
                    "short_name": "cfrzr",
                    "type_of_level": "surface",
                    "idx_level_text": "surface",
                },
                "ice_pellets": {
                    "short_name": "cicep",
                    "type_of_level": "surface",
                    "idx_level_text": "surface",
                },
            },
            "derive": "gfs_precip_type",
        },
    },

    # --------------------------------------------------------
    # CUMULATIVE PRECIPITATION
    # --------------------------------------------------------

    "total_precip": {
        "name": "Total Precipitation",
        "category": "Precipitation",
        "renderer": "accumulation",
        "shade_field": "total_precip",
        "shading_name": "Total Precipitation",
        "shading_units": "in",
        "shading_levels": [
            0.01, 0.05, 0.10, 0.25, 0.50,
            0.75, 1.00, 1.50, 2.00, 3.00,
            4.00, 5.00, 6.00, 8.00, 10.00,
        ],
        "cmap": "turbo",

        "gfs": {
            "fields": {
                "total_precip": {
                    "short_name": "tp",
                    "type_of_level": "surface",
                    "idx_level_text": "surface",
                },
            },
            "accumulation_style": "gfs_interval_or_total",
        },

        "ifs": {
            "fields": {
                "total_precip": {"short_name": "tp"},
            },
            "accumulation_style": "cumulative",
        },

        "aifs": {
            "fields": {
                "total_precip": {"short_name": "tp"},
            },
            "accumulation_style": "cumulative",
        },
    },

    "qpf6": {
        "name": "6-Hour Precipitation",
        "category": "Precipitation",
        "renderer": "accumulation",
        "source_product": "total_precip",
        "window_hours": 6,
        "shade_field": "total_precip",
        "shading_name": "6-Hour Precipitation",
        "shading_units": "in",
        "shading_levels": [
            0.01, 0.05, 0.10, 0.25, 0.50,
            0.75, 1.00, 1.50, 2.00, 3.00,
            4.00, 5.00, 6.00,
        ],
        "cmap": "turbo",

        "gfs": {},
        "ifs": {},
        "aifs": {},
    },

    "qpf12": {
        "name": "12-Hour Precipitation",
        "category": "Precipitation",
        "renderer": "accumulation",
        "source_product": "total_precip",
        "window_hours": 12,
        "shade_field": "total_precip",
        "shading_name": "12-Hour Precipitation",
        "shading_units": "in",
        "shading_levels": [
            0.01, 0.05, 0.10, 0.25, 0.50,
            0.75, 1.00, 1.50, 2.00, 3.00,
            4.00, 5.00, 6.00, 8.00,
        ],
        "cmap": "turbo",

        "gfs": {},
        "ifs": {},
        "aifs": {},
    },

    "qpf24": {
        "name": "24-Hour Precipitation",
        "category": "Precipitation",
        "renderer": "accumulation",
        "source_product": "total_precip",
        "window_hours": 24,
        "shade_field": "total_precip",
        "shading_name": "24-Hour Precipitation",
        "shading_units": "in",
        "shading_levels": [
            0.01, 0.05, 0.10, 0.25, 0.50,
            0.75, 1.00, 1.50, 2.00, 3.00,
            4.00, 5.00, 6.00, 8.00, 10.00,
        ],
        "cmap": "turbo",

        "gfs": {},
        "ifs": {},
        "aifs": {},
    },

    # ========================================================
    # SNOWPACK / SNOW
    # ========================================================

    "snowfall_we": {
        "name": "Snowfall Water Equivalent",
        "category": "Winter",
        "renderer": "accumulation",
        "shade_field": "snowfall",
        "shading_name": "Snowfall Water Equivalent",
        "shading_units": "in",

        "ifs": {
            "fields": {
                "snowfall": {"short_name": "sf"},
            },
        },

        "aifs": {
            "fields": {
                "snowfall": {"short_name": "sf"},
            },
        },
    },

    "snow_depth_we": {
        "name": "Snow Depth",
        "category": "Winter",
        "renderer": "surface_shading",
        "shade_field": "snow_depth",
        "shading_name": "Snow Depth",
        "shading_units": "in",
        "shading_levels": [
            0.01, 0.05, 0.10, 0.25, 0.50,
            1.00, 2.00, 3.00, 5.00, 8.00,
            12.00, 18.00, 24.00,
        ],
        "cmap": "Blues",

        "gfs": {
            "fields": {
                "snow_depth": {
                    "short_name": "sde",
                    "type_of_level": "surface",
                    "idx_level_text": "surface",
                },
            },
        },

        "ifs": {
            "fields": {
                "snow_depth": {"short_name": "sd"},
            },
        },
    },
}


# ============================================================
# NORMAL SINGLE-FRAME PRODUCTS
# ============================================================


# ============================================================
# ECMWF AUTOMATIC PRODUCT EXPANSION
#
# GFS remains untouched.
#
# Existing MassachusettsWx product definitions are reused for
# IFS/AIFS whenever the required raw fields exist in ECMWF
# Open Data.
#
# This prevents us from maintaining three nearly-identical
# copies of every atmospheric product definition.
# ============================================================

from copy import deepcopy


ECMWF_FIELD_TRANSLATIONS = {

    # --------------------------------------------------------
    # Pressure-level fields
    # --------------------------------------------------------

    "gh": {
        "ifs": "gh",
        "aifs": "z",
    },

    "t": {
        "ifs": "t",
        "aifs": "t",
    },

    "r": {
        "ifs": "r",
        # AIFS RH is derived separately from q + temperature.
    },

    "q": {
        "ifs": "q",
        "aifs": "q",
    },

    "u": {
        "ifs": "u",
        "aifs": "u",
    },

    "v": {
        "ifs": "v",
        "aifs": "v",
    },

    "w": {
        "ifs": "w",
        "aifs": "w",
    },

    # --------------------------------------------------------
    # Surface / near-surface fields
    # --------------------------------------------------------

    "prmsl": {
        "ifs": "msl",
        "aifs": "msl",
    },

    "10u": {
        "ifs": "10u",
        "aifs": "10u",
    },

    "10v": {
        "ifs": "10v",
        "aifs": "10v",
    },

    "100u": {
        "ifs": "100u",
        "aifs": "100u",
    },

    "100v": {
        "ifs": "100v",
        "aifs": "100v",
    },

    "gust": {
        "ifs": "10fg",
        "aifs": "10fg",
    },

    "2t": {
        "ifs": "2t",
        "aifs": "2t",
    },

    "2d": {
        "ifs": "2d",
        "aifs": "2d",
    },

    "pwat": {
        "ifs": "tcwv",
        "aifs": "tcwv",
    },

    "tcc": {
        "ifs": "tcc",
        "aifs": "tcc",
    },

    "tp": {
        "ifs": "tp",
        "aifs": "tp",
    },

    "sde": {
        "ifs": "sd",
        "aifs": "sd",
    },
}


def _ecmwf_field_from_gfs(
    field,
    *,
    model,
):
    """
    Convert one existing GFS raw-field description into an
    equivalent ECMWF IFS/AIFS raw-field description.

    Returns None when that field does not have a safe ECMWF
    equivalent.
    """

    source_short_name = (
        field.get(
            "short_name"
        )
    )

    translations = (
        ECMWF_FIELD_TRANSLATIONS.get(
            source_short_name
        )
    )

    if not translations:
        return None

    target_short_name = (
        translations.get(
            model
        )
    )

    if target_short_name is None:
        return None

    result = deepcopy(
        field
    )

    result[
        "short_name"
    ] = target_short_name

    # --------------------------------------------------------
    # AIFS encodes pressure-level height as geopotential z.
    # Convert to geometric/geopotential height before plotting.
    # --------------------------------------------------------

    if (
        model == "aifs"
        and
        source_short_name == "gh"
    ):

        result[
            "short_name"
        ] = "z"

        result[
            "conversion"
        ] = (
            "geopotential_to_height"
        )

    # GFS .idx-only matching text must never leak into ECMWF.
    result.pop(
        "idx_level_text",
        None,
    )

    return result


def _expand_ecmwf_products():
    """
    Add IFS/AIFS mappings to existing atmospheric products
    whenever every required field can be mapped safely.

    Explicit hand-written IFS/AIFS definitions always win.
    """

    added = {
        "ifs": [],
        "aifs": [],
    }

    for (
        product_name,
        product,
    ) in PRODUCTS.items():

        gfs_config = (
            product.get(
                "gfs"
            )
        )

        if not isinstance(
            gfs_config,
            dict,
        ):
            continue

        gfs_fields = (
            gfs_config.get(
                "fields"
            )
        )

        if not isinstance(
            gfs_fields,
            dict,
        ):
            continue

        for model in (
            "ifs",
            "aifs",
        ):

            # Explicit product mapping remains authoritative.
            if model in product:
                continue

            converted_fields = {}
            compatible = True

            for (
                logical_name,
                field,
            ) in gfs_fields.items():

                converted = (
                    _ecmwf_field_from_gfs(
                        field,
                        model=model,
                    )
                )

                if converted is None:
                    compatible = False
                    break

                converted_fields[
                    logical_name
                ] = converted

            if not compatible:
                continue

            if not converted_fields:
                continue

            model_config = {
                "fields": (
                    converted_fields
                ),
            }

            # Preserve product-level derivation instructions.
            if "derive" in gfs_config:
                model_config[
                    "derive"
                ] = gfs_config[
                    "derive"
                ]

            product[
                model
            ] = model_config

            added[
                model
            ].append(
                product_name
            )

    return added


ECMWF_AUTO_EXPANDED_PRODUCTS = (
    _expand_ecmwf_products()
)


# ============================================================
# AIFS MOISTURE-DERIVED PRODUCTS
#
# AIFS pressure-level RH is reconstructed from:
#
#     specific humidity q
#     temperature T
#     pressure level
#
# rather than requiring a direct RH field.
# ============================================================

if (
    "rh700_hgt" in PRODUCTS
    and
    "aifs"
    not in PRODUCTS[
        "rh700_hgt"
    ]
):

    PRODUCTS[
        "rh700_hgt"
    ][
        "aifs"
    ] = {
        "fields": {
            "rh": {
                "short_name": "q",
                "level": 700,
                "type_of_level": (
                    "isobaricInhPa"
                ),
                "derive": (
                    "relative_humidity_from_specific_humidity"
                ),
                "temperature_short_name": "t",
            },

            "temperature": {
                "short_name": "t",
                "level": 700,
                "type_of_level": (
                    "isobaricInhPa"
                ),
            },

            "height": {
                "short_name": "z",
                "level": 700,
                "type_of_level": (
                    "isobaricInhPa"
                ),
                "conversion": (
                    "geopotential_to_height"
                ),
            },
        },

        "derive": (
            "relative_humidity_from_specific_humidity"
        ),
    }


OPERATIONAL_PRODUCTS = [
    "h5_vort",
    "t925_hgt",
    "t850_hgt",
    "rh700_hgt",
    "omega700",
    "wind925_hgt",
    "wind850_hgt",
    "wind700_hgt",
    "wind500_hgt",
    "jet300",
    "jet250",
    "thickness_1000_500",
    "mslp",
    "mslp_wind10",
    "wind10",
    "wind100",
    "gust10",
    "t2m",
    "td2m",
    "pwat",
    "cloud_total",
    "snow_depth_we",
]


GFS_INSTABILITY_PRODUCTS = [
    "sbcape",
    "mlcape",
    "mucape",
    "sbcin",
    "mlcin",
    "mucin",
]


IFS_INSTABILITY_PRODUCTS = [
    "mucape",
]


AIFS_INSTABILITY_PRODUCTS = []


# ============================================================
# SEQUENCE PRODUCTS
# ============================================================

ACCUMULATION_PRODUCTS = [
    "total_precip",
    "snowfall_we",
]


WINDOWED_ACCUMULATION_PRODUCTS = [
    "qpf6",
    "qpf12",
    "qpf24",
]


CATEGORICAL_PRODUCTS = [
    "ptype",
    "gfs_ptype",
]


ALL_PRODUCTS = list(
    PRODUCTS.keys()
)