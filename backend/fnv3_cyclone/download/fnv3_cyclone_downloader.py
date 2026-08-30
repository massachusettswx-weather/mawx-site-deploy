import re
from pathlib import Path

import requests

from ..process.generalized_parser import (
    parse_weatherlab_atcf,
)


BASE_URL = (
    "https://deepmind.google.com/science/weatherlab/"
    "download/cyclones"
)

MODEL_CODE = "OPER"


def _normalize_cycle(cycle):
    """
    Normalize MassachusettsWx / Weather Lab cycle identifiers.

    Accepted inputs:

        2026082700
        20260827_00z
        {"date": "20260827", "hour": 0}
        {"id": "20260827_00z", ...}

    Returns the Weather Lab timestamp string expected by the
    FNV3 source URL.
    """

    if isinstance(cycle, dict):

        date = str(
            cycle.get(
                "date",
                "",
            )
        )

        try:
            hour = int(
                cycle.get(
                    "hour",
                    0,
                )
            )
        except (TypeError, ValueError):
            hour = 0

        if (
            len(date) == 8
            and
            date.isdigit()
        ):
            compact = (
                f"{date}"
                f"{hour:02d}"
            )

        else:
            cycle = cycle.get(
                "id",
                "",
            )

            compact = str(
                cycle
            )

    else:
        compact = str(
            cycle
        )


    compact = compact.strip()


    # MassachusettsWx operational form:
    #
    #     20260827_00z
    #
    match = re.fullmatch(
        r"(\d{8})_(\d{2})z",
        compact,
        flags=re.IGNORECASE,
    )

    if match:
        compact = (
            match.group(1)
            +
            match.group(2)
        )


    # Weather Lab compact form:
    #
    #     2026082700
    #
    if not re.fullmatch(
        r"\d{10}",
        compact,
    ):
        raise ValueError(
            "FNV3 cycle must use "
            "YYYYMMDDHH or YYYYMMDD_HHz format."
        )


    return (
        f"{compact[0:4]}_"
        f"{compact[4:6]}_"
        f"{compact[6:8]}T"
        f"{compact[8:10]}_00"
    )


def build_weatherlab_url(cycle):
    timestamp = _normalize_cycle(
        cycle
    )

    filename = (
        f"{MODEL_CODE}_"
        f"{timestamp}_"
        "atcf_a_deck.txt"
    )

    return (
        f"{BASE_URL}/"
        f"{MODEL_CODE}/"
        "ensemble/"
        "paired/"
        "atcf/"
        f"{filename}"
    )


def download_fnv3_cyclone_cycle(
    cycle=None,
    output_dir=None,
    overwrite=False,
):
    """
    Download and parse the real WeatherNext Cyclones
    Operational/FNV3 ensemble ATCF feed from
    Google Weather Lab.
    """

    if cycle is None:
        raise ValueError(
            "cycle is required for FNV3 download."
        )

    if output_dir is None:
        output_dir = (
            Path(__file__).resolve().parents[1]
            / "output"
            / "raw"
            / str(cycle)
        )

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = _normalize_cycle(
        cycle
    )

    filename = (
        f"{MODEL_CODE}_"
        f"{timestamp}_"
        "atcf_a_deck.txt"
    )

    output_path = (
        output_dir
        / filename
    )

    url = build_weatherlab_url(
        cycle
    )

    if (
        output_path.exists()
        and not overwrite
    ):
        text = output_path.read_text(
            encoding="utf-8"
        )

    else:
        print(
            "Downloading Weather Lab FNV3:"
        )

        print(
            url
        )

        response = requests.get(
            url,
            timeout=60,
        )

        response.raise_for_status()

        text = response.text

        if "# BEGIN DATA" not in text:
            raise RuntimeError(
                "Weather Lab response does not look "
                "like an ATCF cyclone feed."
            )

        output_path.write_text(
            text,
            encoding="utf-8",
        )

    tracks = parse_weatherlab_atcf(
        text
    )

    if not tracks:
        raise RuntimeError(
            "Weather Lab FNV3 feed downloaded, "
            "but no cyclone track points were parsed."
        )

    print(
        "Parsed track points:",
        len(tracks),
    )

    print(
        "Members:",
        len(
            {
                point.member
                for point in tracks
            }
        ),
    )

    print(
        "Systems:",
        len(
            {
                point.system_id
                for point in tracks
            }
        ),
    )

    return tracks
