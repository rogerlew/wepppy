"""Lookup tables linking peak gust speeds to ash transport proportions."""

from __future__ import annotations

import csv
import os
from typing import Final, List

from os.path import join as _join

import numpy as np

_THISDIR = os.path.dirname(__file__)
_DATA_DIR = _join(_THISDIR, "data")

with open(_join(_DATA_DIR, "wind_transport_thresholds.csv"), encoding="utf-8") as _fp:
    _dict_reader = csv.DictReader(_fp)

    _wind_speeds: List[float] = []
    _white_w_pct: List[float] = []
    _black_w_pct: List[float] = []
    for _row in _dict_reader:
        _wind_speeds.append(float(_row["U' (m/s)"]))
        _white_w_pct.append(float(_row["Transported cum. White (w,%)"]))
        _black_w_pct.append(float(_row["Remaining cum. Black (w,%)"]))

_wind_speeds_arr: Final[np.ndarray] = np.array(_wind_speeds)


def _lookup_proportion(samples: List[float], wind_speed: float) -> float | None:
    """Return the interpolated proportion for ``wind_speed`` or ``None``."""
    for i, candidate in enumerate(_wind_speeds_arr[1:]):
        if candidate > wind_speed:
            return samples[i]
    return None


def lookup_wind_threshold_white_ash_proportion(wind_speed: float) -> float | None:
    """Fraction of transported cumulative white ash for a given wind speed."""
    return _lookup_proportion(_white_w_pct, wind_speed)


def lookup_wind_threshold_black_ash_proportion(wind_speed: float) -> float | None:
    """Fraction of remaining cumulative black ash for a given wind speed."""
    return _lookup_proportion(_black_w_pct, wind_speed)
