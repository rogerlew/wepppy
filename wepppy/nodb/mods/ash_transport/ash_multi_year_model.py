"""Multi-year hillslope ash transport models and helpers."""

from __future__ import annotations

import math
import os
import warnings
from os.path import join as _join
from typing import Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from wepppy.all_your_base import isfloat
from wepppy.all_your_base.dateutils import YearlessDate

from .wind_transport_thresholds import *


_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

pd.options.mode.chained_assignment = None  # default='warn'

from .ash_type import AshType

__all__ = [
    "AshNoDbLockedException",
    "AshModel",
    "WhiteAshModel",
    "BlackAshModel",
]


class AshNoDbLockedException(Exception):
    pass



class AshModel:
    """Base class for hillslope ash transport simulations.

    Subclasses provide calibrated parameter defaults for different ash
    compositions (for example, white versus black ash). The model tracks daily
    runoff, wind transport, and decomposition following a fire.

    Args:
        ash_type: AshType flag controlling wind transport thresholds.
        ini_bulk_den: Initial ash bulk density (grams per cubic centimeter).
        fin_bulk_den: Bulk density after consolidation (grams per cubic centimeter).
        bulk_den_fac: Exponential decay factor applied to bulk density.
        par_den: Particle density for ash solids (grams per cubic centimeter).
        decomp_fac: Daily decomposition factor applied to remaining ash.
        ini_erod: Initial erodibility (tonnes per hectare per millimeter of runoff).
        fin_erod: Residual erodibility once ash consolidates.
        roughness_limit: Depth threshold (millimeters) remaining after transport.
        run_wind_transport: Whether to evaluate wind-driven erosion.
    """

    def __init__(
        self,
        ash_type: AshType,
        ini_bulk_den: Optional[float] = None,
        fin_bulk_den: Optional[float] = None,
        bulk_den_fac: Optional[float] = None,
        par_den: Optional[float] = None,
        decomp_fac: Optional[float] = None,
        ini_erod: Optional[float] = None,
        fin_erod: Optional[float] = None,
        roughness_limit: Optional[float] = None,
        run_wind_transport: bool = False,
    ) -> None:

        assert fin_bulk_den >= ini_bulk_den, (fin_bulk_den, ini_bulk_den)

        self.ash_type = ash_type
        self.ini_ash_depth_mm: Optional[float] = None
        self.ini_ash_load_tonneha: Optional[float] = None
        self.ini_bulk_den = ini_bulk_den  # Initial bulk density, gm/cm3
        self.fin_bulk_den = fin_bulk_den  # Final bulk density, gm/cm3
        self.bulk_den_fac = bulk_den_fac  # Bulk density factor
        self.par_den = par_den  # Ash particle density, gm/cm3
        self.decomp_fac = decomp_fac  # Ash decomposition factor, per day
        self.ini_erod = ini_erod  # Initial erodibility, t/ha
        self.fin_erod = fin_erod  # Final erodibility, t/ha
        self.roughness_limit = roughness_limit  # Roughness limit, mm
        self.run_wind_transport = run_wind_transport

    @property
    def ini_material_available_mm(self) -> float:
        """Initial ash depth available for transport in millimeters."""
        return self.proportion * self.ini_ash_depth_mm

    @property
    def ini_material_available_tonneperha(self) -> float:
        """Initial ash load available for transport (tonnes per hectare)."""
        if self.ini_ash_load_tonneha is not None:
            return self.ini_ash_load_tonneha
        else:
            return 10.0 * self.ini_material_available_mm * self.bulk_density

    def lookup_wind_threshold_proportion(self, w: float) -> float:
        """Return wind-driven transport proportion for a daily peak gust."""
        if w == 0.0:
            return 0.0

        if self.ash_type == AshType.BLACK:
            return lookup_wind_threshold_black_ash_proportion(w)
        elif self.ash_type == AshType.WHITE:
            return lookup_wind_threshold_white_ash_proportion(w)

        raise ValueError(f"Unsupported ash type {self.ash_type!r}")

    def run_model(
        self,
        fire_date: YearlessDate,
        cli_df: pd.DataFrame,
        hill_wat_df: pd.DataFrame,
        out_dir: str,
        prefix: str,
        recurrence: Sequence[int] = (100, 50, 25, 20, 10, 5, 2),
        area_ha: Optional[float] = None,
        ini_ash_depth: Optional[float] = None,  # kept for signature parity
        ini_ash_load: Optional[float] = None,
        run_wind_transport: bool = True,
    ) -> str:

        """Run the ash transport model for each year containing the fire date.

        Args:
            fire_date: Month/day of the fire expressed without a year.
            cli_df: Daily climate data (typically CLIGEN output).
            hill_wat_df: Aggregated daily hillslope water balance dataframe.
            out_dir: Directory where plots and parquet output are written.
            prefix: Basename for generated artifacts.
            recurrence: Historical recurrence intervals (unused placeholder).
            area_ha: Optional hillslope area; retained for signature parity.
            ini_ash_depth: Optional initial ash depth override (unused).
            ini_ash_load: Optional initial ash load override; defaults to
                :attr:`ini_material_available_tonneperha`.
            run_wind_transport: Override for the instance wind transport flag.

        Returns:
            Path to the generated parquet file containing the simulated time
            series.
        """

        self.ini_ash_depth_mm = None
        self.ini_ash_load_tonneha = ini_ash_load
        self.run_wind_transport = run_wind_transport

        assert isfloat(self.par_den), (prefix, self.par_den)
        assert isfloat(self.ini_bulk_den), (prefix, self.ini_bulk_den)
        assert isfloat(self.fin_bulk_den), (prefix, self.fin_bulk_den)
        assert isfloat(self.ini_erod), (prefix, self.ini_erod)
        assert isfloat(self.fin_erod), (prefix, self.fin_erod)

        # timeseries
        fig = plt.figure()
        ax1 = plt.gca()

        # scatter plot
        fig2 = plt.figure()
        ax2 = plt.gca()

        # Create an empty list to store DataFrames
        dfs = []

        years = hill_wat_df['year'].to_numpy(dtype=np.int32, copy=False)
        months = hill_wat_df['month'].to_numpy(dtype=np.int16, copy=False)
        days = hill_wat_df['day_of_month'].to_numpy(dtype=np.int16, copy=False)

        # use np.unique to get the unique years in the climate file
        for year0 in np.unique(years):
            matches = np.flatnonzero((years == year0) &
                                     (months == fire_date.month) &
                                     (days == fire_date.day))
            if len(matches) == 0:
                continue

            start_index = matches[0]

            df = self._run_ash_model_until_gone(
                fire_date,
                hill_wat_df,
                cli_df,
                ini_ash_load,
                start_index,
                year0,
            )
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

    def _calc_transportable_ash(
        self,
        remaining_ash_tonspha: float,
        bulk_density_gmpcm3: float,
    ) -> Tuple[float, float]:
        """Convert remaining ash to depth and transportable load."""
        roughness_limit = self.roughness_limit  # mm
        remaining_mm = remaining_ash_tonspha / (10.0 * bulk_density_gmpcm3)
        transportable_mm = np.clip(remaining_mm - roughness_limit, 0, None)
        transportable_tonspha = transportable_mm * (10.0 * bulk_density_gmpcm3)
        return remaining_mm, transportable_tonspha


    def _run_ash_model_until_gone(
        self,
        fire_date: YearlessDate,
        hill_wat_df: pd.DataFrame,
        cli_df: pd.DataFrame,
        ini_ash_load: float,
        start_index: int,
        year0: int,
    ) -> pd.DataFrame:
        """Simulate post-fire ash decay for one climate year."""

        assert self.roughness_limit >= 0.0, self.roughness_limit

        source_label = hill_wat_df.attrs.get("source_path", "H.wat.parquet")

        # number of days in the file
        s_len = len(hill_wat_df)

        years = hill_wat_df['year'].to_numpy(dtype=np.int32, copy=False)
        months = hill_wat_df['month'].to_numpy(dtype=np.int16, copy=False)
        day_of_month = hill_wat_df['day_of_month'].to_numpy(dtype=np.int16, copy=False)
        julian_days = hill_wat_df['julian'].to_numpy(dtype=np.int16, copy=False)

        days_from_fire = np.arange(s_len, dtype=np.int64)
        yr = np.roll(years, -start_index)
        mo = np.roll(months, -start_index)
        da = np.roll(day_of_month, -start_index)
        julian = np.roll(julian_days, -start_index)

        assert year0 == yr[0], (year0, yr[0])

        precip = np.roll(hill_wat_df['P'].to_numpy(dtype=np.float64, copy=False), -start_index)
        rm = np.roll(hill_wat_df['RM'].to_numpy(dtype=np.float64, copy=False), -start_index)
        q = np.roll(hill_wat_df['Q'].to_numpy(dtype=np.float64, copy=False), -start_index)
        tsw = np.roll(hill_wat_df['Total-Soil Water'].to_numpy(dtype=np.float64, copy=False), -start_index)
        swe = np.roll(hill_wat_df['Snow-Water'].to_numpy(dtype=np.float64, copy=False), -start_index)
        cum_q_mm = np.cumsum(q)

        wind_vel = np.roll(cli_df['w-vl'], -start_index)

        infil_mm = rm - q
        cum_infil_mm = np.cumsum(infil_mm)

        fire_year = np.ones(s_len) * np.nan
        bulk_density_gmpcm3 = np.ones(s_len) * np.nan
        porosity = np.ones(s_len) * np.nan
        remaining_ash_tonspha = np.ones(s_len) * np.nan
        transportable_ash_tonspha = np.ones(s_len) * np.nan
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

                if ash_runoff_mm[i] > 0.0:
                    transport_tonspha[i] = (self.ini_erod - self.fin_erod) * \
                                           np.clip((bulk_density_gmpcm3[i] - self.fin_bulk_den) / \
                                                   (self.ini_bulk_den - self.fin_bulk_den) , 0, 1) + \
                                            self.fin_erod

                    water_transport_tonspha[i] = np.clip(ash_runoff_mm[i] * transport_tonspha[i],
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

            # balance check
            assert math.isclose(ini_ash_load - remaining_ash_tonspha[i],
                                cum_ash_transport_tonspha[i] + cum_ash_decomp_tonspha[i]), \
                f'day {i} ash not balancing, { ini_ash_load - remaining_ash_tonspha[i] } ' \
                f'{cum_ash_transport_tonspha[i]} {cum_ash_decomp_tonspha[i]}'


            # increment day
            i += 1

        if transportable_ash_tonspha[i-1] > 0:
            warnings.warn(
                f'ash transportable {transportable_ash_tonspha[i-1]} not zero, ({source_label}, {i}, {s_len})'
            )

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


class WhiteAshModel(AshModel):
    """AshModel variant calibrated for white ash conditions."""
    __name__ = 'WhiteAshModel'

    def __init__(self, bulk_density=WHITE_ASH_BD):
        super(WhiteAshModel, self).__init__(
            ash_type=AshType.WHITE,
            ini_bulk_den=WHITE_ASH_BD,  # Initial bulk density, gm/cm3
            fin_bulk_den=0.62,  # Final bulk density, gm/cm3
            bulk_den_fac=0.005,  # Bulk density factor
            par_den=1.2,  # Ash particle density, gm/cm3
            decomp_fac=0.00018,  # Ash decomposition factor, per day
            ini_erod=10,  # Initial erodibility, t/ha
            fin_erod=0.1,  # Final erodibility, t/ha
            roughness_limit=1)  # Verify Roughness limit, mm
        
    def to_dict(self) -> dict[str, float | str]:
        """Serialize calibrated model parameters for inspection."""
        return {
            'ash_type': str(self.ash_type),
            'ini_bulk_den': self.ini_bulk_den,
            'fin_bulk_den': self.fin_bulk_den,
            'bulk_den_fac': self.bulk_den_fac,
            'par_den': self.par_den,
            'decomp_fac': self.decomp_fac,
            'ini_erod': self.ini_erod,
            'fin_erod': self.fin_erod,
            'roughness_limit': self.roughness_limit
        }


class BlackAshModel(AshModel):
    """AshModel variant calibrated for black ash conditions."""
    __name__ = 'BlackAshModel'

    def __init__(self, bulk_density=BLACK_ASH_BD):
        super(BlackAshModel, self).__init__(
            ash_type=AshType.BLACK,
            ini_bulk_den=BLACK_ASH_BD,  # Initial bulk density, gm/cm3
            fin_bulk_den=0.62,  # Final bulk density, gm/cm3
            bulk_den_fac=0.005,  # Bulk density factor
            par_den=1.2,  # Ash particle density, gm/cm3
            decomp_fac=0.00018,  # Ash decomposition factor, per day
            ini_erod=1.0,  # Initial erodibility, t/ha
            fin_erod=0.1,  # Final erodibility, t/ha
            roughness_limit=1)   # Verify Roughness limit, mm
        
    def to_dict(self) -> dict[str, float | str]:
        """Serialize calibrated model parameters for inspection."""
        return {
            'ash_type': str(self.ash_type),
            'ini_bulk_den': self.ini_bulk_den,
            'fin_bulk_den': self.fin_bulk_den,
            'bulk_den_fac': self.bulk_den_fac,
            'par_den': self.par_den,
            'decomp_fac': self.decomp_fac,
            'ini_erod': self.ini_erod,
            'fin_erod': self.fin_erod,
            'roughness_limit': self.roughness_limit
        }


# per Sarah
# 40 mm of Rain over 3 months 2 to 3 storms (13-20 mm per storm).
# Removed 10 to 20 mm of ash. 15 mm of ash 46.5 tonne/ha
# Removed all the Ash
