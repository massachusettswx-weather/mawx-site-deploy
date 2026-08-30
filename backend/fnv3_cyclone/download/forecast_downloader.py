from .forecast_client import (
    FNV3ForecastClient,
)


def download_fnv3_cycle(
    cycle=None,
    output_dir=None,
):
    """
    Retrieve generalized FNV3 tropical-cyclone tracker output.

    This is the MAIN FNV3 pipeline and is not constrained
    to storms already present in ATCF.
    """

    client = FNV3ForecastClient(
        cache_dir=output_dir,
    )

    if cycle is None:
        cycle = client.latest_cycle()

    return client.load_cycle(
        cycle
    )
