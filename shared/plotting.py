import numpy as np

import matplotlib.pyplot as plt


import cartopy.crs as ccrs

import cartopy.feature as cfeature



from cartopy.util import (
    add_cyclic_point,
)


from matplotlib.colors import (
    BoundaryNorm,
    ListedColormap,
)


from matplotlib.patches import (
    Patch,
)


from shared.regions import (
    REGIONS,
)


from shared.products import (
    PRODUCTS,
)


from shared.attribution import (
    get_map_attribution,
)


# ============================================================
# SETTINGS
# ============================================================

DPI = 120

# Fixed physical map panel used by every region.
# This is intentionally identical regardless of geographic extent.
MAP_AXES_RECT = [
    0.02,   # left
    0.14,   # bottom
    0.96,   # width
    0.78,   # height
]


# ============================================================
# PROJECTION
# ============================================================

def get_projection(
    region,
):
    projection_name = (
        region.get(
            "projection",
            "platecarree",
        )
    )

    central_longitude = (
        region.get(
            "central_longitude",
            0,
        )
    )

    if (
        projection_name
        == "north_polar"
    ):

        return (
            ccrs.NorthPolarStereo(
                central_longitude=(
                    central_longitude
                )
            )
        )

    if (
        projection_name
        == "south_polar"
    ):

        return (
            ccrs.SouthPolarStereo(
                central_longitude=(
                    central_longitude
                )
            )
        )

    return (
        ccrs.PlateCarree(
            central_longitude=(
                central_longitude
            )
        )
    )


# ============================================================
# EXTENT
# ============================================================

def set_map_extent(
    ax,
    region,
    region_name,
):
    if region_name == "global":

        ax.set_global()

        return

    projection_name = (
        region.get(
            "projection",
            "platecarree",
        )
    )

    # ========================================================
    # POLAR PROJECTIONS
    # ========================================================

    if (
        projection_name
        == "north_polar"
    ):

        ax.set_extent(
            [
                -180,
                180,
                region[
                    "south"
                ],
                90,
            ],

            crs=(
                ccrs.PlateCarree()
            ),
        )

        return

    if (
        projection_name
        == "south_polar"
    ):

        ax.set_extent(
            [
                -180,
                180,
                -90,
                region[
                    "north"
                ],
            ],

            crs=(
                ccrs.PlateCarree()
            ),
        )

        return

    # ========================================================
    # REGULAR LAT/LON REGIONS
    # ========================================================

    west = float(
        region[
            "west"
        ]
    )

    east = float(
        region[
            "east"
        ]
    )

    south = float(
        region[
            "south"
        ]
    )

    north = float(
        region[
            "north"
        ]
    )

    central_longitude = float(
        region.get(
            "central_longitude",
            0,
        )
    )

    # ========================================================
    # DATELINE-CENTERED REGIONS
    #
    # For PlateCarree projections centered away from 0 degrees,
    # use the axes' native x/y limits. This avoids forcing a
    # wrapped longitude interval such as 120E -> 100W through
    # PlateCarree(0), which can trigger Cartopy transform issues.
    # ========================================================

    if (
        projection_name
        == "platecarree"
        and
        central_longitude
        != 0
    ):

        def shifted_longitude(
            longitude,
        ):
            return (
                (
                    longitude
                    -
                    central_longitude
                    +
                    180
                )
                %
                360
            ) - 180

        west_native = (
            shifted_longitude(
                west
            )
        )

        east_native = (
            shifted_longitude(
                east
            )
        )

        if (
            east_native
            <= west_native
        ):

            east_native += 360

        ax.set_xlim(
            west_native,
            east_native,
        )

        ax.set_ylim(
            south,
            north,
        )

        return

    # ========================================================
    # STANDARD NON-DATELINE REGIONS
    # ========================================================

    ax.set_extent(
        [
            west,
            east,
            south,
            north,
        ],

        crs=(
            ccrs.PlateCarree()
        ),
    )

