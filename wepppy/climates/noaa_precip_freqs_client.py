import ast
import logging

import requests

import numpy as np

from wepppy.all_your_base import try_parse_float
from deprecated import deprecated

LOGGER = logging.getLogger(__name__)
PFDS_URL = (
    'https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py'
    '?lat={lat}&lon={lon}&type=pf&data=depth&units=english&series=pds'
)


def _eval(line):
    tbl = ast.literal_eval(line.split('=')[-1]
                           .replace(';', '')
                           .strip())

    return [[try_parse_float(v) for v in row] for row in tbl]

@deprecated(reason="This client is deprecated.")
def fetch_pf(lat, lng):
    try:
        r = requests.get(PFDS_URL.format(lat=lat, lon=lng), timeout=20)
    except requests.RequestException as exc:
        LOGGER.warning(
            "NOAA PFDS request failed for lat=%s lon=%s: %s",
            lat,
            lng,
            exc,
        )
        return None

    if r.status_code != 200:
        LOGGER.warning(
            "NOAA PFDS returned status %s for lat=%s lon=%s",
            r.status_code,
            lat,
            lng,
        )
        return None

    lines = [line.strip() for line in r.text.split('\n') if line.strip()]

    quantiles, upper, lower = None, None, None
    for line in lines:
        if line.startswith('result') and 'none' in line:
            return None

        if line.startswith('quantiles'):
            try:
                quantiles = _eval(line)
            except (ValueError, SyntaxError) as exc:
                LOGGER.warning(
                    "NOAA PFDS quantiles parse failed for lat=%s lon=%s: %s",
                    lat,
                    lng,
                    exc,
                )
                return None

        elif line.startswith('upper'):
            try:
                upper = _eval(line)
            except (ValueError, SyntaxError) as exc:
                LOGGER.warning(
                    "NOAA PFDS upper parse failed for lat=%s lon=%s: %s",
                    lat,
                    lng,
                    exc,
                )
                return None

        elif line.startswith('lower'):
            try:
                lower = _eval(line)
            except (ValueError, SyntaxError) as exc:
                LOGGER.warning(
                    "NOAA PFDS lower parse failed for lat=%s lon=%s: %s",
                    lat,
                    lng,
                    exc,
                )
                return None

    if quantiles is None or upper is None or lower is None:
        LOGGER.warning(
            "NOAA PFDS response missing expected tables for lat=%s lon=%s",
            lat,
            lng,
        )
        return None

    rec_intervals = [1, 2, 5, 10, 25, 50, 100, 200, 500, 1000]
    durations = ['5-min', '10-min', '15-min', '30-min', '60-min', '2-hour', '3-hour', '6-hour', '12-hour', '24-hour',
                 '2-day', '3-day', '4-day', '7-day', '10-day', '20-day', '30-day', '45-day', '60-day']

    expected_shape = (len(durations), len(rec_intervals))
    quantiles_shape = np.array(quantiles).shape
    upper_shape = np.array(upper).shape
    lower_shape = np.array(lower).shape

    if quantiles_shape != expected_shape or upper_shape != expected_shape or lower_shape != expected_shape:
        LOGGER.warning(
            "NOAA PFDS response shape mismatch for lat=%s lon=%s: "
            "quantiles=%s upper=%s lower=%s expected=%s",
            lat,
            lng,
            quantiles_shape,
            upper_shape,
            lower_shape,
            expected_shape,
        )
        return None

    return dict(rec_intervals=rec_intervals,
                durations=durations,
                quantiles=quantiles,
                upper=upper,
                lower=lower,
                units='in')


if __name__ == '__main__':
    import numpy as np
    from pprint import pprint

    def _duration_in_hours(duration):
        x, unit = duration.split('-')
        x = float(x)
        assert unit in ['min', 'hour', 'day']
        if unit == 'min':
            return x/60.0
        elif unit == 'day':
            return x*24.0
        return x

    pf = fetch_pf(lat=38.94443015887001, lng=-120.0772405129294)
    T = np.array(pf['quantiles']) * 25.4
    I = np.array(pf['quantiles']) * 25.4
    durations = pf['durations']

    for i, d in enumerate(durations):
        hours = _duration_in_hours(d)
        I[i, :] /= hours

    I = I.tolist()
    T = T.tolist()


