from __future__ import annotations

"""Utility helpers for parsing and formatting DSS date ranges.

The DSS export workflow needs to support both observed climates that use
calendar years (e.g., 2000) and stochastic climates that use simulation-year
indices (e.g., 1, 2, 3).  Python's :class:`datetime.date` supports the full range
of year values we care about, so we normalize user input to ``date`` objects and
serialize them using a consistent ``MM/DD/YYYY`` format.
"""

from datetime import date, datetime
import re
from typing import Iterable

__all__ = ["DATE_DISPLAY_FORMAT", "parse_dss_date", "format_dss_date"]

DATE_DISPLAY_FORMAT = "%m/%d/%Y"
_DATE_TOKEN_RE = re.compile(r"(\d+)")


def _coerce_date_tokens(value: str) -> tuple[int, int, int]:
    tokens = [token for token in _DATE_TOKEN_RE.findall(value) if token]
    if len(tokens) != 3:
        raise ValueError("DSS dates must include month, day, and year components")
    month, day, year = (int(token) for token in tokens[:3])
    return month, day, year


def parse_dss_date(value: str | date | datetime | None) -> date | None:
    """Parse a DSS date value.

    Args:
        value: User-supplied date. Accepts ``None``/empty strings, ``date`` or
            ``datetime`` objects, or free-form strings containing three numeric
            tokens (month/day/year) separated by any delimiter.

    Returns:
        ``datetime.date`` when parsing succeeds, otherwise ``None`` for blank
        inputs.

    Raises:
        ValueError: If the value cannot be interpreted as a valid calendar date.
    """

    if value in (None, "", False):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        return None

    month, day, year = _coerce_date_tokens(text)
    return date(year, month, day)


def format_dss_date(value: date | None) -> str | None:
    """Serialize a ``datetime.date`` using the standard display format."""

    if value is None:
        return None
    return value.strftime(DATE_DISPLAY_FORMAT)
