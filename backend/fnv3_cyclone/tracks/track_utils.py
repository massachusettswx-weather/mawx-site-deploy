MAX_TRACK_WIND_KT = 140
MIN_TRACK_WIND_KT = 20

WIND_BREAKPOINTS_KT = list(range(20, 141, 10))

WIND_LABELS = [
    "20",
    "30",
    "40",
    "50",
    "60",
    "70",
    "80",
    "90",
    "100",
    "110",
    "120",
    "130",
    "140",
]


def normalize_longitude(lon):
    """
    Convert longitude to -180 to 180.
    """
    lon = float(lon)

    while lon > 180:
        lon -= 360

    while lon < -180:
        lon += 360

    return lon


def knots_from_mps(value):
    return float(value) * 1.943844


def mps_from_knots(value):
    return float(value) / 1.943844


def clamp_wind(wind_kt):
    """
    Clamp wind for plotting to 20-140 kt.
    """

    if wind_kt is None:
        return None

    wind_kt = float(wind_kt)

    return min(
        max(wind_kt, MIN_TRACK_WIND_KT),
        MAX_TRACK_WIND_KT,
    )


def categorize_wind(wind_kt):
    """
    Saffir-Simpson category based on sustained wind.
    """

    if wind_kt is None:
        return "unknown"

    wind_kt = float(wind_kt)

    if wind_kt < 34:
        return "disturbance"

    if wind_kt < 64:
        return "tropical_storm"

    if wind_kt < 83:
        return "category_1"

    if wind_kt < 96:
        return "category_2"

    if wind_kt < 113:
        return "category_3"

    if wind_kt < 137:
        return "category_4"

    return "category_5"


def category_label(wind_kt):
    labels = {
        "unknown": "Unknown",
        "disturbance": "Disturbance",
        "tropical_storm": "Tropical Storm",
        "category_1": "Category 1",
        "category_2": "Category 2",
        "category_3": "Category 3",
        "category_4": "Category 4",
        "category_5": "Category 5",
    }

    return labels[categorize_wind(wind_kt)]


def wind_bin(wind_kt):
    """
    Return the 10-kt plotting bin.

    Examples:
        37 -> 30
        68 -> 60
        104 -> 100
        155 -> 140
    """

    wind_kt = clamp_wind(wind_kt)

    if wind_kt >= 140:
        return 140

    return int(wind_kt // 10) * 10
