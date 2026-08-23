import os
import subprocess
import sys
from datetime import datetime


def run_module(module_name):
    print(
        f"[cloud-job] launching python -m {module_name}",
        flush=True,
    )

    result = subprocess.run(
        [sys.executable, "-m", module_name],
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{module_name} exited with code {result.returncode}"
        )

    return None


def normalize_cycle(resolved):
    if resolved is None:
        raise RuntimeError(
            "Cycle resolver returned None."
        )

    if isinstance(resolved, datetime):
        cycle_date = resolved.strftime("%Y%m%d")
        cycle_hour = int(resolved.hour)

        return {
            "id": f"{cycle_date}_{cycle_hour:02d}z",
            "date": cycle_date,
            "hour": cycle_hour,
        }

    if isinstance(resolved, dict):
        cycle_date = resolved.get("date")
        cycle_hour = resolved.get("hour")
        cycle_id = resolved.get("id")

        if cycle_date is None:
            raise RuntimeError(
                "Resolved cycle dictionary does not contain 'date'."
            )

        if cycle_hour is None:
            raise RuntimeError(
                "Resolved cycle dictionary does not contain 'hour'."
            )

        if isinstance(cycle_date, datetime):
            cycle_date = cycle_date.strftime("%Y%m%d")
        else:
            cycle_date = str(cycle_date).replace("-", "")[:8]

        cycle_hour = int(cycle_hour)

        if not cycle_id:
            cycle_id = (
                f"{cycle_date}_{cycle_hour:02d}z"
            )

        return {
            "id": cycle_id,
            "date": cycle_date,
            "hour": cycle_hour,
        }

    raise RuntimeError(
        "Unsupported cycle resolver result: "
        f"{type(resolved).__name__}"
    )


def run_ecmwf_model(model):
    from shared.cycles import latest_cycle

    print(
        f"[cloud-job] resolving latest available "
        f"{model.upper()} cycle...",
        flush=True,
    )

    resolved = latest_cycle(model)
    cycle = normalize_cycle(resolved)

    print(
        f"[cloud-job] resolved {model.upper()} cycle: "
        f"{cycle['id']}",
        flush=True,
    )

    if model == "ifs":
        from ifs.run import run_ifs

        return run_ifs(
            cycle=cycle
        )

    if model == "aifs":
        from aifs.run import run_aifs

        return run_aifs(
            cycle=cycle
        )

    raise RuntimeError(
        f"Unsupported ECMWF model: {model}"
    )


def main():
    model = (
        os.environ
        .get("MODEL", "")
        .strip()
        .lower()
    )

    print("=" * 60, flush=True)
    print(
        "MASSACHUSETTSWX CLOUD MODEL JOB",
        flush=True,
    )
    print("=" * 60, flush=True)
    print(f"Model: {model}", flush=True)
    print()

    if model == "gfs":
        result = run_module("gfs.run")

    elif model == "ifs":
        result = run_ecmwf_model("ifs")

    elif model == "aifs":
        result = run_ecmwf_model("aifs")

    elif model == "fnv3":
        from fnv3.run import run_fnv3
        result = run_fnv3()

    elif model in {
        "fnv3_large",
        "fnv3-large",
        "fnv3l",
    }:
        from fnv3_large.run import run_fnv3_large
        result = run_fnv3_large()

    else:
        raise RuntimeError(
            "Unknown MODEL. Expected one of: "
            "gfs, ifs, aifs, fnv3, fnv3_large"
        )

    print()
    print("=" * 60, flush=True)
    print(
        f"{model.upper()} COMPLETED",
        flush=True,
    )

    if result is not None:
        print(result, flush=True)

    print("=" * 60, flush=True)


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(
            f"[cloud-job] FAILED: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
            flush=True,
        )
        raise
