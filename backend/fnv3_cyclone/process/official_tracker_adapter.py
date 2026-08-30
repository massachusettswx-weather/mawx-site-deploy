from __future__ import annotations

from collections.abc import Iterable

from .track_schema import FNV3TrackPoint


FIELD_ALIASES = {
    "system_id": (
        "track_id",
        "system_id",
        "cyclone_id",
    ),
    "forecast_hour": (
        "lead_time",
        "forecast_hour",
        "lead_time_hours",
    ),
    "latitude": (
        "latitude",
        "lat",
        "center_latitude",
    ),
    "longitude": (
        "longitude",
        "lon",
        "center_longitude",
    ),
    "max_wind_kt": (
        "maximum_sustained_wind_speed_knots",
        "max_wind_kt",
        "maximum_wind_speed_knots",
    ),
    "mslp_hpa": (
        "minimum_sea_level_pressure_hpa",
        "mslp_hpa",
        "minimum_pressure_hpa",
    ),
    "radius_max_wind_km": (
        "radius_of_maximum_winds_km",
        "radius_max_wind_km",
    ),
    "r34_ne_km": (
        "radius_34_knot_winds_ne_km",
    ),
    "r34_se_km": (
        "radius_34_knot_winds_se_km",
    ),
    "r34_sw_km": (
        "radius_34_knot_winds_sw_km",
    ),
    "r34_nw_km": (
        "radius_34_knot_winds_nw_km",
    ),
    "r50_ne_km": (
        "radius_50_knot_winds_ne_km",
    ),
    "r50_se_km": (
        "radius_50_knot_winds_se_km",
    ),
    "r50_sw_km": (
        "radius_50_knot_winds_sw_km",
    ),
    "r50_nw_km": (
        "radius_50_knot_winds_nw_km",
    ),
    "r64_ne_km": (
        "radius_64_knot_winds_ne_km",
    ),
    "r64_se_km": (
        "radius_64_knot_winds_se_km",
    ),
    "r64_sw_km": (
        "radius_64_knot_winds_sw_km",
    ),
    "r64_nw_km": (
        "radius_64_knot_winds_nw_km",
    ),
}


def _first_value(row, aliases, default=None):
    for name in aliases:
        if name in row:
            value = row[name]

            try:
                if value != value:
                    continue
            except Exception:
                pass

            if value is not None:
                return value

    return default


def _float_or_none(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_forecast_hour(value):
    """
    Convert Google's lead-time representation to forecast hours.

    Supports:
      * integers/floats already expressed in hours
      * pandas Timedelta
      * numpy timedelta64
      * strings such as '6h', '12:00:00', etc.
    """

    if value is None:
        raise ValueError("Missing lead time")

    if isinstance(value, (int, float)):
        return int(round(float(value)))

    if hasattr(value, "total_seconds"):
        return int(
            round(
                value.total_seconds()
                / 3600.0
            )
        )

    try:
        import pandas as pd

        delta = pd.to_timedelta(value)

        return int(
            round(
                delta.total_seconds()
                / 3600.0
            )
        )
    except Exception:
        pass

    text = str(value).strip().lower()

    if text.endswith("h"):
        return int(
            round(
                float(text[:-1])
            )
        )

    return int(
        round(
            float(text)
        )
    )


def _iter_rows(data):
    """
    Accept either:
      * pandas.DataFrame
      * iterable of dictionaries
    """

    if hasattr(data, "to_dict"):
        try:
            return data.to_dict(
                orient="records"
            )
        except TypeError:
            pass

    if isinstance(data, Iterable):
        return data

    raise TypeError(
        "Tracker output must be a pandas DataFrame "
        "or iterable of dictionaries."
    )


def adapt_official_tracker_output(
    data,
    member=0,
    existing_storm=False,
):
    """
    Convert Google WeatherNext DirectTracker output into
    MassachusettsWx FNV3TrackPoint objects.

    Parameters
    ----------
    data
        pandas DataFrame returned by Google's DirectTracker
        or an iterable of row dictionaries.

    member : int
        Ensemble member associated with this tracker run.

        DirectTracker may be executed separately for each
        ensemble member, so membership is deliberately supplied
        here instead of assuming it is always a DataFrame column.

    existing_storm : bool
        Whether these tracks were initialized from an already
        identified tropical cyclone.

    Returns
    -------
    list[FNV3TrackPoint]
    """

    tracks = []

    for row in _iter_rows(data):
        try:
            system_id = str(
                _first_value(
                    row,
                    FIELD_ALIASES["system_id"],
                )
            )

            if system_id in (
                "",
                "None",
            ):
                continue

            forecast_hour = (
                _normalize_forecast_hour(
                    _first_value(
                        row,
                        FIELD_ALIASES[
                            "forecast_hour"
                        ],
                    )
                )
            )

            latitude = float(
                _first_value(
                    row,
                    FIELD_ALIASES["latitude"],
                )
            )

            longitude = float(
                _first_value(
                    row,
                    FIELD_ALIASES["longitude"],
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        tracks.append(
            FNV3TrackPoint(
                system_id=system_id,
                member=int(member),
                forecast_hour=forecast_hour,
                latitude=latitude,
                longitude=longitude,

                max_wind_kt=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES[
                            "max_wind_kt"
                        ],
                    )
                ),

                mslp_hpa=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES[
                            "mslp_hpa"
                        ],
                    )
                ),

                genesis=not bool(
                    existing_storm
                ),

                existing_storm=bool(
                    existing_storm
                ),

                radius_max_wind_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES[
                            "radius_max_wind_km"
                        ],
                    )
                ),

                r34_ne_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r34_ne_km"],
                    )
                ),
                r34_se_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r34_se_km"],
                    )
                ),
                r34_sw_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r34_sw_km"],
                    )
                ),
                r34_nw_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r34_nw_km"],
                    )
                ),

                r50_ne_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r50_ne_km"],
                    )
                ),
                r50_se_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r50_se_km"],
                    )
                ),
                r50_sw_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r50_sw_km"],
                    )
                ),
                r50_nw_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r50_nw_km"],
                    )
                ),

                r64_ne_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r64_ne_km"],
                    )
                ),
                r64_se_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r64_se_km"],
                    )
                ),
                r64_sw_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r64_sw_km"],
                    )
                ),
                r64_nw_km=_float_or_none(
                    _first_value(
                        row,
                        FIELD_ALIASES["r64_nw_km"],
                    )
                ),
            )
        )

    tracks.sort(
        key=lambda point: (
            point.system_id,
            point.member,
            point.forecast_hour,
        )
    )

    return tracks
