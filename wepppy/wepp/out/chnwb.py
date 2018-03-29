from os.path import exists as _exists
from datetime import datetime, timedelta
from collections import OrderedDict
import numpy as np
import os

from wepppy.all_your_base import parse_units

uint_types = ['OFE (#)', 'J', 'Y', 'M', 'D']
vars_collapse_ofe = ['Y', 'J', 'M', 'D', 'Date', 'P (mm)', 'P (mm)', 'Q (mm)', 'latqcc (mm)']
vars_collapse_time = ['Area (m^2)']


def parse_float(x):
    try:
        return float(x)
    except:
        return float('nan')


class AnnualWaterBalanceReport:
    def __init__(self, chnwb):
        
        self.header = ['Year', 'P (mm)', 'RM (mm)',
                       'Ep (mm)', 'Es (mm)', 'Er (mm)', 'Dp (mm)',
                       'Total-Soil Water (mm)', 'frozwt (mm)', 'Snow-Water (mm)',
                       'Tile (mm)', 'Irr (mm)', 'Q (mm)', 'latqcc (mm)']
        
        data = OrderedDict()

        for colname in self.header:
            data[colname] = []

        _data = chnwb.data
        area_w = _data['Area Weights']

        weighted_vars = ['RM (mm)', 'Ep (mm)', 'Es (mm)', 'Er (mm)', 'Dp (mm)',
                         'Total-Soil Water (mm)', 'frozwt (mm)',
                         'Snow-Water (mm)', 'Tile (mm)', 'Irr (mm)']

        last_ofe_vars = ['Q (mm)', 'latqcc (mm)']

        years = sorted(set(_data['Y'].flatten()))
        for year in years:
            indx = np.where(year == _data['Y'])[0]

            data['Year'].append(year)
            data['P (mm)'].append(np.sum(_data['P (mm)'][indx, :], axis=1))

            for k in weighted_vars:
                data[k].append(np.sum(_data[k][indx, :] * area_w, axis=1))

            for k in last_ofe_vars:
                data[k].append(_data[k][indx[-1], :])

        self.data = data

    @property
    def hdr(self):
        for colname in self.header:
            yield colname.split()[0]

    @property
    def units(self):
        for colname in self.header:
            yield parse_units(colname)

    def __iter__(self):
        data = self.data
        for i in range(len(data['Year'])):
            yield RowData(OrderedDict([(colname, np.sum(data[colname][i])) for colname in self.header]))


class RowData:
    def __init__(self, row):
        self.row = row

    def __iter__(self):
        for colname in self.row:
            value = float(self.row[colname])
            units = parse_units(colname)
            yield value, units


class Chnwb:
    def __init__(self, fname):
        assert _exists(fname)

        self.fname = fname

        # read datafile
        lines = []
        with open(self.fname) as f:
            lines = f.readlines()
        lines = [L.strip() for L in lines]

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
                    data[k].append(parse_float(v))

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
        self.total_area = total_area
        self.num_ofes = num_ofes

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


if __name__ == "__main__":
    wat = Chnwb('/geodata/weppcloud_runs/f26c3690-c491-478f-90f9-f6710abb2618/wepp/output/chnwb.txt')
    watbal = AnnualWaterBalanceReport(wat)

    print(list(watbal.hdr))
    print(list(watbal.units))

    for row in watbal:
        print(row)
        input()
