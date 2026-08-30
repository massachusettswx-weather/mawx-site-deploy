from __future__ import annotations

from pathlib import Path


# ============================================================
# CYCLONE OUTPUT CONTRACT
# ============================================================

VALID_CYCLONE_MODELS = {
    "fnv3",
    "fnv3_large",
}


def normalize_cyclone_model(model):
    model = (
        str(model)
        .strip()
        .lower()
        .replace("-", "_")
    )

    aliases = {
        "fnv3l": "fnv3_large",
        "fnv3_l": "fnv3_large",
        "fnv3large": "fnv3_large",
    }

    model = aliases.get(
        model,
        model,
    )

    if model not in VALID_CYCLONE_MODELS:
        raise ValueError(
            f"Unsupported cyclone model: {model}"
        )

    return model


def cyclone_cycle_id(
    date,
    hour,
):
    return (
        f"{str(date)}_"
        f"{int(hour):02d}z"
    )


def cyclone_frame_name(
    forecast_hour,
):
    return (
        f"f{int(forecast_hour):03d}.png"
    )


def cyclone_product_prefix(
    model,
    date,
    hour,
    product,
    region,
):
    model = normalize_cyclone_model(
        model
    )

    return (
        f"products/"
        f"{model}/"
        f"{date}/"
        f"{int(hour):02d}/"
        f"{product}/"
        f"{region}"
    )


def cyclone_object_name(
    model,
    date,
    hour,
    product,
    region,
    forecast_hour,
):
    return (
        f"{cyclone_product_prefix(
            model=model,
            date=date,
            hour=hour,
            product=product,
            region=region,
        )}/"
        f"{cyclone_frame_name(forecast_hour)}"
    )


def cyclone_local_path(
    root,
    model,
    date,
    hour,
    product,
    region,
    forecast_hour,
):
    return (
        Path(root)
        / normalize_cyclone_model(model)
        / str(date)
        / f"{int(hour):02d}"
        / str(product)
        / str(region)
        / cyclone_frame_name(
            forecast_hour
        )
    )
