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

common_cols =  ['area (ha)', 'topaz_id', 'year', 'mo', 'da', 'julian', 'days_from_fire (days)', 'year0', 'burn_class']

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
            if indx > num_events - 1:
                indx = num_events - 1

            _row = df.iloc[indx][cols_to_extract].to_dict()
            for _m in _row:
                if _m in ('date_int', 'year0', 'year', 'mo', 'da', 'days_from_fire (days)', measure_rank):
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
    df_hillslope_average_annuals.drop('year', axis=1, inplace=True)
    df_hillslope_average_annuals.to_pickle(_join(ash_post_dir, 'hillslope_annuals.pkl'))


def calculate_watershed_statisics(df, ash_post_dir, recurrence, burn_classes=[1, 2, 3]):
    global common_cols

    #df.to_pickle(_join(ash_post_dir, 'full.pkl'))

    measures = ['wind_transport (tonne)', 'water_transport (tonne)', 'ash_transport (tonne)']

    ws_cols_to_drop = ['date_int', 'topaz_id']
    for col in ['da', 'mo', 'julian']:
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

    df_daily = df.groupby(['year0', 'year', 'julian']).agg(agg_d)
    df_daily.to_pickle(_join(ash_post_dir, 'watershed_daily.pkl'))

    num_days = len(df_daily.julian)
    num_fire_years = num_days / 365.25
    return_periods = {}
    cols_to_extract = ['days_from_fire (days)', 'year0', 'year', 'julian']

    # Group the DataFrame by 'date_int' and 'burn_class' columns
    grouped_df = df.groupby(['year0', 'year', 'julian', 'burn_class']).agg(agg_d)
    grouped_df.to_pickle(_join(ash_post_dir, 'watershed_daily_by_burn_class.pkl'))

    # Initialize the return_periods dictionary
    burn_class_return_periods = {}
    for burn_class in burn_classes:
        burn_class_return_periods[burn_class] = {}
        for measure in measures:
            burn_class_return_periods[burn_class][measure] = {}
            for rec in recurrence:
                burn_class_return_periods[burn_class][measure][rec] = {}

    for measure in measures:
        return_periods[measure] = calculate_return_periods(df_daily, measure, recurrence, num_fire_years,
                                                           cols_to_extract)

        for rec in return_periods[measure]:
            v = return_periods[measure][rec][measure]

            year0 = return_periods[measure][rec].get('year0', None)
            year = return_periods[measure][rec].get('year', None)
            julian = return_periods[measure][rec].get('julian', None)

            for burn_class in burn_classes:
                burn_class_return_periods[burn_class][measure][rec] = deepcopy(return_periods[measure][rec])
                burn_class_return_periods[burn_class][measure][rec][measure] = 0.0

                if v == 0:
                    continue

                # Calculate return_periods using the values for the current burn_class
                # Boolean indexing to filter rows

                filtered_df = grouped_df[(grouped_df['year0'] == np.uint16(year0)) &
                                         (grouped_df['year'] == np.uint16(year)) &
                                         (grouped_df['julian'] == np.uint16(julian)) &
                                         (grouped_df['burn_class'] == np.uint8(burn_class))]

                num_rows = len(filtered_df)

                if num_rows == 0:
                    continue
                elif num_rows == 1:
                    burn_class_return_periods[burn_class][measure][rec][measure] = float(filtered_df.iloc[0][measure])
                else:
                    raise Exception('Unexpected number of rows: {}'.format(num_rows))

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
    print('hill_data_frames', hill_data_frames)

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

    del df
    del hill_data_frames

    # return all the results
    return return_periods, cum_return_periods, burn_class_return_periods



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
                self._return_periods, self._cum_return_periods, self._burn_class_return_periods = res
            else:
                self._return_periods, self._cum_return_periods, self._burn_class_return_periods = None, None, None

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

    @property
    def ash_out(self):
        ash_out = self.meta
        hillslope_annuals = self.hillslope_annuals

        for topaz_id in ash_out:
            if ash_out[topaz_id]['ash_type'] is None or topaz_id not in hillslope_annuals:
                ash_out[topaz_id]['water_transport (kg/ha)'] = 0.0
                ash_out[topaz_id]['wind_transport (kg/ha)'] = 0.0
                ash_out[topaz_id]['ash_transport (kg/ha)'] = 0.0
                ash_out[topaz_id]['ash_ini_depth (mm)'] = 0.0
            else:
                ash_out[topaz_id]['water_transport (kg/ha)'] = hillslope_annuals[topaz_id]['water_transport (tonne/ha)'] * 1000.0
                ash_out[topaz_id]['wind_transport (kg/ha)'] = hillslope_annuals[topaz_id]['wind_transport (tonne/ha)'] * 1000.0
                ash_out[topaz_id]['ash_transport (kg/ha)'] = hillslope_annuals[topaz_id]['ash_transport (tonne/ha)'] * 1000.0
                ash_out[topaz_id]['ash_ini_depth (mm)'] = ash_out[topaz_id]['ini_ash_depth']
                ash_out[topaz_id]['area (ha)'] = ash_out[topaz_id]['area_ha']

            if 'ini_ash_depth' in ash_out[topaz_id]:
                del ash_out[topaz_id]['ini_ash_depth']

            del ash_out[topaz_id]['area_ha']

        return ash_out
