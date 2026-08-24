from __future__ import annotations

import json
import shutil

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path
from urllib.parse import quote

from shared.models import (
    get_model_name,
)

from shared.runner import (
    OPERATIONAL_REGIONS,
    get_default_products_for_model,
    get_sequence_products_for_model,
)

from shared.storage import (
    get_bucket,
    get_bucket_name,
    get_local_root,
    upload_bytes,
)


# ============================================================
# SETTINGS
# ============================================================

METADATA_ROOT = "metadata"

PRODUCTS_ROOT = "products"

MANIFEST_VERSION = 1


# ============================================================
# UTC TIME
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    )


def utc_now_iso():

    return (
        utc_now()
        .replace(
            microsecond=0
        )
        .isoformat()
    )


# ============================================================
# CYCLE NORMALIZATION
# ============================================================

def normalize_cycle(
    cycle,
):
    """
    Normalize the backend cycle dictionary into stable publication
    metadata.

    Expected operational cycle dictionaries contain:

        id
        date
        hour
        datetime

    The helper tolerates a missing datetime field and constructs one
    from date/hour when possible.
    """

    if cycle is None:

        raise ValueError(
            "publish_cycle requires "
            "an exact cycle."
        )

    cycle_id = str(
        cycle[
            "id"
        ]
    )

    cycle_date = str(
        cycle[
            "date"
        ]
    )

    cycle_hour = int(
        cycle[
            "hour"
        ]
    )

    cycle_datetime = (
        cycle.get(
            "datetime"
        )
    )

    if cycle_datetime:

        try:

            parsed = (
                datetime.fromisoformat(
                    str(
                        cycle_datetime
                    )
                )
            )

            if parsed.tzinfo is None:

                parsed = (
                    parsed.replace(
                        tzinfo=timezone.utc
                    )
                )

            cycle_time_utc = (
                parsed
                .astimezone(
                    timezone.utc
                )
                .replace(
                    microsecond=0
                )
                .isoformat()
            )

        except Exception:

            cycle_time_utc = None

    else:

        cycle_time_utc = None

    if cycle_time_utc is None:

        try:

            parsed = (
                datetime.strptime(
                    (
                        f"{cycle_date}"
                        f"{cycle_hour:02d}"
                    ),
                    "%Y%m%d%H",
                )
                .replace(
                    tzinfo=timezone.utc
                )
            )

            cycle_time_utc = (
                parsed.isoformat()
            )

        except Exception:

            cycle_time_utc = None

    return {
        "id": cycle_id,
        "date": cycle_date,
        "hour": cycle_hour,
        "datetime_utc": (
            cycle_time_utc
        ),
    }


# ============================================================
# CLOUD PATHS
# ============================================================

def get_product_cycle_prefix(
    model,
    cycle_date,
    cycle_hour,
):

    return (
        f"{PRODUCTS_ROOT}/"
        f"{model}/"
        f"{cycle_date}/"
        f"{int(cycle_hour):02d}/"
    )


def get_cycle_metadata_prefix(
    model,
    cycle_id,
):

    return (
        f"{METADATA_ROOT}/"
        f"{model}/"
        f"{cycle_id}/"
    )


def get_cycle_manifest_object_name(
    model,
    cycle_id,
):

    return (
        get_cycle_metadata_prefix(
            model,
            cycle_id,
        )
        +
        "manifest.json"
    )


def get_cycle_ready_object_name(
    model,
    cycle_id,
):

    return (
        get_cycle_metadata_prefix(
            model,
            cycle_id,
        )
        +
        "READY.json"
    )


def get_cycle_manifest_alias_object_name(
    model,
    cycle_id,
):
    """
    Flat compatibility/discovery alias:

        metadata/ifs/20260810_00z.json

    This points to the same manifest content stored under the cycle
    metadata directory.
    """

    return (
        f"{METADATA_ROOT}/"
        f"{model}/"
        f"{cycle_id}.json"
    )


def get_latest_object_name(
    model,
):

    return (
        f"{METADATA_ROOT}/"
        f"{model}/"
        f"latest.json"
    )


