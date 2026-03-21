from __future__ import annotations

import numpy as np
import pytest

from wepppy.nodb.mods.rusle.k_nomograph import (
    compute_polaris_nomograph_k,
    estimate_vfs_pct,
    infer_permeability_class,
    infer_structure_code,
)


pytestmark = pytest.mark.unit


def test_estimate_vfs_pct_clamps_to_sand_bounds() -> None:
    sand = np.asarray([0.0, 20.0, 80.0, 120.0])
    vfs = estimate_vfs_pct(sand)

    assert np.all(vfs >= 0.0)
    assert np.all(vfs <= np.clip(sand, 0.0, 100.0))


def test_infer_structure_code_texture_contract() -> None:
    clay = np.asarray([45.0, 30.0, 10.0, 20.0])
    sand = np.asarray([20.0, 30.0, 75.0, 40.0])

    structure = infer_structure_code(clay, sand)

    assert np.array_equal(structure, np.asarray([1.0, 2.0, 4.0, 3.0]))


def test_infer_permeability_class_ksat_contract() -> None:
    ksat = np.asarray([0.05, 0.2, 1.0, 5.0, 10.0, 30.0])
    permeability = infer_permeability_class(ksat)

    assert np.array_equal(permeability, np.asarray([6.0, 5.0, 4.0, 3.0, 2.0, 1.0]))


def test_compute_polaris_nomograph_k_returns_finite_in_range() -> None:
    sand = np.asarray([[45.0, 60.0], [35.0, 70.0]])
    silt = np.asarray([[35.0, 25.0], [45.0, 15.0]])
    clay = np.asarray([[20.0, 15.0], [20.0, 15.0]])
    om = np.asarray([[3.5, 2.5], [4.0, 1.5]])
    ksat = np.asarray([[4.0, 8.0], [2.0, 30.0]])

    k = compute_polaris_nomograph_k(
        sand_pct=sand,
        silt_pct=silt,
        clay_pct=clay,
        om_pct=om,
        ksat_cm_hr=ksat,
    )

    assert k.shape == sand.shape
    assert np.all(np.isfinite(k))
    assert np.all(k >= 0.0)
    assert np.all(k <= 1.0)


def test_compute_polaris_nomograph_k_propagates_nodata() -> None:
    sand = np.asarray([[45.0, np.nan]])
    silt = np.asarray([[35.0, 25.0]])
    clay = np.asarray([[20.0, 15.0]])
    om = np.asarray([[3.5, 2.5]])
    ksat = np.asarray([[4.0, 8.0]])

    k = compute_polaris_nomograph_k(
        sand_pct=sand,
        silt_pct=silt,
        clay_pct=clay,
        om_pct=om,
        ksat_cm_hr=ksat,
    )

    assert np.isfinite(k[0, 0])
    assert np.isnan(k[0, 1])
