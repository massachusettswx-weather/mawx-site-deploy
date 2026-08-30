from __future__ import annotations

from pathlib import Path

from shared.cyclone_adapter import (
    discover_cyclone_inputs,
    resolve_product_input,
)


# ============================================================
# RENDERER REGISTRY
#
# Production modules register their actual plotting functions
# here. This keeps the shared operational framework independent
# from FNV3/FNV3-L implementation details.
# ============================================================

_RENDERERS = {}


def register_renderer(
    model,
    product,
    renderer,
):
    key = (
        str(model).strip().lower(),
        str(product).strip().lower(),
    )

    _RENDERERS[key] = renderer


def get_renderer(
    model,
    product,
):
    key = (
        str(model).strip().lower(),
        str(product).strip().lower(),
    )

    renderer = _RENDERERS.get(
        key
    )

    if renderer is None:
        raise KeyError(
            "No cyclone renderer registered for "
            f"{key[0]} / {key[1]}"
        )

    return renderer


def render_cyclone_frame(
    *,
    request,
    output_path,
):
    bundle = discover_cyclone_inputs(
        request.model,
        date=request.date,
        hour=request.hour,
    )

    try:
        source = resolve_product_input(
            bundle,
            request.product,
        )
    except FileNotFoundError:
        # Operational FNV3 uses a WeatherLab ATCF A-deck.
        # If the generic cyclone bundle does not classify that
        # text file as an ensemble input, resolve the exact cycle
        # directly instead of failing before the FNV3 renderer.
        if str(request.model).lower() != "fnv3":
            raise

        cycle_dir = (
            f"{request.date}{str(request.hour).zfill(2)}"
        )

        candidates = []

        for root in (
            Path("fnv3_cyclone/output/raw"),
            Path("/app/fnv3_cyclone/output/raw"),
        ):
            exact = root / cycle_dir

            if exact.exists():
                candidates.extend(
                    exact.glob("*atcf*a_deck*.txt")
                )
                candidates.extend(
                    exact.glob("*atcf*.txt")
                )

        candidates = list(dict.fromkeys(candidates))

        if not candidates:
            raise FileNotFoundError(
                "No FNV3 ATCF source found for "
                f"{request.date}{request.hour}"
            )

        source = max(
            candidates,
            key=lambda x: x.stat().st_mtime,
        )

    renderer = get_renderer(
        request.model,
        request.product,
    )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = renderer(
        source=source,
        bundle=bundle,
        request=request,
        output_path=output_path,
    )

    if not output_path.exists():
        raise RuntimeError(
            "Cyclone renderer returned without "
            f"creating {output_path}"
        )

    return (
        result
        if result is not None
        else output_path
    )


def registered_products(
    model,
):
    model = (
        str(model)
        .strip()
        .lower()
    )

    return tuple(
        product
        for (
            registered_model,
            product,
        ) in _RENDERERS
        if registered_model == model
    )


def operational_products(
    model,
):
    """
    Products that have an actual registered production renderer.

    This deliberately prevents a configured-but-unimplemented
    product from entering an operational cycle.
    """

    return tuple(
        sorted(
            registered_products(
                model
            )
        )
    )
