from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import BinaryIO

from google.cloud import storage


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_LOCAL_ROOT = Path(
    "/tmp/massachusettswx"
)

DEFAULT_BUCKET = (
    "massachusettswx-nwp-project"
)

DEFAULT_MIN_FREE_DISK_GB = 3.0


# ============================================================
# LOCAL ROOT
# ============================================================

def get_local_root() -> Path:
    """
    Return the temporary local workspace root.

    Large model GRIB files and transient rendered PNGs should live
    here instead of in the persistent Cloud Shell home partition.
    """

    configured = os.getenv(
        "WEATHER_LOCAL_ROOT"
    )

    if configured:

        return (
            Path(
                configured
            )
            .expanduser()
            .resolve()
        )

    return DEFAULT_LOCAL_ROOT


def get_bucket_name() -> str:
    """
    Return the configured Google Cloud Storage bucket name.
    """

    return os.getenv(
        "WEATHER_STORAGE_BUCKET",
        DEFAULT_BUCKET,
    )


# ============================================================
# GOOGLE CLOUD STORAGE CLIENT
# ============================================================

_storage_client: storage.Client | None = None


def get_storage_client() -> storage.Client:
    """
    Return a reusable Google Cloud Storage client.
    """

    global _storage_client

    if _storage_client is None:

        _storage_client = (
            storage.Client()
        )

    return _storage_client


def get_bucket():
    """
    Return the configured Cloud Storage bucket.
    """

    return (
        get_storage_client()
        .bucket(
            get_bucket_name()
        )
    )


# ============================================================
# TEMPORARY LOCAL PATHS
# ============================================================

def build_local_forecast_path(
    model: str,
    cycle_date: str,
    cycle_hour: int,
    forecast_hour: int,
    extension: str = "grib2",
) -> Path:
    """
    Build a canonical temporary raw forecast path.

    Example:

        /tmp/massachusettswx/
            ifs/
                20260809/
                    12/
                        f006.grib2
    """

    model = (
        model
        .lower()
        .strip()
    )

    extension = (
        extension
        .lstrip(".")
    )

    return (
        get_local_root()
        / model
        / str(
            cycle_date
        )
        / f"{int(cycle_hour):02d}"
        / (
            f"f"
            f"{int(forecast_hour):03d}."
            f"{extension}"
        )
    )


def build_local_output_cycle_dir(
    model: str,
    cycle_date: str,
    cycle_hour: int,
) -> Path:
    """
    Return the temporary rendered-output directory for one cycle.
    """

    return (
        get_local_root()
        / "output"
        / model.lower().strip()
        / str(
            cycle_date
        )
        / f"{int(cycle_hour):02d}"
    )


def ensure_parent_directory(
    path: Path,
) -> None:
    """
    Ensure a path's parent directory exists.
    """

    Path(
        path
    ).parent.mkdir(
        parents=True,
        exist_ok=True,
    )


def local_exists(
    path: Path,
) -> bool:
    """
    Return True when a local file exists.
    """

    return (
        Path(
            path
        ).exists()
    )


def local_file_size(
    path: Path,
) -> int | None:
    """
    Return local file size in bytes.
    """

    try:

        return (
            Path(
                path
            )
            .stat()
            .st_size
        )

    except FileNotFoundError:

        return None


def open_local_for_read(
    path: Path,
) -> BinaryIO:
    """
    Open a local file for binary reading.
    """

    return (
        Path(
            path
        ).open(
            "rb"
        )
    )


def open_local_for_write(
    path: Path,
) -> BinaryIO:
    """
    Open a local file for binary writing.
    """

    path = Path(
        path
    )

    ensure_parent_directory(
        path
    )

    return path.open(
        "wb"
    )


def delete_local(
    path: Path,
    missing_ok: bool = True,
) -> None:
    """
    Delete a local file.
    """

    Path(
        path
    ).unlink(
        missing_ok=missing_ok
    )


# ============================================================
# DISK SAFETY
# ============================================================

