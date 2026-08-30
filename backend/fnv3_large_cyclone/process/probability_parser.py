from __future__ import annotations

import atexit

from dataclasses import dataclass
from pathlib import Path
import gzip
import tempfile

import numpy as np
import xarray as xr


# ============================================================
# NORMALIZED PROBABILITY FIELD
# ============================================================

@dataclass
class ProbabilityField:
    probability: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray

    variable: str
    threshold_kt: int

    forecast_hour: int | None = None

    units: str | None = None


# ============================================================
# THRESHOLD DISCOVERY
# ============================================================

_THRESHOLD_TERMS = {
    34: (
        "34",
        "34kt",
        "34_kt",
        "34kts",
        "gale",
        "tropical_storm",
    ),

    50: (
        "50",
        "50kt",
        "50_kt",
        "50kts",
    ),

    64: (
        "64",
        "64kt",
        "64_kt",
        "64kts",
        "hurricane",
    ),
}


def _text_for_variable(
    name,
    variable,
):
    pieces = [
        str(name),
    ]

    for key, value in (
        variable.attrs.items()
    ):
        pieces.append(
            str(key)
        )
        pieces.append(
            str(value)
        )

    return " ".join(
        pieces
    ).lower()


def _variable_score(
    name,
    variable,
    threshold_kt,
):
    text = _text_for_variable(
        name,
        variable,
    )

    score = 0

    if "prob" in text:
        score += 10

    if "wind" in text:
        score += 5

    for term in _THRESHOLD_TERMS[
        threshold_kt
    ]:
        if term in text:
            score += 20

    if variable.ndim >= 2:
        score += 2

    return score


def find_probability_variable(
    dataset,
    threshold_kt,
):
    threshold_kt = int(
        threshold_kt
    )

    if threshold_kt not in (
        34,
        50,
        64,
    ):
        raise ValueError(
            "Wind probability threshold "
            "must be 34, 50, or 64 kt."
        )

    ranked = []

    for name, variable in (
        dataset.data_vars.items()
    ):
        score = _variable_score(
            name,
            variable,
            threshold_kt,
        )

        if score:
            ranked.append(
                (
                    score,
                    name,
                )
            )

    ranked.sort(
        reverse=True
    )

    if not ranked:
        raise KeyError(
            "Could not identify a "
            f"{threshold_kt}-kt probability "
            "variable."
        )

    best_score, best_name = (
        ranked[0]
    )

    # Require an actual threshold match,
    # not merely the word "probability".
    if best_score < 20:
        raise KeyError(
            "Probability variables exist, "
            f"but none clearly identifies "
            f"{threshold_kt} kt."
        )

    return best_name


# ============================================================
# COORDINATE DISCOVERY
# ============================================================

def _find_coordinate(
    dataset,
    candidates,
):
    lowered = {
        str(name).lower(): name
        for name
        in dataset.coords
    }

    for candidate in candidates:

        if candidate in lowered:
            return lowered[
                candidate
            ]

    for name in dataset.coords:

        text = str(
            name
        ).lower()

        for candidate in candidates:

            if candidate in text:
                return name

    return None


def find_lat_lon(
    dataset,
):
    lat_name = _find_coordinate(
        dataset,
        (
            "lat",
            "latitude",
        ),
    )

    lon_name = _find_coordinate(
        dataset,
        (
            "lon",
            "longitude",
        ),
    )

    if (
        lat_name is None
        or
        lon_name is None
    ):
        raise KeyError(
            "Could not identify latitude/"
            "longitude coordinates in "
            "probability dataset."
        )

    return (
        lat_name,
        lon_name,
    )


# ============================================================
# FORECAST-HOUR SELECTION
# ============================================================

def _select_forecast_hour(
    variable,
    forecast_hour,
):
    forecast_hour = int(
        forecast_hour
    )

    for dim in variable.dims:

        name = str(
            dim
        ).lower()

        if name in (
            "forecast_hour",
            "forecast_hours",
            "fhr",
            "lead",
            "lead_time",
            "step",
            "time",
        ):

            coordinate = (
                variable.coords.get(
                    dim
                )
            )

            if coordinate is None:
                continue

            values = np.asarray(
                coordinate.values
            )

            # Numeric forecast-hour coordinate.
            if np.issubdtype(
                values.dtype,
                np.number,
            ):
                index = int(
                    np.argmin(
                        np.abs(
                            values.astype(
                                float
                            )
                            -
                            forecast_hour
                        )
                    )
                )

                return variable.isel(
                    {
                        dim: index
                    }
                )

            # Timedelta coordinate.
            if np.issubdtype(
                values.dtype,
                np.timedelta64,
            ):
                hours = (
                    values
                    /
                    np.timedelta64(
                        1,
                        "h",
                    )
                ).astype(
                    float
                )

                index = int(
                    np.argmin(
                        np.abs(
                            hours
                            -
                            forecast_hour
                        )
                    )
                )

                return variable.isel(
                    {
                        dim: index
                    }
                )

    return variable


