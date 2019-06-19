import csv
import os
from os.path import join as _join
import numpy as np

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


with open(_join(_data_dir, 'wind_transport_thresholds.csv')) as fp:
    dictReader = csv.DictReader(fp)

    _wind_speeds = []
    _white_w_pct = []
    _black_w_pct = []
    for row in dictReader:
        _wind_speeds.append(float(row["U' (m/s)"]))
        _white_w_pct.append(float(row["Transported cum. White (w,%)"]))
        _black_w_pct.append(float(row["Remaining cum. Black (w,%)"]))

_wind_speeds = np.array(_wind_speeds)


def lookup_wind_threshold_white_ash_proportion(w):
    """
    Returns the fraction of transported cummlative black Ash cooresponding to the wind value w

    :param w: windspeed in m/s
    :return: fraction_w
    """
    global _wind_speeds, _white_w_pct

    for i, _w in enumerate(_wind_speeds[1:]):
        if _w > w:
            return _white_w_pct[i]


def lookup_wind_threshold_black_ash_proportion(w):
    """
    Returns the fraction of remaining cumulative black ash cooresponding to the wind value w

    :param w: windspeed in m/s
    :return: fraction_w
    """
    global _wind_speeds, _black_w_pct

    for i, _w in enumerate(_wind_speeds[1:]):
        if _w > w:
            return _black_w_pct[i]
