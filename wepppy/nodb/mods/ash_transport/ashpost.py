# Copyright (c) 2016-2023, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.


import os
from glob import glob
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from glob import glob
from copy import deepcopy

import shutil
import math

# non-standard
import jsonpickle
import numpy as np
import pandas as pd
import dask.dataframe as dd

from wepppy.all_your_base import isfloat
from wepppy.all_your_base.stats import probability_of_occurrence, weibull_series

from wepppy.nodb.base import NoDbBase

from pprint import pprint

common_cols =  ['area (ha)', 'topaz_id', 'year', 'mo', 'da', 'julian', 'year0', 'days_from_fire (days)', 'burn_class']

out_cols = ['year0', 'year', 'julian', 'days_from_fire (days)',
            'wind_transport (tonne/ha)', 'water_transport (tonne/ha)', 'ash_transport (tonne/ha)',
            'ash_depth (mm)', 'transportable_ash (tonne/ha)']


def calculate_return_periods(df, measure, recurrence, num_fire_years, cols_to_extract):

    measure_rank = measure.replace(' (tonne)', '_rank')\
                          .replace(' (days)', '_rank')
    measure_ri = measure.replace(' (tonne)', '_ri')\
                        .replace(' (days)', '_ri')
    measure_poo = measure.replace(' (tonne)', '_probability')\
                         .replace(' (days)', '_probability')

    cols_to_extract = [measure, measure_rank, measure_ri, measure_poo] + cols_to_extract

    df.sort_values(by=measure, ascending=False, inplace=True)

    df[measure_rank] = df[measure].rank(ascending=False)
    df[measure_ri] = (num_fire_years + 1) / df[measure_rank]
    df[measure_poo] = df[measure_ri].apply(lambda ri: probability_of_occurrence(ri, 1.0))

    rec = weibull_series(recurrence, num_fire_years)

    num_events = (df[measure] > 0).sum()
    return_periods= {}
    for retperiod in recurrence:
        if retperiod not in rec:
            return_periods[retperiod] = { measure: 0,
                                          'probability': 0,
                                          'rank': 0,
                                          'ri': 0 }
        else:
            indx = rec[retperiod]
            if indx >= num_events:
                return_periods[retperiod] = { measure: 0,
                                              'probability': 0,
                                              'rank': 0,
                                              'ri': 0 }
            else:
                _row = df.iloc[indx][cols_to_extract].to_dict()
                for _m in _row:
                    if _m in ('year0', 'year', 'mo', 'da', 'days_from_fire (days)', measure_rank):
                        _row[_m] = int(_row[_m])
                    elif isfloat(_row[_m]):
                        _row[_m] = float(_row[_m])
                    else:
                        _row[_m] = str(_row[_m])

                _row['probability'] = _row[measure_poo]
                _row['rank'] = _row[measure_rank]
                _row['ri'] = _row[measure_ri]

                del _row[measure_poo]
                del _row[measure_rank]
                del _row[measure_ri]

                return_periods[retperiod] = _row

    return return_periods


def calculate_cumulative_transport(df, recurrence, ash_post_dir):

    # group the filtered rows by year0 and aggregate the cum_ columns and weighted average of days_from_fire
    agg_d = {'days_from_fire (days)': 'first'}

    for col_name in df.columns:
        if col_name.startswith('cum_'):
            agg_d[col_name] = 'sum'

    df_agg = df.groupby('year0').agg(agg_d)

    # create a new dataframe with one row per unique year
    cum_df = pd.DataFrame({'year0': df['year0'].unique()})

    # merge the aggregated data with the new dataframe
    cum_df = pd.merge(cum_df, df_agg, on='year0')
    df.to_pickle(_join(ash_post_dir, 'watershed_cumulatives.pkl'))

    # calculate return intervals and probabilities for cumulative results
    num_fire_years = len(cum_df)
    cum_return_periods = {}
    cols_to_extract = ['year0']

    for measure in ['cum_wind_transport (tonne)', 'cum_water_transport (tonne)',
                    'cum_ash_transport (tonne)', 'days_from_fire (days)']:
        cum_return_periods[measure] = calculate_return_periods(cum_df, measure, recurrence, num_fire_years,
                                                               cols_to_extract)

    return cum_return_periods


