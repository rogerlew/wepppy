from typing import Optional
import math
import enum
import json

from os.path import join as _join

from copy import deepcopy
import pandas as pd

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.all_your_base.stats import weibull_series, probability_of_occurrence

from .wind_transport_thresholds import *

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

from .ash_type import AshType

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
                 proportion,
                 decomposition_rate,
                 bulk_density,
                 density_at_fc,
                 fraction_water_retention_capacity_at_sat,
                 runoff_threshold,
                 water_transport_rate,
                 water_transport_rate_k,
                 wind_threshold,
                 porosity):
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

    @property
    def ini_material_available_mm(self):
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

    def run_model(self, fire_date: YearlessDate, element_d, cli_df: pd.DataFrame, hill_wat_df: pd.DataFrame, out_dir, prefix,
                  recurrence=[100, 50, 25, 20, 10, 5, 2], 
                  area_ha: Optional[float]=None, 
                  ini_ash_depth: Optional[float]=None, 
                  ini_ash_load: Optional[float]=None, run_wind_transport=True):
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
        self.ini_ash_load_tonneha = ini_ash_load

        # copy the DataFrame
        df = deepcopy(cli_df)

        drop_columns = {'Area', 'day', 'ofe_id', 'OFE'}
        hill_wat_d = {}
        for record in hill_wat_df.to_dict('records'):
            key = (
                int(record['year']),
                int(record['month']),
                int(record['day_of_month']),
            )
            hill_wat_d[key] = {k: v for k, v in record.items() if k not in drop_columns}

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
                soil_evap[i] = hill_wat_d[yr_mo_da]['Es']
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
