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

from collections import OrderedDict
import  numpy as np
from wepppy.all_your_base import parse_units, RowData

from .report_base import ReportBase

from wepppy.wepp.out import Chanwb

"""
class ChanWatbal2(ReportBase):
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
            i0, iend = indx[0], indx[-1]

            data['Year'].append(year)
            data['P (mm)'].append(np.sum(_data['P (mm)'][i0:iend, :], axis=1))

            for k in weighted_vars:
                data[k].append(np.sum(_data[k][i0:iend, :] * area_w, axis=1))

            for k in last_ofe_vars:
                data[k].append(_data[k][iend, :])

        self.data = data

    def yearly_iter(self):
        data = self.data
        for i in range(len(data['Year'])):
            yield RowData(OrderedDict([(colname, np.sum(data[colname][i])) for colname in self.header]))
"""


class ChannelWatbal(ReportBase):
    def __init__(self, wd):
        self.wd = wd

        from wepppy.nodb import Watershed
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        output_dir = _join(wd, 'wepp/output')

        chnwb_fn = _join(output_dir, 'chnwb.txt')
        chanwb_fn = _join(output_dir, 'chanwb.out')

        assert chnwb_fn
        assert chanwb_fn

        d = {}
        areas = {}
        years = set()

        with open(chnwb_fn) as chnwb_fp:
            chnwb_data = chnwb_fp.readlines()[25:]

        m = len(chnwb_data)

        for i, wl in enumerate(chnwb_data):
            OFE, J, Y, P, RM, Q, Ep, Es, Er, Dp, UpStrmQ, \
            SubRIn, latqcc, TSW, frozwt, SnowWater, QOFE, Tile, Irr, Surf, Base, Area = wl.split()

            OFE, J, Y, P, Ep, Es, Er, Dp, latqcc, TSW, Base, Area = \
                int(OFE), int(J), int(Y), float(P), float(Ep), float(Es), float(Er), float(Dp), \
                float(latqcc), float(TSW), float(Base), float(Area)

            try:
                Q = float(Q)
            except ValueError:
                Q = 0.0

            topaz_id = translator.top(chn_enum=OFE)

            areas[topaz_id] = Area
            years.add(Y)

            if topaz_id not in d:
                d[topaz_id] = {'Precipitation (mm)': {},
                               'Streamflow (mm)': {},
                               'Transpiration + Evaporation (mm)': {},
                               'Percolation (mm)': {},
                               'Total Soil Water Storage (mm)': {},
                               'Baseflow (mm)': {}}

            if Y not in d[topaz_id]['Precipitation (mm)']:
                d[topaz_id]['Precipitation (mm)'][Y] = P
                d[topaz_id]['Streamflow (mm)'][Y] = Q
                d[topaz_id]['Transpiration + Evaporation (mm)'][Y] = Ep + Es + Er
                d[topaz_id]['Percolation (mm)'][Y] = Dp
                d[topaz_id]['Total Soil Water Storage (mm)'][Y] = TSW
                d[topaz_id]['Baseflow (mm)'][Y] = Base
            else:
                d[topaz_id]['Precipitation (mm)'][Y] += P
                d[topaz_id]['Streamflow (mm)'][Y] += Q
                d[topaz_id]['Transpiration + Evaporation (mm)'][Y] += Ep + Es + Er
                d[topaz_id]['Percolation (mm)'][Y] += Dp
                d[topaz_id]['Total Soil Water Storage (mm)'][Y] += TSW
                d[topaz_id]['Baseflow (mm)'][Y] += Base

        self.chanwb = Chanwb(chanwb_fn)
        self.years = sorted(years)
        self.data = d
        self.areas = areas
        self.wsarea = float(np.sum(list(areas.values())))
        self.last_top = topaz_id

    @property
    def header(self):
        return list(self.data[self.last_top].keys())

    def daily_outlet_iter(self):
        chanwb = self.chanwb

        for i in chanwb.data['Julian']:
            row = OrderedDict([('Y', chanwb.data['Year'][i]),
                        ('J', chanwb.data['Julian'][i]),
                        ('Inflow', chanwb.data['Inflow'][i]),
                        ('Outflow', chanwb.data['Outflow'][i]),
                        ('Baseflow', chanwb.data['Baseflow'][i]),
                        ('Loss', chanwb.data['Loss'][i])])

            yield RowData(row)

    def yearly_outlet_iter(self):
        chanwb = self.chanwb

        years = self.years

        for y in years:
            indx = np.where(chanwb.data['Year'] == y)[0]
            i0, iend = indx[0], indx[-1]

            row = OrderedDict([('Y', chanwb.data['Year'][i0]),
                        ('Inflow', np.sum(chanwb.data['Inflow'][i0:iend])),
                        ('Outflow', np.sum(chanwb.data['Outflow'][i0:iend])),
                        ('Baseflow', np.sum(chanwb.data['Baseflow'][i0:iend])),
                        ('Loss', np.sum(chanwb.data['Loss'][i0:iend]))])

            yield RowData(row)

    @property
    def yearly_header(self):
        return ['Year'] + list(self.hdr)

    @property
    def yearly_units(self):
        return [None] + list(self.units)

    def yearly_iter(self):
        data = self.data
        areas = self.areas
        wsarea = self.wsarea
        header = self.header
        years = self.years

        for y in years:
            row = OrderedDict([('Year', y)] + [(k, 0.0) for k in header])

            for k in header:
                row[k] = 0.0

            for topaz_id in data:
                for k in header:
                    row[k] += data[topaz_id][k][y] * 0.001 * areas[topaz_id]

            for k in header:
                row[k] /= wsarea
                row[k] *= 1000.0

            yield RowData(row)

    @property
    def avg_annual_header(self):
        return ['TopazID'] + list(self.hdr)

    @property
    def avg_annual_units(self):
        return [None] + list(self.units)

    def avg_annual_iter(self):
        data = self.data
        header = self.header

        for topaz_id in data:
            row = OrderedDict([('TopazID', topaz_id)])
            for k in header:
                row[k] = np.mean(list(data[topaz_id][k].values()))

            yield RowData(row)

if __name__ == "__main__":
    #output_dir = '/geodata/weppcloud_runs/Blackwood_forStats/'
    output_dir = '/geodata/weppcloud_runs/1fa2e981-49b2-475a-a0dd-47f28b52c179/'
    watbal = ChannelWatbal(output_dir)
    from pprint import pprint

    watbal.export_daily_streamflow('/geodata/weppcloud_runs/1fa2e981-49b2-475a-a0dd-47f28b52c179/daily.csv')

    print(list(watbal.hdr))
    print(list(watbal.units))
#    for row in watbal.yearly_iter():
#    for row in watbal.avg_annual_iter():
#    for row in watbal.daily_iter():
#    for row in watbal.daily_outlet_iter():
    for row in watbal.yearly_outlet_iter():
        print([(k, v) for k, v in row])

