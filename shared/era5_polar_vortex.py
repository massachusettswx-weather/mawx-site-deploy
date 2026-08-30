from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from shared.state import (
    acquire_lock,
    load_state,
    mark_run_failure,
    mark_run_started,
    mark_run_success,
    release_lock,
    update_state,
)

from shared.storage import (
    get_bucket,
    upload_bytes,
)


# ============================================================
# SMALL LOCAL HELPERS
#
# shared/publish.py has an upload_json()/utc_now_iso() pair that do
# the same thing, but importing shared.publish transitively pulls in
# shared.runner -> shared.plotting/shared.download, which require
# matplotlib/cartopy/cfgrib. Those are unrelated to ERA5 ingestion,
# so this module reimplements the two small helpers locally to keep
# its own dependency footprint limited to shared.storage (which only
# needs google-cloud-storage) plus xarray/numpy/cdsapi.
# ============================================================

def utc_now_iso() -> str:

    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def upload_json(
    object_name: str,
    payload: dict,
) -> str:

    data = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        .encode(
            "utf-8"
        )
    )

    return upload_bytes(
        data,
        object_name,
        content_type=(
            "application/json"
        ),
    )


# ============================================================
# CURRENT ANALYSIS: POLAR VORTEX
# ============================================================
#
# First Current Analysis product: 10 hPa, 60N zonal-mean zonal
# wind from ERA5 / ERA5T (Copernicus Climate Change Service).
#
# This is NOT a forecast-cycle pipeline like GFS/IFS/AIFS, so
# shared/cycles.py, shared/resume.py, shared/runner.py, and
# shared/sequence.py (all built around forecast hours and cycle
# readiness) intentionally are not used here. Instead this module
# follows the same *patterns* those modules establish elsewhere:
#
#   - shared.storage for all Cloud Storage I/O
#   - shared.state for local state/lock tracking of the ingestion
#     job (keyed by STATE_KEY below, same as a model name would be)
#   - shared.publish.upload_json for uploading JSON payloads
#
# Storage layout in the shared bucket (see shared/storage.py for
# the bucket itself):
#
#   analysis/polar_vortex/10hpa_60n_zonal_wind/series/{year}.json
#       -> one compact file per year, the source of truth.
#          Written once during backfill, appended to daily.
#
#   analysis/polar_vortex/10hpa_60n_zonal_wind/bundle.json
#       -> all years combined into a single file for the frontend,
#          rebuilt cheaply from the per-year files above (no
#          re-downloading of ERA5 required to rebuild this).
#
#   analysis/polar_vortex/10hpa_60n_zonal_wind/latest.json
#       -> current value, latest date, easterly/westerly state,
#          historical percentile, and other summary stats.
#
# Retrieval uses ECMWF's ARCO (Analysis-Ready, Cloud-Optimized) Zarr
# store over HTTPS -- the same mechanism already proven for surface
# fields in the ~/era5 sandbox scripts (get_t2m/open_era5), rather
# than the classic cdsapi Toolbox request-and-wait-in-queue flow.
# ARCO reads exactly the time/level/latitude slice needed directly
# via HTTP range requests, so nothing is ever downloaded in bulk or
# persisted locally -- there's no temp file to clean up at all.
#
# The exact ARCO schema for pressure-level data (dataset URL,
# variable name, level coordinate name/units) was NOT confirmed at
# the time this was written, since it isn't reachable from the
# environment this was developed in. The retrieval code below tries
# multiple candidates defensively (matching the fallback style
# already used in ~/era5/era5.py for latitude/longitude conventions
# and variable names) and raises a clear, specific error listing
# what it tried if none match -- run with `--probe` first to see the
# real schema before running a full backfill.
# ============================================================


# ============================================================
# STATE / IDENTITY
# ============================================================

STATE_KEY = "era5_polar_vortex"

PRODUCT_KEY = "10hpa_60n_zonal_wind"

ANALYSIS_ROOT = "analysis"

PRODUCT_ROOT = (
    f"{ANALYSIS_ROOT}/polar_vortex/{PRODUCT_KEY}"
)


