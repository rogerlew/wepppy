from __future__ import annotations

"""Shared helpers for filtering interchange dataframes by DSS date ranges."""

from datetime import date, datetime
from typing import Tuple

import pandas as pd

DateLike = date | datetime

__all__ = ["apply_date_filters"]


def _decompose(value: DateLike) -> Tuple[int, int, int]:
    return value.year, value.month, value.day


def _inclusive_lower_mask(year, month, day, boundary: Tuple[int, int, int]):
    by, bm, bd = boundary
    return (
        (year > by)
        | ((year == by) & (month > bm))
        | ((year == by) & (month == bm) & (day >= bd))
    )


def _inclusive_upper_mask(year, month, day, boundary: Tuple[int, int, int]):
    by, bm, bd = boundary
    return (
        (year < by)
        | ((year == by) & (month < bm))
        | ((year == by) & (month == bm) & (day <= bd))
    )


def apply_date_filters(
    frame: pd.DataFrame,
    *,
    start: DateLike | None,
    end: DateLike | None,
    year_column: str = "year",
    month_column: str = "month",
    day_column: str = "day_of_month",
) -> pd.DataFrame:
    """Return a DataFrame slice constrained to the provided date range.

    Args:
        frame: Source dataframe containing date component columns.
        start: Inclusive start date. ``None`` disables the lower bound.
        end: Inclusive end date. ``None`` disables the upper bound.
        year_column: Name of the column containing year values.
        month_column: Name of the column containing month values.
        day_column: Name of the column containing day-of-month values.

    Returns:
        ``frame`` if no filtering is required, otherwise a filtered view.
    """

    if frame.empty or (start is None and end is None):
        return frame

    year = frame[year_column].astype(int, copy=False)
    month = frame[month_column].astype(int, copy=False)
    day = frame[day_column].astype(int, copy=False)

    mask = pd.Series(True, index=frame.index)

    if start is not None:
        mask &= _inclusive_lower_mask(year, month, day, _decompose(start))
    if end is not None:
        mask &= _inclusive_upper_mask(year, month, day, _decompose(end))

    if mask.all():
        return frame
    return frame.loc[mask]