# ============================================================
# CYCLIC GLOBAL FIELD
# ============================================================

def make_cyclic(
    field,
    lons,
):
    (
        cyclic_field,
        cyclic_lons,
    ) = add_cyclic_point(
        field,
        coord=lons,
    )

    return (
        cyclic_field,
        cyclic_lons,
    )


# ============================================================
# BASE MAP
# ============================================================

def add_base_map(
    ax,
    region_name,
):
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


# ============================================================
# FIGURE
# ============================================================

def create_figure(
    region,
    region_name,
):
    fig = plt.figure(
        figsize=(
            16,
            9,
        ),

        dpi=DPI,

        facecolor="white",
    )

    ax = fig.add_axes(
        MAP_AXES_RECT,

        projection=(
            get_projection(
                region
            )
        ),
    )

    set_map_extent(
        ax,
        region,
        region_name,
    )

    # --------------------------------------------------------
    # FIXED WIDE LAYOUT FOR REGIONAL PLATE-CARREE MAPS
    #
    # Cartopy normally preserves geographic aspect ratio, which
    # makes tall domains such as the Atlantic, New England, etc.
    # shrink into narrow portrait-shaped map boxes.  For the
    # operational graphics we want every regional map to occupy
    # the same wide canvas area as CONUS.
    # --------------------------------------------------------

    if (
        region.get(
            "projection",
            "platecarree",
        )
        == "platecarree"
    ):
        ax.set_aspect(
            "auto"
        )

    add_base_map(
        ax,
        region_name,
    )

    return (
        fig,
        ax,
    )

# ============================================================
# FIXED MAP PANEL
# ============================================================

def lock_map_panel(
    ax,
):
    """
    Force the GeoAxes back into the exact same physical rectangle.

    Cartopy/Matplotlib can readjust a GeoAxes position while drawing
    different geographic extents.  Calling this immediately before
    saving guarantees that Global, CONUS, Northeast, New England,
    Atlantic, Western Atlantic, Tropical Atlantic, and North Pacific
    use the same map-panel width and height on the 16:9 canvas.
    """

    ax.set_position(
        MAP_AXES_RECT
    )

    # Stretch the geographic view to the fixed panel rather than
    # shrinking the axes to preserve the longitude/latitude ratio.
    ax.set_aspect(
        "auto",
        adjustable="box",
    )

    ax.set_anchor(
        "C"
    )


# ============================================================
# TITLES
# ============================================================

def add_titles(
    ax,
    *,
    model_name,
    product_name,
    init_time,
    valid_time,
):
    # Use figure coordinates rather than ax.set_title().
    #
    # This keeps the main title and Init/Valid block in fixed
    # positions even when a regional map has unusual geographic
    # dimensions.
    fig = ax.figure

    fig.text(
        0.02,
        0.965,

        (
            f"{model_name} "
            f"{product_name}"
        ),

        fontsize=15,

        fontweight="bold",

        ha="left",

        va="top",
    )

    fig.text(
        0.98,
        0.965,

        (
            f"Init: "
            f"{init_time} UTC\n"
            f"Valid: "
            f"{valid_time} UTC"
        ),

        fontsize=10,

        fontweight="semibold",

        ha="right",

        va="top",
    )

# ============================================================
# COLORBAR
# ============================================================

def add_colorbar(
    fig,
    filled,
    label,
):
    colorbar_ax = (
        fig.add_axes(
            [
                0.12,
                0.065,
                0.76,
                0.026,
            ]
        )
    )

    colorbar = fig.colorbar(
        filled,

        cax=colorbar_ax,

        orientation=(
            "horizontal"
        ),
    )

    colorbar.set_label(
        label,

        fontsize=12,

        fontweight="medium",

        labelpad=4,
    )

    colorbar.ax.tick_params(
        labelsize=10,

        pad=2,
    )

    return colorbar

