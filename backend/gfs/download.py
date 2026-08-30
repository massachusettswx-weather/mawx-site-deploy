from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import urllib.request
import time

from shared.download import (
    gfs_idx_matchers,
)

from shared.products import (
    OPERATIONAL_PRODUCTS,
)

from shared.storage import (
    build_local_forecast_path,
)


# ============================================================
# SETTINGS
# ============================================================

BASE_URL = (
    "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
)

FORECAST_HOURS = list(
    range(
        0,
        121,
        6,
    )
)


# ============================================================
# GFS URLS
# ============================================================

def build_urls(
    date,
    cycle,
    forecast_hour,
):

    ymd = (
        date.strftime(
            "%Y%m%d"
        )
    )

    cycle_string = (
        f"{int(cycle):02d}"
    )

    fhour = (
        f"{int(forecast_hour):03d}"
    )

    filename = (
        f"gfs.t"
        f"{cycle_string}z."
        f"pgrb2.0p25."
        f"f{fhour}"
    )

    base_url = (
        f"{BASE_URL}/"
        f"gfs.{ymd}/"
        f"{cycle_string}/"
        f"atmos/"
        f"{filename}"
    )

    return (
        base_url,
        base_url + ".idx",
        filename,
    )


# ============================================================
# HTTP CHECK
# ============================================================

def url_exists(
    url,
):
    """
    Check whether an upstream GFS object is actually readable.

    Do not rely exclusively on HTTP HEAD. Some upstream/CDN
    paths can intermittently fail or mishandle HEAD even though
    the object itself is already available.

    Strategy:
      1. Try HEAD as the inexpensive fast path.
      2. If HEAD does not prove availability, try a tiny GET.
      3. Retry transient failures briefly.
      4. Only return False for a genuine unavailable response.
    """

    import time
    import urllib.error
    import urllib.request

    attempts = 3

    for attempt in range(
        1,
        attempts + 1,
    ):

        # ----------------------------------------------------
        # FAST PATH: HEAD
        # ----------------------------------------------------

        try:

            request = (
                urllib.request.Request(
                    url,
                    method="HEAD",
                    headers={
                        "User-Agent": (
                            "MassachusettsWx-GFS/1.0"
                        ),
                        "Cache-Control": (
                            "no-cache"
                        ),
                    },
                )
            )

            with urllib.request.urlopen(
                request,
                timeout=10,
            ) as response:

                if (
                    200
                    <= response.status
                    <
                    400
                ):
                    return True

        except urllib.error.HTTPError as exc:

            if exc.code == 404:
                return False

        except Exception:
            pass


        # ----------------------------------------------------
        # FALLBACK: SMALL GET
        # ----------------------------------------------------

        try:

            request = (
                urllib.request.Request(
                    url,
                    method="GET",
                    headers={
                        "User-Agent": (
                            "MassachusettsWx-GFS/1.0"
                        ),
                        "Cache-Control": (
                            "no-cache"
                        ),
                        "Range": (
                            "bytes=0-255"
                        ),
                    },
                )
            )

            with urllib.request.urlopen(
                request,
                timeout=15,
            ) as response:

                if response.status in (
                    200,
                    206,
                ):

                    response.read(
                        256
                    )

                    return True

        except urllib.error.HTTPError as exc:

            if exc.code == 404:
                return False

        except Exception:
            pass


        if attempt < attempts:

            time.sleep(
                1.0
            )


    return False


# ============================================================
# CYCLE NORMALIZATION
# ============================================================

def normalize_cycle_time(
    cycle_time,
):

    if cycle_time is None:

        return None

    if isinstance(
        cycle_time,
        str,
    ):

        cycle_time = (
            datetime.fromisoformat(
                cycle_time
            )
        )

    if cycle_time.tzinfo is None:

        cycle_time = (
            cycle_time.replace(
                tzinfo=timezone.utc
            )
        )

    return (
        cycle_time.astimezone(
            timezone.utc
        )
    )


