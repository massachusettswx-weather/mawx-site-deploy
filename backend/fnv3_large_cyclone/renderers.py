from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from shared.cyclone_renderer import (
    register_renderer,
)

from fnv3_large_cyclone.plot.track_plots import (
    plot_fnv3_large_tracks,
)

from fnv3_large_cyclone.plot.mean_track_plots import (
    plot_fnv3_large_mean_tracks,
)

from fnv3_large_cyclone.plot.probability_plots import (
    plot_wind_probability,
)


from fnv3_large_cyclone.process.mean_parser import (
    parse_weatherlab_paired_mean_file,
)


from fnv3_cyclone.plot.diagnostic_plots import (
    plot_mslp_spaghetti,
    plot_intensity_distribution,
)

def _region_values(
    request,
):
    from shared.cyclone_regions import (
        get_cyclone_region,
    )

    config = get_cyclone_region(
        request.region
    )

    if isinstance(
        config,
        dict,
    ):
        basin = (
            config.get("basin")
            or
            request.region
        )

        extent = (
            config.get("extent")
            or
            config.get("bounds")
        )

    else:
        basin = request.region
        extent = None

    return (
        basin,
        extent,
    )


def _subtitle(
    request,
):
    return (
        f"{request.date} "
        f"{request.hour:02d}Z  •  "
        f"F{request.forecast_hour:03d}"
    )




@lru_cache(maxsize=128)
def _load_native_probability_uncached(
    probability_path,
    forecast_hour,
):
    """
    Read the native Weather Lab cumulative
    cyclogenesis-probability NetCDF.

    Variable names are discovered rather than
    hard-coded wherever possible.
    """

    import xarray as xr
    import numpy as np

    dataset = xr.open_dataset(
        probability_path
    )

    try:

        # ----------------------------------------
        # Coordinate discovery
        # ----------------------------------------

        lat_name = next(
            (
                name
                for name in (
                    "latitude",
                    "lat",
                    "y",
                )
                if (
                    name in dataset.coords
                    or name in dataset.variables
                )
            ),
            None,
        )

        lon_name = next(
            (
                name
                for name in (
                    "longitude",
                    "lon",
                    "x",
                )
                if (
                    name in dataset.coords
                    or name in dataset.variables
                )
            ),
            None,
        )

        if (
            lat_name is None
            or lon_name is None
        ):
            raise RuntimeError(
                "Could not identify probability "
                "latitude/longitude coordinates"
            )


        # ----------------------------------------
        # Find probability variable
        # ----------------------------------------

        candidates = []

        for name, variable in (
            dataset.data_vars.items()
        ):

            lower = name.lower()

            if (
                "prob" in lower
                or
                "cyclogen" in lower
            ):
                candidates.append(
                    name
                )

        if not candidates:
            raise RuntimeError(
                "No native probability variable "
                "found in FNV3-L NetCDF"
            )

        variable_name = candidates[0]

        probability = dataset[
            variable_name
        ]


        # ----------------------------------------
        # Forecast-hour coordinate
        # ----------------------------------------

        lead_dimension = None

        for candidate in (
            "forecast_hour",
            "lead_time",
            "lead",
            "step",
            "time",
        ):

            if candidate in probability.dims:
                lead_dimension = candidate
                break


        if lead_dimension is not None:

            coordinate = dataset[
                lead_dimension
            ]

            values = np.asarray(
                coordinate.values
            )

            requested = int(
                forecast_hour
            )

            # Handle timedelta coordinates.
            if np.issubdtype(
                values.dtype,
                np.timedelta64,
            ):

                hours = (
                    values
                    / np.timedelta64(
                        1,
                        "h",
                    )
                ).astype(float)

            else:

                try:
                    hours = values.astype(
                        float
                    )

                except Exception:
                    hours = np.arange(
                        len(values)
                    ) * 6.0


            index = int(
                np.argmin(
                    np.abs(
                        hours
                        - requested
                    )
                )
            )

            probability = (
                probability.isel(
                    {
                        lead_dimension:
                            index
                    }
                )
            )


        # Remove singleton dimensions.
        probability = (
            probability.squeeze()
        )


        latitude = np.asarray(
            dataset[
                lat_name
            ].values
        )

        longitude = np.asarray(
            dataset[
                lon_name
            ].values
        )

        field = np.asarray(
            probability.values,
            dtype=float,
        )


        # Convert 0–1 probabilities to percent.
        finite = field[
            np.isfinite(field)
        ]

        if (
            finite.size
            and
            np.nanmax(finite) <= 1.01
        ):
            field = field * 100.0


        return (
            field,
            latitude,
            longitude,
            variable_name,
        )

    finally:
        dataset.close()

