from __future__ import annotations

from collections import defaultdict

from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)

import json
import math
import os
import tempfile

from pathlib import Path

from urllib.error import (
    HTTPError,
    URLError,
)

from urllib.parse import urlencode

from urllib.request import (
    Request,
    urlopen,
)


# ============================================================
# CURRENT ANALYSIS — GFS STRATOSPHERIC WIND
# ============================================================
#
# Near-real-time extension for:
#
#     10 hPa
#     60°N
#     zonal-mean zonal wind
#
# ERA5 remains the authoritative historical archive.
#
# GFS analysis is used ONLY for dates later than the newest
# available ERA5 / ERA5T date.
#
# Operational source:
#
# NOAA/NCEP NOMADS GFS 0.25-degree analysis (f000)
#
# We request only:
#
#     UGRD
#     10 mb
#     narrow latitude strip around 60°N
#     all longitudes
#
# so we never download a complete global GFS GRIB.
# ============================================================


LEVEL_HPA = 10

LATITUDE = 60.0

LATITUDE_TOLERANCE = 0.25

SOURCE_ID = "gfs_analysis"

SOURCE_NAME = "NCEP GFS Analysis"


# ============================================================
# GCS PRODUCT
# ============================================================

ANALYSIS_ROOT = "analysis"

PRODUCT_KEY = "10hpa_60n_zonal_wind"

PRODUCT_ROOT = (
    f"{ANALYSIS_ROOT}/"
    f"polar_vortex/"
    f"{PRODUCT_KEY}"
)

GFS_RECENT_OBJECT = (
    f"{PRODUCT_ROOT}/"
    f"gfs_recent.json"
)


# ============================================================
# GFS CONFIGURATION
# ============================================================

GFS_CYCLES = (
    0,
    6,
    12,
    18,
)

DEFAULT_LOOKBACK_DAYS = int(
    os.getenv(
        "GFS_STRATWIND_LOOKBACK_DAYS",
        "10",
    )
)

HTTP_TIMEOUT_SECONDS = int(
    os.getenv(
        "GFS_STRATWIND_HTTP_TIMEOUT",
        "60",
    )
)


NOMADS_FILTER_URL = (
    "https://nomads.ncep.noaa.gov/"
    "cgi-bin/filter_gfs_0p25.pl"
)


# ============================================================
# SMALL HELPERS
# ============================================================

def utc_now():
    return datetime.now(
        timezone.utc
    )


