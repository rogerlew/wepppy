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

from abc import ABC, abstractmethod
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from copy import deepcopy
from collections import OrderedDict
import csv
import math
import json
from datetime import datetime, timedelta
from glob import glob
from multiprocessing import Pool
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from deprecated import deprecated

from wepppy.all_your_base.hydro import determine_wateryear
from wepppy.wepp.out import watershed_swe
from wepppy.all_your_base import NCPU


NCPU = math.ceil(NCPU * 0.6)


def _read_hill_wat_sed(pass_fn):
    from .hill_pass import HillPass
    from .hill_wat import HillWat

    wepp_id = _split(pass_fn)[-1].split('.')[0].replace('H', '')

    wat_fn = pass_fn.replace('.pass.dat', '.wat.dat')
    hill_wat = HillWat(wat_fn)
    watbal = hill_wat.calculate_daily_watbal()

    hill_pass = HillPass(pass_fn)
    sed_df = hill_pass.sed_df
 
    for col in sed_df.columns:
        if col in ['Julian', 'Year', 'Area (ha)']:
            continue
        watbal[col] = sed_df[col]

    return watbal, hill_wat.total_area, wepp_id


def process_measures_df(d, totarea_m2, baseflow_opts, phos_opts):
    from wepppy.nodb import PhosphorusOpts

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

        _aq_losses[i - 1] = _res_vol[i - 1] * baseflow_opts.dscoeff
        _res_vol[i] = _res_vol[i - 1] - _baseflow[i - 1] + perc - _aq_losses[i - 1]
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
    _wy = np.zeros(d.shape[0], dtype=np.int64)
    for i, (mo, y) in enumerate(zip(d['Month'], d['Year'])):
        _wy[i] = determine_wateryear(y, mo=mo)
    d['Water Year'] = _wy

    return d


class AbstractTotalWatSed2(ABC):
    def __init__(self, wd, baseflow_opts=None, phos_opts=None):
        self.wd = wd
        self.baseflow_opts = baseflow_opts
        self.phos_opts = phos_opts
        self.load_data()

    @property
    @abstractmethod
    def parquet_fn(self):
        pass

    @property
    @abstractmethod
    def pickle_fn(self):
        pass

    def load_data(self):
        output_dir = _join(self.wd, 'wepp/output')
        parquet_fn = self.parquet_fn
        pkl_fn = self.pickle_fn

        # deserialize if possible
        if _exists(parquet_fn):
            # Read the table from the Parquet file
            table = pq.read_table(parquet_fn)

            # Convert the table to a pandas DataFrame
            self.d = table.to_pandas()

            # Extract and set the metadata
            for k, v in table.schema.metadata.items():
                setattr(self, k.decode('utf-8'), json.loads(v.decode('utf-8')))
            return

        # old projects have pickle files
        if _exists(pkl_fn):
            self.d = pd.read_pickle(pkl_fn)
            self.wsarea = self.d.attrs['wsarea']
            return

        # determine baseflow and phosphorus options
        if self.baseflow_opts is None or self.phos_opts is None:
            from wepppy.nodb import Wepp
            wepp = Wepp.getInstance(self.wd)

        if self.baseflow_opts is None:
            self.baseflow_opts = wepp.baseflow_opts

        if self.baseflow_opts is None:
            if wepp.has_phosphorus:
                self.phos_opts = wepp.phosphorus_opts

        # load the data
        pass_fns = glob(_join(output_dir, 'H*.pass.dat'))

        pool = Pool(processes=NCPU)
        results = pool.map(_read_hill_wat_sed, pass_fns)
        pool.close()
        pool.join()

        self.compile_data(results)

    @abstractmethod
    def compile_data(self, results, parquet_fn):
        pass

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

    def to_parquet(self, df, metadata=None):

        # Convert the pandas DataFrame to an arrow Table
        table = pa.Table.from_pandas(df)

        if metadata is not None:
            # Add the metadata to the table
            metadata_bytes = {bytes(k, 'utf-8'): bytes(json.dumps(v), 'utf-8') for k, v in metadata.items()}
            table = table.replace_schema_metadata(metadata_bytes)

        # Write the table to a Parquet file
        pq.write_table(table, self.parquet_fn)


class TotalWatSed2(AbstractTotalWatSed2):

    @property
    def parquet_fn(self):
        return _join(self.wd, 'wepp/output/totwatsed2.parquet')

    @property
    def pickle_fn(self):
        return _join(self.wd, 'wepp/output/totwatsed2.pkl')

    def compile_data(self, results):
        # compile the data
        d = None
        totarea_m2 = 0.0
        for watsed, area, wepp_id in results:
            totarea_m2 += area

            if d is None:
                d = deepcopy(watsed)
            else:
                for col in watsed.columns:
                    if col in ['Year', 'Month', 'Day', 'Julian']:
                        continue
                    d[col] += watsed[col]

        # process the single data frame
        d = process_measures_df(d, totarea_m2, self.baseflow_opts, self.phos_opts)

        self.to_parquet(d, metadata={'wsarea': totarea_m2})

        # save attributes
        self.wsarea = totarea_m2
        self.d = d


