from dataclasses import dataclass


@dataclass
class CyclonePoint:
    member: int
    forecast_hour: int

    latitude: float
    longitude: float

    mslp_hpa: float | None = None
    max_wind_kt: float | None = None


class FNV3CycloneTracker:
    """
    Tracker for FNV3 Cyclone ensemble members.
    """

    def __init__(self):
        self.tracks = {}

    def track_member(
        self,
        member,
        dataset,
    ):
        """
        Track tropical systems for one ensemble member.

        Detection/tracking logic will be implemented after
        the exact FNV3 Cyclone fields are established.
        """

        raise NotImplementedError(
            "Cyclone detection algorithm "
            "has not been configured yet."
        )

    def track_ensemble(self, dataset):
        """
        Track all FNV3 Cyclone ensemble members.
        """

        raise NotImplementedError(
            "FNV3 Cyclone ensemble tracking "
            "has not been configured yet."
        )
