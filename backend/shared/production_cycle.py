from __future__ import annotations

import json

from datetime import (
    datetime,
    timezone,
)

from shared.storage import (
    get_bucket,
)


def utc_now_iso():
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def metadata_root(
    model,
    cycle_id,
):
    return (
        f"metadata/"
        f"{model}/"
        f"{cycle_id}"
    )


def upload_json(
    object_name,
    payload,
):
    (
        get_bucket()
        .blob(
            object_name
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


def publish_cycle_started(
    *,
    model,
    cycle_id,
    extra=None,
):
    root = (
        metadata_root(
            model,
            cycle_id,
        )
    )

    payload = {
        "model": model,
        "cycle": cycle_id,
        "cycle_id": cycle_id,
        "status": "running",
        "started_at_utc": (
            utc_now_iso()
        ),
    }

    if extra:
        payload.update(
            extra
        )

    progress_object = (
        f"{root}/progress.json"
    )

    current_object = (
        f"metadata/"
        f"{model}/"
        f"current.json"
    )

    upload_json(
        progress_object,
        payload,
    )

    upload_json(
        current_object,
        {
            "model": model,
            "cycle": cycle_id,
            "cycle_id": cycle_id,
            "status": "running",
            "manifest_object": (
                progress_object
            ),
            "updated_at_utc": (
                utc_now_iso()
            ),
        },
    )

    return payload


def publish_cycle_progress(
    *,
    model,
    cycle_id,
    payload,
):
    root = (
        metadata_root(
            model,
            cycle_id,
        )
    )

    data = {
        "model": model,
        "cycle": cycle_id,
        "cycle_id": cycle_id,
        "status": "running",
        "updated_at_utc": (
            utc_now_iso()
        ),
    }

    data.update(
        payload
    )

    progress_object = (
        f"{root}/progress.json"
    )

    upload_json(
        progress_object,
        data,
    )

    upload_json(
        (
            f"metadata/"
            f"{model}/"
            f"current.json"
        ),
        {
            "model": model,
            "cycle": cycle_id,
            "cycle_id": cycle_id,
            "status": "running",
            "manifest_object": (
                progress_object
            ),
            "updated_at_utc": (
                utc_now_iso()
            ),
        },
    )

    return data


def publish_cycle_completed(
    *,
    model,
    cycle_id,
    payload=None,
):
    root = (
        metadata_root(
            model,
            cycle_id,
        )
    )

    completed_at = (
        utc_now_iso()
    )

    data = {
        "model": model,
        "cycle": cycle_id,
        "cycle_id": cycle_id,
        "status": "complete",
        "completed_at_utc": (
            completed_at
        ),
    }

    if payload:
        data.update(
            payload
        )

    progress_object = (
        f"{root}/progress.json"
    )

    ready_object = (
        f"{root}/READY.json"
    )

    pointer = {
        "model": model,
        "cycle": cycle_id,
        "cycle_id": cycle_id,
        "status": "complete",
        "manifest_object": (
            progress_object
        ),
        "updated_at_utc": (
            completed_at
        ),
    }

    upload_json(
        progress_object,
        data,
    )

    upload_json(
        ready_object,
        {
            **pointer,
            "completed_at_utc": (
                completed_at
            ),
        },
    )

    upload_json(
        (
            f"metadata/"
            f"{model}/"
            f"latest.json"
        ),
        pointer,
    )

    upload_json(
        (
            f"metadata/"
            f"{model}/"
            f"current.json"
        ),
        pointer,
    )

    try:
        from shared.archive import (
            publish_archive_catalog,
        )

        publish_archive_catalog(
            model=model,
        )

    except Exception as error:
        print(
            f"WARNING: "
            f"{model.upper()} archive refresh failed: "
            f"{type(error).__name__}: "
            f"{error}"
        )

    return data