# ============================================================
# PHYSICAL / RETRIEVAL CONFIGURATION
# ============================================================

ERA5_LEVEL_HPA = 10

ERA5_LATITUDE = 60.0

ERA5_START_DATE = date(1940, 1, 1)

# ERA5T (near-real-time) typically lags real time by several days
# in the classic CDS Toolbox. Whether the ARCO store carries ERA5T
# at all -- or only finalized ERA5, which would lag much further --
# is one of the open questions `--probe` is meant to answer. This is
# a starting assumption, not a confirmed value.
ERA5T_LAG_DAYS = 5

# How many days on either side of a calendar date to pool together
# when computing a "historical percentile" for that date.
PERCENTILE_WINDOW_DAYS = 5


# ============================================================
# ARCO RETRIEVAL CONFIGURATION
# ============================================================
#
# ARCO_PRESSURE_URL_CANDIDATES: guesses at the pressure-level sibling
# of the confirmed-working surface-level URL
# (.../reanalysis_era5_single_levels/sfc/timeChunked.zarr, see
# ~/era5/era5.py). `--probe` reports which one (if any) actually
# opens, and prints the real variable/coordinate names so this list
# can be corrected once known.
# ============================================================

ARCO_BASE_URL = (
    "https://arco.datastores.ecmwf.int/"
    "cadl-arco-time-048/arco"
)

ARCO_PRESSURE_URL_CANDIDATES = [
    f"{ARCO_BASE_URL}/reanalysis_era5_pressure_levels/pl/timeChunked.zarr",
    f"{ARCO_BASE_URL}/reanalysis_era5_pressure_levels/timeChunked.zarr",
]

# Candidate names for the eastward (zonal) wind variable.
ARCO_U_WIND_VARIABLE_NAMES = (
    "u",
    "u_component_of_wind",
)

# Candidate names for the pressure-level coordinate.
ARCO_LEVEL_COORD_NAMES = (
    "pressureLevel",
    "level",
    "pressure_level",
    "isobaricInhPa",
)


# ============================================================
# OBJECT NAMING
# ============================================================

def object_name_year(
    year: int,
) -> str:

    return (
        f"{PRODUCT_ROOT}/series/{int(year)}.json"
    )


def object_name_bundle() -> str:

    return (
        f"{PRODUCT_ROOT}/bundle.json"
    )


def object_name_latest() -> str:

    return (
        f"{PRODUCT_ROOT}/latest.json"
    )


# ============================================================
# YEAR SERIES: LOAD / SAVE / MERGE
#
# Stored format for one year:
#
#   {
#     "year": 1940,
#     "level_hpa": 10,
#     "latitude": 60.0,
#     "daily": [["1940-01-01", 5.2], ["1940-01-02", 4.8], ...]
#   }
#
# [date, value] pairs (rather than repeated keys) keep the file
# small, since this is downloaded by the frontend at page load.
# ============================================================

def load_year_series(
    year: int,
) -> dict | None:
    """
    Read one year's stored series from Cloud Storage.

    Returns None if the year has never been processed or the
    stored object is unreadable.
    """

    object_name = (
        object_name_year(
            year
        )
    )

    try:

        blob = (
            get_bucket()
            .blob(
                object_name
            )
        )

        if not blob.exists():

            return None

        text = (
            blob.download_as_text()
        )

        payload = json.loads(
            text
        )

        if not isinstance(
            payload,
            dict,
        ):

            return None

        return payload

    except Exception as error:

        print(
            f"ERA5 PV: failed to load "
            f"{object_name}: {error}"
        )

        return None


def _year_payload_to_mapping(
    payload: dict,
) -> dict:

    mapping = {}

    for entry in payload.get(
        "daily",
        [],
    ):

        try:

            date_str, value = entry

            mapping[
                str(date_str)
            ] = float(value)

        except (
            ValueError,
            TypeError,
        ):

            continue

    return mapping


def _mapping_to_year_payload(
    year: int,
    mapping: dict,
) -> dict:

    daily = sorted(
        mapping.items()
    )

    return {
        "year": int(year),

        "level_hpa": ERA5_LEVEL_HPA,

        "latitude": ERA5_LATITUDE,

        "daily": [
            [date_str, round(value, 3)]
            for date_str, value in daily
        ],
    }