def utc_now_iso():
    return (
        utc_now()
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def normalize_date(
    value,
):
    if isinstance(
        value,
        datetime,
    ):

        return value.date()

    if isinstance(
        value,
        date,
    ):

        return value

    return date.fromisoformat(
        str(
            value
        )
    )


def normalize_daily_record(
    *,
    valid_date,
    value_ms,
    cycles=None,
):
    valid_date = normalize_date(
        valid_date
    )

    cycles = sorted(
        {
            int(
                cycle
            )
            for cycle
            in (
                cycles
                or []
            )
        }
    )

    return {
        "date": (
            valid_date.isoformat()
        ),

        "value_ms": (
            float(
                value_ms
            )
        ),

        "source": (
            SOURCE_ID
        ),

        "source_name": (
            SOURCE_NAME
        ),

        "level_hpa": (
            LEVEL_HPA
        ),

        "latitude": (
            LATITUDE
        ),

        "cycles_used": (
            cycles
        ),

        "cycle_count": (
            len(
                cycles
            )
        ),
    }


# ============================================================
# NOMADS REQUEST
# ============================================================

def build_nomads_url(
    *,
    valid_date,
    cycle_hour,
):
    valid_date = normalize_date(
        valid_date
    )

    cycle_hour = int(
        cycle_hour
    )

    cycle_text = (
        f"{cycle_hour:02d}"
    )

    filename = (
        f"gfs.t"
        f"{cycle_text}"
        f"z.pgrb2.0p25.f000"
    )

    directory = (
        f"/gfs."
        f"{valid_date:%Y%m%d}/"
        f"{cycle_text}/"
        f"atmos"
    )

    params = {
        "file":
            filename,

        "lev_10_mb":
            "on",

        "var_UGRD":
            "on",

        "subregion":
            "",

        "leftlon":
            "0",

        "rightlon":
            "360",

        "toplat":
            str(
                LATITUDE
                +
                LATITUDE_TOLERANCE
            ),

        "bottomlat":
            str(
                LATITUDE
                -
                LATITUDE_TOLERANCE
            ),

        "dir":
            directory,
    }

    return (
        NOMADS_FILTER_URL
        +
        "?"
        +
        urlencode(
            params
        )
    )


def download_analysis_slice(
    *,
    valid_date,
    cycle_hour,
    destination,
):
    """
    Download only the GFS f000 10-mb U-wind latitude strip.

    Returns True when a usable GRIB was downloaded.

    A 404/403/empty response is treated as "cycle not available"
    rather than a fatal pipeline error.
    """

    url = build_nomads_url(
        valid_date=valid_date,
        cycle_hour=cycle_hour,
    )

    destination = Path(
        destination
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "MassachusettsWx Current Analysis/1.0",
        },
    )

    try:

        with urlopen(
            request,
            timeout=(
                HTTP_TIMEOUT_SECONDS
            ),
        ) as response:

            data = (
                response.read()
            )

    except HTTPError as error:

        if error.code in {
            403,
            404,
        }:

            return False

        raise

    except URLError:

        return False


    # GRIB files begin with GRIB.
    if (
        len(
            data
        )
        <
        16
        or
        not data.startswith(
            b"GRIB"
        )
    ):

        return False


    destination.write_bytes(
        data
    )

    return True


# ============================================================
# GRIB EXTRACTION
# ============================================================

def read_zonal_mean_from_grib(
    path,
):
    """
    Read one tiny filtered GRIB and return the 60°N zonal mean.

    cfgrib is imported locally so importing this module does not
    require eccodes inside the lightweight Cloud Run web service.
    """

    import xarray as xr

    path = Path(
        path
    )

    dataset = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={
            "indexpath":
                "",
        },
    )

    try:

        variable_name = None

        for candidate in (
            "u",
            "ugrd",
            "u10",
        ):

            if candidate in (
                dataset.data_vars
            ):

                variable_name = (
                    candidate
                )

                break


        if variable_name is None:

            if (
                len(
                    dataset.data_vars
                )
                ==
                1
            ):

                variable_name = (
                    next(
                        iter(
                            dataset.data_vars
                        )
                    )
                )

            else:

                raise RuntimeError(
                    "Could not identify GFS "
                    "zonal-wind variable. "
                    f"Available: "
                    f"{list(dataset.data_vars)}"
                )


        wind = dataset[
            variable_name
        ]


        # ----------------------------------------------------
        # PRESSURE LEVEL
        # ----------------------------------------------------

        for coordinate in (
            "isobaricInhPa",
            "isobaricInPa",
            "level",
        ):

            if coordinate not in (
                wind.coords
            ):

                continue

            pressure_coord = (
                wind[
                    coordinate
                ]
            )

            # ------------------------------------------------
            # NOMADS was already filtered to one pressure level.
            #
            # cfgrib therefore commonly exposes isobaricInhPa
            # as a scalar (0-dimensional) coordinate rather than
            # an indexed dimension. In that case there is nothing
            # left to select.
            # ------------------------------------------------

            if (
                pressure_coord.ndim
                ==
                0
            ):

                pressure_value = float(
                    pressure_coord.values
                )

                expected = (
                    LEVEL_HPA * 100
                    if pressure_value > 2000
                    else LEVEL_HPA
                )

                if (
                    abs(
                        pressure_value
                        -
                        expected
                    )
                    >
                    1.0
                ):

                    raise RuntimeError(
                        "GFS stratwind: "
                        f"unexpected pressure level "
                        f"{pressure_value} "
                        f"from filtered GRIB."
                    )

                break


            coordinate_values = (
                pressure_coord.values
            )

            try:

                maximum = float(
                    coordinate_values.max()
                )

            except Exception:

                maximum = 0.0


            target = (
                LEVEL_HPA * 100
                if maximum > 2000
                else LEVEL_HPA
            )

            wind = wind.sel(
                {
                    coordinate:
                        target
                },
                method="nearest",
            )

            break


        # ----------------------------------------------------
        # LATITUDE
        # ----------------------------------------------------

        latitude_name = None

        for candidate in (
            "latitude",
            "lat",
        ):

            if candidate in (
                wind.coords
            ):

                latitude_name = (
                    candidate
                )

                break


        if latitude_name is None:

            raise RuntimeError(
                "GFS stratwind: "
                "latitude coordinate not found."
            )


        wind = wind.sel(
            {
                latitude_name:
                    LATITUDE
            },
            method="nearest",
        )


        # ----------------------------------------------------
        # LONGITUDE / ZONAL MEAN
        # ----------------------------------------------------

        longitude_name = None

        for candidate in (
            "longitude",
            "lon",
        ):

            if candidate in (
                wind.coords
            ):

                longitude_name = (
                    candidate
                )

                break


        if longitude_name is None:

            raise RuntimeError(
                "GFS stratwind: "
                "longitude coordinate not found."
            )


        zonal_mean = (
            wind.mean(
                dim=(
                    longitude_name
                ),
                skipna=True,
            )
        )


        values = (
            zonal_mean.values
        )


        value = float(
            values
        )


        if not math.isfinite(
            value
        ):

            raise RuntimeError(
                "GFS stratwind: "
                "non-finite zonal mean."
            )


        return value

    finally:

        dataset.close()


