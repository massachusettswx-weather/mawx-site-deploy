TROPICAL_BASINS = {
    # Atlantic
    "atlantic": {
        "name": "Tropical Atlantic",
        "extent": (-105, 25, -5, 55),
    },

    "caribbean": {
        "name": "Caribbean",
        "extent": (-90, -55, 5, 30),
    },

    "gulf": {
        "name": "Gulf of Mexico",
        "extent": (-100, -75, 15, 32),
    },

    "south_atlantic": {
        "name": "South Atlantic",
        "extent": (-70, 25, -40, 5),
    },

    # Eastern/Central Pacific
    "epac": {
        "name": "Eastern Pacific",
        "extent": (-140, -75, 0, 45),
    },

    "cpac": {
        "name": "Central Pacific",
        "extent": (-180, -135, 0, 45),
    },

    # Western Pacific
    "wpac": {
        "name": "Western Pacific",
        "extent": (100, 180, 0, 50),
    },

    # Indian Ocean
    "north_indian": {
        "name": "North Indian Ocean",
        "extent": (40, 110, 0, 35),
    },

    "arabian_sea": {
        "name": "Arabian Sea",
        "extent": (40, 80, 0, 30),
    },

    "bay_of_bengal": {
        "name": "Bay of Bengal",
        "extent": (75, 105, 0, 30),
    },

    "south_indian": {
        "name": "South Indian Ocean",
        "extent": (20, 120, -40, 5),
    },

    # Australia / Southwest Pacific
    "australia": {
        "name": "Australian Region",
        "extent": (90, 180, -40, 5),
    },

    "sw_pacific": {
        "name": "Southwest Pacific",
        "extent": (135, 180, -40, 5),
    },

    # Dateline-east side of South Pacific
    "se_pacific": {
        "name": "Southeast Pacific",
        "extent": (-180, -75, -40, 5),
    },

    # Broad hemispheric views
    "north_tropics": {
        "name": "Northern Tropics",
        "extent": (-180, 180, 0, 55),
    },

    "south_tropics": {
        "name": "Southern Tropics",
        "extent": (-180, 180, -45, 5),
    },

    "global_tropics": {
        "name": "Global Tropics",
        "extent": (-180, 180, -45, 55),
    },
}


DEFAULT_BASIN = "atlantic"


def get_basin(name):

    # MassachusettsWx shared-region aliases
    _aliases = {
        "tropical_atlantic": "atlantic",
        "western_atlantic": "atlantic",
        "central_atlantic": "atlantic",
        "eastern_atlantic": "atlantic",
        "mid_atlantic": "atlantic",
        "gulf_of_mexico": "gulf",
        "eastern_pacific": "epac",
        "central_pacific": "cpac",
        "western_pacific": "wpac",
        "indian_ocean": "north_indian",
        "western_indian_ocean": "south_indian",
        "central_indian_ocean": "south_indian",
        "eastern_indian_ocean": "south_indian",
        "tropical_indian_ocean": "south_indian",
    }
    name = _aliases.get(name, name)

    key = str(name).lower()

    if key not in TROPICAL_BASINS:
        raise ValueError(
            f"Unknown tropical basin: {name}. "
            f"Available: {', '.join(TROPICAL_BASINS)}"
        )

    return TROPICAL_BASINS[key]


def get_extent(name):
    return get_basin(name)["extent"]


def get_basin_name(name):
    return get_basin(name)["name"]
