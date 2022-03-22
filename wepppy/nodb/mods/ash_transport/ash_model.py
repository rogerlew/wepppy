from typing import Optional
import math
import enum
import json

from os.path import join as _join

from copy import deepcopy
import pandas as pd

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.all_your_base.stats import weibull_series, probability_of_occurrence

from wepppy.wepp.out import HillWat

from .wind_transport_thresholds import *

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


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
                 proportion=None,
                 decomposition_rate=None,
                 bulk_density=None,
                 density_at_fc=None,
                 fraction_water_retention_capacity_at_sat=None,
                 runoff_threshold=None,
                 water_transport_rate=None,
                 water_transport_rate_k=None,
                 wind_threshold=None,
                 porosity=None,
                 iniBulkDen=None,
                 finBulkDen=None,
                 bulkDenFac=None,
                 parDen=None,
                 decompFac=None,
                 iniErod=None,
                 finErod=None,
                 roughnessLimit=None):
        self.ash_type = ash_type
        self.proportion = proportion
        self.ini_ash_depth_mm = None
        self.ini_ash_load_tonneha = None
        self.decomposition_rate = decomposition_rate
        self.bulk_density = bulk_density
        self.density_at_fc = density_at_fc
        self.fraction_water_retention_capacity_at_sat = fraction_water_retention_capacity_at_sat
        self.runoff_threshold = runoff_threshold
        self.water_transport_rate = water_transport_rate
        self.water_transport_rate_k = water_transport_rate_k
        self.wind_threshold = wind_threshold
        self.porosity = porosity
        

        self.iniBulkDen = WHITE_ASH_BD,  # Initial bulk density, gm/cm3
        self.finBulkDen = 0.62,  # Final bulk density, gm/cm3
        self.bulkDenFac = 0.005,  # Bulk density factor
        self.parDen = 1.2,  # Ash particle density, gm/cm3
        self.decompFac = 0.00018  # Ash decomposition factor, per day
        self.iniErod = 1  # Initial erodibility, t/ha
        self.finErod = 0.01  # Final erodibility, t/ha
        self.roughnessLimit = 1  # Roughness limit, mm

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

    @property
    def water_retention_capacity_at_sat(self):
        return self.fraction_water_retention_capacity_at_sat * self.ini_ash_depth_mm

    def lookup_wind_threshold_proportion(self, w):
        if w == 0.0:
            return 0.0

        if self.ash_type == AshType.BLACK:
            return lookup_wind_threshold_black_ash_proportion(w)
        elif self.ash_type == AshType.WHITE:
            return lookup_wind_threshold_white_ash_proportion(w)

    def run_model(self, fire_date: YearlessDate, element_d, cli_df: pd.DataFrame, hill_wat: HillWat, out_dir, prefix,
                  recurrence=[100, 50, 25, 20, 10, 5, 2], 
                  area_ha: Optional[float]=None, 
                  ini_ash_depth: Optional[float]=None, 
                  ini_ash_load: Optional[float]=None, run_wind_transport=True, model='neris'):
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
        
        if model == 'anu':
            return self._anu_run_model(fire_date=fire_date, element_d=element_d, cli_df=cli_df, hill_wat=hill_wat, 
                                         out_dir=out_dir, prefix=prefix, recurrence=recurrence, 
                                         area_ha=area_ha, ini_ash_depth=ini_ash_depth, ini_ash_load=ini_ash_load, 
                                         run_wind_transport=run_wind_transport)
        
        else:
            return self._neris_run_model(fire_date=fire_date, element_d=element_d, cli_df=cli_df, hill_wat=hill_wat, 
                                         out_dir=out_dir, prefix=prefix, recurrence=recurrence, 
                                         area_ha=area_ha, ini_ash_depth=ini_ash_depth, ini_ash_load=ini_ash_load, 
                                         run_wind_transport=run_wind_transport)
        
    def _neris_run_model(self, fire_date: YearlessDate, element_d, cli_df: pd.DataFrame, hill_wat: HillWat, out_dir, prefix,
                  recurrence=[100, 50, 25, 20, 10, 5, 2], 
                  area_ha: Optional[float]=None, 
                  ini_ash_depth: Optional[float]=None, 
                  ini_ash_load: Optional[float]=None, run_wind_transport=True):

        self.ini_ash_depth_mm = ini_ash_depth
        self.ini_ash_load_tonneha = ini_ash_load

        # copy the DataFrame
        df = deepcopy(cli_df)

        hill_wat_d = hill_wat.as_dict()

        # number of days in the file
        s_len = len(df.da)

        #
        # Initialize np.arrays to store model values
        #

        # current fire year starting at 1
        fire_years = np.zeros((s_len,), dtype=np.int32)

        # days from fire for wach fire year
        days_from_fire = np.zeros((s_len,), dtype=np.int32)

        # fraction of ash lost from decay for a day
        daily_relative_ash_decay = np.zeros((s_len,))
        cum_relative_ash_decay = np.zeros((s_len,))

        # daily total available ash in tonne/ha
        available_ash = np.zeros((s_len,))

        # wind transport variables
        w_vl_ifgt = np.zeros((s_len,))
        proportion_ash_transport = np.zeros((s_len,))
        cum_proportion_ash_transport = np.zeros((s_len,))
        wind_transport = np.zeros((s_len,))
        cum_wind_transport = np.zeros((s_len,))

        # peak runoff from the element (PeakRunoffRAW) WEPP output
        peak_ro = np.zeros((s_len,))

        # effective duration from the element (PeakRunoffRAW) WEPP output
        eff_dur = np.zeros((s_len,))

        # effective duration from the element (Precip) WEPP output
        precip = np.zeros((s_len,))

        # water transport modeling variables
        water_excess = np.zeros((s_len,))
        real_runoff = np.zeros((s_len,))
        effective_runoff = np.zeros((s_len,))
        cum_runoff = np.zeros((s_len,))
        soil_evap = np.zeros((s_len,))
        ash_wat_cap = np.zeros((s_len,))
        water_transport = np.zeros((s_len,))
        cum_water_transport = np.zeros((s_len,))

        #
        # Loop through each day in the climate file
        #

        breaks = []    # list of indices of new fire years
        fire_year = 0  # current fire year
        w_vl_if = 0.0  # maximum wind speed event for current fire year
        dff = -1       # days from fire for current year
        for i, _row in df.iterrows():
            #
            # is today the fire day?
            #
            if _row.mo == fire_date.month and _row.da == fire_date.day:
                breaks.append(i)  # record the index for the new year
                fire_year += 1    # increment the fire year
                w_vl_if = 0.0     # reset the wind threshold for the fire year
                dff = 0           # reset the days from fire

            # store the fire year and days from fire
            fire_years[i] = fire_year
            days_from_fire[i] = dff

            # if we are in the first year of the climate file and haven't encountered the fire date
            # we can just continue to the next day
            if dff == -1:
                continue

            #
            # on the first day of the fire reset the available ash
            #
            if dff == 0:
                available_ash[i] = self.ini_material_available_tonneperha

            #
            # model ash decay
            #
            # this was determine as the derivative of 1 * exp(decomposition_rate * time_from_fire(days))
            else:
                daily_relative_ash_decay[i] = self.decomposition_rate * math.exp(-self.decomposition_rate * dff)
                if i > 0:
                    cum_relative_ash_decay[i] = cum_relative_ash_decay[i-1] + daily_relative_ash_decay[i]

                available_ash[i] = available_ash[i-1] * (1.0 - daily_relative_ash_decay[i])

            #
            # model runoff
            #

            # the element file contains event data we need to look up if the current day has data
            # from the element_d dictionary

            # unpack the key
            yr_mo_da = _row.year, _row.mo, _row.da
            if yr_mo_da in element_d:
                peak_ro[i] = element_d[yr_mo_da]['PeakRO']
                eff_dur[i] = element_d[yr_mo_da]['EffDur']
                precip[i] = element_d[yr_mo_da]['Precip']
            else:
                peak_ro[i] = 0.0
                eff_dur[i] = 0.0
                precip[i] = 0.0

            if yr_mo_da in hill_wat_d:
                soil_evap[i] = hill_wat_d[yr_mo_da]['Es (mm)']
            else:
                soil_evap[i] = 0.0

            assert not math.isnan(peak_ro[i])
            assert not math.isnan(eff_dur[i])

            # calculate excess water
            water_excess[i] = peak_ro[i] * eff_dur[i]

            assert not math.isnan(water_excess[i])

            # calculate real runoff accounting for available ash
            real_runoff[i] = water_excess[i] - (available_ash[i] / (10 * self.bulk_density)) * self.porosity
            if real_runoff[i] < 0:
                real_runoff[i] = 0.0

            assert not math.isnan(real_runoff[i]), (i, available_ash[i], self.bulk_density)

            # calculate runoff over the runoff_threshold specified by the model parameters
            effective_runoff[i] = real_runoff[i] - self.runoff_threshold

            # clamp to 0
            if effective_runoff[i] < 0.0:
                effective_runoff[i] = 0.0

            if dff == 0:
                ash_wat_cap[i] = effective_runoff[i] - soil_evap[i]
            else:
                ash_wat_cap[i] = ash_wat_cap[i - 1] + effective_runoff[i] - soil_evap[i]
                if ash_wat_cap[i] < 0.0:
                    ash_wat_cap[i] = 0.0

            # calculate cumulative runoff
            if dff > 0:
                cum_runoff[i] = cum_runoff[i-1] + effective_runoff[i-1]

            # water transport is empirically modeled
            # black and white ash have their own models
            if self.ash_type == AshType.BLACK:
                water_transport[i] = effective_runoff[i] * self.water_transport_rate
            elif self.ash_type == AshType.WHITE:
                # runoff_threshold == 0, so real_runoff == effective_runoff
                water_transport[i] = effective_runoff[i] * self.water_transport_rate * \
                                     math.exp(self.water_transport_rate_k * cum_runoff[i])

            if water_transport[i] > 0:
                if water_transport[i] > available_ash[i]:
                    water_transport[i] = available_ash[i]
                available_ash[i] -= water_transport[i]
            elif run_wind_transport:  # only apply wind transport if there is no water
                #
                # model wind transport
                #
                # identify peak wind values within the fire year
                if _row['w-vl'] > w_vl_if:
                    w_vl_if = _row['w-vl']  # store daily wind threshold
                    w_vl_ifgt[i] = w_vl_if  # track max for comparison
                else:
                    w_vl_ifgt[i] = 0.0  # if day is not a max for the year store 0.0

                # identify the fraction removed by wind from the wind_transport_thresholds.csv
                proportion_ash_transport[i] = self.lookup_wind_threshold_proportion(w_vl_ifgt[i])
                assert proportion_ash_transport[i] >= 0.0

                # if not the day of the fire adjust by the cumulative proportion of ash transport
                if dff > 0:
                    proportion_ash_transport[i] -= cum_proportion_ash_transport[i-1]

                    # clamp to 0
                    if proportion_ash_transport[i] < 0.0:
                        proportion_ash_transport[i] = 0.0

                # calculate cumulative ash transport
                if dff == 0:
                    # on the day of the fire it is the value from the wind thresholds table
                    cum_proportion_ash_transport[i] = proportion_ash_transport[i]
                else:
                    # on subsequent days sum up the values
                    cum_proportion_ash_transport[i] = cum_proportion_ash_transport[i-1] + proportion_ash_transport[i]

                # lookup yesterdays water transport
                relative_ash_decay = 1.0 - cum_relative_ash_decay[i]

                # calculate wind transport
                wind_transport[i] = (self.ini_material_available_tonneperha - relative_ash_decay) * \
                                    (1.0 - daily_relative_ash_decay[i]) * proportion_ash_transport[i]

                if wind_transport[i] < 0.0:
                    wind_transport[i] = 0.0

                if wind_transport[i] > available_ash[i]:
                    wind_transport[i] = available_ash[i]
                # remove wind and water transported ash from the available ash
                available_ash[i] -= wind_transport[i]

            # clamp to 0
            if available_ash[i] < 0.0:
                available_ash[i] = 0.0

            cum_wind_transport[i] = wind_transport[i]
            cum_water_transport[i] = water_transport[i]

            if dff > 0:
                cum_wind_transport[i] += cum_wind_transport[i-1]
                cum_water_transport[i] += cum_water_transport[i-1]

            # increment the days from fire variable
            dff += 1

        # calculate cumulative wind and water transport
        ash_transport = water_transport + wind_transport
        cum_ash_transport = cum_water_transport + cum_wind_transport

        # store in the dataframe
        df['fire_year (yr)'] = pd.Series(fire_years, index=df.index)
        df['w_vl_ifgt (m/s)'] = pd.Series(w_vl_ifgt, index=df.index)
        df['days_from_fire (days)'] = pd.Series(days_from_fire, index=df.index)
        df['daily_relative_ash_decay (fraction)'] = pd.Series(daily_relative_ash_decay, index=df.index)
        df['available_ash (tonne/ha)'] = pd.Series(available_ash, index=df.index)
        df['_proportion_ash_transport (fraction)'] = pd.Series(proportion_ash_transport, index=df.index)
        df['_cum_proportion_ash_transport (fraction)'] = pd.Series(cum_proportion_ash_transport, index=df.index)
        df['wind_transport (tonne/ha)'] = pd.Series(wind_transport, index=df.index)
        df['cum_wind_transport (tonne/ha)'] = pd.Series(cum_wind_transport, index=df.index)
        df['peak_ro (mm/hr)'] = pd.Series(peak_ro, index=df.index)
        df['eff_dur (hr)'] = pd.Series(eff_dur, index=df.index)
        df['precip (mm)'] = pd.Series(precip, index=df.index)
        df['water_excess (mm)'] = pd.Series(water_excess, index=df.index)
        df['real_runoff (mm)'] = pd.Series(real_runoff, index=df.index)
        df['effective_runoff (mm)'] = pd.Series(effective_runoff, index=df.index)
        df['cum_runoff (mm)'] = pd.Series(cum_runoff, index=df.index)
        df['water_transport (tonne/ha)'] = pd.Series(water_transport, index=df.index)
        df['cum_water_transport (tonne/ha)'] = pd.Series(cum_water_transport, index=df.index)
        df['ash_transport (tonne/ha)'] = pd.Series(ash_transport, index=df.index)
        df['cum_ash_transport (tonne/ha)'] = pd.Series(cum_ash_transport, index=df.index)

        if area_ha is not None:
            df['ash_delivery (tonne)'] = pd.Series(ash_transport * area_ha, index=df.index)
            df['ash_delivery_by_wind (tonne)'] = pd.Series(wind_transport * area_ha, index=df.index)
            df['ash_delivery_by_water (tonne)'] = pd.Series(water_transport * area_ha, index=df.index)
            df['cum_ash_delivery (tonne)'] = pd.Series(cum_ash_transport * area_ha, index=df.index)
            df['cum_ash_delivery_by_wind (tonne)'] = pd.Series(cum_wind_transport * area_ha, index=df.index)
            df['cum_ash_delivery_by_water (tonne)'] = pd.Series(cum_water_transport * area_ha, index=df.index)

        df.drop(columns=['dur', 'tp', 'ip', 'tmax', 'tmin', 'rad', 'w-dir', 'tdew'], inplace=True)

        yr_df = df.loc[[brk-1 for brk in breaks[1:]],
                       ['year',
                        'cum_wind_transport (tonne/ha)',
                        'cum_water_transport (tonne/ha)',
                        'cum_ash_transport (tonne/ha)']]

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
            colnames =['year', measure, 'probability', 'rank', 'return_interval']
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
                ['year', 'mo', 'da', 'days_from_fire', measure, 'probability', 'rank', 'return_interval' , 'precip'])
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

    def _anu_run_model(self, fire_date: YearlessDate, element_d, cli_df: pd.DataFrame, hill_wat: HillWat, out_dir, prefix,
                  recurrence=[100, 50, 25, 20, 10, 5, 2], 
                  area_ha: Optional[float]=None, 
                  ini_ash_depth: Optional[float]=None, 
                  ini_ash_load: Optional[float]=None, run_wind_transport=True):

        
        import matplotlib.pyplot as plt
        pd.options.mode.chained_assignment = None  # default='warn'

        self.ini_ash_depth_mm = ini_ash_depth
        # self.ini_ash_load_tonneha = ini_ash_load
        
        # define fire day in julian
        fireDay = fire_date.julian

        # define parameters
        iniBulkDen = 0.31  # Initial bulk density, gm/cm3
        finBulkDen = 0.62  # Final bulk density, gm/cm3
        bulkDenFac = 0.005  # Bulk density factor
        parDen = 1.2  # Ash particle density, gm/cm3
        decompFac = self.decomposition_rate  # 0.00018  # Ash decomposition factor, per day
        iniErod = 1  # Initial erodibility, t/ha
        finErod = 0.01  # Final erodibility, t/ha
        roughnessLimit = 1  # Roughness limit, mm
        self.ini_ash_depth_mm = iniAshDepth = ini_ash_depth
        self.ini_ash_load_tonneha = iniAshLoad = ini_ash_load  #  10 * iniAshDepth * iniBulkDen   # Initial ash load, t/ha
        

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

        # make starting/ending date for stochastic climate
        if watr['Y_#'].iloc[0] == 1:
            starting = '1/1/' + str(watr['Y_#'].iloc[0] + 1900)
            ending = '12/31/' + str(watr['Y_#'].iloc[-1] + 1900)
        # make starting/ending date for observed climate
        else:
            starting = '1/1/' + str(watr['Y_#'].iloc[0])
            ending = '12/31/' + str(watr['Y_#'].iloc[-1])

        # create ash df
        df = pd.DataFrame()

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
        J = ash_df.loc[idx_sim, 'J_#'].values
        Y = ash_df.loc[idx_sim, 'Y_#'].values
        P = ash_df.loc[idx_sim, 'P_mm'].values
        RM = ash_df.loc[idx_sim, 'RM_mm'].values
        Q = ash_df.loc[idx_sim, 'Q_mm'].values
        TSW = ash_df.loc[idx_sim, 'Total-Soil-Water_mm'].values
        SWE = ash_df.loc[idx_sim, 'Snow-Water_mm'].values

        # Pre-allocate arrays with NaN values
        Julian = np.ones(N) * np.nan
        Year = np.ones(N) * np.nan
        Infil_mm = np.ones(N) * np.nan
        Cum_Infil_mm = np.ones(N) * np.nan
        Cum_Q_mm = np.ones(N) * np.nan
        Bulk_density_gmpcm3 = np.ones(N) * np.nan
        Porosity = np.ones(N) * np.nan
        Available_ash_tonspha = np.ones(N) * np.nan
        Ash_depth_mm = np.ones(N) * np.nan
        Ash_runoff_mm = np.ones(N) * np.nan
        Transport_tonspha = np.ones(N) * np.nan
        Water_transport_tonspha = np.ones(N) * np.nan
        Cum_ash_runoff_mm = np.ones(N) * np.nan
        Cum_water_transport_tonspha = np.ones(N) * np.nan    
        Wind_transport_tonspha = np.zeros(N)
        Cum_wind_transport_tonspha = np.zeros(N)
        Ash_transport_tonspha = np.ones(N) * np.nan
        Cum_ash_transport_tonspha = np.ones(N) * np.nan
        

        # Define initial conditions
        Year[0] = watr['Y_#'].iloc[0] - 1
        Ash_depth_mm[0] = iniAshDepth
        Available_ash_tonspha[0] = iniAshLoad
        Julian[0] = 0
        Infil_mm[0] = 0
        Cum_Infil_mm[0] = 0
        Cum_Q_mm[0] = 0
        Bulk_density_gmpcm3[0] = iniBulkDen
        Porosity[0] = 1 - (Bulk_density_gmpcm3[0] / parDen)
        Cum_ash_runoff_mm[0] = 0
        Cum_water_transport_tonspha[0] = 0

        # Model
        for t in range(1, N):

            if J[t] >= fireDay:
                Year[t] = Y[t]
            else:
                Year[t] = Y[t] - 1

            if J[t] == fireDay:
                Julian[t] = 1
            else:
                Julian[t] = Julian[t - 1] + 1

            Infil_mm[t] = RM[t] - Q[t]

            if J[t] == fireDay:
                Cum_Infil_mm[t] = Infil_mm[t]
                Cum_Q_mm[t] = Q[t]
                Bulk_density_gmpcm3[t] = iniBulkDen
                Porosity[t] = 1 - (Bulk_density_gmpcm3[t] / parDen)
            else:
                Cum_Infil_mm[t] = Cum_Infil_mm[t - 1] + Infil_mm[t]
                Cum_Q_mm[t] = Cum_Q_mm[t - 1] + Q[t]
                Bulk_density_gmpcm3[t] = finBulkDen + (
                    iniBulkDen - finBulkDen) * np.exp(
                        -bulkDenFac * Cum_Infil_mm[t])
                Porosity[t] = 1 - (Bulk_density_gmpcm3[t] / parDen)

            if Q[t - 1] > (Available_ash_tonspha[t - 1] /
                           (10. * Bulk_density_gmpcm3[t - 1])) * Porosity[t - 1]:
                Ash_runoff_mm[t - 1] = np.maximum(
                    0, Q[t - 1] -
                    (Available_ash_tonspha[t - 1] /
                     (10. * Bulk_density_gmpcm3[t - 1])) * Porosity[t - 1])
            else:
                Ash_runoff_mm[t - 1] = 0

            if Ash_runoff_mm[t - 1] > 0:
                Transport_tonspha[t - 1] = (iniErod - finErod) * (
                    Bulk_density_gmpcm3[t - 1] -
                    finBulkDen) / (iniBulkDen - finBulkDen) + finErod
                
                Water_transport_tonspha[t - 1] = np.maximum(
                    0,
                    np.minimum(Available_ash_tonspha[t - 1], Ash_runoff_mm[t - 1] *
                               Transport_tonspha[t - 1]))
                
                Wind_transport_tonspha[t - 1] = 0
                            
            else:
                Transport_tonspha[t - 1] = 0
                Water_transport_tonspha[t - 1] = 0
                
                Wind_transport_tonspha[t - 1] = 0
                Ash_transport_tonspha[t - 1] = 0
                
            Ash_transport_tonspha[t - 1] = Wind_transport_tonspha[t - 1] + Water_transport_tonspha[t - 1]

            if Julian[t] > 1:

                if Ash_depth_mm[t - 1] < roughnessLimit:
                    Available_ash_tonspha[t] = 0
                else:
                    Available_ash_tonspha[t] = Available_ash_tonspha[t - 1] * np.exp(-decompFac * Infil_mm[t]) - \
                        Water_transport_tonspha[t - 1]
            else:
                Available_ash_tonspha[t] = iniAshLoad

            Ash_depth_mm[t] = Available_ash_tonspha[t] / (10. *
                                                          Bulk_density_gmpcm3[t])

            if Julian[t] == 1:
                Cum_ash_runoff_mm[t] = Ash_runoff_mm[t - 1]
                Cum_wind_transport_tonspha[t] = 0
                Cum_water_transport_tonspha[t] = Water_transport_tonspha[t - 1]
            else:
                Cum_ash_runoff_mm[t] = Cum_ash_runoff_mm[t - 1] + \
                    Ash_runoff_mm[t - 1]
                Cum_wind_transport_tonspha[t] = 0
                Cum_water_transport_tonspha[t] = Cum_water_transport_tonspha[
                    t - 1] + Water_transport_tonspha[t - 1]
                
            Cum_ash_transport_tonspha[t] = Cum_wind_transport_tonspha[t] + Cum_water_transport_tonspha[t]

        # convert numpy arrays to pandas dataframe
        my_array = np.array([
            Year, Julian, P, RM, SWE, Q, TSW, Infil_mm, Cum_Infil_mm, Cum_Q_mm,
            Bulk_density_gmpcm3, Porosity, Available_ash_tonspha, Ash_depth_mm,
            Ash_runoff_mm, Transport_tonspha, Cum_ash_runoff_mm, Water_transport_tonspha,
            Wind_transport_tonspha, Ash_transport_tonspha,
            Cum_water_transport_tonspha, Cum_wind_transport_tonspha, Cum_ash_transport_tonspha  
        ]).T

        index = list(range(0, len(Year)))

        columns = [
            'year', 'julian', 'precip (mm)', 'rainmelt (mm)', 'snow water equivalent (mm)', 'runoff (mm)', 'tot soil water (mm)',
            'infiltration (mm)', 'cum_infiltration (mm)', 'cum_runoff (mm)', 'bulk density (gm/cm3)',
            'porosity', 'available ash (tonne/ha)', 'ash depth (mm)', 'ash runoff (mm)',
            'transport (tonne/ha)', 'cum_ash_runoff (mm)',
            'water_transport (tonne/ha)', 'wind_transport (tonne/ha)', 'ash_transport (tonne/ha)', 
            'cum_water_transport (tonne/ha)', 'cum_wind_transport (tonne/ha)', 'cum_ash_transport (tonne/ha)'        
        ]

        df = pd.DataFrame(my_array, index, columns)

        # remove the first and the last year
        df = df[(df['year'] > df['year'].iloc[0])
                & (df['year'] < df['year'].iloc[-1])]

        # reset and rename index
        df.reset_index(drop=True, inplace=True)
        df.index.rename("sno", inplace=True)    

        # Update date
        df.insert(0, 'date', pd.date_range("01-01-" + str(int(df['year'].iloc[0])), periods=len(df), freq='D'))
        
        breaks = []    # list of indices of new fire years
        for i, _row in df.iterrows():
            if _row.julian == fireDay:
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

        yr_df = df.loc[[brk-1 for brk in breaks[1:]],
                       ['year',
                        'cum_wind_transport (tonne/ha)',
                        'cum_water_transport (tonne/ha)',
                        'cum_ash_transport (tonne/ha)']]

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
            colnames =['year', measure, 'probability', 'rank', 'return_interval']
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
                ['year', 'mo', 'da', 'days_from_fire', measure, 'probability', 'rank', 'return_interval' , 'precip'])
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
            proportion=1.0,
            decomposition_rate=1.8E-4,
            bulk_density=bulk_density,
            density_at_fc=0.68,
            fraction_water_retention_capacity_at_sat=0.87,
            runoff_threshold=0.0,
            water_transport_rate=3.816,
            water_transport_rate_k=-0.0421,
            wind_threshold=6,
            porosity=0.8)