# ============================================================
# ONE ANALYSIS CYCLE
# ============================================================

def fetch_cycle_value(
    *,
    valid_date,
    cycle_hour,
):
    valid_date = normalize_date(
        valid_date
    )

    cycle_hour = int(
        cycle_hour
    )

    with tempfile.TemporaryDirectory(
        prefix="masswx-gfs-stratwind-"
    ) as temp_directory:

        grib_path = (
            Path(
                temp_directory
            )
            /
            (
                f"gfs_"
                f"{valid_date:%Y%m%d}_"
                f"{cycle_hour:02d}z_"
                f"10hpa_60n.grib2"
            )
        )


        available = (
            download_analysis_slice(
                valid_date=(
                    valid_date
                ),
                cycle_hour=(
                    cycle_hour
                ),
                destination=(
                    grib_path
                ),
            )
        )


        if not available:

            return None


        value = (
            read_zonal_mean_from_grib(
                grib_path
            )
        )


        return {
            "date":
                valid_date.isoformat(),

            "cycle_hour":
                cycle_hour,

            "value_ms":
                float(
                    value
                ),
        }


# ============================================================
# DAILY GFS ANALYSIS
# ============================================================

def fetch_daily_gfs_analysis(
    *,
    start_date,
    end_date,
):
    """
    Fetch f000 analyses for each available GFS cycle and make a
    daily mean.

    A completed day normally contains four cycles:
        00 / 06 / 12 / 18 UTC

    The current day may contain fewer. That is allowed; cycle_count
    tells the frontend / metadata how many analyses contributed.
    """

    start_date = normalize_date(
        start_date
    )

    end_date = normalize_date(
        end_date
    )

    if end_date < start_date:

        return []


    values_by_date = defaultdict(
        list
    )

    cycles_by_date = defaultdict(
        list
    )


    current_date = start_date

    while (
        current_date
        <=
        end_date
    ):

        for cycle_hour in (
            GFS_CYCLES
        ):

            print(
                f"GFS stratwind: "
                f"{current_date} "
                f"{cycle_hour:02d}z"
            )

            try:

                record = (
                    fetch_cycle_value(
                        valid_date=(
                            current_date
                        ),
                        cycle_hour=(
                            cycle_hour
                        ),
                    )
                )

            except Exception as error:

                print(
                    f"GFS stratwind: "
                    f"{current_date} "
                    f"{cycle_hour:02d}z "
                    f"failed: "
                    f"{error}"
                )

                continue


            if record is None:

                print(
                    f"GFS stratwind: "
                    f"{current_date} "
                    f"{cycle_hour:02d}z "
                    f"not available"
                )

                continue


            values_by_date[
                current_date
            ].append(
                float(
                    record[
                        "value_ms"
                    ]
                )
            )

            cycles_by_date[
                current_date
            ].append(
                cycle_hour
            )


        current_date += timedelta(
            days=1
        )


    daily_records = []


    for valid_date in sorted(
        values_by_date
    ):

        values = (
            values_by_date[
                valid_date
            ]
        )


        if not values:

            continue


        daily_value = (
            sum(
                values
            )
            /
            len(
                values
            )
        )


        daily_records.append(
            normalize_daily_record(
                valid_date=(
                    valid_date
                ),
                value_ms=(
                    daily_value
                ),
                cycles=(
                    cycles_by_date[
                        valid_date
                    ]
                ),
            )
        )


    return daily_records


