from __future__ import annotations

import json
import tempfile
from pathlib import Path

from shared.cyclone_publish import (
    upload_file,
)


def metadata_prefix(
    model,
    date,
    hour,
):
    return (
        f"metadata/"
        f"{model}/"
        f"{date}_{int(hour):02d}z"
    )


def publish_json(
    data,
    object_name,
):
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
    ) as handle:
        json.dump(
            data,
            handle,
            indent=2,
            sort_keys=True,
        )

        path = Path(
            handle.name
        )

    return upload_file(
        path,
        object_name,
        content_type=(
            "application/json"
        ),
        delete_after_upload=True,
    )


def publish_progress(
    status,
):
    prefix = metadata_prefix(
        status["model"],
        status["date"],
        status["hour"],
    )

    return publish_json(
        status,
        f"{prefix}/progress.json",
    )


def publish_manifest(
    manifest,
):
    cycle = manifest["cycle"]

    prefix = metadata_prefix(
        manifest["model"],
        cycle["date"],
        cycle["hour"],
    )

    return publish_json(
        manifest,
        f"{prefix}/manifest.json",
    )


def publish_current(
    *,
    model,
    date,
    hour,
    status,
):
    data = {
        "model": model,
        "date": str(date),
        "hour": int(hour),
        "cycle": (
            f"{date}_{int(hour):02d}z"
        ),
        "status": status,
        "progress_object": (
            f"metadata/"
            f"{model}/"
            f"{date}_{int(hour):02d}z/"
            f"progress.json"
        ),
        "manifest_object": (
            f"metadata/"
            f"{model}/"
            f"{date}_{int(hour):02d}z/"
            f"manifest.json"
        ),
    }

    return publish_json(
        data,
        f"metadata/{model}/current.json",
    )


def publish_archive(
    *,
    model,
    archive,
):
    return publish_json(
        archive,
        f"metadata/{model}/archive.json",
    )
