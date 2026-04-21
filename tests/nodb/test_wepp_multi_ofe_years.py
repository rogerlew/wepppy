from __future__ import annotations

import pytest

from wepppy.nodb.core.wepp import _coerce_sim_years

pytestmark = pytest.mark.unit


def test_coerce_sim_years_accepts_int() -> None:
    assert _coerce_sim_years(100) == 100


def test_coerce_sim_years_counts_iterable_years() -> None:
    assert _coerce_sim_years([2001, 2002, 2003]) == 3

