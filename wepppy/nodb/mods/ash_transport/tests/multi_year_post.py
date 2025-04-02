import os
from glob import glob
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import pandas as pd
import numpy as np

from pprint import pprint

from wepppy.nodb import Watershed
from wepppy.nodb.mods import Ash
import sys

common_cols =  ['area (ha)', 'topaz_id', 'year', 'mo', 'da', 'julian', 'year0', 'days_from_fire (days)']


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
            return_periods[retperiod] = None
        else:
            indx = rec[retperiod]
            if indx >= num_events:
                return_periods[retperiod] = None
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
    # filter the rows where transportable_ash (tonne) equals 0.0
    df_filtered = df[df['transportable_ash (tonne/ha)'] == 0.0]

    # group the filtered rows by year0 and aggregate the cum_ columns and weighted average of days_from_fire
    agg_d = {'days_from_fire (days)': lambda x: (x * df_filtered['area (ha)']).sum() /
                                                df_filtered['area (ha)'].sum()}
    for col_name in df.columns:
        if col_name.startswith('cum_'):
            agg_d[col_name] = 'sum'

    df_agg = df_filtered.groupby('year0').agg(agg_d)

    # create a new dataframe with one row per unique year
    cum_df = pd.DataFrame({'year0': df_filtered['year0'].unique()})

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


#    print('Cumulative Watershed Return Periods')
#    pprint(cum_return_periods)

        return cum_return_periods


def calculate_hillslope_statistics(df, ash, ash_post_dir):
    agg_d = { 'wind_transport (tonne/ha)': 'sum',
              'water_transport (tonne/ha)': 'sum',
              'ash_transport (tonne/ha)': 'sum' }


    # TODO: this doesn't know that ash is ran until it is all transported. this could take several years and causes the
    # average annuals to be incorrect

    # group the dataframe by topaz_id and year, and calculate the sum of x within each group
    df_hillslope_annuals = df.groupby(['topaz_id', 'year']).agg(agg_d).reset_index()
    df_hillslope_average_annuals = df_hillslope_annuals.groupby('topaz_id').mean().reset_index()
    df_hillslope_average_annuals['ash_ini_depth (mm)'] = \
        df['topaz_id'].apply(lambda topaz_id: ash.get_ini_ash_depth(topaz_id))
    df_hillslope_average_annuals.drop('year', axis=1, inplace=True)
    df_hillslope_average_annuals.to_pickle(_join(ash_post_dir, 'hillslope_annuals.pkl'))

#    print('Hillslope Averages')
#    print(df_hillslope_average_annuals)


def calculate_watershed_statisics(df, ash_post_dir, recurrence):
    ws_cols_to_drop = ['date_int', 'year0', 'da', 'mo', 'julian', 'year', 'topaz_id']
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

    #    print('Watershed Annuals')
    #    print(df_annuals)
    #    print(df_annuals.columns)

    df_daily = df.groupby('date_int').agg(agg_d)
    df_daily.to_pickle(_join(wd, 'ash', 'watershed_daily.pkl'))

    num_days = len(df_daily.julian)
    num_fire_years = num_days / 365.25
    return_periods = {}
    cols_to_extract = ['year', 'mo', 'da']

    for measure in ['wind_transport (tonne)', 'water_transport (tonne)', 'ash_transport (tonne)']:
        return_periods[measure] = calculate_return_periods(df_daily, measure, recurrence, num_fire_years,
                                                           cols_to_extract)

#    print('Watershed Return Periods')
#    pprint(return_periods)

    return return_periods


def read_hillslope_out_fns(file_list, meta_data=None):

    data_frames = []
    for file_path in file_list:
        data_frames.append(pd.read_csv(file_path))

    # Combine all data into a single DataFrame
    df = pd.concat(data_frames, ignore_index=True)

    if meta_data is not None:
        for key, value in meta_data.items():
            df[key] = pd.Series([value] * len(df))

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

    return df_agg


def watershed_daily_aggregated(wd,  recurrence=(1000, 500, 200, 100, 50, 25, 20, 10, 5, 2)):
    #
    # Setup stuff
    #

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

        # get the area in hectares
        area_m2 = summary['area']
        area_ha = area_m2 / 10000

        # get the list of output files
        out_fns = glob(_join(ash.ash_dir, f'H{wepp_id}_*.csv'))

        # read the output files into dataframes and append them to hill_data_frames
        hill_data_frames.append(read_hillslope_out_fns(out_fns, meta_data={"topaz_id": topaz_id, "area (ha)": area_ha}))

    # Combine all data into a single DataFrame
    df = pd.concat(hill_data_frames, ignore_index=True)

    cum_return_periods = calculate_cumulative_transport(df, recurrence, ash_post_dir)
    calculate_hillslope_statistics(df, ash, ash_post_dir)
    return_periods = calculate_watershed_statisics(df, ash_post_dir, recurrence)

    return return_periods, cum_return_periods


if __name__ == "__main__":
    from wepppy.nodb.mods.ash_transport import Ash
    from wepppy.nodb.mods.ash_transport.ash_multi_year_model import *

    wd = '/geodata/weppcloud_runs/squab-salami'

    #df = watershed_daily_aggregated(wd)

    #print(df)

    pkl = _join(wd, 'ash', 'hillslope_annuals.pkl')
    df = pd.read_pickle(pkl)

    for d in df:
        print(d)