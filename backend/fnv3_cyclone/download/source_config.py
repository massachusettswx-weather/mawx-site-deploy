FNV3_SOURCE = {
    "enabled": True,

    "base_url": (
        "https://deepmind.google.com/science/weatherlab/"
        "download/cyclones"
    ),

    # WeatherNext Cyclones Operational / FNV3
    "model_code": "OPER",

    "source_type": "weatherlab_atcf",

    # Use all ensemble cyclone detections, including
    # model-generated systems not paired to an existing storm.
    "data_type": "ensemble",
    "pairing": "unpaired",
    "format": "atcf",

    "members": 50,

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

    "latest_cycle_lookback": 12,

    "request_timeout": 60,
}
