from __future__ import annotations

import numpy as np
import pytest

from wepppy.nodb.mods.rusle.c_formula import (
    compute_c_from_fg_pct,
    compute_c_from_ground_cover_fraction,
    compute_fg_from_bare_ground_pct,
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