"""
Summary by landuse

Measures


Precipitation (mm)
Rain + Melt (mm)     ANU
ET (mm)              ANU
Percolation (mm)     ANU
Lateral Flow (mm)    ANU
Baseflow (mm)        ANU
Runoff (mm)
Sed Del (kg)
phosphorus if available


Average Annuals by Landuse

Measures as columns
Landuse as rows

"""

class DisturbedTotalWatSed2(AbstractTotalWatSed2):
    @property
    def parquet_fn(self):
        return _join(self.wd, 'wepp/output/disturbedtotwatsed2.parquet')

    @property
    def pickle_fn(self):
        return _join(self.wd, 'wepp/output/disturbedtotwatsed2.pkl')

    def compile_data(self, results):
        # need to translator to identify topaz_ids from wepp_ids
        from wepppy.nodb import Watershed
        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        from wepppy.nodb import Landuse
        landuse = Landuse.getInstance(self.wd)

        # compile the data
        keys = list(landuse.domlc_d.values())
        d = {k: None for k in keys}
        d_m2 = {k: 0 for k in keys}

        totarea_m2 = 0.0
        for watsed, area, wepp_id in results:
            topaz_id = translator.top(wepp=wepp_id)
            dom = landuse.domlc_d[str(topaz_id)]

            d_m2[dom] += area
            totarea_m2 += area

            if d[dom] is None:
                d[dom] = deepcopy(watsed)
            else:
                for col in watsed.columns:
                    if col in ['Year', 'Month', 'Day', 'Julian']:
                        continue
                    d[dom][col] += watsed[col]

        for dom in d:
            print(dom)
            if d[dom] is None:
                continue

            d[dom] = process_measures_df(d[dom], d_m2[dom], self.baseflow_opts, self.phos_opts)
            d[dom]['dom'] = dom

        # Concatenate all the DataFrames together
        d = pd.concat(d.values())
        self.to_parquet(d, metadata={'d_m2': d_m2, 'wsarea': totarea_m2})

        self.wsarea = totarea_m2
        self.d_m2 = d_m2
        self.d = d

    @property
    def annual_averages_parquet_fn(self):
        return _join(self.wd, 'wepp/output/disturbedtotwatsed2_annual_averages.parquet')

    @property
    def annual_averages(self):
        if _exists(self.annual_averages_parquet_fn):
            return pd.read_parquet(self.annual_averages_parquet_fn)
        else:
            return self._calculate_annuals()

    @property
    def annual_averages_report(self):
        from wepppy.wepp.stats.average_annuals_by_landuse import AverageAnnualsByLanduse
        return AverageAnnualsByLanduse(self.annual_averages)


    def _calculate_annuals(self):
        from wepppy.nodb import Landuse
        landuse = Landuse.getInstance(self.wd)

        measures = ['Precipitation (mm)', 'Rain + Melt (mm)', 'ET (mm)', 'Percolation (mm)',
                    'Lateral Flow (mm)', 'Baseflow (mm)', 'Runoff (mm)', 'Sed Del (kg)']

        # Sum the values for each water year for each dom
        yearly_totals = self.d.groupby(['Water Year', 'dom'])[measures].sum().reset_index()

        # Calculate the number of water years for bias correction
        number_of_years = yearly_totals['Water Year'].nunique() - 1

        # Calculate the average of the yearly totals for each dom with bias correction
        annual_averages = yearly_totals.groupby('dom')[measures].sum().div(number_of_years).reset_index()

        # Add area
        annual_averages['Area (ha)'] = annual_averages['dom'].apply(lambda x: self.d_m2[x] / 10000.0)

        # Add management description to each row
        annual_averages['man_description'] = annual_averages['dom'].apply(lambda x: landuse.managements[x].desc)

        # Reorder the columns so that 'dom' and 'man_description' are the first two columns
        cols = annual_averages.columns.tolist()
        cols = cols[:1] + ['man_description'] + cols[1:-1]
        annual_averages = annual_averages[cols]

        # Sort by 'Area (ha)' in descending order
        annual_averages.sort_values('Area (ha)', ascending=False, inplace=True)

        # Serialize DataFrame to parquet
        annual_averages.to_parquet(self.annual_averages_parquet_fn)

        # Set the header after re-ordering the columns
        self.header = annual_averages.columns.tolist()

        return annual_averages


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
            d['Water Year'].append(determine_wateryear(y, mo=d['mo']))

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
