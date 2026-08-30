from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from datetime import datetime, timezone

import google.auth
from google.auth.transport.requests import Request

from shared.inventory_seed import (
    build_work_plan,
    mark_complete,
)

from shared.operational_lifecycle import (
    FrontierSweep,
    OperationalCycleState,
    OperationalLifecycle,
)

from shared.cycles import latest_cycle
from shared.storage import get_bucket

# Google-model upstream cycle resolvers.
#
# These deliberately remain model-specific. shared.cycles currently
# handles the traditional NWP families, while these feeds have their
# own availability semantics.
from fnv3_cyclone.production import (
    resolve_cycle_id as resolve_fnv3_cycle_id,
)
from fnv3_large_cyclone.production import (
    resolve_cycle_id as resolve_fnv3_large_cycle_id,
)
from wn2.production import (
    resolve_wn2_cycle_id,
)


# ============================================================
# SETTINGS
# ============================================================

PROJECT_ID = os.environ.get(
    "GOOGLE_CLOUD_PROJECT",
    "project-166f07ba-7a61-4fa9-ae7",
)

REGION = os.environ.get(
    "WATCHER_REGION",
    "us-east1",
)

FAST_INTERVAL_SECONDS = int(
    os.environ.get(
        "WATCHER_FAST_INTERVAL_SECONDS",
        "10",
    )
)

FAST_RUNTIME_SECONDS = int(
    os.environ.get(
        "WATCHER_FAST_RUNTIME_SECONDS",
        "52",
    )
)

STATE_ROOT = "metadata/model-watcher"

# ============================================================
# GFS SAME-CYCLE RESUME
#
# GFS jobs intentionally stop cleanly when they reach the
# current NOAA dissemination frontier. The watcher may launch
# the SAME cycle again later so the job can resume from the
# first missing forecast hour.
#
# Avoid relaunching an idle same-cycle job every minute while
# NOAA has not advanced.
# ============================================================

MODEL_RESUME_COOLDOWN_SECONDS = int(
    os.environ.get(
        "MODEL_RESUME_COOLDOWN_SECONDS",
        os.environ.get(
            "GFS_RESUME_COOLDOWN_SECONDS",
            "180",
        ),
    )
)

# Backward-compatible name for the existing GFS helper.
GFS_RESUME_COOLDOWN_SECONDS = (
    MODEL_RESUME_COOLDOWN_SECONDS
)

MODELS = {
    "gfs": {
        # Fast CONUS dissemination lane.
        "job": "masswx-gfs",

        # Non-CONUS background rendering lane.
        "backfill_job": "masswx-gfs-backfill",

        # UTC windows around normal dissemination.
        # These are deliberately broad because dissemination varies.
        "fast_windows": [
            (2, 0, 4, 30),
            (8, 0, 10, 30),
            (14, 0, 16, 30),
            (20, 0, 22, 30),
        ],
    },

    "ifs": {
        "job": "masswx-ifs",
        "fast_windows": [
            (4, 30, 6, 45),
            (10, 30, 12, 45),
            (16, 30, 18, 45),
            (22, 30, 0, 45),
        ],
    },

    "aifs": {
        "job": "masswx-aifs",
        "fast_windows": [
            (4, 30, 6, 45),
            (10, 30, 12, 45),
            (16, 30, 18, 45),
            (22, 30, 0, 45),
        ],
    },

    "fnv3": {
        "job": "masswx-fnv3",
        "resolver": resolve_fnv3_cycle_id,
    },

    "fnv3_large": {
        "job": "masswx-fnv3-large",
        "resolver": resolve_fnv3_large_cycle_id,
    },

    "wn2": {
        "job": "weathernext-operational",
        "resolver": resolve_wn2_cycle_id,
    },
}


# ============================================================
# TIME HELPERS
# ============================================================

def utc_now():
    return datetime.now(
        timezone.utc
    )


def utc_timestamp():
    return int(
        utc_now().timestamp()
    )