def get_working_disk_free_gb() -> float:
    """
    Return free space on the filesystem containing the temp root.
    """

    root = (
        get_local_root()
    )

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    usage = (
        shutil.disk_usage(
            root
        )
    )

    return (
        usage.free
        /
        1024
        /
        1024
        /
        1024
    )


def check_working_disk_space(
    minimum_free_gb: float = (
        DEFAULT_MIN_FREE_DISK_GB
    ),
) -> float:
    """
    Raise before a model run can consume the final working disk space.

    Returns the current free space in GB when the check passes.
    """

    free_gb = (
        get_working_disk_free_gb()
    )

    print(
        f"Working disk free: "
        f"{free_gb:.2f} GB"
    )

    if (
        free_gb
        <
        float(
            minimum_free_gb
        )
    ):

        raise RuntimeError(
            f"Pipeline stopped: "
            f"only {free_gb:.2f} GB "
            f"of working disk remains; "
            f"minimum is "
            f"{float(minimum_free_gb):.2f} GB."
        )

    return free_gb


# ============================================================
# EMPTY-DIRECTORY CLEANUP
# ============================================================

def remove_empty_directories(
    root: Path | str,
) -> None:
    """
    Remove empty descendant directories and then the root if empty.
    """

    root = Path(
        root
    )

    if not root.exists():

        return

    directories = sorted(
        (
            path
            for path
            in root.rglob(
                "*"
            )
            if path.is_dir()
        ),
        key=lambda path: len(
            path.parts
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

    try:

        root.rmdir()

    except OSError:

        pass


# ============================================================
# CLOUD OBJECT NAMING
# ============================================================

def build_product_object_name(
    model: str,
    cycle_date: str,
    cycle_hour: int,
    product: str,
    region: str,
    forecast_hour: int,
    extension: str = "png",
) -> str:
    """
    Build the canonical Cloud Storage path for a rendered product.

    Example:

        products/ifs/20260809/12/h5_vort/northeast/f006.png
    """

    model = (
        model
        .lower()
        .strip()
    )

    product = (
        product
        .lower()
        .strip()
    )

    region = (
        region
        .lower()
        .strip()
    )

    extension = (
        extension
        .lstrip(".")
    )

    return (
        f"products/{model}/"
        f"{cycle_date}/"
        f"{int(cycle_hour):02d}/"
        f"{product}/"
        f"{region}/"
        f"f{int(forecast_hour):03d}."
        f"{extension}"
    )


def build_metadata_object_name(
    model: str,
    filename: str,
) -> str:
    """
    Build a Cloud Storage path for model metadata.
    """

    model = (
        model
        .lower()
        .strip()
    )

    filename = (
        filename
        .lstrip("/")
    )

    return (
        f"metadata/"
        f"{model}/"
        f"{filename}"
    )


# ============================================================
# CLOUD STORAGE OPERATIONS
# ============================================================

def cloud_exists(
    object_name: str,
) -> bool:
    """
    Return True if an object exists in Cloud Storage.
    """

    blob = (
        get_bucket()
        .blob(
            object_name
        )
    )

    return blob.exists()


def upload_file(
    local_path: Path | str,
    object_name: str,
    content_type: str | None = None,
) -> str:
    """
    Upload a local file and return its gs:// URI.
    """

    local_path = Path(
        local_path
    )

    if not local_path.exists():

        raise FileNotFoundError(
            local_path
        )

    blob = (
        get_bucket()
        .blob(
            object_name
        )
    )

    blob.upload_from_filename(
        str(
            local_path
        ),
        content_type=(
            content_type
        ),
    )

    return (
        f"gs://"
        f"{get_bucket_name()}/"
        f"{object_name}"
    )


def upload_bytes(
    data: bytes,
    object_name: str,
    content_type: str | None = None,
) -> str:
    """
    Upload bytes directly to Cloud Storage.
    """

    blob = (
        get_bucket()
        .blob(
            object_name
        )
    )

    blob.upload_from_string(
        data,
        content_type=(
            content_type
        ),
    )

    return (
        f"gs://"
        f"{get_bucket_name()}/"
        f"{object_name}"
    )


def download_file(
    object_name: str,
    local_path: Path | str,
) -> Path:
    """
    Download an object from Cloud Storage.
    """

    local_path = Path(
        local_path
    )

    ensure_parent_directory(
        local_path
    )

    blob = (
        get_bucket()
        .blob(
            object_name
        )
    )

    blob.download_to_filename(
        str(
            local_path
        )
    )

    return local_path


def delete_cloud(
    object_name: str,
) -> None:
    """
    Delete an object from Cloud Storage.
    """

    blob = (
        get_bucket()
        .blob(
            object_name
        )
    )

    blob.delete()


# ============================================================
# PRODUCT CONVENIENCE FUNCTIONS
# ============================================================

def upload_product(
    local_path: Path | str,
    model: str,
    cycle_date: str,
    cycle_hour: int,
    product: str,
    region: str,
    forecast_hour: int,
) -> str:
    """
    Upload a rendered PNG using the canonical bucket layout.
    """

    object_name = (
        build_product_object_name(
            model=model,
            cycle_date=(
                cycle_date
            ),
            cycle_hour=(
                cycle_hour
            ),
            product=product,
            region=region,
            forecast_hour=(
                forecast_hour
            ),
            extension="png",
        )
    )

    return upload_file(
        local_path=(
            local_path
        ),
        object_name=(
            object_name
        ),
        content_type="image/png",
    )


def product_exists(
    model: str,
    cycle_date: str,
    cycle_hour: int,
    product: str,
    region: str,
    forecast_hour: int,
) -> bool:
    """
    Return True if a rendered product already exists in GCS.
    """

    object_name = (
        build_product_object_name(
            model=model,
            cycle_date=(
                cycle_date
            ),
            cycle_hour=(
                cycle_hour
            ),
            product=product,
            region=region,
            forecast_hour=(
                forecast_hour
            ),
            extension="png",
        )
    )

    return cloud_exists(
        object_name
    )



# ============================================================
# INDIVIDUAL FRAME STREAMING
# ============================================================

def _infer_cycle_identity_from_output_dir(
    *,
    model: str,
    cycle_output_dir: Path | str,
) -> tuple[str, int] | None:
    """
    Infer YYYYMMDD / HH from the canonical temporary output layout:

        .../output/<model>/YYYYMMDD/HH/

    Returns None for non-operational/manual output directories.
    """

    model = (
        str(model)
        .lower()
        .strip()
    )

    path = (
        Path(
            cycle_output_dir
        )
        .expanduser()
        .resolve()
    )

    parts = (
        path.parts
    )

    for index in range(
        len(parts) - 3
    ):

        if (
            parts[index]
            != "output"
        ):

            continue

        if (
            parts[
                index + 1
            ]
            != model
        ):

            continue

        cycle_date = (
            parts[
                index + 2
            ]
        )

        cycle_hour_text = (
            parts[
                index + 3
            ]
        )

        if (
            len(cycle_date)
            != 8
            or
            not cycle_date.isdigit()
        ):

            return None

        if (
            not cycle_hour_text.isdigit()
        ):

            return None

        cycle_hour = int(
            cycle_hour_text
        )

        if (
            cycle_hour
            not in (
                0,
                6,
                12,
                18,
            )
        ):

            return None

        return (
            cycle_date,
            cycle_hour,
        )

    return None


def upload_rendered_frame(
    *,
    local_path: Path | str,
    model: str,
    product: str,
    region: str,
    forecast_hour: int,
    cycle_output_dir: Path | str,
    delete_after_upload: bool = True,
    publish_progress: bool = True,
) -> dict:
    """
    Upload ONE rendered PNG immediately after it is created.

    This is the fast-path used by shared.runner. It avoids waiting for
    every product and region in an entire forecast hour to finish.

    If cycle_output_dir does not look like an operational
    .../output/model/YYYYMMDD/HH directory, streaming is skipped and the
    local PNG is left in place for normal/manual workflows.

    On successful upload the local PNG may be deleted immediately.
    Metadata publication is coalesced by shared.publish so parallel
    product workers do not rewrite current.json for every single PNG.
    """

    local_path = Path(
        local_path
    )

    identity = (
        _infer_cycle_identity_from_output_dir(
            model=model,
            cycle_output_dir=(
                cycle_output_dir
            ),
        )
    )

    result = {
        "streamed": False,
        "uploaded": False,
        "removed": False,
        "progress_published": False,
        "skipped": False,
        "error": None,
    }

    if identity is None:

        result[
            "skipped"
        ] = True

        return result

    cycle_date, cycle_hour = (
        identity
    )

    if (
        not local_path.exists()
    ):

        result[
            "error"
        ] = (
            f"Rendered frame does not exist: "
            f"{local_path}"
        )

        return result

    try:

        upload_product(
            local_path=(
                local_path
            ),
            model=model,
            cycle_date=(
                cycle_date
            ),
            cycle_hour=(
                cycle_hour
            ),
            product=product,
            region=region,
            forecast_hour=(
                forecast_hour
            ),
        )

        result[
            "uploaded"
        ] = True

        result[
            "streamed"
        ] = True

        print(
            f"STREAMED "
            f"{str(model).upper()} "
            f"{product}/"
            f"{region}/"
            f"f{int(forecast_hour):03d}"
        )

        if delete_after_upload:

            local_path.unlink(
                missing_ok=True
            )

            result[
                "removed"
            ] = True

        if publish_progress:

            try:

                from shared.publish import (
                    publish_frame_progress,
                )

                publish_result = (
                    publish_frame_progress(
                        model=model,
                        cycle_date=(
                            cycle_date
                        ),
                        cycle_hour=(
                            cycle_hour
                        ),
                        forecast_hour=(
                            forecast_hour
                        ),
                    )
                )

                result[
                    "progress_published"
                ] = bool(
                    publish_result.get(
                        "published",
                        False,
                    )
                )

            except Exception as error:

                print(
                    f"{str(model).upper()} "
                    f"{product}/"
                    f"{region}/"
                    f"f{int(forecast_hour):03d}: "
                    f"FRAME PROGRESS PUBLISH FAILED: "
                    f"{error}"
                )

        return result

    except Exception as error:

        result[
            "error"
        ] = str(
            error
        )

        print(
            f"FRAME STREAM FAILED "
            f"{local_path}: "
            f"{error}"
        )

        return result


# ============================================================
# FORECAST-HOUR OUTPUT UPLOAD
# ============================================================

def upload_forecast_hour_outputs(
    *,
    model: str,
    cycle_date: str,
    cycle_hour: int,
    forecast_hour: int,
    cycle_output_dir: Path | str,
    delete_after_upload: bool = True,
    expected_products=None,
    expected_regions=None,
) -> dict:
    """
    Upload all PNGs produced for one forecast hour.

    Expected local layout beneath cycle_output_dir:

        product/
            region/
                model_product_region_f006.png

    A local PNG is deleted ONLY after its upload succeeds.
    Failed uploads remain on disk for recovery/debugging.
    """

    cycle_output_dir = Path(
        cycle_output_dir
    )

    forecast_tag = (
        f"f"
        f"{int(forecast_hour):03d}"
    )

    png_files = sorted(
        cycle_output_dir.rglob(
            f"*{forecast_tag}.png"
        )
    )

    result = {
        "found": len(
            png_files
        ),
        "uploaded": 0,
        "failed": 0,
        "removed": 0,
        "progress_published": False,
        "progress_publish_failed": 0,
    }

    if not png_files:

        print(
            f"{model.upper()} "
            f"{forecast_tag}: "
            f"no local PNGs remain; "
            f"frames may already have streamed"
        )

        # ----------------------------------------------------
        # END-OF-HOUR COMPLETION
        #
        # Fast frame streaming uploads and deletes PNGs as soon
        # as they are rendered. Therefore zero local PNGs here is
        # normal and must NOT prevent the forecast hour from being
        # marked complete.
        #
        # publish_forecast_hour_progress() verifies that the hour
        # actually exists in the GCS inventory before marking it.
        # ----------------------------------------------------

        try:

            from shared.publish import (
                publish_forecast_hour_progress,
            )

            progress_result = (
                publish_forecast_hour_progress(
                    model=model,
                    cycle_date=(
                        cycle_date
                    ),
                    cycle_hour=(
                        cycle_hour
                    ),
                    forecast_hour=(
                        forecast_hour
                    ),
                    expected_products=(
                        expected_products
                    ),
                    expected_regions=(
                        expected_regions
                    ),
                )
            )

            result[
                "progress_published"
            ] = bool(
                progress_result.get(
                    "published",
                    False,
                )
            )

        except Exception as error:

            result[
                "progress_publish_failed"
            ] += 1

            print(
                f"{model.upper()} "
                f"{forecast_tag}: "
                f"END-OF-HOUR PROGRESS "
                f"PUBLISH FAILED: "
                f"{error}"
            )

        return result

    print()
    print(
        f"{model.upper()} "
        f"{forecast_tag}: "
        f"uploading "
        f"{len(png_files)} "
        f"PNG files..."
    )

    for local_path in (
        png_files
    ):

        try:

            relative = (
                local_path.relative_to(
                    cycle_output_dir
                )
            )

            parts = (
                relative.parts
            )

            if len(
                parts
            ) < 3:

                raise RuntimeError(
                    f"Unexpected output path: "
                    f"{relative}"
                )

            product = (
                parts[
                    0
                ]
            )

            region = (
                parts[
                    1
                ]
            )

            upload_product(
                local_path=(
                    local_path
                ),
                model=model,
                cycle_date=(
                    cycle_date
                ),
                cycle_hour=(
                    cycle_hour
                ),
                product=product,
                region=region,
                forecast_hour=(
                    forecast_hour
                ),
            )

            result[
                "uploaded"
            ] += 1

            if delete_after_upload:

                local_path.unlink(
                    missing_ok=True
                )

                result[
                    "removed"
                ] += 1

        except Exception as error:

            result[
                "failed"
            ] += 1

            print(
                f"UPLOAD FAILED "
                f"{local_path}: "
                f"{error}"
            )

    remove_empty_directories(
        cycle_output_dir
    )

    # ========================================================
    # PROGRESSIVE PUBLISHING
    #
    # Import locally to avoid a module-level circular import:
    # shared.publish uses shared.storage for GCS operations.
    # ========================================================

    if (
        result[
            "failed"
        ]
        == 0
        and
        result[
            "uploaded"
        ]
        > 0
    ):

        try:

            from shared.publish import (
                publish_forecast_hour_progress,
            )

            progress_result = (
                publish_forecast_hour_progress(
                    model=model,
                    cycle_date=(
                        cycle_date
                    ),
                    cycle_hour=(
                        cycle_hour
                    ),
                    forecast_hour=(
                        forecast_hour
                    ),
                    expected_products=(
                        expected_products
                    ),
                    expected_regions=(
                        expected_regions
                    ),
                )
            )

            result[
                "progress_published"
            ] = bool(
                progress_result.get(
                    "published",
                    False,
                )
            )

        except Exception as error:

            result[
                "progress_publish_failed"
            ] += 1

            print(
                f"{model.upper()} "
                f"{forecast_tag}: "
                f"PROGRESS PUBLISH FAILED: "
                f"{error}"
            )

    print(
        f"{model.upper()} "
        f"{forecast_tag} upload: "
        f"uploaded="
        f"{result['uploaded']}, "
        f"failed="
        f"{result['failed']}, "
        f"local_removed="
        f"{result['removed']}"
    )

    return result