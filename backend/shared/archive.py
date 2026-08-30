from datetime import (
    datetime,
    timedelta,
    timezone,
)

import json
import os
import re

from google.cloud import storage


# ============================================================
# SETTINGS
# ============================================================

ARCHIVE_DAYS = int(
    os.environ.get(
        "MODEL_ARCHIVE_DAYS",
        "7",
    )
)

BUCKET_NAME = (
    os.environ.get(
        "MODEL_OUTPUT_BUCKET",
    )
    or
    os.environ.get(
        "GCS_BUCKET",
    )
    or
    "massachusettswx-nwp-project"
)


# ============================================================
# CYCLE FORMAT
# ============================================================

CYCLE_PATTERN = re.compile(
    r"^metadata/"
    r"(?P<model>[a-z0-9_-]+)/"
    r"(?P<date>\d{8})_"
    r"(?P<hour>\d{2})z/"
    r"progress\.json$"
)


def cycle_datetime(
    cycle_date,
    cycle_hour,
):
    return datetime.strptime(
        (
            f"{cycle_date}"
            f"{int(cycle_hour):02d}"
        ),
        "%Y%m%d%H",
    ).replace(
        tzinfo=timezone.utc
    )


# ============================================================
# BUILD ARCHIVE
# ============================================================

def build_archive_catalog(
    model,
    archive_days=ARCHIVE_DAYS,
):
    """
    Discover recent published cycle manifests for one model.

    The archive is derived from existing progress.json objects,
    so it does not require a separate database.
    """

    model = (
        str(model)
        .strip()
        .lower()
    )

    client = storage.Client()

    bucket = client.bucket(
        BUCKET_NAME
    )

    prefix = (
        f"metadata/{model}/"
    )

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now
        -
        timedelta(
            days=archive_days
        )
    )

    cycles = []

    for blob in client.list_blobs(
        bucket,
        prefix=prefix,
    ):

        match = CYCLE_PATTERN.match(
            blob.name
        )

        if not match:
            continue

        cycle_date = (
            match.group(
                "date"
            )
        )

        cycle_hour = int(
            match.group(
                "hour"
            )
        )

        valid_time = cycle_datetime(
            cycle_date,
            cycle_hour,
        )

        if valid_time < cutoff:
            continue

        cycle_id = (
            f"{cycle_date}_"
            f"{cycle_hour:02d}z"
        )

        cycles.append(
            {
                "id": cycle_id,
                "cycle": cycle_id,
                "date": cycle_date,
                "hour": cycle_hour,
                "datetime": (
                    valid_time
                    .isoformat()
                ),
                "manifest_object": (
                    blob.name
                ),
            }
        )

    cycles.sort(
        key=lambda item: (
            item[
                "datetime"
            ]
        ),
        reverse=True,
    )

    return {
        "model": model,
        "archive_days": (
            archive_days
        ),
        "generated_at_utc": (
            now.isoformat()
        ),
        "cycle_count": (
            len(cycles)
        ),
        "cycles": cycles,
    }


# ============================================================
# PUBLISH ARCHIVE
# ============================================================

def publish_archive_catalog(
    model,
    archive_days=ARCHIVE_DAYS,
):
    """
    Build and upload:

        metadata/<model>/archive.json
    """

    catalog = (
        build_archive_catalog(
            model=model,
            archive_days=(
                archive_days
            ),
        )
    )

    client = storage.Client()

    bucket = client.bucket(
        BUCKET_NAME
    )

    object_name = (
        f"metadata/{model}/"
        f"archive.json"
    )

    blob = bucket.blob(
        object_name
    )

    payload = json.dumps(
        catalog,
        indent=2,
        sort_keys=False,
    )

    blob.upload_from_string(
        payload,
        content_type=(
            "application/json"
        ),
    )

    print(
        f"ARCHIVE {model}: "
        f"{catalog['cycle_count']} cycles "
        f"published to "
        f"gs://{BUCKET_NAME}/"
        f"{object_name}"
    )

    return catalog


# ============================================================
# COMMAND LINE
# ============================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "models",
        nargs="+",
        help=(
            "Models whose archive catalogs "
            "should be rebuilt."
        ),
    )

    parser.add_argument(
        "--days",
        type=int,
        default=ARCHIVE_DAYS,
    )

    args = parser.parse_args()

    for model_name in args.models:

        publish_archive_catalog(
            model=model_name,
            archive_days=args.days,
        )
