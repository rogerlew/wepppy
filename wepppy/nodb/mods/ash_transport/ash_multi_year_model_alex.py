from typing import Optional
import enum
from os.path import join as _join

import json
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import warnings

from wepppy.all_your_base import isfloat
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

    def __str__(self):
        if self == AshType.BLACK:
            return 'Black'
        elif self == AshType.WHITE:
            return 'White'
        else:
            raise ValueError(f'Unknown ash type {self}')
        

class AshNoDbLockedException(Exception):
    pass



class AshModelAlex(object):
    """
    Base class for the hillslope ash models. This class is inherited by
    the WhiteAshModel and BlackAshModel classes
    """

    def __init__(self,
                 ash_type: AshType,
                 ini_bulk_den=None,
                 fin_bulk_den=None,
                 bulk_den_fac=None,
                 par_den=None,
                 decomp_fac=None,
                 roughness_limit=None,
                 run_wind_transport=False,
                 org_mat=None,
                 beta0=14.33,
                 beta1=0.22,
                 beta2=5.85,
                 beta3=-0.36,
                 transport_mode='dynamic',
                 initranscap=0.8,
                 depletcoeff=0.009
                 ):

        assert fin_bulk_den >= ini_bulk_den, (fin_bulk_den, ini_bulk_den)

        self.ash_type = ash_type
        self.ini_ash_depth_mm = None
        self.ini_ash_load_tonneha = None
        self.ini_bulk_den = ini_bulk_den  # Initial bulk density, gm/cm3
        self.fin_bulk_den = fin_bulk_den  # Final bulk density, gm/cm3
        self.bulk_den_fac = bulk_den_fac  # Bulk density factor
        self.par_den = par_den  # Ash particle density, gm/cm3
        self.decomp_fac = decomp_fac  # Ash decomposition factor, per day
        self.roughness_limit = roughness_limit  # Roughness limit, mm
        self.org_mat = org_mat  # percent organic matter as ratio
        self.run_wind_transport = run_wind_transport
        self.slope = None
        self.beta0 = beta0
        self.beta1 = beta1
        self.beta2 = beta2
        self.beta3 = beta3
        self.transport_mode = transport_mode
        self.initranscap = initranscap
        self.depletcoeff = depletcoeff

    @property
    def ini_material_available_mm(self):
        return self.proportion * self.ini_ash_depth_mm

    @property
    def ini_material_available_tonneperha(self):
        if self.ini_ash_load_tonneha is not None:
            return self.ini_ash_load_tonneha
        else:
            return 10.0 * self.ini_material_available_mm * self.bulk_density

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
                  ini_ash_depth: Optional[float] = None,  # not used
                  ini_ash_load: Optional[float] = None, 
                  slope: float = None,
                  run_wind_transport=True):

        """
        Runs the ash model for a hillslope

        :param fire_date:
            month, day of fire as a YearlessDate instance
        :param element_d:
            dictionary runoff events from the element WEPP output. The keys are (year, mo, da) and the values contain
            the row data as dictionaries with header keys
        :param cli_df:
            the climate file produced by CLIGEN as a pandas.Dataframe
        :param hill_wat:
               the hillslope water model output
        :param out_dir:
            the directory save the model output
        :param prefix:
            prefix for the model output file
        :param recurrence:
            list of recurrence intervals
        :return:
            returns the output file name, return period results dictionary
        """

        self.ini_ash_depth_mm = None
        self.ini_ash_load_tonneha = ini_ash_load
        self.slope = slope

        assert isfloat(self.par_den), (prefix, self.par_den)
        assert isfloat(self.ini_bulk_den), (prefix, self.ini_bulk_den)
        assert isfloat(self.fin_bulk_den), (prefix, self.fin_bulk_den)
        assert isfloat(self.org_mat), (prefix, self.org_mat)

        # timeseries
        fig = plt.figure()
        ax1 = plt.gca()

        # scatter plot
        fig2 = plt.figure()
        ax2 = plt.gca()

        # Create an empty list to store DataFrames
        dfs = []

        # use np.unique to get the unique years in the climate file
        for year0 in np.unique(hill_wat.data['Y']):
            start_index = np.where((hill_wat.data['Y'] == year0) &
                                   (hill_wat.data['M'] == fire_date.month) &
                                   (hill_wat.data['D'] == fire_date.day))[0][0]

            df = self._run_ash_model_until_gone(fire_date, hill_wat, cli_df,
                                                ini_ash_load, start_index, year0)
            dfs.append(df)

            dates = np.linspace(start_index, start_index + len(df), len(df))
            ax1.plot(dates, df['cum_ash_transport (tonne/ha)'].to_numpy(), color='red')
            ax2.scatter(df['cum_ash_runoff (mm)'].to_numpy(), df['cum_ash_transport (tonne/ha)'].to_numpy(), color='blue')

        ax1.set_ylabel('cumulative ash transport (tonne/ha)')
        ax2.set_xlabel('cumulative ash runoff (mm)')
        ax2.set_ylabel('cumulative ash transport (tonne/ha)')

        fig.savefig(_join(out_dir, f'{prefix}_ash.png'))
        plt.close()
        del fig

        fig2.savefig(_join(out_dir, f'{prefix}_ash_scatter.png'))
        plt.close()
        del fig2

        # Concatenate all DataFrames and save as a Parquet file
        all_dfs = pd.concat(dfs)

        out_fn = _join(out_dir, f'{prefix}_ash.parquet')
        all_dfs.to_parquet(out_fn)

        return out_fn

    def _calc_transportable_ash(self, remaining_ash_tonspha, bulk_density_gmpcm3):
        """
        Calculates the amount of transportable ash in a given volume based on the remaining ash and bulk density.

        Parameters
        ----------
        remaining_ash_tonspha : float
            The amount of remaining ash in tonnes per hectare.
        bulk_density_gmpcm3 : float
            The bulk density of the ash in grams per cubic centimeter.

        Returns
        -------
        Tuple[float, float]
            A tuple containing the remaining ash in millimeters and the transportable ash in tonnes per hectare.

        Raises
        ------
        None

        Examples
        --------
        To calculate the transportable ash with remaining ash of 30 tonnes per hectare and bulk density of 0.8 grams per cubic centimeter,
        the method can be called as follows:

        >>> remaining_mm, transportable_tonspha = _calc_transportable_ash(30, 0.8)
        """
        roughness_limit = self.roughness_limit  # mm
        remaining_mm = remaining_ash_tonspha / (10.0 * bulk_density_gmpcm3)
        transportable_mm = np.clip(remaining_mm - roughness_limit, 0, None)
        transportable_tonspha = transportable_mm * (10.0 * bulk_density_gmpcm3)
        return remaining_mm, transportable_tonspha


    def _run_ash_model_until_gone(self, fire_date, hill_wat, cli_df, ini_ash_load,
                                  start_index, year0):

        assert self.roughness_limit >= 0.0, self.roughness_limit

        org_mat = self.org_mat
        slope = self.slope
        beta0 = self.beta0
        beta1 = self.beta1
        beta2 = self.beta2
        beta3 = self.beta3
        transport_mode = self.transport_mode
        A = self.initranscap
        B = self.depletcoeff
        
        # number of days in the file
        s_len = hill_wat.days_in_sim

        days_from_fire = np.arange(s_len, dtype=np.int64)
        yr = np.roll(hill_wat.data['Y'], -start_index)
        mo = np.roll(hill_wat.data['M'], -start_index)
        da = np.roll(hill_wat.data['D'], -start_index)
        julian = np.roll(hill_wat.data['J'], -start_index)

        assert year0 == yr[0], (year0, yr[0])

        precip = np.roll(hill_wat.data['P (mm)'], -start_index)
        rm = np.roll(hill_wat.data['RM (mm)'], -start_index)
        q = np.roll(hill_wat.data['Q (mm)'], -start_index)
        tsw = np.roll(hill_wat.data['Total-Soil Water (mm)'], -start_index)
        swe = np.roll(hill_wat.data['Snow-Water (mm)'], -start_index)
        cum_q_mm = np.cumsum(q)

        wind_vel = np.roll(cli_df['w-vl'], -start_index)

        infil_mm = rm - q
        cum_infil_mm = np.cumsum(infil_mm)

        fire_year = np.ones(s_len) * np.nan
        bulk_density_gmpcm3 = np.ones(s_len) * np.nan
        porosity = np.ones(s_len) * np.nan
        remaining_ash_tonspha = np.ones(s_len) * np.nan
        transportable_ash_tonspha = np.ones(s_len) * np.nan
        tau = np.zeros(s_len)
        k_r = np.zeros(s_len)
        M_0 = np.zeros(s_len)
        ash_depth_mm = np.ones(s_len) * np.nan
        ash_runoff_mm = np.zeros(s_len)
        transport_tonspha = np.zeros(s_len)
        water_transport_tonspha = np.zeros(s_len)
        wind_transport_tonspha = np.zeros(s_len)
        ash_transport_tonspha = np.zeros(s_len)
        ash_decomp_tonspha = np.zeros(s_len)

        # Model day by day until ash is gone
        cum_ash_runoff_mm = np.zeros(s_len)
        cum_wind_transport_tonspha = np.zeros(s_len)
        cum_water_transport_tonspha = np.zeros(s_len)
        cum_ash_transport_tonspha = np.zeros(s_len)
        cum_ash_decomp_tonspha = np.zeros(s_len)

        w_vl_ifgt = np.zeros(s_len)
        _w_vl_if = 0.0 # max daily wind velocity

        assert ini_ash_load > 0.0, ini_ash_load

        # Let's do this
        i = 0
        _fire_year = 0
        fire_year[i] = _fire_year
        remaining_ash_tonspha[i] = ini_ash_load
        days_from_fire[i] = 0
        infil_mm[i] = 0
        cum_infil_mm[i] = 0
        bulk_density_gmpcm3[i] = self.ini_bulk_den
        porosity[i] = 1.0 - (bulk_density_gmpcm3[i] / self.par_den)
        ash_depth_mm[i], transportable_ash_tonspha[i] = \
            self._calc_transportable_ash(remaining_ash_tonspha[i], self.ini_bulk_den)
        if transportable_ash_tonspha[i] > 0.0:
            M_0[i] = transportable_ash_tonspha[i] ** beta3
        
        i += 1

        # No transport on the day of the fire!
        while transportable_ash_tonspha[i-1] > 0 and i < s_len:
            # determine fire year
            if (mo[i] == fire_date.month and da[i] == fire_date.day):
                _fire_year += 1
            fire_year[i] = _fire_year

            # calculate bulk density
            bulk_density_gmpcm3[i] = self.fin_bulk_den + \
                                     (self.ini_bulk_den - self.fin_bulk_den) * \
                                     np.exp(-self.bulk_den_fac * cum_infil_mm[i])

            # calculate porosity
            porosity[i] = 1.0 - (bulk_density_gmpcm3[i] / self.par_den)
            assert porosity[i] >= 0.0 and porosity[i] <= 1.0, \
                f'porosity must be between 0 and 1, not {porosity[i]}'

            # calculate water transport
            _ash_saturated_storage_mm = ash_depth_mm[i-1] * porosity[i]
            if q[i] > _ash_saturated_storage_mm:
                ash_runoff_mm[i] = np.clip(q[i] - _ash_saturated_storage_mm, 0.0, None)

                # Dynamic transport tau, organic matter, and remaining transportable ash
                # Static transport based on exponential decay

                if ash_runoff_mm[i] > 0.0:
                    if transport_mode == 'dynamic':
                        tau[i] = 9810 * slope * (ash_runoff_mm[i] / 1000.0)
                        k_r[i] = math.exp(beta0) * tau[i] ** beta1 * org_mat ** beta2 * M_0[i-1]
                        transport_tonspha[i] = \
                            transportable_ash_tonspha[i-1] * (1.0 - math.exp(-k_r[i] * ash_runoff_mm[i]))
                    elif transport_mode == 'static':
                        transport_tonspha[i] = ( A / B ) * (
                            math.exp(-B * cum_ash_runoff_mm[:i] - ash_runoff_mm[i]) -
                            math.exp(-B * cum_ash_runoff_mm[i])
                        )

                    water_transport_tonspha[i] = np.clip(transport_tonspha[i],
                                                         0, remaining_ash_tonspha[i-1])

            elif q[i] == 0:
                if self.run_wind_transport:
                    # identify peak wind values within the fire year
                    if  wind_vel[i] > _w_vl_if:
                        _w_vl_if = wind_vel[i]  # store daily wind threshold
                        w_vl_ifgt[i] = _w_vl_if  # track max for comparison

                        # identify the fraction removed by wind from the wind_transport_thresholds.csv
                        wind_transport_tonspha[i] = remaining_ash_tonspha[i-1] * \
                                                    self.lookup_wind_threshold_proportion(w_vl_ifgt[i])

            assert not (wind_transport_tonspha[i] > 0 and water_transport_tonspha[i] > 0), \
                f'wind and water transport cannot occur on the same day'

            # calculate available_ash_tonspha, and ash_depth_mm
            ash_transport_tonspha[i] = wind_transport_tonspha[i] + water_transport_tonspha[i]
            assert not math.isnan(ash_transport_tonspha[i]), f'ash_transport_tonspha is nan on day {i}'

            # calculate cummulative transport variables
            cum_ash_runoff_mm[i] = cum_ash_runoff_mm[i - 1] + ash_runoff_mm[i]
            cum_water_transport_tonspha[i] = cum_water_transport_tonspha[i-1] + water_transport_tonspha[i]
            cum_ash_transport_tonspha[i] = cum_ash_transport_tonspha[i-1] + water_transport_tonspha[i]
            cum_wind_transport_tonspha[i] = cum_wind_transport_tonspha[i-1] + wind_transport_tonspha[i]

            # check transport balance
            assert math.isclose(cum_ash_transport_tonspha[i],
                                cum_wind_transport_tonspha[i] + cum_water_transport_tonspha[i]), \
                f'day {i} transport not balancing {cum_ash_transport_tonspha[i]} ' \
                f'{cum_water_transport_tonspha[i]} {cum_wind_transport_tonspha[i]}'

            # calculate decomposition for day
            _available_ash_for_decomp = remaining_ash_tonspha[i-1] - ash_transport_tonspha[i]
            assert not math.isnan(_available_ash_for_decomp), f'_available_ash_for_decomp is nan on day {i}'

            ash_decomp_tonspha[i] = np.clip(_available_ash_for_decomp * \
                                            (1.0 - np.exp(-self.decomp_fac * infil_mm[i])),
                                             0.0, _available_ash_for_decomp)
            assert not math.isnan(ash_decomp_tonspha[i]), f'ash_decomp_tonspha is nan on day {i}'

            cum_ash_decomp_tonspha[i] = cum_ash_decomp_tonspha[i-1] + ash_decomp_tonspha[i]

            # apply ash_transport
            remaining_ash_tonspha[i] = np.clip(remaining_ash_tonspha[i-1] - \
                                               ash_decomp_tonspha[i] - \
                                               ash_transport_tonspha[i], 0.0, None)

            # calculate ash depth and transportable ash
            ash_depth_mm[i], transportable_ash_tonspha[i] = \
                self._calc_transportable_ash(remaining_ash_tonspha[i], bulk_density_gmpcm3[i])
            assert not math.isnan(ash_depth_mm[i]), f'ash_depth_mm is nan on day {i}'
            assert not math.isnan(transportable_ash_tonspha[i]), f'transportable_ash_tonspha is nan on day {i}'

            if transportable_ash_tonspha[i] > 0.0:
                M_0[i] = transportable_ash_tonspha[i] ** beta3

            # balance check
            assert math.isclose(ini_ash_load - remaining_ash_tonspha[i],
                                cum_ash_transport_tonspha[i] + cum_ash_decomp_tonspha[i]), \
                f'day {i} ash not balancing, { ini_ash_load - remaining_ash_tonspha[i] } ' \
                f'{cum_ash_transport_tonspha[i]} {cum_ash_decomp_tonspha[i]}'


            # increment day
            i += 1

        if transportable_ash_tonspha[i-1] > 0:
            warnings.warn(f'ash transportable {transportable_ash_tonspha[i-1]} not zero, ({hill_wat.fname}, {i}, {s_len})')

