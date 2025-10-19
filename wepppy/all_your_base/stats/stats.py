"""Statistical helpers shared across WEPP analytics."""

from __future__ import annotations

from typing import Dict, Sequence

import numpy as np

__all__ = ['probability_of_occurrence', 'weibull_series']


def probability_of_occurrence(
    return_interval: float,
    period_of_interest: float,
    pct: bool = True,
) -> float:
    """Probability that an event with the given return interval occurs."""
    prob = 1.0 - (1.0 - 1.0 / return_interval) ** period_of_interest
    prob = min(max(prob, 0.0), 1.0)
    return prob * 100.0 if pct else prob


def weibull_series(
    recurrence: Sequence[float],
    years: float,
    method: str = 'cta',
    gringorten_correction: bool = False,
) -> Dict[float, int]:
    """Return order statistic ranks for a set of recurrence intervals."""
    if years <= 0:
        raise ValueError('years must be greater than zero.')

    if method == 'cta':
        count = int(round(years * 365.25))
    elif method == 'am':
        count = int(round(years))
    else:
        raise ValueError('method must be either "cta" or "am".')

    ranks = np.arange(1, count + 1, dtype=float)
    if gringorten_correction:
        periods = (count + 1.0) / (ranks - 0.44)
    else:
        periods = (count + 1.0) / ranks

    if method == 'cta':
        periods /= 365.25

    result: Dict[float, int] = {}
    for target in sorted(recurrence):
        for rank, period in zip(ranks[::-1], periods[::-1]):
            index = int(rank - 1)
            if period >= target and index not in result.values():
                result[float(target)] = index
                break
    return result
