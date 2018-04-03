from os.path import join as _join
from os.path import exists as _exists

from collections import OrderedDict

from glob import glob

import numpy as np

from wepppy.all_your_base import parse_units, RowData
from .report_base import ReportBase

class HillslopeWatbal(ReportBase):
    def __init__(self, wd):
        self.wd = wd

        from wepppy.nodb import Watershed
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        output_dir = _join(wd, 'wepp/output')

        wat_fns = glob(_join(output_dir, 'H*.wat.dat'))
        n = len(wat_fns)
        assert n > 0

        for wepp_id in range(1, n+1):
            assert _exists(_join(output_dir, 'H{}.wat.dat'.format(wepp_id)))

        d = {}
        areas = {}
        years = set()

        for wepp_id in range(1, n + 1):
            topaz_id = translator.top(wepp=wepp_id)
            d[topaz_id] = {'Precipitation (mm)': {},
                           'Streamflow (mm)': {},
                           'Transpiration + Evaporation (mm)': {},
                           'Percolation (mm)': {},
                           'Total Soil Water Storage (mm)': {}}

            wat_fn = _join(output_dir, 'H{}.wat.dat'.format(wepp_id))

            with open(wat_fn) as wat_fp:
                wat_data = wat_fp.readlines()[23:]

            for i, wl in enumerate(wat_data):
                OFE, J, Y, P, RM, Q, Ep, Es, Er, Dp, UpStrmQ, \
                SubRIn, latqcc, TSW, frozwt, SnowWater, QOFE, Tile, Irr, Area = wl.split()

                J, Y, P, Q, Ep, Es, Er, Dp, latqcc, TSW, Area = \
                    int(J), int(Y), float(P), float(Q), float(Ep), float(Es), float(Er), float(Dp), float(latqcc), \
                    float(TSW), float(Area)

                if i == 0:
                    areas[topaz_id] = Area

                if wepp_id == 1:
                    years.add(Y)

                if Y not in d[topaz_id]['Precipitation (mm)']:
                    d[topaz_id]['Precipitation (mm)'][Y] = P
                    d[topaz_id]['Streamflow (mm)'][Y] = Q
                    d[topaz_id]['Transpiration + Evaporation (mm)'][Y] = Ep + Es + Er
                    d[topaz_id]['Percolation (mm)'][Y] = Dp
                    d[topaz_id]['Total Soil Water Storage (mm)'][Y] = TSW
                else:
                    d[topaz_id]['Precipitation (mm)'][Y] += P
                    d[topaz_id]['Streamflow (mm)'][Y] += Q
                    d[topaz_id]['Transpiration + Evaporation (mm)'][Y] += Ep + Es + Er
                    d[topaz_id]['Percolation (mm)'][Y] += Dp
                    d[topaz_id]['Total Soil Water Storage (mm)'][Y] += TSW

        self.years = sorted(years)
        self.data = d
        self.areas = areas
        self.wsarea = float(np.sum(list(areas.values())))
        self.last_top = topaz_id

    @property
    def header(self):
        return list(self.data[self.last_top].keys())

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
            row = {'TopazID': topaz_id}
            for k in header:
                row[k] = np.mean(list(data[topaz_id][k].values()))

            yield RowData(row)


if __name__ == "__main__":
    #output_dir = '/geodata/weppcloud_runs/Blackwood_forStats/'
    output_dir = '/geodata/weppcloud_runs/1fa2e981-49b2-475a-a0dd-47f28b52c179/'
    watbal = HillslopeWatbal(output_dir)
    from pprint import pprint


    print(list(watbal.hdr))
    print(list(watbal.units))
    for row in watbal.yearly_iter():
#    for row in watbal.avg_annual_iter():
#    for row in watbal.daily_iter():
        print([(k, v) for k, v in row])

