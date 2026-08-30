import csv
import io
from pathlib import Path

from fnv3_cyclone.process.track_schema import (
    FNV3TrackPoint,
)


def _first(row, names):
    for name in names:
        if name in row:
            value = row.get(name)

            if value is not None:
                value = str(value).strip()

                if value:
                    return value

    return None


def _optional_float(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _required_float(value):
    if value is None:
        raise ValueError(
            "Required numeric value is missing."
        )

    return float(
        str(value).strip()
    )


def _required_int(value):
    if value is None:
        raise ValueError(
            "Required integer value is missing."
        )

    return int(
        float(
            str(value).strip()
        )
    )


def _normalize_system_id(value):
    value = str(value).strip()

    if not value:
        raise ValueError(
            "Empty ensemble-mean system ID."
        )

    return value


def parse_weatherlab_paired_mean_csv(text):
    """
    Parse the Google Weather Lab paired ensemble-mean CSV.

    Ensemble mean is represented downstream as member 0.
    Individual systems remain separated by system_id.

    The parser intentionally accepts several reasonable
    Weather Lab column aliases so it remains resilient if
    the paired export names differ slightly from the
    cyclogenesis CSV.
    """

    data_lines = []

    for raw_line in text.splitlines():
        if raw_line.startswith("#"):
            continue

        if not raw_line.strip():
            continue

        data_lines.append(
            raw_line
        )

    if not data_lines:
        return []

    reader = csv.DictReader(
        io.StringIO(
            "\n".join(
                data_lines
            )
        )
    )

    output = []

    for row in reader:
        try:
            raw_track_id = _first(
                row,
                [
                    "track_id",
                    "system_id",
                    "storm_id",
                    "cyclone_id",
                ],
            )

            lead_time = _first(
                row,
                [
                    "lead_time_hours",
                    "forecast_hour",
                    "tau",
                ],
            )

            latitude = _first(
                row,
                [
                    "lat",
                    "latitude",
                ],
            )

            longitude = _first(
                row,
                [
                    "lon",
                    "longitude",
                ],
            )

            if (
                raw_track_id is None
                or lead_time is None
                or latitude is None
                or longitude is None
            ):
                continue

            output.append(
                FNV3TrackPoint(
                    system_id=(
                        _normalize_system_id(
                            raw_track_id
                        )
                    ),

                    member=0,

                    forecast_hour=(
                        _required_int(
                            lead_time
                        )
                    ),

                    latitude=(
                        _required_float(
                            latitude
                        )
                    ),

                    longitude=(
                        _required_float(
                            longitude
                        )
                    ),

                    max_wind_kt=(
                        _optional_float(
                            _first(
                                row,
                                [
                                    "maximum_sustained_wind_speed_knots",
                                    "max_wind_kt",
                                    "wind_speed_knots",
                                ],
                            )
                        )
                    ),

                    mslp_hpa=(
                        _optional_float(
                            _first(
                                row,
                                [
                                    "minimum_sea_level_pressure_hpa",
                                    "mslp_hpa",
                                    "minimum_pressure_hpa",
                                ],
                            )
                        )
                    ),

                    # Paired ensemble-mean systems correspond
                    # to initialized/paired systems rather than
                    # unpaired genesis IDs.
                    genesis=False,
                    existing_storm=True,

                    radius_max_wind_km=(
                        _optional_float(
                            _first(
                                row,
                                [
                                    "radius_of_maximum_winds_km",
                                    "radius_max_wind_km",
                                ],
                            )
                        )
                    ),

                    r34_ne_km=(
                        _optional_float(
                            row.get(
                                "radius_34_knot_winds_ne_km"
                            )
                        )
                    ),
                    r34_se_km=(
                        _optional_float(
                            row.get(
                                "radius_34_knot_winds_se_km"
                            )
                        )
                    ),
                    r34_sw_km=(
                        _optional_float(
                            row.get(
                                "radius_34_knot_winds_sw_km"
                            )
                        )
                    ),
                    r34_nw_km=(
                        _optional_float(
                            row.get(
                                "radius_34_knot_winds_nw_km"
                            )
                        )
                    ),

                    r50_ne_km=(
                        _optional_float(
                            row.get(
                                "radius_50_knot_winds_ne_km"
                            )
                        )
                    ),
                    r50_se_km=(
                        _optional_float(
                            row.get(
                                "radius_50_knot_winds_se_km"
                            )
                        )
                    ),
                    r50_sw_km=(
                        _optional_float(
                            row.get(
                                "radius_50_knot_winds_sw_km"
                            )
                        )
                    ),
                    r50_nw_km=(
                        _optional_float(
                            row.get(
                                "radius_50_knot_winds_nw_km"
                            )
                        )
                    ),

                    r64_ne_km=(
                        _optional_float(
                            row.get(
                                "radius_64_knot_winds_ne_km"
                            )
                        )
                    ),
                    r64_se_km=(
                        _optional_float(
                            row.get(
                                "radius_64_knot_winds_se_km"
                            )
                        )
                    ),
                    r64_sw_km=(
                        _optional_float(
                            row.get(
                                "radius_64_knot_winds_sw_km"
                            )
                        )
                    ),
                    r64_nw_km=(
                        _optional_float(
                            row.get(
                                "radius_64_knot_winds_nw_km"
                            )
                        )
                    ),
                )
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

    return output


def parse_weatherlab_paired_mean_file(path):
    path = Path(
        path
    )

    return (
        parse_weatherlab_paired_mean_csv(
            path.read_text(
                encoding="utf-8"
            )
        )
    )
