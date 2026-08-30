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

from fnv3_large_cyclone.process.mean_parser import (
    parse_weatherlab_paired_mean_file,
)

from fnv3_large_cyclone.plot.track_plots import (
    plot_fnv3_large_tracks,
)

from fnv3_large_cyclone.plot.mean_track_plots import (
    plot_fnv3_large_mean_tracks,
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


# ============================================================
# MODEL
# ============================================================

MODEL = "fnv3_large"

MODEL_CODE = (
    "FNV3_LARGE_ENSEMBLE"
)

TRACK_PRODUCT = (
    "tracks_max_wind"
)

MEAN_PRODUCT = (
    "ensemble_mean_tracks"
)


# ============================================================
# WEATHER LAB URLS
# ============================================================

BASE_URL = (
    "https://deepmind.google.com/science/weatherlab/"
    "download/cyclones/"
    "FNV3_LARGE_ENSEMBLE"
)

CYCLE_HOURS = (
    0,
    6,
    12,
    18,
)

LOOKBACK_CYCLES = 12


# ============================================================
# CYCLE FORMAT
# ============================================================

def _cycle_string(dt):
    return dt.strftime(
        "%Y%m%d%H"
    )


def _weatherlab_timestamp(dt):
    return dt.strftime(
        "%Y_%m_%dT%H_00"
    )


# ============================================================
# SOURCE URLS
# ============================================================

def build_ensemble_url(dt):
    timestamp = (
        _weatherlab_timestamp(
            dt
        )
    )

    filename = (
        f"{MODEL_CODE}_"
        f"{timestamp}_"
        "cyclogenesis.csv"
    )

    return (
        f"{BASE_URL}/"
        "ensemble/"
        "cyclogenesis/"
        "csv/"
        f"{filename}"
    )


def build_mean_url(dt):
    timestamp = (
        _weatherlab_timestamp(
            dt
        )
    )

    filename = (
        f"{MODEL_CODE}_"
        f"{timestamp}_"
        "paired.csv"
    )

    return (
        f"{BASE_URL}/"
        "ensemble_mean/"
        "paired/"
        "csv/"
        f"{filename}"
    )


# ============================================================
# REMOTE AVAILABILITY
# ============================================================

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

    # Weather Lab can occasionally be awkward with HEAD.
    # Fall back to a tiny ranged GET.
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
        "60",
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


# ============================================================
# LATEST AVAILABLE CYCLE
# ============================================================

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
            "Checking FNV3-L WeatherLab cycle:",
            dt.strftime(
                "%Y-%m-%d %HZ"
            ),
            flush=True,
        )

        # The 1000-member cyclogenesis file remains our
        # primary cycle-availability probe.
        if not _remote_exists(
            build_ensemble_url(
                dt
            )
        ):
            continue

        # Mean data is now a required production product.
        # Do not advertise a cycle until that file exists too.
        if not _remote_exists(
            build_mean_url(
                dt
            )
        ):
            print(
                "  Ensemble file exists, but paired "
                "ensemble mean is not available yet.",
                flush=True,
            )

            continue

        print(
            "Latest complete FNV3-L WeatherLab cycle:",
            _cycle_string(
                dt
            ),
            flush=True,
        )

        return dt

    raise RuntimeError(
        "No recent complete WeatherNext FNV3 Large "
        "Ensemble cycle found."
    )


# ============================================================
# GCS PRODUCT OBJECT
# ============================================================

def _product_object_name(
    cycle_date,
    cycle_hour,
    product,
    basin,
    forecast_hour=360,
):
    return (
        f"products/{MODEL}/"
        f"{cycle_date}/"
        f"{int(cycle_hour):02d}/"
        f"{product}/"
        f"{basin}/"
        f"f{int(forecast_hour):03d}.png"
    )


# ============================================================
# CYCLE COMPLETION
# ============================================================

def _cycle_already_complete(dt):
    cycle_date = dt.strftime(
        "%Y%m%d"
    )

    cycle_hour = int(
        dt.hour
    )

    cycle_id = build_cycle_id(
        cycle_date,
        cycle_hour,
    )

    ready_object = (
        get_cycle_ready_object_name(
            MODEL,
            cycle_id,
        )
    )

    if not cloud_exists(
        ready_object
    ):
        return False

    # A legacy tracks-only READY marker must no longer
    # count as a fully complete FNV3-L cycle.
    track_product_exists = any(
        cloud_exists(
            _product_object_name(
                cycle_date=cycle_date,
                cycle_hour=cycle_hour,
                product=TRACK_PRODUCT,
                basin=basin,
            )
        )
        for basin in ACTIVE_BASINS
    )

    mean_product_exists = any(
        cloud_exists(
            _product_object_name(
                cycle_date=cycle_date,
                cycle_hour=cycle_hour,
                product=MEAN_PRODUCT,
                basin=basin,
            )
        )
        for basin in ACTIVE_BASINS
    )

    if (
        track_product_exists
        and mean_product_exists
    ):
        return True

    print(
        f"FNV3-L {cycle_id} has a READY marker "
        "but is missing one or more required "
        "product families. Reprocessing cycle.",
        flush=True,
    )

    return False


