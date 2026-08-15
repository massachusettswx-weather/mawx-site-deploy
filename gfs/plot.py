from pathlib import Path

import numpy as np
import xarray as xr

import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.util import add_cyclic_point

from shared.regions import REGIONS


BASE_DIR = Path(__file__).parent

DPI = 120


def convert_longitudes(ds):
    ds = ds.assign_coords(
        longitude=(
            (ds.longitude + 180) % 360
        ) - 180
    )

    return ds.sortby(
        "longitude"
    )


def load_500mb_data(grib_path):
    """
    Open a forecast-hour GRIB only once.
    Load both global fields into memory.
    """

    print(
        "Opening GFS GRIB2 once..."
    )

    common = {
        "typeOfLevel": "isobaricInhPa",
        "level": 500,
    }

    height_ds = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {
                **common,
                "shortName": "gh",
            },
            "indexpath": "",
        },
    )

    vort_ds = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {
                **common,
                "shortName": "absv",
            },
            "indexpath": "",
        },
    )

    print(
        "Loading global 500-mb fields into memory..."
    )

    height_ds = convert_longitudes(
        height_ds
    )

    vort_ds = convert_longitudes(
        vort_ds
    )

    height = (
        height_ds["gh"]
        .load()
    )

    # Use magnitude for consistent shading
    # between hemispheres.
    vort = (
        np.abs(
            vort_ds["absv"]
        )
        * 100000.0
    ).load()

    lons = (
        height_ds.longitude.values
    )

    lats = (
        height_ds.latitude.values
    )

    init_time = (
        np.datetime_as_string(
            height_ds.time.values,
            unit="h",
        )
    )

    valid_time = (
        np.datetime_as_string(
            height_ds.valid_time.values,
            unit="h",
        )
    )

    height_values = (
        height.values
    )

    vort_values = (
        vort.values
    )

    height_ds.close()
    vort_ds.close()

    print(
        "GRIB loaded. "
        "Reusing data for all regions."
    )

    return {
        "height": height_values,
        "vort": vort_values,
        "lons": lons,
        "lats": lats,
        "init_time": init_time,
        "valid_time": valid_time,
    }


def get_projection(region):
    projection_name = region.get(
        "projection",
        "platecarree",
    )

    central_longitude = region.get(
        "central_longitude",
        0,
    )

    central_latitude = region.get(
        "central_latitude",
        0,
    )

    if projection_name == "lambert":
        return ccrs.LambertConformal(
            central_longitude=central_longitude,
            central_latitude=central_latitude,
        )

    if projection_name == "north_polar":
        return ccrs.NorthPolarStereo(
            central_longitude=central_longitude
        )

    if projection_name == "south_polar":
        return ccrs.SouthPolarStereo(
            central_longitude=central_longitude
        )

    return ccrs.PlateCarree(
        central_longitude=central_longitude
    )


def set_map_extent(
    ax,
    region,
    region_name,
):
    if region_name == "global":
        ax.set_extent(
            [-180, 180, -90, 90],
            crs=ccrs.PlateCarree(),
        )
        return

    if (
        region.get("projection")
        == "north_polar"
    ):
        ax.set_extent(
            [
                -180,
                180,
                region["south"],
                90,
            ],
            crs=ccrs.PlateCarree(),
        )
        return

    if (
        region.get("projection")
        == "south_polar"
    ):
        ax.set_extent(
            [
                -180,
                180,
                -90,
                region["north"],
            ],
            crs=ccrs.PlateCarree(),
        )
        return

    west = region["west"]
    east = region["east"]

    if west < east:
        ax.set_extent(
            [
                west,
                east,
                region["south"],
                region["north"],
            ],
            crs=ccrs.PlateCarree(),
        )

    else:
        ax.set_extent(
            [
                west,
                east + 360,
                region["south"],
                region["north"],
            ],
            crs=ccrs.PlateCarree(),
        )


def subset_regular_region(
    data,
    region,
):
    """
    Reduce the amount of data Matplotlib has to contour
    for ordinary regions.

    A little padding is retained beyond the visible map.
    """

    west = region["west"]
    east = region["east"]

    # Dateline-crossing areas are kept global for now.
    if west >= east:
        return (
            data["height"],
            data["vort"],
            data["lons"],
            data["lats"],
        )

    if (
        west <= -179
        and east >= 179
    ):
        return (
            data["height"],
            data["vort"],
            data["lons"],
            data["lats"],
        )

    padding = 5

    lon_mask = (
        (data["lons"] >= west - padding)
        &
        (data["lons"] <= east + padding)
    )

    lat_mask = (
        (data["lats"] >= region["south"] - padding)
        &
        (data["lats"] <= region["north"] + padding)
    )

    height = data["height"][
        np.ix_(
            lat_mask,
            lon_mask,
        )
    ]

    vort = data["vort"][
        np.ix_(
            lat_mask,
            lon_mask,
        )
    ]

    lons = data["lons"][
        lon_mask
    ]

    lats = data["lats"][
        lat_mask
    ]

    return (
        height,
        vort,
        lons,
        lats,
    )


