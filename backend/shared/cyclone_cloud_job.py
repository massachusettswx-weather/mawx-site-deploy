from __future__ import annotations

from fnv3_cyclone.operational import (
    run_fnv3_operational,
)

from fnv3_large_cyclone.operational import (
    run_fnv3_large_operational,
)


def run_cyclone_cloud_job(
    model,
):
    model = (
        str(model)
        .strip()
        .lower()
        .replace("-", "_")
    )

    if model == "fnv3":
        return run_fnv3_operational()

    if model in (
        "fnv3_large",
        "fnv3l",
        "fnv3_l",
    ):
        return (
            run_fnv3_large_operational()
        )

    raise ValueError(
        f"Unsupported cyclone job: "
        f"{model}"
    )
