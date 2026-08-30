from datetime import (
    datetime,
    timedelta,
    timezone,
)

import urllib.request


from shared.models import (
    get_model,
    model_exists,
    get_readiness_config,
    get_required_ready_step,
)


# ============================================================
# SETTINGS
# ============================================================

HTTP_TIMEOUT = 12

SEARCH_BACK_HOURS = 48


# ============================================================
# BASIC HTTP CHECK
# ============================================================

def url_exists(
    url,
    *,
    timeout=HTTP_TIMEOUT,
):
    # --------------------------------------------------------
    # HEAD
    # --------------------------------------------------------

    try:

        request = (
            urllib.request.Request(
                url,
                method="HEAD",
            )
        )

        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            if (
                200
                <= response.status
                < 400
            ):

                return True

    except Exception:

        pass

    # --------------------------------------------------------
    # RANGE GET FALLBACK
    # --------------------------------------------------------

    try:

        request = (
            urllib.request.Request(
                url,

                headers={
                    "Range": (
                        "bytes=0-0"
                    ),
                },
            )
        )

        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            return (
                200
                <= response.status
                < 400
            )

    except Exception:

        return False


# ============================================================
# STANDARD CYCLE OBJECT
# ============================================================

def make_cycle(
    model,
    cycle_time,
):
    cycle_time = (
        cycle_time.astimezone(
            timezone.utc
        )
    )

    return {
        "model": model,

        "date": (
            cycle_time.strftime(
                "%Y%m%d"
            )
        ),

        "hour": (
            cycle_time.hour
        ),

        "id": (
            cycle_time.strftime(
                "%Y%m%d_%Hz"
            )
        ),

        "datetime": (
            cycle_time
            .replace(
                microsecond=0
            )
            .isoformat()
        ),
    }


# ============================================================
# NORMALIZE ECMWF DATETIME
# ============================================================

def normalize_ecmwf_datetime(
    value,
):
    if value is None:

        return None

    if isinstance(
        value,
        datetime,
    ):

        output = value

    elif hasattr(
        value,
        "datetime",
    ):

        output = (
            value.datetime
        )

    else:

        text = str(
            value
        )

        if text.endswith(
            "Z"
        ):

            text = (
                text[:-1]
                +
                "+00:00"
            )

        try:

            output = (
                datetime.fromisoformat(
                    text
                )
            )

        except Exception as error:

            raise RuntimeError(
                f"Could not interpret "
                f"ECMWF latest() "
                f"result: "
                f"{value!r}"
            ) from error

    if output.tzinfo is None:

        output = (
            output.replace(
                tzinfo=timezone.utc
            )
        )

    return (
        output.astimezone(
            timezone.utc
        )
    )


# ============================================================
# SAME CYCLE
# ============================================================

def same_cycle_time(
    first,
    second,
):
    if (
        first is None
        or second is None
    ):

        return False

    first = first.astimezone(
        timezone.utc
    )

    second = second.astimezone(
        timezone.utc
    )

    return (
        first.year
        == second.year

        and first.month
        == second.month

        and first.day
        == second.day

        and first.hour
        == second.hour
    )


# ============================================================
# CANDIDATE CYCLES
# ============================================================

def candidate_cycle_times(
    model,
    *,
    now=None,
    search_back_hours=(
        SEARCH_BACK_HOURS
    ),
):
    config = get_model(
        model
    )

    cycle_hours = sorted(
        config.get(
            "cycles",
            [
                0,
                6,
                12,
                18,
            ],
        )
    )

    if now is None:

        now = datetime.now(
            timezone.utc
        )

    else:

        now = (
            now.astimezone(
                timezone.utc
            )
        )

    start_day = (
        now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    )

    candidates = []

    days_back = (
        search_back_hours
        // 24
        + 2
    )

    for day_offset in range(
        days_back
    ):

        day = (
            start_day
            -
            timedelta(
                days=day_offset
            )
        )

        for hour in cycle_hours:

            candidate = (
                day.replace(
                    hour=hour
                )
            )

            if candidate > now:

                continue

            age = (
                now
                -
                candidate
            )

            if (
                age.total_seconds()
                >
                search_back_hours
                * 3600
            ):

                continue

            candidates.append(
                candidate
            )

    candidates.sort(
        reverse=True
    )

    return candidates


# ============================================================
# GFS URL
# ============================================================