@lru_cache(maxsize=4)

@lru_cache(maxsize=4)
def _load_native_probability_cached(
    probability_path_string,
    forecast_hour,
):
    return _load_native_probability_uncached(
        Path(probability_path_string),
        forecast_hour,
    )


def _load_native_probability(
    probability_path,
    forecast_hour,
):
    probability_path = Path(probability_path)

    return _load_native_probability_cached(
        str(probability_path.resolve()),
        int(forecast_hour),
    )

def _load_ensemble_tracks_uncached(
    source,
):
    from pathlib import Path
    from fnv3_large_cyclone.download.fnv3_large_downloader import (
        parse_weatherlab_cyclogenesis_file,
    )

    source = Path(source)

    if not source.exists():
        raise FileNotFoundError(source)

    # Operational FNV3-L ensemble input is the real
    # WeatherLab cyclogenesis CSV, not the legacy JSON payload.
    return parse_weatherlab_cyclogenesis_file(
        source
    )



@lru_cache(maxsize=2)
def _load_ensemble_tracks_cached(source_string, mtime_ns):
    return _load_ensemble_tracks_uncached(
        Path(source_string)
    )


def _load_ensemble_tracks(source):
    source = Path(source)

    return _load_ensemble_tracks_cached(
        str(source.resolve()),
        source.stat().st_mtime_ns,
    )

def _tracks_through_hour(
    tracks,
    forecast_hour,
):
    forecast_hour = int(
        forecast_hour
    )

    result = []

    for track in tracks:

        if not isinstance(
            track,
            dict,
        ):
            result.append(
                track
            )
            continue

        points = track.get(
            "points"
        )

        if not isinstance(
            points,
            list,
        ):
            result.append(
                track
            )
            continue

        filtered = []

        for point in points:

            if not isinstance(
                point,
                dict,
            ):
                filtered.append(
                    point
                )
                continue

            lead = None

            for key in (
                "forecast_hour",
                "forecastHour",
                "fhr",
                "tau",
                "lead",
                "lead_hour",
                "lead_hours",
            ):
                if key in point:
                    lead = point[
                        key
                    ]
                    break

            if lead is None:
                filtered.append(
                    point
                )
                continue

            try:
                lead = int(
                    float(lead)
                )
            except (
                TypeError,
                ValueError,
            ):
                filtered.append(
                    point
                )
                continue

            if lead <= forecast_hour:
                filtered.append(
                    point
                )

        if not filtered:
            continue

        copied = dict(
            track
        )

        copied[
            "points"
        ] = filtered

        result.append(
            copied
        )

    return result



def _tracks_at_hour(tracks, forecast_hour):
    fh = int(forecast_hour)

    return [
        point
        for point in tracks
        if int(
            getattr(point, "forecast_hour", -999)
        ) == fh
    ]

def render_fnv3_large_track(
    *,
    source,
    bundle,
    request,
    output_path,
):
    tracks = _load_ensemble_tracks(
        source
    )

    tracks = _tracks_through_hour(
        tracks,
        request.forecast_hour,
    )

    basin, extent = _region_values(
        request
    )

    plot_fnv3_large_tracks(
        tracks=tracks,
        output_file=output_path,
        title=(
            "FNV3-L 1000-Member "
            "Cyclone Ensemble"
        ),
        subtitle=_subtitle(
            request
        ),
        basin=basin,
        extent=extent,
        dpi=150,
    )

    return output_path



# FNV3L_CACHED_MEAN_TRACKS
@lru_cache(maxsize=4)
def _load_mean_tracks(
    source,
):
    return (
        _load_mean_tracks(source)
    )