def model_resume_key():
    return "last_dispatch_unix"


def model_resume_allowed(
    state,
    model,
):
    """
    Same-cycle continuation cooldown for single-lane models
    such as IFS and AIFS.
    """

    last_dispatch = state.get(
        model_resume_key()
    )

    if last_dispatch is None:
        return True

    try:
        last_dispatch = int(
            last_dispatch
        )

    except (
        TypeError,
        ValueError,
    ):
        return True

    elapsed = (
        utc_timestamp()
        -
        last_dispatch
    )

    if (
        elapsed
        >=
        MODEL_RESUME_COOLDOWN_SECONDS
    ):
        return True

    remaining = max(
        0,
        (
            MODEL_RESUME_COOLDOWN_SECONDS
            -
            elapsed
        ),
    )

    print(
        f"{str(model).upper()} "
        f"same-cycle resume cooldown: "
        f"{remaining}s remaining"
    )

    return False


def cycle_is_ready(
    model,
    cycle_id,
):
    """
    READY.json is the durable signal that a model cycle is
    complete. A completed cycle must never be relaunched merely
    because its Cloud Run job is idle.
    """

    object_name = (
        f"metadata/"
        f"{str(model).lower()}/"
        f"{cycle_id}/"
        f"READY.json"
    )

    try:

        return (
            get_bucket()
            .blob(
                object_name
            )
            .exists()
        )

    except Exception as error:

        print(
            f"{str(model).upper()} "
            f"{cycle_id}: "
            f"READY check failed: "
            f"{type(error).__name__}: "
            f"{error}"
        )

        # Fail safe: do not launch when completion state is
        # unknown. The next watcher pass can try again.
        return None


def gfs_lane_resume_key(
    lane_name,
):
    return (
        f"{lane_name}_last_dispatch_unix"
    )


def gfs_lane_resume_allowed(
    state,
    lane_name,
):
    """
    Return True when enough time has passed since the most
    recent dispatch of this GFS lane.

    New cycles do not depend on this function. It is only used
    for SAME-cycle continuation launches.
    """

    key = (
        gfs_lane_resume_key(
            lane_name
        )
    )

    last_dispatch = state.get(
        key
    )

    if last_dispatch is None:
        return True

    try:
        last_dispatch = int(
            last_dispatch
        )
    except (
        TypeError,
        ValueError,
    ):
        return True

    elapsed = (
        utc_timestamp()
        -
        last_dispatch
    )

    if (
        elapsed
        >=
        GFS_RESUME_COOLDOWN_SECONDS
    ):
        return True

    remaining = max(
        0,
        (
            GFS_RESUME_COOLDOWN_SECONDS
            -
            elapsed
        ),
    )

    print(
        f"GFS {lane_name} lane "
        f"same-cycle resume cooldown: "
        f"{remaining}s remaining"
    )

    return False


def minutes_since_midnight(dt):
    return (
        dt.hour * 60
        +
        dt.minute
    )


def in_window(
    now_minutes,
    start_minutes,
    end_minutes,
):
    if start_minutes <= end_minutes:
        return (
            start_minutes
            <= now_minutes
            <= end_minutes
        )

    # Window crosses 00 UTC.
    return (
        now_minutes >= start_minutes
        or
        now_minutes <= end_minutes
    )


def model_is_in_fast_window(
    model,
    now=None,
):
    if now is None:
        now = utc_now()

    current = (
        minutes_since_midnight(
            now
        )
    )

    for (
        start_hour,
        start_minute,
        end_hour,
        end_minute,
    ) in MODELS[
        model
    ][
        "fast_windows"
    ]:

        start = (
            start_hour * 60
            +
            start_minute
        )

        end = (
            end_hour * 60
            +
            end_minute
        )

        if in_window(
            current,
            start,
            end,
        ):
            return True

    return False


# ============================================================
# CYCLE NORMALIZATION
# ============================================================