# ============================================================
# BRANDING + ATTRIBUTION
# ============================================================

def add_branding(
    fig,
    model_name=None,
):
    # --------------------------------------------------------
    # MASSACHUSETTSWX
    #
    # Keep the site branding below the colorbar on the lower-left
    # side of the full figure.
    # --------------------------------------------------------

    fig.text(
        0.02,
        0.025,

        "@MassachusettsWx",

        fontsize=10,

        fontweight="bold",

        ha="left",

        va="bottom",
    )

    # --------------------------------------------------------
    # PROVIDER ATTRIBUTION
    #
    # Place provider/licensing text inside the lower-right corner
    # of the map panel, similar to commercial weather-map layouts.
    # This prevents it from colliding with the horizontal colorbar
    # label or the MassachusettsWx branding.
    # --------------------------------------------------------

    attribution = (
        get_map_attribution(
            model_name
        )
    )

    if attribution:

        map_right = (
            MAP_AXES_RECT[
                0
            ]
            +
            MAP_AXES_RECT[
                2
            ]
        )

        map_bottom = (
            MAP_AXES_RECT[
                1
            ]
        )

        fig.text(
            map_right - 0.006,
            map_bottom + 0.006,

            attribution,

            fontsize=6.5,

            ha="right",

            va="bottom",

            zorder=20,

            bbox={
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.72,
                "pad": 1.0,
            },
        )

# ============================================================
# MIN / MAX VALUES
# ============================================================

def add_min_max_values(
    fig,
    field,
    *,
    label="",
    units="",
):
    """Add the plotted parameter minimum and maximum near the colorbar."""
    values = np.asarray(field, dtype=float)

    if not np.isfinite(values).any():
        return

    minimum = np.nanmin(values)
    maximum = np.nanmax(values)
    magnitude = max(abs(minimum), abs(maximum))

    if magnitude >= 100:
        value_format = ".0f"
    elif magnitude >= 10:
        value_format = ".1f"
    else:
        value_format = ".2f"

    units_text = f" {units}" if units else ""
    label_text = f"{label}: " if label else ""

    fig.text(
        0.98,
        0.073,
        (
            f"{label_text}"
            f"Min: {minimum:{value_format}}{units_text}  •  "
            f"Max: {maximum:{value_format}}{units_text}"
        ),
        fontsize=9,
        fontweight="semibold",
        ha="right",
        va="center",
    )


# ============================================================
# SAVE
# ============================================================

def save_figure(
    fig,
    output_path,
):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,

        dpi=DPI,

        facecolor="white",
    )

    plt.close(
        fig
    )

    print(
        f"Saved: "
        f"{output_path.name}"
    )

# ============================================================
# FILLED FIELD
# ============================================================

def draw_filled_field(
    ax,
    field,
    lons,
    lats,
    product,
):
    (
        field_cyclic,
        cyclic_lons,
    ) = make_cyclic(
        field,
        lons,
    )

    levels = np.asarray(
        product[
            "shading_levels"
        ]
    )

    filled = ax.contourf(
        cyclic_lons,

        lats,

        field_cyclic,

        levels=levels,

        cmap=product.get(
            "cmap",
            "viridis",
        ),

        extend="both",

        transform=(
            ccrs.PlateCarree()
        ),

        zorder=1,
    )

    return (
        filled,
        field_cyclic,
        cyclic_lons,
    )


# ============================================================
# COMMON FINALIZATION
# ============================================================

