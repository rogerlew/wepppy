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

import pandas as pd
from deprecated import deprecated

from wepppy.all_your_base import try_parse_float
from wepppy.all_your_base.hydro import determine_wateryear

uint_types = ['OFE (#)', 'J', 'Y', 'M', 'D']
vars_collapse_ofe = ['Y', 'J', 'M', 'D', 'Date', 'P (mm)', 'RM (mm)', 
                     'Ep (mm)', 'Es (mm)', 'Er (mm)', 'Dp (mm)', 
                     'Snow-Water (mm)',]  # value across OFEs is the same for each day (not calculated by OFE)
vars_collapse_time = ['Area (m^2)']   # value of these repeat for every day


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
        data['Water Year'] = []

        date_indx = []

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
            julian = data['J'][-1]
            wy = determine_wateryear(year, julian)
            ofe = data['OFE (#)'][-1]
            dt = datetime(year, 1, 1) + timedelta(julian - 1)
            data['Date'].append(np.datetime64(dt))
            data['M'].append(dt.month)
            data['D'].append(dt.day)
            data['Water Year'].append(wy)

            if ofe == 1:
                date_indx.append((year, dt.month, dt.day, julian, wy))

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
        self.days_in_sim = days_in_sim

        date_indx = np.array(date_indx)
        self._year_indx = date_indx[:, 0]
        self._month_indx = date_indx[:,1]
        self._day_indx = date_indx[:,2]
        self._julian_indx = date_indx[:,3]
        self._wy_indx = date_indx[:,4]
        self.watbal = None
                       
    def as_dict(self):
        if self.num_ofes > 1:
            raise NotImplementedError()

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

    def _calculate_daily_watbal(self, watbal_measures, units='m^3'):
        assert units in ('m^3', 'mm')
        days_in_sim = self.days_in_sim
        ofe_areas = self.data['Area (m^2)']
        total_area = self.total_area
        num_ofes = self.num_ofes
        data = self.data

        d = pd.DataFrame()
        d['Year'] = self._year_indx
        d['Month'] = self._month_indx
        d['Day'] = self._day_indx
        d['Julian'] = self._julian_indx
        d['Water Year'] = self._wy_indx
        
        for _vars in watbal_measures:
           key = f'{_vars} ({units})' 
           d[key] = np.zeros(days_in_sim)
           for var in _vars.split('+'):
               var_mm = f'{var} (mm)'
               assert var_mm in self.data, f'{var_mm} not in self.data'
               if var_mm in vars_collapse_ofe:
                   y = data[var_mm] * total_area
               else:
                   y = np.sum(data[var_mm] * ofe_areas, axis=1)
               y = np.reshape(y, (-1, 1))
               d[key] += y[:, 0]
          
           if units == 'm^3':
               d[key] *= 0.001        
           else:
#               d[key] *= 0.001  # m^3
               d[key] /= total_area  # m
#               d[key] *= 1000.0  # to mm
        
        return d
      
    def calculate_daily_watbal(self, watbal_measures=
        ('P', 'RM', 'Ep', 'Es+Er', 'Dp', 'QOFE', 
         'latqcc', 'Total-Soil Water', 'Snow-Water')):
        return  self._calculate_daily_watbal(watbal_measures)

    def calculate_annual_watbal(self, watbal_measures=
        ('P', 'QOFE', 'latqcc', 'Ep+Es+Er', 'Dp'), units='mm'):

        watbal = self._calculate_daily_watbal(watbal_measures, units=units)

        total_area = self.total_area

        d = watbal.pivot_table(index='Water Year', 
                               values=[f'{m} (mm)' for m in watbal_measures], 
                               aggfunc='sum')
        return d 


@deprecated
def watershed_swe(wd):
    wat_fns = glob(_join(wd, 'wepp/output/*.wat.dat'))

    total_area = 0.0
    cumulative_swe = None
    for wat_fn in wat_fns:
        wat = HillWat(wat_fn)
        area = wat.total_area
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
