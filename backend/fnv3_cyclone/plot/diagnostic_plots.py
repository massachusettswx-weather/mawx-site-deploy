
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def _value(point, key):
    if isinstance(point, dict):
        return point.get(key)

    return getattr(
        point,
        key,
        None,
    )


def _projection():
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    return ccrs, cfeature


def _points_through_hour(
    tracks,
    forecast_hour,
):
    result = []

    for item in tracks:

        points = (
            item.get("points")
            if isinstance(item, dict)
            else None
        )

        if isinstance(points, list):
            source_points = points
        else:
            source_points = [item]

        for point in source_points:

            lead = _value(
                point,
                "forecast_hour",
            )

            try:
                lead = int(float(lead))
            except (TypeError, ValueError):
                continue

            if lead <= int(forecast_hour):
                result.append(point)

    return result


def plot_mslp_spaghetti(
    *,
    tracks,
    forecast_hour,
    output_file,
    title,
    subtitle,
    extent=None,
    dpi=150,
):
    """
    Ensemble cyclone MSLP/intensity spaghetti.

    Each member/system trajectory is plotted using its
    actual tracker MSLP values. This is cyclone-center
    pressure guidance, not a gridded synoptic MSLP field.
    """

    ccrs, cfeature = _projection()

    points = _points_through_hour(
        tracks,
        forecast_hour,
    )

    grouped = defaultdict(list)

    for point in points:

        member = _value(
            point,
            "member",
        )

        system = (
            _value(point, "system_id")
            or
            _value(point, "storm_id")
            or
            "system"
        )

        grouped[
            (
                str(system),
                str(member),
            )
        ].append(point)

    projection = ccrs.PlateCarree()

    fig = plt.figure(
        figsize=(16, 9)
    )

    ax = fig.add_subplot(
        1,
        1,
        1,
        projection=projection,
    )

    if extent:
        ax.set_extent(
            extent,
            crs=projection,
        )
    else:
        ax.set_global()

    ax.add_feature(
        cfeature.LAND,
        zorder=0,
    )

    ax.add_feature(
        cfeature.COASTLINE,
        linewidth=0.7,
        zorder=4,
    )

    ax.add_feature(
        cfeature.BORDERS,
        linewidth=0.4,
        zorder=4,
    )

    plotted = 0

    for member_points in grouped.values():

        member_points.sort(
            key=lambda p: int(
                float(
                    _value(
                        p,
                        "forecast_hour",
                    )
                    or 0
                )
            )
        )

        lons = []
        lats = []
        pressures = []

        for point in member_points:

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

            if (
                lon is None
                or lat is None
                or pressure is None
            ):
                continue

            try:
                lons.append(float(lon))
                lats.append(float(lat))
                pressures.append(
                    float(pressure)
                )
            except (TypeError, ValueError):
                continue

        if not lons:
            continue

        # Pressure controls line darkness.
        mean_pressure = np.nanmean(
            pressures
        )

        normalized = np.clip(
            (
                1020.0
                - mean_pressure
            )
            / 100.0,
            0.0,
            1.0,
        )

        ax.plot(
            lons,
            lats,
            linewidth=0.7
            + normalized * 1.1,
            alpha=0.40,
            transform=projection,
            zorder=2,
        )

        # Mark current member position.
        ax.scatter(
            lons[-1],
            lats[-1],
            s=9,
            transform=projection,
            zorder=3,
        )

        plotted += 1

    ax.set_title(
        title,
        loc="left",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title(
        subtitle,
        loc="right",
        fontsize=9,
    )

    ax.text(
        0.01,
        0.01,
        (
            f"{plotted} cyclone/member trajectories | "
            "Line weight increases with lower MSLP"
        ),
        transform=ax.transAxes,
        fontsize=8,
    )

    output_file = Path(
        output_file
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_file,
        dpi=dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    return output_file


def plot_intensity_distribution(
    *,
    tracks,
    forecast_hour,
    output_file,
    title,
    subtitle,
    dpi=150,
):
    """
    Distribution of tracker maximum winds at one lead time.
    """

    points = _points_through_hour(
        tracks,
        forecast_hour,
    )

    winds = []

    for point in points:

        lead = _value(
            point,
            "forecast_hour",
        )

        try:
            if int(float(lead)) != int(
                forecast_hour
            ):
                continue
        except (TypeError, ValueError):
            continue

        wind = _value(
            point,
            "max_wind_kt",
        )

        try:
            winds.append(
                float(wind)
            )
        except (TypeError, ValueError):
            pass

    fig = plt.figure(
        figsize=(16, 9)
    )

    ax = fig.add_subplot(
        1,
        1,
        1,
    )

    if winds:
        bins = np.arange(
            0,
            max(170, int(max(winds)) + 10),
            5,
        )

        ax.hist(
            winds,
            bins=bins,
        )

        ax.axvline(
            np.mean(winds),
            linewidth=1.5,
            label=(
                f"Mean {np.mean(winds):.0f} kt"
            ),
        )

        ax.legend()

    ax.set_xlabel(
        "Maximum sustained wind (kt)"
    )

    ax.set_ylabel(
        "Cyclone / member count"
    )

    ax.set_title(
        title,
        loc="left",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title(
        subtitle,
        loc="right",
        fontsize=9,
    )

    output_file = Path(
        output_file
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_file,
        dpi=dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    return output_file