def calculate_hillslope_statistics(df, ash, ash_post_dir):
    agg_d = { 'wind_transport (tonne/ha)': 'sum',
              'water_transport (tonne/ha)': 'sum',
              'ash_transport (tonne/ha)': 'sum' }

    # group the dataframe by topaz_id and year, and calculate the sum of x within each group
    df_hillslope_annuals = df.groupby(['topaz_id', 'year']).agg(agg_d).reset_index()
    df_hillslope_average_annuals = df_hillslope_annuals.groupby('topaz_id').mean().reset_index()
    df_hillslope_average_annuals['ash_ini_depth (mm)'] = \
        df['topaz_id'].apply(lambda topaz_id: ash.get_ini_ash_depth(topaz_id))
    df_hillslope_average_annuals.drop('year', axis=1, inplace=True)
    df_hillslope_average_annuals.to_pickle(_join(ash_post_dir, 'hillslope_annuals.pkl'))


def calculate_watershed_statisics(df, ash_post_dir, recurrence):
    global common_cols

    measures = ['wind_transport (tonne)', 'water_transport (tonne)', 'ash_transport (tonne)']

    ws_cols_to_drop = ['date_int', 'topaz_id']
    for col in ['year0', 'da', 'mo', 'julian', 'year']:
        if col in out_cols:
            ws_cols_to_drop.append(col)

    agg_d = {}
    for col in df.columns:
        if 'm^3' in col or 'tonne':
            agg_d[col] = 'sum'
        if col in common_cols:
            agg_d[col] = 'first'

        if 'mm' in col or 'tonne/ha' in col or col.startswith('cum_'):
            ws_cols_to_drop.append(col)

    df_annuals = df.groupby('year').agg(agg_d)
    df_annuals.drop(ws_cols_to_drop, axis=1, inplace=True)
    df_annuals.to_pickle(_join(ash_post_dir, 'watershed_annuals.pkl'))

    del df_annuals

    df_daily = df.groupby('date_int').agg(agg_d)
    df_daily.to_pickle(_join(ash_post_dir, 'watershed_daily.pkl'))

    num_days = len(df_daily.julian)
    num_fire_years = num_days / 365.25
    return_periods = {}
    cols_to_extract = ['days_from_fire (days)']

    for measure in measures:
        return_periods[measure] = calculate_return_periods(df_daily, measure, recurrence, num_fire_years,
                                                           cols_to_extract)

    # Group the DataFrame by 'date_int' and 'burn_class' columns
    grouped_df = df.groupby(['date_int', 'burn_class']).agg(agg_d)

    # Pivot the multi-level index to have burn_class as columns
    df_daily = grouped_df.unstack(level='burn_class')

    # Compute the number of days and fire years
    num_days = len(df_daily.index)
    num_fire_years = num_days / 365.25

    # Initialize the return_periods dictionary
    burn_class_return_periods = {burn_class: {} for burn_class in [1, 2, 3, 4]}

    # Iterate through burn classes and calculate return_periods for each one
    burn_classes_present = df['burn_class'].unique()
    for burn_class in [1, 2, 3, 4]:
        cols_to_extract = ['days_from_fire (days)']
        for measure in measures:
            # Calculate return_periods using the values for the current burn_class
            if burn_class in  burn_classes_present:
                burn_class_return_periods[burn_class][measure] = calculate_return_periods(
                    df_daily.xs(burn_class, axis=1, level='burn_class'),
                    measure,
                    recurrence,
                    num_fire_years,
                    cols_to_extract
                )
            else:
                burn_class_return_periods[burn_class][measure] = {rec: {measure: 0} for rec in recurrence}

    return return_periods, burn_class_return_periods