def render_fnv3_large_mean_track(
    *,
    source,
    bundle,
    request,
    output_path,
):
    tracks = (
        _load_mean_tracks(source)
    )

    tracks = _tracks_through_hour(
        tracks,
        request.forecast_hour,
    )

    basin, extent = _region_values(
        request
    )

    plot_fnv3_large_mean_tracks(
        tracks=tracks,
        output_file=output_path,
        title=(
            "FNV3-L Ensemble Mean Track"
        ),
        subtitle=_subtitle(
            request
        ),
        basin=basin,
        extent=extent,
        dpi=150,
    )

    return output_path


def render_fnv3_large_intensity(
    *,
    source,
    bundle,
    request,
    output_path,
):
    return render_fnv3_large_track(
        source=source,
        bundle=bundle,
        request=request,
        output_path=output_path,
    )




def render_fnv3_large_mslp_spaghetti(
    *,
    source,
    bundle,
    request,
    output_path,
):
    tracks = _load_ensemble_tracks(
        source
    )

    basin, extent = _region_values(
        request
    )

    plot_mslp_spaghetti(
        tracks=tracks,
        forecast_hour=request.forecast_hour,
        output_file=output_path,
        title=(
            "FNV3-L 1000-Member | "
            "MSLP / Intensity Spaghetti"
        ),
        subtitle=_subtitle(request),
        extent=extent,
        dpi=150,
    )

    return output_path


def render_fnv3_large_intensity_distribution(
    *,
    source,
    bundle,
    request,
    output_path,
):
    tracks = _load_ensemble_tracks(
        source
    )

    plot_intensity_distribution(
        tracks=tracks,
        forecast_hour=request.forecast_hour,
        output_file=output_path,
        title=(
            "FNV3-L 1000-Member | "
            "Intensity Distribution"
        ),
        subtitle=_subtitle(request),
        dpi=150,
    )

    return output_path




def render_fnv3_large_cyclogenesis_probability(
    *,
    source,
    bundle,
    request,
    output_path,
):
    """
    Render the native Weather Lab cumulative
    cyclogenesis probability field.

    This does NOT derive probability from the
    track CSV.
    """

    probability_path = None

    # Prefer the complete download bundle.
    if isinstance(bundle, dict):
        probability_path = (
            bundle.get(
                "probability_path"
            )
        )

    # Some operational paths may expose
    # bundle attributes instead.
    if (
        probability_path is None
        and bundle is not None
    ):
        probability_path = getattr(
            bundle,
            "probability_path",
            None,
        )

    if probability_path is None:
        raise RuntimeError(
            "FNV3-L native probability "
            "NetCDF missing from source bundle"
        )


    (
        probability,
        latitude,
        longitude,
        variable_name,
    ) = _load_native_probability(
        probability_path,
        request.forecast_hour,
    )


    basin, extent = _region_values(
        request
    )


    # Existing plotter is generic despite its
    # historical function name. For this product
    # we explicitly title it cyclogenesis probability.
    plot_wind_probability(
        probability=probability,
        latitude=latitude,
        longitude=longitude,
        output_file=output_path,
        threshold_kt=0,
        title=(
            "FNV3-L 1000-Member | "
            "Cumulative Cyclogenesis Probability"
        ),
        subtitle=(
            _subtitle(request)
            + "  •  Native Weather Lab field"
        ),
        extent=extent,
        dpi=150,
    )


    return output_path

def register_fnv3_large_renderers():

    register_renderer(
        "fnv3_large",
        "track",
        render_fnv3_large_track,
    )

    register_renderer(
        "fnv3_large",
        "intensity",
        render_fnv3_large_intensity,
    )

    register_renderer(
        "fnv3_large",
        "instantaneous_track",
        render_fnv3_large_track,
    )

    register_renderer(
        "fnv3_large",
        "instantaneous_intensity",
        render_fnv3_large_intensity,
    )

    register_renderer(
        "fnv3_large",
        "mean_track",
        render_fnv3_large_mean_track,
    )

    register_renderer(
        "fnv3_large",
        "mslp_spaghetti",
        render_fnv3_large_mslp_spaghetti,
    )

    register_renderer(
        "fnv3_large",
        "intensity_distribution",
        render_fnv3_large_intensity_distribution,
    )



    register_renderer(
        "fnv3_large",
        "cyclogenesis_probability",
        render_fnv3_large_cyclogenesis_probability,
    )


register_fnv3_large_renderers()