def get_current_object_name(
    model,
):

    return (
        f"{METADATA_ROOT}/"
        f"{model}/"
        f"current.json"
    )


def get_cycle_progress_object_name(
    model,
    cycle_id,
):

    return (
        get_cycle_metadata_prefix(
            model,
            cycle_id,
        )
        +
        "progress.json"
    )


def build_cycle_id(
    cycle_date,
    cycle_hour,
):

    return (
        f"{str(cycle_date)}_"
        f"{int(cycle_hour):02d}z"
    )


# ============================================================
# PUBLIC HTTPS OBJECT URL
# ============================================================

def build_https_url(
    object_name,
):
    """
    Build the standard Cloud Storage HTTPS object URL.

    Whether anonymous browsers can read the object still depends on
    the bucket/IAM configuration.
    """

    encoded = quote(
        object_name,
        safe="/",
    )

    return (
        f"https://storage.googleapis.com/"
        f"{get_bucket_name()}/"
        f"{encoded}"
    )


# ============================================================
# JSON UPLOAD
# ============================================================

def upload_json(
    object_name,
    payload,
):

    data = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        .encode(
            "utf-8"
        )
    )

    return upload_bytes(
        data,
        object_name,
        content_type=(
            "application/json"
        ),
    )


# ============================================================
# PRODUCT INVENTORY FROM GCS
# ============================================================

def list_cycle_product_objects(
    model,
    cycle_date,
    cycle_hour,
):
    """
    List the PNG products that have already been streamed to GCS.

    Publication deliberately inventories GCS rather than local output
    directories. This makes publication compatible with the streaming
    runners, which delete local PNGs immediately after successful
    upload.
    """

    prefix = (
        get_product_cycle_prefix(
            model,
            cycle_date,
            cycle_hour,
        )
    )

    bucket = (
        get_bucket()
    )

    objects = []

    for blob in (
        bucket.list_blobs(
            prefix=prefix
        )
    ):

        name = (
            blob.name
        )

        if not name.lower().endswith(
            ".png"
        ):

            continue

        objects.append(
            {
                "name": name,
                "size": int(
                    blob.size
                    or
                    0
                ),
                "updated": (
                    blob.updated
                    .astimezone(
                        timezone.utc
                    )
                    .replace(
                        microsecond=0
                    )
                    .isoformat()
                    if blob.updated
                    is not None
                    else None
                ),
            }
        )

    objects.sort(
        key=lambda item: (
            item[
                "name"
            ]
        )
    )

    return objects


# ============================================================
# PARSE PRODUCT OBJECT
# ============================================================

def parse_product_object(
    *,
    model,
    cycle_date,
    cycle_hour,
    object_record,
):
    """
    Parse:

        products/model/YYYYMMDD/HH/product/region/f006.png

    into a website-friendly manifest record.
    """

    object_name = (
        object_record[
            "name"
        ]
    )

    prefix = (
        get_product_cycle_prefix(
            model,
            cycle_date,
            cycle_hour,
        )
    )

    if not object_name.startswith(
        prefix
    ):

        return None

    relative = (
        object_name[
            len(
                prefix
            ):
        ]
    )

    parts = (
        relative.split(
            "/"
        )
    )

    if len(
        parts
    ) != 3:

        return None

    product, region, filename = (
        parts
    )

    if not filename.lower().endswith(
        ".png"
    ):

        return None

    stem = (
        Path(
            filename
        )
        .stem
    )

    if not stem.startswith(
        "f"
    ):

        return None

    try:

        forecast_hour = int(
            stem[
                1:
            ]
        )

    except ValueError:

        return None

    return {
        "product": product,
        "region": region,
        "forecast_hour": (
            forecast_hour
        ),
        "object_name": (
            object_name
        ),
        "gs_uri": (
            f"gs://"
            f"{get_bucket_name()}/"
            f"{object_name}"
        ),
        "https_url": (
            build_https_url(
                object_name
            )
        ),
        "size_bytes": int(
            object_record.get(
                "size",
                0,
            )
        ),
        "updated_utc": (
            object_record.get(
                "updated"
            )
        ),
    }


# ============================================================
# BUILD MANIFEST
# ============================================================

