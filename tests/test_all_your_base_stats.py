import numpy as np
import pytest

from wepppy.all_your_base.stats import probability_of_occurrence, weibull_series


def test_probability_of_occurrence_returns_percentage_by_default() -> None:
    result = probability_of_occurrence(return_interval=10, period_of_interest=5)
    expected = (1.0 - (1.0 - 0.1) ** 5) * 100.0
    assert result == pytest.approx(expected)

    fractional = probability_of_occurrence(10, 5, pct=False)
    assert fractional == pytest.approx(expected / 100.0)


def test_weibull_series_cta_method() -> None:
    recurrence = [1, 5, 10]
    mapping = weibull_series(recurrence, years=2, method="cta")
    # Recurrence intervals greater than the available record length should be absent.
    assert set(mapping.keys()) == {1.0}
    assert 5.0 not in mapping
    assert 10.0 not in mapping

    total_days = int(round(2 * 365.25))
    ranks = np.arange(1, total_days + 1)
    periods = (total_days + 1) / ranks / 365.25
    # Verify the stored index satisfies the recurrence requirement.
    idx = mapping[1.0]
    period = periods[idx]
    assert period >= 1.0


def test_weibull_series_am_method_and_validation() -> None:
    recurrence = [2, 3]
    mapping = weibull_series(recurrence, years=5, method="am")
    assert set(mapping.keys()) == {2.0, 3.0}

    with pytest.raises(ValueError):
        weibull_series(recurrence, years=0)

    with pytest.raises(ValueError):
        weibull_series(recurrence, years=5, method="invalid")
