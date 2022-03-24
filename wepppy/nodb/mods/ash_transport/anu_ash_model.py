from typing import Optional
import math
import enum
import json
import os
from os.path import join as _join

import numpy as np

from copy import deepcopy
import pandas as pd
import matplotlib.pyplot as plt

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.all_your_base.stats import weibull_series, probability_of_occurrence

from wepppy.wepp.out import HillWat

from .wind_transport_thresholds import *

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

pd.options.mode.chained_assignment = None  # default='warn'

class AshType(enum.IntEnum):
    BLACK = 0
    WHITE = 1


class AshNoDbLockedException(Exception):
    pass


WHITE_ASH_BD = 0.31
BLACK_ASH_BD = 0.22


class AshModel(object):
    """
    Base class for the hillslope ash models. This class is inherited by
    the WhiteAshModel and BlackAshModel classes
    """

    def __init__(self,
                 ash_type: AshType,
                 ini_bulk_den=None,
                 fin_bulk_de=None,
                 bulk_den_fac=None,
                 par_den=None,
                 decomp_fac=None,
                 ini_erod=None,
                 fin_erod=None,
                 roughness_limit=None):
        self.ash_type = ash_type
        self.ini_ash_depth_mm = None
        self.ini_ash_load_tonneha = None
        self.ini_bulk_den = WHITE_ASH_BD,  # Initial bulk density, gm/cm3
        self.fin_bulk_de = 0.62,  # Final bulk density, gm/cm3
        self.bulk_den_fac = 0.005,  # Bulk density factor
        self.par_den = 1.2,  # Ash particle density, gm/cm3
        self.decomp_fac = 0.00018  # Ash decomposition factor, per day
        self.ini_erod = 1  # Initial erodibility, t/ha
        self.fin_erod = 0.01  # Final erodibility, t/ha
        self.roughness_limit = 1  # Roughness limit, mm

    @property
    def ini_material_available_mm(self):
        print('proportion', self.proportion, type(self.proportion))
        print('ini_ash_depth_mm', self.ini_ash_depth_mm, type(self.ini_ash_depth_mm))
        return self.proportion * self.ini_ash_depth_mm

    @property
    def ini_material_available_tonneperha(self):
        if self.ini_ash_load_tonneha is not None:
            return self.ini_ash_load_tonneha
        else:
            return 10.0 * self.ini_material_available_mm * self.bulk_density

#    @property
#    def water_retention_capacity_at_sat(self):
#        return self.fraction_water_retention_capacity_at_sat * self.ini_ash_depth_mm

    def lookup_wind_threshold_proportion(self, w):
        if w == 0.0:
            return 0.0

        if self.ash_type == AshType.BLACK:
            return lookup_wind_threshold_black_ash_proportion(w)
        elif self.ash_type == AshType.WHITE:
            return lookup_wind_threshold_white_ash_proportion(w)

    def run_model(self, fire_date: YearlessDate, element_d, cli_df: pd.DataFrame, hill_wat: HillWat, out_dir, prefix,
                  recurrence=[100, 50, 25, 20, 10, 5, 2],
                  area_ha: Optional[float] = None,
                  ini_ash_depth: Optional[float] = None,
                  ini_ash_load: Optional[float] = None, run_wind_transport=True, model='neris'):
        """
        Runs the ash model for a hillslope

        :param fire_date:
            month, day of fire as a YearlessDate instance
        :param element_d:
            dictionary runoff events from the element WEPP output. The keys are (year, mo, da) and the values contain
            the row data as dictionaries with header keys
        :param cli_df:
            the climate file produced by CLIGEN as a pandas.Dataframe
        :param out_dir:
            the directory save the model output
        :param prefix:
            prefix for the model output file
        :param recurrence:
            list of recurrence intervals
        :return:
            returns the output file name, return period results dictionary
        """


        self.ini_ash_depth_mm = ini_ash_depth
        # self.ini_ash_load_tonneha = ini_ash_load

        # define fire day in julian
        fire_day = fire_date.julian

        # define parameters
        ini_bulk_den = 0.31  # Initial bulk density, gm/cm3
        fin_bulk_de = 0.62  # Final bulk density, gm/cm3
        bulk_den_fac = 0.005  # Bulk density factor
        par_den = 1.2  # Ash particle density, gm/cm3
        decomp_fac = self.decomp_fac  # 0.00018  # Ash decomposition factor, per day
        ini_erod = 1  # Initial erodibility, t/ha
        fin_erod = 0.01  # Final erodibility, t/ha
        roughness_limit = 1  # Roughness limit, mm
        self.ini_ash_depth_mm = ini_ash_depth = ini_ash_depth
        self.ini_ash_load_tonneha = ini_ash_load = ini_ash_load  # 10 * ini_ash_depth * ini_bulk_den   # Initial ash load, t/ha

        col_names = "OFE J Y P RM Q Ep Es Er Dp UpStrmQ SubRIn latqcc Total-Soil-Water frozwt Snow-Water QOFE Tile Irr Area"
        col_names = col_names.split()

        # Units row
        units = "# # # mm mm mm mm mm mm mm mm mm mm mm mm mm mm mm mm m^2"
        units = units.split()

        # Concatenating header and units
        concat_func = lambda x, y: x + "_" + y
        col_names = list(map(concat_func, col_names, units))

        # Skip all rows before actual data
        skipped_rows = range(0, 23)

        watr = pd.read_table(hill_wat.fname, skiprows=skipped_rows, sep='\s+', header=None, names=col_names)

        is_gregorian = not watr['Y_#'].iloc[0] == 1

        # make starting/ending date for stochastic climate
        if is_gregorian:
            starting = '1/1/' + str(watr['Y_#'].iloc[0])
            ending = '12/31/' + str(watr['Y_#'].iloc[-1])
        # make starting/ending date for observed climate
        else:
            starting = '1/1/' + str(watr['Y_#'].iloc[0] + 1900)
            ending = '12/31/' + str(watr['Y_#'].iloc[-1] + 1900)

