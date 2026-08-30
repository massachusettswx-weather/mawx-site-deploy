from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .source_config import FNV3_SOURCE


class FNV3ForecastClient:
    def __init__(
        self,
        cache_dir=None,
        session=None,
    ):
        if cache_dir is None:
            cache_dir = (
                Path(__file__).resolve().parents[1]
                / "output"
                / "raw"
            )

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        if session is None:
            session = requests.Session()

        self.session = session
        self.session.headers.update(
            {
                "User-Agent": (
                    "MassachusettsWx WeatherNext "
                    "Cyclone Downloader"
                ),
                "Accept": "*/*",
            }
        )

    def available(self):
        return bool(
            FNV3_SOURCE["enabled"]
        )

    @staticmethod
    def _normalize_cycle(cycle):
        if isinstance(cycle, datetime):
            dt = cycle

            if dt.tzinfo is None:
                dt = dt.replace(
                    tzinfo=timezone.utc,
                )
            else:
                dt = dt.astimezone(
                    timezone.utc,
                )

            return dt.strftime(
                "%Y%m%d%H"
            )

        text = str(cycle).strip()

        if len(text) != 10:
            raise ValueError(
                "FNV3 cycle must be YYYYMMDDHH. "
                f"Received: {cycle!r}"
            )

        datetime.strptime(
            text,
            "%Y%m%d%H",
        )

        return text

    @staticmethod
    def _cycle_datetime(cycle):
        cycle = (
            FNV3ForecastClient
            ._normalize_cycle(cycle)
        )

        return datetime.strptime(
            cycle,
            "%Y%m%d%H",
        ).replace(
            tzinfo=timezone.utc,
        )

    def build_url(self, cycle):
        """
        Build the canonical Weather Lab FNV3 URL.

        Keep cycle discovery and the production downloader
        on exactly the same URL-generation path.
        """

        cycle = self._normalize_cycle(
            cycle
        )

        from .fnv3_cyclone_downloader import (
            build_weatherlab_url,
        )

        return build_weatherlab_url(
            cycle
        )


    def _remote_cycle_exists(
        self,
        cycle,
    ):
        """
        Return True only when the Weather Lab
        FNV3 source file is actually readable.

        Use a ranged GET rather than HEAD because
        the Weather Lab endpoint does not provide
        reliable HEAD semantics for cycle discovery.
        """

        url = self.build_url(
            cycle
        )

        try:
            response = self.session.get(
                url,
                headers={
                    "Range": "bytes=0-1023",
                },
                allow_redirects=True,
                timeout=30,
                stream=True,
            )

            status = response.status_code

            response.close()

            return status in (
                200,
                206,
            )

        except Exception as exc:
            print(
                "FNV3 availability probe failed:",
                cycle,
                type(exc).__name__,
                exc,
            )

            return False


    def latest_cycle(self):
        if not self.available():
            raise RuntimeError(
                "FNV3 Weather Lab feed "
                "is disabled."
            )

        now = datetime.now(
            timezone.utc
        )

        latest_hour = (
            now.hour
            // 6
            * 6
        )

        candidate = now.replace(
            hour=latest_hour,
            minute=0,
            second=0,
            microsecond=0,
        )

        lookback = int(
            FNV3_SOURCE[
                "latest_cycle_lookback"
            ]
        )

        for offset in range(
            lookback
        ):
            dt = (
                candidate
                - timedelta(
                    hours=6 * offset
                )
            )

            cycle = dt.strftime(
                "%Y%m%d%H"
            )

            print(
                "Checking FNV3 cycle:",
                cycle,
            )

            if self._remote_cycle_exists(
                cycle
            ):
                print(
                    "Latest FNV3 cycle:",
                    cycle,
                )

                return cycle

        raise RuntimeError(
            "Could not locate an available "
            "Weather Lab FNV3 cycle within "
            f"{lookback} cycles."
        )

    def load_cycle(
        self,
        cycle,
        overwrite=False,
    ):
        if not self.available():
            raise RuntimeError(
                "FNV3 Weather Lab feed "
                "is disabled."
            )

        cycle = self._normalize_cycle(
            cycle
        )

        url = self.build_url(
            cycle
        )

        cycle_dir = (
            self.cache_dir
            / cycle
        )

        cycle_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            cycle_dir
            / (
                f"OPER_{cycle}_"
                "atcf_a_deck.txt"
            )
        )

        if (
            output_path.exists()
            and not overwrite
        ):
            if (
                output_path.stat().st_size
                > 0
            ):
                print(
                    "Using cached FNV3 file:",
                    output_path,
                )

                return output_path

        print(
            "Downloading FNV3:",
            cycle,
        )

        print(
            "URL:",
            url,
        )

        timeout = (
            FNV3_SOURCE[
                "request_timeout"
            ]
        )

        response = self.session.get(
            url,
            allow_redirects=True,
            timeout=timeout,
        )

        response.raise_for_status()

        content = response.content

        if not content:
            raise RuntimeError(
                "Weather Lab returned an "
                "empty FNV3 file."
            )

        text_prefix = content[
            :4096
        ].decode(
            "utf-8",
            errors="ignore",
        )

        if "# BEGIN DATA" not in text_prefix:
            raise RuntimeError(
                "Downloaded Weather Lab "
                "response does not look like "
                "an ATCF A-deck."
            )

        output_path.write_bytes(
            content
        )

        print(
            "Saved:",
            output_path,
        )

        print(
            "Size:",
            output_path.stat().st_size,
            "bytes",
        )

        return output_path