def build_cycle_manifest(
    *,
    model,
    cycle,
    result,
):
    """
    Build a complete GCS-first cycle manifest.

    The manifest is generated only after the model runner reports zero
    failures and therefore represents a cycle that is eligible to
    become the model's latest cycle.
    """

    identity = (
        normalize_cycle(
            cycle
        )
    )

    model_name = (
        get_model_name(
            model
        )
    )

    object_records = (
        list_cycle_product_objects(
            model,
            identity[
                "date"
            ],
            identity[
                "hour"
            ],
        )
    )

    files = []

    for object_record in (
        object_records
    ):

        parsed = (
            parse_product_object(
                model=model,
                cycle_date=(
                    identity[
                        "date"
                    ]
                ),
                cycle_hour=(
                    identity[
                        "hour"
                    ]
                ),
                object_record=(
                    object_record
                ),
            )
        )

        if parsed is not None:

            files.append(
                parsed
            )

    if not files:

        raise RuntimeError(
            f"{model_name} "
            f"{identity['id']}: "
            f"no uploaded PNG products "
            f"were found in GCS."
        )

    forecast_hours = sorted(
        {
            int(
                item[
                    "forecast_hour"
                ]
            )
            for item in files
        }
    )

    products = sorted(
        {
            item[
                "product"
            ]
            for item in files
        }
    )

    regions = sorted(
        {
            item[
                "region"
            ]
            for item in files
        }
    )

    file_count_by_product = {}

    file_count_by_region = {}

    for item in files:

        product = (
            item[
                "product"
            ]
        )

        region = (
            item[
                "region"
            ]
        )

        file_count_by_product[
            product
        ] = (
            file_count_by_product.get(
                product,
                0,
            )
            +
            1
        )

        file_count_by_region[
            region
        ] = (
            file_count_by_region.get(
                region,
                0,
            )
            +
            1
        )

    expected_products = sorted(
        set(
            get_default_products_for_model(
                model
            )
            +
            get_sequence_products_for_model(
                model
            )
        )
    )

    expected_regions = list(
        OPERATIONAL_REGIONS
    )

    result_payload = (
        dict(
            result
        )
        if isinstance(
            result,
            dict,
        )
        else {}
    )

    manifest = {
        "manifest_version": (
            MANIFEST_VERSION
        ),

        "status": "ready",

        "model": model,

        "model_name": (
            model_name
        ),

        "cycle": (
            identity[
                "id"
            ]
        ),

        "cycle_date": (
            identity[
                "date"
            ]
        ),

        "cycle_hour": (
            identity[
                "hour"
            ]
        ),

        "cycle_time_utc": (
            identity[
                "datetime_utc"
            ]
        ),

        "published_at_utc": (
            utc_now_iso()
        ),

        "bucket": (
            get_bucket_name()
        ),

        "product_prefix": (
            get_product_cycle_prefix(
                model,
                identity[
                    "date"
                ],
                identity[
                    "hour"
                ],
            )
        ),

        "available_forecast_hours": (
            forecast_hours
        ),

        "first_forecast_hour": (
            forecast_hours[
                0
            ]
        ),

        "last_forecast_hour": (
            forecast_hours[
                -1
            ]
        ),

        "products": (
            products
        ),

        "regions": (
            regions
        ),

        "expected_products": (
            expected_products
        ),

        "expected_regions": (
            expected_regions
        ),

        "file_count": len(
            files
        ),

        "file_count_by_product": (
            file_count_by_product
        ),

        "file_count_by_region": (
            file_count_by_region
        ),

        "pipeline_result": (
            result_payload
        ),

        "files": (
            files
        ),
    }

    return manifest


# ============================================================
# PROGRESSIVE / IN-PROGRESS PUBLISHING
# ============================================================

