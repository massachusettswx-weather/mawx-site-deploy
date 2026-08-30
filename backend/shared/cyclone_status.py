from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import threading


_LOCK = threading.Lock()


def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def frame_key(
    product,
    region,
    forecast_hour,
):
    return (
        f"{product}/"
        f"{region}/"
        f"f{int(forecast_hour):03d}.png"
    )


def new_cycle_status(
    *,
    model,
    date,
    hour,
    products,
    regions,
    forecast_hours,
    member_count=None,
):
    return {
        "schema_version": 1,
        "model": model,
        "cycle": (
            f"{date}_{int(hour):02d}z"
        ),
        "date": str(date),
        "hour": int(hour),
        "status": "running",
        "member_count": member_count,
        "products": list(products),
        "regions": list(regions),
        "forecast_hours": sorted(
            {
                int(value)
                for value
                in forecast_hours
            }
        ),
        "completed_forecast_hours": [],
        "files": [],
        "failed": [],
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "completed_at": None,
    }


def load_status(
    path,
):
    path = Path(path)

    if not path.exists():
        return None

    return json.loads(
        path.read_text()
    )


def save_status(
    path,
    status,
):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    status["updated_at"] = utc_now()

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            status,
            indent=2,
            sort_keys=True,
        )
    )

    temporary.replace(path)


def mark_frame_complete(
    status,
    *,
    product,
    region,
    forecast_hour,
    object_name,
):
    key = frame_key(
        product,
        region,
        forecast_hour,
    )

    with _LOCK:
        existing = {
            item["key"]
            for item
            in status["files"]
        }

        if key not in existing:
            status["files"].append(
                {
                    "key": key,
                    "product": product,
                    "region": region,
                    "forecast_hour": int(
                        forecast_hour
                    ),
                    "object": object_name,
                    "published_at": utc_now(),
                }
            )


def mark_frame_failed(
    status,
    *,
    product,
    region,
    forecast_hour,
    error,
):
    with _LOCK:
        status["failed"].append(
            {
                "product": product,
                "region": region,
                "forecast_hour": int(
                    forecast_hour
                ),
                "error": str(error),
                "time": utc_now(),
            }
        )


def update_completed_hours(
    status,
):
    products = set(
        status["products"]
    )

    regions = set(
        status["regions"]
    )

    completed = set()

    for hour in status[
        "forecast_hours"
    ]:
        combinations = {
            (
                item["product"],
                item["region"],
            )
            for item
            in status["files"]
            if item["forecast_hour"]
            == hour
        }

        required = {
            (
                product,
                region,
            )
            for product in products
            for region in regions
        }

        if required.issubset(
            combinations
        ):
            completed.add(hour)

    status[
        "completed_forecast_hours"
    ] = sorted(completed)


def finish_cycle(
    status,
):
    update_completed_hours(
        status
    )

    if (
        len(
            status[
                "completed_forecast_hours"
            ]
        )
        ==
        len(
            status[
                "forecast_hours"
            ]
        )
        and
        not status["failed"]
    ):
        status["status"] = "complete"

    elif status["files"]:
        status["status"] = "partial"

    else:
        status["status"] = "failed"

    status["completed_at"] = utc_now()