def build_gfs_probe_url(
    cycle_time,
    forecast_hour,
):
    date_string = (
        cycle_time.strftime(
            "%Y%m%d"
        )
    )

    cycle_string = (
        cycle_time.strftime(
            "%H"
        )
    )

    return (
        "https://"
        "noaa-gfs-bdp-pds."
        "s3.amazonaws.com/"
        f"gfs.{date_string}/"
        f"{cycle_string}/"
        "atmos/"
        f"gfs.t{cycle_string}z."
        f"pgrb2.0p25."
        f"f{forecast_hour:03d}.idx"
    )


# ============================================================
# GFS CYCLE EXISTS
# ============================================================

def gfs_cycle_available(
    cycle_time,
):
    return url_exists(
        build_gfs_probe_url(
            cycle_time,
            0,
        )
    )


# ============================================================
# GFS READY
# ============================================================

def gfs_cycle_ready(
    cycle,
    required_step,
):
    cycle_time = (
        datetime.fromisoformat(
            cycle[
                "datetime"
            ]
        )
        .astimezone(
            timezone.utc
        )
    )

    url = (
        build_gfs_probe_url(
            cycle_time,
            required_step,
        )
    )

    print(
        f"  readiness probe: "
        f"GFS "
        f"f{required_step:03d}"
    )

    ready = (
        url_exists(
            url
        )
    )

    if ready:

        print(
            f"    GFS "
            f"f{required_step:03d} "
            f"is available."
        )

    else:

        print(
            f"    GFS "
            f"f{required_step:03d} "
            f"is not available yet."
        )

    return ready


# ============================================================
# ECMWF CLIENT
# ============================================================

def create_ecmwf_probe_client(
    model,
):
    try:

        from ecmwf.opendata import (
            Client,
        )

    except ImportError as error:

        raise RuntimeError(
            "ecmwf-opendata is not "
            "installed in this "
            "Python environment."
        ) from error

    config = get_model(
        model
    )

    ecmwf_model = (
        config.get(
            "ecmwf_model",
            "ifs",
        )
    )

    if model == "ifs":

        return Client(
            source="ecmwf",
            model=ecmwf_model,
            resol="0p25",
            infer_stream_keyword=True,
            preserve_request_order=False,
        )

    return Client(
        source="ecmwf",
        model=ecmwf_model,
        resol="0p25",
        preserve_request_order=False,
    )


# ============================================================
# IFS STREAM
#
# Cycle 50r1:
# SCDA is deprecated.
#
# 00/06/12/18 atmospheric deterministic data use OPER.
# ============================================================

def get_ifs_stream(
    hour,
):
    hour = int(
        hour
    )

    if hour in {
        0,
        6,
        12,
        18,
    }:

        return "oper"

    raise ValueError(
        f"Unsupported IFS "
        f"cycle hour: "
        f"{hour}"
    )


# ============================================================
# LATEST ECMWF CYCLE AT HOUR
# ============================================================

