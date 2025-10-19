"""Hydrology helpers for translating dates into water years."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__ = ['determine_wateryear', 'vec_determine_wateryear']


def determine_wateryear(year: int, julian: int | None = None, month: int | None = None) -> int:
    """Return the water year associated with a calendar date."""
    if julian is not None:
        month = int((datetime(int(year), 1, 1) + timedelta(int(julian) - 1)).month)

    if month is None:
        raise ValueError('Either julian or month must be supplied.')

    return int(year) + 1 if int(month) > 9 else int(year)


def vec_determine_wateryear(
    year: ArrayLike,
    julian: ArrayLike | None = None,
    month: ArrayLike | None = None,
) -> NDArray[np.int_]:
    """Vectorized :func:`determine_wateryear` operating on array-like inputs."""
    year_array = np.asarray(year)

    if julian is not None:
        julian_array = np.asarray(julian)
        month_array = np.vectorize(
            lambda y, j: int((datetime(int(y), 1, 1) + timedelta(int(j) - 1)).month)
        )(year_array, julian_array)
    elif month is not None:
        month_array = np.asarray(month)
    else:
        raise ValueError('Either julian or month must be supplied.')

    vectorized = np.vectorize(lambda y, m: determine_wateryear(int(y), month=int(m)))
    return vectorized(year_array, month_array)
