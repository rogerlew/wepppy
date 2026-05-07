"""POLARIS nominal RUSLE-facing (nomograph-like) K estimator."""

from __future__ import annotations

from typing import Any

import numpy as np


__all__ = [
    "estimate_vfs_pct",
    "infer_structure_code",
    "infer_permeability_class",
    "compute_polaris_nomograph_k",
]


def _as_float_array(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=np.float64)


def estimate_vfs_pct(sand_pct: Any) -> np.ndarray:
    """Estimate very-fine-sand percent from sand percent using RUSLE2 fallback."""
    sand = np.clip(_as_float_array(sand_pct), 0.0, 100.0)
    vfs_pct = 0.74 * sand - 0.0062 * np.square(sand)
    return np.clip(vfs_pct, 0.0, sand)


def infer_structure_code(clay_pct: Any, sand_pct: Any) -> np.ndarray:
    """Infer a modeled structure code from texture proxies.

    Codes are aligned to the nomograph class range (1-4) and are explicitly
    modeled, not observed NRCS structure classes.
    """
    clay = _as_float_array(clay_pct)
    sand = _as_float_array(sand_pct)
    structure = np.full(np.broadcast(clay, sand).shape, 3.0, dtype=np.float64)

    structure = np.where(clay >= 40.0, 1.0, structure)
    structure = np.where((clay >= 27.0) & (clay < 40.0), 2.0, structure)
    structure = np.where((sand >= 70.0) & (clay <= 15.0), 4.0, structure)

    invalid = ~np.isfinite(clay) | ~np.isfinite(sand)
    structure = np.where(invalid, np.nan, structure)
    return structure


def infer_permeability_class(ksat_cm_hr: Any) -> np.ndarray:
    """Infer permeability class (1-6) from Ksat in cm/hr.

    The class thresholds are a modeled mapping contract for gridded inputs.
    """
    ksat = _as_float_array(ksat_cm_hr)
    permeability = np.full(ksat.shape, 1.0, dtype=np.float64)

    permeability = np.where(ksat <= 20.0, 2.0, permeability)
    permeability = np.where(ksat <= 6.0, 3.0, permeability)
    permeability = np.where(ksat <= 2.0, 4.0, permeability)
    permeability = np.where(ksat <= 0.5, 5.0, permeability)
    permeability = np.where(ksat <= 0.13, 6.0, permeability)

    permeability = np.where(~np.isfinite(ksat), np.nan, permeability)
    return permeability


def compute_polaris_nomograph_k(
    *,
    sand_pct: Any,
    silt_pct: Any,
    clay_pct: Any,
    om_pct: Any,
    ksat_cm_hr: Any,
    permeability_class_override: Any | None = None,
) -> np.ndarray:
    """Compute a nomograph-like K estimate from POLARIS-like gridded inputs.

    Inputs are expected in percent units (`sand`, `silt`, `clay`, `om`) and
    linear `ksat_cm_hr`. Output K is clamped to [0, 1].
    """
    sand = np.clip(_as_float_array(sand_pct), 0.0, 100.0)
    silt = np.clip(_as_float_array(silt_pct), 0.0, 100.0)
    clay = np.clip(_as_float_array(clay_pct), 0.0, 100.0)
    om = np.clip(_as_float_array(om_pct), 0.0, 20.0)
    ksat = np.clip(_as_float_array(ksat_cm_hr), 0.0, None)

    vfs = estimate_vfs_pct(sand)
    structure = infer_structure_code(clay, sand)
    if permeability_class_override is None:
        permeability = infer_permeability_class(ksat)
    else:
        permeability = np.clip(_as_float_array(permeability_class_override), 1.0, 6.0)
        permeability = np.where(~np.isfinite(permeability), np.nan, permeability)

    texture_term = (silt + vfs) * (100.0 - clay)
    texture_term = np.clip(texture_term, 0.0, None)

    k = (
        2.1e-4 * np.power(texture_term, 1.14) * (12.0 - om)
        + 3.25 * (structure - 2.0)
        + 2.5 * (permeability - 3.0)
    ) / 100.0

    invalid = (
        ~np.isfinite(sand)
        | ~np.isfinite(silt)
        | ~np.isfinite(clay)
        | ~np.isfinite(om)
        | ~np.isfinite(ksat)
    )
    k = np.where(invalid, np.nan, k)
    return np.clip(k, 0.0, 1.0)
