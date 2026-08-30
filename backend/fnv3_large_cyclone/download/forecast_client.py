from pathlib import Path

from .source_config import FNV3_LARGE_SOURCE


class FNV3LargeForecastClient:
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = (
                Path(__file__).resolve().parents[1]
                / "output"
                / "raw"
            )

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def available(self):
        return bool(FNV3_LARGE_SOURCE["enabled"])

    def latest_cycle(self):
        if not self.available():
            raise RuntimeError(
                "FNV3-L generalized cyclone feed is not enabled yet."
            )

        raise NotImplementedError

    def load_cycle(self, cycle):
        if not self.available():
            raise RuntimeError(
                "FNV3-L generalized cyclone feed is not enabled yet."
            )

        raise NotImplementedError
