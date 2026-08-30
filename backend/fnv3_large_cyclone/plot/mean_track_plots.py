from pathlib import Path

import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from fnv3_cyclone.plot.track_plots import (
    WIND_COLORS,
)

from fnv3_cyclone.regions import (
    DEFAULT_BASIN,
    get_basin,
)

from fnv3_cyclone.tracks.track_utils import (
    wind_bin,
)


def _value(
    point,
    name,
    default=None,
):
    if isinstance(
        point,
        dict,
    ):
        return point.get(
            name,
            default,
        )

    return getattr(
        point,
        name,
        default,
    )


def _group_tracks(
    tracks,
):
    grouped = {}

    for point in tracks:
        system_id = _value(
            point,
            "system_id",
        )

        if system_id is None:
            continue

        grouped.setdefault(
            str(system_id),
            [],
        ).append(
            point
        )

    for system_id in grouped:
        grouped[
            system_id
        ].sort(
            key=lambda p: (
                _value(
                    p,
                    "forecast_hour",
                    0,
                )
            )
        )

    return grouped


def _add_map(ax):
    land = cfeature.NaturalEarthFeature(
        "physical",
        "land",
        "10m",
        facecolor="white",
        edgecolor="none",
    )

    coastline = cfeature.NaturalEarthFeature(
        "physical",
        "coastline",
        "10m",
        facecolor="none",
        edgecolor="black",
    )

    borders = cfeature.NaturalEarthFeature(
        "cultural",
        "admin_0_boundary_lines_land",
        "10m",
        facecolor="none",
        edgecolor="black",
    )

    states = cfeature.NaturalEarthFeature(
        "cultural",
        "admin_1_states_provinces_lines",
        "10m",
        facecolor="none",
        edgecolor="black",
    )

    ax.set_facecolor(
        "white"
    )

    ax.add_feature(
        land,
        zorder=1,
    )

    ax.add_feature(
        coastline,
        linewidth=0.8,
        zorder=20,
    )

    ax.add_feature(
        borders,
        linewidth=0.5,
        zorder=20,
    )

    ax.add_feature(
        states,
        linewidth=0.28,
        zorder=19,
    )


def _plot_track(
    ax,
    points,
    transform,
):
    if len(points) < 2:
        return

    for p1, p2 in zip(
        points[:-1],
        points[1:],
    ):
        lon1 = _value(
            p1,
            "longitude",
        )
        lat1 = _value(
            p1,
            "latitude",
        )

        lon2 = _value(
            p2,
            "longitude",
        )
        lat2 = _value(
            p2,
            "latitude",
        )

        if None in (
            lon1,
            lat1,
            lon2,
            lat2,
        ):
            continue

        if (
            abs(
                float(lon2)
                - float(lon1)
            )
            > 180
        ):
            continue

        wind = _value(
            p2,
            "max_wind_kt",
            20,
        )

        ax.plot(
            [
                lon1,
                lon2,
            ],
            [
                lat1,
                lat2,
            ],
            color=(
                WIND_COLORS[
                    wind_bin(
                        wind
                    )
                ]
            ),
            linewidth=2.2,
            alpha=0.95,
            transform=transform,
            solid_capstyle="round",
            zorder=8,
        )

    # Put a small marker at the end of each
    # ensemble-mean track.
    last = points[-1]

    lon = _value(
        last,
        "longitude",
    )
    lat = _value(
        last,
        "latitude",
    )

    if (
        lon is not None
        and lat is not None
    ):
        ax.scatter(
            [lon],
            [lat],
            s=14,
            facecolor="white",
            edgecolor="black",
            linewidth=0.7,
            transform=transform,
            zorder=12,
        )


def plot_fnv3_large_mean_tracks(
    tracks,
    output_file,
    title=(
        "WeatherNext 2 Cyclones r2 | "
        "Large Ensemble Mean"
    ),
    subtitle=None,
    basin=DEFAULT_BASIN,
    extent=None,
    dpi=180,
):
    output_file = Path(
        output_file
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    grouped = _group_tracks(
        tracks
    )

    basin_config = get_basin(
        basin
    )

    if extent is None:
        extent = basin_config[
            "extent"
        ]

    projection = (
        ccrs.PlateCarree()
    )

    fig = plt.figure(
        figsize=(
            16,
            10,
        )
    )

    ax = plt.axes(
        projection=projection
    )

    ax.set_extent(
        extent,
        crs=projection,
    )

    _add_map(
        ax
    )

    for points in grouped.values():
        _plot_track(
            ax,
            points,
            projection,
        )

    ax.set_title(
        (
            f"{title} | "
            f"{len(grouped)} systems"
        ),
        loc="right",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )

    ax.text(
        0.0,
        1.005,
        basin_config["name"],
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        fontweight="bold",
    )

    if subtitle:
        ax.text(
            1.0,
            1.005,
            subtitle,
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
        )

    ax.text(
        1.0,
        -0.025,
        (
            "Data: Google DeepMind "
            "Weather Lab"
        ),
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
    )

    plt.tight_layout()

    fig.savefig(
        output_file,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(
        fig
    )

    print(
        "Saved FNV3-L ensemble mean:",
        output_file,
    )

    print(
        "Basin:",
        basin_config["name"],
    )

    print(
        "Mean systems:",
        len(grouped),
    )