def save_year_series(
    year: int,
    mapping: dict,
) -> dict:
    """
    Write one year's series (date -> value mapping) to Cloud Storage.
    """

    payload = (
        _mapping_to_year_payload(
            year,
            mapping,
        )
    )

    upload_json(
        object_name_year(
            year
        ),
        payload,
    )

    return payload


def merge_year(
    year: int,
    new_points: dict,
) -> dict:
    """
    Merge newly fetched date->value points into a year's stored
    series (overwriting any overlapping dates, e.g. ERA5T being
    replaced by finalized ERA5) and save the result.
    """

    existing = (
        load_year_series(
            year
        )
    )

    mapping = (
        _year_payload_to_mapping(
            existing
        )
        if existing
        else {}
    )

    mapping.update(
        new_points
    )

    return save_year_series(
        year,
        mapping,
    )


def list_available_years() -> list:
    """
    List years that already have a stored series in Cloud Storage.

    This lists GCS objects rather than trusting local state, since
    GCS is the source of truth and this job may run on ephemeral
    compute with no persistent local state between runs.
    """

    prefix = (
        f"{PRODUCT_ROOT}/series/"
    )

    years = []

    for blob in (
        get_bucket().list_blobs(
            prefix=prefix
        )
    ):

        name = blob.name[
            len(prefix):
        ]

        if not name.endswith(
            ".json"
        ):

            continue

        try:

            years.append(
                int(
                    name[:-5]
                )
            )

        except ValueError:

            continue

    return sorted(
        years
    )


# ============================================================
# ARCO RETRIEVAL
# ============================================================

def get_cds_api_key() -> str:
    """
    Read the CDS API key used as an ARCO Bearer token.

    This matches ~/era5/era5.py's convention exactly: a CDS_API_KEY
    environment variable, NOT a ~/.cdsapirc file (that file format
    is for the older cdsapi Toolbox client, which this module does
    not use).
    """

    import os

    key = os.environ.get(
        "CDS_API_KEY"
    )

    if not key:

        raise RuntimeError(
            "CDS_API_KEY environment variable is not set."
        )

    return key


_pressure_dataset_cache = {
    "dataset": None,
    "url": None,
}


def open_era5_pressure_levels():
    """
    Open the ARCO pressure-level Zarr store, trying each candidate
    URL in ARCO_PRESSURE_URL_CANDIDATES until one opens successfully.
    Cached for the life of the process (same pattern as ~/era5's
    open_era5(), which also opens its store once per process).

    Returns (dataset, url_that_worked).
    """

    if (
        _pressure_dataset_cache["dataset"]
        is not None
    ):

        return (
            _pressure_dataset_cache["dataset"],
            _pressure_dataset_cache["url"],
        )

    import xarray as xr

    key = (
        get_cds_api_key()
    )

    attempted_errors = []

    for url in (
        ARCO_PRESSURE_URL_CANDIDATES
    ):

        try:

            dataset = xr.open_zarr(
                url,
                consolidated=True,
                storage_options={
                    "headers": {
                        "Authorization": (
                            f"Bearer {key}"
                        )
                    }
                },
            )

            _pressure_dataset_cache[
                "dataset"
            ] = dataset

            _pressure_dataset_cache[
                "url"
            ] = url

            print(
                f"ERA5 PV: opened ARCO "
                f"pressure-level store at {url}"
            )

            return dataset, url

        except Exception as error:

            attempted_errors.append(
                f"  {url}\n"
                f"    -> {error}"
            )

    raise RuntimeError(
        "ERA5 PV: could not open any ARCO "
        "pressure-level store. Tried:\n"
        + "\n".join(attempted_errors)
        + "\n\nRun with --probe to investigate, "
        "or update ARCO_PRESSURE_URL_CANDIDATES "
        "in shared/era5_polar_vortex.py once the "
        "correct URL is known."
    )


