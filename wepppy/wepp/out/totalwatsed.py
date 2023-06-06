# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""
Parses Erin Brooks's totalwatsed.txt files produced from the .wat.txt and .pass.txt hillslope
WEPP outputs and performs streamflow and water balance calculations.

The calculations were provided by Mariana Dobre.
"""

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from copy import deepcopy
from collections import OrderedDict
import csv
import math
from datetime import datetime, timedelta
from glob import glob
from multiprocessing import Pool
import numpy as np
import pandas as pd

from deprecated import deprecated

from wepppy.all_your_base.hydro import determine_wateryear
from wepppy.wepp.out import watershed_swe
from wepppy.all_your_base import NCPU

NCPU = math.ceil(NCPU * 0.6)


def _read_hill_wat_sed(pass_fn):
    from .hill_pass import HillPass
    from .hill_wat import HillWat

    wat_fn = pass_fn.replace('.pass.dat', '.wat.dat')
    hill_wat = HillWat(wat_fn)
    watbal = hill_wat.calculate_daily_watbal()

    hill_pass = HillPass(pass_fn)
    sed_df = hill_pass.sed_df
 
    for col in sed_df.columns:
        if col in ['Julian', 'Year', 'Area (ha)']:
            continue
        watbal[col] = sed_df[col]

    return watbal, hill_wat.total_area


class TotalWatSed2(object):
    def __init__(self, wd, baseflow_opts=None, phos_opts=None):

        if baseflow_opts is None:
            from wepppy.nodb import Ron, Wepp
            wepp = Wepp.getInstance(wd)
            baseflow_opts = wepp.baseflow_opts

        if baseflow_opts is None:
            from wepppy.nodb import Ron, Wepp
            wepp = Wepp.getInstance(wd)
            if wepp.has_phosphorus:
                phos_opts = wepp.phosphorus_opts

        output_dir = _join(wd, 'wepp/output')
        pkl_fn = _join(output_dir, 'totwatsed2.pkl')
        if _exists(pkl_fn):
            self.d = pd.read_pickle(pkl_fn)
            self.wsarea = self.d.attrs['wsarea']
            return

        pass_fns = glob(_join(output_dir, 'H*.pass.dat'))
        
        pool = Pool(processes=NCPU)
        results = pool.map(_read_hill_wat_sed, pass_fns)
        pool.close()
        pool.join()

        d = None
        totarea_m2 = 0.0
        for watsed, area in results:
            totarea_m2 += area

            if d is None:
                d = deepcopy(watsed)
            else:
                for col in watsed.columns:
                    if col in ['Year', 'Month', 'Day', 'Julian']:
                        continue
                    d[col] += watsed[col]

        totarea_ha = totarea_m2 / 10000.0


        d['Cumulative Sed Del (tonnes)'] = np.cumsum(d['Sed Del (kg)'] / 1000.0)
        d['Sed Del Density (tonne/ha)'] = (d['Sed Del (kg)'] / 1000.0) / totarea_ha
        d['Precipitation (mm)'] = d['P (m^3)'] / totarea_m2 * 1000.0
        d['Rain + Melt (mm)'] = d['RM (m^3)'] / totarea_m2 * 1000.0
        d['Transpiration (mm)'] = d['Ep (m^3)'] / totarea_m2 * 1000.0
        d['Evaporation (mm)'] = d['Es+Er (m^3)'] / totarea_m2 * 1000.0
        d['ET (mm)'] = d['Evaporation (mm)'] + d['Transpiration (mm)']
        d['Percolation (mm)'] = d['Dp (m^3)'] / totarea_m2 * 1000.0
        d['Runoff (mm)'] = d['QOFE (m^3)'] / totarea_m2 * 1000.0
        d['Lateral Flow (mm)'] = d['latqcc (m^3)'] / totarea_m2 * 1000.0
        d['Storage (mm)'] = d['Total-Soil Water (m^3)'] / totarea_m2 * 1000.0

        # calculate Res volume, baseflow, and aquifer losses
        _res_vol = np.zeros(d.shape[0])
        _res_vol[0] = baseflow_opts.gwstorage
        _baseflow = np.zeros(d.shape[0])
        _aq_losses = np.zeros(d.shape[0])

        for i, perc in enumerate(d['Percolation (mm)']):
            if i == 0:
                continue

            _aq_losses[i-1] = _res_vol[i-1] * baseflow_opts.dscoeff
            _res_vol[i] = _res_vol[i-1] - _baseflow[i-1] + perc - _aq_losses[i-1]
            _baseflow[i] = _res_vol[i] * baseflow_opts.bfcoeff

        d['Reservoir Volume (mm)'] = _res_vol
        d['Baseflow (mm)'] = _baseflow
        d['Aquifer Losses (mm)'] = _aq_losses

        d['Streamflow (mm)'] = d['Runoff (mm)'] + d['Lateral Flow (mm)'] + d['Baseflow (mm)']

        if phos_opts is not None:
            assert isinstance(phos_opts, PhosphorusOpts)
            if phos_opts.isvalid:
                d['P Load (mg)'] = d['Sed. Del (kg)'] * phos_opts.sediment
                d['P Runoff (mg)'] = d['Runoff (mm)'] * phos_opts.surf_runoff * totarea_ha 
                d['P Lateral (mg)'] = d['Lateral Flow (mm)'] * phos_opts.lateral_flow * totarea_ha
                d['P Baseflow (mg)'] = d['Baseflow (mm)'] * phos_opts.baseflow * totarea_ha
                d['Total P (kg)'] = (d['P Load (mg)'] +
                                     d['P Runoff (mg)'] +
                                     d['P Lateral (mg)'] +
                                     d['P Baseflow (mg)']) / 1000.0 / 1000.0
                d['Particulate P (kg)'] = d['P Load (mg)'] / 1000000.0
                d['Soluble Reactive P (kg)'] = d['Total P (kg)'] - d['Particulate P (kg)']

                d['P Total (kg/ha)'] = d['Total P (kg)'] / totarea_ha
                d['Particulate P (kg/ha)'] = d['Particulate P (kg)'] / totarea_ha
                d['Soluble Reactive P (kg/ha)'] = d['Soluble Reactive P (kg)'] / totarea_ha

        # Determine Water Year Column
        _wy = np.zeros(d.shape[0], dtype=np.int)
        for i, (j, y) in enumerate(zip(d['Julian'], d['Year'])):
            _wy[i] = determine_wateryear(y, j=j)
        d['Water Year'] = _wy

#        d.columns = d.columns.str.replace('P (m^3)', 'Precipitation (m^3)')
#        d.columns = d.columns.str.replace('RM (m^3)', 'Rain + Melt (m^3)')
#        d.columns = d.columns.str.replace('ES+EP (m^3)', 'Evaporation (m^3)')
#        d.columns = d.columns.str.replace('Ep (m^3)', 'Percolation (m^3)')
#        d.columns = d.columns.str.replace('QOFE (m^3)', 'Runoff (m^3)')
#        d.columns = d.columns.str.replace('latqcc (m^3)', 'Lateral Flow (m^3)')
#        d.columns = d.columns.str.replace('Total-Soil Water (m^3)', 'Storage (m^3)')
        d.attrs['wsarea'] = totarea_m2
        d.to_pickle(pkl_fn)

        self.wsarea = totarea_m2
        self.d = d

    @property
    def num_years(self):
        return len(set(self.d['Year']))

    @property
    def sed_delivery(self):
        return np.sum(self.d['Sed Del (kg)'])

    @property
    def class_fractions(self):
        d = self.d

        sed_delivery = self.sed_delivery

        if sed_delivery == 0.0:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

        return [np.sum(d['Sed Del c1 (kg)']) / sed_delivery,
                np.sum(d['Sed Del c2 (kg)']) / sed_delivery,
                np.sum(d['Sed Del c3 (kg)']) / sed_delivery,
                np.sum(d['Sed Del c4 (kg)']) / sed_delivery,
                np.sum(d['Sed Del c5 (kg)']) / sed_delivery]

    def export(self, fn):
        d = self.d
        for k in d.keys():
            if '(m^3)' in k:
                del d[k]

        with open(fn, 'w') as fp:
            fp.write('DAILY TOTAL WATER BALANCE AND SEDIMENT\n\n')
            fp.write(f'Total Area (m^2): {self.wsarea}\n\n')

            wtr = csv.DictWriter(fp,
                                 fieldnames=list(d.keys()),
                                 lineterminator='\n')
            wtr.writeheader()
            for i, yr in enumerate(d['Year']):
                wtr.writerow(OrderedDict([(k, d[k][i]) for k in d]))

@deprecated
class TotalWatSed(object):

    hdr = ['Julian', 'Year', 'Area (m^2)', 'Precip Vol (m^3)', 'Rain + Melt Vol (m^3)',
           'Transpiration Vol (m^3)', 'Evaporation Vol (m^3)', 'Percolation Vol (m^3)',
           'Runoff Vol (m^3)', 'Lateral Flow Vol (m^3)', 'Storage Vol (m^3)', 'Sed. Det. (kg)',
           'Sed. Dep. (kg)', 'Sed. Del (kg)',
           'Class 1', 'Class 2', 'Class 3', 'Class 4', 'Class 5']

    types = [int, int, float, float, float, float, float, float, float, float,
             float, float, float, float, float, float, float, float, float]

    def __init__(self, fn,
                 baseflow_opts,
                 phos_opts=None):

        from wepppy.nodb import PhosphorusOpts, BaseflowOpts
        wd = _join(_split(fn)[0], '../../')

        hdr = self.hdr
        types = self.types

        # read the loss report
        with open(fn) as fp:
            lines = fp.readlines()

        d = OrderedDict((k, []) for k in hdr)

        for L in lines:
            L = L.split()
            assert len(L) == len(hdr)
            assert len(L) == len(types)

            for k, v, _type in zip(hdr, L, types):
                d[k].append(_type(v))

        for k in d:
            d[k] = np.array(d[k])

        d['Area (ha)'] = d['Area (m^2)'] / 10000.0
        d['cumulative Sed. Del (tonnes)'] = np.cumsum(d['Sed. Del (kg)'] / 1000.0)
        d['Sed. Del Density (tonne/ha)'] = (d['Sed. Del (kg)'] / 1000.0) / d['Area (ha)']
        d['Precipitation (mm)'] = d['Precip Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Rain + Melt (mm)'] = d['Rain + Melt Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Transpiration (mm)'] = d['Transpiration Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Evaporation (mm)'] = d['Evaporation Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['ET (mm)'] = d['Evaporation (mm)'] + d['Transpiration (mm)']
        d['Percolation (mm)'] = d['Percolation Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Runoff (mm)'] = d['Runoff Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Lateral Flow (mm)'] = d['Lateral Flow Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Storage (mm)'] = d['Storage Vol (m^3)'] / d['Area (m^2)'] * 1000.0

        # calculate Res volume, baseflow, and aquifer losses
        d['Reservoir Volume (mm)'] = [baseflow_opts.gwstorage]
        d['Baseflow (mm)'] = [0.0]
        d['Aquifer Losses (mm)'] = []

        for perc in d['Percolation (mm)']:
            d['Aquifer Losses (mm)'].append(d['Reservoir Volume (mm)'][-1] * baseflow_opts.dscoeff)
            d['Reservoir Volume (mm)'].append(d['Reservoir Volume (mm)'][-1] -
                                              d['Baseflow (mm)'][-1] + perc -
                                              d['Aquifer Losses (mm)'][-1])
            d['Baseflow (mm)'].append(d['Reservoir Volume (mm)'][-1] * baseflow_opts.bfcoeff)

        d['Reservoir Volume (mm)'] = np.array(d['Reservoir Volume (mm)'][1:])
        d['Baseflow (mm)'] = np.array(d['Baseflow (mm)'][1:])
        d['Aquifer Losses (mm)'] = np.array(d['Aquifer Losses (mm)'])

        d['Streamflow (mm)'] = d['Runoff (mm)'] + d['Lateral Flow (mm)'] + d['Baseflow (mm)']

        d['Sed. Del (tonne)'] = d['Sed. Del (kg)'] / 1000.0

        d['SWE (mm)'] = watershed_swe(wd)

        if phos_opts is not None:
            assert isinstance(phos_opts, PhosphorusOpts)
            if phos_opts.isvalid:
                d['P Load (mg)'] = d['Sed. Del (kg)'] * phos_opts.sediment
                d['P Runoff (mg)'] = d['Runoff (mm)'] * phos_opts.surf_runoff * d['Area (ha)']
                d['P Lateral (mg)'] = d['Lateral Flow (mm)'] * phos_opts.lateral_flow * d['Area (ha)']
                d['P Baseflow (mg)'] = d['Baseflow (mm)'] * phos_opts.baseflow * d['Area (ha)']
                d['Total P (kg)'] = (d['P Load (mg)'] +
                                               d['P Runoff (mg)'] +
                                               d['P Lateral (mg)'] +
                                               d['P Baseflow (mg)']) / 1000.0 / 1000.0
                d['Particulate P (kg)'] = d['P Load (mg)'] / 1000000.0
                d['Soluble Reactive P (kg)'] = d['Total P (kg)'] - d['Particulate P (kg)']

                d['P Total (kg/ha)'] = d['Total P (kg)'] / d['Area (ha)']
                d['Particulate P (kg/ha)'] = d['Particulate P (kg)'] / d['Area (ha)']
                d['Soluble Reactive P (kg/ha)'] = d['Soluble Reactive P (kg)'] / d['Area (ha)']

        d['Water Year'] = []
        d['mo'] = []
        d['da'] = []
        for j, y in zip(d['Julian'], d['Year']):
            j, y = int(j), int(y)
            date = datetime(y, 1, 1) + timedelta(j - 1)
            d['mo'].append(int(date.month))
            d['da'].append(int(date.day))
            d['Water Year'].append(determine_wateryear(y, j=j))

        for k in d:
            if k in ['Water Year', 'Year', 'Julian', 'mo', 'da']:
                d[k] = [int(v) for v in d[k]]
            else:
                d[k] = [float(v) for v in d[k]]

        self.d = d
        self.wsarea = float(d['Area (m^2)'][0])

    @property
    def num_years(self):
        return len(set(self.d['Year']))

    @property
    def sed_delivery(self):
        return np.sum(self.d['Sed. Del (kg)'])

    @property
    def class_fractions(self):
        d = self.d

        sed_delivery = self.sed_delivery

        if sed_delivery == 0.0:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

        return [np.sum(d['Class 1']) / sed_delivery,
                np.sum(d['Class 2']) / sed_delivery,
                np.sum(d['Class 3']) / sed_delivery,
                np.sum(d['Class 4']) / sed_delivery,
                np.sum(d['Class 5']) / sed_delivery]

    def export(self, fn):
        d = self.d
        with open(fn, 'w') as fp:
            wtr = csv.DictWriter(fp,
                                 fieldnames=list(d.keys()),
                                 lineterminator='\n')
            wtr.writeheader()
            for i, yr in enumerate(d['Year']):
                wtr.writerow(OrderedDict([(k, d[k][i]) for k in d]))


if __name__ == "__main__":
    from pprint import pprint
    fn = '/geodata/weppcloud_runs/srivas42-greatest-ballad/wepp/output/totalwatsed.txt'
    from wepppy.nodb import PhosphorusOpts, BaseflowOpts
    phosOpts = PhosphorusOpts()
    phosOpts.surf_runoff = 0.0118
    phosOpts.lateral_flow = 0.0118
    phosOpts.baseflow = 0.0196
    phosOpts.sediment = 1024
    baseflowOpts = BaseflowOpts()
    totwatsed = TotalWatSed(fn, baseflowOpts, phos_opts=phosOpts)
    totwatsed.export('/home/roger/totwatsed.csv')
