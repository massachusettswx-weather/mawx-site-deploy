import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import xarray as xr

from wn3.fields import mean_fields, select_region, style_for
from wn3.run import export, forecast_steps
from wn3.source import PREFIX, validate_source


def fixture():
    return xr.Dataset({"temperature_2m_mean": (
        ("lead_time", "lat_0p1", "lon_0p1"), np.ones((2, 4, 4)) * 280,
        {"units": "K"})}, coords={"lead_time": np.array([6, 12], dtype="timedelta64[h]"),
                                  "lat_0p1": [55, 45, 35, 20],
                                  "lon_0p1": [230, 250, 270, 300],
                                  "init_time": np.datetime64("2026-09-23T00:00:00")})


class ExportTests(unittest.TestCase):
    def test_units_and_scalar_wind(self):
        t = style_for("temperature_2m_mean", "K")
        self.assertAlmostEqual(273.15 * t.scale + t.offset, 0)
        p = style_for("total_precipitation_1hr_mean", "m")
        self.assertEqual(.01 * p.scale, 10)
        self.assertIn("1-hour", p.title)
        self.assertEqual(style_for("mean_sea_level_pressure_mean", "Pa").scale, .01)
        self.assertEqual(style_for("wind_speed_10m_mean", "m/s").low, 0)
        self.assertLess(style_for("u_component_of_wind_10m_mean", "m/s").low, 0)

    def test_descending_lat_and_longitude_wrap(self):
        da = fixture().temperature_2m_mean.isel(lead_time=0)
        region = {"west": -130, "east": -60, "south": 20, "north": 55}
        frame = select_region(da, region)
        np.testing.assert_array_equal(frame.lat_0p1.values, [20, 35, 45, 55])
        np.testing.assert_array_equal(frame.lon_0p1.values, [-130, -110, -90, -60])
        da = da.assign_coords(lon_0p1=[160, 175, 185, 200])
        frame = select_region(da, {**region, "west": 170, "east": -170})
        np.testing.assert_array_equal(frame.lon_0p1.values, [175, 185])

    def test_no_raw_or_unknown_units(self):
        with self.assertRaises(ValueError):
            validate_source("gs://weathernext3_spatial/anything/predictions.zarr")
        ds = fixture()
        ds["temperature_2m_p90"] = ds.temperature_2m_mean
        self.assertEqual(mean_fields(ds), ["temperature_2m_mean"])
        ds.temperature_2m_mean.attrs["units"] = "unknown"
        with self.assertRaises(ValueError):
            mean_fields(ds)

    def test_missing_hour_refused(self):
        with self.assertRaises(ValueError):
            forecast_steps(fixture(), 18, 6)

    def test_export_manifest_and_viewer_paths(self):
        def fake_render(da, region, initial, hour, target):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fixture")
        with tempfile.TemporaryDirectory() as folder, patch("wn3.run.render", fake_render):
            output = Path(folder) / "preview"
            export(fixture(), PREFIX + "/20260923_00hr_01_preds/predictions.zarr",
                   output, ["conus"], 12, 6)
            manifest = json.loads((output / "metadata/weathernext3_mean/latest.json").read_text())
            self.assertEqual(len(manifest["files"]), 2)
            self.assertEqual(manifest["cycle"], "2026092300")
            for entry in manifest["files"]:
                self.assertTrue((output / "site" / ".." / entry["object_name"]).is_file())
            self.assertIn('wn3-preview.js', (output / "site/index.html").read_text())
            with self.assertRaises(ValueError):
                export(fixture(), "source", output, ["conus"], 12, 6)

    def test_failure_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as folder, patch("wn3.run.render", side_effect=RuntimeError("failure")):
            output = Path(folder) / "preview"
            with self.assertRaises(RuntimeError):
                export(fixture(), "source", output, ["conus"], 12, 6)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