def finalize_filled_plot(
    *,
    fig,
    ax,
    filled,
    data,
    product,
    model_name,
    output_path,
    min_max_field=None,
):
    # Re-lock after all contours/shading have been drawn because
    # Cartopy may otherwise resize the GeoAxes based on region shape.
    lock_map_panel(
        ax
    )

    add_titles(
        ax,

        model_name=model_name,

        product_name=(
            product[
                "name"
            ]
        ),

        init_time=(
            data[
                "init_time"
            ]
        ),

        valid_time=(
            data[
                "valid_time"
            ]
        ),
    )

    add_colorbar(
        fig,

        filled,

        (
            f"{product['shading_name']} "
            f"("
            f"{product['shading_units']}"
            f")"
        ),
    )

    if min_max_field is not None:
        add_min_max_values(
            fig,
            min_max_field,
            label=product.get("shading_name", ""),
            units=product.get("shading_units", ""),
        )

    add_branding(
        fig,
        model_name=model_name,
    )

    save_figure(
        fig,
        output_path,
    )


# ============================================================
# HEIGHT + SHADING
# ============================================================

def render_height_shading(
    *,
    data,
    product,
    region_name,
    output_path,
    model_name,
):
    region = REGIONS[
        region_name
    ]

    fields = data[
        "fields"
    ]

    height = fields[
        "height"
    ]

    shading = fields[
        product[
            "shade_field"
        ]
    ]

    fig, ax = (
        create_figure(
            region,
            region_name,
        )
    )

    (
        filled,
        _,
        cyclic_lons,
    ) = draw_filled_field(
        ax,
        shading,
        data[
            "lons"
        ],
        data[
            "lats"
        ],
        product,
    )

    (
        height_cyclic,
        _,
    ) = make_cyclic(
        height,
        data[
            "lons"
        ],
    )

    interval = (
        product.get(
            "height_interval",
            60,
        )
    )

    minimum = (
        np.floor(
            np.nanmin(
                height_cyclic
            )
            / interval
        )
        * interval
    )

    maximum = (
        np.ceil(
            np.nanmax(
                height_cyclic
            )
            / interval
        )
        * interval
    )

    levels = np.arange(
        minimum,
        maximum + interval,
        interval,
    )

    contours = ax.contour(
        cyclic_lons,

        data[
            "lats"
        ],

        height_cyclic,

        levels=levels,

        colors="black",

        linewidths=0.85,

        transform=(
            ccrs.PlateCarree()
        ),

        zorder=4,
    )

    ax.clabel(
        contours,

        inline=True,

        inline_spacing=3,

        fontsize=(
            6
            if region_name
            == "global"
            else 7
        ),

        fmt="%d",
    )

    finalize_filled_plot(
        fig=fig,
        ax=ax,
        filled=filled,
        data=data,
        product=product,
        model_name=model_name,
        output_path=output_path,
        min_max_field=shading,
    )


# ============================================================
# SURFACE SHADING
# ============================================================

def render_surface_shading(
    *,
    data,
    product,
    region_name,
    output_path,
    model_name,
):
    region = REGIONS[
        region_name
    ]

    field = (
        data[
            "fields"
        ][
            product[
                "shade_field"
            ]
        ]
    )

    fig, ax = (
        create_figure(
            region,
            region_name,
        )
    )

    filled, _, _ = (
        draw_filled_field(
            ax,
            field,
            data[
                "lons"
            ],
            data[
                "lats"
            ],
            product,
        )
    )

    finalize_filled_plot(
        fig=fig,
        ax=ax,
        filled=filled,
        data=data,
        product=product,
        model_name=model_name,
        output_path=output_path,
        min_max_field=field,
    )


# ============================================================
# MSLP
# ============================================================