#        print(f'{i}\t{np.max(water_transport_tonspha[:i]):.2f}\t{remaining_ash_tonspha[i]:.2f}\t{cum_ash_transport_tonspha[i]:.2f}')

        # convert numpy arrays to pandas dataframe
        df = pd.DataFrame({
            'fire_year (yr)': fire_year[:i].flatten(),
            'year0': (np.ones(i) * year0).flatten(),
            'year': yr[:i].flatten(),
            'da': da[:i].flatten(),
            'mo': mo[:i].flatten(),
            'julian': julian[:i].flatten(),
            'days_from_fire (days)': days_from_fire[:i].flatten(),
            'precip (mm)': precip[:i].flatten(),
            'rainmelt (mm)': rm[:i].flatten(),
            'snow_water_equivalent (mm)': swe[:i].flatten(),
            'runoff (mm)': q[:i].flatten(),
            'tot_soil_water (mm)': tsw[:i].flatten(),
            'infiltration (mm)': infil_mm[:i].flatten(),
            'cum_infiltration (mm)': cum_infil_mm[:i].flatten(),
            'cum_runoff (mm)': cum_q_mm[:i].flatten(),
            'bulk_density (gm/cm3)': bulk_density_gmpcm3[:i].flatten(),
            'porosity': porosity[:i].flatten(),
            'remaining_ash (tonne/ha)': remaining_ash_tonspha[:i].flatten(),
            'transportable_ash (tonne/ha)': transportable_ash_tonspha[:i].flatten(),
            'ash_depth (mm)': ash_depth_mm[:i].flatten(),
            'ash_runoff (mm)': ash_runoff_mm[:i].flatten(),
            'transport (tonne/ha)': transport_tonspha[:i].flatten(),
            'tau': tau[:i].flatten(),
            'k_r': k_r[:i].flatten(),
            'M_0': M_0[:i].flatten(),
            'cum_ash_runoff (mm)': cum_ash_runoff_mm[:i].flatten(),
            'water_transport (tonne/ha)': water_transport_tonspha[:i].flatten(),
            'wind_transport (tonne/ha)': wind_transport_tonspha[:i].flatten(),
            'ash_transport (tonne/ha)': ash_transport_tonspha[:i].flatten(),
            'ash_decomp (tonne/ha)': ash_decomp_tonspha[:i].flatten(),
            'cum_water_transport (tonne/ha)': cum_water_transport_tonspha[:i].flatten(),
            'cum_wind_transport (tonne/ha)': cum_wind_transport_tonspha[:i].flatten(),
            'cum_ash_transport (tonne/ha)': cum_ash_transport_tonspha[:i].flatten(),
            'cum_ash_decomp (tonne/ha)': cum_ash_decomp_tonspha[:i].flatten(),
        }, index=np.arange(i))

        # convert the data type of specific columns as multiple statements
        df['fire_year (yr)'] = df['fire_year (yr)'].astype(np.uint16)
        df['year0'] = df['year0'].astype(np.uint16)
        df['year'] = df['year'].astype(np.uint16)
        df['da'] = df['da'].astype(np.uint16)
        df['mo'] = df['mo'].astype(np.uint16)

        return df