def _resolve_pressure_level_schema(
    dataset,
) -> tuple:
    """
    Figure out the actual variable name and level-coordinate name in
    the opened dataset, from the candidate lists above. Raises a
    clear error listing what IS available if nothing matches, so a
    failure is immediately actionable rather than a cryptic KeyError.
    """

    variable_name = None

    for name in (
        ARCO_U_WIND_VARIABLE_NAMES
    ):

        if name in dataset.data_vars:

            variable_name = name

            break

    if variable_name is None:

        raise KeyError(
            f"ERA5 PV: none of "
            f"{ARCO_U_WIND_VARIABLE_NAMES} found "
            f"in the pressure-level store. "
            f"Available data variables: "
            f"{list(dataset.data_vars)}"
        )

    level_coord = None

    for name in (
        ARCO_LEVEL_COORD_NAMES
    ):

        if name in dataset.coords:

            level_coord = name

            break

    if level_coord is None:

        raise KeyError(
            f"ERA5 PV: none of "
            f"{ARCO_LEVEL_COORD_NAMES} found as a "
            f"level coordinate. Available "
            f"coordinates: {list(dataset.coords)}"
        )

    return variable_name, level_coord


def _select_10hpa(
    data_array,
    level_coord: str,
):
    """
    Select the level nearest to 10 hPa, defensively handling either
    hPa-valued (e.g. 10) or Pa-valued (e.g. 1000) level coordinates
    -- the ARCO schema for this wasn't confirmed at write time.
    """

    values = (
        data_array[level_coord].values
    )

    if float(values.max()) > 2000:

        # Coordinate looks like it's in Pa, not hPa.
        return data_array.sel(
            {
                level_coord: (
                    ERA5_LEVEL_HPA * 100
                )
            },
            method="nearest",
        )

    return data_array.sel(
        {
            level_coord: ERA5_LEVEL_HPA
        },
        method="nearest",
    )


def fetch_zonal_mean_range(
    start_date: date,
    end_date: date,
) -> dict:
    """
    Fetch daily-mean, zonal-mean 10 hPa 60N u-wind for every day in
    [start_date, end_date] (inclusive), reading directly from the
    ARCO Zarr store. No bulk request queue, no temporary local
    files -- only the needed (1 latitude row) x (all longitudes) x
    (1 level) x (date range) slice is read over HTTP.
    """

    dataset, _ = (
        open_era5_pressure_levels()
    )

    variable_name, level_coord = (
        _resolve_pressure_level_schema(
            dataset
        )
    )

    wind = dataset[
        variable_name
    ]

    time_coord = (
        "valid_time"
        if "valid_time" in wind.coords
        else "time"
    )

    wind = wind.sel(
        {
            time_coord: slice(
                start_date.isoformat(),
                end_date.isoformat(),
            )
        }
    )

    # Recent data can mix finalized ERA5 (expver=1) and near-real-
    # time ERA5T (expver=5) in one response, the same way the
    # classic CDS Toolbox does. Handle it if present; the surface
    # ARCO store in ~/era5/era5.py does not show this dimension, so
    # it may not apply here either -- harmless either way.
    if "expver" in wind.dims:

        preferred = wind.sel(
            expver=1
        )

        fallback = wind.sel(
            expver=5
        )

        wind = (
            preferred
            .combine_first(fallback)
        )

    wind = _select_10hpa(
        wind,
        level_coord,
    )

    # Nearest grid row to 60N (works for ascending or descending
    # latitude arrays, same defensive approach as
    # ~/era5/era5.py's _select_latitude).
    wind = wind.sel(
        latitude=ERA5_LATITUDE,
        method="nearest",
    )

    # Zonal mean: average across all longitudes.
    wind = wind.mean(
        dim="longitude"
    )

    wind = wind.load()

    daily_mean = wind.groupby(
        f"{time_coord}.date"
    ).mean()

    result = {}

    for day_value, wind_value in zip(
        daily_mean["date"].values,
        daily_mean.values,
    ):

        result[
            str(day_value)
        ] = float(
            wind_value
        )

    return result


def fetch_year_zonal_mean(
    year: int,
) -> dict:
    """
    Fetch a full year (used by the one-time historical backfill).
    """

    return fetch_zonal_mean_range(
        date(year, 1, 1),
        date(year, 12, 31),
    )