# ============================================================
# FIND / RESOLVE CYCLE
# ============================================================

def find_latest_cycle():

    now = (
        datetime.now(
            timezone.utc
        )
    )

    cycle_hour = (
        now.hour
        //
        6
    ) * 6

    candidate = (
        now.replace(
            hour=cycle_hour,
            minute=0,
            second=0,
            microsecond=0,
        )
    )

    print()
    print(
        "Searching for latest "
        "available GFS cycle..."
    )

    for _ in range(
        8
    ):

        date = candidate
        cycle = candidate.hour

        _, idx_url, _ = (
            build_urls(
                date,
                cycle,
                0,
            )
        )

        print(
            f"Checking "
            f"{date:%Y-%m-%d} "
            f"{cycle:02d}z..."
        )

        if url_exists(
            idx_url
        ):

            print()
            print(
                f"Latest GFS cycle: "
                f"{date:%Y-%m-%d} "
                f"{cycle:02d}z"
            )

            return (
                date,
                cycle,
            )

        candidate -= timedelta(
            hours=6
        )

    raise RuntimeError(
        "Could not locate a "
        "recent GFS cycle."
    )


def resolve_gfs_cycle(
    cycle_time=None,
):
    """
    Resolve either the exact backend-selected GFS cycle or latest.
    """

    cycle_time = (
        normalize_cycle_time(
            cycle_time
        )
    )

    if cycle_time is None:

        return (
            find_latest_cycle()
        )

    return (
        cycle_time,
        int(
            cycle_time.hour
        ),
    )


# ============================================================
# READ .IDX
# ============================================================

def read_idx(
    idx_url,
):

    with urllib.request.urlopen(
        idx_url,
        timeout=30,
    ) as response:

        text = (
            response
            .read()
            .decode(
                "utf-8"
            )
        )

    records = []

    for line in (
        text.splitlines()
    ):

        parts = (
            line.split(
                ":"
            )
        )

        if len(
            parts
        ) < 5:

            continue

        try:

            offset = int(
                parts[
                    1
                ]
            )

        except ValueError:

            continue

        records.append(
            {
                "offset": offset,
                "line": line,
            }
        )

    return records


# ============================================================
# MATCH PRODUCT FIELDS
# ============================================================

def find_required_records(
    records,
    products=None,
):
    """
    Match all GFS GRIB records required by the enabled products.
    """

    if products is None:

        products = (
            OPERATIONAL_PRODUCTS
        )

    matchers = (
        gfs_idx_matchers(
            products
        )
    )

    selected = []
    selected_offsets = set()

    print()
    print(
        "Required GFS fields:"
    )

    for matcher in (
        matchers
    ):

        idx_name = (
            matcher[
                "idx_name"
            ]
        )

        level_text = (
            matcher[
                "level_text"
            ]
        )

        matches = []

        for (
            index,
            record,
        ) in enumerate(
            records
        ):

            line = (
                record[
                    "line"
                ]
            )

            if (
                f":{idx_name}:"
                not in line
            ):

                continue

            if (
                level_text
                is not None
                and
                level_text
                not in line
            ):

                continue

            start = (
                record[
                    "offset"
                ]
            )

            if (
                start
                in selected_offsets
            ):

                continue

            if (
                index
                +
                1
                <
                len(
                    records
                )
            ):

                end = (
                    records[
                        index
                        +
                        1
                    ][
                        "offset"
                    ]
                    -
                    1
                )

            else:

                end = None

            matches.append(
                {
                    "start": start,
                    "end": end,
                    "description": line,
                }
            )

        if not matches:

            print(
                f"  MISSING: "
                f"{idx_name} "
                f"{level_text or ''}"
            )

            continue

        match = (
            matches[
                0
            ]
        )

        selected.append(
            match
        )

        selected_offsets.add(
            match[
                "start"
            ]
        )

        print(
            f"  FOUND: "
            f"{match['description']}"
        )

    if not selected:

        raise RuntimeError(
            "No required GFS fields "
            "were found in the inventory."
        )

    selected.sort(
        key=lambda item: (
            item[
                "start"
            ]
        )
    )

    return selected


