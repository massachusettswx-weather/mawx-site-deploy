from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.cyclone_output import (
    normalize_cyclone_model,
)

from shared.cyclone_products import (
    get_cyclone_product,
)

from shared.cyclone_regions import (
    get_cyclone_region,
)


# ============================================================
# NORMALIZED OBJECTS
# ============================================================

@dataclass
class CycloneFrameRequest:
    model: str
    date: str
    hour: int
    forecast_hour: int
    product: str
    region: str

    def __post_init__(self):
        self.model = normalize_cyclone_model(
            self.model
        )

        self.date = str(
            self.date
        )

        self.hour = int(
            self.hour
        )

        self.forecast_hour = int(
            self.forecast_hour
        )

        self.product = (
            str(self.product)
            .strip()
            .lower()
        )

        self.region = (
            str(self.region)
            .strip()
            .lower()
        )

        get_cyclone_product(
            self.product
        )

        get_cyclone_region(
            self.region
        )


@dataclass
class CycloneInputBundle:
    model: str
    cycle_id: str | None = None

    ensemble_file: Path | None = None
    probability_file: Path | None = None
    mean_file: Path | None = None

    metadata: dict[str, Any] | None = None


# ============================================================
# RAW ROOTS
# ============================================================

def candidate_raw_roots(
    model,
):
    model = normalize_cyclone_model(
        model
    )

    if model == "fnv3":
        return (
            Path(
                "fnv3_cyclone/output/raw"
            ),
            Path(
                "fnv3/output/raw"
            ),
        )

    return (
        Path(
            "fnv3_large_cyclone/output/raw"
        ),
        Path(
            "fnv3_large/output/raw"
        ),
    )


# ============================================================
# CYCLE DIRECTORY
# ============================================================

def cycle_directory_names(
    date,
    hour,
):
    date = str(date)
    hour = int(hour)

    return (
        f"{date}{hour:02d}",
        f"{date}_{hour:02d}",
        f"{date}_{hour:02d}z",
    )


def find_cycle_root(
    model,
    date=None,
    hour=None,
):
    roots = candidate_raw_roots(
        model
    )

    # --------------------------------------------------------
    # Explicit cycle
    # --------------------------------------------------------

    if (
        date is not None
        and
        hour is not None
    ):

        names = cycle_directory_names(
            date,
            hour,
        )

        for root in roots:

            for name in names:

                candidate = (
                    root
                    /
                    name
                )

                if candidate.exists():
                    return candidate

        return None

    # --------------------------------------------------------
    # Latest locally available cycle
    # --------------------------------------------------------

    candidates = []

    for root in roots:

        if not root.exists():
            continue

        for child in root.iterdir():

            if child.is_dir():
                candidates.append(
                    child
                )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )


# ============================================================
# FILE SELECTION
# ============================================================

def newest_file(
    directory,
    *,
    suffixes=None,
):
    if (
        directory is None
        or
        not directory.exists()
    ):
        return None

    files = [
        path
        for path in directory.rglob("*")
        if path.is_file()
    ]

    if suffixes:

        suffixes = tuple(
            suffix.lower()
            for suffix in suffixes
        )

        files = [
            path
            for path in files
            if path.name.lower().endswith(
                suffixes
            )
        ]

    if not files:
        return None

    return max(
        files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )


def find_ensemble_file(
    cycle_root,
):
    if cycle_root is None:
        return None

    # Preferred production layout:
    #
    # cycle/
    #   ensemble/
    #   probability/
    #   mean/

    ensemble_dir = (
        cycle_root
        /
        "ensemble"
    )

    path = newest_file(
        ensemble_dir,
        suffixes=(
            ".csv",
            ".csv.gz",
        ),
    )

    if path is not None:
        return path

    # Fallback for older layouts.

    candidates = [
        path
        for path in cycle_root.rglob("*")
        if (
            path.is_file()
            and
            "ensemble"
            in path.name.lower()
            and
            path.name.lower().endswith(
                (
                    ".csv",
                    ".csv.gz",
                )
            )
        )
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )


def find_probability_file(
    cycle_root,
):
    if cycle_root is None:
        return None

    probability_dir = (
        cycle_root
        /
        "probability"
    )

    path = newest_file(
        probability_dir,
        suffixes=(
            ".nc",
            ".nc.gz",
            ".base64",
        ),
    )

    if path is not None:
        return path

    candidates = [
        path
        for path in cycle_root.rglob("*")
        if (
            path.is_file()
            and
            "probability"
            in path.name.lower()
        )
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )


def find_mean_file(
    cycle_root,
):
    if cycle_root is None:
        return None

    mean_dir = (
        cycle_root
        /
        "mean"
    )

    path = newest_file(
        mean_dir,
        suffixes=(
            ".csv",
            ".csv.gz",
        ),
    )

    if path is not None:
        return path

    candidates = [
        path
        for path in cycle_root.rglob("*")
        if (
            path.is_file()
            and
            (
                "paired"
                in path.name.lower()
                or
                "mean"
                in path.name.lower()
            )
            and
            path.name.lower().endswith(
                (
                    ".csv",
                    ".csv.gz",
                )
            )
        )
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )


# ============================================================
# DISCOVERY
# ============================================================

def discover_cyclone_inputs(
    model,
    date=None,
    hour=None,
):
    model = normalize_cyclone_model(
        model
    )

    cycle_root = find_cycle_root(
        model,
        date=date,
        hour=hour,
    )

    if cycle_root is None:

        return CycloneInputBundle(
            model=model,
            metadata={
                "cycle_root": None,
            },
        )

    return CycloneInputBundle(
        model=model,

        cycle_id=(
            cycle_root.name
        ),

        ensemble_file=(
            find_ensemble_file(
                cycle_root
            )
        ),

        probability_file=(
            find_probability_file(
                cycle_root
            )
        ),

        mean_file=(
            find_mean_file(
                cycle_root
            )
        ),

        metadata={
            "cycle_root": str(
                cycle_root
            ),
        },
    )


# ============================================================
# PRODUCT INPUT CONTRACT
# ============================================================

PRODUCT_INPUT_KIND = {

    "track":
        "ensemble",

    "intensity":
        "ensemble",

    "instantaneous_track":
        "ensemble",

    "instantaneous_intensity":
        "ensemble",

    "mean_track":
        "mean",

    "cyclogenesis_probability":
        "probability",

    "wind_probability_34kt":
        "probability",

    "wind_probability_50kt":
        "probability",

    "wind_probability_64kt":
        "probability",
}


def get_required_input_kind(
    product,
):
    product = (
        str(product)
        .strip()
        .lower()
    )

    get_cyclone_product(
        product
    )

    return PRODUCT_INPUT_KIND[
        product
    ]


def resolve_product_input(
    bundle,
    product,
):
    kind = get_required_input_kind(
        product
    )

    if kind == "ensemble":

        path = (
            bundle.ensemble_file
        )

    elif kind == "probability":

        path = (
            bundle.probability_file
        )

    elif kind == "mean":

        path = (
            bundle.mean_file
            or
            bundle.ensemble_file
        )

    else:

        raise RuntimeError(
            f"Unknown cyclone input "
            f"kind: {kind}"
        )

    if path is None:

        raise FileNotFoundError(
            f"No {kind} input "
            f"available for "
            f"{bundle.model} / "
            f"{product} "
            f"(cycle={bundle.cycle_id})"
        )

    return Path(
        path
    )
