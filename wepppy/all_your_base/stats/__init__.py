"""Small statistical helper re-exports."""

from __future__ import annotations

from .stats import probability_of_occurrence, weibull_series

__all__: list[str] = ['probability_of_occurrence', 'weibull_series']