# ============================================================
# ERA5 / GFS MERGE
# ============================================================

def merge_era5_and_gfs(
    *,
    era5_records,
    gfs_records,
):
    """
    Merge using strict source precedence.

    ERA5 always wins.

    GFS may ONLY extend dates later than the latest ERA5 date.
    """

    merged = {}


    for record in (
        era5_records
        or []
    ):

        if not isinstance(
            record,
            dict,
        ):

            continue


        record_date = (
            record.get(
                "date"
            )
        )


        if not record_date:

            continue


        merged[
            str(
                record_date
            )
        ] = dict(
            record
        )


    latest_era5_date = (
        max(
            merged
        )
        if merged
        else None
    )


    for record in (
        gfs_records
        or []
    ):

        if not isinstance(
            record,
            dict,
        ):

            continue


        record_date = (
            record.get(
                "date"
            )
        )


        if not record_date:

            continue


        record_date = str(
            record_date
        )


        if (
            latest_era5_date
            is not None
            and
            record_date
            <=
            latest_era5_date
        ):

            continue


        merged[
            record_date
        ] = dict(
            record
        )


    return [
        merged[
            record_date
        ]
        for record_date
        in sorted(
            merged
        )
    ]


# ============================================================
# GCS
# ============================================================

def get_bucket():
    """
    Reuse the site's configured shared storage bucket.
    """

    from shared.storage import (
        get_bucket as shared_get_bucket,
    )

    return shared_get_bucket()


def upload_json(
    object_name,
    payload,
):
    bucket = get_bucket()

    blob = bucket.blob(
        object_name
    )

    blob.upload_from_string(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        content_type=(
            "application/json"
        ),
    )


def download_json(
    object_name,
):
    bucket = get_bucket()

    blob = bucket.blob(
        object_name
    )

    if not blob.exists():

        return None


    try:

        return json.loads(
            blob.download_as_text()
        )

    except Exception:

        return None


# ============================================================
# DISCOVER ERA5 FRONTIER
# ============================================================

def get_latest_era5_date():
    """
    Read the existing ERA5 latest.json.

    Expected existing field:
        latest_date

    This keeps GFS independent of ERA5 internals.
    """

    latest_object = (
        f"{PRODUCT_ROOT}/"
        f"latest.json"
    )

    payload = download_json(
        latest_object
    )


    if not payload:

        return None


    latest_date = (
        payload.get(
            "latest_era5_date"
        )
        or
        payload.get(
            "latest_date"
        )
    )


    if not latest_date:

        return None


    try:

        return date.fromisoformat(
            str(
                latest_date
            )
        )

    except ValueError:

        return None


# ============================================================
# PUBLISH RECENT GFS EXTENSION
# ============================================================