def read_hillslope_out_fn(out_fn, meta_data=None, meta_data_types=None, cumulative=False):
    global common_cols, out_cols

    if cumulative:
        df = pd.read_parquet(out_fn)
    else:
        df = pd.read_parquet(out_fn, columns=out_cols)

    if meta_data is not None:
        for key, value in meta_data.items():
            if meta_data_types and key in meta_data_types and meta_data_types[key] == 'category':
                df[key] = pd.Categorical([value] * len(df))
            else:
                df[key] = pd.Series([value] * len(df)).astype(meta_data_types.get(key) if meta_data_types else None)

    # Create a unique index from year and julian columns
    df['date_int'] = df['year'] * 1000 + df['julian']
    df.set_index('date_int', inplace=True)

    # Select columns to aggregate
    agg_d = {}
    for col in df.columns:
        if '(mm)' in col or '(tonne/ha)' in col or '(gm/cm3)' in col:
            agg_d[col] = 'sum'
        if col in common_cols:
            agg_d[col] = 'first'

    # Pivot and aggregate the data
    df_agg =  df.groupby('date_int').agg(agg_d)

    # Reset the index to get a dataframe with one row per unique combination of year, julian, and topaz_id
    df_agg.reset_index(inplace=True)

    area_ha = float(df_agg['area (ha)'].iloc[0])

    # Convert columns in tonne/ha to tonne by multiplying by area_ha
    for col in df_agg.columns:
        if 'tonne/ha' in col:
            df_agg[col.replace('tonne/ha', 'tonne')] = df_agg[col] * area_ha

    # Convert columns in mm to m^3 using area_ha
    for col in df_agg.columns:
        if 'mm' in col:
            df_agg[col.replace('mm', 'm^3')] = ( df_agg[col] * 0.001) *  (area_ha * 10000)

    if cumulative:
        df_agg = df_agg[df_agg['transportable_ash (tonne/ha)'] == 0.0]
    return df_agg


def calculate_cum_watershed_stats_by_burnclass(cum_df):
    """
    cum_df cols
    Data columns (total 55 columns):
 #   Column                          Non-Null Count  Dtype
---  ------                          --------------  -----
 0   date_int                        295 non-null    int64
 1   year0                           295 non-null    uint16
 2   year                            295 non-null    uint16
 3   da                              295 non-null    uint16
 4   mo                              295 non-null    uint16
 5   julian                          295 non-null    int16
 6   days_from_fire (days)           295 non-null    int64
 7   precip (mm)                     295 non-null    float32
 8   rainmelt (mm)                   295 non-null    float32
 9   snow_water_equivalent (mm)      295 non-null    float32
 10  runoff (mm)                     295 non-null    float32
 11  tot_soil_water (mm)             295 non-null    float32
 12  infiltration (mm)               295 non-null    float32
 13  cum_infiltration (mm)           295 non-null    float32
 14  cum_runoff (mm)                 295 non-null    float32
 15  bulk_density (gm/cm3)           295 non-null    float64
 16  remaining_ash (tonne/ha)        295 non-null    float64
 17  transportable_ash (tonne/ha)    295 non-null    float64
 18  ash_depth (mm)                  295 non-null    float64
 19  ash_runoff (mm)                 295 non-null    float64
 20  transport (tonne/ha)            295 non-null    float64
 21  cum_ash_runoff (mm)             295 non-null    float64
 22  water_transport (tonne/ha)      295 non-null    float64
 23  wind_transport (tonne/ha)       295 non-null    float64
 24  ash_transport (tonne/ha)        295 non-null    float64
 25  ash_decomp (tonne/ha)           295 non-null    float64
 26  cum_water_transport (tonne/ha)  295 non-null    float64
 27  cum_wind_transport (tonne/ha)   295 non-null    float64
 28  cum_ash_transport (tonne/ha)    295 non-null    float64
 29  cum_ash_decomp (tonne/ha)       295 non-null    float64
 30  topaz_id                        295 non-null    uint16
 31  area (ha)                       295 non-null    float32
 32  burn_class                      295 non-null    uint8
 33  remaining_ash (tonne)           295 non-null    float64
 34  transportable_ash (tonne)       295 non-null    float64
 35  transport (tonne)               295 non-null    float64
 36  water_transport (tonne)         295 non-null    float64
 37  wind_transport (tonne)          295 non-null    float64
 38  ash_transport (tonne)           295 non-null    float64
 39  ash_decomp (tonne)              295 non-null    float64
 40  cum_water_transport (tonne)     295 non-null    float64
 41  cum_wind_transport (tonne)      295 non-null    float64
 42  cum_ash_transport (tonne)       295 non-null    float64
 43  cum_ash_decomp (tonne)          295 non-null    float64
 44  precip (m^3)                    295 non-null    float32
 45  rainmelt (m^3)                  295 non-null    float32
 46  snow_water_equivalent (m^3)     295 non-null    float32
 47  runoff (m^3)                    295 non-null    float32
 48  tot_soil_water (m^3)            295 non-null    float32
 49  infiltration (m^3)              295 non-null    float32
 50  cum_infiltration (m^3)          295 non-null    float32
 51  cum_runoff (m^3)                295 non-null    float32
 52  ash_depth (m^3)                 295 non-null    float64
 53  ash_runoff (m^3)                295 non-null    float64
    """

    # Group the DataFrame by 'burn_class' column
    grouped_df = cum_df.groupby('burn_class')

    # Compute the count and mean for the specified columns
    result = grouped_df.agg(
        {
            'cum_water_transport (tonne)': ['count', 'mean'],
            'cum_wind_transport (tonne)': ['mean'],
            'cum_ash_transport (tonne)': ['mean'],
        }
    )

    # Initialize the dictionary with default values
    pw0_stats = {
        burn_class: {
            'count': 0,
            'cum_water_transport (tonne)': 0,
            'cum_wind_transport (tonne)': 0,
            'cum_ash_transport (tonne)': 0,
        }
        for burn_class in [1, 2, 3, 4]
    }

    # Iterate through the result DataFrame and update the values in the dictionary
    for index, row in result.iterrows():
        pw0_stats[index] = {
            'count': int( row[('cum_water_transport (tonne)', 'count') ] ),
            'cum_water_transport (tonne)': float( row[('cum_water_transport (tonne)', 'mean') ] ),
            'cum_wind_transport (tonne)': float( row[('cum_wind_transport (tonne)', 'mean') ] ),
            'cum_ash_transport (tonne)': float( row[('cum_ash_transport (tonne)', 'mean') ] ),
        }

    return pw0_stats


