from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import subprocess

from fnv3_cyclone.basins import ACTIVE_BASINS

from fnv3_cyclone.process.generalized_parser import (
    parse_weatherlab_cyclogenesis_file,
)

from fnv3_cyclone.process.basin_filter import (
    filter_tracks_for_basin,
    flatten_tracks,
)

from fnv3_cyclone.plot.track_plots import (
    plot_cyclone_tracks,
)

from shared.inventory_seed import (
    build_work_plan,
    mark_complete,
)

from shared.operational_lifecycle import (
    FrontierSweep,
    OperationalCycleState,
    OperationalLifecycle,
)

from shared.cycles import (
    make_cycle,
)

from shared.publish import (
    build_cycle_id,
    get_cycle_ready_object_name,
    publish_cycle,
)

from shared.storage import (
    build_local_output_cycle_dir,
    cloud_exists,
    get_local_root,
    upload_product,
)


MODEL = "fnv3"
MODEL_CODE = "OPER"
PRODUCT = "tracks_max_wind"

BASE_URL = (
    "https://deepmind.google.com/science/weatherlab/"
    "download/cyclones/OPER/ensemble/cyclogenesis/csv"
)

CYCLE_HOURS = (
    0,
    6,
    12,
    18,
)

LOOKBACK_CYCLES = 12


def _cycle_string(dt):
    return dt.strftime(
        "%Y%m%d%H"
    )


def _weatherlab_timestamp(dt):
    return dt.strftime(
        "%Y_%m_%dT%H_00"
    )


def build_weatherlab_url(dt):
    timestamp = (
        _weatherlab_timestamp(
            dt
        )
    )

    return (
        f"{BASE_URL}/"
        f"OPER_{timestamp}_"
        "cyclogenesis.csv"
    )


