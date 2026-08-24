# ============================================================
# MASSACHUSETTSWX MODEL REGISTRY
# ============================================================


MODELS = {

    # ========================================================
    # NCEP GFS
    # ========================================================

    "gfs": {
        "name": "NCEP GFS",
        "short_name": "GFS",

        "center": "NCEP",
        "family": "ncep",

        "deterministic": True,

        "native_resolution": "0.25°",

        "cycles": [
            0,
            6,
            12,
            18,
        ],

        "forecast_start": 0,
        "forecast_end": 384,

        "workers": 2,

        # ----------------------------------------------------
        # FORECAST SCHEDULE
        #
        # f000-f120:
        #     hourly
        #
        # f123-f240:
        #     every 3 hours
        #
        # f246-f384:
        #     every 6 hours
        # ----------------------------------------------------

        "forecast_schedule": {
            "segments": [
                {
                    "start": 0,
                    "end": 120,
                    "step": 1,
                },

                {
                    "start": 123,
                    "end": 240,
                    "step": 3,
                },

                {
                    "start": 246,
                    "end": 384,
                    "step": 6,
                },
            ],
        },

        "download_family": (
            "gfs_idx"
        ),

        "readiness": {
            "method": (
                "gfs_idx"
            ),

            "required_step": 384,
        },

        "extra_products": [
            "sbcape",
            "mlcape",
            "mucape",
            "sbcin",
            "mlcin",
            "mucin",
        ],

        "sequence_enabled": True,
    },

    # ========================================================
    # ECMWF IFS
    # ========================================================

    "ifs": {
        "name": "ECMWF IFS",
        "short_name": "IFS",

        "center": "ECMWF",
        "family": "ecmwf",

        "deterministic": True,

        "native_resolution": "0.25°",

        "cycles": [
            0,
            6,
            12,
            18,
        ],

        "forecast_start": 0,
        "forecast_end": 360,

        "workers": 2,

        # ----------------------------------------------------
        # IFS FORECAST SCHEDULE
        #
        # Requested MassachusettsWx schedule:
        #
        # f000-f090:
        #     hourly
        #
        # f093-f144:
        #     every 3 hours
        #
        # NOTE:
        # 06/18 Open Data availability will be verified by
        # the downloader. If ECMWF does not expose individual
        # hourly 06/18 fields, we can give those cycles their
        # own schedule without changing ifs/run.py.
        # ----------------------------------------------------

        "forecast_schedule": {
            "segments": [
                {
                    "start": 0,
                    "end": 144,
                    "step": 3,
                },
            ],
        },

        "download_family": (
            "ecmwf_open_data"
        ),

        "ecmwf_model": "ifs",

        # ----------------------------------------------------
        # READINESS
        #
        # 00/12 need f144.
        #
        # 06/18 are checked through f90 because current ECMWF
        # Open Data documentation gives the shorter range for
        # those cycles.
        # ----------------------------------------------------

        "readiness": {
            "method": (
                "ecmwf_latest"
            ),

            "required_step_by_cycle": {
                0: 144,
                6: 90,
                12: 144,
                18: 90,
            },

            "probe_param": "msl",
        },

        "extra_products": [
            "mucape",
            "gust10",
            "precip_rate",
        ],

        "sequence_enabled": True,
    },

    # ========================================================
    # ECMWF AIFS
    # ========================================================

    "aifs": {
        "name": "ECMWF AIFS",
        "short_name": "AIFS",

        "center": "ECMWF",
        "family": "ecmwf",

        "deterministic": True,

        "native_resolution": "0.25°",

        "cycles": [
            0,
            6,
            12,
            18,
        ],

        "forecast_start": 0,
        "forecast_end": 360,

        "workers": 2,

        "forecast_schedule": {
            "segments": [
                {
                    "start": 0,
                    "end": 120,
                    "step": 6,
                },
            ],
        },

        "download_family": (
            "ecmwf_open_data"
        ),

        "ecmwf_model": (
            "aifs-single"
        ),

        "readiness": {
            "method": (
                "ecmwf_latest"
            ),

            "required_step": 120,

            "probe_param": "msl",
        },

        "extra_products": [],

        "sequence_enabled": True,
    },

    # ========================================================
    # GOOGLE DEEPMIND FNV3 CYCLONES
    # ========================================================

    "fnv3": {
        "name": "Google DeepMind FNV3",
        "short_name": "FNV3",

        "center": "Google DeepMind",
        "family": "weathernext_cyclones",

        "deterministic": False,
        "ensemble": True,
        "members": 50,

        "native_resolution": "0.25°",

        "cycles": [
            0,
            6,
            12,
            18,
        ],

        "forecast_start": 0,
        "forecast_end": 360,

        "workers": 1,

        "forecast_schedule": {
            "segments": [
                {
                    "start": 0,
                    "end": 360,
                    "step": 6,
                },
            ],
        },

        "download_family": (
            "fnv3_cyclone_tracks"
        ),

        "backend_enabled": True,

        "readiness": {
            "method": (
                "fnv3_cyclone_feed"
            ),
            "required_step": 360,
        },

        "extra_products": [],

        "sequence_enabled": False,
    },

    # ========================================================
    # GOOGLE DEEPMIND FNV3-L CYCLONES
    # ========================================================

    "fnv3_large": {
        "name": "Google DeepMind FNV3-L",
        "short_name": "FNV3-L",

        "center": "Google DeepMind",
        "family": "weathernext_cyclones",

        "deterministic": False,
        "ensemble": True,
        "members": 1000,

        "native_resolution": "0.25°",

        "cycles": [
            0,
            6,
            12,
            18,
        ],

        "forecast_start": 0,
        "forecast_end": 360,

        "workers": 1,

        "forecast_schedule": {
            "segments": [
                {
                    "start": 0,
                    "end": 360,
                    "step": 6,
                },
            ],
        },

        "download_family": (
            "fnv3_large_cyclone_tracks"
        ),

        "backend_enabled": True,

        "readiness": {
            "method": (
                "fnv3_large_cyclone_feed"
            ),
            "required_step": 360,
        },

        "extra_products": [],

        "sequence_enabled": False,
    },
}