# ============================================================
# FILE OPENING
# ============================================================

_OPEN_DATASETS = {}


def _close_cached_datasets():
    for dataset in list(
        _OPEN_DATASETS.values()
    ):
        try:
            dataset.close()
        except Exception:
            pass

    _OPEN_DATASETS.clear()


atexit.register(
    _close_cached_datasets
)


def _open_dataset(
    path,
):
    """
    Open the native probability dataset efficiently.

    Normal decoded NetCDF files stay open for the lifetime of
    this worker process. Xarray remains lazy and does not cache
    full arrays in memory.

    Compressed .nc.gz inputs retain the compatibility path and
    are treated as temporary one-shot datasets.
    """
    path = Path(
        path
    )

    name = path.name.lower()

    if name.endswith(
        ".nc.gz"
    ):
        temporary = tempfile.NamedTemporaryFile(
            suffix=".nc",
            delete=False,
        )

        temporary.close()

        temp_path = Path(
            temporary.name
        )

        with gzip.open(
            path,
            "rb",
        ) as source:
            with temp_path.open(
                "wb"
            ) as target:
                while True:
                    chunk = source.read(
                        8 * 1024 * 1024
                    )

                    if not chunk:
                        break

                    target.write(
                        chunk
                    )

        dataset = xr.open_dataset(
            temp_path,
            cache=False,
        )

        dataset.attrs[
            "_masswx_temp_path"
        ] = str(
            temp_path
        )

        dataset.attrs[
            "_masswx_persistent"
        ] = False

        return dataset

    resolved = str(
        path.resolve()
    )

    try:
        mtime_ns = (
            path.stat().st_mtime_ns
        )
    except OSError:
        mtime_ns = 0

    key = (
        resolved,
        mtime_ns,
    )

    dataset = (
        _OPEN_DATASETS.get(
            key
        )
    )

    if dataset is not None:
        return dataset

    # Remove an older cached handle for the same path if the
    # file was replaced between cycles.
    for old_key in list(
        _OPEN_DATASETS
    ):
        if (
            old_key[0]
            ==
            resolved
            and
            old_key
            !=
            key
        ):
            try:
                _OPEN_DATASETS[
                    old_key
                ].close()
            except Exception:
                pass

            del _OPEN_DATASETS[
                old_key
            ]

    dataset = xr.open_dataset(
        path,
        cache=False,
    )

    dataset.attrs[
        "_masswx_persistent"
    ] = True

    _OPEN_DATASETS[
        key
    ] = dataset

    return dataset


# ============================================================
# PUBLIC PARSER
# ============================================================

def parse_probability_field(
    path,
    *,
    threshold_kt,
    forecast_hour,
):
    dataset = _open_dataset(
        path
    )

    try:
        variable_name = (
            find_probability_variable(
                dataset,
                threshold_kt,
            )
        )

        variable = dataset[
            variable_name
        ]

        variable = (
            _select_forecast_hour(
                variable,
                forecast_hour,
            )
        )

        lat_name, lon_name = (
            find_lat_lon(
                dataset
            )
        )

        # Remove remaining singleton
        # dimensions where safe.
        variable = variable.squeeze(
            drop=True
        )

        values = np.asarray(
            variable.values,
            dtype=float,
        )

        latitude = np.asarray(
            dataset[
                lat_name
            ].values,
            dtype=float,
        )

        longitude = np.asarray(
            dataset[
                lon_name
            ].values,
            dtype=float,
        )

        units = variable.attrs.get(
            "units"
        )

        # Normalize fractions to percent.
        finite = values[
            np.isfinite(
                values
            )
        ]

        if (
            finite.size
            and
            np.nanmax(
                finite
            )
            <= 1.01
        ):
            values = (
                values
                *
                100.0
            )

            units = "%"

        return ProbabilityField(
            probability=values,
            latitude=latitude,
            longitude=longitude,
            variable=variable_name,
            threshold_kt=int(
                threshold_kt
            ),
            forecast_hour=int(
                forecast_hour
            ),
            units=units,
        )

    finally:
        temporary = (
            dataset.attrs.get(
                "_masswx_temp_path"
            )
        )

        persistent = bool(
            dataset.attrs.get(
                "_masswx_persistent",
                False,
            )
        )

        if not persistent:
            dataset.close()

        if temporary:
            try:
                Path(
                    temporary
                ).unlink()
            except FileNotFoundError:
                pass