class BlackAshModel(AshModel):
    __name__ = 'BlackAshModel'

    def __init__(self, bulk_density=BLACK_ASH_BD):
        super(BlackAshModel, self).__init__(
            ash_type=AshType.BLACK,
            proportion=1.0,
            decomposition_rate=1.8E-4,
            bulk_density=bulk_density,
            density_at_fc=0.54,
            fraction_water_retention_capacity_at_sat=0.87,
            runoff_threshold=3.45,
            water_transport_rate=0.098509,
            water_transport_rate_k=None,
            wind_threshold=6,
            porosity=0.8)
        
        
class AnuWhiteAshModel(AshModel):
    __name__ = 'AnuWhiteAshModel'

    def __init__(self, bulk_density=WHITE_ASH_BD):
        super(AnuWhiteAshModel, self).__init__(
            ash_type=AshType.WHITE,
            iniBulkDen=WHITE_ASH_BD,  # Initial bulk density, gm/cm3
            finBulkDen=0.62,  # Final bulk density, gm/cm3
            bulkDenFac=0.005,  # Bulk density factor
            parDen=1.2,  # Ash particle density, gm/cm3
            decompFac=0.00018,  # Ash decomposition factor, per day
            iniErod=1, # Initial erodibility, t/ha
            finErod=0.01,  # Final erodibility, t/ha
            roughnessLimit=1  # Roughness limit, mm)

class AnuBlackAshModel(AshModel):
    __name__ = 'AnuBlackAshModel'

    def __init__(self, bulk_density=BLACK_ASH_BD):
        super(AnuBlackAshModel, self).__init__(
            ash_type=AshType.BLACK,        
            iniBulkDen=BLACK_ASH_BD,  # Initial bulk density, gm/cm3
            finBulkDen=0.62,  # Final bulk density, gm/cm3
            bulkDenFac=0.005,  # Bulk density factor
            parDen=1.2, # Ash particle density, gm/cm3
            decompFac=0.00018,  # Ash decomposition factor, per day
            iniErod=0.098509,  # Initial erodibility, t/ha
            finErod=0.01,  # Final erodibility, t/ha
            roughnessLimit=1  # Roughness limit, mm)
        
        