def render_surface_pressure(
    *,
    data,
    product,
    region_name,
    output_path,
    model_name,
):
    pressure = (
        data[
            "fields"
        ][
            "mslp"
        ]
    )

    (
        pressure_cyclic,
        cyclic_lons,
    ) = make_cyclic(
        pressure,
        data[
            "lons"
        ],
    )

    fig, ax = (
        create_figure(
            REGIONS[
                region_name
            ],
            region_name,
        )
    )

    minimum = (
        np.floor(
            np.nanmin(
                pressure_cyclic
            )
            / 4
        )
        * 4
    )

    maximum = (
        np.ceil(
            np.nanmax(
                pressure_cyclic
            )
            / 4
        )
        * 4
    )

    levels = np.arange(
        minimum,
        maximum + 4,
        4,
    )

    contours = ax.contour(
        cyclic_lons,

        data[
            "lats"
        ],

        pressure_cyclic,

        levels=levels,

        colors="black",

        linewidths=0.9,

        transform=(
            ccrs.PlateCarree()
        ),

        zorder=4,
    )

    ax.clabel(
        contours,

        inline=True,

        fontsize=7,

        fmt="%d",
    )

    lock_map_panel(
        ax
    )

    add_titles(
        ax,

        model_name=model_name,

        product_name=(
            product[
                "name"
            ]
        ),

        init_time=(
            data[
                "init_time"
            ]
        ),

        valid_time=(
            data[
                "valid_time"
            ]
        ),
    )

    add_min_max_values(
        fig,
        pressure_cyclic,
        label=product.get("name", "MSLP"),
        units=product.get("shading_units", "hPa"),
    )

    add_branding(
        fig,
        model_name=model_name,
    )

    save_figure(
        fig,
        output_path,
    )


# ============================================================
# PRESSURE + WIND
# ============================================================

def render_pressure_wind(
    *,
    data,
    product,
    region_name,
    output_path,
    model_name,
):
    fields = data[
        "fields"
    ]

    pressure = fields[
        "mslp"
    ]

    wind = fields[
        "wind_speed"
    ]

    fig, ax = (
        create_figure(
            REGIONS[
                region_name
            ],
            region_name,
        )
    )

    (
        filled,
        _,
        cyclic_lons,
    ) = draw_filled_field(
        ax,
        wind,
        data[
            "lons"
        ],
        data[
            "lats"
        ],
        product,
    )

    (
        pressure_cyclic,
        _,
    ) = make_cyclic(
        pressure,
        data[
            "lons"
        ],
    )

    minimum = (
        np.floor(
            np.nanmin(
                pressure_cyclic
            )
            / 4
        )
        * 4
    )

    maximum = (
        np.ceil(
            np.nanmax(
                pressure_cyclic
            )
            / 4
        )
        * 4
    )

    levels = np.arange(
        minimum,
        maximum + 4,
        4,
    )

    contours = ax.contour(
        cyclic_lons,

        data[
            "lats"
        ],

        pressure_cyclic,

        levels=levels,

        colors="black",

        linewidths=0.85,

        transform=(
            ccrs.PlateCarree()
        ),

        zorder=4,
    )

    ax.clabel(
        contours,

        inline=True,

        fontsize=7,

        fmt="%d",
    )

    finalize_filled_plot(
        fig=fig,
        ax=ax,
        filled=filled,
        data=data,
        product=product,
        model_name=model_name,
        output_path=output_path,
        min_max_field=wind,
    )


# ============================================================
# SCALAR CONTOUR
# ============================================================

def render_scalar_contour(
    *,
    data,
    product,
    region_name,
    output_path,
    model_name,
):
    field = (
        data[
            "fields"
        ][
            product[
                "shade_field"
            ]
        ]
    )

    fig, ax = (
        create_figure(
            REGIONS[
                region_name
            ],
            region_name,
        )
    )

    (
        filled,
        field_cyclic,
        cyclic_lons,
    ) = draw_filled_field(
        ax,
        field,
        data[
            "lons"
        ],
        data[
            "lats"
        ],
        product,
    )

    interval = (
        product.get(
            "contour_interval",
            60,
        )
    )

    minimum = (
        np.floor(
            np.nanmin(
                field_cyclic
            )
            / interval
        )
        * interval
    )

    maximum = (
        np.ceil(
            np.nanmax(
                field_cyclic
            )
            / interval
        )
        * interval
    )

    levels = np.arange(
        minimum,
        maximum + interval,
        interval,
    )

    contours = ax.contour(
        cyclic_lons,

        data[
            "lats"
        ],

        field_cyclic,

        levels=levels,

        colors="black",

        linewidths=0.75,

        transform=(
            ccrs.PlateCarree()
        ),

        zorder=4,
    )

    ax.clabel(
        contours,

        inline=True,

        fontsize=7,

        fmt="%d",
    )

    finalize_filled_plot(
        fig=fig,
        ax=ax,
        filled=filled,
        data=data,
        product=product,
        model_name=model_name,
        output_path=output_path,
        min_max_field=field_cyclic,
    )


