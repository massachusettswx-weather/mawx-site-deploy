from __future__ import annotations

import json


from shared.storage import (
    get_bucket,
)


# ============================================================
# CYCLE ID
# ============================================================

def build_cycle_id(
    cycle_date,
    cycle_hour,
):
    """
    Build the canonical operational cycle identifier.

    Example:

        20260814_00z
    """

    return (
        f"{str(cycle_date)}_"
        f"{int(cycle_hour):02d}z"
    )


# ============================================================
# PROGRESS OBJECT
# ============================================================

def get_progress_object_name(
    model,
    cycle_date,
    cycle_hour,
):
    """
    Return the progressive-publication metadata object.

    Example:

        metadata/gfs/20260814_00z/progress.json
        metadata/ifs/20260814_00z/progress.json
        metadata/aifs/20260814_00z/progress.json
    """

    model = (
        str(model)
        .lower()
        .strip()
    )

    cycle_id = (
        build_cycle_id(
            cycle_date,
            cycle_hour,
        )
    )

    return (
        f"metadata/"
        f"{model}/"
        f"{cycle_id}/"
        f"progress.json"
    )


# ============================================================
# READ PROGRESS
# ============================================================

def load_progress(
    model,
    cycle_date,
    cycle_hour,
):
    """
    Read progressive cycle metadata from GCS.

    Returns None when the model cycle has never published progress.

    A metadata-read failure does NOT prevent the model pipeline
    from running; callers may safely fall back to a fresh run.
    """

    object_name = (
        get_progress_object_name(
            model,
            cycle_date,
            cycle_hour,
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

        payload = (
            json.loads(
                text
            )
        )

        if not isinstance(
            payload,
            dict,
        ):

            return None

        return payload

    except Exception as error:

        print()
        print(
            f"{str(model).upper()} "
            f"resume metadata read failed: "
            f"{error}"
        )

        return None


# ============================================================
# PUBLISHED FORECAST HOURS
# ============================================================

def get_published_forecast_hours(
    model,
    cycle_date,
    cycle_hour,
):
    """
    Return forecast hours already successfully published to GCS.

    The progressive publisher writes these hours only after the
    forecast-hour PNGs have uploaded and been inventoried.

    Therefore these are safe hours to skip during a resumed run.
    """

    progress = (
        load_progress(
            model,
            cycle_date,
            cycle_hour,
        )
    )

    if progress is None:

        return set()

    raw_hours = (
        progress.get(
            "available_forecast_hours",
            [],
        )
    )

    published = set()

    for hour in raw_hours:

        try:

            published.add(
                int(
                    hour
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

    return published


# ============================================================
# BUILD RESUME PLAN
# ============================================================

def build_resume_plan(
    *,
    model,
    cycle_date,
    cycle_hour,
    forecast_hours,
):
    """
    Compare the model's expected forecast schedule against GCS.

    Returns:

        {
            "expected": [...],
            "published": [...],
            "remaining": [...],
            "expected_count": int,
            "published_count": int,
            "remaining_count": int,
            "resume_hour": int | None,
            "complete": bool,
        }

    This function is model-independent.
    """

    expected = sorted(
        {
            int(
                hour
            )
            for hour in forecast_hours
        }
    )

    published_all = (
        get_published_forecast_hours(
            model,
            cycle_date,
            cycle_hour,
        )
    )

    # Only count published hours that belong to the model's
    # current configured forecast schedule.
    published = [
        hour
        for hour in expected
        if hour in published_all
    ]

    remaining = [
        hour
        for hour in expected
        if hour not in published_all
    ]

    return {
        "expected": expected,

        "published": published,

        "remaining": remaining,

        "expected_count": (
            len(
                expected
            )
        ),

        "published_count": (
            len(
                published
            )
        ),

        "remaining_count": (
            len(
                remaining
            )
        ),

        "resume_hour": (
            remaining[
                0
            ]
            if remaining
            else None
        ),

        "complete": (
            len(
                remaining
            )
            == 0
        ),
    }


# ============================================================
# DISPLAY RESUME PLAN
# ============================================================

def print_resume_plan(
    model,
    plan,
):
    """
    Print a concise startup summary for a model pipeline.
    """

    model_name = (
        str(model)
        .upper()
    )

    print()
    print(
        f"{model_name} cloud resume:"
    )

    print(
        f"  Expected frames: "
        f"{plan['expected_count']}"
    )

    print(
        f"  Already published: "
        f"{plan['published_count']}"
    )

    print(
        f"  Remaining: "
        f"{plan['remaining_count']}"
    )

    if plan[
        "complete"
    ]:

        print(
            "  Cycle already complete."
        )

    elif plan[
        "resume_hour"
    ] is not None:

        print(
            f"  Resume at: "
            f"f"
            f"{plan['resume_hour']:03d}"
        )


# ============================================================
# CONVENIENCE HELPER
# ============================================================

def get_remaining_forecast_hours(
    *,
    model,
    cycle_date,
    cycle_hour,
    forecast_hours,
    print_status=True,
):
    """
    Main helper intended for model run.py files.

    Example:

        forecast_hours = get_remaining_forecast_hours(
            model="gfs",
            cycle_date="20260814",
            cycle_hour=0,
            forecast_hours=forecast_hours,
        )

    The returned list contains ONLY forecast hours that still need
    to be downloaded/rendered/uploaded.
    """

    plan = (
        build_resume_plan(
            model=model,
            cycle_date=cycle_date,
            cycle_hour=cycle_hour,
            forecast_hours=(
                forecast_hours
            ),
        )
    )

    if print_status:

        print_resume_plan(
            model,
            plan,
        )

    return list(
        plan[
            "remaining"
        ]
    )
