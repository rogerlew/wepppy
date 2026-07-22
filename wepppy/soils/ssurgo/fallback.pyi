from __future__ import annotations

from collections.abc import Iterable

FULL_SSURGO_DATASET: str


def full_ssurgo_mukey_raster_path() -> str: ...


def full_ssurgo_candidate_support(
    bounds_epsg5070: tuple[float, float, float, float],
    radius_m: float,
    invalid_mukeys: Iterable[int | str],
    valid_mukeys: Iterable[int | str],
) -> list[tuple[str, int]]: ...