# ============================================================
# BASIC MODEL HELPERS
# ============================================================

def model_exists(
    model,
):
    return (
        model in MODELS
    )


def get_model(
    model,
):
    if model not in MODELS:

        raise ValueError(
            f"Unknown model: "
            f"{model}"
        )

    return MODELS[
        model
    ]


def get_model_name(
    model,
):
    return get_model(
        model
    )[
        "name"
    ]


def get_registered_models():
    return list(
        MODELS.keys()
    )


# ============================================================
# WORKERS
# ============================================================

def get_model_workers(
    model,
):
    workers = int(
        get_model(
            model
        ).get(
            "workers",
            1,
        )
    )

    return max(
        1,
        workers,
    )


# ============================================================
# EXTRA PRODUCTS
# ============================================================

def get_model_extra_products(
    model,
):
    return list(
        get_model(
            model
        ).get(
            "extra_products",
            [],
        )
    )


def model_supports_sequences(
    model,
):
    return bool(
        get_model(
            model
        ).get(
            "sequence_enabled",
            False,
        )
    )


# ============================================================
# READINESS
# ============================================================

def get_readiness_config(
    model,
):
    return dict(
        get_model(
            model
        ).get(
            "readiness",
            {},
        )
    )


def get_required_ready_step(
    model,
    cycle_hour,
):
    config = (
        get_readiness_config(
            model
        )
    )

    by_cycle = config.get(
        "required_step_by_cycle"
    )

    if by_cycle is not None:

        if cycle_hour in by_cycle:

            return int(
                by_cycle[
                    cycle_hour
                ]
            )

        text_hour = str(
            cycle_hour
        )

        if text_hour in by_cycle:

            return int(
                by_cycle[
                    text_hour
                ]
            )

    required_step = (
        config.get(
            "required_step"
        )
    )

    if required_step is None:

        return None

    return int(
        required_step
    )


# ============================================================
# FORECAST SCHEDULE EXPANSION
# ============================================================

def _expand_segments(
    segments,
):
    output = []
    seen = set()

    for segment in segments:

        start = int(
            segment[
                "start"
            ]
        )

        end = int(
            segment[
                "end"
            ]
        )

        step = int(
            segment[
                "step"
            ]
        )

        if step <= 0:

            raise ValueError(
                "Forecast schedule "
                "step must be > 0."
            )

        for forecast_hour in range(
            start,
            end + 1,
            step,
        ):

            if forecast_hour in seen:
                continue

            seen.add(
                forecast_hour
            )

            output.append(
                forecast_hour
            )

    output.sort()

    return output


# ============================================================
# GET SCHEDULE CONFIGURATION
# ============================================================

def get_forecast_schedule(
    model,
    cycle_hour=None,
):
    config = get_model(
        model
    )

    schedule = config.get(
        "forecast_schedule"
    )

    if not schedule:

        raise RuntimeError(
            f"No forecast schedule "
            f"configured for "
            f"{model}"
        )

    # --------------------------------------------------------
    # SIMPLE SCHEDULE
    # --------------------------------------------------------

    if "segments" in schedule:

        return schedule

    # --------------------------------------------------------
    # CYCLE-SPECIFIC SCHEDULE
    # --------------------------------------------------------

    by_cycle = schedule.get(
        "by_cycle",
        {},
    )

    if cycle_hour is not None:

        if cycle_hour in by_cycle:

            return by_cycle[
                cycle_hour
            ]

        text_hour = str(
            cycle_hour
        )

        if text_hour in by_cycle:

            return by_cycle[
                text_hour
            ]

    default = schedule.get(
        "default"
    )

    if default is None:

        raise RuntimeError(
            f"No applicable schedule "
            f"for {model} cycle "
            f"{cycle_hour}"
        )

    return default


# ============================================================
# GET FORECAST HOURS
# ============================================================

def get_forecast_hours(
    model,
    cycle_hour=None,
):
    schedule = (
        get_forecast_schedule(
            model,
            cycle_hour=cycle_hour,
        )
    )

    segments = (
        schedule.get(
            "segments",
            [],
        )
    )

    if not segments:

        raise RuntimeError(
            f"Forecast schedule "
            f"for {model} "
            f"has no segments."
        )

    return _expand_segments(
        segments
    )