# ============================================================
# ACCUMULATION
# ============================================================

def render_accumulation(
    *,
    data,
    product,
    region_name,
    output_path,
    model_name,
):
    field = (
        data[
            "fields"
        ][
            product[
                "shade_field"
            ]
        ]
    )

    (
        field_cyclic,
        cyclic_lons,
    ) = make_cyclic(
        field,
        data[
            "lons"
        ],
    )

    fig, ax = (
        create_figure(
            REGIONS[
                region_name
            ],
            region_name,
        )
    )

    levels = product.get(
        "shading_levels",

        [
            0.01,
            0.05,
            0.10,
            0.25,
            0.50,
            0.75,
            1.00,
            1.50,
            2.00,
            3.00,
            4.00,
            5.00,
            6.00,
            8.00,
            10.00,
        ],
    )

    filled = ax.contourf(
        cyclic_lons,

        data[
            "lats"
        ],

        field_cyclic,

        levels=levels,

        cmap=product.get(
            "cmap",

            (
                "Blues"
                if "snow"
                in product[
                    "shade_field"
                ]
                else "turbo"
            ),
        ),

        extend="max",

        transform=(
            ccrs.PlateCarree()
        ),

        zorder=1,
    )

    finalize_filled_plot(
        fig=fig,
        ax=ax,
        filled=filled,
        data=data,
        product=product,
        model_name=model_name,
        output_path=output_path,
        min_max_field=field_cyclic,
    )


# ============================================================
# PRECIPITATION CATEGORIES
# ============================================================

def draw_precip_categories(
    *,
    data,
    display,
    region_name,
    output_path,
    model_name,
    product_name,
    include_convective=False,
):
    (
        display_cyclic,
        cyclic_lons,
    ) = make_cyclic(
        display,
        data[
            "lons"
        ],
    )

    fig, ax = (
        create_figure(
            REGIONS[
                region_name
            ],
            region_name,
        )
    )

    colors = [
        (
            0,
            0,
            0,
            0,
        ),

        "green",
        "magenta",
        "blue",
        "purple",
        "orange",
    ]

    if include_convective:

        colors.append(
            "red"
        )

    cmap = ListedColormap(
        colors
    )

    maximum_category = (
        6
        if include_convective
        else 5
    )

    boundaries = np.arange(
        -0.5,
        maximum_category + 1.5,
        1,
    )

    norm = BoundaryNorm(
        boundaries,
        cmap.N,
    )

    ax.pcolormesh(
        cyclic_lons,

        data[
            "lats"
        ],

        display_cyclic,

        cmap=cmap,

        norm=norm,

        shading="auto",

        transform=(
            ccrs.PlateCarree()
        ),

        zorder=2,
    )

    lock_map_panel(
        ax
    )

    add_titles(
        ax,

        model_name=model_name,

        product_name=product_name,

        init_time=(
            data[
                "init_time"
            ]
        ),

        valid_time=(
            data[
                "valid_time"
            ]
        ),
    )

    handles = [
        Patch(
            facecolor="green",
            label="Rain",
        ),

        Patch(
            facecolor="magenta",
            label="Freezing Rain",
        ),

        Patch(
            facecolor="blue",
            label="Snow",
        ),

        Patch(
            facecolor="purple",
            label="Mixed",
        ),

        Patch(
            facecolor="orange",
            label="Ice Pellets",
        ),
    ]

    if include_convective:

        handles.append(
            Patch(
                facecolor="red",
                label=(
                    "Convective / Hail"
                ),
            )
        )

    ax.legend(
        handles=handles,

        loc="lower center",

        bbox_to_anchor=(
            0.5,
            -0.075,
        ),

        ncol=len(
            handles
        ),

        fontsize=9,

        frameon=True,
    )

    add_branding(
        fig,
        model_name=model_name,
    )

    save_figure(
        fig,
        output_path,
    )


