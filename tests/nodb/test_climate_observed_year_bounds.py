from __future__ import annotations

import contextlib

import pytest

from wepppy.nodb.core.climate import Climate, ClimateMode

pytestmark = pytest.mark.unit


def test_require_observed_year_bounds_for_build_coerces_numeric_strings() -> None:
    climate = object.__new__(Climate)
    climate._observed_start_year = "1981"
    climate._observed_end_year = "2020"

    start_year, end_year = climate._require_observed_year_bounds_for_build()

    assert (start_year, end_year) == (1981, 2020)
    assert climate._observed_start_year == 1981
    assert climate._observed_end_year == 2020


def test_require_observed_year_bounds_for_build_rejects_non_integer_values() -> None:
    climate = object.__new__(Climate)
    climate._observed_start_year = ""
    climate._observed_end_year = "2020"

    with pytest.raises(ValueError, match="observed_start_year must be an integer year"):
        climate._require_observed_year_bounds_for_build()


@pytest.mark.parametrize(
    "mode",
    [
        ClimateMode.ObservedPRISM,
        ClimateMode.GridMetPRISM,
        ClimateMode.DepNexrad,
    ],
)
def test_set_observed_pars_validates_observed_modes(mode: ClimateMode) -> None:
    climate = object.__new__(Climate)
    climate._climate_mode = mode

    @contextlib.contextmanager
    def _locked():
        yield

    climate.locked = _locked  # type: ignore[attr-defined]

    with pytest.raises(AssertionError):
        climate.set_observed_pars(start_year="", end_year="2020")

    climate.set_observed_pars(start_year="1981", end_year="1982")
    assert climate._observed_start_year == 1981
    assert climate._observed_end_year == 1982
    assert climate._input_years == 2
