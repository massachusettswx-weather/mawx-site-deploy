FNV3_LARGE_SOURCE = {
    "enabled": True,

    "base_url": (
        "https://deepmind.google.com/science/weatherlab/"
        "download/cyclones"
    ),

    "model_code": "FNV3_LARGE_ENSEMBLE",

    "members": 1000,

    "cycle_hours": [
        0,
        6,
        12,
        18,
    ],

    "forecast_hours": list(
        range(
            0,
            361,
            6,
        )
    ),

    # Individual 1000-member cyclogenesis tracks.
    "ensemble": {
        "data_type": "ensemble",
        "pairing": "cyclogenesis",
        "format": "csv",
    },

    # Google's paired ensemble-mean product.
    "ensemble_mean": {
        "data_type": "ensemble_mean",
        "pairing": "paired",
        "format": "csv",
    },

    # Google's native gridded cumulative
    # cyclogenesis probabilities.
    "cumulative_probability": {
        "data_type": "ensemble",
        "pairing": "cyclogenesis",
        "format": "netcdf",
        "product": "cumulative_probability_fields",
    },

    "curl_retries": 5,
    "curl_connect_timeout": 30,
    "curl_max_time": 900,
}