# ============================================================
# ECMWF PTYPE
# ============================================================

def render_categorical(
    *,
    data,
    product,
    region_name,
    output_path,
    model_name,
):
    raw = (
        data[
            "fields"
        ][
            product[
                "shade_field"
            ]
        ]
    )

    display = np.zeros(
        raw.shape,
        dtype=np.int16,
    )

    # Rain / drizzle
    display[
        np.isin(
            raw,
            [
                1,
                11,
            ],
        )
    ] = 1

    # Freezing rain / freezing drizzle
    display[
        np.isin(
            raw,
            [
                3,
                12,
            ],
        )
    ] = 2

    # Snow / wet snow
    display[
        np.isin(
            raw,
            [
                5,
                6,
            ],
        )
    ] = 3

    # Mixed
    display[
        np.isin(
            raw,
            [
                4,
                7,
            ],
        )
    ] = 4

    # Ice pellets
    display[
        raw == 8
    ] = 5

    # Thunder / graupel / hail
    display[
        np.isin(
            raw,
            [
                2,
                9,
                10,
                13,
                14,
            ],
        )
    ] = 6

    draw_precip_categories(
        data=data,

        display=display,

        region_name=region_name,

        output_path=output_path,

        model_name=model_name,

        product_name=(
            product[
                "name"
            ]
        ),

        include_convective=True,
    )


# ============================================================
# GFS PTYPE
# ============================================================

def render_categorical_gfs(
    *,
    data,
    product,
    region_name,
    output_path,
    model_name,
):
    display = (
        data[
            "fields"
        ][
            "ptype"
        ]
    )

    draw_precip_categories(
        data=data,

        display=display,

        region_name=region_name,

        output_path=output_path,

        model_name=model_name,

        product_name=(
            product[
                "name"
            ]
        ),

        include_convective=False,
    )


# ============================================================
# MASTER RENDERER
# ============================================================

def render_product(
    *,
    data,
    product_name,
    region_name,
    output_path,
    model_name,
):
    if product_name not in PRODUCTS:

        raise ValueError(
            f"Unknown product: "
            f"{product_name}"
        )

    if region_name not in REGIONS:

        raise ValueError(
            f"Unknown region: "
            f"{region_name}"
        )

    product = PRODUCTS[
        product_name
    ]

    renderer = product[
        "renderer"
    ]

    print(
        f"Rendering "
        f"{product['name']} "
        f"for "
        f"{REGIONS[region_name]['name']}..."
    )

    renderer_map = {
        "height_shading": (
            render_height_shading
        ),

        "surface_shading": (
            render_surface_shading
        ),

        "surface_pressure": (
            render_surface_pressure
        ),

        "pressure_wind": (
            render_pressure_wind
        ),

        "scalar_contour": (
            render_scalar_contour
        ),

        "accumulation": (
            render_accumulation
        ),

        "categorical": (
            render_categorical
        ),

        "categorical_gfs": (
            render_categorical_gfs
        ),
    }

    if renderer not in renderer_map:

        raise RuntimeError(
            f"Unsupported renderer: "
            f"{renderer}"
        )

    return renderer_map[
        renderer
    ](
        data=data,

        product=product,

        region_name=region_name,

        output_path=output_path,

        model_name=model_name,
    )