def build_progress_manifest(
    *,
    model,
    cycle_date,
    cycle_hour,
):

    cycle_date = str(
        cycle_date
    )

    cycle_hour = int(
        cycle_hour
    )

    cycle_id = (
        build_cycle_id(
            cycle_date,
            cycle_hour,
        )
    )

    object_records = (
        list_cycle_product_objects(
            model,
            cycle_date,
            cycle_hour,
        )
    )

    files = []

    for object_record in (
        object_records
    ):

        parsed = (
            parse_product_object(
                model=model,
                cycle_date=(
                    cycle_date
                ),
                cycle_hour=(
                    cycle_hour
                ),
                object_record=(
                    object_record
                ),
            )
        )

        if parsed is not None:

            files.append(
                parsed
            )

    files.sort(
        key=lambda item: (
            int(
                item[
                    "forecast_hour"
                ]
            ),
            item[
                "product"
            ],
            item[
                "region"
            ],
        )
    )

    forecast_hours = sorted(
        {
            int(
                item[
                    "forecast_hour"
                ]
            )
            for item in files
        }
    )

    products = sorted(
        {
            item[
                "product"
            ]
            for item in files
        }
    )

    regions = sorted(
        {
            item[
                "region"
            ]
            for item in files
        }
    )

    return {
        "manifest_version": (
            MANIFEST_VERSION
        ),

        "status": "running",

        "model": model,

        "model_name": (
            get_model_name(
                model
            )
        ),

        "cycle": (
            cycle_id
        ),

        "cycle_date": (
            cycle_date
        ),

        "cycle_hour": (
            cycle_hour
        ),

        "updated_at_utc": (
            utc_now_iso()
        ),

        "bucket": (
            get_bucket_name()
        ),

        "product_prefix": (
            get_product_cycle_prefix(
                model,
                cycle_date,
                cycle_hour,
            )
        ),

        "available_forecast_hours": (
            forecast_hours
        ),

        "forecast_hours_completed": (
            len(
                forecast_hours
            )
        ),

        "first_forecast_hour": (
            forecast_hours[
                0
            ]
            if forecast_hours
            else None
        ),

        "last_forecast_hour": (
            forecast_hours[
                -1
            ]
            if forecast_hours
            else None
        ),

        "products": (
            products
        ),

        "regions": (
            regions
        ),

        "file_count": (
            len(
                files
            )
        ),

        "files": (
            files
        ),
    }