def watershed_daily_aggregated(wd,  recurrence=(1000, 500, 200, 100, 50, 25, 20, 10, 5, 2), verbose=True):
    #
    # Setup stuff
    #

    from wepppy.nodb import Watershed
    from wepppy.nodb import Ash

    # Get NoDB instances
    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()
    ash = Ash.getInstance(wd)

    ash_post_dir = _join(ash.ash_dir, 'post')
    os.makedirs(ash_post_dir, exist_ok=True)

    #
    # Read all hillslope output files to a single df
    #

    # loop over the hillslopes and read their ash output files.
    hill_data_frames = []
    for topaz_id, summary in watershed.subs_summary.items():
        # get the wepp_id
        wepp_id = translator.wepp(top=topaz_id)

        # get the burn class
        burn_class = ash.meta[topaz_id]['burn_class']

        # get the area in hectares
        area_m2 = summary['area']
        area_ha = area_m2 / 10000


        # get the list of output files
        out_fn = _join(ash.ash_dir, f'H{wepp_id}_ash.parquet')

        if _exists(out_fn):
            # read the output files into dataframes and append them to hill_data_frames
            meta = {"topaz_id": topaz_id, "area (ha)": area_ha, "burn_class": burn_class}
            meta_dtypes = {"topaz_id": "uint16", "area (ha)": "float32", "burn_class": "uint8"}
            hill_data_frames.append(read_hillslope_out_fn(out_fn,
                meta_data=meta,
                meta_data_types=meta_dtypes))

    if hill_data_frames == []:
        return None


    # Combine all data into a single DataFrame
    df = pd.concat(hill_data_frames, ignore_index=True)

    calculate_hillslope_statistics(df, ash, ash_post_dir)

    return_periods, burn_class_return_periods = calculate_watershed_statisics(df, ash_post_dir, recurrence)

    del df
    del hill_data_frames

    # Calculate cumulative return periods
    # read the last day of each fire run
    hill_data_frames = []
    for topaz_id, summary in watershed.subs_summary.items():
        # get the wepp_id
        wepp_id = translator.wepp(top=topaz_id)

        # get the burn class
        burn_class = ash.meta[topaz_id]['burn_class']

        # get the area in hectares
        area_m2 = summary['area']
        area_ha = area_m2 / 10000


        # get the list of output files
        out_fn = _join(ash.ash_dir, f'H{wepp_id}_ash.parquet')

        if _exists(out_fn):
            # read the output files into dataframes and append them to hill_data_frames
            meta = {"topaz_id": topaz_id, "area (ha)": area_ha, "burn_class": burn_class}
            meta_dtypes = {"topaz_id": "uint16", "area (ha)": "float32", "burn_class": "uint8"}
            hill_data_frames.append(read_hillslope_out_fn(out_fn,
                meta_data=meta, meta_data_types=meta_dtypes, cumulative=True))

    # combine to single dataframe
    df = pd.concat(hill_data_frames, ignore_index=True)

    cum_return_periods = calculate_cumulative_transport(df, recurrence, ash_post_dir)
    pw0_stats = calculate_cum_watershed_stats_by_burnclass(df)

    del df
    del hill_data_frames

    # return all the results
    return return_periods, cum_return_periods, burn_class_return_periods, pw0_stats



