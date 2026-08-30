from __future__ import annotations

from pathlib import Path

from shared.cyclone_output import (
    cyclone_object_name,
)


def get_storage_bucket_name():
    import os

    bucket = os.environ.get(
        "WEATHER_STORAGE_BUCKET",
        "massachusettswx-nwp-project",
    )

    return bucket


def object_exists(
    object_name,
):
    try:
        from google.cloud import storage

        client = storage.Client()

        bucket = client.bucket(
            get_storage_bucket_name()
        )

        return bucket.blob(
            object_name
        ).exists()

    except Exception:
        return False


def upload_file(
    local_path,
    object_name,
    *,
    content_type="image/png",
    delete_after_upload=True,
):
    from google.cloud import storage

    local_path = Path(
        local_path
    )

    client = storage.Client()

    bucket = client.bucket(
        get_storage_bucket_name()
    )

    blob = bucket.blob(
        object_name
    )

    blob.upload_from_filename(
        str(local_path),
        content_type=content_type,
    )

    if delete_after_upload:
        try:
            local_path.unlink()
        except FileNotFoundError:
            pass

    return object_name


def publish_cyclone_frame(
    *,
    request,
    local_path,
    delete_after_upload=True,
):
    object_name = cyclone_object_name(
        model=request.model,
        date=request.date,
        hour=request.hour,
        product=request.product,
        region=request.region,
        forecast_hour=(
            request.forecast_hour
        ),
    )

    upload_file(
        local_path,
        object_name,
        delete_after_upload=(
            delete_after_upload
        ),
    )

    return object_name


def frame_already_published(
    request,
):
    object_name = cyclone_object_name(
        model=request.model,
        date=request.date,
        hour=request.hour,
        product=request.product,
        region=request.region,
        forecast_hour=(
            request.forecast_hour
        ),
    )

    return object_exists(
        object_name
    )
