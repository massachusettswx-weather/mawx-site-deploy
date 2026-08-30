from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import xarray as xr


WN2_BASE = (
    "gs://weathernext/"
    "weathernext_2_0_0/"
    "zarr/"
    "2025_to_present/"
)

RUN_PATTERN = re.compile(
    r"(?P<date>\d{8})_"
    r"(?P<hour>\d{2})hr_"
    r"01_preds/?$"
)


@dataclass(frozen=True)
class WeatherNext2Cycle:
    cycle: str
    path: str

    @property
    def datetime(self) -> datetime:
        return datetime.strptime(
            self.cycle,
            "%Y%m%d%H",
        )

    @property
    def zarr_url(self) -> str:
        return (
            self.path.rstrip("/")
            + "/predictions.zarr"
        )


class WeatherNext2Client:
    """
    Client for Google's pre-generated WeatherNext 2
    operational forecast archive.

    This does NOT run WeatherNext 2 inference.
    """

    def __init__(
        self,
        base_url: str = WN2_BASE,
    ):
        self.base_url = base_url.rstrip("/") + "/"

    def _gcloud_ls(
        self,
        path: str,
    ) -> list[str]:
        result = subprocess.run(
            [
                "gcloud",
                "storage",
                "ls",
                path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    @staticmethod
    def cycle_from_path(
        path: str,
    ) -> Optional[WeatherNext2Cycle]:
        name = path.rstrip("/").split("/")[-1]

        match = RUN_PATTERN.match(name)

        if match is None:
            return None

        cycle = (
            match.group("date")
            + match.group("hour")
        )

        return WeatherNext2Cycle(
            cycle=cycle,
            path=path.rstrip("/"),
        )

    def available_cycles(
        self,
    ) -> list[WeatherNext2Cycle]:
        paths = self._gcloud_ls(
            self.base_url
        )

        cycles = []

        for path in paths:
            cycle = self.cycle_from_path(path)

            if cycle is not None:
                cycles.append(cycle)

        cycles.sort(
            key=lambda item: item.cycle
        )

        return cycles

    def latest_cycle(
        self,
    ) -> WeatherNext2Cycle:
        cycles = self.available_cycles()

        if not cycles:
            raise RuntimeError(
                "No WeatherNext 2 cycles were found."
            )

        return cycles[-1]

    def get_cycle(
        self,
        cycle: str,
    ) -> WeatherNext2Cycle:
        cycle = str(cycle)

        if len(cycle) != 10:
            raise ValueError(
                "WeatherNext 2 cycle must be YYYYMMDDHH."
            )

        date = cycle[:8]
        hour = cycle[8:10]

        path = (
            self.base_url
            + f"{date}_{hour}hr_01_preds"
        )

        return WeatherNext2Cycle(
            cycle=cycle,
            path=path,
        )

    def open_cycle(
        self,
        cycle: str | None = None,
    ) -> xr.Dataset:
        if cycle is None:
            resolved = self.latest_cycle()
        else:
            resolved = self.get_cycle(cycle)

        print(
            "Opening WeatherNext 2:",
            resolved.cycle,
        )

        print(
            "Zarr:",
            resolved.zarr_url,
        )

        return xr.open_zarr(
            resolved.zarr_url,
            consolidated=False,
        )

    def cycle_metadata(
        self,
        cycle: str | None = None,
    ) -> dict:
        if cycle is None:
            resolved = self.latest_cycle()
        else:
            resolved = self.get_cycle(cycle)

        ds = self.open_cycle(
            resolved.cycle
        )

        return {
            "cycle": resolved.cycle,
            "samples": int(
                ds.sizes.get("sample", 0)
            ),
            "forecast_steps": int(
                ds.sizes.get("time", 0)
            ),
            "lat_points": int(
                ds.sizes.get("lat", 0)
            ),
            "lon_points": int(
                ds.sizes.get("lon", 0)
            ),
            "levels": int(
                ds.sizes.get("level", 0)
            ),
            "variables": list(
                ds.data_vars
            ),
        }

    def select(
        self,
        *,
        cycle: str | None = None,
        sample: int | None = None,
        forecast_hour: int | None = None,
        variables: list[str] | None = None,
        levels: list[int] | None = None,
    ) -> xr.Dataset:
        """
        Lazily select only requested WeatherNext 2 data.

        Nothing is fully downloaded unless the caller
        explicitly loads/computes the returned Dataset.
        """

        ds = self.open_cycle(cycle)

        if variables is not None:
            missing = [
                name
                for name in variables
                if name not in ds.data_vars
            ]

            if missing:
                raise KeyError(
                    "WeatherNext 2 variables not found: "
                    + ", ".join(missing)
                )

            ds = ds[variables]

        if sample is not None:
            ds = ds.sel(
                sample=int(sample)
            )

        if forecast_hour is not None:
            target_time = pd.Timedelta(
                hours=int(forecast_hour)
            )

            if target_time not in ds.indexes["time"]:
                available_hours = [
                    int(
                        pd.Timedelta(value)
                        .total_seconds()
                        / 3600
                    )
                    for value in ds["time"].values
                ]

                raise KeyError(
                    f"Forecast hour {forecast_hour} "
                    f"is not available. "
                    f"Available hours: {available_hours}"
                )

            ds = ds.sel(
                time=target_time
            )

        if (
            levels is not None
            and "level" in ds.coords
        ):
            ds = ds.sel(
                level=levels
            )

        return ds