def prepare_plot_fields(
    data,
    region,
    region_name,
):
    if region_name == "global":
        height, lons = add_cyclic_point(
            data["height"],
            coord=data["lons"],
        )

        vort, _ = add_cyclic_point(
            data["vort"],
            coord=data["lons"],
        )

        return (
            height,
            vort,
            lons,
            data["lats"],
        )

    return subset_regular_region(
        data,
        region,
    )


def plot_500mb_region(
    data,
    region_name,
    output_path,
):
    if region_name not in REGIONS:
        raise ValueError(
            f"Unknown region: "
            f"{region_name}"
        )

    region = REGIONS[
        region_name
    ]

    print(
        f"Plotting region: "
        f"{region['name']}..."
    )

    (
        height,
        vort,
        lons,
        lats,
    ) = prepare_plot_fields(
        data,
        region,
        region_name,
    )

    projection = get_projection(
        region
    )

    fig = plt.figure(
        figsize=(16, 9),
        dpi=DPI,
        facecolor="white",
    )

    ax = fig.add_axes(
        [
            0.025,
            0.115,
            0.95,
            0.81,
        ],
        projection=projection,
    )

    set_map_extent(
        ax,
        region,
        region_name,
    )

    ax.add_feature(
        cfeature.LAND,
        facecolor="0.94",
        zorder=0,
    )

    ax.add_feature(
        cfeature.OCEAN,
        facecolor="white",
        zorder=0,
    )

    ax.add_feature(
        cfeature.COASTLINE,
        linewidth=0.65,
        zorder=5,
    )

    ax.add_feature(
        cfeature.BORDERS,
        linewidth=0.5,
        zorder=5,
    )

    if region_name in {
        "conus",
        "north_america",
        "northeast",
        "new_england",
    }:
        ax.add_feature(
            cfeature.STATES,
            linewidth=0.35,
            zorder=5,
        )

    vort_levels = np.arange(
        10,
        52,
        2,
    )

    shading = ax.contourf(
        lons,
        lats,
        vort,
        levels=vort_levels,
        cmap="YlOrRd",
        extend="max",
        transform=ccrs.PlateCarree(),
        zorder=1,
    )

    min_height = (
        np.floor(
            np.nanmin(height) / 60
        )
        * 60
    )

    max_height = (
        np.ceil(
            np.nanmax(height) / 60
        )
        * 60
    )

    height_levels = np.arange(
        min_height,
        max_height + 60,
        60,
    )

    contours = ax.contour(
        lons,
        lats,
        height,
        levels=height_levels,
        colors="black",
        linewidths=0.85,
        transform=ccrs.PlateCarree(),
        zorder=4,
    )

    # Global map gets fewer contour labels
    # to avoid clutter and speed rendering.
    if region_name == "global":
        ax.clabel(
            contours,
            inline=True,
            fontsize=6,
            fmt="%d",
        )
    else:
        ax.clabel(
            contours,
            inline=True,
            inline_spacing=3,
            fontsize=7,
            fmt="%d",
        )

    ax.set_title(
        (
            "GFS 500 mb Geopotential Height "
            "& Absolute Vorticity"
        ),
        loc="left",
        fontsize=15,
        fontweight="bold",
        pad=5,
    )

    ax.set_title(
        (
            f"Init: "
            f"{data['init_time']} UTC\n"
            f"Valid: "
            f"{data['valid_time']} UTC"
        ),
        loc="right",
        fontsize=9,
        pad=5,
    )

    colorbar_ax = fig.add_axes(
        [
            0.13,
            0.062,
            0.74,
            0.025,
        ]
    )

    colorbar = fig.colorbar(
        shading,
        cax=colorbar_ax,
        orientation="horizontal",
    )

    colorbar.set_label(
        (
            "500 mb Absolute Vorticity "
            "(10⁻⁵ s⁻¹)"
        ),
        fontsize=9,
        labelpad=3,
    )

    colorbar.ax.tick_params(
        labelsize=8,
        pad=2,
    )

    fig.text(
        0.025,
        0.025,
        "@MassachusettsWx",
        fontsize=9,
        fontweight="bold",
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        dpi=DPI,
        facecolor="white",
    )

    plt.close(fig)

    print(
        f"Saved: "
        f"{output_path.name}"
    )

    return output_path