def build_gfs_recent_payload(
    *,
    records,
    era5_latest_date,
):
    records = list(
        records
        or []
    )

    latest_record = (
        records[
            -1
        ]
        if records
        else None
    )


    return {
        "schema_version":
            1,

        "product":
            PRODUCT_KEY,

        "source":
            SOURCE_ID,

        "source_name":
            SOURCE_NAME,

        "level_hpa":
            LEVEL_HPA,

        "latitude":
            LATITUDE,

        "generated_at_utc":
            utc_now_iso(),

        "era5_latest_date":
            (
                era5_latest_date.isoformat()
                if era5_latest_date
                else None
            ),

        "first_gfs_date":
            (
                records[
                    0
                ][
                    "date"
                ]
                if records
                else None
            ),

        "latest_gfs_date":
            (
                latest_record[
                    "date"
                ]
                if latest_record
                else None
            ),

        "latest_value_ms":
            (
                latest_record[
                    "value_ms"
                ]
                if latest_record
                else None
            ),

        "record_count":
            len(
                records
            ),

        "records":
            records,
    }


def publish_recent_gfs_extension(
    *,
    lookback_days=(
        DEFAULT_LOOKBACK_DAYS
    ),
):
    """
    Fetch recent GFS analysis and publish gfs_recent.json.

    If ERA5 latest.json exists:
        begin the day AFTER latest ERA5.

    We also bound retrieval to lookback_days so a stale/missing
    ERA5 archive cannot accidentally trigger a huge GFS download.
    """

    today = (
        utc_now()
        .date()
    )


    era5_latest_date = (
        get_latest_era5_date()
    )


    fallback_start = (
        today
        -
        timedelta(
            days=max(
                1,
                int(
                    lookback_days
                )
            )
        )
    )


    if era5_latest_date:

        start_date = max(
            fallback_start,
            (
                era5_latest_date
                +
                timedelta(
                    days=1
                )
            ),
        )

    else:

        start_date = (
            fallback_start
        )


    print(
        "GFS stratwind extension:"
    )

    print(
        "  ERA5 latest:",
        (
            era5_latest_date
            if era5_latest_date
            else "unknown"
        ),
    )

    print(
        "  GFS start:",
        start_date,
    )

    print(
        "  GFS end:",
        today,
    )


    if start_date > today:

        records = []

    else:

        records = (
            fetch_daily_gfs_analysis(
                start_date=(
                    start_date
                ),
                end_date=(
                    today
                ),
            )
        )


    payload = (
        build_gfs_recent_payload(
            records=records,
            era5_latest_date=(
                era5_latest_date
            ),
        )
    )


    upload_json(
        GFS_RECENT_OBJECT,
        payload,
    )


    print(
        f"GFS stratwind published: "
        f"{GFS_RECENT_OBJECT}"
    )

    print(
        f"GFS days published: "
        f"{len(records)}"
    )


    return payload


# ============================================================
# PROBE
# ============================================================

def probe_gfs_stratwind():
    """
    Fetch the newest available analysis from today/yesterday.

    Does not publish anything.
    """

    today = (
        utc_now()
        .date()
    )


    for offset in (
        0,
        1,
    ):

        valid_date = (
            today
            -
            timedelta(
                days=offset
            )
        )


        for cycle_hour in reversed(
            GFS_CYCLES
        ):

            print(
                f"Probe GFS stratwind: "
                f"{valid_date} "
                f"{cycle_hour:02d}z"
            )


            try:

                result = (
                    fetch_cycle_value(
                        valid_date=(
                            valid_date
                        ),
                        cycle_hour=(
                            cycle_hour
                        ),
                    )
                )

            except Exception as error:

                print(
                    "  failed:",
                    error,
                )

                continue


            if result is None:

                print(
                    "  unavailable"
                )

                continue


            print(
                "  SUCCESS"
            )

            print(
                "  value:",
                f"{result['value_ms']:.2f} m/s",
            )

            return result


    raise RuntimeError(
        "No usable recent GFS "
        "10-hPa analysis found."
    )
