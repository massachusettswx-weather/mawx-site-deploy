from pathlib import Path
from datetime import datetime, timezone

import json
import os
import socket
import traceback


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)


# ============================================================
# RUNTIME DIRECTORIES
# ============================================================

RUNTIME_DIR = (
    ROOT_DIR
    / "runtime"
)

STATE_DIR = (
    RUNTIME_DIR
    / "state"
)

LOCK_DIR = (
    RUNTIME_DIR
    / "locks"
)

LOG_DIR = (
    RUNTIME_DIR
    / "logs"
)


# ============================================================
# DIRECTORY INITIALIZATION
# ============================================================

def ensure_runtime_directories():
    for directory in [
        RUNTIME_DIR,
        STATE_DIR,
        LOCK_DIR,
        LOG_DIR,
    ]:

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================
# UTC TIME
# ============================================================

def utc_now():
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


# ============================================================
# STATE FILE
# ============================================================

def get_state_path(
    model,
):
    ensure_runtime_directories()

    return (
        STATE_DIR
        / f"{model}.json"
    )


# ============================================================
# DEFAULT STATE
# ============================================================

def default_state(
    model,
):
    return {
        "model": model,

        "status": "never_run",

        "last_attempt": None,

        "last_success": None,

        "last_failure": None,

        "last_completed_cycle": None,

        "active_cycle": None,

        "completed_cycles": [],

        "failed_cycles": {},

        "error": None,

        "hostname": None,

        "pid": None,
    }


# ============================================================
# LOAD STATE
# ============================================================

def load_state(
    model,
):
    path = get_state_path(
        model
    )

    if not path.exists():
        return default_state(
            model
        )

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            loaded = json.load(
                file
            )

    except Exception:

        # Corrupted state should never kill the backend.
        return default_state(
            model
        )

    state = default_state(
        model
    )

    state.update(
        loaded
    )

    return state


# ============================================================
# WRITE STATE ATOMICALLY
# ============================================================

def save_state(
    model,
    state,
):
    ensure_runtime_directories()

    path = get_state_path(
        model
    )

    temporary = (
        path.parent
        / f".{path.name}.tmp"
    )

    with open(
        temporary,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            state,
            file,
            indent=2,
            sort_keys=True,
        )

    temporary.replace(
        path
    )

    return path


# ============================================================
# UPDATE STATE
# ============================================================

def update_state(
    model,
    **changes,
):
    state = load_state(
        model
    )

    state.update(
        changes
    )

    save_state(
        model,
        state,
    )

    return state


# ============================================================
# RUN START
# ============================================================

def mark_run_started(
    model,
    cycle=None,
):
    return update_state(
        model,

        status="running",

        last_attempt=utc_now(),

        active_cycle=cycle,

        error=None,

        hostname=socket.gethostname(),

        pid=os.getpid(),
    )


# ============================================================
# RUN SUCCESS
# ============================================================

def mark_run_success(
    model,
    cycle=None,
):
    state = load_state(
        model
    )

    now = utc_now()

    state[
        "status"
    ] = "complete"

    state[
        "last_success"
    ] = now

    state[
        "error"
    ] = None

    state[
        "hostname"
    ] = None

    state[
        "pid"
    ] = None

    if cycle is not None:

        state[
            "last_completed_cycle"
        ] = cycle

        completed = state.get(
            "completed_cycles",
            [],
        )

        if cycle not in completed:

            completed.append(
                cycle
            )

        # Prevent unlimited state-file growth.
        state[
            "completed_cycles"
        ] = completed[
            -30:
        ]

        failed_cycles = state.get(
            "failed_cycles",
            {},
        )

        failed_cycles.pop(
            cycle,
            None,
        )

        state[
            "failed_cycles"
        ] = failed_cycles

    state[
        "active_cycle"
    ] = None

    save_state(
        model,
        state,
    )

    return state


# ============================================================
# RUN FAILURE
# ============================================================