WHITE_ASH_BD = 0.31
BLACK_ASH_BD = 0.22


class WhiteAshModel(AshModelAlex):
    __name__ = 'WhiteAshModel'

    def __init__(self, bulk_density=WHITE_ASH_BD):
        super(WhiteAshModel, self).__init__(
            ash_type=AshType.WHITE,
            ini_bulk_den=WHITE_ASH_BD,  # Initial bulk density, gm/cm3
            fin_bulk_den=0.62,  # Final bulk density, gm/cm3
            bulk_den_fac=0.005,  # Bulk density factor
            par_den=1.2,  # Ash particle density, gm/cm3
            decomp_fac=0.00018,  # Ash decomposition factor, per day
            roughness_limit=1,
            org_mat=0.04,
            beta0=14.33,
            beta1=0.22,
            beta2=5.85,
            beta3=-0.36,
            transport_mode='dynamic',
            initranscap=0.8,    # Initial Transport Capacity (t ha^-1 mm^-1)
            depletcoeff=0.009)  # Depletion coefficient (mm^-1)

    def to_dict(self):
        return {
            'ash_type': str(self.ash_type),
            'ini_bulk_den': self.ini_bulk_den,
            'fin_bulk_den': self.fin_bulk_den,
            'bulk_den_fac': self.bulk_den_fac,
            'par_den': self.par_den,
            'decomp_fac': self.decomp_fac,
            'org_mat': self.org_mat,
            'roughness_limit': self.roughness_limit,
            'transport_mode': getattr(self, 'transport_mode', 'dynamic'),
            'initranscap': getattr(self, 'initranscap', 0.8),
            'depletcoeff': getattr(self, 'depletcoeff', 0.009)
        }


