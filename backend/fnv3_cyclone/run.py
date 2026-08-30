from shared.inventory_seed import (
    build_work_plan,
    mark_complete,
)

from shared.operational_lifecycle import (
    FrontierSweep,
    OperationalCycleState,
    OperationalLifecycle,
)

from pathlib import Path

from .download.fnv3_cyclone_downloader import (


    download_fnv3_cyclone_cycle,
)

from .products.cyclone_products import (
    get_default_products,
)


BASE_DIR = Path(__file__).parent

OUTPUT_DIR = (
    BASE_DIR
    / "output"
)


def run_fnv3_cyclone_cycle(
    cycle,
    products=None,
    overwrite=False,
):
    if products is None:
        products = get_default_products()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_dir = (
        OUTPUT_DIR
        / "raw"
        / str(cycle)
    )

    print()
    print("=" * 60)
    print("FNV3 CYCLONE")
    print("=" * 60)

    print(
        "Cycle:",
        cycle,
    )

    print(
        "Products:",
        ", ".join(products),
    )

    print(
        "Output:",
        OUTPUT_DIR,
    )

    print()

    data = download_fnv3_cyclone_cycle(
        cycle=cycle,
        output_dir=raw_dir,
        overwrite=overwrite,
    )

    return data


if __name__ == "__main__":
    raise SystemExit(
        "FNV3 Cyclone should be run through "
        "the model backend after cycle detection "
        "is configured."
    )
