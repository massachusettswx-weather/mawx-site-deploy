import base64
import gzip
import subprocess
from pathlib import Path
from datetime import datetime

from .source_config import (
    FNV3_LARGE_SOURCE,
)

from fnv3_cyclone.process.generalized_parser import (
    parse_weatherlab_cyclogenesis_file,
)


def _normalize_cycle(cycle):
    """
    Normalize supported cyclone cycle forms to
    Weather Lab YYYY_MM_DDTHH_00 format.

    Accepted:
        YYYYMMDDHH
        YYYYMMDD_HHz
        YYYYMMDD_HH
    """

    if isinstance(cycle, dict):
        date = str(cycle["date"])
        hour = int(cycle["hour"])
        compact = f"{date}{hour:02d}"
    else:
        compact = (
            str(cycle)
            .strip()
            .lower()
            .replace("_", "")
            .replace("z", "")
        )

    if (
        len(compact) != 10
        or not compact.isdigit()
    ):
        raise ValueError(
            "FNV3-L cycle must resolve to YYYYMMDDHH. "
            f"Received: {cycle!r}"
        )

    datetime.strptime(
        compact,
        "%Y%m%d%H",
    )

    return (
        f"{compact[0:4]}_"
        f"{compact[4:6]}_"
        f"{compact[6:8]}T"
        f"{compact[8:10]}_00"
    )


def _curl_download(
    url,
    output_path,
    overwrite=False,
):
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        output_path.exists()
        and output_path.stat().st_size > 0
        and not overwrite
    ):
        print(
            "Using cached:",
            output_path,
        )

        return output_path

    temp_path = (
        output_path.with_suffix(
            output_path.suffix
            + ".part"
        )
    )

    if temp_path.exists():
        temp_path.unlink()

    command = [
        "curl",
        "-L",
        "--fail",
        "--show-error",
        "--silent",
        "--retry",
        str(
            FNV3_LARGE_SOURCE[
                "curl_retries"
            ]
        ),
        "--retry-delay",
        "3",
        "--retry-all-errors",
        "--connect-timeout",
        str(
            FNV3_LARGE_SOURCE[
                "curl_connect_timeout"
            ]
        ),
        "--max-time",
        str(
            FNV3_LARGE_SOURCE[
                "curl_max_time"
            ]
        ),
        "-o",
        str(
            temp_path
        ),
        url,
    ]

    print()
    print(
        "Downloading:"
    )
    print(
        url
    )

    result = subprocess.run(
        command,
        check=False,
    )

    if result.returncode != 0:
        if temp_path.exists():
            temp_path.unlink()

        raise RuntimeError(
            "Weather Lab download failed. "
            f"curl exit code: {result.returncode}"
        )

    if (
        not temp_path.exists()
        or temp_path.stat().st_size == 0
    ):
        raise RuntimeError(
            "Weather Lab returned an empty file."
        )

    temp_path.replace(
        output_path
    )

    print(
        "Saved:",
        output_path,
    )

    print(
        "Size:",
        output_path.stat().st_size,
        "bytes",
    )

    return output_path


def build_ensemble_url(cycle):
    timestamp = _normalize_cycle(
        cycle
    )

    model = FNV3_LARGE_SOURCE[
        "model_code"
    ]

    filename = (
        f"{model}_"
        f"{timestamp}_"
        "cyclogenesis.csv"
    )

    return (
        f"{FNV3_LARGE_SOURCE['base_url']}/"
        f"{model}/"
        "ensemble/"
        "cyclogenesis/"
        "csv/"
        f"{filename}"
    )


def build_mean_url(cycle):
    timestamp = _normalize_cycle(
        cycle
    )

    model = FNV3_LARGE_SOURCE[
        "model_code"
    ]

    filename = (
        f"{model}_"
        f"{timestamp}_"
        "paired.csv"
    )

    return (
        f"{FNV3_LARGE_SOURCE['base_url']}/"
        f"{model}/"
        "ensemble_mean/"
        "paired/"
        "csv/"
        f"{filename}"
    )


def build_probability_url(cycle):
    timestamp = _normalize_cycle(
        cycle
    )

    model = FNV3_LARGE_SOURCE[
        "model_code"
    ]

    filename = (
        f"{model}_"
        f"{timestamp}_"
        "cumulative_probability_fields"
        ".nc.gz.base64"
    )

    return (
        f"{FNV3_LARGE_SOURCE['base_url']}/"
        f"{model}/"
        "ensemble/"
        "cyclogenesis/"
        "netcdf/"
        "cumulative_probability_fields/"
        f"{filename}"
    )