def normalize_cycle(
    cycle,
):
    if cycle is None:
        return None

    if isinstance(
        cycle,
        datetime,
    ):
        return {
            "id": (
                f"{cycle:%Y%m%d}_"
                f"{cycle.hour:02d}z"
            ),
            "date": (
                f"{cycle:%Y%m%d}"
            ),
            "hour": int(
                cycle.hour
            ),
        }

    if isinstance(
        cycle,
        dict,
    ):
        date = str(
            cycle.get(
                "date",
                "",
            )
        )

        hour = int(
            cycle.get(
                "hour",
                0,
            )
        )

        cycle_id = cycle.get(
            "id"
        )

        if not cycle_id:
            cycle_id = (
                f"{date}_"
                f"{hour:02d}z"
            )

        return {
            "id": str(
                cycle_id
            ),
            "date": date,
            "hour": hour,
        }

    raise RuntimeError(
        f"Unsupported cycle value: "
        f"{cycle!r}"
    )


# ============================================================
# GCS STATE
# ============================================================

def state_object_name(
    model,
):
    return (
        f"{STATE_ROOT}/"
        f"{model}.json"
    )


def load_state(
    model,
):
    blob = (
        get_bucket()
        .blob(
            state_object_name(
                model
            )
        )
    )

    if not blob.exists():
        return {}

    try:
        payload = json.loads(
            blob.download_as_text()
        )

        if isinstance(
            payload,
            dict,
        ):
            return payload

    except Exception as error:
        print(
            f"{model.upper()} "
            f"watcher state read failed: "
            f"{error}"
        )

    return {}


def save_state(
    model,
    payload,
):
    payload = dict(
        payload
    )

    payload[
        "updated_at_utc"
    ] = (
        utc_now()
        .replace(
            microsecond=0
        )
        .isoformat()
    )

    (
        get_bucket()
        .blob(
            state_object_name(
                model
            )
        )
        .upload_from_string(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ),
            content_type=(
                "application/json"
            ),
        )
    )


# ============================================================
# GOOGLE AUTH
# ============================================================

def get_access_token():
    credentials, _ = (
        google.auth.default(
            scopes=[
                "https://www.googleapis.com/auth/cloud-platform"
            ]
        )
    )

    credentials.refresh(
        Request()
    )

    return credentials.token


