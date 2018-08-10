# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.


from os.path import join as _join
from os.path import exists as _exists

from collections import OrderedDict

from glob import glob

import numpy as np

from wepppy.all_your_base import parse_units, RowData
from .report_base import ReportBase


class TotalWatbal(ReportBase):
    def __init__(self, totalwatsed, exclude_yr_indxs=[0, 1]):
        self.totalwatsed = totalwatsed
        self.exclude_yr_indxs = exclude_yr_indxs

        header = ['Water Year', 'Precipitation (mm)', 'Rain + Melt (mm)',
                  'Streamflow (mm)', 'ET (mm)', 'Percolation (mm)',
                  'Storage (mm)', 'Sed. Del (tonne)']

        d = self.totalwatsed.d

        if 'Total P (kg)' in d:
            header.append('Total P (kg)')

        if 'Particulate P (kg)' in d:
            header.append('Particulate P (kg)')

        if 'Soluble Reactive P (kg)' in d:
            header.append('Soluble Reactive P (kg)')

        exclude_yr_indxs = self.exclude_yr_indxs

        wateryears = sorted(set(d['Water Year']))
        excluded_years = [wateryears[i] for i in exclude_yr_indxs]
        wyr_array = np.array(d['Water Year'])

        data = []
        yearlies = {}
        for k in header[1:]:
            yearlies[k] = []

        store_wat_yr0 = None
        store_wat_yrend = None

        for year in wateryears:
            if year in excluded_years:
                continue

            indx = np.where(wyr_array == year)[0]
            i0, iend = indx[0], indx[-1]

            store_wat_yrend = d['Storage (mm)'][iend]
            if store_wat_yr0 is None:
                store_wat_yr0 = store_wat_yrend

            row = OrderedDict([('WaterYear', int(year))])
            for k in header[1:]:
                if k in ['Storage (mm)']:
                    x = d[k][iend]
                else:
                    x = np.sum(d[k][i0:iend])
                row[k] = x
                yearlies[k].append(x)

            data.append(row)

        means = OrderedDict([('Water Year', 'Mean')])
        stdevs = OrderedDict([('Water Year', 'StdDev')])
        pratios = OrderedDict([('Water Year', '{X}/P'),
                               ('Precipitation (mm)', '')])

        psum = np.sum(yearlies['Precipitation (mm)'])
        for k in header[1:]:
            means[k] = np.mean(yearlies[k])
            stdevs[k] = np.std(yearlies[k])

            if k in ['Rain + Melt (mm)', 'Streamflow (mm)',
                     'ET (mm)', 'Percolation (mm)']:
                pratios[k.replace('(mm)', '(%)')] = np.sum(yearlies[k]) / psum * 100.0
            elif k in ['Storage (mm)']:
                pratios[k.replace('(mm)', '(%)')] = (store_wat_yrend - store_wat_yr0) / psum * 100.0
            else:
                pratios[k] = ''

        self.header = header
        self.data = data
        self._means = means
        self._stdevs = stdevs
        self._pratios = pratios

    @property
    def means(self):
        return RowData(self._means)

    @property
    def stdevs(self):
        return RowData(self._stdevs)

    @property
    def pratios(self):
        return RowData(self._pratios)

    def __iter__(self):
        for row in self.data:
            yield RowData(row)

