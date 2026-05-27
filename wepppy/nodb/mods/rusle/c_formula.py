"""Shared RUSLE C-factor math helpers."""

from __future__ import annotations

from typing import Any

import numpy as np


__all__ = [
    "compute_c_from_fg_pct",
    "compute_c_from_ground_cover_fraction",
    "compute_fg_from_bare_ground_pct",
    "compute_observed_rap_fg_pct",
]


def _return_scalar_if_needed(original: Any, value: np.ndarray) -> float | np.ndarray:
    if np.isscalar(original):
        return float(value.reshape(()))
    return value


def compute_fg_from_bare_ground_pct(bare_ground_pct: float | np.ndarray) -> float | np.ndarray:
    """Return net ground cover percent from bare-ground percent.

    The locked v1 contract is:

    `fg = clamp(100 - bare_ground_pct, 0, 100)`
    """

    bare = np.asarray(bare_ground_pct, dtype=np.float64)
    fg = np.full_like(bare, np.nan, dtype=np.float64)

    valid = np.isfinite(bare)
    fg[valid] = np.clip(100.0 - bare[valid], 0.0, 100.0)

    return _return_scalar_if_needed(bare_ground_pct, fg)


def compute_observed_rap_fg_pct(
    bare_ground_pct: float | np.ndarray,
    *,
    rock_fraction_of_rap_bare: float | np.ndarray = 0.0,
) -> float | np.ndarray:
    """Return observed-RAP ground-cover percent with rock-partitioned bare ground.

    Locked v1 contract:

    `fg = 100 * (1 - bare_rap_0_1 * (1 - r_bare))`

    where:
    - `bare_rap_0_1 = clamp(bare_ground_pct / 100, 0, 1)`
    - `r_bare = clamp(rock_fraction_of_rap_bare, 0, 1)`
    """

    bare = np.asarray(bare_ground_pct, dtype=np.float64)
    rock_fraction = np.asarray(rock_fraction_of_rap_bare, dtype=np.float64)
    if rock_fraction.ndim == 0:
        rock_fraction = np.full_like(bare, float(rock_fraction), dtype=np.float64)
    else:
        try:
            rock_fraction = np.broadcast_to(rock_fraction, bare.shape).astype(np.float64, copy=False)
        except ValueError as exc:
            raise ValueError(
                "rock_fraction_of_rap_bare must be scalar or broadcastable to bare_ground_pct shape"
            ) from exc
    fg = np.full_like(bare, np.nan, dtype=np.float64)

    valid_bare = np.isfinite(bare)
    valid_rock = np.isfinite(rock_fraction)
    if not np.all(valid_rock):
        raise ValueError("rock_fraction_of_rap_bare must be finite")
    if np.any((rock_fraction < 0.0) | (rock_fraction > 1.0)):
        raise ValueError("rock_fraction_of_rap_bare must be within [0, 1]")

    bare_0_1 = np.full_like(bare, np.nan, dtype=np.float64)
    bare_0_1[valid_bare] = np.clip(bare[valid_bare] / 100.0, 0.0, 1.0)
    fg[valid_bare] = 100.0 * (1.0 - (bare_0_1[valid_bare] * (1.0 - rock_fraction[valid_bare])))

    return _return_scalar_if_needed(bare_ground_pct, fg)


def compute_c_from_fg_pct(fg_pct: float | np.ndarray, *, b: float = 0.04) -> float | np.ndarray:
    """Return `C = exp(-b * fg)` for ground cover percent."""

    if b <= 0.0:
        raise ValueError(f"RUSLE C decay parameter must be > 0, got {b}")

    fg = np.asarray(fg_pct, dtype=np.float64)
    c = np.full_like(fg, np.nan, dtype=np.float64)

    valid = np.isfinite(fg)
    c[valid] = np.exp(-b * fg[valid])

    return _return_scalar_if_needed(fg_pct, c)


def compute_c_from_ground_cover_fraction(
    ground_cover_fraction: float | np.ndarray,
    *,
    b: float = 0.04,
) -> float | np.ndarray:
    """Convert a 0-1 ground-cover fraction into `C` using the v1 contract."""

    ground_cover = np.asarray(ground_cover_fraction, dtype=np.float64)
    valid = np.isfinite(ground_cover)

    if np.any((ground_cover[valid] < 0.0) | (ground_cover[valid] > 1.0)):
        raise ValueError("Ground-cover fraction must be within [0, 1]")

    fg_pct = np.full_like(ground_cover, np.nan, dtype=np.float64)
    fg_pct[valid] = ground_cover[valid] * 100.0

    return compute_c_from_fg_pct(fg_pct, b=b)
