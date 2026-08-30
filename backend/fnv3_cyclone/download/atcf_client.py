from pathlib import Path


GOOGLE_ATCF_AIDS = {
    f"F{i:03d}"
    for i in range(50)
    for i in range(50)
    for i in range(50)
}


class FNV3CycloneClient:
    """
    Parser for publicly disseminated Google DeepMind
    tropical cyclone guidance in NHC ATCF aid decks.

    Known Google aids include:
        GDMN
        GDMI
        GDM2

    Individual ensemble-member tracks will be ingested
    separately from the WeatherNext/WeatherLab cyclone feed.
    """

    def __init__(self, cache_dir=None):
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

    @staticmethod
    def _parse_latlon(value):
        value = value.strip().upper()

        if not value:
            return None

        hemisphere = value[-1]

        number = float(
            value[:-1]
        ) / 10.0

        if hemisphere in ("S", "W"):
            number *= -1

        return number

    def parse_atcf(self, text):
        """
        Parse the operational Weather Lab FNV3 ATCF A-deck.

        IMPORTANT
        ---------
        F000-F049 are ENSEMBLE MEMBER identifiers.

        They are NOT cyclone/system identifiers.

        ATCF columns provide the real storm identity:

            parts[0] = basin
            parts[1] = storm number
            parts[4] = model/member aid

        Example:

            AL, 04, ..., F017, ...

        becomes:

            system_id   = "AL04"
            basin       = "AL"
            storm_number= "04"
            aid         = "F017"
            member      = 17

        This keeps storm identity and ensemble membership
        completely independent.
        """

        rows = []

        if not text:
            return rows

        for raw_line in str(text).splitlines():

            line = raw_line.strip()

            if not line:
                continue

            parts = [
                part.strip()
                for part in line.split(",")
            ]

            # Need through MSLP at minimum.
            if len(parts) < 10:
                continue

            basin = (
                parts[0]
                .strip()
                .upper()
            )

            storm_number = (
                parts[1]
                .strip()
                .upper()
            )

            cycle = (
                parts[2]
                .strip()
            )

            aid = (
                parts[4]
                .strip()
                .upper()
            )

            # Only the actual operational FNV3 members.
            if aid not in GOOGLE_ATCF_AIDS:
                continue

            try:
                member = int(
                    aid[1:]
                )
            except Exception:
                continue

            # Source truth is F000-F049.
            if not 0 <= member < 50:
                continue

            try:
                forecast_hour = int(
                    parts[5]
                )
            except Exception:
                continue

            # ------------------------------------------------
            # Latitude / longitude
            # ATCF examples:
            #   156N
            #   485W
            # ------------------------------------------------

            lat_text = (
                parts[6]
                .strip()
                .upper()
            )

            lon_text = (
                parts[7]
                .strip()
                .upper()
            )

            try:
                lat_value = float(
                    lat_text[:-1]
                ) / 10.0

                if lat_text.endswith("S"):
                    lat_value *= -1.0

                lon_value = float(
                    lon_text[:-1]
                ) / 10.0

                if lon_text.endswith("W"):
                    lon_value *= -1.0

            except Exception:
                continue

            try:
                max_wind_kt = float(
                    parts[8]
                )
            except Exception:
                max_wind_kt = None

            try:
                min_pressure_hpa = float(
                    parts[9]
                )
            except Exception:
                min_pressure_hpa = None

            # ------------------------------------------------
            # REAL cyclone identity.
            #
            # Never use aid/member here.
            # ------------------------------------------------

            if basin and storm_number:
                system_id = (
                    f"{basin}{storm_number}"
                )
            else:
                system_id = None

            rows.append(
                {
                    "system_id": system_id,
                    "basin": basin,
                    "storm_number": storm_number,
                    "aid": aid,
                    "member": member,
                    "cycle": cycle,
                    "forecast_hour": forecast_hour,
                    "latitude": lat_value,
                    "longitude": lon_value,
                    "max_wind_kt": max_wind_kt,
                    "min_pressure_hpa": (
                        min_pressure_hpa
                    ),
                }
            )

        return rows