# ============================================================
# DOWNLOAD
# ============================================================

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
        "1800",
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
            "FNV3-L WeatherLab download "
            "failed with curl code "
            f"{result.returncode}."
        )

    if (
        not temp_path.exists()
        or temp_path.stat().st_size == 0
    ):
        raise RuntimeError(
            "FNV3-L WeatherLab download "
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


# ============================================================
# UPLOAD ONE PRODUCT
# ============================================================

def _upload_plot(
    local_file,
    cycle_date,
    cycle_hour,
    product,
    basin,
):
    uri = upload_product(
        local_path=local_file,
        model=MODEL,
        cycle_date=cycle_date,
        cycle_hour=cycle_hour,
        product=product,
        region=basin,
        forecast_hour=360,
    )

    print(
        "Uploaded:",
        uri,
        flush=True,
    )

    local_file.unlink(
        missing_ok=True
    )

    return uri


# ============================================================
# MAIN RUNNER
# ============================================================

def run_fnv3_large(
    cycle=None,
):
    # --------------------------------------------------------
    # RESOLVE CYCLE
    # --------------------------------------------------------

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

    cycle_date = (
        cycle_dt.strftime(
            "%Y%m%d"
        )
    )

    cycle_hour = int(
        cycle_dt.hour
    )

    cycle_id = build_cycle_id(
        cycle_date,
        cycle_hour,
    )

    # --------------------------------------------------------
    # IDEMPOTENCE
    # --------------------------------------------------------

    if _cycle_already_complete(
        cycle_dt
    ):
        print(
            f"FNV3-L {cycle_id} is already "
            "fully published. Nothing to do.",
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

    # --------------------------------------------------------
    # TEMP STORAGE
    # --------------------------------------------------------

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

    shutil.rmtree(
        output_dir,
        ignore_errors=True,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = (
        _weatherlab_timestamp(
            cycle_dt
        )
    )

    ensemble_file = (
        raw_dir
        / "ensemble"
        / (
            f"{MODEL_CODE}_"
            f"{timestamp}_"
            "cyclogenesis.csv"
        )
    )

    mean_file = (
        raw_dir
        / "mean"
        / (
            f"{MODEL_CODE}_"
            f"{timestamp}_"
            "paired.csv"
        )
    )

    try:
        # ====================================================
        # DOWNLOAD
        # ====================================================

        _download_file(
            build_ensemble_url(
                cycle_dt
            ),
            ensemble_file,
        )

        _download_file(
            build_mean_url(
                cycle_dt
            ),
            mean_file,
        )

        # ====================================================
        # PARSE 1000-MEMBER ENSEMBLE
        # ====================================================

        tracks = (
            parse_weatherlab_cyclogenesis_file(
                ensemble_file
            )
        )

        if not tracks:
            raise RuntimeError(
                "FNV3-L WeatherLab ensemble CSV "
                "parsed zero track points."
            )

        members = {
            point.member
            for point in tracks
        }

        print(
            "FNV3-L track points:",
            len(tracks),
            flush=True,
        )

        print(
            "FNV3-L members:",
            len(members),
            flush=True,
        )

        if len(members) != 1000:
            raise RuntimeError(
                "Expected 1000 FNV3-L members, "
                f"but found {len(members)}."
            )

        # ====================================================
        # PARSE ENSEMBLE MEAN
        # ====================================================

        mean_tracks = (
            parse_weatherlab_paired_mean_file(
                mean_file
            )
        )

        if not mean_tracks:
            raise RuntimeError(
                "FNV3-L paired ensemble-mean CSV "
                "parsed zero track points."
            )

        mean_systems = {
            point.system_id
            for point in mean_tracks
        }

        print(
            "FNV3-L mean track points:",
            len(mean_tracks),
            flush=True,
        )

        print(
            "FNV3-L mean systems:",
            len(mean_systems),
            flush=True,
        )

        # ====================================================
        # RENDER + UPLOAD
        # ====================================================

        created = []
        failures = []

        for basin in ACTIVE_BASINS:
            print()
            print(
                "=" * 60,
                flush=True,
            )
            print(
                "FNV3-L BASIN:",
                basin,
                flush=True,
            )
            print(
                "=" * 60,
                flush=True,
            )

            # ------------------------------------------------
            # 1000-MEMBER TRACKS
            # ------------------------------------------------

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

            if basin_tracks:
                local_file = (
                    output_dir
                    / TRACK_PRODUCT
                    / basin
                    / (
                        f"{MODEL}_"
                        f"{TRACK_PRODUCT}_"
                        f"{basin}_"
                        "f360.png"
                    )
                )

                local_file.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                try:
                    plot_fnv3_large_tracks(
                        tracks=basin_tracks,
                        output_file=local_file,
                        title=(
                            "WeatherNext 2 Cyclones r2 | "
                            "1000-Member Ensemble"
                        ),
                        subtitle=(
                            f"Init "
                            f"{cycle_date} "
                            f"{cycle_hour:02d}Z | "
                            "Unpaired Cyclogenesis"
                        ),
                        basin=basin,
                        dpi=160,
                    )

                    uri = _upload_plot(
                        local_file=local_file,
                        cycle_date=cycle_date,
                        cycle_hour=cycle_hour,
                        product=TRACK_PRODUCT,
                        basin=basin,
                    )

                    created.append(
                        uri
                    )

                except Exception as error:
                    failures.append(
                        (
                            TRACK_PRODUCT,
                            basin,
                            error,
                        )
                    )

                    print(
                        f"FNV3-L {TRACK_PRODUCT} "
                        f"{basin} failed: "
                        f"{type(error).__name__}: "
                        f"{error}",
                        flush=True,
                    )

            # ------------------------------------------------
            # ENSEMBLE MEAN
            # ------------------------------------------------

            mean_grouped = (
                filter_tracks_for_basin(
                    mean_tracks,
                    basin,
                )
            )

            basin_mean_tracks = (
                flatten_tracks(
                    mean_grouped
                )
            )

            if basin_mean_tracks:
                mean_local_file = (
                    output_dir
                    / MEAN_PRODUCT
                    / basin
                    / (
                        f"{MODEL}_"
                        f"{MEAN_PRODUCT}_"
                        f"{basin}_"
                        "f360.png"
                    )
                )

                mean_local_file.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                try:
                    plot_fnv3_large_mean_tracks(
                        tracks=basin_mean_tracks,
                        output_file=mean_local_file,
                        title=(
                            "WeatherNext 2 Cyclones r2 | "
                            "Large Ensemble Mean"
                        ),
                        subtitle=(
                            f"Init "
                            f"{cycle_date} "
                            f"{cycle_hour:02d}Z | "
                            "Paired Ensemble Mean"
                        ),
                        basin=basin,
                        dpi=180,
                    )

                    uri = _upload_plot(
                        local_file=mean_local_file,
                        cycle_date=cycle_date,
                        cycle_hour=cycle_hour,
                        product=MEAN_PRODUCT,
                        basin=basin,
                    )

                    created.append(
                        uri
                    )

                except Exception as error:
                    failures.append(
                        (
                            MEAN_PRODUCT,
                            basin,
                            error,
                        )
                    )

                    print(
                        f"FNV3-L {MEAN_PRODUCT} "
                        f"{basin} failed: "
                        f"{type(error).__name__}: "
                        f"{error}",
                        flush=True,
                    )

        # ====================================================
        # FAILURE GATE
        # ====================================================

        if failures:
            print()
            print(
                "=" * 60,
                flush=True,
            )
            print(
                "FNV3-L PRODUCT FAILURES",
                flush=True,
            )
            print(
                "=" * 60,
                flush=True,
            )

            for (
                product,
                basin,
                error,
            ) in failures:
                print(
                    product,
                    basin,
                    type(error).__name__,
                    error,
                    flush=True,
                )

            raise RuntimeError(
                "FNV3-L rendering/upload had "
                f"{len(failures)} failures. "
                "Cycle will not be published."
            )

        if not created:
            raise RuntimeError(
                "FNV3-L created no uploaded products."
            )

        # Make sure we actually produced at least one
        # product from BOTH required families.
        uploaded_track_product = any(
            (
                f"/{TRACK_PRODUCT}/"
                in uri
            )
            for uri in created
        )

        uploaded_mean_product = any(
            (
                f"/{MEAN_PRODUCT}/"
                in uri
            )
            for uri in created
        )

        if not uploaded_track_product:
            raise RuntimeError(
                "FNV3-L produced no "
                "1000-member track products."
            )

        if not uploaded_mean_product:
            raise RuntimeError(
                "FNV3-L produced no "
                "ensemble-mean track products."
            )

        # ====================================================
        # PUBLICATION
        # ====================================================

        result = {
            "model": MODEL,
            "cycle": cycle_id,
            "members": len(members),
            "points": len(tracks),
            "mean_points": len(
                mean_tracks
            ),
            "mean_systems": len(
                mean_systems
            ),
            "products": [
                TRACK_PRODUCT,
                MEAN_PRODUCT,
            ],
            "created": len(
                created
            ),
            "failed": 0,
            "files": created,
        }

        cycle_object = make_cycle(
            MODEL,
            cycle_dt,
        )

        publish_result = (
            publish_cycle(
                model=MODEL,
                cycle=cycle_object,
                result=result,
            )
        )

        result[
            "publication"
        ] = publish_result

        print()
        print(
            "=" * 60,
            flush=True,
        )
        print(
            "FNV3-L CYCLE COMPLETE",
            flush=True,
        )
        print(
            "Cycle:",
            cycle_id,
            flush=True,
        )
        print(
            "Uploaded products:",
            len(created),
            flush=True,
        )
        print(
            "Required product families:",
            (
                f"{TRACK_PRODUCT}, "
                f"{MEAN_PRODUCT}"
            ),
            flush=True,
        )
        print(
            "=" * 60,
            flush=True,
        )

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
        run_fnv3_large()
    )
