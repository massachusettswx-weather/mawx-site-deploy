import gzip
import io

import requests

from .atcf_client import (
    FNV3CycloneClient,
)


def download_google_atcf_guidance(
    url,
    output_dir=None,
    aids=None,
):
    response = requests.get(
        url,
        timeout=60,
    )

    response.raise_for_status()

    raw = response.content

    if url.endswith(".gz"):
        with gzip.GzipFile(
            fileobj=io.BytesIO(raw)
        ) as gz:
            text = gz.read().decode(
                "utf-8",
                errors="replace",
            )
    else:
        text = raw.decode(
            "utf-8",
            errors="replace",
        )

    client = FNV3CycloneClient(
        cache_dir=output_dir,
    )

    tracks = client.parse_atcf(
        text,
        aids=aids,
    )

    found_aids = sorted({
        point["aid"]
        for point in tracks
    })

    cycles = sorted({
        point["cycle"]
        for point in tracks
    })

    print(
        "Google aids found:",
        found_aids,
    )

    print(
        "Cycles found:",
        cycles[-10:],
    )

    print(
        "Track points:",
        len(tracks),
    )

    return tracks