# ============================================================
# PROBE / DIAGNOSTIC
# ============================================================

def probe_arco_pressure_levels():
    """
    Open the ARCO pressure-level store and print everything needed
    to confirm (or correct) the retrieval assumptions above:
    variable names, level coordinate + values, and critically --
    the most recent available timestamp, which determines whether
    "automatic daily updates" are even possible from this store at
    all, or whether it only carries finalized ERA5 with a much
    longer lag than ERA5T.

    Run via: python jobs/update_polar_vortex.py --probe
    """

    dataset, url = (
        open_era5_pressure_levels()
    )

    print(
        f"URL that opened successfully: {url}"
    )

    print(
        f"Data variables: "
        f"{list(dataset.data_vars)}"
    )

    print(
        f"Coordinates: "
        f"{list(dataset.coords)}"
    )

    try:

        variable_name, level_coord = (
            _resolve_pressure_level_schema(
                dataset
            )
        )

        print(
            f"Resolved wind variable: "
            f"{variable_name}"
        )

        print(
            f"Resolved level coordinate: "
            f"{level_coord}"
        )

        level_values = (
            dataset[level_coord].values
        )

        print(
            f"Level values "
            f"(first 30): "
            f"{level_values[:30]}"
        )

    except KeyError as error:

        print(
            str(error)
        )

        return

    time_coord = (
        "valid_time"
        if "valid_time"
        in dataset[variable_name].coords
        else "time"
    )

    time_values = (
        dataset[time_coord]
    )

    print(
        f"Time coordinate: {time_coord}"
    )

    print(
        f"Earliest available time: "
        f"{time_values.min().values}"
    )

    print(
        f"MOST RECENT available time: "
        f"{time_values.max().values}"
    )

    print()

    print(
        "^ Compare that most-recent "
        "timestamp against today's date. "
        "If it's weeks/months old rather "
        "than a few days old, this store "
        "likely does not carry ERA5T and "
        "\"automatic daily updates\" will "
        "lag much further behind real "
        "time than originally intended."
    )

    if "expver" in dataset[
        variable_name
    ].dims:

        print(
            "Note: 'expver' dimension "
            "present (ERA5/ERA5T split "
            "handled automatically)."
        )

    else:

        print(
            "Note: no 'expver' dimension "
            "-- this store appears to be "
            "a single continuous series."
        )


# ============================================================
# BUNDLE (COMBINED FRONTEND FILE)
# ============================================================

def rebuild_bundle() -> dict:
    """
    Combine every stored per-year series into a single file so the
    frontend can load the whole historical spaghetti plot in one
    request. This only reads already-stored per-year JSON from
    Cloud Storage -- it never re-downloads ERA5.
    """

    years = (
        list_available_years()
    )

    bundle_years = {}

    for year in years:

        payload = (
            load_year_series(
                year
            )
        )

        if payload:

            bundle_years[
                str(year)
            ] = payload.get(
                "daily",
                [],
            )

    bundle = {
        "product": PRODUCT_KEY,

        "level_hpa": ERA5_LEVEL_HPA,

        "latitude": ERA5_LATITUDE,

        "generated_utc": (
            utc_now_iso()
        ),

        "years": bundle_years,
    }

    upload_json(
        object_name_bundle(),
        bundle,
    )

    return bundle


# ============================================================
# STATS
# ============================================================

def compute_wind_state(
    value: float,
) -> str:

    return (
        "westerly"
        if value >= 0
        else "easterly"
    )


def compute_percentile(
    value: float,
    samples: list,
) -> float | None:

    if not samples:

        return None

    at_or_below = sum(
        1
        for sample in samples
        if sample <= value
    )

    return round(
        100.0
        * at_or_below
        / len(samples),
        1,
    )


def _reference_day(
    month: int,
    day: int,
) -> date:

    # A fixed leap year lets Feb 29 map onto a real calendar date
    # for distance comparisons; non-leap-year callers passing Feb 29
    # are simply mapped onto Feb 28.
    if month == 2 and day == 29:

        day = 28

    return date(
        2000,
        month,
        day,
    )


