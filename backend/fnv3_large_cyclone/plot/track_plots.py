from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

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


def _value(point, name, default=None):
    if isinstance(point, dict):
        return point.get(name, default)

    return getattr(point, name, default)


def _group_tracks(tracks):
    grouped = {}

    for point in tracks:
        member = _value(point, "member")

        if member is None:
            continue

        grouped.setdefault(
            int(member),
            [],
        ).append(point)

    for member in grouped:
        grouped[member].sort(
            key=lambda p: _value(
                p,
                "forecast_hour",
                0,
            )
        )

    return grouped


def _add_high_resolution_map(ax):
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

    ax.set_facecolor("white")

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
        linewidth=0.55,
        zorder=20,
    )

    ax.add_feature(
        states,
        linewidth=0.30,
        zorder=19,
    )


def _plot_member_track(
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
        lon1 = _value(p1, "longitude")
        lat1 = _value(p1, "latitude")

        lon2 = _value(p2, "longitude")
        lat2 = _value(p2, "latitude")

        wind = _value(
            p2,
            "max_wind_kt",
            20,
        )

        if None in (
            lon1,
            lat1,
            lon2,
            lat2,
        ):
            continue

        ax.plot(
            [lon1, lon2],
            [lat1, lat2],
            color=WIND_COLORS[
                wind_bin(wind)
            ],
            linewidth=0.42,
            alpha=0.30,
            transform=transform,
            solid_capstyle="round",
            zorder=6,
        )


def _add_wind_legend(ax):
    handles = []

    for wind in sorted(WIND_COLORS):
        handles.append(
            Line2D(
                [0],
                [0],
                color=WIND_COLORS[wind],
                linewidth=6,
                label=str(wind),
            )
        )

    legend = ax.legend(
        handles=handles,
        title="Tracks  Max Wind (kt)",
        loc="upper right",
        ncol=7,
        fontsize=7,
        title_fontsize=9,
        frameon=True,
        framealpha=1.0,
        handlelength=1.5,
        columnspacing=0.7,
        borderpad=0.5,
    )

    legend.set_zorder(100)


def plot_fnv3_large_tracks(
    tracks,
    output_file,
    title="FNV3-L | Tropical Cyclone Tracks",
    subtitle=None,
    basin=DEFAULT_BASIN,
    extent=None,
    dpi=220,
):
    output_file = Path(output_file)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    grouped = _group_tracks(tracks)

    member_count = len(grouped)

    basin_config = get_basin(basin)

    if extent is None:
        extent = basin_config["extent"]

    basin_name = basin_config["name"]

    projection = ccrs.PlateCarree()

    fig = plt.figure(
        figsize=(16, 10),
    )

    ax = plt.axes(
        projection=projection,
    )

    ax.set_extent(
        extent,
        crs=projection,
    )

    _add_high_resolution_map(ax)

    for member_points in grouped.values():
        _plot_member_track(
            ax=ax,
            points=member_points,
            transform=projection,
        )

    ax.set_title(
        f"{title} ({member_count} members)",
        loc="right",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )

    ax.text(
        0.0,
        1.005,
        basin_name,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9,
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

    _add_wind_legend(ax)

    fig.subplots_adjust(
        left=0.035,
        right=0.965,
        bottom=0.055,
        top=0.90,
    )

    fig.savefig(
        output_file,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(fig)

    print(
        f"Saved FNV3-L track plot: {output_file}"
    )

    print(
        f"Basin: {basin_name}"
    )

    print(
        f"Members plotted: {member_count}"
    )
