# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import join as _join
from os.path import exists as _exists
from datetime import datetime, timedelta
from glob import glob
from collections import OrderedDict
import numpy as np
import os

from wepppy.all_your_base import try_parse_float

uint_types = ['OFE (#)', 'J', 'Y', 'M', 'D']
vars_collapse_ofe = ['Y', 'J', 'M', 'D', 'Date', 'P (mm)', 'RM (mm)', 'Q (mm)',
                     'Ep (mm)', 'Es (mm)', 'Er (mm)', 'Dp (mm)', 'UpStrmQ (mm)',
                     'SubRIn (mm)', 'latqcc (mm)', 'Total-Soil Water (mm)',
                     'frozwt (mm)', 'Snow-Water (mm)', 'QOFE (mm)', 'Tile (mm)', 'Irr (mm)']
vars_collapse_time = ['Area (m^2)']


_nan = float('nan')


class HillWat:
    def __init__(self, fname):
        assert _exists(fname), fname

        self.fname = fname

        # read datafile
        lines = []
        with open(self.fname) as f:
            lines = f.readlines()
        lines = [L.strip() for L in lines]

        assert len(lines) > 19, fname

        # Read header
        i0, iend = self._find_headerlines(lines)
        header = [L.split() for L in lines[i0:iend]]
        header = zip(*header)
        header = [' '.join(tup) for tup in header]
        header = [h.replace(' -', '')
                   .replace('#', '(#)')
                   .replace(' mm', ' (mm)')
                   .replace('Water(mm)', 'Water (mm)')
                   .replace('m^2', '(m^2)')
                   .strip() for h in header]

        # iterate through the data
        ncols = len(header)
        data = dict([(h, []) for h in header])
        data['Date'] = []
        data['M'] = []
        data['D'] = []

        for L in lines[iend + 2:]:
            L = L.split()

            assert len(L) >= ncols

            for k, v in zip(header, L[:ncols]):
                if k in uint_types:
                    data[k].append(int(v))
                else:
                    data[k].append(try_parse_float(v, _nan))

            assert 'Y' in data, (data, lines)
            year = data['Y'][-1]
            julday = data['J'][-1]
            dt = datetime(year, 1, 1) + timedelta(julday - 1)
            data['Date'].append(np.datetime64(dt))
            data['M'].append(dt.month)
            data['D'].append(dt.day)

        # cast data values as np.arrays
        for (k, v) in data.items():
            dtype = (np.float32, np.int16)[any([k == s for s in uint_types])]
            if k == 'Date':
                dtype = np.datetime64
            data[k] = np.array(v, dtype=dtype)

        # reshape depending on number of ofes
        num_ofes = len(set(data['OFE (#)']))
        days_in_sim = int(len(data['OFE (#)']) / num_ofes)

        # pack the table data into numpy arrays
        for (k, v) in data.items():
            data[k] = np.reshape(data[k], (days_in_sim, num_ofes))

        # collapse to reduce redundancy
        for k in vars_collapse_ofe:
            data[k] = data[k][:, 0]
            data[k] = np.reshape(data[k], (days_in_sim, 1))

        for k in vars_collapse_time:
            data[k] = data[k][0, :]
            data[k] = np.reshape(data[k], (1, num_ofes))

        # Create array of Area weights
        total_area = np.sum(data['Area (m^2)'])
        data['Area Weights'] = data['Area (m^2)'] / total_area

        self.data = data
        self.header = header
        self.total_area = total_area
        self.num_ofes = num_ofes

    def as_dict(self):
        data = self.data
        header = data.keys()
        d = {}

        m, n = data['D'].shape
        for i in range(m):
            row = {k: data[k][i, 0] for k in header if 'Area' not in k}
            year = row['Y']
            month = row['M']
            day = row['D']
            d[(year, month, day)] = row

        return d

    def _find_headerlines(self, lines):
        i0 = None
        iend = None

        for i, L in enumerate(lines):
            s = L.strip()
            if s == '':
                continue

            if s[0] == '-':
                if i0 == None:
                    i0 = i
                else:
                    iend = i

        return i0 + 1, iend

def watershed_swe(wd):
    wat_fns = glob(_join(wd, 'wepp/output/*.wat.dat'))

    total_area = 0.0
    cumulative_swe = None
    for wat_fn in wat_fns:
        wat = HillWat(wat_fn)
        area = wat.data['Area (m^2)'][0]
        total_area += area
       
        # calc swe in m^3 
        swe = wat.data['Snow-Water (mm)'] * 0.001 * area
        if cumulative_swe is None:
            cumulative_swe = swe
        else:
            cumulative_swe += swe

    return cumulative_swe / total_area * 1000


if __name__ == "__main__":
    from pprint import pprint
    from glob import glob
    from os.path import join as _join

    import sys

    print(watershed_swe('/geodata/weppcloud_runs/srivas42-greatest-ballad'))
    sys.exit()

    test_wd = '/geodata/weppcloud_runs/srivas42-greatest-ballad/wepp/output'

    fns = glob(_join(test_wd, '*.wat.dat'))
    for fn in fns:
        print(fn)
        wat = HillWat(fn)
        pprint(wat.data.keys())
        input()
