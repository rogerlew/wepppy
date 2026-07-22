"""Low-level, read-only support for SSURGO fallback research and selection."""

from __future__ import annotations

import os
from collections.abc import Iterable
from os.path import isfile
from os.path import join as _join
from typing import List, Tuple


FULL_SSURGO_DATASET = "ssurgo/gNATSGSO/2025"


def full_ssurgo_mukey_raster_path() -> str:
    """Return the canonical full 2025 gNATSGO MUKEY VRT.

    Candidate support must be drawn from the complete map, never a run-cropped
    SSURGO raster. ``GEODATA_DIR`` is the container/host geodata mount.
    """
    geodata_dir = os.environ.get("GEODATA_DIR", "/geodata")
    raster_path = _join(geodata_dir, FULL_SSURGO_DATASET, ".vrt")
    if not isfile(raster_path):
        raise FileNotFoundError(
            "Full 2025 gNATSGO MUKEY VRT is required for SSURGO fallback "
            f"candidate support: {raster_path}"
        )
    return raster_path


def _mukey_number(mukey: int | str) -> int:
    try:
        return int(str(mukey).split("-", 1)[0])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"MUKEY must begin with an integer: {mukey!r}") from exc


def full_ssurgo_candidate_support(
    bounds_epsg5070: Tuple[float, float, float, float],
    radius_m: float,
    invalid_mukeys: Iterable[int | str],
    valid_mukeys: Iterable[int | str],
) -> List[Tuple[str, int]]:
    """Return buildable donor MUKEY support from one full-map bounded crop.

    ``bounds_epsg5070`` must describe the source area in the full gNATSGO
    raster's CRS. All supplied invalid MUKEYs are excluded, which lets callers
    query an adjacent invalid cluster without admitting another invalid donor.
    """
    try:
        from wepppyo3.raster_characteristics import categorical_support_within_bounds
    except ImportError as exc:
        raise RuntimeError(
            "wepppyo3 categorical support is required for SSURGO fallback candidate support"
        ) from exc

    valid_by_number: dict[int, str] = {}
    for mukey in valid_mukeys:
        numeric_mukey = _mukey_number(mukey)
        canonical_mukey = str(mukey)
        previous = valid_by_number.setdefault(numeric_mukey, canonical_mukey)
        if previous != canonical_mukey:
            raise ValueError(
                f"Ambiguous buildable MUKEY values for {numeric_mukey}: "
                f"{previous!r}, {canonical_mukey!r}"
            )

    support = categorical_support_within_bounds(
        full_ssurgo_mukey_raster_path(),
        bounds_epsg5070,
        radius_m,
        excluded_values={_mukey_number(mukey) for mukey in invalid_mukeys},
    )
    candidates = [
        (valid_by_number[mukey], pixel_support)
        for mukey, pixel_support in support
        if mukey in valid_by_number
    ]
    return sorted(candidates, key=lambda item: (-item[1], _mukey_number(item[0]), item[0]))
