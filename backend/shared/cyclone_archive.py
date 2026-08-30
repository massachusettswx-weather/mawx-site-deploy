from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)


CYCLONE_ARCHIVE_DAYS = 7

CYCLONE_ARCHIVE_MODELS = (
    "fnv3",
    "fnv3_large",
)


def get_cyclone_archive_days(
    model,
):
    model = (
        str(model)
        .strip()
        .lower()
    )

    if model not in (
        CYCLONE_ARCHIVE_MODELS
    ):
        raise ValueError(
            f"Unsupported cyclone model: {model}"
        )

    return CYCLONE_ARCHIVE_DAYS


def archive_cutoff():
    return (
        datetime.now(
            timezone.utc
        )
        -
        timedelta(
            days=CYCLONE_ARCHIVE_DAYS
        )
    )


def build_archive_document(
    *,
    model,
    cycles,
):
    model = (
        str(model)
        .strip()
        .lower()
    )

    get_cyclone_archive_days(
        model
    )

    normalized = []

    for cycle in cycles:

        date = str(
            cycle["date"]
        )

        hour = int(
            cycle["hour"]
        )

        cycle_id = (
            f"{date}_{hour:02d}z"
        )

        normalized.append(
            {
                "cycle": cycle_id,
                "date": date,
                "hour": hour,
                "status": cycle.get(
                    "status",
                    "complete",
                ),
                "manifest_object": (
                    cycle.get(
                        "manifest_object"
                    )
                    or
                    (
                        f"metadata/{model}/"
                        f"{cycle_id}/"
                        f"manifest.json"
                    )
                ),
                "progress_object": (
                    cycle.get(
                        "progress_object"
                    )
                    or
                    (
                        f"metadata/{model}/"
                        f"{cycle_id}/"
                        f"progress.json"
                    )
                ),
            }
        )

    normalized.sort(
        key=lambda item: (
            item["date"],
            item["hour"],
        ),
        reverse=True,
    )

    return {
        "schema_version": 1,
        "model": model,
        "retention_days": (
            CYCLONE_ARCHIVE_DAYS
        ),
        "cycles": normalized,
    }
