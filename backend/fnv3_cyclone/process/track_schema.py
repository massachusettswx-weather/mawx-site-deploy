from dataclasses import dataclass


@dataclass
class FNV3TrackPoint:
    system_id: str
    member: int
    forecast_hour: int

    latitude: float
    longitude: float

    max_wind_kt: float | None = None
    mslp_hpa: float | None = None

    genesis: bool = False
    existing_storm: bool = False

    radius_max_wind_km: float | None = None

    r34_ne_km: float | None = None
    r34_se_km: float | None = None
    r34_sw_km: float | None = None
    r34_nw_km: float | None = None

    r50_ne_km: float | None = None
    r50_se_km: float | None = None
    r50_sw_km: float | None = None
    r50_nw_km: float | None = None

    r64_ne_km: float | None = None
    r64_se_km: float | None = None
    r64_sw_km: float | None = None
    r64_nw_km: float | None = None
