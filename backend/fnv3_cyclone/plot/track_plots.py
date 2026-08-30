from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from fnv3_cyclone.regions import (
    DEFAULT_BASIN,
    get_basin,
)

from fnv3_cyclone.tracks.track_utils import (
    wind_bin,
)


# ============================================================
# WIND COLORS
# ============================================================

WIND_COLORS = {
    20: "#9E9E9E",
    30: "#46D9D9",
    40: "#1696F7",
    50: "#1464F4",
    60: "#12D83B",
    70: "#7BE000",
    80: "#E5E500",
    90: "#FFB000",
    100: "#FF7300",
    110: "#FF3030",
    120: "#FF1688",
    130: "#E318E8",
    140: "#A000D0",
}


# ============================================================
# GENERIC VALUE ACCESS
# ============================================================

def _value(point, name, default=None):
    if isinstance(point, dict):
        return point.get(name, default)

    return getattr(point, name, default)


# ============================================================
# TRACK GROUPING
# ============================================================

def _group_tracks(tracks):
    """
    Group WeatherNext Cyclones points into individual tracks.

    IMPORTANT:
    Cyclogenesis/unpaired data can contain multiple independent
    systems for a single ensemble member. Therefore member alone
    is NOT a unique track identifier.

    Unique track:
        (system_id, member)
    """

    grouped = {}

    for point in tracks:
        system_id = _value(
            point,
            "system_id",
        )

        member = _value(
            point,
            "member",
        )

        if system_id is None or member is None:
            continue

        key = (
            str(system_id),
            int(member),
        )

        grouped.setdefault(
            key,
            [],
        ).append(point)

    for key in grouped:
        grouped[key].sort(
            key=lambda p: _value(
                p,
                "forecast_hour",
                0,
            )
        )

    return grouped


# ============================================================
# MAP
# ============================================================

def _add_high_resolution_map(ax):
    """
    Natural Earth 10m map features.
    """

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
        linewidth=0.35,
        zorder=19,
    )


# ============================================================
# TRACK SEGMENTS
# ============================================================

def _plot_member_track(
    ax,
    points,
    transform,
    linewidth=1.05,
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

        # Do not connect tracks across the dateline with a
        # giant line across the entire map.
        if abs(float(lon2) - float(lon1)) > 180:
            continue

        ax.plot(
            [lon1, lon2],
            [lat1, lat2],
            color=WIND_COLORS[
                wind_bin(wind)
            ],
            linewidth=linewidth,
            alpha=0.82,
            transform=transform,
            solid_capstyle="round",
            zorder=7,
        )


# ============================================================
# 6-HOUR TRACK POINTS
# ============================================================

def _plot_track_points(
    ax,
    points,
    transform,
):
    for point in points:
        lon = _value(
            point,
            "longitude",
        )

        lat = _value(
            point,
            "latitude",
        )

        wind = _value(
            point,
            "max_wind_kt",
            20,
        )

        if lon is None or lat is None:
            continue

        ax.scatter(
            [lon],
            [lat],
            s=5,
            color=WIND_COLORS[
                wind_bin(wind)
            ],
            transform=transform,
            zorder=8,
        )


# ============================================================
# FINAL LOW MARKER
# ============================================================

def _plot_low_marker(
    ax,
    point,
    transform,
    show_pressure=True,
):
    lon = _value(
        point,
        "longitude",
    )

    lat = _value(
        point,
        "latitude",
    )

    pressure = _value(
        point,
        "mslp_hpa",
    )

    wind = _value(
        point,
        "max_wind_kt",
        20,
    )

    if lon is None or lat is None:
        return

    color = WIND_COLORS[
        wind_bin(wind)
    ]

    ax.text(
        lon,
        lat,
        "L",
        color=color,
        fontsize=10,
        fontweight="bold",
        ha="center",
        va="center",
        transform=transform,
        zorder=10,
    )

    if show_pressure and pressure is not None:
        try:
            pressure_text = str(
                int(
                    round(
                        float(pressure)
                    )
                )
            )
        except (TypeError, ValueError):
            pressure_text = str(
                pressure
            )

        ax.text(
            lon + 0.45,
            lat - 0.45,
            pressure_text,
            fontsize=6.5,
            color="black",
            ha="left",
            va="top",
            transform=transform,
            zorder=10,
        )


# ============================================================
# WIND LEGEND
# ============================================================

def _add_wind_legend(ax):
    handles = []

    for wind in sorted(
        WIND_COLORS
    ):
        handles.append(
            Line2D(
                [0],
                [0],
                color=WIND_COLORS[
                    wind
                ],
                linewidth=6,
                label=str(wind),
            )
        )

    legend = ax.legend(
        handles=handles,
        title="Maximum Wind (kt)",
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

    legend.set_zorder(
        100
    )


# ============================================================
# MAIN TRACK PLOT
# ============================================================

def plot_cyclone_tracks(
    tracks,
    output_file,
    title="WeatherNext Cyclones Operational",
    subtitle=None,
    basin=DEFAULT_BASIN,
    extent=None,
    mark_final_lows=False,
    label_pressures=False,
    plot_points=True,
    dpi=220,
):
    """
    Plot the full WeatherNext Cyclones unpaired/cyclogenesis
    ensemble.

    Each (system_id, member) pair is treated as an independent
    track. This prevents unrelated model-generated storms from
    being connected together.
    """

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

    members = {
        key[1]
        for key in grouped
    }

    systems = {
        key[0]
        for key in grouped
    }

    member_count = len(
        members
    )

    system_count = len(
        systems
    )

    track_count = len(
        grouped
    )

    basin_config = get_basin(
        basin
    )

    if extent is None:
        extent = basin_config[
            "extent"
        ]

    basin_name = basin_config[
        "name"
    ]

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

    _add_high_resolution_map(
        ax
    )

    # --------------------------------------------------------
    # Plot every independent model track.
    # --------------------------------------------------------

    for (
        system_id,
        member,
    ), member_points in grouped.items():

        _plot_member_track(
            ax=ax,
            points=member_points,
            transform=projection,
        )

        if plot_points:
            _plot_track_points(
                ax=ax,
                points=member_points,
                transform=projection,
            )

        if (
            mark_final_lows
            and member_points
        ):
            _plot_low_marker(
                ax=ax,
                point=member_points[-1],
                transform=projection,
                show_pressure=label_pressures,
            )

    # --------------------------------------------------------
    # Titles
    # --------------------------------------------------------

    display_title = (
        f"{title} | "
        f"{member_count} members"
    )

    ax.set_title(
        display_title,
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
        0.0,
        -0.025,
        (
            f"{system_count} systems | "
            f"{track_count} ensemble tracks | "
            "Unpaired cyclogenesis"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
    )

    ax.text(
        1.0,
        -0.025,
        "Data: Google DeepMind Weather Lab",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
    )

    _add_wind_legend(
        ax
    )

    # Fill the output canvas reliably. Cartopy GeoAxes frequently
    # cannot satisfy tight_layout(), producing a tiny centered map.
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

    plt.close(
        fig
    )

    print(
        f"Saved WeatherNext cyclone plot: {output_file}"
    )

    print(
        f"Basin: {basin_name}"
    )

    print(
        f"Members represented: {member_count}"
    )

    print(
        f"Systems represented: {system_count}"
    )

    print(
        f"Independent tracks: {track_count}"
    )


# ============================================================
# DENSITY
# ============================================================

def plot_track_density(
    density,
    output_file,
    title="WeatherNext Cyclones | Track Density",
):
    raise NotImplementedError(
        "Track-density plotting is not configured yet."
    )