class BlackAshModel(AshModelAlex):
    __name__ = 'BlackAshModel'

    def __init__(self, bulk_density=BLACK_ASH_BD):
        super(BlackAshModel, self).__init__(
            ash_type=AshType.BLACK,
            ini_bulk_den=BLACK_ASH_BD,  # Initial bulk density, gm/cm3
            fin_bulk_den=0.62,  # Final bulk density, gm/cm3
            bulk_den_fac=0.005,  # Bulk density factor
            par_den=1.2,  # Ash particle density, gm/cm3
            decomp_fac=0.00018,  # Ash decomposition factor, per day
            roughness_limit=1,
            org_mat=0.065,
            beta0=14.33,
            beta1=0.22,
            beta2=5.85,
            beta3=-0.36,
            transport_mode='dynamic',
            initranscap=0.8,    # Initial Transport Capacity (t ha^-1 mm^-1)
            depletcoeff=0.009)  # Depletion coefficient (mm^-1)
        
    def to_dict(self):
        return {
            'ash_type': str(self.ash_type),
            'ini_bulk_den': self.ini_bulk_den,
            'fin_bulk_den': self.fin_bulk_den,
            'bulk_den_fac': self.bulk_den_fac,
            'par_den': self.par_den,
            'decomp_fac': self.decomp_fac,
            'org_mat': self.org_mat,
            'roughness_limit': self.roughness_limit,
            'transport_mode': getattr(self, 'transport_mode', 'dynamic'),
            'initranscap': getattr(self, 'initranscap', 0.8),
            'depletcoeff': getattr(self, 'depletcoeff', 0.009)
        }
