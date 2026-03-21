from __future__ import annotations

import numpy as np
import pytest

from wepppy.nodb.mods.rusle.k_epic import compute_polaris_epic_k, organic_matter_to_organic_carbon


pytestmark = pytest.mark.unit


def test_organic_matter_to_organic_carbon_default_factor() -> None:
    om = np.asarray([0.0, 1.724, 3.448, 20.0])
    oc = organic_matter_to_organic_carbon(om)

    assert np.isclose(oc[0], 0.0)
    assert np.isclose(oc[1], 1.0)
    assert np.isclose(oc[2], 2.0)
    assert oc[3] <= 20.0


def test_compute_polaris_epic_k_returns_finite_in_range() -> None:
    sand = np.asarray([[45.0, 60.0], [35.0, 70.0]])
    silt = np.asarray([[35.0, 25.0], [45.0, 15.0]])
    clay = np.asarray([[20.0, 15.0], [20.0, 15.0]])
    om = np.asarray([[3.5, 2.5], [4.0, 1.5]])

    k = compute_polaris_epic_k(
        sand_pct=sand,
        silt_pct=silt,
        clay_pct=clay,
        om_pct=om,
    )

    assert k.shape == sand.shape
    assert np.all(np.isfinite(k))
    assert np.all(k >= 0.0)
    assert np.all(k <= 1.0)


def test_compute_polaris_epic_k_propagates_nodata() -> None:
    k = compute_polaris_epic_k(
        sand_pct=np.asarray([[45.0, np.nan]]),
        silt_pct=np.asarray([[35.0, 25.0]]),
        clay_pct=np.asarray([[20.0, 15.0]]),
        om_pct=np.asarray([[3.5, 2.5]]),
    )

    assert np.isfinite(k[0, 0])
    assert np.isnan(k[0, 1])