def _day_distance(
    month_a: int,
    day_a: int,
    month_b: int,
    day_b: int,
) -> int:

    reference_a = (
        _reference_day(
            month_a,
            day_a,
        )
    )

    reference_b = (
        _reference_day(
            month_b,
            day_b,
        )
    )

    diff = abs(
        (
            reference_a
            - reference_b
        ).days
    )

    return min(
        diff,
        366 - diff,
    )


def gather_day_of_year_samples(
    bundle_years: dict,
    target_month: int,
    target_day: int,
    window_days: int = (
        PERCENTILE_WINDOW_DAYS
    ),
) -> list:
    """
    Collect historical values from all years within `window_days` of
    the given calendar date (ignoring year), for percentile ranking.
    """

    samples = []

    for daily in bundle_years.values():

        for entry in daily:

            try:

                date_str, value = entry

                year_part, month_part, day_part = (
                    int(part)
                    for part in str(date_str).split("-")
                )

            except (
                ValueError,
                TypeError,
            ):

                continue

            if (
                _day_distance(
                    target_month,
                    target_day,
                    month_part,
                    day_part,
                )
                <= window_days
            ):

                samples.append(
                    float(value)
                )

    return samples


def recompute_and_publish_latest(
    bundle: dict | None = None,
) -> dict:
    """
    Determine the latest processed date/value from the bundle and
    publish latest.json with current stats: value, date, easterly/
    westerly state, and historical percentile.
    """

    if bundle is None:

        bundle = (
            rebuild_bundle()
        )

    bundle_years = bundle[
        "years"
    ]

    years_available = sorted(
        int(year)
        for year in bundle_years.keys()
    )

    if not years_available:

        raise RuntimeError(
            "ERA5 PV: no data available "
            "to publish."
        )

    latest_year = (
        years_available[-1]
    )

    latest_daily = bundle_years[
        str(latest_year)
    ]

    if not latest_daily:

        raise RuntimeError(
            f"ERA5 PV: no daily records "
            f"for {latest_year}."
        )

    latest_date_str, latest_value = (
        latest_daily[-1]
    )

    _, month_part, day_part = (
        int(part)
        for part in str(latest_date_str).split("-")
    )

    samples = (
        gather_day_of_year_samples(
            bundle_years,
            month_part,
            day_part,
        )
    )

    payload = {
        "product": PRODUCT_KEY,

        "level_hpa": ERA5_LEVEL_HPA,

        "latitude": ERA5_LATITUDE,

        "updated_utc": (
            utc_now_iso()
        ),

        "latest_date": (
            latest_date_str
        ),

        "latest_value_ms": round(
            float(latest_value),
            2,
        ),

        "state": (
            compute_wind_state(
                float(latest_value)
            )
        ),

        "percentile": (
            compute_percentile(
                float(latest_value),
                samples,
            )
        ),

        "percentile_sample_size": len(
            samples
        ),

        "percentile_window_days": (
            PERCENTILE_WINDOW_DAYS
        ),

        "years_available": (
            years_available
        ),

        "record_start": (
            ERA5_START_DATE.isoformat()
        ),
    }

    upload_json(
        object_name_latest(),
        payload,
    )

    return payload


# ============================================================
# BACKFILL (ONE-TIME HISTORICAL PROCESSING)
# ============================================================

