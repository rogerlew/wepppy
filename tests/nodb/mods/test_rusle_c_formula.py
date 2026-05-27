from __future__ import annotations

import numpy as np
import pytest

from wepppy.nodb.mods.rusle.c_formula import (
    compute_c_from_fg_pct,
    compute_c_from_ground_cover_fraction,
    compute_fg_from_bare_ground_pct,
    compute_observed_rap_fg_pct,
)


pytestmark = pytest.mark.unit


def test_compute_fg_from_bare_ground_pct_clamps_and_inverts() -> None:
    bare_ground = np.asarray([-10.0, 0.0, 25.0, 100.0, 110.0, np.nan])
    fg = compute_fg_from_bare_ground_pct(bare_ground)

    assert np.allclose(fg[:5], np.asarray([100.0, 100.0, 75.0, 0.0, 0.0]))
    assert np.isnan(fg[5])


def test_compute_c_from_fg_pct_matches_locked_formula() -> None:
    fg = np.asarray([0.0, 30.0, 60.0, 100.0])
    c = compute_c_from_fg_pct(fg)
    expected = np.exp(-0.04 * fg)

    assert np.allclose(c, expected)


def test_compute_c_from_ground_cover_fraction_validates_bounds() -> None:
    assert compute_c_from_ground_cover_fraction(0.6) == pytest.approx(np.exp(-0.04 * 60.0))

    with pytest.raises(ValueError, match="within \\[0, 1\\]"):
        compute_c_from_ground_cover_fraction(1.2)


def test_compute_observed_rap_fg_pct_applies_rock_partition() -> None:
    bare_ground = np.asarray([0.0, 25.0, 50.0, 100.0, 110.0, np.nan])
    fg = compute_observed_rap_fg_pct(bare_ground, rock_fraction_of_rap_bare=0.5)

    expected = np.asarray([100.0, 87.5, 75.0, 50.0, 50.0, np.nan])
    assert np.allclose(fg[:5], expected[:5])
    assert np.isnan(fg[5])


def test_compute_observed_rap_fg_pct_validates_rock_fraction_bounds() -> None:
    with pytest.raises(ValueError, match="within \\[0, 1\\]"):
        compute_observed_rap_fg_pct(50.0, rock_fraction_of_rap_bare=1.1)


def test_compute_observed_rap_fg_pct_accepts_array_rock_fraction() -> None:
    bare_ground = np.asarray([[50.0, 50.0], [50.0, 50.0]])
    rock_fraction = np.asarray([[0.0, 0.25], [0.5, 1.0]])

    fg = compute_observed_rap_fg_pct(bare_ground, rock_fraction_of_rap_bare=rock_fraction)

    expected = np.asarray([[50.0, 62.5], [75.0, 100.0]])
    assert np.allclose(fg, expected)
