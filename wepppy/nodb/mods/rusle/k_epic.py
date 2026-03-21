"""POLARIS EPIC-style K estimator helpers."""

from __future__ import annotations

from typing import Any

import numpy as np


__all__ = ["organic_matter_to_organic_carbon", "compute_polaris_epic_k"]


OM_TO_OC_FACTOR = 1.724


def _as_float_array(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=np.float64)


def organic_matter_to_organic_carbon(om_pct: Any, *, factor: float = OM_TO_OC_FACTOR) -> np.ndarray:
    """Convert organic matter percent to organic carbon percent."""
    om = np.clip(_as_float_array(om_pct), 0.0, 20.0)
    oc = np.divide(om, factor, out=np.zeros_like(om), where=factor != 0.0)
    return np.clip(oc, 0.0, 20.0)


def compute_polaris_epic_k(
    *,
    sand_pct: Any,
    silt_pct: Any,
    clay_pct: Any,
    om_pct: Any,
) -> np.ndarray:
    """Compute EPIC-style K estimate from texture + organic matter grids.

    Uses the widely applied Williams (1995) EPIC formulation.
    """
    sand = np.clip(_as_float_array(sand_pct), 0.0, 100.0)
    silt = np.clip(_as_float_array(silt_pct), 0.0, 100.0)
    clay = np.clip(_as_float_array(clay_pct), 0.0, 100.0)
    oc = organic_matter_to_organic_carbon(om_pct)

    sand_frac = sand / 100.0
    silt_frac = silt / 100.0
    clay_frac = clay / 100.0
    sn = np.clip(1.0 - sand_frac, 0.0, 1.0)

    fcsand = 0.2 + 0.3 * np.exp(-0.0256 * sand * (1.0 - silt_frac))

    silt_clay_sum = silt_frac + clay_frac
    fcl_si_ratio = np.divide(
        silt_frac,
        silt_clay_sum,
        out=np.zeros_like(silt_frac),
        where=silt_clay_sum > 0.0,
    )
    fcl_si = np.power(fcl_si_ratio, 0.3)

    forgc = 1.0 - (0.25 * oc) / (oc + np.exp(3.72 - 2.95 * oc))
    fhisand = 1.0 - (0.7 * sn) / (sn + np.exp(-5.51 + 22.9 * sn))

    k = fcsand * fcl_si * forgc * fhisand

    invalid = ~np.isfinite(sand) | ~np.isfinite(silt) | ~np.isfinite(clay) | ~np.isfinite(oc)
    k = np.where(invalid, np.nan, k)
    return np.clip(k, 0.0, 1.0)