# ============================================================
# HTTP BYTE RANGE
# ============================================================

def download_range(
    url,
    start,
    end,
    *,
    attempts=4,
):
    """
    Download one exact NOAA GRIB byte range.

    NOAA/NOMADS range responses are operational network traffic, so a
    short/truncated response must never be silently appended to the
    local GRIB. cfgrib/eccodes may otherwise fail later with misleading
    messages such as:

        unpack requires a buffer of N bytes

    Fixed-length ranges are validated against their exact expected
    byte count. Open-ended ranges are validated against Content-Range
    when available.

    Transient failures are retried with short exponential backoff.
    """

    start = int(
        start
    )

    if end is not None:
        end = int(
            end
        )

    if end is None:

        range_header = (
            f"bytes="
            f"{start}-"
        )

        expected_size = None

    else:

        if end < start:
            raise ValueError(
                f"Invalid byte range: "
                f"{start}-{end}"
            )

        range_header = (
            f"bytes="
            f"{start}-"
            f"{end}"
        )

        expected_size = (
            end
            -
            start
            +
            1
        )

    last_error = None

    for attempt in range(
        1,
        int(attempts) + 1,
    ):

        try:

            request = (
                urllib.request.Request(
                    url,
                    headers={
                        "Range": (
                            range_header
                        ),
                        "Accept-Encoding": (
                            "identity"
                        ),
                        "User-Agent": (
                            "MassachusettsWx-GFS/1.0"
                        ),
                    },
                )
            )

            with urllib.request.urlopen(
                request,
                timeout=90,
            ) as response:

                status = getattr(
                    response,
                    "status",
                    None,
                )

                content_range = (
                    response.headers.get(
                        "Content-Range"
                    )
                )

                data = (
                    response.read()
                )

            # ----------------------------------------------------
            # NOAA should honor byte-range requests with HTTP 206.
            #
            # A 200 response may mean the server ignored Range and
            # returned the entire GRIB, which must not be appended as
            # though it were one selected record.
            # ----------------------------------------------------

            if status != 206:

                raise RuntimeError(
                    f"NOAA range request "
                    f"{range_header} returned "
                    f"HTTP {status}, expected 206"
                )

            if not data:

                raise RuntimeError(
                    f"NOAA range request "
                    f"{range_header} returned "
                    f"zero bytes"
                )

            # ----------------------------------------------------
            # FIXED RANGE: exact byte count is mandatory.
            # ----------------------------------------------------

            if (
                expected_size
                is not None
                and
                len(data)
                !=
                expected_size
            ):

                raise RuntimeError(
                    f"NOAA range request "
                    f"{range_header} returned "
                    f"{len(data)} bytes; "
                    f"expected "
                    f"{expected_size}"
                )

            # ----------------------------------------------------
            # CONTENT-RANGE VALIDATION
            # ----------------------------------------------------

            if content_range:

                # Expected form:
                #
                #     bytes START-END/TOTAL
                #
                # Open-ended client requests are converted by the
                # server into an explicit returned END.
                try:

                    units, values = (
                        content_range
                        .split(
                            " ",
                            1,
                        )
                    )

                    returned_range, _ = (
                        values.split(
                            "/",
                            1,
                        )
                    )

                    returned_start, returned_end = (
                        returned_range.split(
                            "-",
                            1,
                        )
                    )

                    returned_start = int(
                        returned_start
                    )

                    returned_end = int(
                        returned_end
                    )

                except Exception as error:

                    raise RuntimeError(
                        f"Malformed NOAA "
                        f"Content-Range: "
                        f"{content_range!r}"
                    ) from error

                if (
                    units.lower()
                    !=
                    "bytes"
                ):

                    raise RuntimeError(
                        f"Unexpected NOAA "
                        f"Content-Range units: "
                        f"{content_range!r}"
                    )

                if (
                    returned_start
                    !=
                    start
                ):

                    raise RuntimeError(
                        f"NOAA Content-Range "
                        f"started at "
                        f"{returned_start}; "
                        f"expected {start}"
                    )

                if (
                    end is not None
                    and
                    returned_end
                    !=
                    end
                ):

                    raise RuntimeError(
                        f"NOAA Content-Range "
                        f"ended at "
                        f"{returned_end}; "
                        f"expected {end}"
                    )

                returned_size = (
                    returned_end
                    -
                    returned_start
                    +
                    1
                )

                if (
                    len(data)
                    !=
                    returned_size
                ):

                    raise RuntimeError(
                        f"NOAA Content-Range "
                        f"declares "
                        f"{returned_size} bytes "
                        f"but response contained "
                        f"{len(data)}"
                    )

            return data

        except Exception as error:

            last_error = error

            if (
                attempt
                >=
                int(attempts)
            ):

                break

            delay = min(
                8,
                2 ** (
                    attempt - 1
                ),
            )

            print(
                f"NOAA byte-range retry "
                f"{attempt}/"
                f"{attempts} "
                f"for {range_header}: "
                f"{type(error).__name__}: "
                f"{error}; "
                f"retrying in {delay}s"
            )

            time.sleep(
                delay
            )

    raise RuntimeError(
        f"NOAA byte-range download "
        f"failed after "
        f"{attempts} attempts "
        f"for {range_header}: "
        f"{last_error}"
    )