def publish_forecast_hour_progress(
    *,
    model,
    cycle_date,
    cycle_hour,
    forecast_hour,
    expected_products=None,
    expected_regions=None,
):
    """
    Publish the model cycle while it is still running.

    This is called only AFTER one forecast hour has successfully
    uploaded its PNG files to GCS.

    Publication order:

        progress.json
        current.json   <-- written last

    The website reads current.json first, which lets newly completed
    forecast hours become clickable immediately instead of waiting for
    the entire model cycle.
    """

    cycle_date = str(
        cycle_date
    )

    cycle_hour = int(
        cycle_hour
    )

    forecast_hour = int(
        forecast_hour
    )

    # Operational cycles use YYYYMMDD. Do not create a permanent
    # "latest_00z" metadata tree for manual latest-mode tests.
    if (
        len(
            cycle_date
        )
        != 8
        or
        not cycle_date.isdigit()
    ):

        return {
            "published": False,
            "reason": (
                "non-operational cycle date"
            ),
        }

    cycle_id = (
        build_cycle_id(
            cycle_date,
            cycle_hour,
        )
    )

    progress = (
        build_progress_manifest(
            model=model,
            cycle_date=(
                cycle_date
            ),
            cycle_hour=(
                cycle_hour
            ),
        )
    )

    if (
        forecast_hour
        not in progress[
            "available_forecast_hours"
        ]
    ):

        raise RuntimeError(
            f"{model.upper()} "
            f"{cycle_id}: "
            f"f{forecast_hour:03d} "
            f"was uploaded but is missing "
            f"from the GCS inventory."
        )

    # ========================================================
    # EXACT EXPECTED FRAME INVENTORY VALIDATION
    #
    # "available" means at least one frame exists.
    # "complete" means every expected product/region frame for
    # this forecast hour exists in the GCS inventory.
    # ========================================================

    if (
        expected_products is not None
        and
        expected_regions is not None
    ):

        expected_products = list(
            dict.fromkeys(
                str(product)
                for product in expected_products
            )
        )

        expected_regions = list(
            dict.fromkeys(
                str(region)
                for region in expected_regions
            )
        )

        expected_pairs = {
            (
                product,
                region,
            )
            for product in expected_products
            for region in expected_regions
        }

        actual_pairs = set()

        for file_record in progress.get(
            "files",
            [],
        ):

            try:

                file_hour = int(
                    file_record.get(
                        "forecast_hour"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            if file_hour != forecast_hour:
                continue

            product = file_record.get(
                "product"
            )

            region = file_record.get(
                "region"
            )

            if (
                product is None
                or
                region is None
            ):
                continue

            actual_pairs.add(
                (
                    str(product),
                    str(region),
                )
            )

        missing_pairs = sorted(
            expected_pairs
            -
            actual_pairs
        )

        present_count = len(
            expected_pairs
            &
            actual_pairs
        )

        expected_count = len(
            expected_pairs
        )

        if missing_pairs:

            print(
                f"{model.upper()} "
                f"{cycle_id}: "
                f"f{forecast_hour:03d} "
                f"PARTIAL — "
                f"{present_count}/"
                f"{expected_count} "
                f"expected frames present; "
                f"missing="
                f"{len(missing_pairs)}"
            )

            print(
                "First missing frames: "
                +
                ", ".join(
                    f"{product}/{region}"
                    for product, region
                    in missing_pairs[:10]
                )
            )

            return {
                "published": False,
                "reason": (
                    "forecast-hour inventory incomplete"
                ),
                "cycle": cycle_id,
                "forecast_hour": forecast_hour,
                "expected_count": (
                    expected_count
                ),
                "present_count": (
                    present_count
                ),
                "missing_count": (
                    len(missing_pairs)
                ),
                "missing": [
                    {
                        "product": product,
                        "region": region,
                    }
                    for product, region
                    in missing_pairs
                ],
            }

        print(
            f"{model.upper()} "
            f"{cycle_id}: "
            f"f{forecast_hour:03d} "
            f"inventory verified "
            f"{present_count}/"
            f"{expected_count}"
        )

    progress_object = (
        get_cycle_progress_object_name(
            model,
            cycle_id,
        )
    )

    current_object = (
        get_current_object_name(
            model
        )
    )

    # --------------------------------------------------------
    # 1. UPDATE CYCLE PROGRESS INVENTORY
    # --------------------------------------------------------

    upload_json(
        progress_object,
        progress,
    )

    # --------------------------------------------------------
    # 2. ADVANCE CURRENT POINTER LAST
    # --------------------------------------------------------

    current_payload = {
        "manifest_version": (
            MANIFEST_VERSION
        ),

        "status": "running",

        "model": model,

        "model_name": (
            progress[
                "model_name"
            ]
        ),

        "cycle": (
            cycle_id
        ),

        "cycle_date": (
            cycle_date
        ),

        "cycle_hour": (
            cycle_hour
        ),

        "updated_at_utc": (
            progress[
                "updated_at_utc"
            ]
        ),

        # Keep the same pointer field used by latest.json so the
        # frontend does not need a second manifest schema.
        "manifest_object": (
            progress_object
        ),

        "manifest_url": (
            build_https_url(
                progress_object
            )
        ),

        "progress_object": (
            progress_object
        ),

        "progress_url": (
            build_https_url(
                progress_object
            )
        ),

        "product_prefix": (
            progress[
                "product_prefix"
            ]
        ),

        "available_forecast_hours": (
            progress[
                "available_forecast_hours"
            ]
        ),

        "forecast_hours_completed": (
            progress[
                "forecast_hours_completed"
            ]
        ),

        "products": (
            progress[
                "products"
            ]
        ),

        "regions": (
            progress[
                "regions"
            ]
        ),

        "file_count": (
            progress[
                "file_count"
            ]
        ),
    }

    upload_json(
        current_object,
        current_payload,
    )

    print(
        f"{model.upper()} "
        f"{cycle_id}: "
        f"progress published through "
        f"f{forecast_hour:03d} "
        f"("
        f"{progress['forecast_hours_completed']} "
        f"hours available"
        f")"
    )

    return {
        "published": True,
        "cycle": (
            cycle_id
        ),
        "forecast_hour": (
            forecast_hour
        ),
        "progress": (
            progress_object
        ),
        "current": (
            current_object
        ),
        "forecast_hours_completed": (
            progress[
                "forecast_hours_completed"
            ]
        ),
        "file_count": (
            progress[
                "file_count"
            ]
        ),
    }


# ============================================================
# READY MARKER
# ============================================================

def build_ready_payload(
    *,
    model,
    identity,
    manifest_object,
    manifest,
):

    return {
        "status": "ready",

        "model": model,

        "cycle": (
            identity[
                "id"
            ]
        ),

        "cycle_date": (
            identity[
                "date"
            ]
        ),

        "cycle_hour": (
            identity[
                "hour"
            ]
        ),

        "cycle_time_utc": (
            identity[
                "datetime_utc"
            ]
        ),

        "published_at_utc": (
            manifest[
                "published_at_utc"
            ]
        ),

        "file_count": (
            manifest[
                "file_count"
            ]
        ),

        "manifest_object": (
            manifest_object
        ),

        "manifest_url": (
            build_https_url(
                manifest_object
            )
        ),
    }


# ============================================================
# LATEST POINTER
# ============================================================

def build_latest_payload(
    *,
    model,
    identity,
    manifest,
    manifest_object,
    ready_object,
):

    return {
        "manifest_version": (
            MANIFEST_VERSION
        ),

        "status": "ready",

        "model": model,

        "model_name": (
            get_model_name(
                model
            )
        ),

        "cycle": (
            identity[
                "id"
            ]
        ),

        "cycle_date": (
            identity[
                "date"
            ]
        ),

        "cycle_hour": (
            identity[
                "hour"
            ]
        ),

        "cycle_time_utc": (
            identity[
                "datetime_utc"
            ]
        ),

        "published_at_utc": (
            manifest[
                "published_at_utc"
            ]
        ),

        "manifest_object": (
            manifest_object
        ),

        "manifest_url": (
            build_https_url(
                manifest_object
            )
        ),

        "ready_object": (
            ready_object
        ),

        "ready_url": (
            build_https_url(
                ready_object
            )
        ),

        "product_prefix": (
            manifest[
                "product_prefix"
            ]
        ),

        "available_forecast_hours": (
            manifest[
                "available_forecast_hours"
            ]
        ),

        "products": (
            manifest[
                "products"
            ]
        ),

        "regions": (
            manifest[
                "regions"
            ]
        ),

        "file_count": (
            manifest[
                "file_count"
            ]
        ),
    }


# ============================================================
# PUBLISH COMPLETE CYCLE
# ============================================================

def publish_cycle(
    *,
    model,
    cycle,
    result,
):
    """
    Publish metadata for an already-uploaded streaming model cycle.

    Publication order is deliberate:

        1. Inventory the PNGs already in GCS.
        2. Write the immutable cycle manifest.
        3. Write the flat cycle-manifest alias.
        4. Write READY.json for the cycle.
        5. Write model latest.json LAST.

    Therefore the website never advances to a cycle whose cycle
    manifest/READY marker has not already been written.
    """

    identity = (
        normalize_cycle(
            cycle
        )
    )

    model_name = (
        get_model_name(
            model
        )
    )

    print()
    print("=" * 70)

    print(
        f"PUBLISHING "
        f"{model_name} "
        f"{identity['id']}"
    )

    print("=" * 70)

    manifest = (
        build_cycle_manifest(
            model=model,
            cycle=cycle,
            result=result,
        )
    )

    manifest_object = (
        get_cycle_manifest_object_name(
            model,
            identity[
                "id"
            ],
        )
    )

    manifest_alias_object = (
        get_cycle_manifest_alias_object_name(
            model,
            identity[
                "id"
            ],
        )
    )

    ready_object = (
        get_cycle_ready_object_name(
            model,
            identity[
                "id"
            ],
        )
    )

    latest_object = (
        get_latest_object_name(
            model
        )
    )

    current_object = (
        get_current_object_name(
            model
        )
    )

    # --------------------------------------------------------
    # 1. IMMUTABLE CYCLE MANIFEST
    # --------------------------------------------------------

    upload_json(
        manifest_object,
        manifest,
    )

    # --------------------------------------------------------
    # 2. FLAT CYCLE ALIAS
    # --------------------------------------------------------

    upload_json(
        manifest_alias_object,
        manifest,
    )

    # --------------------------------------------------------
    # 3. READY MARKER
    # --------------------------------------------------------

    ready_payload = (
        build_ready_payload(
            model=model,
            identity=identity,
            manifest_object=(
                manifest_object
            ),
            manifest=manifest,
        )
    )

    upload_json(
        ready_object,
        ready_payload,
    )

    # --------------------------------------------------------
    # 4. LATEST POINTER - ALWAYS LAST
    # --------------------------------------------------------

    latest_payload = (
        build_latest_payload(
            model=model,
            identity=identity,
            manifest=manifest,
            manifest_object=(
                manifest_object
            ),
            ready_object=(
                ready_object
            ),
        )
    )

    upload_json(
        latest_object,
        latest_payload,
    )

    # --------------------------------------------------------
    # 5. CURRENT POINTER NOW REFERENCES THE COMPLETE MANIFEST
    # --------------------------------------------------------

    current_payload = dict(
        latest_payload
    )

    current_payload[
        "status"
    ] = "complete"

    current_payload[
        "updated_at_utc"
    ] = utc_now_iso()

    upload_json(
        current_object,
        current_payload,
    )

    print(
        f"Manifest: "
        f"gs://{get_bucket_name()}/"
        f"{manifest_object}"
    )

    print(
        f"READY: "
        f"gs://{get_bucket_name()}/"
        f"{ready_object}"
    )

    print(
        f"Latest: "
        f"gs://{get_bucket_name()}/"
        f"{latest_object}"
    )

    print(
        f"Files indexed: "
        f"{manifest['file_count']}"
    )

    print("=" * 70)

    return {
        "manifest": (
            manifest_object
        ),
        "manifest_alias": (
            manifest_alias_object
        ),
        "ready": (
            ready_object
        ),
        "latest": (
            latest_object
        ),
        "current": (
            current_object
        ),
        "file_count": (
            manifest[
                "file_count"
            ]
        ),
    }


# ============================================================
# LOCAL STREAMING CLEANUP
# ============================================================

def _remove_tree_if_present(
    path,
):

    path = Path(
        path
    )

    if not path.exists():

        return False

    try:

        shutil.rmtree(
            path
        )

        return True

    except OSError:

        return False


def cleanup_model(
    model,
    *,
    retain=3,
):
    """
    Cleanup compatibility function used by run_backend.py.

    Persistent product retention is intentionally NOT performed here
    yet. Products now live in GCS, and deleting old cloud cycles is a
    separate policy decision.

    This function only cleans stale temporary/local streaming folders
    that may survive interrupted runs. It preserves the backend's
    existing return structure:

        removed_data
        removed_output
    """

    del retain

    local_root = (
        get_local_root()
    )

    removed_data = []

    removed_output = []

    model_data_root = (
        local_root
        /
        model
    )

    model_output_root = (
        local_root
        /
        "output"
        /
        model
    )

    # Streaming runners normally remove hour files immediately.
    # Only remove model roots when they are already empty.
    for root, removed in (
        (
            model_data_root,
            removed_data,
        ),
        (
            model_output_root,
            removed_output,
        ),
    ):

        if not root.exists():

            continue

        try:

            # Remove empty descendant directories first.
            directories = sorted(
                (
                    path
                    for path
                    in root.rglob(
                        "*"
                    )
                    if path.is_dir()
                ),
                key=lambda path: (
                    len(
                        path.parts
                    )
                ),
                reverse=True,
            )

            for directory in (
                directories
            ):

                try:

                    directory.rmdir()

                except OSError:

                    pass

            root.rmdir()

            removed.append(
                str(
                    root
                )
            )

        except OSError:

            # Non-empty directories are deliberately preserved.
            pass

    return {
        "removed_data": (
            removed_data
        ),
        "removed_output": (
            removed_output
        ),
    }