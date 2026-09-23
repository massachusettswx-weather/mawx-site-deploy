"""Display precomputed scalar means; never infer ensemble statistics from vectors."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Style:
    title: str
    units: str
    scale: float
    offset: float
    cmap: str
    low: float
    high: float


def style_for(name, units):
    base = name.removesuffix("_mean")
    title = base.replace("_", " ").capitalize()
    if units in {"K", "kelvin"}:
        return Style(title, "°C", 1, -273.15, "coolwarm", -35, 40)
    if units in {"Pa", "pascal"}:
        return Style(title, "hPa", .01, 0, "Spectral_r", 960, 1040)
    if units in {"m s-1", "m/s", "m s**-1", "m s^-1"}:
        component = "component" in name
        return Style(title, "kt", 1.94384449, 0,
                     "RdBu_r" if component else "turbo", -70 if component else 0, 70)
    if units in {"m", "meter", "metres"} and ("precipitation" in base or "tp_" in base):
        interval = "1-hour" if base.endswith("1hr") else "6-hour"
        return Style(f"{title} ({interval} accumulation)", "mm", 1000, 0, "YlGnBu", 0, 30)
    if units in {"1", "(0 - 1)", "0-1", "fraction"} and "cloud" in base:
        return Style(title, "%", 100, 0, "Greys", 0, 100)
    if units in {"J m-2", "J/m^2", "J m**-2", "J m^-2"}:
        return Style(title, "MJ/m²", 1e-6, 0, "inferno", 0, 4 if base.endswith("1hr") else 20)
    raise ValueError(f"Unrecognized units {units!r} for {name}; verify source metadata before plotting.")


def coordinate_names(da):
    lat = [d for d in da.dims if d in {"lat", "latitude"} or d.startswith("lat_")]
    lon = [d for d in da.dims if d in {"lon", "longitude"} or d.startswith("lon_")]
    if len(lat) != 1 or len(lon) != 1:
        raise ValueError(f"Cannot identify a rectilinear grid for {da.name}: {da.dims}")
    return lat[0], lon[0]


def mean_fields(ds):
    fields = []
    for name, da in ds.data_vars.items():
        if not name.endswith("_mean"):
            continue
        if any(d in da.dims for d in ("level", "sample", "member", "pressure_level")):
            raise ValueError(f"Unexpected ensemble/pressure dimension in mean field {name}")
        coordinate_names(da)
        style_for(name, da.attrs.get("units", ""))
        fields.append(name)
    if not fields:
        raise ValueError("No supported precomputed *_mean fields found.")
    return sorted(fields)


def select_region(da, region):
    """Index before loading, including descending latitude and dateline crossings."""
    lat, lon = coordinate_names(da)
    lats = np.asarray(da[lat].values)
    lons = np.asarray(da[lon].values)
    y = np.flatnonzero((lats >= region["south"]) & (lats <= region["north"]))
    width = region["east"] - region["west"]
    if width <= 0:
        width += 360
    delta = (lons - region["west"]) % 360
    x = np.flatnonzero(delta <= width + 1e-8)
    x = x[np.argsort(delta[x])]
    y = y[np.argsort(lats[y])]
    if len(x) < 2 or len(y) < 2:
        raise ValueError("Region contains fewer than two grid points on either axis.")
    result = da.isel({lat: y, lon: x})
    return result.assign_coords({lon: region["west"] + delta[x]}).transpose(lat, lon)
