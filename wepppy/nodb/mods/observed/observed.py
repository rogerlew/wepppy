# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import exists as _exists
from os.path import join as _join

from datetime import datetime
import io
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro.objective_functions import calculate_all_functions

from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core.wepp import BaseflowOpts
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wepppy.wepp.interchange import (
        run_totalwatsed3 as _run_totalwatsed3,
        run_wepp_hillslope_pass_interchange as _run_wepp_hillslope_pass_interchange,
        run_wepp_hillslope_wat_interchange as _run_wepp_hillslope_wat_interchange,
        run_wepp_watershed_chanwb_interchange as _run_wepp_watershed_chanwb_interchange,
        run_wepp_watershed_ebe_interchange as _run_wepp_watershed_ebe_interchange,
    )


@lru_cache(maxsize=1)
def _interchange_module():
    from wepppy.wepp import interchange  # local import to avoid circular dependency

    return interchange

__all__ = [
    'validate',
    'ObservedNoDbLockedException',
    'Observed',
]

def validate(Qm, Qo):
    assert Qm.shape == Qo.shape
    assert len(Qo.shape) == 1


class ObservedNoDbLockedException(Exception):
    pass


class Observed(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Observed'

    filename = 'observed.nodb'
    
    measures = ['Streamflow (mm)',
                'Sed Del (kg)',
                'Total P (kg)',
                'Soluble Reactive P (kg)',
                'Particulate P (kg)']

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(Observed, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self.results = None
            if not _exists(self.observed_dir):
                os.mkdir(self.observed_dir)

    def read_observed_fn(self, fn):
        with open(fn) as fp:
            textdata = fp.read()
            self.parse_textdata(textdata)

    def parse_textdata(self, textdata):

        with self.locked():
            with io.StringIO(textdata) as fp:
                df = pd.read_csv(fp)

            assert 'Date' in df

            yrs, mos, das, juls = [], [], [], []
            for d in df['Date']:
                mo, da, yr = d.split('/')
                mo = int(mo)
                da = int(da)
                yr = int(yr)
                jul = (datetime(yr, mo, da) - datetime(yr, 1, 1)).days

                yrs.append(yr)
                mos.append(mo)
                das.append(da)
                juls.append(jul)

            df['Year'] = yrs
            df['Month'] = mos
            df['Day'] = das
            df['Julian'] = juls

            df.to_csv(self.observed_fn)
            
    @property
    def has_observed(self):
        return _exists(self.observed_fn)

    @property
    def has_results(self):
        return self.results is not None

    def calc_model_fit(self):
        assert self.has_observed

        observed_df = pd.read_csv(self.observed_fn)

        hillslope_sim, wsarea_m2 = self._load_hillslope_simulation()
        results = {}
        results['Hillslopes'] = self.run_measures(observed_df, hillslope_sim, 'Hillslopes')

        channel_sim = self._load_channel_simulation(wsarea_m2, hillslope_sim['Year'].min() if not hillslope_sim.empty else None)
        results['Channels'] = self.run_measures(observed_df, channel_sim, 'Channels')

        with self.locked():
            self.results = results
            
        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.run_observed)
        except FileNotFoundError:
            pass

    @property
    def stat_names(self):
        measure0 = list(self.results['Hillslopes'].keys())[0]
        return list(self.results['Hillslopes'][measure0]['Daily'].keys())

    def run_measures(self, obs, sim, hillorChannel):

        results = {}
        for m in self.measures:
            if m not in obs:
                continue

            res = self.run_measure(obs, sim, m, hillorChannel)

            results[m] = res

        return results

    def run_measure(self, obs, sim, measure, hillorChannel):
        sim_dates = dict([((int(yr), int(mo), int(da)), i) for i, (yr, mo, da) in
                              enumerate(zip(sim['Year'], sim['Month'], sim['Day']))])

        years = sorted(set(int(yr) for yr in obs['Year']))
        wtr_yr_d = dict((yr, i) for i, yr in enumerate(years))
        last_yr = years[-1]

        Qm, Qo, dates = [], [], []
        Qm_yearly, Qo_yearly = np.zeros(len(years)), np.zeros(len(years))

        for i, v in enumerate(obs[measure]):
            if math.isnan(v):
                continue

            jul = int(obs['Julian'][i])
            mo = int(obs['Month'][i])
            da = int(obs['Day'][i])
            yr = int(obs['Year'][i])

            j = sim_dates.get((yr, mo, da), None)

            if j is None:
                continue

            Qm.append(sim[measure][j])
            Qo.append(v)
            dates.append(str(obs['Date'][i]))

            wtr_yr = yr

            if jul > 273:
                wtr_yr += 1

            if wtr_yr <= last_yr:
                k = wtr_yr_d[wtr_yr]
                Qm_yearly[k] += Qm[-1]
                Qo_yearly[k] += Qo[-1]

        self._write_measure(Qm, Qo, dates, measure, hillorChannel, 'Daily')
        self._write_measure(Qm_yearly, Qo_yearly, years, measure, hillorChannel, 'Yearly')

        Qm = np.array(Qm)
        Qo = np.array(Qo)

        validate(Qo, Qm)
        validate(Qo_yearly, Qm_yearly)

        return dict([
            ('Daily', dict(calculate_all_functions(Qo, Qm))),
            ('Yearly', dict(calculate_all_functions(Qo_yearly, Qm_yearly)))
        ])

    def _load_hillslope_simulation(self):
        output_dir = Path(self.output_dir)
        interchange = _interchange_module()
        interchange.run_wepp_hillslope_pass_interchange(output_dir)
        interchange.run_wepp_hillslope_wat_interchange(output_dir)

        interchange_dir = output_dir / 'interchange'

        wepp = self.wepp_instance
        baseflow_opts = getattr(wepp, 'baseflow_opts', None)
        if baseflow_opts is None:
            baseflow_opts = BaseflowOpts()

        tot_path = interchange.run_totalwatsed3(interchange_dir, baseflow_opts)
        table = pq.read_table(tot_path)
        sim = table.to_pandas()

        if sim.empty:
            empty_columns = [
                'Year', 'Month', 'Day', 'Julian', 'Water Year',
                'Streamflow (mm)', 'Sed Del (kg)',
                'Total P (kg)', 'Soluble Reactive P (kg)', 'Particulate P (kg)',
            ]
            return pd.DataFrame(columns=empty_columns), 0.0

        rename_map = {
            'year': 'Year',
            'month': 'Month',
            'day_of_month': 'Day',
            'julian': 'Julian',
            'water_year': 'Water Year',
            'Area': 'Area (m^2)',
            'P': 'P (m^3)',
            'RM': 'RM (m^3)',
            'Q': 'Q (m^3)',
            'Dp': 'Dp (m^3)',
            'latqcc': 'latqcc (m^3)',
            'QOFE': 'QOFE (m^3)',
            'Ep': 'Ep (m^3)',
            'Es': 'Es (m^3)',
            'Er': 'Er (m^3)',
            'Precipitation': 'Precipitation (mm)',
            'Rain+Melt': 'Rain + Melt (mm)',
            'Percolation': 'Percolation (mm)',
            'Lateral Flow': 'Lateral Flow (mm)',
            'Runoff': 'Runoff (mm)',
            'Transpiration': 'Transpiration (mm)',
            'Evaporation': 'Evaporation (mm)',
            'ET': 'ET (mm)',
            'Baseflow': 'Baseflow (mm)',
            'Aquifer losses': 'Aquifer Losses (mm)',
            'Reservoir Volume': 'Reservoir Volume (mm)',
            'Streamflow': 'Streamflow (mm)',
            'Total-Soil Water': 'Storage (mm)',
            'Snow-Water': 'Snow-Water (mm)',
        }
        sim.rename(columns=rename_map, inplace=True)

        for col_name in ("day", "sim_day_index"):
            if col_name in sim:
                sim.drop(columns=[col_name], inplace=True)

        sed_cols = [col for col in sim.columns if col.startswith('seddep_')]
        if sed_cols:
            sim[sed_cols] = sim[sed_cols].fillna(0.0)
            sim['Sed Del (kg)'] = sim[sed_cols].sum(axis=1)
            for idx, col in enumerate(sed_cols, start=1):
                sim[f'Sed Del c{idx} (kg)'] = sim[col]
            sim.drop(columns=sed_cols, inplace=True)
        else:
            sim['Sed Del (kg)'] = 0.0

        if {'Es (m^3)', 'Er (m^3)'}.issubset(sim.columns):
            sim['Es+Er (m^3)'] = sim['Es (m^3)'] + sim['Er (m^3)']

        for col in ('Year', 'Month', 'Day', 'Julian', 'Water Year'):
            if col in sim:
                sim[col] = sim[col].astype(int, copy=False)

        if 'Area (m^2)' in sim:
            sim['Area (m^2)'] = sim['Area (m^2)'].astype(float, copy=False)
            wsarea_m2 = float(sim['Area (m^2)'].max())
        else:
            wsarea_m2 = 0.0

        phos_opts = getattr(wepp, 'phos_opts', None)
        if phos_opts is None:
            phos_opts = getattr(wepp, 'phosphorus_opts', None)

        if (
            phos_opts is not None
            and getattr(phos_opts, 'isvalid', False)
            and wsarea_m2 > 0
            and all(col in sim for col in ('Runoff (mm)', 'Lateral Flow (mm)', 'Baseflow (mm)'))
        ):
            totarea_ha = wsarea_m2 / 10000.0
            sim['P Load (mg)'] = sim['Sed Del (kg)'] * phos_opts.sediment
            sim['P Runoff (mg)'] = sim['Runoff (mm)'] * phos_opts.surf_runoff * totarea_ha
            sim['P Lateral (mg)'] = sim['Lateral Flow (mm)'] * phos_opts.lateral_flow * totarea_ha
            sim['P Baseflow (mg)'] = sim['Baseflow (mm)'] * phos_opts.baseflow * totarea_ha
            total_p_mg = sim['P Load (mg)'] + sim['P Runoff (mg)'] + sim['P Lateral (mg)'] + sim['P Baseflow (mg)']
            sim['Total P (kg)'] = total_p_mg / 1_000_000.0
            sim['Particulate P (kg)'] = sim['P Load (mg)'] / 1_000_000.0
            sim['Soluble Reactive P (kg)'] = sim['Total P (kg)'] - sim['Particulate P (kg)']
        else:
            for col in ('Total P (kg)', 'Particulate P (kg)', 'Soluble Reactive P (kg)'):
                if col not in sim:
                    sim[col] = np.nan

        sim.sort_values(['Year', 'Julian', 'Day'], inplace=True, ignore_index=True)
        return sim, wsarea_m2

    def _load_channel_simulation(self, wsarea_m2, first_year):
        output_dir = Path(self.output_dir)
        interchange = _interchange_module()
        ebe_path = interchange.run_wepp_watershed_ebe_interchange(output_dir)
        chan_path = interchange.run_wepp_watershed_chanwb_interchange(output_dir)

        ebe_table = pq.read_table(ebe_path)
        ebe_df = ebe_table.to_pandas()
        if ebe_df.empty:
            empty_columns = [
                'Year', 'Month', 'Day', 'Julian', 'Water Year',
                'Streamflow (mm)', 'Sed Del (kg)',
                'Total P (kg)', 'Soluble Reactive P (kg)', 'Particulate P (kg)',
            ]
            return pd.DataFrame(columns=empty_columns)

        rename_map = {
            'year': 'Year',
            'simulation_year': 'simulation_year',
            'month': 'Month',
            'day_of_month': 'Day',
            'julian': 'Julian',
            'water_year': 'Water Year',
            'precip': 'Precipitation Depth (mm)',
            'runoff_volume': 'Runoff Volume (m^3)',
            'peak_runoff': 'Peak Runoff (m^3/s)',
            'sediment_yield': 'Sediment Yield (kg)',
            'soluble_pollutant': 'Soluble Reactive P (kg)',
            'particulate_pollutant': 'Particulate P (kg)',
            'total_pollutant': 'Total P (kg)',
        }
        ebe_df.rename(columns=rename_map, inplace=True)

        if first_year is not None and 'Year' in ebe_df:
            mask = ebe_df['Year'] < 1000
            if mask.any() and 'simulation_year' in ebe_df:
                ebe_df.loc[mask, 'Year'] = ebe_df.loc[mask, 'simulation_year'].astype(int) + first_year - 1

        for col in ('Year', 'Month', 'Day', 'Julian', 'Water Year'):
            if col in ebe_df:
                ebe_df[col] = ebe_df[col].astype(int, copy=False)

        if 'Sediment Yield (kg)' in ebe_df and 'Sed Del (kg)' not in ebe_df:
            ebe_df['Sed Del (kg)'] = ebe_df['Sediment Yield (kg)']
        elif 'Sed Del (kg)' not in ebe_df:
            ebe_df['Sed Del (kg)'] = np.nan

        chan_table = pq.read_table(chan_path)
        chan_df = chan_table.to_pandas()

        if chan_df.empty:
            ebe_df['Streamflow (mm)'] = np.nan
        else:
            chan_rename = {
                'year': 'Year',
                'month': 'Month',
                'day_of_month': 'Day',
                'julian': 'Julian',
                'water_year': 'Water Year',
            }
            chan_df.rename(columns=chan_rename, inplace=True)

            for col in ('Year', 'Month', 'Day'):
                if col in chan_df:
                    chan_df[col] = chan_df[col].astype(int, copy=False)

            if wsarea_m2 > 0 and 'Outflow (m^3)' in chan_df:
                chan_df['Streamflow (mm)'] = chan_df['Outflow (m^3)'] / wsarea_m2 * 1000.0
            else:
                chan_df['Streamflow (mm)'] = np.nan

            agg_map = {'Streamflow (mm)': 'sum'}
            if 'Julian' in chan_df:
                agg_map['Julian'] = 'first'
            if 'Water Year' in chan_df:
                agg_map['Water Year'] = 'first'

            chan_daily = chan_df.groupby(['Year', 'Month', 'Day'], as_index=False).agg(agg_map)
            chan_daily = chan_daily.rename(columns={
                'Streamflow (mm)': '_chan_streamflow',
                'Julian': '_chan_julian',
                'Water Year': '_chan_water_year',
            })

            ebe_df = ebe_df.merge(chan_daily, on=['Year', 'Month', 'Day'], how='left')
            if '_chan_streamflow' in ebe_df:
                ebe_df['Streamflow (mm)'] = ebe_df['_chan_streamflow']
                ebe_df.drop(columns=['_chan_streamflow'], inplace=True)
            else:
                ebe_df['Streamflow (mm)'] = np.nan

            if '_chan_julian' in ebe_df:
                ebe_df['Julian'] = ebe_df['Julian'].fillna(ebe_df['_chan_julian'])
                ebe_df.drop(columns=['_chan_julian'], inplace=True)

            if '_chan_water_year' in ebe_df:
                ebe_df['Water Year'] = ebe_df['Water Year'].fillna(ebe_df['_chan_water_year'])
                ebe_df.drop(columns=['_chan_water_year'], inplace=True)

        if 'simulation_year' in ebe_df:
            ebe_df.drop(columns=['simulation_year'], inplace=True)

        ebe_df.sort_values(['Year', 'Julian', 'Day'], inplace=True, ignore_index=True)
        return ebe_df

    def _write_measure(self, Qm, Qo, dates, measure, hillorChannel, dailyorYearly):
        assert len(Qm) == len(Qo)
        assert len(Qm) == len(dates)

        fn = '%s-%s-%s.csv' % (hillorChannel, measure, dailyorYearly)
        fn = fn.replace(' ', '_')
        fn = _join(self.observed_dir, fn)
        with open(fn, 'w') as fn:
            fn.write('date,Modeled,Observed\n')

            for m, o, d in zip(Qm, Qo, dates):
                fn.write('%s,%f,%f\n' % (d, m, o))
