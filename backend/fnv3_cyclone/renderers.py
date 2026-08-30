from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from shared.cyclone_renderer import (
    register_renderer,
)

from fnv3_cyclone.plot.track_plots import (
    plot_cyclone_tracks,
)

from fnv3_cyclone.process.generalized_parser import (
    parse_generalized_tracks,
)


FNV3_RENDERER_PRODUCTS = (
    "track",
    "intensity",
    "instantaneous_track",
    "instantaneous_intensity",
)


def _read_tracks_uncached(source):
    """
    Read an FNV3 cyclone source using the parser appropriate
    for the actual source format.

    Operational WeatherLab FNV3 uses ATCF text.

    Legacy generalized sources may still be JSON/dictionaries.
    """

    import json
    from pathlib import Path

    from fnv3_cyclone.process.generalized_parser import (
        parse_generalized_tracks,
        parse_weatherlab_atcf,
    )

    source = Path(source)

    if not source.exists():
        raise FileNotFoundError(source)

    text = source.read_text(
        encoding="utf-8",
        errors="replace",
    )

    stripped = text.lstrip()

    # WeatherLab operational ATCF A-deck.
    if (
        source.suffix.lower() == ".txt"
        or "atcf" in source.name.lower()
        or "a_deck" in source.name.lower()
    ):
        return parse_weatherlab_atcf(text)

    # Legacy generalized JSON source.
    if stripped.startswith("{") or stripped.startswith("["):
        payload = json.loads(text)
        return parse_generalized_tracks(payload)

    # Real operational FNV3 text is the safer fallback.
    return parse_weatherlab_atcf(text)


@lru_cache(maxsize=4)
def _read_tracks_cached(source_string, mtime_ns):
    return _read_tracks_uncached(
        Path(source_string)
    )


def _read_tracks(source):
    source = Path(source)

    return _read_tracks_cached(
        str(source.resolve()),
        source.stat().st_mtime_ns,
    )

def _tracks_through_hour(
    tracks,
    forecast_hour,
):
    """
    Keep only points valid through the requested forecast hour.

    Track dictionaries from different FNV3 sources have used several
    names for forecast lead. Preserve a point when no lead-time field
    exists rather than silently deleting valid guidance.
    """

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



def _tracks_at_hour(
    tracks,
    forecast_hour,
):
    """
    Return only cyclone points valid at the selected forecast hour.

    Used by instantaneous products. Normal track products remain
    cumulative through the selected forecast hour.
    """
    fh = int(forecast_hour)

    return [
        point
        for point in tracks
        if int(
            getattr(
                point,
                "forecast_hour",
                -999,
            )
        ) == fh
    ]

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
        basin = {
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
    }.get(request.region, request.region)
        extent = None

    return (
        basin,
        extent,
    )


from fnv3_cyclone.plot.diagnostic_plots import (
    plot_mslp_spaghetti,
    plot_intensity_distribution,
)

def _title(
    request,
):
    return (
        "FNV3 Cyclone Ensemble"
    )


def _subtitle(
    request,
):
    return (
        f"{request.date} "
        f"{request.hour:02d}Z  •  "
        f"F{request.forecast_hour:03d}"
    )


def render_fnv3_track(
    *,
    source,
    bundle,
    request,
    output_path,
):
    tracks = _read_tracks(
        source
    )

    tracks = _tracks_through_hour(
        tracks,
        request.forecast_hour,
    )

    basin, extent = _region_values(
        request
    )

    plot_cyclone_tracks(
        tracks=tracks,
        output_file=output_path,
        title=_title(
            request
        ),
        subtitle=_subtitle(
            request
        ),
        basin=basin,
        extent=extent,
        mark_final_lows=True,
        label_pressures=True,
        plot_points=True,
        dpi=150,
    )

    return output_path


def render_fnv3_instantaneous_track(
    *,
    source,
    bundle,
    request,
    output_path,
):
    tracks = _read_tracks(
        source
    )

    tracks = _tracks_at_hour(
        tracks,
        request.forecast_hour,
    )

    basin, extent = _region_values(
        request
    )

    plot_cyclone_tracks(
        tracks=tracks,
        output_file=output_path,
        title=_title(request),
        subtitle=_subtitle(request),
        basin=basin,
        extent=extent,
        mark_final_lows=True,
        label_pressures=True,
        plot_points=True,
        dpi=150,
    )

    return output_path


def render_fnv3_intensity(
    *,
    source,
    bundle,
    request,
    output_path,
):
    # The existing FNV3 track plot already encodes cyclone
    # intensity along the member tracks. Until a dedicated
    # intensity-only plotter is added, preserve the real
    # model visualization rather than fabricating a new one.

    return render_fnv3_track(
        source=source,
        bundle=bundle,
        request=request,
        output_path=output_path,
    )




def render_fnv3_mslp_spaghetti(
    *,
    source,
    bundle,
    request,
    output_path,
):
    tracks = _read_tracks(
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
            "FNV3 Cyclone Ensemble | "
            "MSLP / Intensity Spaghetti"
        ),
        subtitle=_subtitle(request),
        extent=extent,
        dpi=150,
    )

    return output_path


def render_fnv3_intensity_distribution(
    *,
    source,
    bundle,
    request,
    output_path,
):
    tracks = _read_tracks(
        source
    )

    plot_intensity_distribution(
        tracks=tracks,
        forecast_hour=request.forecast_hour,
        output_file=output_path,
        title=(
            "FNV3 Cyclone Ensemble | "
            "Intensity Distribution"
        ),
        subtitle=_subtitle(request),
        dpi=150,
    )

    return output_path


def register_fnv3_renderers():

    register_renderer(
        "fnv3",
        "track",
        render_fnv3_track,
    )

    register_renderer(
        "fnv3",
        "intensity",
        render_fnv3_intensity,
    )

    register_renderer(
        "fnv3",
        "instantaneous_track",
        render_fnv3_instantaneous_track,
    )

    register_renderer(
        "fnv3",
        "instantaneous_intensity",
        render_fnv3_instantaneous_track,
    )

    register_renderer(
        "fnv3",
        "mslp_spaghetti",
        render_fnv3_mslp_spaghetti,
    )

    register_renderer(
        "fnv3",
        "intensity_distribution",
        render_fnv3_intensity_distribution,
    )



register_fnv3_renderers()

