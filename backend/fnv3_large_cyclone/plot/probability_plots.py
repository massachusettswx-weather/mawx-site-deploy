from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def _get_projection_modules():
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        return (
            ccrs,
            cfeature,
        )

    except ImportError as exc:
        raise RuntimeError(
            "Cartopy is required for "
            "cyclone probability maps."
        ) from exc


def plot_wind_probability(
    *,
    probability,
    latitude,
    longitude,
    output_file,
    threshold_kt,
    title,
    subtitle,
    extent=None,
    dpi=150,
):
    ccrs, cfeature = (
        _get_projection_modules()
    )

    output_file = Path(
        output_file
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    probability = np.asarray(
        probability,
        dtype=float,
    )

    latitude = np.asarray(
        latitude,
        dtype=float,
    )

    longitude = np.asarray(
        longitude,
        dtype=float,
    )

    projection = (
        ccrs.PlateCarree()
    )

    figure = plt.figure(
        figsize=(
            12,
            8,
        )
    )

    ax = figure.add_subplot(
        1,
        1,
        1,
        projection=projection,
    )

    if extent is not None:
        ax.set_extent(
            extent,
            crs=projection,
        )

    else:
        ax.set_global()

    ax.add_feature(
        cfeature.LAND,
        zorder=1,
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

    levels = (
        1,
        5,
        10,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        100,
    )

    if (
        latitude.ndim == 1
        and
        longitude.ndim == 1
    ):
        lon_grid, lat_grid = (
            np.meshgrid(
                longitude,
                latitude,
            )
        )

    else:
        lat_grid = latitude
        lon_grid = longitude

    contour = ax.contourf(
        lon_grid,
        lat_grid,
        probability,
        levels=levels,
        extend="max",
        transform=projection,
        zorder=2,
    )

    colorbar = figure.colorbar(
        contour,
        ax=ax,
        orientation="horizontal",
        pad=0.045,
        fraction=0.05,
    )

    colorbar.set_label(
        (
            f"Probability of "
            f"≥{int(threshold_kt)} kt "
            f"winds (%)"
        )
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

    figure.savefig(
        output_file,
        dpi=dpi,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )

    return output_file
