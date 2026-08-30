from __future__ import annotations

from shared.resume import (
    get_published_forecast_hours,
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_hours(
    hours,
):
    """
    Return sorted unique integer forecast hours.
    """

    if hours is None:
        return []

    normalized = set()

    for hour in hours:

        try:
            normalized.add(
                int(hour)
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    return sorted(
        normalized
    )


# ============================================================
# OPERATIONAL WORK PLAN
# ============================================================

def build_operational_plan(
    *,
    model,
    cycle_date,
    cycle_hour,
    expected_hours,
    available_hours=None,
):
    """
    Build the authoritative work plan for one model cycle.

    expected_hours:
        Every forecast hour configured for this model/cycle.

    available_hours:
        Forecast hours known to exist upstream right now.

        If None, all expected hours are treated as available.
        This is useful for sources where availability is already
        guaranteed before the model runner is started.

    published hours:
        Loaded from persistent progress.json in GCS.

    The resulting work_hours are therefore:

        available upstream
        MINUS
        already safely published

    This makes repeated Cloud Scheduler / Cloud Run invocations
    idempotent.
    """

    expected = normalize_hours(
        expected_hours
    )

    published_raw = (
        get_published_forecast_hours(
            model,
            cycle_date,
            cycle_hour,
        )
    )

    published = [
        hour
        for hour in expected
        if hour in published_raw
    ]

    if available_hours is None:

        available = list(
            expected
        )

    else:

        available_raw = set(
            normalize_hours(
                available_hours
            )
        )

        available = [
            hour
            for hour in expected
            if hour in available_raw
        ]

    work_hours = [
        hour
        for hour in available
        if hour not in published_raw
    ]

    waiting_upstream = [
        hour
        for hour in expected
        if (
            hour not in available
            and
            hour not in published_raw
        )
    ]

    complete = (
        len(published)
        ==
        len(expected)
        and
        len(expected)
        >
        0
    )

    return {
        "model": str(model).lower(),

        "cycle_date": str(
            cycle_date
        ),

        "cycle_hour": int(
            cycle_hour
        ),

        "expected": expected,

        "available": available,

        "published": published,

        "work_hours": work_hours,

        "waiting_upstream": (
            waiting_upstream
        ),

        "expected_count": len(
            expected
        ),

        "available_count": len(
            available
        ),

        "published_count": len(
            published
        ),

        "work_count": len(
            work_hours
        ),

        "waiting_upstream_count": len(
            waiting_upstream
        ),

        "resume_hour": (
            work_hours[0]
            if work_hours
            else None
        ),

        "complete": complete,
    }


# ============================================================
# DISPLAY PLAN
# ============================================================

def print_operational_plan(
    plan,
):
    """
    Print a concise production-cycle summary.
    """

    model = (
        str(
            plan["model"]
        )
        .upper()
    )

    print()
    print(
        f"{model} operational plan:"
    )

    print(
        f"  Expected: "
        f"{plan['expected_count']}"
    )

    print(
        f"  Available upstream: "
        f"{plan['available_count']}"
    )

    print(
        f"  Already published: "
        f"{plan['published_count']}"
    )

    print(
        f"  Ready to process: "
        f"{plan['work_count']}"
    )

    print(
        f"  Waiting upstream: "
        f"{plan['waiting_upstream_count']}"
    )

    if plan["complete"]:

        print(
            "  Cycle complete."
        )

    elif (
        plan["resume_hour"]
        is not None
    ):

        print(
            f"  Next work hour: "
            f"f"
            f"{plan['resume_hour']:03d}"
        )

    else:

        print(
            "  No forecast hour "
            "is ready for processing."
        )


# ============================================================
# RESULT VALIDATION
# ============================================================

def require_success(
    *,
    model,
    forecast_hour,
    stage,
    result,
    failed_key="failed",
):
    """
    Hard publication gate.

    A stage with reported failures raises immediately.

    This is intentionally strict:
    a partially rendered/uploaded forecast hour must never become
    advertised as available to the website.
    """

    if result is None:

        raise RuntimeError(
            f"{str(model).upper()} "
            f"f{int(forecast_hour):03d} "
            f"{stage}: "
            f"no result returned."
        )

    failed = int(
        result.get(
            failed_key,
            0,
        )
    )

    if failed > 0:

        raise RuntimeError(
            f"{str(model).upper()} "
            f"f{int(forecast_hour):03d} "
            f"{stage}: "
            f"{failed} failures. "
            f"Forecast hour will NOT "
            f"be published."
        )

    return result
