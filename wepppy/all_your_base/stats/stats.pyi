from __future__ import annotations

from typing import Dict, Sequence

__all__: list[str]


def probability_of_occurrence(
    return_interval: float,
    period_of_interest: float,
    pct: bool = ...,
) -> float: ...


def weibull_series(
    recurrence: Sequence[float],
    years: float,
    method: str = ...,
    gringorten_correction: bool = ...,
) -> Dict[float, int]: ...