def _remote_exists(url):
    command = [
        "curl",
        "-L",
        "--fail",
        "--silent",
        "--show-error",
        "--head",
        "--connect-timeout",
        "15",
        "--max-time",
        "30",
        url,
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    if result.returncode == 0:
        return True

    # Some endpoints can behave poorly with HEAD.
    command = [
        "curl",
        "-L",
        "--fail",
        "--silent",
        "--show-error",
        "--range",
        "0-0",
        "--connect-timeout",
        "15",
        "--max-time",
        "45",
        "-o",
        "/dev/null",
        url,
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return (
        result.returncode
        == 0
    )


def find_latest_cycle():
    now = datetime.now(
        timezone.utc
    )

    latest_hour = (
        now.hour
        // 6
        * 6
    )

    candidate = now.replace(
        hour=latest_hour,
        minute=0,
        second=0,
        microsecond=0,
    )

    for offset in range(
        LOOKBACK_CYCLES
    ):
        dt = (
            candidate
            - timedelta(
                hours=6 * offset
            )
        )

        if dt.hour not in CYCLE_HOURS:
            continue

        print(
            "Checking FNV3 WeatherLab cycle:",
            dt.strftime(
                "%Y-%m-%d %HZ"
            ),
            flush=True,
        )

        if _remote_exists(
            build_weatherlab_url(
                dt
            )
        ):
            print(
                "Latest FNV3 WeatherLab cycle:",
                _cycle_string(
                    dt
                ),
                flush=True,
            )

            return dt

    raise RuntimeError(
        "No recent WeatherNext Cyclones "
        "Operational cycle found."
    )


def _cycle_already_complete(dt):
    cycle_id = build_cycle_id(
        dt.strftime("%Y%m%d"),
        dt.hour,
    )

    ready_object = (
        get_cycle_ready_object_name(
            MODEL,
            cycle_id,
        )
    )

    return cloud_exists(
        ready_object
    )


def _download_file(
    url,
    output_path,
):
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = (
        output_path.with_suffix(
            output_path.suffix
            + ".part"
        )
    )

    temp_path.unlink(
        missing_ok=True
    )

    command = [
        "curl",
        "-L",
        "--fail",
        "--show-error",
        "--silent",
        "--retry",
        "5",
        "--retry-delay",
        "3",
        "--retry-all-errors",
        "--connect-timeout",
        "30",
        "--max-time",
        "900",
        "-o",
        str(temp_path),
        url,
    ]

    print(
        "Downloading:",
        url,
        flush=True,
    )

    result = subprocess.run(
        command,
        check=False,
    )

    if result.returncode != 0:
        temp_path.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "FNV3 WeatherLab download failed "
            f"with curl code {result.returncode}."
        )

    if (
        not temp_path.exists()
        or temp_path.stat().st_size == 0
    ):
        raise RuntimeError(
            "FNV3 WeatherLab download "
            "returned an empty file."
        )

    temp_path.replace(
        output_path
    )

    print(
        "Downloaded:",
        output_path,
        output_path.stat().st_size,
        "bytes",
        flush=True,
    )

    return output_path


def run_fnv3(
    cycle=None,
):
    if cycle is None:
        cycle_dt = (
            find_latest_cycle()
        )

    elif isinstance(
        cycle,
        datetime,
    ):
        cycle_dt = (
            cycle.astimezone(
                timezone.utc
            )
        )

    else:
        cycle_dt = (
            datetime.strptime(
                str(cycle),
                "%Y%m%d%H",
            )
            .replace(
                tzinfo=timezone.utc
            )
        )

    cycle_date = cycle_dt.strftime(
        "%Y%m%d"
    )

    cycle_hour = int(
        cycle_dt.hour
    )

    cycle_id = build_cycle_id(
        cycle_date,
        cycle_hour,
    )

    if _cycle_already_complete(
        cycle_dt
    ):
        print(
            f"FNV3 {cycle_id} is already "
            "published. Nothing to do.",
            flush=True,
        )

        return {
            "model": MODEL,
            "cycle": cycle_id,
            "status": "already_complete",
            "created": 0,
            "failed": 0,
            "files": [],
        }

    workspace = (
        get_local_root()
        / MODEL
        / cycle_date
        / f"{cycle_hour:02d}"
    )

    raw_dir = (
        workspace
        / "raw"
    )

    output_dir = (
        build_local_output_cycle_dir(
            MODEL,
            cycle_date,
            cycle_hour,
        )
    )

    shutil.rmtree(
        workspace,
        ignore_errors=True,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_file = (
        raw_dir
        / (
            f"{MODEL_CODE}_"
            f"{_weatherlab_timestamp(cycle_dt)}_"
            "cyclogenesis.csv"
        )
    )

    try:
        _download_file(
            build_weatherlab_url(
                cycle_dt
            ),
            raw_file,
        )

        tracks = (
            parse_weatherlab_cyclogenesis_file(
                raw_file
            )
        )

        if not tracks:
            raise RuntimeError(
                "FNV3 WeatherLab CSV parsed "
                "zero track points."
            )

        members = {
            point.member
            for point in tracks
        }

        print(
            "FNV3 track points:",
            len(tracks),
            flush=True,
        )

        print(
            "FNV3 members:",
            len(members),
            flush=True,
        )

        created = []
        failed = 0

        for basin in ACTIVE_BASINS:
            grouped = (
                filter_tracks_for_basin(
                    tracks,
                    basin,
                )
            )

            basin_tracks = (
                flatten_tracks(
                    grouped
                )
            )

            if not basin_tracks:
                continue

            local_file = (
                output_dir
                / PRODUCT
                / basin
                / (
                    f"{MODEL}_"
                    f"{PRODUCT}_"
                    f"{basin}_"
                    "f360.png"
                )
            )

            local_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            try:
                plot_cyclone_tracks(
                    tracks=basin_tracks,
                    output_file=local_file,
                    title=(
                        "WeatherNext Cyclones "
                        "Operational"
                    ),
                    subtitle=(
                        f"Init "
                        f"{cycle_date} "
                        f"{cycle_hour:02d}Z | "
                        "Unpaired Cyclogenesis"
                    ),
                    basin=basin,
                    mark_final_lows=False,
                    label_pressures=False,
                    plot_points=True,
                    dpi=180,
                )

                uri = upload_product(
                    local_path=local_file,
                    model=MODEL,
                    cycle_date=cycle_date,
                    cycle_hour=cycle_hour,
                    product=PRODUCT,
                    region=basin,
                    forecast_hour=360,
                )

                print(
                    "Uploaded:",
                    uri,
                    flush=True,
                )

                created.append(
                    uri
                )

                local_file.unlink(
                    missing_ok=True
                )

            except Exception as error:
                failed += 1

                print(
                    f"FNV3 {basin} failed: "
                    f"{type(error).__name__}: "
                    f"{error}",
                    flush=True,
                )

        if failed:
            raise RuntimeError(
                f"FNV3 rendering/upload had "
                f"{failed} basin failures. "
                "Cycle will not be published."
            )

        if not created:
            raise RuntimeError(
                "FNV3 created no uploaded products."
            )

        result = {
            "model": MODEL,
            "cycle": cycle_id,
            "members": len(members),
            "points": len(tracks),
            "created": len(created),
            "failed": 0,
            "files": created,
        }

        cycle_object = make_cycle(
            MODEL,
            cycle_dt,
        )

        publish_result = publish_cycle(
            model=MODEL,
            cycle=cycle_object,
            result=result,
        )

        result[
            "publication"
        ] = publish_result

        return result

    finally:
        shutil.rmtree(
            workspace,
            ignore_errors=True,
        )

        shutil.rmtree(
            output_dir,
            ignore_errors=True,
        )


if __name__ == "__main__":
    print(
        run_fnv3()
    )