def api_request(
    *,
    method,
    url,
    body=None,
):
    token = (
        get_access_token()
    )

    data = None

    if body is not None:
        data = json.dumps(
            body
        ).encode(
            "utf-8"
        )

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
            "Content-Type": (
                "application/json"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:

            text = (
                response.read()
                .decode(
                    "utf-8"
                )
            )

            if not text:
                return {}

            return json.loads(
                text
            )

    except urllib.error.HTTPError as error:
        body_text = (
            error.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        raise RuntimeError(
            f"Google API "
            f"{error.code}: "
            f"{body_text}"
        )


# ============================================================
# CLOUD RUN EXECUTION CHECK
# ============================================================

def execution_is_running(
    execution,
):
    """
    Return True unless Cloud Run gives us positive evidence that
    the execution has reached a terminal state.

    Cloud Run may expose a condition whose type is "Completed"
    while that condition is still pending. Therefore the mere
    presence of a Completed condition must NOT be interpreted as
    completion.
    """

    completion_time = (
        execution.get(
            "completionTime"
        )
    )

    # A populated completionTime is the strongest terminal signal.
    if completion_time:
        return False

    running_count = execution.get(
        "runningCount"
    )

    try:
        if (
            running_count is not None
            and
            int(running_count) > 0
        ):
            return True

    except (
        TypeError,
        ValueError,
    ):
        pass

    conditions = (
        execution.get(
            "conditions",
            []
        )
    )

    for condition in conditions:

        if (
            condition.get(
                "type"
            )
            !=
            "Completed"
        ):
            continue

        # Cloud Run v2 uses condition state values such as
        # CONDITION_PENDING / CONDITION_SUCCEEDED /
        # CONDITION_FAILED.
        state = str(
            condition.get(
                "state",
                ""
            )
        ).upper()

        if state in {
            "CONDITION_SUCCEEDED",
            "CONDITION_FAILED",
        }:
            return False

        # Some representations use a boolean/string status.
        status = str(
            condition.get(
                "status",
                ""
            )
        ).upper()

        if status in {
            "TRUE",
            "SUCCEEDED",
            "FAILED",
        }:
            return False

        # Completed exists but is still pending/unknown:
        # execution is still active.
        return True

    # No terminal signal was present. Be conservative and treat
    # provisioning/pending/ambiguous executions as active so the
    # watcher never creates a duplicate.
    return True


def job_has_active_execution(
    job_name,
):
    url = (
        f"https://run.googleapis.com/"
        f"v2/projects/{PROJECT_ID}/"
        f"locations/{REGION}/"
        f"jobs/{job_name}/executions"
        f"?pageSize=20"
    )

    payload = api_request(
        method="GET",
        url=url,
    )

    for execution in payload.get(
        "executions",
        [],
    ):

        if execution_is_running(
            execution
        ):
            return True

    return False


# ============================================================
# CLOUD RUN DISPATCH
# ============================================================

def launch_job(
    job_name,
):
    url = (
        f"https://run.googleapis.com/"
        f"v2/projects/{PROJECT_ID}/"
        f"locations/{REGION}/"
        f"jobs/{job_name}:run"
    )

    return api_request(
        method="POST",
        url=url,
        body={},
    )


# ============================================================
# ONE MODEL PROBE
# ============================================================

def probe_model(
    model,
):
    print()
    print(
        "=" * 60
    )
    print(
        f"WATCH {model.upper()}"
    )
    print(
        "=" * 60
    )

    try:
        resolver = MODELS.get(
            model,
            {},
        ).get(
            "resolver"
        )

        if resolver is not None:
            raw_cycle = resolver()
        else:
            raw_cycle = (
                latest_cycle(
                    model
                )
            )

        cycle = (
            normalize_cycle(
                raw_cycle
            )
        )

    except Exception as error:
        print(
            f"{model.upper()} "
            f"upstream probe failed: "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return

    if cycle is None:
        print(
            f"{model.upper()}: "
            f"no upstream cycle found"
        )

        return

    cycle_id = cycle[
        "id"
    ]

    print(
        f"{model.upper()} "
        f"latest upstream cycle: "
        f"{cycle_id}"
    )

    state = (
        load_state(
            model
        )
    )

    # ========================================================
    # GFS DUAL-LANE DISPATCH
    #
    # priority:
    #     masswx-gfs
    #     CONUS only
    #
    # backfill:
    #     masswx-gfs-backfill
    #     every region except CONUS
    #
    # Each lane has independent dispatch state and independent
    # active-execution protection.
    # ========================================================

    if model == "gfs":

        priority_job = (
            MODELS[
                "gfs"
            ][
                "job"
            ]
        )

        backfill_job = (
            MODELS[
                "gfs"
            ][
                "backfill_job"
            ]
        )

        priority_key = (
            "priority_last_launched_cycle"
        )

        backfill_key = (
            "backfill_last_launched_cycle"
        )

        priority_last = (
            state.get(
                priority_key
            )
        )

        backfill_last = (
            state.get(
                backfill_key
            )
        )

        legacy_last = (
            state.get(
                "last_launched_cycle"
            )
        )

        # ----------------------------------------------------
        # MIGRATE EXISTING SINGLE-LANE STATE
        #
        # Do not redispatch an already handled cycle merely
        # because the watcher code gained two new state keys.
        # ----------------------------------------------------

        if (
            priority_last is None
            and
            backfill_last is None
        ):

            baseline = (
                legacy_last
                or
                cycle_id
            )

            state[
                priority_key
            ] = baseline

            state[
                backfill_key
            ] = baseline

            state[
                "last_launched_cycle"
            ] = baseline

            state[
                "last_detected_cycle"
            ] = cycle_id

            save_state(
                model,
                state,
            )

            print(
                "GFS dual-lane watcher "
                f"state initialized at "
                f"{baseline}"
            )

            # If there was no old watcher state, this really is
            # the first baseline and we must not launch an old run.
            if not legacy_last:

                print(
                    f"GFS {cycle_id}: "
                    f"initial watcher baseline; "
                    f"no dispatch"
                )

                return

            priority_last = baseline
            backfill_last = baseline

        state[
            "last_detected_cycle"
        ] = cycle_id

        lanes = [
            (
                "priority",
                priority_job,
                priority_key,
            ),
            (
                "backfill",
                backfill_job,
                backfill_key,
            ),
        ]

        for (
            lane_name,
            job_name,
            state_key,
        ) in lanes:

            last_lane_cycle = (
                state.get(
                    state_key
                )
            )

            # ====================================================
            # SAME-CYCLE GFS RESUME
            #
            # "Already launched" is NOT the same as "cycle complete".
            #
            # GFS dissemination advances incrementally. A lane may
            # legitimately stop at the current NOAA frontier and need
            # another execution later for the SAME cycle.
            #
            # Active-execution protection below prevents duplicate
            # concurrent launches.
            # ====================================================

            same_cycle = (
                last_lane_cycle
                ==
                cycle_id
            )

            if same_cycle:

                print(
                    f"GFS {cycle_id}: "
                    f"{lane_name} lane was previously dispatched; "
                    f"checking whether it needs resume"
                )

            try:

                active = (
                    job_has_active_execution(
                        job_name
                    )
                )

            except Exception as error:

                print(
                    f"GFS {lane_name} "
                    f"execution check failed: "
                    f"{error}"
                )

                continue

            if active:

                print(
                    f"GFS: "
                    f"{job_name} already running; "
                    f"{lane_name} lane waits"
                )

                continue

            # ----------------------------------------------------
            # SAME-CYCLE RESUME COOLDOWN
            #
            # A completed execution may only have reached the
            # current NOAA frontier. Allow another execution of
            # the same cycle after a short delay. The GFS runner
            # itself determines the first missing forecast hour.
            #
            # A genuinely NEW cycle bypasses this cooldown.
            # ----------------------------------------------------

            if same_cycle:

                ready = (
                    cycle_is_ready(
                        "gfs",
                        cycle_id,
                    )
                )

                if ready is None:

                    continue

                if ready:

                    print(
                        f"GFS {cycle_id}: "
                        f"cycle READY; "
                        f"{lane_name} lane does not need resume"
                    )

                    continue

                if not gfs_lane_resume_allowed(
                    state,
                    lane_name,
                ):

                    continue

            try:

                launch_job(
                    job_name
                )

            except Exception as error:

                print(
                    f"GFS {lane_name} "
                    f"dispatch failed: "
                    f"{error}"
                )

                continue

            print(
                f"GFS {cycle_id}: "
                f"DISPATCHED "
                f"{lane_name} lane "
                f"{job_name}"
            )

            # Save immediately so a partial success is durable.
            # If one lane fails to dispatch, the successful lane
            # will not be launched twice on the next probe.
            state[
                state_key
            ] = cycle_id

            state[
                gfs_lane_resume_key(
                    lane_name
                )
            ] = utc_timestamp()

            save_state(
                model,
                state,
            )

        # Legacy compatibility field becomes current only when
        # BOTH GFS lanes have successfully dispatched.
        if (
            state.get(
                priority_key
            )
            ==
            cycle_id
            and
            state.get(
                backfill_key
            )
            ==
            cycle_id
        ):

            state[
                "last_launched_cycle"
            ] = cycle_id

        save_state(
            model,
            state,
        )

        return

    # ========================================================
    # GOOGLE MODEL ONE-SHOT DISPATCH
    # ========================================================
    #
    # FNV3 / FNV3-L / WN2 upstream resolvers return only an
    # actually available cycle. These pipelines should launch
    # once for a new cycle and must not use ECMWF/GFS
    # same-cycle frontier continuation behavior.
    #
    # Each production runner is responsible for publishing its
    # completed-cycle metadata.
    # ========================================================

    if model in (
        "fnv3",
        "fnv3_large",
        "wn2",
    ):
        job_name = MODELS[
            model
        ][
            "job"
        ]

        last_launched_cycle = state.get(
            "last_launched_cycle"
        )

        same_cycle = (
            last_launched_cycle == cycle_id
        )

        try:
            active = job_has_active_execution(
                job_name
            )
        except Exception as error:
            print(
                f"{model.upper()} execution check failed: "
                f"{error}"
            )
            return

        if active:
            print(
                f"{model.upper()}: "
                f"{job_name} already running; "
                f"not launching duplicate"
            )
            return

        if same_cycle:
            ready = cycle_is_ready(
                model,
                cycle_id,
            )

            if ready:
                print(
                    f"{model.upper()} {cycle_id}: "
                    f"cycle READY; no dispatch needed"
                )
                return

            if not model_resume_allowed(
                state,
                model,
            ):
                return

            print(
                f"{model.upper()} {cycle_id}: "
                f"incomplete and inactive; retrying"
            )

        try:
            launch_job(
                job_name
            )
        except Exception as error:
            print(
                f"{model.upper()} dispatch failed: "
                f"{error}"
            )
            return

        state[
            "last_detected_cycle"
        ] = cycle_id

        state[
            "last_launched_cycle"
        ] = cycle_id

        state[
            "last_dispatch_unix"
        ] = utc_timestamp()

        save_state(
            model,
            state,
        )

        print(
            f"{model.upper()} {cycle_id}: "
            f"DISPATCHED {job_name}"
        )

        return


    # ========================================================
    # IFS / AIFS SINGLE-LANE BEHAVIOR
    # ========================================================

    last_launched_cycle = (
        state.get(
            "last_launched_cycle"
        )
    )

    # A fresh watcher state must not silently consume an
    # available cycle. With no previous launch, treat the
    # resolved upstream cycle as new and continue to dispatch.
    same_cycle = (
        last_launched_cycle is not None
        and
        last_launched_cycle == cycle_id
    )

    if same_cycle:

        print(
            f"{model.upper()} "
            f"{cycle_id}: "
            f"previously dispatched; "
            f"checking whether continuation is needed"
        )

    job_name = (
        MODELS[
            model
        ][
            "job"
        ]
    )

    try:

        active = (
            job_has_active_execution(
                job_name
            )
        )

    except Exception as error:

        print(
            f"{model.upper()} "
            f"execution check failed: "
            f"{error}"
        )

        return

    if active:

        print(
            f"{model.upper()}: "
            f"{job_name} already running; "
            f"not launching duplicate"
        )

        return

    # ========================================================
    # SAME-CYCLE CONTINUATION
    #
    # A successful Cloud Run execution can mean either:
    #
    #   complete
    #
    # or:
    #
    #   waiting at the current ECMWF dissemination frontier
    #
    # READY.json distinguishes the two.
    # ========================================================

    if same_cycle:

        ready = (
            cycle_is_ready(
                model,
                cycle_id,
            )
        )

        if ready is None:

            return

        if ready:

            print(
                f"{model.upper()} "
                f"{cycle_id}: "
                f"cycle READY; "
                f"no continuation needed"
            )

            return

        if not model_resume_allowed(
            state,
            model,
        ):

            return

    try:

        launch_job(
            job_name
        )

    except Exception as error:

        print(
            f"{model.upper()} "
            f"dispatch failed: "
            f"{error}"
        )

        return

    print(
        f"{model.upper()} "
        f"{cycle_id}: "
        f"DISPATCHED {job_name}"
    )

    state[
        "last_detected_cycle"
    ] = cycle_id

    state[
        "last_launched_cycle"
    ] = cycle_id

    state[
        model_resume_key()
    ] = utc_timestamp()

    save_state(
        model,
        state,
    )



# ============================================================
# WATCH PASS
# ============================================================

def probe_all():
    """
    One short operational probe pass.

    Each model is checked once. Any ready model job is dispatched
    independently; the watcher itself does not wait for rendering.
    """
    for model in (
        "gfs",
        "ifs",
        "aifs",
        "fnv3",
        "fnv3_large",
        "wn2",
    ):
        probe_model(
            model
        )


def any_fast_window():
    now = utc_now()

    return any(
        model_is_in_fast_window(
            model,
            now=now,
        )
        for model in MODELS
    )



# ============================================================
# DISTRIBUTED WATCHER LOCK
#
# Prevent overlapping Cloud Run watcher executions from
# dispatching the same newly arriving model cycle.
# ============================================================

WATCHER_LOCK_OBJECT = (
    f"{STATE_ROOT}/watcher.lock"
)

WATCHER_LOCK_TTL_SECONDS = 90


def acquire_watcher_lock():
    """
    Acquire a short GCS-backed watcher lease.

    The create uses if_generation_match=0, so only ONE watcher
    execution can create the lock when it does not already exist.
    """

    blob = (
        get_bucket()
        .blob(
            WATCHER_LOCK_OBJECT
        )
    )

    now = time.time()

    # --------------------------------------------------------
    # REMOVE AN ABANDONED / EXPIRED LOCK
    # --------------------------------------------------------

    try:

        if blob.exists():

            payload = json.loads(
                blob.download_as_text()
            )

            created = float(
                payload.get(
                    "created_unix",
                    0,
                )
            )

            if (
                created > 0
                and
                (
                    now
                    -
                    created
                )
                <
                WATCHER_LOCK_TTL_SECONDS
            ):

                print(
                    "Another watcher execution "
                    "already owns the active lock."
                )

                return False

            print(
                "Removing expired watcher lock."
            )

            try:
                blob.delete()

            except Exception:
                pass

    except Exception as error:

        print(
            f"Watcher lock inspection failed: "
            f"{error}"
        )

        return False

    # --------------------------------------------------------
    # ATOMIC CREATE
    # --------------------------------------------------------

    payload = {
        "created_unix": now,
        "created_at_utc": (
            utc_now()
            .replace(
                microsecond=0
            )
            .isoformat()
        ),
    }

    try:

        blob.upload_from_string(
            json.dumps(
                payload,
                indent=2,
            ),
            content_type="application/json",
            if_generation_match=0,
        )

        print(
            "Watcher lock acquired."
        )

        return True

    except Exception as error:

        # Another execution most likely won the atomic create.
        print(
            f"Watcher lock not acquired: "
            f"{error}"
        )

        return False


def release_watcher_lock():

    blob = (
        get_bucket()
        .blob(
            WATCHER_LOCK_OBJECT
        )
    )

    try:

        blob.delete()

        print(
            "Watcher lock released."
        )

    except Exception as error:

        print(
            f"Watcher lock release warning: "
            f"{error}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    if not acquire_watcher_lock():

        print(
            "Watcher execution exiting "
            "because another watcher is active."
        )

        return

    try:

        _run_watcher()

    finally:

        release_watcher_lock()


def _run_watcher():
    """
    Perform exactly one operational probe pass.

    The watcher detects upstream availability, dispatches any
    required Cloud Run model jobs, then exits immediately.
    Rendering continues independently in those jobs.
    """
    print("=" * 60)
    print("MASSACHUSETTSWX MODEL WATCHER")
    print("=" * 60)

    print(
        f"UTC now: {utc_now().isoformat()}"
    )

    probe_all()

    print()
    print("Watcher pass complete; exiting.")


if __name__ == "__main__":
    main()
