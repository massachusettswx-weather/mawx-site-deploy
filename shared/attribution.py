from datetime import (
    datetime,
    timezone,
)

from shared.models import (
    MODELS,
)


# ============================================================
# MASSACHUSETTSWX ATTRIBUTION REGISTRY
#
# This keeps provider attribution separate from plotting code.
#
# A future model can add its attribution here without
# modifying every renderer.
# ============================================================

ATTRIBUTIONS = {

    # ========================================================
    # ECMWF IFS
    # ========================================================

    "ifs": {
        "provider": (
            "European Centre for Medium-Range "
            "Weather Forecasts (ECMWF)"
        ),

        "map_footer": (
            "© {year} European Centre for Medium-Range "
            "Weather Forecasts (ECMWF). "
            "This service is based on data and products "
            "of the European Centre for Medium-Range "
            "Weather Forecasts (ECMWF)."
        ),

        "source": (
            "European Centre for Medium-Range "
            "Weather Forecasts (ECMWF)"
        ),

        "license_name": (
            "Creative Commons Attribution 4.0 "
            "International (CC BY 4.0)"
        ),

        "license_url": (
            "https://creativecommons.org/"
            "licenses/by/4.0/"
        ),

        "modifications_notice": (
            "Graphics and derived products have been "
            "created and modified by MassachusettsWx "
            "from ECMWF data."
        ),

        "disclaimer": (
            "ECMWF is not responsible for the content "
            "or interpretation of this service or for "
            "derived MassachusettsWx graphics."
        ),
    },

    # ========================================================
    # ECMWF AIFS
    # ========================================================

    "aifs": {
        "provider": (
            "European Centre for Medium-Range "
            "Weather Forecasts (ECMWF)"
        ),

        "map_footer": (
            "© {year} European Centre for Medium-Range "
            "Weather Forecasts (ECMWF). "
            "This service is based on data and products "
            "of the European Centre for Medium-Range "
            "Weather Forecasts (ECMWF)."
        ),

        "source": (
            "European Centre for Medium-Range "
            "Weather Forecasts (ECMWF)"
        ),

        "license_name": (
            "Creative Commons Attribution 4.0 "
            "International (CC BY 4.0)"
        ),

        "license_url": (
            "https://creativecommons.org/"
            "licenses/by/4.0/"
        ),

        "modifications_notice": (
            "Graphics and derived products have been "
            "created and modified by MassachusettsWx "
            "from ECMWF data."
        ),

        "disclaimer": (
            "ECMWF is not responsible for the content "
            "or interpretation of this service or for "
            "derived MassachusettsWx graphics."
        ),
    },

    # ========================================================
    # NOAA/NCEP GFS
    # ========================================================

    "gfs": {
        "provider": "NOAA/NCEP",

        # We can add a separate NOAA attribution footer later
        # if desired.
        "map_footer": None,

        "source": "NOAA/NCEP",

        "license_name": None,

        "license_url": None,

        "modifications_notice": (
            "Graphics and derived products created "
            "by MassachusettsWx."
        ),

        "disclaimer": None,
    },
}


# ============================================================
# CURRENT YEAR
# ============================================================

def current_year():
    return (
        datetime.now(
            timezone.utc
        ).year
    )


# ============================================================
# RESOLVE MODEL KEY
# ============================================================

def resolve_model_key(
    model,
):
    """
    Accept either:

        "ifs"
        "aifs"
        "gfs"

    or display names such as:

        "ECMWF IFS"
        "ECMWF AIFS"
        "NCEP GFS"

    This lets plotting.py keep its current interface.
    """

    if model is None:
        return None

    value = str(
        model
    ).strip()

    lowered = (
        value.lower()
    )

    # Exact registry key.
    if lowered in MODELS:

        return lowered

    # Match configured display name.
    for (
        model_key,
        config,
    ) in MODELS.items():

        configured_name = str(
            config.get(
                "name",
                ""
            )
        )

        if (
            configured_name.lower()
            == lowered
        ):

            return model_key

        short_name = str(
            config.get(
                "short_name",
                ""
            )
        )

        if (
            short_name
            and short_name.lower()
            == lowered
        ):

            return model_key

    return None


# ============================================================
# GET ATTRIBUTION CONFIG
# ============================================================

def get_attribution(
    model,
):
    model_key = (
        resolve_model_key(
            model
        )
    )

    if model_key is None:

        return {}

    return ATTRIBUTIONS.get(
        model_key,
        {},
    )


# ============================================================
# MAP FOOTER
# ============================================================

def get_map_attribution(
    model,
):
    config = get_attribution(
        model
    )

    footer = config.get(
        "map_footer"
    )

    if not footer:

        return None

    return footer.format(
        year=current_year()
    )


# ============================================================
# LEGAL METADATA
# ============================================================

def get_legal_attribution(
    model,
):
    config = get_attribution(
        model
    )

    if not config:

        return None

    return {
        "provider": (
            config.get(
                "provider"
            )
        ),

        "source": (
            config.get(
                "source"
            )
        ),

        "license_name": (
            config.get(
                "license_name"
            )
        ),

        "license_url": (
            config.get(
                "license_url"
            )
        ),

        "modifications_notice": (
            config.get(
                "modifications_notice"
            )
        ),

        "disclaimer": (
            config.get(
                "disclaimer"
            )
        ),
    }