# ============================================================
# LOCAL CYCLE DIRECTORY
# ============================================================

def get_cycle_directory(
    date,
    cycle,
):

    ymd = (
        date.strftime(
            "%Y%m%d"
        )
    )

    sample_path = (
        build_local_forecast_path(
            model="gfs",
            cycle_date=ymd,
            cycle_hour=(
                cycle
            ),
            forecast_hour=0,
            extension="grib2",
        )
    )

    directory = (
        sample_path.parent
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


# ============================================================
# DOWNLOAD ONE FORECAST HOUR
# ============================================================

def download_gfs_hour(
    date,
    cycle,
    forecast_hour,
    products=None,
):

    forecast_hour = int(
        forecast_hour
    )

    cycle = int(
        cycle
    )

    if products is None:

        products = (
            OPERATIONAL_PRODUCTS
        )

    grib_url, idx_url, _ = (
        build_urls(
            date,
            cycle,
            forecast_hour,
        )
    )

    ymd = (
        date.strftime(
            "%Y%m%d"
        )
    )

    output_file = (
        build_local_forecast_path(
            model="gfs",
            cycle_date=ymd,
            cycle_hour=cycle,
            forecast_hour=(
                forecast_hour
            ),
            extension="grib2",
        )
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    partial_file = (
        output_file.with_suffix(
            output_file.suffix
            +
            ".part"
        )
    )

    # --------------------------------------------------------
    # REUSE COMPLETE TEMP FILE
    # --------------------------------------------------------

    if (
        output_file.exists()
        and
        output_file.stat().st_size
        > 0
    ):

        size_mb = (
            output_file
            .stat()
            .st_size
            /
            1024
            /
            1024
        )

        print(
            f"f{forecast_hour:03d}: "
            f"already downloaded "
            f"({size_mb:.2f} MB)"
        )

        return output_file

    # --------------------------------------------------------
    # AVAILABILITY
    # --------------------------------------------------------

    if not url_exists(
        idx_url
    ):

        print(
            f"f{forecast_hour:03d}: "
            f"not available yet"
        )

        return None

    print(
        f"f{forecast_hour:03d}: "
        f"reading GFS inventory..."
    )

    records = (
        read_idx(
            idx_url
        )
    )

    required_records = (
        find_required_records(
            records,
            products,
        )
    )

    print()
    print(
        f"f{forecast_hour:03d}: "
        f"downloading "
        f"{len(required_records)} "
        f"GRIB records..."
    )

    partial_file.unlink(
        missing_ok=True
    )

    try:

        with partial_file.open(
            "wb"
        ) as destination:

            for (
                number,
                record,
            ) in enumerate(
                required_records,
                start=1,
            ):

                print(
                    f"  [{number}/"
                    f"{len(required_records)}] "
                    f"{record['description']}"
                )

                data = (
                    download_range(
                        grib_url,
                        record[
                            "start"
                        ],
                        record[
                            "end"
                        ],
                    )
                )

                destination.write(
                    data
                )

        if (
            not partial_file.exists()
            or
            partial_file.stat().st_size
            <= 0
        ):

            raise RuntimeError(
                f"GFS "
                f"f{forecast_hour:03d}: "
                f"download produced "
                f"an empty file"
            )

        partial_file.replace(
            output_file
        )

    except Exception:

        partial_file.unlink(
            missing_ok=True
        )

        output_file.unlink(
            missing_ok=True
        )

        raise

    size_mb = (
        output_file
        .stat()
        .st_size
        /
        1024
        /
        1024
    )

    print()
    print(
        f"f{forecast_hour:03d}: "
        f"complete "
        f"({size_mb:.2f} MB)"
    )

    return output_file


# ============================================================
# DOWNLOAD COMPLETE CYCLE
# ============================================================

def download_gfs_cycle(
    forecast_hours=None,
    products=None,
    cycle_time=None,
):
    """
    Backward-compatible cycle downloader.

    Operational GFS now streams forecast hours one by one.
    """

    if forecast_hours is None:

        forecast_hours = (
            FORECAST_HOURS
        )

    if products is None:

        products = (
            OPERATIONAL_PRODUCTS
        )

    date, cycle = (
        resolve_gfs_cycle(
            cycle_time
        )
    )

    print()
    print("=" * 70)
    print(
        "GFS MULTI-PRODUCT DOWNLOAD"
    )
    print("=" * 70)

    print(
        f"Cycle: "
        f"{date:%Y-%m-%d} "
        f"{cycle:02d}z"
    )

    print(
        f"Forecast hours: "
        f"{len(forecast_hours)}"
    )

    print(
        f"Products: "
        f"{len(products)}"
    )

    print("=" * 70)

    downloaded = []
    failed = []

    for (
        index,
        forecast_hour,
    ) in enumerate(
        forecast_hours,
        start=1,
    ):

        print()
        print(
            f"[{index}/"
            f"{len(forecast_hours)}] "
            f"f{int(forecast_hour):03d}"
        )

        try:

            path = (
                download_gfs_hour(
                    date,
                    cycle,
                    forecast_hour,
                    products,
                )
            )

            if path is not None:

                downloaded.append(
                    (
                        int(
                            forecast_hour
                        ),
                        path,
                    )
                )

        except Exception as error:

            failed.append(
                (
                    int(
                        forecast_hour
                    ),
                    str(
                        error
                    ),
                )
            )

            print(
                f"FAILED "
                f"f{int(forecast_hour):03d}: "
                f"{error}"
            )

    print()
    print("=" * 70)
    print(
        "GFS DOWNLOAD COMPLETE"
    )
    print("=" * 70)

    print(
        f"Downloaded/reused: "
        f"{len(downloaded)}"
    )

    print(
        f"Failed: "
        f"{len(failed)}"
    )

    return (
        date,
        cycle,
        downloaded,
    )


# ============================================================
# BACKWARD-COMPATIBLE NAME
# ============================================================

def download_cycle(
    forecast_hours=None,
    products=None,
    cycle_time=None,
):

    return (
        download_gfs_cycle(
            forecast_hours=(
                forecast_hours
            ),
            products=(
                products
            ),
            cycle_time=(
                cycle_time
            ),
        )
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    download_gfs_cycle()
