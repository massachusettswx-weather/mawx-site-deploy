from dataclasses import dataclass


@dataclass
class TrackedSystem:
    system_id: str

    member: int
    forecast_hour: int

    latitude: float
    longitude: float

    mslp_hpa: float | None = None
    max_wind_kt: float | None = None

    genesis: bool = False
    existing_storm: bool = False


class FNV3DirectTracker:
    """
    Interface for generalized FNV3 cyclone tracking.

    Systems do NOT require an NHC/JTWC storm identifier.
    """

    def track_member(
        self,
        member,
        forecast,
    ):
        raise NotImplementedError

    def track_ensemble(
        self,
        forecast,
    ):
        raise NotImplementedError