#        # create ash df
#        df = pd.DataFrame()

        # Get selected variables from watr df to ash df
        ash_df = watr[[
            'J_#', 'Y_#', 'P_mm', 'RM_mm', 'Q_mm', 'Total-Soil-Water_mm',
            'Snow-Water_mm'
        ]]

        # Insert date column to ash df
        ash_df.insert(0, 'Date', pd.date_range(start=starting, end=ending))

        # Define simulation length
        start_date = pd.to_datetime(starting)
        end_date = pd.to_datetime(ending)
        N = (end_date - start_date).days + 1
        idx_sim = (ash_df['Date'] >= start_date) & (ash_df['Date'] <= end_date)

        # Pre-compute some variables
        dates = ash_df.loc[idx_sim, 'Date'].values
        julian = ash_df.loc[idx_sim, 'J_#'].values
        year = ash_df.loc[idx_sim, 'Y_#'].values
        precip = ash_df.loc[idx_sim, 'P_mm'].values
        rm = ash_df.loc[idx_sim, 'RM_mm'].values
        q = ash_df.loc[idx_sim, 'Q_mm'].values
        tsw = ash_df.loc[idx_sim, 'Total-Soil-Water_mm'].values
        swe = ash_df.loc[idx_sim, 'Snow-Water_mm'].values
        da = np.array([pd.Timestamp(date).day for date in dates])
        mo = np.array([pd.Timestamp(date).month for date in dates])
        yr = np.array([pd.Timestamp(date).year for date in dates])

        if not is_gregorian:
            yr = yr - 1900

        # Pre-allocate arrays with NaN values
        days_from_fire = np.ones(N) * np.nan
        fire_year = np.ones(N) * np.nan
        infil_mm = np.ones(N) * np.nan
        cum_infil_mm = np.ones(N) * np.nan
        cum_q_mm = np.ones(N) * np.nan
        bulk_density_gmpcm3 = np.ones(N) * np.nan
        porosity = np.ones(N) * np.nan
        available_ash_tonspha = np.ones(N) * np.nan
        ash_depth_mm = np.ones(N) * np.nan
        ash_runoff_mm = np.ones(N) * np.nan
        transport_tonspha = np.zeros(N)
        water_transport_tonspha = np.zeros(N)
        cum_ash_runoff_mm = np.zeros(N)
        cum_water_transport_tonspha = np.zeros(N)
        wind_transport_tonspha = np.zeros(N)
        cum_wind_transport_tonspha = np.zeros(N)
        ash_transport_tonspha = np.zeros(N)
        cum_ash_transport_tonspha = np.zeros(N)

        # Define initial conditions
        fire_year[0] = watr['Y_#'].iloc[0] - 1
        ash_depth_mm[0] = ini_ash_depth
        available_ash_tonspha[0] = ini_ash_load
        days_from_fire[0] = 0
        infil_mm[0] = 0
        cum_infil_mm[0] = 0
        cum_q_mm[0] = 0
        bulk_density_gmpcm3[0] = ini_bulk_den
        porosity[0] = 1 - (bulk_density_gmpcm3[0] / par_den)
        cum_ash_runoff_mm[0] = 0
        cum_water_transport_tonspha[0] = 0

        # Model
        for t in range(1, N):

            if julian[t] >= fire_day:
                fire_year[t] = year[t]
            else:
                fire_year[t] = year[t] - 1

            if julian[t] == fire_day:
                days_from_fire[t] = 1
            else:
                days_from_fire[t] = days_from_fire[t - 1] + 1

            infil_mm[t] = rm[t] - q[t]

            if julian[t] == fire_day:
                cum_infil_mm[t] = infil_mm[t]
                cum_q_mm[t] = q[t]
                bulk_density_gmpcm3[t] = ini_bulk_den
                porosity[t] = 1 - (bulk_density_gmpcm3[t] / par_den)
            else:
                cum_infil_mm[t] = cum_infil_mm[t - 1] + infil_mm[t]
                cum_q_mm[t] = cum_q_mm[t - 1] + q[t]
                bulk_density_gmpcm3[t] = fin_bulk_de + \
                                         (ini_bulk_den - fin_bulk_de) * \
                                         np.exp(-bulk_den_fac * cum_infil_mm[t])
                porosity[t] = 1 - (bulk_density_gmpcm3[t] / par_den)

            if q[t - 1] > (available_ash_tonspha[t - 1] /
                           (10. * bulk_density_gmpcm3[t - 1])) * porosity[t - 1]:
                ash_runoff_mm[t - 1] = np.maximum(
                    0, q[t - 1] -
                       (available_ash_tonspha[t - 1] /
                        (10. * bulk_density_gmpcm3[t - 1])) * porosity[t - 1])
            else:
                ash_runoff_mm[t - 1] = 0

            if ash_runoff_mm[t - 1] > 0:
                transport_tonspha[t - 1] = (ini_erod - fin_erod) * (
                        bulk_density_gmpcm3[t - 1] -
                        fin_bulk_de) / (ini_bulk_den - fin_bulk_de) + fin_erod

                water_transport_tonspha[t - 1] = np.maximum(
                    0,
                    np.minimum(available_ash_tonspha[t - 1], ash_runoff_mm[t - 1] *
                               transport_tonspha[t - 1]))

                wind_transport_tonspha[t - 1] = 0

            else:
                transport_tonspha[t - 1] = 0
                water_transport_tonspha[t - 1] = 0

                wind_transport_tonspha[t - 1] = 0
                ash_transport_tonspha[t - 1] = 0

            ash_transport_tonspha[t - 1] = wind_transport_tonspha[t - 1] + water_transport_tonspha[t - 1]

            if days_from_fire[t] > 1:

                if ash_depth_mm[t - 1] < roughness_limit:
                    available_ash_tonspha[t] = 0
                else:
                    available_ash_tonspha[t] = available_ash_tonspha[t - 1] * np.exp(-decomp_fac * infil_mm[t]) - \
                                               water_transport_tonspha[t - 1]
            else:
                available_ash_tonspha[t] = ini_ash_load

            ash_depth_mm[t] = available_ash_tonspha[t] / (10. *
                                                          bulk_density_gmpcm3[t])

            if days_from_fire[t] == 1:
                cum_ash_runoff_mm[t] = ash_runoff_mm[t - 1]
                cum_wind_transport_tonspha[t] = 0
                cum_water_transport_tonspha[t] = water_transport_tonspha[t - 1]
            else:
                cum_ash_runoff_mm[t] = cum_ash_runoff_mm[t - 1] + \
                                       ash_runoff_mm[t - 1]
                cum_wind_transport_tonspha[t] = 0
                cum_water_transport_tonspha[t] = cum_water_transport_tonspha[
                                                     t - 1] + water_transport_tonspha[t - 1]

            cum_ash_transport_tonspha[t] = cum_wind_transport_tonspha[t] + cum_water_transport_tonspha[t]

        # convert numpy arrays to pandas dataframe
        my_array = np.array([
            fire_year, yr, da, mo, julian,
            days_from_fire, precip, rm, swe, q, tsw, infil_mm, cum_infil_mm, cum_q_mm,
            bulk_density_gmpcm3, porosity, available_ash_tonspha, ash_depth_mm,
            ash_runoff_mm, transport_tonspha, cum_ash_runoff_mm, water_transport_tonspha,
            wind_transport_tonspha, ash_transport_tonspha,
            cum_water_transport_tonspha, cum_wind_transport_tonspha, cum_ash_transport_tonspha
        ]).T

        index = list(range(0, len(fire_year)))

        columns = [
            'fire_year (yr)', 'year', 'da', 'mo', 'julian', 
            'days_from_fire (days)', 
            'precip (mm)', 'rainmelt (mm)', 'snow water equivalent (mm)', 'runoff (mm)',
            'tot soil water (mm)',
            'infiltration (mm)', 'cum_infiltration (mm)', 'cum_runoff (mm)', 'bulk density (gm/cm3)',
            'porosity', 'available ash (tonne/ha)', 'ash depth (mm)', 'ash runoff (mm)',
            'transport (tonne/ha)', 'cum_ash_runoff (mm)',
            'water_transport (tonne/ha)', 'wind_transport (tonne/ha)', 'ash_transport (tonne/ha)',
            'cum_water_transport (tonne/ha)', 'cum_wind_transport (tonne/ha)', 'cum_ash_transport (tonne/ha)'
        ]

        df = pd.DataFrame(my_array, index, columns)

        if area_ha is not None:
            df['ash_delivery (tonne)'] = pd.Series(ash_transport_tonspha * area_ha, index=df.index)
            df['ash_delivery_by_wind (tonne)'] = pd.Series(wind_transport_tonspha * area_ha, index=df.index)
            df['ash_delivery_by_water (tonne)'] = pd.Series(water_transport_tonspha * area_ha, index=df.index)
            df['cum_ash_delivery (tonne)'] = pd.Series(cum_ash_transport_tonspha * area_ha, index=df.index)
            df['cum_ash_delivery_by_wind (tonne)'] = pd.Series(cum_wind_transport_tonspha * area_ha, index=df.index)
            df['cum_ash_delivery_by_water (tonne)'] = pd.Series(cum_water_transport_tonspha * area_ha, index=df.index)

        # remove the first and the last year
        df = df[(df['year'] > df['year'].iloc[0])
                & (df['year'] < df['year'].iloc[-1])]

        # reset and rename index
        df.reset_index(drop=True, inplace=True)
        df.index.rename("sno", inplace=True)

        # Update date
        df.insert(0, 'date', pd.date_range("01-01-" + str(int(df['year'].iloc[0])), periods=len(df), freq='D'))

        breaks = []  # list of indices of new fire years
        for i, _row in df.iterrows():
            if _row.julian == fire_day:
                breaks.append(i)  # record the index for the new year

        out_fn = _join(out_dir, '%s_ash.csv' % prefix)
        # write ash output file
        df.to_csv(out_fn)

        # graphing

        # line plot
        fig = plt.figure()
        ax = plt.gca()
        df.plot(kind='line', x='date', y='cum_ash_runoff (mm)', color='blue', ax=ax)
        df.plot(secondary_y=True, kind='line', x='date', y='cum_ash_transport (tonne/ha)', color='red', ax=ax)
        fig.savefig(_join(out_dir, f'{prefix}_ash.png'))

        # scatter plot
        fig2 = plt.figure()
        ax = plt.gca()
        df.plot(kind='scatter', x='cum_ash_runoff (mm)', y='cum_ash_transport (tonne/ha)', color='blue', ax=ax)
        fig2.savefig(_join(out_dir, f'{prefix}_ash_scatter.png'))

        yr_df = df.loc[[brk - 1 for brk in breaks[1:]],
                       ['year',
                        'cum_wind_transport (tonne/ha)',
                        'cum_water_transport (tonne/ha)',
                        'cum_ash_transport (tonne/ha)']]

        s_len = len(df.da)

        df.drop(index=range(breaks[0]), inplace=True)
        df.drop(index=range(breaks[-1], s_len), inplace=True)

        out_fn = _join(out_dir, '%s_ash.csv' % prefix)
        df.to_csv(out_fn, index=False)

        num_fire_years = len(breaks) - 1

        annuals = {}
        for measure in ['cum_wind_transport (tonne/ha)',
                        'cum_water_transport (tonne/ha)',
                        'cum_ash_transport (tonne/ha)']:

            annuals[measure] = []
            yr_df.sort_values(by=measure, ascending=False, inplace=True)

            data = []
            colnames = ['year', measure, 'probability', 'rank', 'return_interval']
            for j, (i, _row) in enumerate(yr_df.iterrows()):
                val = _row[measure]

                rank = j + 1
                ri = (num_fire_years + 1) / rank
                prob = probability_of_occurrence(ri, 1.0)
                data.append([int(_row.year), val, prob, int(rank), ri])
                annuals[measure].append(dict(zip(colnames, data[-1])))

            _df = pd.DataFrame(data, columns=colnames)
            _df.to_csv(_join(out_dir, '%s_ash_stats_per_year_%s.csv' % (prefix, measure.split('_')[1])), index=False)

        recurrence = [rec for rec in recurrence if rec <= num_fire_years]
        num_days = len(df.da)
        return_periods = {}
        for measure in ['wind_transport (tonne/ha)', 'water_transport (tonne/ha)', 'ash_transport (tonne/ha)']:
            return_periods[measure] = {}
            df.sort_values(by=measure, ascending=False, inplace=True)

            data = []
            for j, (i, _row) in enumerate(df.iterrows()):
                val = _row[measure]

                if val == 0.0:
                    continue

                dff = _row['days_from_fire (days)']
                rank = j + 1
                ri = (num_days + 1) / rank
                ri /= 365.25
                prob = probability_of_occurrence(ri, 1.0)
                data.append([int(_row.year), int(_row.mo), int(_row.da), dff, val, prob, rank, ri, _row['precip (mm)']])

            _df = pd.DataFrame(data, columns=
            ['year', 'mo', 'da', 'days_from_fire', measure, 'probability', 'rank', 'return_interval', 'precip'])
            _df.to_csv(_join(out_dir, '%s_ash_stats_per_event_%s.csv' % (prefix, measure.split('_')[0])), index=False)

            rec = weibull_series(recurrence, num_fire_years)

            num_events = len(_df.da)
            for retperiod in recurrence:
                if retperiod not in rec:
                    return_periods[measure][retperiod] = None
                else:
                    indx = rec[retperiod]
                    if indx >= num_events:
                        return_periods[measure][retperiod] = None
                    else:
                        _row = dict(_df.loc[indx, :])
                        for _m in ['year', 'mo', 'da', 'days_from_fire', 'rank']:
                            _row[_m] = int(_row[_m])

                        return_periods[measure][retperiod] = _row

        with open(_join(out_dir, '%s_ash_return_periods.json' % prefix), 'w') as fp:
            json.dump(return_periods, fp)

        with open(_join(out_dir, '%s_ash_annuals.json' % prefix), 'w') as fp:
            json.dump(annuals, fp)

        return out_fn, return_periods, annuals


