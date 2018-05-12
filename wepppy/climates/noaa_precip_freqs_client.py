import requests
import ast

import numpy as np

from wepppy.all_your_base import try_parse_float

url = 'https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py'\
      '?lat={lat}&lon={lon}&type=pf&data=depth&units=english&series=pds'


def _eval(line):
    tbl = ast.literal_eval(line.split('=')[-1]
                           .replace(';', '')
                           .strip())

    return [[try_parse_float(v) for v in row] for row in tbl]


def fetch_pf(lat, lng):
    r = requests.get(url.format(lat=lat, lon=lng))

    assert r.status_code == 200

    lines = r.text.split('\n')
    lines = [line.strip() for line in lines]

    quantiles, upper, lower = None, None, None
    for line in lines:
        if line.startswith('result'):
            if 'none' in line:
                return None

        if line.startswith('quantiles'):
            quantiles = _eval(line)

        elif line.startswith('upper'):
            upper = _eval(line)

        elif line.startswith('lower'):
            lower = _eval(line)

    rec_intervals = [1, 2, 5, 10, 25, 50, 100, 200, 500, 1000]
    durations = ['5-min', '10-min', '15-min', '30-min', '60-min', '2-hour', '3-hour', '6-hour', '12-hour', '24-hour',
                 '2-day', '3-day', '4-day', '7-day', '10-day', '20-day', '30-day', '45-day', '60-day']

    assert np.array(quantiles).shape == (len(durations), len(rec_intervals))
    assert np.array(upper).shape == (len(durations), len(rec_intervals))
    assert np.array(lower).shape == (len(durations), len(rec_intervals))

    return dict(rec_intervals=rec_intervals,
                durations=durations,
                quantiles=quantiles,
                upper=upper,
                lower=lower,
                units='in')


if __name__ == '__main__':
    import numpy as np

    def _duration_in_hours(duration):
        x, unit = duration.split('-')
        x = float(x)
        assert unit in ['min', 'hour', 'day']
        if unit == 'min':
            return x/60.0
        elif unit == 'day':
            return x*24.0
        return x

    pf = fetch_pf(lat=40.7367, lon=-110.5428)
    T = np.array(pf['quantiles']) * 25.4
    I = np.array(pf['quantiles']) * 25.4
    durations = pf['durations']

    for i, d in enumerate(durations):
        hours = _duration_in_hours(d)
        I[i, :] /= hours

    I = I.tolist()
    T = T.tolist()


    print(T)
    print(I)
    print(type(T[0][0]))