def run_backfill(
    start_year: int = (
        ERA5_START_DATE.year
    ),
    end_year: int | None = None,
    overwrite: bool = False,
):
    """
    Process the full ERA5 historical record once, year by year, and
    store the compact result. Already-processed prior years are
    skipped unless overwrite=True. The current (in-progress) year is
    always re-fetched, since it is incomplete by definition.
    """

    if end_year is None:

        end_year = (
            datetime.now(
                timezone.utc
            ).year
        )

    if not acquire_lock(
        STATE_KEY
    ):

        raise RuntimeError(
            "ERA5 PV: backfill already "
            "running (lock held)."
        )

    try:

        mark_run_started(
            STATE_KEY
        )

        for year in range(
            start_year,
            end_year + 1,
        ):

            existing = (
                load_year_series(
                    year
                )
            )

            already_has_data = bool(
                existing
                and existing.get(
                    "daily"
                )
            )

            if (
                already_has_data
                and not overwrite
                and year < end_year
            ):

                print(
                    f"ERA5 PV: {year} already "
                    f"processed, skipping."
                )

                continue

            print(
                f"ERA5 PV: fetching {year}..."
            )

            new_points = (
                fetch_year_zonal_mean(
                    year
                )
            )

            merge_year(
                year,
                new_points,
            )

            print(
                f"ERA5 PV: {year} -> "
                f"{len(new_points)} days"
            )

        bundle = (
            rebuild_bundle()
        )

        recompute_and_publish_latest(
            bundle
        )

        update_state(
            STATE_KEY,
            last_backfill_year=end_year,
        )

        mark_run_success(
            STATE_KEY
        )

    except Exception as error:

        mark_run_failure(
            STATE_KEY,
            error,
        )

        raise

    finally:

        release_lock(
            STATE_KEY
        )


# ============================================================
# DAILY UPDATE (INCREMENTAL)
# ============================================================

def run_daily_update(
    lag_days: int = (
        ERA5T_LAG_DAYS
    ),
):
    """
    Fetch any newly available ERA5/ERA5T days and append them.

    Re-fetches a short trailing window (lag_days) even for dates
    already stored, so that recently-appended ERA5T values get
    silently refreshed once CDS serves finalized ERA5 for them.
    """

    if not acquire_lock(
        STATE_KEY
    ):

        raise RuntimeError(
            "ERA5 PV: update already "
            "running (lock held)."
        )

    try:

        mark_run_started(
            STATE_KEY
        )

        state = load_state(
            STATE_KEY
        )

        last_date_str = (
            state.get(
                "last_processed_date"
            )
        )

        today = (
            datetime.now(
                timezone.utc
            ).date()
        )

        target_end = (
            today
            - timedelta(
                days=lag_days
            )
        )

        if last_date_str:

            last_date = (
                date.fromisoformat(
                    last_date_str
                )
            )

        else:

            # No local state (fresh environment): re-derive the
            # last processed date from what's actually stored.
            years = (
                list_available_years()
            )

            last_date = (
                ERA5_START_DATE
                - timedelta(days=1)
            )

            if years:

                latest_payload = (
                    load_year_series(
                        years[-1]
                    )
                )

                daily = (
                    latest_payload.get(
                        "daily",
                        [],
                    )
                    if latest_payload
                    else []
                )

                if daily:

                    last_date = (
                        date.fromisoformat(
                            daily[-1][0]
                        )
                    )

        refresh_start = (
            last_date
            - timedelta(
                days=lag_days
            )
        )

        refresh_start = max(
            refresh_start,
            ERA5_START_DATE,
        )

        if refresh_start > target_end:

            print(
                "ERA5 PV: nothing new "
                "to fetch."
            )

            mark_run_success(
                STATE_KEY
            )

            return

        print(
            f"ERA5 PV: refreshing "
            f"{refresh_start} .. {target_end}..."
        )

        # ARCO can slice an arbitrary continuous date range directly
        # (unlike the old CDS Toolbox month/day cross-product), so
        # this is a single fetch even when the window crosses a
        # year boundary. Split the result by year afterward, since
        # storage is still one file per year.
        new_points = (
            fetch_zonal_mean_range(
                refresh_start,
                target_end,
            )
        )

        points_by_year = {}

        for date_str, value in (
            new_points.items()
        ):

            year = int(
                date_str[:4]
            )

            points_by_year.setdefault(
                year, {}
            )[date_str] = value

        for year, year_points in (
            points_by_year.items()
        ):

            merge_year(
                year,
                year_points,
            )

        bundle = (
            rebuild_bundle()
        )

        recompute_and_publish_latest(
            bundle
        )

        update_state(
            STATE_KEY,
            last_processed_date=(
                target_end.isoformat()
            ),
        )

        mark_run_success(
            STATE_KEY
        )

    except Exception as error:

        mark_run_failure(
            STATE_KEY,
            error,
        )

        raise

    finally:

        release_lock(
            STATE_KEY
        )
