from os.path import join as _join
from os.path import exists as _exists
from glob import glob

from wepppy.all_your_base import parse_units, RowData


class HillslopeWatbal:
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


            years = set()
            for i, wl in enumerate(wat_data):
                OFE, J, Y, P, RM, Q, Ep, Es, Er, Dp, UpStrmQ, \
                SubRIn, latqcc, TSW, frozwt, SnowWater, QOFE, Tile, Irr, Area = wl.split()

                years.add(Y)

                if i == 0:
                    d[topaz_id]['Precipitation (mm)'] = float(P)
                    d[topaz_id]['Streamflow (mm)'] = float(Q)
                    d[topaz_id]['Transpiration + Evaporation (mm)'] = float(Ep) + float(Er)
                    d[topaz_id]['Percolation (mm)'] = float(Dp)
                    d[topaz_id]['Total Soil Water Storage (mm)'] = float(TSW)
                else:
                    d[topaz_id]['Precipitation (mm)'] += float(P)
                    d[topaz_id]['Streamflow (mm)'] += float(Q)
                    d[topaz_id]['Transpiration + Evaporation (mm)'] += float(Ep) + float(Er)
                    d[topaz_id]['Percolation (mm)'] += float(Dp)
                    d[topaz_id]['Total Soil Water Storage (mm)'] += float(TSW)

            num_years = len(years)
            for topaz_id in d:
                for k in d[topaz_id]:
                    d[topaz_id][k] /= num_years

            self.data = d
            self.last_top = topaz_id

    @property
    def header(self):
        return self.data[self.last_top].keys()

    @property
    def hdr(self):
        for colname in self.header:
            yield colname.split()[0]

    @property
    def units(self):
        for colname in self.header:
            yield parse_units(colname)

    def __iter__(self):
        for topaz_id in self.data:
            row = {'topaz_id': topaz_id}
            row.update(self.data[topaz_id])
            yield RowData(row)


if __name__ == "__main__":
    #output_dir = '/geodata/weppcloud_runs/Blackwood_forStats/'
    output_dir = '/geodata/weppcloud_runs/1fa2e981-49b2-475a-a0dd-47f28b52c179/'
    watbal = HillslopeWatbal(output_dir)
    from pprint import pprint


    print(list(watbal.hdr))
    print(list(watbal.units))
    for row in watbal:
        for k,v in row:
            print(k, v)