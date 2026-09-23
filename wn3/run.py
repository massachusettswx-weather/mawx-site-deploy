"""python -m wn3.run --inspect; python -m wn3.run --regions conus northeast."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile

import numpy as np

from shared.regions import REGIONS
from wn3.fields import coordinate_names, mean_fields, select_region, style_for
from wn3.source import connect, latest_source, open_source

MODEL = "weathernext3_mean"


def init_time(ds):
    values = np.asarray(ds["init_time"].values).reshape(-1)
    if values.size != 1 or not np.issubdtype(values.dtype, np.datetime64):
        raise ValueError("Expected exactly one datetime initialization in this store.")
    return datetime.fromisoformat(np.datetime_as_string(values[0], unit="s")).replace(tzinfo=timezone.utc)


def forecast_steps(ds, end_hour, step):
    values = np.asarray(ds["lead_time"].values)
    if values.ndim != 1 or not np.issubdtype(values.dtype, np.timedelta64):
        raise ValueError("Expected a single decoded timedelta lead_time axis.")
    hours = values / np.timedelta64(1, "h")
    wanted = list(range(step, end_hour + 1, step))
    if not all(np.count_nonzero(hours == h) == 1 for h in wanted):
        raise ValueError("The selected run does not contain every requested forecast hour.")
    return wanted


def render(da, region_name, initial, hour, target):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    from shared.plotting import create_figure

    style = style_for(da.name, da.attrs.get("units", ""))
    lat, lon = coordinate_names(da)
    values = np.asarray(da.values) * style.scale + style.offset
    if not np.isfinite(values).any():
        raise ValueError(f"All values missing for {da.name}, {region_name}, f{hour:03d}")
    fig, ax = create_figure(REGIONS[region_name], region_name)
    try:
        mesh = ax.pcolormesh(da[lon], da[lat], values, transform=ccrs.PlateCarree(),
                             cmap=style.cmap, vmin=style.low, vmax=style.high, shading="auto")
        fig.text(.02, .975, "MassachusettsWx | WeatherNext 3 ensemble mean", fontsize=16, weight="bold")
        fig.text(.02, .943, style.title, fontsize=12)
        valid = initial + timedelta(hours=hour)
        fig.text(.98, .975, f"Init {initial:%Y-%m-%d %HZ}\nValid {valid:%Y-%m-%d %HZ} · f{hour:03d}",
                 ha="right", va="top", fontsize=10)
        cax = fig.add_axes([.18, .075, .64, .024])
        fig.colorbar(mesh, cax=cax, orientation="horizontal", label=style.units, extend="both")
        fig.text(.02, .012, "Source: Google WeatherNext 3 / Cloud Storage · © 2024–6 Google LLC\n"
                 "Experimental data; personal research preview. Terms: developers.google.com/weathernext/guides/models",
                 fontsize=8)
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=90, format="webp", pil_kwargs={"lossless": False, "quality": 85})
    finally:
        plt.close(fig)


def export(ds, source, output, regions, end_hour, step, max_frames=2000, max_mb=200):
    fields = mean_fields(ds)
    initial = init_time(ds)
    hours = forecast_steps(ds, end_hour, step)
    count = len(fields) * len(regions) * len(hours)
    if count > max_frames:
        raise ValueError(f"{count} maps exceeds limit {max_frames}; reduce regions or hours.")
    output = Path(output)
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a new directory to preserve earlier maps.")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".wn3-", dir=output.parent))
    try:
        shutil.copytree(Path(__file__).resolve().parents[1] / "site", stage / "site")
        (stage / "index.html").write_text('<!doctype html><meta charset="utf-8">'
                                        '<meta http-equiv="refresh" content="0;url=site/">'
                                        '<a href="site/">MassachusettsWx WeatherNext 3</a>')
        (stage / ".nojekyll").touch()
        # Preview shows only WN3; the original repository keeps all other model code.
        (stage / "site" / "wn3-preview.js").write_text(
            'window.MASSWX_MODELS = ["weathernext3_mean"];\n')
        html = stage / "site" / "index.html"
        html.write_text(html.read_text().replace('<script src="app.js"></script>',
                        '<script src="wn3-preview.js"></script>\n<script src="app.js"></script>'))
        files, total_bytes = [], 0
        for name in fields:
            variable = ds[name]
            for dim in list(variable.dims):
                if dim == "init_time":
                    variable = variable.isel({dim: 0}, drop=True)
            style = style_for(name, variable.attrs.get("units", ""))
            for region in regions:
                for hour in hours:
                    frame = select_region(variable.sel(lead_time=np.timedelta64(hour, "h")), REGIONS[region])
                    # Exactly one variable, one region, one time in memory.
                    relative = f"maps/{MODEL}/{region}/{name}/f{hour:03d}.webp"
                    target = stage / relative
                    render(frame, region, initial, hour, target)
                    total_bytes += target.stat().st_size
                    if total_bytes > max_mb * 1024**2:
                        raise ValueError(f"Map output exceeded {max_mb} MiB; reduce scope.")
                    files.append({"model": MODEL, "region": region, "product": name,
                                  "forecast_hour": hour, "object_name": relative})
            print(f"Rendered {name}", flush=True)
        manifest = {
            "model": MODEL, "cycle": initial.strftime("%Y%m%d%H"), "status": "complete",
            "generated_at": datetime.now(timezone.utc).isoformat(), "source": "gs://" + source,
            "scope": "Precomputed surface ensemble means only; upper-air fields unavailable.",
            "product_names": {n: style_for(n, ds[n].attrs.get("units", "")).title for n in fields},
            "files": files,
        }
        metadata = stage / "metadata" / MODEL
        metadata.mkdir(parents=True)
        (metadata / "latest.json").write_text(json.dumps(manifest, indent=2))
        os.replace(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    print(f"Created {len(files)} maps ({total_bytes / 1024**2:.1f} MiB) in {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", help="Read metadata only; no map generation")
    parser.add_argument("--source", help="Exact gs:// statistics run; otherwise latest synoptic run")
    parser.add_argument("--regions", nargs="+", choices=sorted(REGIONS), default=["conus"])
    parser.add_argument("--end-hour", type=int, default=48)
    parser.add_argument("--step", type=int, default=6)
    parser.add_argument("--output", default="output/wn3-preview")
    args = parser.parse_args()
    if not 1 <= args.step <= args.end_hour <= 360:
        parser.error("Require 1 <= step <= end-hour <= 360")
    fs = connect()
    source = args.source or latest_source(fs)
    with open_source(fs, source) as ds:
        if args.inspect:
            print(json.dumps({"source": source, "dimensions": dict(ds.sizes),
                              "initialization": init_time(ds).isoformat(),
                              "variables": {n: {"dims": list(da.dims), "units": da.attrs.get("units")}
                                            for n, da in ds.data_vars.items() if n.endswith("_mean")}}, indent=2))
            mean_fields(ds)  # Refuse unexpected schema rather than silently mislabel units.
            return
        export(ds, source.removeprefix("gs://"), args.output, args.regions, args.end_hour, args.step)


if __name__ == "__main__":
    main()