def _decode_probability_file(
    encoded_path,
    nc_path,
):
    """
    Decode WeatherLab .nc.gz.base64 without holding the
    encoded, compressed, or decompressed file in memory.
    """

    import base64
    import gzip
    import shutil
    import tempfile
    from pathlib import Path

    encoded_path = Path(encoded_path)
    nc_path = Path(nc_path)

    nc_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Decode base64 -> temporary gzip file incrementally.
    with tempfile.NamedTemporaryFile(
        suffix=".nc.gz",
        delete=False,
    ) as tmp:

        gz_path = Path(tmp.name)

        carry = b""

        with encoded_path.open("rb") as src:

            while True:
                chunk = src.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                # Base64 source may contain line breaks.
                chunk = b"".join(
                    chunk.split()
                )

                data = carry + chunk

                usable = (
                    len(data) // 4
                ) * 4

                if usable:
                    tmp.write(
                        base64.b64decode(
                            data[:usable]
                        )
                    )

                carry = data[usable:]

            if carry:
                tmp.write(
                    base64.b64decode(
                        carry
                    )
                )

    try:
        # gzip -> NetCDF incrementally.
        with gzip.open(
            gz_path,
            "rb",
        ) as src, nc_path.open(
            "wb",
        ) as dst:

            shutil.copyfileobj(
                src,
                dst,
                length=1024 * 1024,
            )

    finally:
        gz_path.unlink(
            missing_ok=True
        )

    if (
        not nc_path.exists()
        or nc_path.stat().st_size == 0
    ):
        raise RuntimeError(
            "Probability decode produced an empty NetCDF"
        )

    print(
        "Decoded probability NetCDF:",
        nc_path,
        nc_path.stat().st_size,
        "bytes",
    )

    return nc_path

def download_fnv3_large_cycle(
    cycle,
    output_dir=None,
    source_dir=None,
    overwrite=False,
):
    """
    Download the real Google Weather Lab FNV3 Large Ensemble
    products for one initialization.

    Products:
      - 1000-member unpaired cyclogenesis CSV
      - paired ensemble-mean CSV
      - cumulative gridded probability NetCDF

    Returns
    -------
    dict
    """

    _ = source_dir

    cycle = str(
        cycle
    ).strip()

    timestamp = _normalize_cycle(
        cycle
    )

    model = FNV3_LARGE_SOURCE[
        "model_code"
    ]

    if output_dir is None:
        output_dir = (
            Path(__file__).resolve().parents[1]
            / "output"
            / "raw"
            / cycle
        )

    output_dir = Path(
        output_dir
    )

    ensemble_dir = (
        output_dir
        / "ensemble"
    )

    mean_dir = (
        output_dir
        / "mean"
    )

    probability_dir = (
        output_dir
        / "probability"
    )

    ensemble_path = (
        ensemble_dir
        / (
            f"{model}_"
            f"{timestamp}_"
            "cyclogenesis.csv"
        )
    )

    mean_path = (
        mean_dir
        / (
            f"{model}_"
            f"{timestamp}_"
            "paired.csv"
        )
    )

    encoded_probability_path = (
        probability_dir
        / (
            f"{model}_"
            f"{timestamp}_"
            "cumulative_probability_fields"
            ".nc.gz.base64"
        )
    )

    nc_probability_path = (
        probability_dir
        / (
            f"{model}_"
            f"{timestamp}_"
            "cumulative_probability_fields.nc"
        )
    )

    ensemble_path = _curl_download(
        build_ensemble_url(
            cycle
        ),
        ensemble_path,
        overwrite=overwrite,
    )

    mean_path = _curl_download(
        build_mean_url(
            cycle
        ),
        mean_path,
        overwrite=overwrite,
    )

    # Probability is an independent upstream artifact.
    # Do not kill the ensemble/mean production run when Google has
    # not published it for this cycle.
    probability_available = False

    try:
        encoded_probability_path = (
            _curl_download(
                build_probability_url(
                    cycle
                ),
                encoded_probability_path,
                overwrite=overwrite,
            )
        )

        if (
            overwrite
            or not nc_probability_path.exists()
            or nc_probability_path.stat().st_size == 0
        ):
            _decode_probability_file(
                encoded_probability_path,
                nc_probability_path,
            )

        probability_available = (
            nc_probability_path.exists()
            and nc_probability_path.stat().st_size > 0
        )

    except Exception as exc:
        print(
            "FNV3-L native probability unavailable for "
            f"{cycle}: {type(exc).__name__}: {exc}"
        )

        print(
            "Continuing with ensemble + ensemble-mean products."
        )

        probability_available = False
        nc_probability_path = None

    tracks = (
        parse_weatherlab_cyclogenesis_file(
            ensemble_path
        )
    )

    return {
        "cycle": cycle,

        "tracks": tracks,

        "ensemble_path": (
            ensemble_path
        ),

        "mean_path": (
            mean_path
        ),

        "probability_encoded_path": (
            encoded_probability_path
        ),

        "probability_path": (
            nc_probability_path
        ),
    }
