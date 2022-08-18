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
import math
from glob import glob
from multiprocessing import Pool

import numpy as np
import pandas as pd

from wepppy.wepp.out import HillWat
from wepppy.all_your_base import NCPU
from wepppy.all_your_base.hydro import determine_wateryear
from .row_data import RowData, parse_units
from .report_base import ReportBase

NCPU = math.ceil(NCPU * 0.6)

def _pickle_hill_wat_annual_watbal(wat_fn):
    wat = HillWat(wat_fn)
    wat_df = wat.calculate_annual_watbal(
        watbal_measures=('P', 'QOFE', 'latqcc', 'Ep+Es+Er', 'Dp'), 
        units='mm')
    wat_df.attrs['area'] = wat.total_area
    stats_fn = wat_fn.replace('/output/H', '/stats/H').replace('.wat.dat', '.annual_wat.pkl')
    wat_df.to_pickle(stats_fn)


class HillslopeWatbal(ReportBase):
    def __init__(self, wd):
        self.wd = wd

        from wepppy.nodb import Watershed
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        output_dir = _join(wd, 'wepp/output')
        stats_dir = _join(wd, 'wepp/stats')

        # find all the water output files
        wat_fns = glob(_join(output_dir, 'H*.wat.dat'))
        n = len(wat_fns)
        assert n > 0

        # make sure we have all of them
        repickle = False
        for wepp_id in range(1, n+1):
            if not _exists(_join(stats_dir, 'H{}.annual_wat.pkl'.format(wepp_id))):
                repickle = True
                break

        if repickle:
            pool = Pool(processes=NCPU)
            results = pool.map(_pickle_hill_wat_annual_watbal, wat_fns)
            pool.close()
        
        # create dictionaries for the waterbalance
        d = {}
        areas = {}
        years = None

        for wepp_id in range(1, n + 1):
            # find the topaz_id
            topaz_id = translator.top(wepp=wepp_id)

            stats_fn = _join(stats_dir, 'H{}.annual_wat.pkl'.format(wepp_id))
            wat_df = pd.read_pickle(stats_fn)
                
            area = wat_df.attrs['area']

            wat_df.columns = wat_df.columns.str.replace('Ep\+Es\+Er', 'Transpiration + Evaporation')
            wat_df.columns = wat_df.columns.str.replace('P', 'Precipitation')
            wat_df.columns = wat_df.columns.str.replace('QOFE', 'Surface Runoff')
            wat_df.columns = wat_df.columns.str.replace('latqcc', 'Lateral Flow')
            wat_df.columns = wat_df.columns.str.replace('Dp', 'Percolation')

            # initialize the water
            d[topaz_id] = wat_df
            areas[topaz_id] = area

        self.years = sorted([int(wy) for wy in wat_df.index])
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

        num_water_years = len(self.years)

        for topaz_id in data:
            row = OrderedDict([('TopazID', topaz_id)])
            for k in header:
                row[k] = np.sum(data[topaz_id][k]) / (num_water_years - 1)

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