class AshPostNoDbLockedException(Exception):
    pass


class AshPost(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'AshPost'

    def __init__(self, wd, cfg_fn):
        super(AshPost, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._return_periods = None
            self._cum_return_periods = None
            self._pw0_stats = None
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'ashpost.nodb')) as fp:
            db = jsonpickle.decode(fp.read().replace('"pw0_stats"', '"_pw0_stats"'))
            assert isinstance(db, AshPost), db

            if _exists(_join(wd, 'READONLY')):
                db.wd = os.path.abspath(wd)
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'ashpost.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'ashpost.nodb.lock')

    @property
    def return_periods(self):
        return self._return_periods

    @property
    def burn_class_return_periods(self):
        return self._burn_class_return_periods

    @property
    def cum_return_periods(self):
        return self._cum_return_periods

    @property
    def pw0_stats(self):

        meta = self.meta

        # Initialize the dictionary with default values
        pw0_stats = {
            burn_class: {
                'count': 0,
                'cum_water_transport (tonne)': 0,
                'cum_wind_transport (tonne)': 0,
                'cum_ash_transport (tonne)': 0,
            }
            for burn_class in ['1', '2', '3', '4']
        }

        for topaz_id, hill_annuals in self.hillslope_annuals.items():
            burn_class = str(meta[topaz_id]['burn_class'])
            area_ha = meta[topaz_id]['area_ha']

            pw0_stats[burn_class]['cum_water_transport (tonne)'] += hill_annuals['water_transport (tonne/ha)'] * area_ha
            pw0_stats[burn_class]['cum_wind_transport (tonne)'] += hill_annuals['wind_transport (tonne/ha)'] * area_ha
            pw0_stats[burn_class]['cum_ash_transport (tonne)'] += hill_annuals['ash_transport (tonne/ha)'] * area_ha

        return pw0_stats

    @property
    def recurrence_intervals(self):
        rec_int = sorted([int(k) for k in self._return_periods['ash_transport (tonne)']])
        return [str(k) for k in rec_int]

    def run_post(self, recurrence=(1000, 500, 200, 100, 50, 25, 20, 10, 5, 2)):
        self.lock()

        # noinspection PyBroadException
        try:
            res = watershed_daily_aggregated(self.wd, recurrence=recurrence)
            if res != None:
                self._return_periods, self._cum_return_periods, self._burn_class_return_periods, self._pw0_stats = res

            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def meta(self):
        from wepppy.nodb import Ash
        ash = Ash.getInstance(self.wd)
        return ash.meta

    @property
    def fire_date(self):
        from wepppy.nodb import Ash
        ash = Ash.getInstance(self.wd)
        return ash.fire_date

    @property
    def ash_post_dir(self):
        return _join(self.ash_dir, 'post')


    @property
    def hillslope_annuals(self):
        df = pd.read_pickle(_join(self.ash_post_dir, 'hillslope_annuals.pkl'))
        d = {}
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            topaz_id = row_dict['topaz_id']
            d[str(int(topaz_id))] = row_dict
        return d

    @property
    def watershed_annuals(self):
        df = pd.read_pickle(_join(self.ash_post_dir, 'watershed_annuals.pkl'))
        d = {}
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            topaz_id = row_dict['topaz_id']
            d[str(int(topaz_id))] = row_dict
        return d