def mark_run_failure(
    model,
    error,
    cycle=None,
):
    state = load_state(
        model
    )

    now = utc_now()

    state[
        "status"
    ] = "failed"

    state[
        "last_failure"
    ] = now

    state[
        "active_cycle"
    ] = None

    state[
        "hostname"
    ] = None

    state[
        "pid"
    ] = None

    state[
        "error"
    ] = str(
        error
    )

    if cycle is not None:

        failed_cycles = state.get(
            "failed_cycles",
            {},
        )

        previous = failed_cycles.get(
            cycle,
            {},
        )

        attempts = (
            previous.get(
                "attempts",
                0,
            )
            + 1
        )

        failed_cycles[
            cycle
        ] = {
            "attempts": attempts,

            "last_failure": now,

            "error": str(
                error
            ),
        }

        state[
            "failed_cycles"
        ] = failed_cycles

    save_state(
        model,
        state,
    )

    return state


# ============================================================
# CYCLE CHECK
# ============================================================

def cycle_completed(
    model,
    cycle,
):
    if cycle is None:
        return False

    state = load_state(
        model
    )

    return (
        cycle
        in state.get(
            "completed_cycles",
            [],
        )
    )


# ============================================================
# LOCK PATH
# ============================================================

def get_lock_path(
    model,
):
    ensure_runtime_directories()

    return (
        LOCK_DIR
        / f"{model}.lock"
    )


# ============================================================
# READ LOCK
# ============================================================

def read_lock(
    model,
):
    path = get_lock_path(
        model
    )

    if not path.exists():
        return None

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(
                file
            )

    except Exception:

        return None


# ============================================================
# PROCESS CHECK
# ============================================================

def process_is_alive(
    pid,
):
    if pid is None:
        return False

    try:

        os.kill(
            int(pid),
            0,
        )

        return True

    except (
        ProcessLookupError,
        ValueError,
    ):

        return False

    except PermissionError:

        # Process exists but belongs to another user.
        return True


# ============================================================
# CHECK LOCK
# ============================================================

def model_is_locked(
    model,
):
    lock = read_lock(
        model
    )

    if lock is None:
        return False

    lock_host = lock.get(
        "hostname"
    )

    pid = lock.get(
        "pid"
    )

    # If lock belongs to this machine,
    # verify the process still exists.
    if (
        lock_host
        == socket.gethostname()
    ):

        if process_is_alive(
            pid
        ):

            return True

        # Stale lock.
        release_lock(
            model
        )

        return False

    # Different host:
    # conservatively consider it locked.
    return True


# ============================================================
# ACQUIRE LOCK
# ============================================================

def acquire_lock(
    model,
):
    ensure_runtime_directories()

    if model_is_locked(
        model
    ):

        return False

    path = get_lock_path(
        model
    )

    payload = {
        "model": model,

        "pid": os.getpid(),

        "hostname": socket.gethostname(),

        "created": utc_now(),
    }

    temporary = (
        path.parent
        / f".{path.name}.{os.getpid()}.tmp"
    )

    with open(
        temporary,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
        )

    try:

        os.link(
            temporary,
            path,
        )

    except FileExistsError:

        temporary.unlink(
            missing_ok=True
        )

        return False

    temporary.unlink(
        missing_ok=True
    )

    return True


# ============================================================
# RELEASE LOCK
# ============================================================

def release_lock(
    model,
):
    path = get_lock_path(
        model
    )

    try:

        path.unlink()

    except FileNotFoundError:

        pass


# ============================================================
# LOG FILE
# ============================================================

def get_log_path(
    model,
):
    ensure_runtime_directories()

    return (
        LOG_DIR
        / f"{model}.log"
    )


# ============================================================
# LOG MESSAGE
# ============================================================

def write_log(
    model,
    message,
):
    path = get_log_path(
        model
    )

    with open(
        path,
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            f"[{utc_now()}] "
            f"{message}\n"
        )


# ============================================================
# LOG EXCEPTION
# ============================================================

def write_exception(
    model,
    error,
):
    path = get_log_path(
        model
    )

    with open(
        path,
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            "\n"
        )

        file.write(
            f"[{utc_now()}] "
            f"EXCEPTION\n"
        )

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
            file=file,
        )

        file.write(
            "\n"
        )