from pathlib import Path
import json


class FNV3LargeClient:
    """
    Ingestion client for the 1000-member WeatherNext
    Cyclones ensemble used by FNV3-L products.
    """

    EXPECTED_MEMBERS = 1000

    def __init__(self, source_dir=None):
        if source_dir is None:
            source_dir = (
                Path(__file__).resolve().parents[1]
                / "incoming"
            )

        self.source_dir = Path(source_dir)
        self.source_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def cycle_path(self, cycle):
        return (
            self.source_dir
            / str(cycle)
            / "tracks.json"
        )

    def cycle_exists(self, cycle):
        return self.cycle_path(cycle).exists()

    def load_cycle(self, cycle):
        path = self.cycle_path(cycle)

        if not path.exists():
            raise FileNotFoundError(
                f"FNV3-L cycle not available: {path}"
            )

        with path.open("r") as f:
            payload = json.load(f)

        tracks = payload.get("tracks", [])

        members = {
            int(point["member"])
            for point in tracks
            if point.get("member") is not None
        }

        print(
            f"Loaded FNV3-L cycle {cycle}: "
            f"{len(members)} members, "
            f"{len(tracks)} track points"
        )

        return payload