def get_latest_ecmwf_cycle_at_hour(
    model,
    cycle_hour,
    *,
    step=0,
    param="msl",
):
    client = (
        create_ecmwf_probe_client(
            model
        )
    )

    request = {
        "time": int(
            cycle_hour
        ),

        "type": "fc",

        "step": int(
            step
        ),

        "param": (
            param
        ),
    }

    if model == "ifs":

        request[
            "stream"
        ] = get_ifs_stream(
            cycle_hour
        )

    print(
        f"    ECMWF query: "
        f"{model.upper()} "
        f"{int(cycle_hour):02d}Z "
        f"f{int(step):03d} "
        f"{param}"
    )

    try:

        result = (
            client.latest(
                **request
            )
        )

    except Exception as error:

        print(
            f"    ECMWF probe error: "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return None

    try:

        returned = (
            normalize_ecmwf_datetime(
                result
            )
        )

    except Exception as error:

        print(
            f"    ECMWF result error: "
            f"{error}"
        )

        return None

    if returned is None:

        print(
            "    ECMWF returned "
            "no matching forecast."
        )

        return None

    print(
        f"    ECMWF latest match: "
        f"{returned:%Y-%m-%d %HZ}"
    )

    return returned


# ============================================================
# ECMWF CYCLE EXISTS
# ============================================================

def ecmwf_cycle_available(
    model,
    cycle_time,
):
    returned = (
        get_latest_ecmwf_cycle_at_hour(
            model,
            cycle_time.hour,
            step=0,
            param="msl",
        )
    )

    if returned is None:

        return False

    candidate = (
        cycle_time.astimezone(
            timezone.utc
        )
    )

    available = (
        same_cycle_time(
            returned,
            candidate,
        )
    )

    if available:

        print(
            f"    matched candidate "
            f"{candidate:%Y-%m-%d %HZ}"
        )

    return available


# ============================================================
# ECMWF CYCLE READY
# ============================================================

def ecmwf_cycle_ready(
    model,
    cycle,
    required_step,
):
    config = (
        get_readiness_config(
            model
        )
    )

    probe_param = (
        config.get(
            "probe_param",
            "msl",
        )
    )

    cycle_hour = int(
        cycle[
            "hour"
        ]
    )

    expected = (
        datetime.strptime(
            (
                cycle[
                    "date"
                ]
                +
                f"{cycle_hour:02d}"
            ),
            "%Y%m%d%H",
        )
        .replace(
            tzinfo=timezone.utc
        )
    )

    print(
        f"  readiness probe: "
        f"{model.upper()} "
        f"f{required_step:03d}"
    )

    returned = (
        get_latest_ecmwf_cycle_at_hour(
            model,
            cycle_hour,
            step=required_step,
            param=probe_param,
        )
    )

    if returned is None:

        print(
            "    required step "
            "not available yet."
        )

        return False

    ready = (
        same_cycle_time(
            returned,
            expected,
        )
    )

    if ready:

        print(
            f"    {model.upper()} "
            f"{cycle['id']} "
            f"has "
            f"f{required_step:03d}."
        )

    else:

        print(
            f"    required step "
            f"belongs to "
            f"{returned:%Y-%m-%d %HZ}, "
            f"not "
            f"{cycle['id']}."
        )

    return ready


# ============================================================
# GENERIC CYCLE EXISTS
# ============================================================

def cycle_available(
    model,
    cycle_time,
):
    if not model_exists(
        model
    ):

        raise ValueError(
            f"Unknown model: "
            f"{model}"
        )

    config = get_model(
        model
    )

    family = config.get(
        "download_family"
    )

    if family == "gfs_idx":

        return (
            gfs_cycle_available(
                cycle_time
            )
        )

    if family == (
        "ecmwf_open_data"
    ):

        return (
            ecmwf_cycle_available(
                model,
                cycle_time,
            )
        )

    raise RuntimeError(
        f"No cycle availability "
        f"handler for family: "
        f"{family}"
    )


# ============================================================
# GENERIC READINESS
# ============================================================

def cycle_ready(
    model,
    cycle,
):
    if cycle is None:

        return False

    config = (
        get_readiness_config(
            model
        )
    )

    method = config.get(
        "method"
    )

    required_step = (
        get_required_ready_step(
            model,
            int(
                cycle[
                    "hour"
                ]
            ),
        )
    )

    if required_step is None:

        return True

    if method == "gfs_idx":

        return (
            gfs_cycle_ready(
                cycle,
                required_step,
            )
        )

    if method == (
        "ecmwf_latest"
    ):

        return (
            ecmwf_cycle_ready(
                model,
                cycle,
                required_step,
            )
        )

    raise RuntimeError(
        f"Unsupported readiness "
        f"method: "
        f"{method}"
    )


# ============================================================
# LATEST AVAILABLE CYCLE
# ============================================================

def latest_cycle(
    model,
    *,
    now=None,
):
    if not model_exists(
        model
    ):

        raise ValueError(
            f"Unknown model: "
            f"{model}"
        )

    print(
        f"Checking latest cycle "
        f"for "
        f"{model.upper()}..."
    )

    candidates = (
        candidate_cycle_times(
            model,
            now=now,
        )
    )

    ecmwf_cache = {}

    config = get_model(
        model
    )

    family = config.get(
        "download_family"
    )

    for candidate in candidates:

        print(
            f"  checking "
            f"{candidate:%Y-%m-%d %HZ}"
        )

        try:

            if (
                family
                ==
                "ecmwf_open_data"
            ):

                cycle_hour = (
                    candidate.hour
                )

                if (
                    cycle_hour
                    not in ecmwf_cache
                ):

                    ecmwf_cache[
                        cycle_hour
                    ] = (
                        get_latest_ecmwf_cycle_at_hour(
                            model,
                            cycle_hour,
                            step=0,
                            param="msl",
                        )
                    )

                returned = (
                    ecmwf_cache[
                        cycle_hour
                    ]
                )

                available = (
                    same_cycle_time(
                        returned,
                        candidate,
                    )
                )

            else:

                available = (
                    cycle_available(
                        model,
                        candidate,
                    )
                )

        except Exception as error:

            print(
                f"    probe error: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            continue

        if available:

            cycle = (
                make_cycle(
                    model,
                    candidate,
                )
            )

            print(
                f"  latest available: "
                f"{cycle['id']}"
            )

            return cycle

    print(
        f"No recent cycle found "
        f"for "
        f"{model.upper()}."
    )

    return None