class WhiteAshModel(AshModel):
    __name__ = 'WhiteAshModel'

    def __init__(self, bulk_density=WHITE_ASH_BD):
        super(WhiteAshModel, self).__init__(
            ash_type=AshType.WHITE,
            ini_bulk_den=WHITE_ASH_BD,  # Initial bulk density, gm/cm3
            fin_bulk_de=0.62,  # Final bulk density, gm/cm3
            bulk_den_fac=0.005,  # Bulk density factor
            par_den=1.2,  # Ash particle density, gm/cm3
            decomp_fac=0.00018,  # Ash decomposition factor, per day
            ini_erod=1,  # Initial erodibility, t/ha
            fin_erod=0.01,  # Final erodibility, t/ha
            roughness_limit=1)  # Roughness limit, mm


class BlackAshModel(AshModel):
    __name__ = 'BlackAshModel'

    def __init__(self, bulk_density=BLACK_ASH_BD):
        super(BlackAshModel, self).__init__(
            ash_type=AshType.BLACK,
            ini_bulk_den=BLACK_ASH_BD,  # Initial bulk density, gm/cm3
            fin_bulk_de=0.62,  # Final bulk density, gm/cm3
            bulk_den_fac=0.005,  # Bulk density factor
            par_den=1.2,  # Ash particle density, gm/cm3
            decomp_fac=0.00018,  # Ash decomposition factor, per day
            ini_erod=0.098509,  # Initial erodibility, t/ha
            fin_erod=0.01,  # Final erodibility, t/ha
            roughness_limit=1)   # Roughness limit, mm


