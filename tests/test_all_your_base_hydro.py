import numpy as np
import pytest

from wepppy.all_your_base.hydro import determine_wateryear, vec_determine_wateryear


def test_determine_wateryear_from_month() -> None:
    assert determine_wateryear(2020, month=9) == 2020
    assert determine_wateryear(2020, month=10) == 2021


def test_determine_wateryear_from_julian() -> None:
    assert determine_wateryear(2020, julian=273) == 2020  # end of September
    assert determine_wateryear(2020, julian=275) == 2021


def test_determine_wateryear_requires_month_or_julian() -> None:
    with pytest.raises(ValueError):
        determine_wateryear(2020)


def test_vec_determine_wateryear_matches_scalar_logic() -> None:
    years = np.array([2019, 2019, 2020])
    months = np.array([9, 10, 11])
    result = vec_determine_wateryear(years, month=months)
    expected = np.array([2019, 2020, 2021])
    np.testing.assert_array_equal(result, expected)

    julians = np.array([260, 274, 10])
    result_from_julian = vec_determine_wateryear(years, julian=julians)
    expected_from_julian = np.array([2019, 2020, 2020])
    np.testing.assert_array_equal(result_from_julian, expected_from_julian)


def test_vec_determine_wateryear_requires_one_argument() -> None:
    with pytest.raises(ValueError):
        vec_determine_wateryear(np.array([2020]))
