"""Read only the non-Requester-Pays statistics bucket, using explicit identity."""
import json
import os
import re
from pathlib import Path

BUCKET = "weathernext3_statistics_spatial"
PREFIX = f"{BUCKET}/weathernext_3_0_0_statistics/zarr/2026_to_present"
RUN_PATTERN = re.compile(r"\d{8}_(00|06|12|18)hr_\d+_preds$")


def validate_source(path):
    path = path.removeprefix("gs://").rstrip("/")
    if not path.startswith(PREFIX + "/") or not path.endswith("/predictions.zarr"):
        raise ValueError("Only the operational WN3 statistics bucket is permitted.")
    relative = path[len(PREFIX) + 1:]
    if len(relative.split("/")) != 2 or not RUN_PATTERN.fullmatch(relative.split("/")[0]):
        raise ValueError("Choose a 00/06/12/18 UTC statistics forecast run.")
    return path


def connect():
    import gcsfs
    from google.oauth2.credentials import Credentials

    # Never auto-discover a billing project, service account, or cloud VM identity.
    token = os.environ.get("WN3_ACCESS_TOKEN")
    credential_file = os.environ.get("WN3_CREDENTIALS_FILE")
    if token:
        credentials = Credentials(token=token)
    elif credential_file:
        info = json.loads(Path(credential_file).expanduser().read_text())
        if info.get("type") != "authorized_user":
            raise ValueError("Use credentials for your approved Google user account.")
        info.pop("quota_project_id", None)
        credentials = Credentials.from_authorized_user_info(info)
    else:
        raise ValueError("Set WN3_ACCESS_TOKEN or WN3_CREDENTIALS_FILE for your approved account.")
    credentials = credentials.with_quota_project(None)
    return gcsfs.GCSFileSystem(
        token=credentials, project="", requester_pays=False,
        access="read_only", skip_instance_cache=True,
    )


def latest_source(fs):
    # One nonrecursive directory listing. No global ensemble or archival scan.
    entries = fs.ls(PREFIX, detail=False)
    candidates = sorted(
        (p.rstrip("/") for p in entries
         if RUN_PATTERN.fullmatch(p.rstrip("/").rsplit("/", 1)[-1])),
        reverse=True,
    )
    for candidate in candidates[:8]:
        path = validate_source(candidate + "/predictions.zarr")
        if fs.exists(path + "/zarr.json"):
            return path
    raise RuntimeError("No completed synoptic statistics store found in the latest eight runs.")


def open_source(fs, path):
    import xarray as xr
    path = validate_source(path)
    return xr.open_zarr(fs.get_mapper(path, check=False), consolidated=False, chunks=None)
