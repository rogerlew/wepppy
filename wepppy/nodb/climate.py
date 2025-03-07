# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import csv
import os
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from wepppy.all_your_base.geo import read_raster

from datetime import datetime, date

from subprocess import Popen, PIPE

from concurrent.futures import (
    ThreadPoolExecutor, wait, FIRST_EXCEPTION, ProcessPoolExecutor, as_completed
)

import json
from enum import IntEnum
import random
from glob import glob

import shutil

from shutil import copyfile
import multiprocessing

import pandas as pd

# non-standard
import jsonpickle

from wepppy.climates.downscaled_nmme_client import retrieve_rcp85_timeseries

# wepppy
from wepppy.climates import cligen_client as cc
from wepppy.climates.prism import prism_mod
from wepppy.climates.daymet import retrieve_historical_timeseries as daymet_retrieve_historical_timeseries
from wepppy.climates.gridmet import retrieve_historical_timeseries as gridmet_retrieve_historical_timeseries
from wepppy.climates.gridmet import retrieve_historical_wind as gridmet_retrieve_historical_wind
from wepppy.climates.gridmet import retrieve_historical_precip as gridmet_retrieve_historical_precip
#from wepppy.climates.daymet import single_point_extraction as daymet_single_point_extraction
from wepppy.climates.prism.daily_client import retrieve_historical_timeseries as prism_retrieve_historical_timeseries
from wepppy.eu.climates.eobs import eobs_mod
from wepppy.au.climates.agdc import agdc_mod
from wepppy.climates.cligen import (
    CligenStationsManager, 
    ClimateFile, 
    Cligen,
    df_to_prn
)
from wepppy.all_your_base import isint, isfloat, NCPU
from wepppy.all_your_base.geo import RasterDatasetInterpolator
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.topo.watershed_abstraction.support import is_channel
import numpy as np

from copy import deepcopy

import pyproj
from pyproj import Proj

# wepppy submodules
from .base import NoDbBase, TriggerEvents
from .watershed import Watershed, WatershedNotAbstractedError
from .ron import Ron
from .redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.mixins.log_mixin import LogMixin


import requests

import wepppyo3
from wepppyo3.climate import cli_revision as pyo3_cli_revision
from wepppyo3.climate import calculate_monthlies as pyo3_cli_calculate_monthlies
from wepppyo3.climate import calculate_p_annual_monthlies as pyo3_cli_calculate_annual_monthlies
from wepppyo3.climate import rust_cli_p_scale as pyo3_cli_p_scale
from wepppyo3.climate import rust_cli_p_scale_monthlies as pyo3_cli_p_scale_monthlies
from wepppyo3.climate import rust_cli_p_scale_annual_monthlies as pyo3_cli_p_scale_annual_monthlies


def lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height):
    # Create a projection object for the raster
    raster_proj = Proj(proj4)

    # Create a projection object for WGS84 (lat/long)
    wgs84_proj = Proj(proj='latlong', datum='WGS84')

    # Convert the input lng/lat to the raster's projection
    x, y = pyproj.transform(wgs84_proj, raster_proj, lng, lat)

    # Apply the affine transformation to get pixel coordinates
    # Note: Affine transform is in the form of (a, b, c, d, e, f)
    # where x' = a * x + b * y + c and y' = d * x + e * y + f
    a, b, c, d, e, f = transform
    col = (x - a) / b
    row = (y - d) / f

    # Get nearest pixel center
    col, row = round(col), round(row)

    # Check if the pixel is within the bounds of the raster
    if 0 <= col < width and 0 <= row < height:
        # Convert the pixel position back to geographic coordinates
        lng, lat = pyproj.transform(raster_proj, wgs84_proj, col * b + a, row * f + d)
        return lng, lat
    else:
        return None, None


def daymet_pixel_center(lng, lat):
    width, height = (7814, 8075)
    proj4 = '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'
    transform = (-4560750.0, 1000.0, 0.0, 4984500.0, 0.0, -1000.0)

    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)
    
    
def gridmet_pixel_center(lng, lat):
    width, height = (1386, 585)
    proj4 = '+proj=longlat +datum=WGS84 +no_defs'
    transform = (-124.79299639760372, 0.04166601298087771, 0.0, 49.41685580390774, 0.0, -0.041666014553749395)

    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)


def prism4k_pixel_center(lng, lat):
    width, height = (1405, 621)
    proj4 = '+proj=longlat +datum=NAD83 +no_defs'
    transform = (-125.02083333333336, 0.0416666666667, 0.0, 49.93749999999975, 0.0, -0.0416666666667)

    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)


def nexrad_pixel_center(lng, lat):
    return round(lng * 4.0) / 4.0, round(lat * 4.0) / 4.0



def download_file(url, dst):
    response = requests.get(url)
    if response.status_code == 200:
        with open(dst, 'wb') as file:
            file.write(response.content)
    else:
        raise Exception(f'Error retrieving file from {url}')


def breakpoint_file_fix(fn):
    with open(fn) as fp:
        lines = fp.readlines()

    lines[13] = 'da mo year nbrkpt tmax  tmin    rad   w-vel  w-dir   tdew\n'
    lines[14] = '                (mm)    (C)   (C) (l/day) (m/sec)(deg)    (C)\n'

    with open(fn, 'w') as fp:
        fp.writelines(lines)


CLIMATE_MAX_YEARS = 1000

if NCPU > 24:
    NCPU = 24

class ClimateSummary(object):
    def __init__(self):
        self.par_fn = None
        self.description = None
        self.climatestation = None
        self._cli_fn = None


class NoClimateStationSelectedError(Exception):
    """
    Select a climate station before building climate.
    """

    __name__ = 'NoClimateStationSelectedError'

    def __init__(self):
        pass


class ClimateModeIsUndefinedError(Exception):
    """
    Select a climate mode before building climate.
    """

    __name__ = 'ClimateModeIsUndefinedError'

    def __init__(self):
        pass

class ClimateNoDbLockedException(Exception):
    pass


class ClimateStationMode(IntEnum):
    Undefined = -1
    Closest = 0
    Heuristic = 1
    EUHeuristic = 2
    AUHeuristic = 3
    UserDefined = 4
    MesonetIA = 5


class ClimateMode(IntEnum):
    Undefined = -1
    Vanilla = 0     # Single Only
    Observed = 2    # Daymet, single or multiple
    ObservedPRISM = 9    # Daymet, single or multiple
    Future = 3      # Single Only
    SingleStorm = 4 # Single Only
    PRISM = 5       # Single or multiple
    ObservedDb = 6
    FutureDb = 7
    EOBS = 8       # Single or multiple
    AGDC = 10       # Single or multiple
    GridMetPRISM = 11    # Daymet, single or multiple
    UserDefined = 12
    DepNexrad = 13
    SingleStormBatch = 14 # Single Only
    UserDefinedSingleStorm = 15 # Single Only

    @staticmethod
    def parse(x):
        if x == None:
            return ClimateMode.Undefined
        elif x == 'vanilla':
            return ClimateMode.Vanilla
        elif x == 'observed':
            return ClimateMode.Observed
        elif x == 'observed_prism':
            return ClimateMode.ObservedPRISM
        elif x == 'future':
            return ClimateMode.Future
        elif x == 'single_storm':
            return ClimateMode.SingleStorm
        elif x == 'prism':
            return ClimateMode.PRISM
        elif x == 'observed_db':
            return ClimateMode.ObservedDb
        elif x == 'future_db':
            return ClimateMode.FutureDb
        elif x == 'eobs':
            return ClimateMode.EOBS
        elif x == 'agdc':
            return ClimateMode.AGDC
        elif x == 'gridmet_prism':
            return ClimateMode.GridMetPRISM
        elif x == 'user_defined':
            return ClimateMode.UserDefined
        elif x == 'dep_nexrad':
            return ClimateMode.DepNexrad
        elif x == 'user_defined_single_storm':
            return ClimateMode.UserDefinedSingleStorm
        raise KeyError


class ClimateSpatialMode(IntEnum):
    Undefined = -1
    Single = 0
    Multiple = 1
    MultipleInterpolated = 2

    @staticmethod
    def parse(x):
        if x == None:
            return ClimateSpatialMode.Undefined
        elif x == 'single':
            return ClimateSpatialMode.Single
        elif x == 'multiple':
            return ClimateSpatialMode.Multiple
        elif x == 'multiple_interpolated':
            return ClimateSpatialMode.MultipleInterpolated
        raise KeyError


class ClimatePrecipScalingMode(IntEnum):
    NoScaling = 0
    Scalar = 1
    Monthlies = 2
    AnnualMonthlies = 3
    Spatial = 4

    @staticmethod
    def parse(x):
        if x == None or x == 'no_scaling':
            return ClimatePrecipScalingMode.NoScaling
        elif x == 'scalar':
            return ClimatePrecipScalingMode.Scalar
        elif x == 'monthlies':
            return ClimatePrecipScalingMode.Monthlies
        elif x == 'annual_monthlies':
            return ClimatePrecipScalingMode.AnnualMonthlies
        elif x == 'spatial':
            return ClimatePrecipScalingMode.Spatial
        raise KeyError


def get_prism_p_annual_monthlies(lng, lat, start_year, end_year):
    df = prism_retrieve_historical_timeseries(lng, lat, start_year, end_year)
    months = df['date'].month
    precip = df['ppt(mm)'].values
    return pyo3_cli_calculate_annual_monthlies(months=months, ppts=precip)


def build_observed_prism(cligen, lng, lat, start_year, end_year, cli_dir, prn_fn, cli_fn, gridmet_wind=True):
    df = prism_retrieve_historical_timeseries(lng, lat, start_year, end_year, gridmet_wind=gridmet_wind)
    df_to_prn(df, _join(cli_dir, prn_fn), 'ppt(mm)', 'tmax(degc)', 'tmin(degc)')
    
    max_retries = 3
    for retry in range(max_retries):
        try:
            cligen.run_observed(prn_fn, cli_fn=cli_fn)
            break
        except AssertionError:
            if retry == max_retries - 1:
                raise
            import time
            time.sleep(0.5 * (retry + 1))

    dates = df.index

    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.replace_var('tdew', dates, df['tdmean(degc)'])

    if gridmet_wind:
        climate.replace_var('w-vl', dates, df['vs(m/s)'])
        climate.replace_var('w-dir', dates, df['th(DegreesClockwisefromnorth)'])

    df.to_parquet(_join(cli_dir, f'prism_{start_year}-{end_year}.parquet'))

    climate.write(cli_path)


def get_daymet_p_annual_monthlies(lng, lat, start_year, end_year):
    df = daymet_retrieve_historical_timeseries(lng, lat, start_year, end_year, gridmet_wind=False)
    months = df.index.month
    precip = df['prcp(mm/day)'].values
    return pyo3_cli_calculate_annual_monthlies(months=months, ppts=precip)


def build_observed_daymet(cligen, lng, lat, start_year, end_year, cli_dir, prn_fn, cli_fn, gridmet_wind=True):
    df = daymet_retrieve_historical_timeseries(lng, lat, start_year, end_year, gridmet_wind=gridmet_wind)
    df.to_parquet(_join(cli_dir, f'daymet_{start_year}-{end_year}.parquet'))
    df_to_prn(df, _join(cli_dir, prn_fn), 'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)')    

    max_retries = 3
    for retry in range(max_retries):
        try:
            cligen.run_observed(prn_fn, cli_fn=cli_fn)
            break
        except AssertionError:
            if retry == max_retries - 1:
                raise
            import time
            time.sleep(0.5 * (retry + 1))

    dates = df.index

    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.replace_var('rad', dates, df['srad(l/day)'])
    climate.replace_var('tdew', dates, df['tdew(degc)'])

    if gridmet_wind:
        climate.replace_var('w-vl', dates, df['vs(m/s)'])
        climate.replace_var('w-dir', dates, df['th(DegreesClockwisefromnorth)'])

    df.to_parquet(_join(cli_dir, f'daymet_{start_year}-{end_year}.parquet'))

    climate.write(cli_path)


def build_observed_daymet_interpolated(cligen, topaz_id, lng, lat, start_year, end_year, cli_dir, cli_fn, prn_fn, wind_vs=None, wind_dir=None):
    # uses .prn files generated by wepppy.climates.daymet.daily_interpolated

    _parquet_fn = f'daymet_observed_{topaz_id}_{start_year}-{end_year}.parquet'
    df = pd.read_parquet(_join(cli_dir,  _parquet_fn))

    attempts = 3
    for attempt in range(attempts):
        try:
            cligen.run_observed(prn_fn, cli_fn=cli_fn)
            break
        except AssertionError:
            if attempt == attempts - 1:
                raise Exception('cligen.run_observed failed')

    dates = df.index

    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.replace_var('rad', dates, df['srad(l/day)'])
    climate.replace_var('tdew', dates, df['tdew(degc)'])

    if wind_vs is not None:
        climate.replace_var('w-vl', dates, wind_vs)

    if wind_dir is not None:
        climate.replace_var('w-dir', dates, wind_dir)

    climate.write(cli_path)

    return topaz_id


def build_observed_snotel(cligen, lng, lat, snotel_id, start_year, end_year, cli_dir, prn_fn, cli_fn, gridmet_supplement=True):
    import pandas as pd
    snotel_data_dir = '/workdir/wepppy/wepppy/climates/snotel/processed'

    df = pd.read_csv(_join(snotel_data_dir, f'{snotel_id}.csv'), parse_dates=[0], na_values=['', ' '])

    # Adding a 'Year' column to the DataFrame
    df['Year'] = df['Date'].dt.year

    # apply start_year filter
    df = df[df['Year'] >= start_year]
    df = df[df['Year'] <= end_year]

    start_year = min(df['Year'])
    end_year = max(df['Year'])

    df['prcp(mm/day)'] = df['Precipitation Increment (in)'] * 25.4
    df['tmax(degc)'] = (df['Air Temperature Maximum (degF)'] - 32) * 5/9
    df['tmin(degc)'] = (df['Air Temperature Minimum (degF)'] - 32) * 5/9

    df.to_parquet(_join(cli_dir, f'snotel_{start_year}-{end_year}.parquet'))
    df_to_prn(df.set_index('Date'), _join(cli_dir, prn_fn), 'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)')
    cligen.run_observed(prn_fn, cli_fn=cli_fn)


    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    if gridmet_supplement:

        wind_df = gridmet_retrieve_historical_timeseries(lng, lat, start_year, end_year)

        dates = df.index
        climate.replace_var('rad', dates, wind_df['srad(l/day)'])
        climate.replace_var('tdew', dates, wind_df['tdew(degc)'])

        wind_dates = wind_df.index

        climate.replace_var('w-vl', wind_dates, wind_df['vs(m/s)'])
        climate.replace_var('w-dir', wind_dates, wind_df['th(DegreesClockwisefromnorth)'])

        df['vs(m/s)'] = wind_df['vs(m/s)']
        df['vs(m/s)'] = wind_df['th(DegreesClockwisefromnorth)']

        df.to_parquet(_join(cli_dir, f'snotel_gridmet_{start_year}-{end_year}.parquet'))
    else:
        df.to_parquet(_join(cli_dir, f'snotel_{start_year}-{end_year}.parquet'))

    climate.write(cli_path)


def get_gridmet_p_annual_monthlies(lng, lat, start_year, end_year):
    df = gridmet_retrieve_historical_precip(lng, lat, start_year, end_year)
    months = df.index.month
    precip = df['pr(mm/day)'].values
    return pyo3_cli_calculate_annual_monthlies(months=months, ppts=precip)


def build_observed_gridmet(cligen, lng, lat, start_year, end_year, cli_dir, prn_fn, cli_fn):
    df = gridmet_retrieve_historical_timeseries(lng, lat, start_year, end_year)
    df.to_parquet(_join(cli_dir, f'gridmet_{start_year}-{end_year}.parquet'))
    df_to_prn(df, _join(cli_dir, prn_fn), 'pr(mm/day)', 'tmmx(degc)', 'tmmn(degc)')
    
    max_retries = 3
    for retry in range(max_retries):
        try:
            cligen.run_observed(prn_fn, cli_fn=cli_fn)
            break
        except AssertionError:
            if retry == max_retries - 1:
                raise
            import time
            time.sleep(0.5 * (retry + 1))

    dates = df.index

    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.replace_var('rad', dates, df['srad(l/day)'])
    climate.replace_var('tdew', dates, df['tdew(degc)'])
    climate.replace_var('w-vl', dates, df['vs(m/s)'])
    climate.replace_var('w-dir', dates, df['th(DegreesClockwisefromnorth)'])

    climate.write(cli_path)


def build_observed_gridmet_interpolated(cligen, topaz_id, lng, lat, start_year, end_year, cli_dir, cli_fn, prn_fn):
    # uses .prn files generated by wepppy.climates.daymet.daily_interpolated

    _parquet_fn = f'gridmet_observed_{topaz_id}_{start_year}-{end_year}.parquet'
    df = pd.read_parquet(_join(cli_dir,  _parquet_fn))

    cligen.run_observed(prn_fn, cli_fn=cli_fn)

    dates = df.index

    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.replace_var('rad', dates, df['srad(l/day)'])
    climate.replace_var('tdew', dates, df['tdew(degc)'])
    climate.replace_var('w-vl', dates, df['vs(m/s)'])
    climate.replace_var('w-dir', dates, df['th(DegreesClockwisefromnorth)'])

    climate.write(cli_path)

    return topaz_id


def build_future(cligen, lng, lat, start_year, end_year, cli_dir, prn_fn, cli_fn):
    df = retrieve_rcp85_timeseries(lng, lat,
                                   datetime(start_year, 1, 1),
                                   datetime(end_year, 12, 31))
    df_to_prn(df, _join(cli_dir, prn_fn), u'pr(mm)', u'tasmax(degc)', u'tasmin(degc)')
    cligen.run_observed(prn_fn, cli_fn=cli_fn)

    dates = df.index

    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.write(cli_path)



def mod_func_wrapper_factory(mod_func):
    def mod_func_wrapper(kwds):
        mod_func(**kwds)

    return mod_func_wrapper


def get_monthlies(fn, lng, lat):
    cmd = ['gdallocationinfo', '-wgs84', '-valonly', fn, str(lng), str(lat)]
    #    print cmd

    p = Popen(cmd, stdout=PIPE)
    p.wait()

    out = p.stdout.read()

    return [float(v) for v in out.decode('utf-8').strip().split('\n')]


def cli_revision(cli: ClimateFile, ws_ppts: np.array, ws_tmaxs: np.array, ws_tmins: np.array,
                 ppt_fn: str, tmin_fn: str, tmax_fn: str, hill_lng: float, hill_lat: float, new_cli_path: str):

    hill_ppts = get_monthlies(ppt_fn, hill_lng, hill_lat)
    hill_tmins = get_monthlies(tmin_fn, hill_lng, hill_lat)
    hill_tmaxs = get_monthlies(tmax_fn, hill_lng, hill_lat)

    if wepppyo3 is not None and not cli.breakpoint:
        pyo3_cli_revision(cli.cli_fn, new_cli_path,
                          ws_ppts, ws_tmaxs, ws_tmins,
                          hill_ppts, hill_tmaxs, hill_tmins)
        assert _exists(new_cli_path), 'wepppyo3.climate.cli_revision failed'
        return new_cli_path


    cli2 = deepcopy(cli)

    df = cli2.as_dataframe()
    rev_ppt = np.zeros(df.prcp.shape)
    rev_tmax = np.zeros(df.prcp.shape)
    rev_tmin = np.zeros(df.prcp.shape)
    dates = []

    for index, row in df.iterrows():
        mo = int(row.mo) - 1
        rev_ppt[index] = row.prcp * hill_ppts[mo] / ws_ppts[mo]
        rev_tmax[index] = row.tmax - ws_tmaxs[mo] + hill_tmaxs[mo]
        rev_tmin[index] = row.tmin - ws_tmins[mo] + hill_tmins[mo]

        # todo check that tdew is >= tmin
        dates.append((int(row.year), int(row.mo), int(row.da)))

    cli2.replace_var('prcp', dates, rev_ppt)
    cli2.replace_var('tmax', dates, rev_tmax)
    cli2.replace_var('tmin', dates, rev_tmin)

    cli2.write(new_cli_path)
    del cli2


# noinspection PyUnusedLocal
class Climate(NoDbBase, LogMixin):
    def __init__(self, wd, cfg_fn):
        super(Climate, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._input_years = 100
            self._climatestation_mode = ClimateStationMode.Undefined
            self._climatestation = None

            # this gets called from Ron.__init__ before it serializes
            locales = self.config_get_list('general', 'locales')

            if 'eu' in locales:
                self._climate_mode = ClimateMode.EOBS
            if 'au' in locales:
                self._climate_mode = ClimateMode.AGDC
            else:
                self._climate_mode = ClimateMode.Undefined
            self._climate_spatialmode = ClimateSpatialMode.Single
            self._cligen_seed = None
            self._observed_start_year = ''
            self._observed_end_year = ''
            self._future_start_year = ''
            self._future_end_year = ''
            self._ss_storm_date = '4 15 01'
            self._ss_design_storm_amount_inches = 6.3
            self._ss_duration_of_storm_in_hours = 6.0
            self._ss_time_to_peak_intensity_pct = 0.4
            self._ss_max_intensity_inches_per_hour = 3.0
            self._ss_batch = ''
            self._ss_batch_storms = None

            self._precip_scaling_mode = None
            
            self._precip_scale_factor =  self.config_get_float('climate', 'precip_scale_factor', None)
            if self._precip_scale_factor is not None:
                self._precip_scaling_mode = ClimatePrecipScalingMode.Scalar
            
            self._precip_scale_factor_map =  self.config_get_path('climate', 'precip_scale_factor_map', None)
            if self._precip_scale_factor_map is not None:
                self._precip_scaling_mode = ClimatePrecipScalingMode.Spatial
                
            # these gridmet and daymet specific config variables pre-date the ClimatePrecipScalingMode
            sf =  self.config_get_float('climate', 'gridmet_precip_scale_factor', None)
            if sf is not None:
                self._precip_scale_factor = sf
                self._precip_scaling_mode = ClimatePrecipScalingMode.Scalar
            
            sf_map =  self.config_get_path('climate', 'gridmet_precip_scale_factor_map', None)
            if sf_map is not None:
                self._precip_scale_factor_map = sf_map
                self._precip_scaling_mode = ClimatePrecipScalingMode.Spatial
            
            sf =  self.config_get_float('climate', 'daymet_precip_scale_factor', None)
            if sf is not None:
                self._precip_scale_factor = sf
                self._precip_scaling_mode = ClimatePrecipScalingMode.Scalar
                
            sf_map =  self.config_get_path('climate', 'daymet_precip_scale_factor_map', None)
            if sf_map is not None:
                self._precip_scale_factor_map = sf_map
                self._precip_scaling_mode = ClimatePrecipScalingMode.Spatial

            if self._precip_scaling_mode is None:
                self._precip_scaling_reference = self.config_get_str('climate', 'precip_scale_reference', 'no_scaling')
            
            sf =  self.config_get_list('climate', 'precip_monthly_scale_factors', None)
            if sf is not None:
                sf = [float(v) for v in sf]
            else:
                sf = [1 for i in range(12)]
            self._precip_monthly_scale_factors = sf
            
            self._precip_scaling_mode = ClimatePrecipScalingMode.parse(self.config_get_str('climate', 'precip_scale_mode', None))
            
            self._climate_daily_temp_ds = None

            self._orig_cli_fn = None

            self.monthlies = None
            self.par_fn = None
            self.cli_fn = None

            self.sub_par_fns = None
            self.sub_cli_fns = None

            self._closest_stations = None
            self._heuristic_stations = None

            cli_dir = self.cli_dir
            if not _exists(cli_dir):
                os.mkdir(cli_dir)

            self._cligen_db = self.config_get_path('climate', 'cligen_db')
            assert self._cligen_db is not None

            _observed_clis_wc = self.config_get_path('climate', 'observed_clis_wc')
            _future_clis_wc = self.config_get_path('climate', 'future_clis_wc')

            self._observed_clis_wc = _observed_clis_wc
            self._future_clis_wc = _future_clis_wc

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'climate.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read().replace('"orig_cli_fn"', '"_orig_cli_fn"'))
            assert isinstance(db, Climate)

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Climate.getInstance(
            get_wd(runid, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock))

    @property
    def _status_channel(self):
        return f'{self.runid}:climate'

    @property
    def daymet_last_available_year(self):
        return 2023

    @property
    def precip_scale_reference(self):
        return getattr(self, '_precip_scale_reference', None)
    
    @precip_scale_reference.setter
    def precip_scale_reference(self, value):
        
        assert value is None or value in ['prism', 'daymet', 'gridmet']
        
        self.lock()

        # noinspection PyBroadInspection
        try:
            self._precip_scale_reference = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def precip_monthly_scale_factors(self):
        return getattr(self, '_precip_monthly_scale_factors', [1 for i in range(12)])
    
    @precip_monthly_scale_factors.setter
    def precip_monthly_scale_factors(self, value):
        
        assert value is None or len(value) == 12
        
        self.lock()

        # noinspection PyBroadInspection
        try:
            self._precip_monthly_scale_factors = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def precip_scale_factor(self):
        return getattr(self, '_precip_scale_factor', None)

    @precip_scale_factor.setter
    def precip_scale_factor(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self._precip_scale_factor = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def precip_scale_factor_map(self):
        return getattr(self, '_precip_scale_factor_map', None)

    @property
    def gridmet_precip_scale_factor(self):
        return getattr(self, '_gridmet_precip_scale_factor', None)

    @property
    def gridmet_precip_scale_factor_map(self):
        return getattr(self, '_gridmet_precip_scale_factor_map', None)

    @property
    def daymet_precip_scale_factor(self):
        return getattr(self, '_daymet_precip_scale_factor', None)

    @property
    def daymet_precip_scale_factor_map(self):
        return getattr(self, '_daymet_precip_scale_factor_map', None)

    @property
    def _nodb(self):
        return _join(self.wd, 'climate.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'climate.nodb.lock')

    @property
    def cligen_db(self):
        return getattr(self, '_cligen_db', self.config_get_str('climate', 'cligen_db'))

    @property
    def cli_path(self):
        return _join(self.cli_dir, self.cli_fn)

    @property
    def is_breakpoint(self):
        cli = ClimateFile(self.cli_path)
        return cli.breakpoint

    @property
    def status_log(self):
        return os.path.abspath(_join(self.cli_dir, 'status.log'))

    @property
    def observed_clis(self):
        wc = getattr(self, '_observed_clis_wc', None)
        if wc is None:
            return None

        return glob(_join(wc, '*.cli'))

    @property
    def future_clis(self):
        wc = getattr(self, '_future_clis_wc', None)
        if wc is None:
            return None

        return glob(_join(wc, '*.cli'))

    @property
    def years(self):
        return self._input_years

    @property
    def observed_start_year(self):
        return self._observed_start_year

    @property
    def observed_end_year(self):
        return self._observed_end_year

    @property
    def future_start_year(self):
        return self._future_start_year

    @property
    def future_end_year(self):
        return self._future_end_year

    @property
    def ss_storm_date(self):
        return self._ss_storm_date

    @property
    def ss_design_storm_amount_inches(self):
        return self._ss_design_storm_amount_inches

    @property
    def ss_duration_of_storm_in_hours(self):
        return self._ss_duration_of_storm_in_hours

    @property
    def ss_time_to_peak_intensity_pct(self):
        return self._ss_time_to_peak_intensity_pct

    @property
    def ss_max_intensity_inches_per_hour(self):
        return self._ss_max_intensity_inches_per_hour

    @property
    def ss_batch_storms(self):
        return getattr(self, '_ss_batch_storms', None)

    @property
    def ss_batch(self):
        return getattr(self, '_ss_batch', '')


    @ss_batch.setter
    def ss_batch(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._ss_batch = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def climate_daily_temp_ds(self):
        return getattr(self, '_climate_daily_temp_ds', 'null')

    @climate_daily_temp_ds.setter
    def climate_daily_temp_ds(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._climate_daily_temp_ds = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def daymet_version(self):
        return getattr(self, '_daymet_version', 'v4')


    @daymet_version.setter
    def daymet_version(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._daymet_version = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # climatestation_mode
    #
    @property
    def climatestation_mode(self):
        return self._climatestation_mode

    @property
    def has_climatestation_mode(self):
        return self._climatestation_mode \
               is not ClimateStationMode.Undefined

    @climatestation_mode.setter
    def climatestation_mode(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            if isinstance(value, ClimateStationMode):
                self._climatestation_mode = value

            elif isinstance(value, int):
                self._climatestation_mode = ClimateStationMode(value)

            else:
                raise ValueError('most be ClimateStationMode or int')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    # noinspection PyPep8Naming
    @property
    def onLoad_refreshStationSelection(self):
        return json.dumps(self.climatestation_mode is not ClimateStationMode.Undefined)

    @property
    def year0(self):
        try:
            cli_fn = self.cli_fn

            if cli_fn is None:
                return False

            cli_path = _join(self.cli_dir, self.cli_fn)
            cli = ClimateFile(cli_path)
            years = cli.years

            return years[0]
        except:
            return None

    @property
    def has_observed(self):
        try:
            cli_fn = self.cli_fn

            if cli_fn is None:
                return False

            cli_path = _join(self.cli_dir, self.cli_fn)
            cli = ClimateFile(cli_path)
            years = cli.years

            return all(yr > 1900 for yr in years)
        except:
            return None

    #
    # climatestation
    #
    @property
    def climatestation(self):
        return self._climatestation

    @climatestation.setter
    def climatestation(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self._climatestation = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def climatestation_meta(self):
        climatestation = self.climatestation

        if climatestation is None:
            return None

        station_manager = CligenStationsManager(version=self.cligen_db)
        station_meta = station_manager.get_station_fromid(climatestation)
        assert station_meta is not None

        return station_meta

    @property
    def climatestation_par_contents(self):
        par_fn = self.climatestation_meta.parpath
        with open(par_fn) as fp:
            return fp.read()

    #
    # climate_mode
    #
    @property
    def climate_mode(self):
        return self._climate_mode

    @climate_mode.setter
    def climate_mode(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            if isinstance(value, ClimateMode):
                self._climate_mode = value
            elif isint(value):
                self._climate_mode = ClimateMode(int(value))
            else:
                self._climate_mode = ClimateMode.parse(value)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def is_single_storm(self):
        return self._climate_mode in (
    ClimateMode.SingleStorm,
    ClimateMode.SingleStormBatch,
    ClimateMode.UserDefinedSingleStorm)



    #
    # precip_scaling_mode
    #
    @property
    def precip_scaling_mode(self):
        if not hasattr(self, '_precip_scaling_mode'):
            return ClimatePrecipScalingMode.NoScaling
        
        return self._precip_scaling_mode

    @precip_scaling_mode.setter
    def precip_scaling_mode(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            if isinstance(value, ClimatePrecipScalingMode):
                self._precip_scaling_mode = value

            elif isinstance(value, int):
                self._precip_scaling_mode = ClimatePrecipScalingMode(value)

            else:
                self._precip_scaling_mode = ClimatePrecipScalingMode.parse(value)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
        
    #
    # precip_scaling_reference
    #
    @property
    def precip_scaling_reference(self):
        if not hasattr(self, '_precip_scaling_reference'):
            return None
        
        return self._precip_scaling_reference

    @precip_scaling_reference.setter
    def precip_scaling_reference(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self._precip_scaling_reference = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # climate_spatial mode
    #
    @property
    def climate_spatialmode(self):
        return self._climate_spatialmode

    @climate_spatialmode.setter
    def climate_spatialmode(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            if isinstance(value, ClimateSpatialMode):
                self._climate_spatialmode = value

            elif isinstance(value, int):
                self._climate_spatialmode = ClimateSpatialMode(value)

            else:
                self._climate_spatialmode = ClimateSpatialMode.parse(value)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # station search
    #

    def find_closest_stations(self, num_stations=10):
        self.lock()

        # noinspection PyBroadInspection
        try:
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            station_manager = CligenStationsManager(version=self.cligen_db)
            results = station_manager\
                .get_closest_stations((lng, lat), num_stations)
            self._closest_stations = results

            self._climatestation = results[0].id
            self.dump_and_unlock()
            return self.closest_stations

        except Exception:
            self.unlock('-f')
            raise

    @property
    def closest_stations(self):
        """
        returns heuristic_stations as jsonifyable dicts
        """
        if self._closest_stations is None:
            return None

        return [s.as_dict() for s in self._closest_stations]

    def find_heuristic_stations(self, num_stations=10):
        if 'eu' in self.locales:
            return self.find_eu_heuristic_stations(num_stations=num_stations)
        if 'au' in self.locales:
            return self.find_au_heuristic_stations(num_stations=num_stations)

        self.lock()

        # noinspection PyBroadInspection
        try:
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid

            station_manager = CligenStationsManager(version=self.cligen_db)
            results = station_manager\
                .get_stations_heuristic_search((lng, lat), num_stations)
            self._heuristic_stations = results

            self._climatestation = results[0].id
            self.dump_and_unlock()
            return self.heuristic_stations

        except Exception:
            self.unlock('-f')
            raise

    def find_eu_heuristic_stations(self, num_stations=10):
        self.lock()

        # noinspection PyBroadInspection
        try:
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid

            rdi = RasterDatasetInterpolator(watershed.dem_fn)
            elev = rdi.get_location_info(lng, lat, method='near')

            station_manager = CligenStationsManager(version=self.cligen_db)
            results = station_manager\
                .get_stations_eu_heuristic_search((lng, lat), elev, num_stations)
            self._heuristic_stations = results

            self._climatestation = results[0].id
            self.dump_and_unlock()
            return self.heuristic_stations

        except Exception:
            self.unlock('-f')
            raise

    def find_au_heuristic_stations(self, num_stations=None):
        self.lock()

        # noinspection PyBroadInspection
        try:
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid

            rdi = RasterDatasetInterpolator(watershed.dem_fn)
            elev = rdi.get_location_info(lng, lat, method='near')

            station_manager = CligenStationsManager(version=self.cligen_db)
            results = station_manager\
                .get_stations_au_heuristic_search((lng, lat), elev, num_stations)
            self._heuristic_stations = results

            self._climatestation = results[0].id
            self.dump_and_unlock()
            return self.heuristic_stations

        except Exception:
            self.unlock('-f')
            raise

    @property
    def heuristic_stations(self):
        """
        returns heuristic_stations as dicts
        """
        if self._heuristic_stations is None:
            return None

        return [s.as_dict() for s in self._heuristic_stations]

    @property
    def orig_cli_fn(self):
        return self._orig_cli_fn

    @orig_cli_fn.setter
    def orig_cli(self, value):

        self.lock()

        # noinspection PyBroadInspection
        try:
            self._orig_cli_fn = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def input_years(self):
        return self._input_years

    @input_years.setter
    def input_years(self, value):

        self.lock()

        # noinspection PyBroadInspection
        try:
            self._input_years = int(value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def has_station(self):
        return self.climatestation is not None

    #
    # has_climate
    #
    @property
    def has_climate(self):
        if self.climate_spatialmode == ClimateSpatialMode.Multiple:
            return self.sub_par_fns is not None and \
                   self.sub_cli_fns is not None and \
                   self.cli_fn is not None
        else:
            return self.cli_fn is not None

    def parse_inputs(self, kwds):
        self.lock()

        # noinspection PyBroadInspection
        try:
            climate_mode = kwds['climate_mode']
            climate_mode = ClimateMode(int(climate_mode))

            climate_spatialmode = kwds['climate_spatialmode']
            climate_spatialmode = ClimateSpatialMode(int(climate_spatialmode))

            if climate_mode == ClimateMode.SingleStorm:
                climate_spatialmode = ClimateSpatialMode.Single

            input_years = kwds['input_years']
            if isint(input_years):
                input_years = int(input_years)

            if climate_mode in [ClimateMode.Vanilla]:
                assert isint(input_years)
                assert input_years > 0
                assert input_years <= CLIMATE_MAX_YEARS

            if climate_mode in [ClimateMode.ObservedDb, ClimateMode.FutureDb]:
                if climate_mode == ClimateMode.ObservedDb:
                    cli_path = kwds['climate_observed_selection']
                else:
                    cli_path = kwds['climate_future_selection']
                assert _exists(cli_path)
                self._orig_cli_fn = cli_path

            self._climate_mode = climate_mode
            self._climate_spatialmode = climate_spatialmode
            self._input_years = input_years

            self._climate_daily_temp_ds = kwds.get('climate_daily_temp_ds', None)

            if kwds.get('precip_scaling_mode', None) is not None:
                self._precip_scaling_mode = ClimatePrecipScalingMode(int(kwds['precip_scaling_mode']))

            if kwds.get('precip_scale_factor', None) is not None:
                if isfloat(kwds['precip_scale_factor']):
                    self._precip_scale_factor = float(kwds['precip_scale_factor'])
                

                    
            if kwds.get('precip_monthly_scale_factors_7', None) is not None:
                precip_monthly_scale_factors = []
                for i in range(12):
                    precip_monthly_scale_factors.append(
                        float(kwds.get('precip_monthly_scale_factors_%d' % i)))
                self._precip_monthly_scale_factors = precip_monthly_scale_factors

            if kwds.get('precip_scale_reference', None) is not None:
                self._precip_scaling_reference = kwds['precip_scale_reference']

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        # mode 2: observed
        self.set_observed_pars(
            **dict(start_year=kwds['observed_start_year'],
                   end_year=kwds['observed_end_year']))

        # mode 3: future
        self.set_future_pars(
            **dict(start_year=kwds['future_start_year'],
                   end_year=kwds['future_end_year']))

        # mode 4: single storm
        self.set_single_storm_pars(**kwds)

    def set_observed_pars(self, **kwds):
        self.lock()

        # noinspection PyBroadInspection
        try:
            start_year = kwds['start_year']
            end_year = kwds['end_year']

            try:
                start_year = int(start_year)
                end_year = int(end_year)
            except (TypeError, ValueError) as e:
                pass

            if self.climate_mode == ClimateMode.Observed:
                assert isint(start_year)
                assert start_year >= 1980
                #assert start_year <= 2017

                assert isint(end_year)
                assert end_year >= 1980
                #assert end_year <= 2017

                assert end_year >= start_year
                assert end_year - start_year <= CLIMATE_MAX_YEARS
                self._input_years = end_year - start_year + 1

            self._observed_start_year = start_year
            self._observed_end_year = end_year

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_future_pars(self,  **kwds):
        self.lock()

        # noinspection PyBroadInspection
        try:
            start_year = kwds['start_year']
            end_year = kwds['end_year']

            try:
                start_year = int(start_year)
                end_year = int(end_year)
            except (TypeError, ValueError) as e:
                pass

            if self.climate_mode == ClimateMode.Future:
                assert isint(start_year)
                assert start_year >= 2006
                assert start_year <= 2099

                assert isint(end_year)
                assert end_year >= 2006
                assert end_year <= 2099

                assert end_year >= start_year
                assert end_year - start_year <= CLIMATE_MAX_YEARS
                self._input_years = end_year - start_year + 1

            self._future_start_year = start_year
            self._future_end_year = end_year

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_single_storm_pars(self, **kwds):
        self.lock()

        # noinspection PyBroadInspection
        try:
            ss_storm_date = kwds['ss_storm_date']
            ss_design_storm_amount_inches = \
                kwds['ss_design_storm_amount_inches']
            ss_duration_of_storm_in_hours = \
                kwds['ss_duration_of_storm_in_hours']
            ss_max_intensity_inches_per_hour = \
                kwds['ss_max_intensity_inches_per_hour']
            ss_time_to_peak_intensity_pct = \
                kwds['ss_time_to_peak_intensity_pct']

            ss_batch = kwds['ss_batch']

            # Some sort of versioning annoyance. On VM these are strings
            # on wepp1 they are lists
            if isinstance(ss_storm_date, list):
                ss_storm_date = ss_storm_date[0]

            if isinstance(ss_design_storm_amount_inches, list):
                ss_design_storm_amount_inches = ss_design_storm_amount_inches[0]

            if isinstance(ss_duration_of_storm_in_hours, list):
                ss_duration_of_storm_in_hours = ss_duration_of_storm_in_hours[0]

            if isinstance(ss_max_intensity_inches_per_hour, list):
                ss_max_intensity_inches_per_hour = ss_max_intensity_inches_per_hour[0]

            if isinstance(ss_time_to_peak_intensity_pct, list):
                ss_time_to_peak_intensity_pct = ss_time_to_peak_intensity_pct[0]

            try:
                ss_design_storm_amount_inches = \
                    float(ss_design_storm_amount_inches)
                ss_duration_of_storm_in_hours = \
                    float(ss_duration_of_storm_in_hours)
                ss_max_intensity_inches_per_hour = \
                    float(ss_max_intensity_inches_per_hour)
                ss_time_to_peak_intensity_pct = \
                    float(ss_time_to_peak_intensity_pct)
            except (TypeError, ValueError) as e:
                pass

            if self.is_single_storm:
                ss_storm_date = ss_storm_date.split()
                assert len(ss_storm_date) == 3, ss_storm_date
                assert all([isint(token) for token in ss_storm_date])
                ss_storm_date = ' '.join(ss_storm_date)

                assert isfloat(ss_design_storm_amount_inches), ss_design_storm_amount_inches
                assert ss_design_storm_amount_inches > 0

                assert isfloat(ss_duration_of_storm_in_hours), ss_duration_of_storm_in_hours
                assert ss_duration_of_storm_in_hours > 0

                assert isfloat(ss_max_intensity_inches_per_hour), ss_max_intensity_inches_per_hour
                assert ss_max_intensity_inches_per_hour > 0

                assert isfloat(ss_time_to_peak_intensity_pct)
                assert ss_time_to_peak_intensity_pct > 0.0
                assert ss_time_to_peak_intensity_pct < 100.0

            self._ss_storm_date = ss_storm_date
            self._ss_design_storm_amount_inches = \
                ss_design_storm_amount_inches
            self._ss_duration_of_storm_in_hours = \
                ss_duration_of_storm_in_hours
            self._ss_max_intensity_inches_per_hour = \
                ss_max_intensity_inches_per_hour
            self._ss_time_to_peak_intensity_pct = \
                ss_time_to_peak_intensity_pct
            self._ss_batch = ss_batch

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def build(self, verbose=False, attrs=None):
        self.log('Build Climates')
        assert not self.islocked()

        wd = self.wd
        watershed = Watershed.getInstance(wd)
        if not watershed.is_abstracted:
            raise WatershedNotAbstractedError()

        if self.climatestation is None and self.orig_cli_fn is None:
            raise NoClimateStationSelectedError()

        cli_dir = self.cli_dir
        if _exists(cli_dir):
            try:
                shutil.rmtree(cli_dir)
            except:
                pass

        if not _exists(cli_dir):
            os.mkdir(cli_dir)

        climate_mode = self.climate_mode

        if climate_mode == ClimateMode.Undefined:
            raise ClimateModeIsUndefinedError()
        
        # precip scaling mode validation
        
        precip_scaling_mode  = self.precip_scaling_mode
        if precip_scaling_mode == ClimatePrecipScalingMode.Scalar:
            if self.precip_scale_factor is None:
                raise ValueError('precip_scale_factor is None')
            
        elif precip_scaling_mode == ClimatePrecipScalingMode.Spatial:
            if self.precip_scale_factor_map is None:
                raise ValueError('precip_scale_factor_map is None')
            
        elif precip_scaling_mode == ClimatePrecipScalingMode.Monthlies:
            if self.precip_monthly_scale_factors is None:
                raise ValueError('precip_monthly_scale_factors is None')
            
            if len(self.precip_monthly_scale_factors) != 12:
                raise ValueError('precip_monthly_scale_factors length is not 12')
            
            for v in self.precip_monthly_scale_factors:
                if not isfloat(v):
                    raise ValueError('precip_monthly_scale_factors contains non-floats')
                
        elif precip_scaling_mode == ClimatePrecipScalingMode.AnnualMonthlies:
            if self.precip_scaling_reference is None:
                raise ValueError('precip_scaling_reference is None')
            
            if self.precip_scaling_reference not in ['prism', 'daymet', 'gridmet']:
                raise ValueError('precip_scaling_reference is not prism, daymet, or gridmet')
            
            if self.precip_scaling_reference == 'prism':
                if self.observed_start_year < 1981:
                    raise ValueError('prism only available 1981 to present')

        if self.climate_spatialmode == ClimateSpatialMode.MultipleInterpolated:
            # check climate mode is observedprism or gridmetprism
            if self.climate_mode not in [ClimateMode.ObservedPRISM, ClimateMode.GridMetPRISM]:
                raise ValueError('climate_spatialmode is MultipleInterpolated but climate_mode is not ObservedPRISM or GridMetPRISM')

        # vanilla Cligen
        elif climate_mode == ClimateMode.Vanilla:
            self._build_climate_vanilla(verbose=verbose, attrs=attrs)
            if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                self._prism_revision(verbose=verbose)

        # observed
        elif climate_mode == ClimateMode.ObservedPRISM:

            if self.climate_spatialmode == ClimateSpatialMode.MultipleInterpolated:
                # the climate_mode naming is kind of shitty, this doesn't use prism at all
                # but kind of stuck with it for backwards compatibility
                self._build_climate_observed_daymet_multiple(verbose=verbose, attrs=attrs) 
            else:
                self._build_climate_observed_daymet(verbose=verbose, attrs=attrs)
                if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                    self._prism_revision(verbose=verbose)

            if self.daymet_precip_scale_factor is not None:
                self._scale_precip(self.daymet_precip_scale_factor)

            if self.daymet_precip_scale_factor_map is not None:
                self._spatial_scale_precip(self.daymet_precip_scale_factor_map)

        # future
        elif climate_mode == ClimateMode.Future:
            self._build_climate_future(verbose=verbose, attrs=attrs)

        # single storm
        elif climate_mode == ClimateMode.SingleStorm:
            self._build_climate_single_storm(verbose=verbose, attrs=attrs)

        # single storm batch
        elif climate_mode == ClimateMode.SingleStormBatch:
            self._build_climate_single_storm_batch(verbose=verbose, attrs=attrs)

        # PRISM
        elif climate_mode == ClimateMode.PRISM:
            self._build_climate_prism(verbose=verbose, attrs=attrs)
            if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                self._prism_revision(verbose=verbose)

        # NEXRAD
        elif climate_mode == ClimateMode.DepNexrad:
            self._build_climate_depnexrad(verbose=verbose, attrs=attrs)

        elif climate_mode in [ClimateMode.ObservedDb, ClimateMode.FutureDb]:
            assert self.orig_cli_fn is not None
            self._post_defined_climate(verbose=verbose, attrs=attrs)
            if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                self._prism_revision(verbose=verbose)

        # EOBS
        elif climate_mode == ClimateMode.EOBS:
            self._build_climate_mod(mod_function=eobs_mod, verbose=verbose, attrs=attrs)

        elif climate_mode == ClimateMode.AGDC:
            self._build_climate_mod(mod_function=agdc_mod, verbose=verbose, attrs=attrs)

        elif climate_mode == ClimateMode.GridMetPRISM:
            if self.climate_spatialmode == ClimateSpatialMode.MultipleInterpolated:
                self._build_climate_observed_gridmet_multiple(verbose=verbose, attrs=attrs)
            else:
                self._build_climate_observed_gridmet(verbose=verbose, attrs=attrs)
                if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                    self._prism_revision(verbose=verbose)

            if self.gridmet_precip_scale_factor is not None:
                self._scale_precip(self.gridmet_precip_scale_factor)

            if self.gridmet_precip_scale_factor_map is not None:
                self._spatial_scale_precip(self.gridmet_precip_scale_factor_map)


        if self.precip_scaling_mode == ClimatePrecipScalingMode.Scalar:
            assert self.precip_scale_factor is not None
            self._scale_precip(self.precip_scale_factor)
        
        elif self.precip_scaling_mode == ClimatePrecipScalingMode.Spatial:
            assert self.precip_scale_factor_map is not None
            self._spatial_scale_precip(self.precip_scale_factor_map)
        
        elif self.precip_scaling_mode == ClimatePrecipScalingMode.Monthlies:
            assert self.precip_monthly_scale_factors is not None
            self._scale_precip_monthlies(self.precip_monthly_scale_factors, pyo3_cli_p_scale_monthlies)
            
        elif self.precip_scaling_mode == ClimatePrecipScalingMode.AnnualMonthlies:
            assert self.precip_scaling_reference in ['prism', 'daymet', 'gridmet']
            
            ws_lng, ws_lat = watershed.centroid
            start_year, end_year = self.observed_start_year, self.observed_end_year
            
            og_annual_monthlies = pyo3_cli_calculate_annual_monthlies(_join(cli_dir, self.cli_fn))
            if self.precip_scaling_reference == 'prism':
                reference_annual_monthlies = get_prism_p_annual_monthlies(ws_lng, ws_lat, start_year, end_year)
            elif self.precip_scaling_reference == 'daymet':
                reference_annual_monthlies = get_daymet_p_annual_monthlies(ws_lng, ws_lat, start_year, end_year)
            elif self.precip_scaling_reference == 'gridmet':
                reference_annual_monthlies = get_gridmet_p_annual_monthlies(ws_lng, ws_lat, start_year, end_year)
                
            assert og_annual_monthlies.shape == reference_annual_monthlies.shape, (og_annual_monthlies.shape, reference_annual_monthlies.shape)
            
            monthly_scale_factors = []
            for ref, og in zip(reference_annual_monthlies, og_annual_monthlies):
                if og == 0:
                    monthly_scale_factors.append(1.0)
                else:
                    monthly_scale_factors.append(ref / og)
            
            with open(_join(cli_dir, 'reference_annual_monthlies.csv'), 'w') as fp:
                writer = csv.writer(fp)
                # Write header 
                writer.writerow(['Year', 'Month', 'Reference', 'Scale_Factor'])
                # Write data
                year = start_year
                for i, (ref, og, scale) in enumerate(zip(reference_annual_monthlies, og_annual_monthlies, monthly_scale_factors)):
                    month = (i % 12) + 1
                    if i > 0 and i % 12 == 0:
                        year += 1
                    writer.writerow([year, month, ref, scale])
                    
            self._scale_precip_monthlies(monthly_scale_factors, pyo3_cli_p_scale_annual_monthlies)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.build_climate)
        except FileNotFoundError:
            pass

        self.log('Climate Build Successful.')
        self.trigger(TriggerEvents.CLIMATE_BUILD_COMPLETE)
        
# from wepppyo3.climate import calculate_monthlies as pyo3_cli_calculate_monthlies
# from wepppyo3.climate import calculate_p_annual_monthlies as pyo3_cli_calculate_annual_monthlies
# from wepppyo3.climate import rust_cli_p_scale as pyo3_cli_p_scale
# from wepppyo3.climate import rust_cli_p_scale_monthlies as pyo3_cli_p_scale_monthlies
# from wepppyo3.climate import rust_cli_p_scale_annual_monthlies as pyo3_cli_p_scale_annual_monthlies

    def _scale_precip(self, scale_factor):
        """
        scalar scaling of precipitation
        """
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('  running _scale_precip... \n')

            cli_dir = os.path.abspath(self.cli_dir)
            
            pyo3_cli_p_scale(
                _join(cli_dir, self.cli_fn), 
                _join(cli_dir, f'adj_{self.cli_fn}' ),
                scale_factor)
            self.monthlies = pyo3_cli_calculate_monthlies(_join(cli_dir, f'adj_{self.cli_fn}'))
            self.cli_fn = f'adj_{self.cli_fn}'
                    
            if self.sub_cli_fns is not None:
                sub_cli_fns = {}
                for topaz_id, sub_cli_fn in self.sub_cli_fns.items():
                    pyo3_cli_p_scale( 
                        _join(cli_dir, sub_cli_fn), 
                        _join(cli_dir, f'adj_{sub_cli_fn}' ),
                        scale_factor)
                    sub_cli_fns[topaz_id] = f'adj_{sub_cli_fn}'
                    
                self.sub_cli_fns = sub_cli_fns
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _scale_precip_monthlies(self, monthly_scale_factors, scale_func):
        """
        monthly scaling of precipitation
        """
        
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('  running _scale_precip... \n')

            cli_dir = os.path.abspath(self.cli_dir)
            
            scale_func(
                _join(cli_dir, self.cli_fn), 
                _join(cli_dir, f'adj_{self.cli_fn}' ),
                monthly_scale_factors)
            self.monthlies = pyo3_cli_calculate_monthlies(_join(cli_dir, f'adj_{self.cli_fn}'))
            self.cli_fn = f'adj_{self.cli_fn}'
                    
            if self.sub_cli_fns is not None:
                sub_cli_fns = {}
                for topaz_id, sub_cli_fn in self.sub_cli_fns.items():
                    scale_func(
                        _join(cli_dir, sub_cli_fn), 
                        _join(cli_dir, f'adj_{sub_cli_fn' ),
                        monthly_scale_factors)
                    sub_cli_fns[topaz_id] = f'adj_{sub_cli_fn}'
                    
                self.sub_cli_fns = sub_cli_fns
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _spatial_scale_precip(self, scale_factor_map):

        self.lock()

        # noinspection PyBroadInspection
        try:
            cli_dir = os.path.abspath(self.cli_dir)

            assert _exists(scale_factor_map), scale_factor_map
            rdi = RasterDatasetInterpolator(scale_factor_map)
            wd = self.wd

            watershed = Watershed.getInstance(wd)
            ws_lng, ws_lat = watershed.centroid
            scale_factor = rdi.get_location_info(ws_lng, ws_lat)
            if scale_factor is not None:
                if scale_factor > 0:
                    pyo3_cli_p_scale(
                        _join(cli_dir, self.cli_fn), 
                        _join(cli_dir, f'adj_{self.cli_fn}' ),
                        scale_factor)
                    self.monthlies = pyo3_cli_calculate_monthlies(_join(cli_dir, f'adj_{self.cli_fn}'))
                    self.cli_fn = f'adj_{self.cli_fn}'

            if self.sub_cli_fns is not None:
                sub_cli_fns = {}
                for topaz_id, sub_cli_fn in self.sub_cli_fns.items():
                    lng, lat = watershed._subs_summary[topaz_id].centroid.lnglat
                    scale_factor = rdi.get_location_info(lng, lat)
                    if scale_factor is not None:
                        if scale_factor > 0:
                            pyo3_cli_p_scale( 
                                _join(cli_dir, sub_cli_fn), 
                                _join(cli_dir, f'adj_{sub_cli_fn}' ),
                                scale_factor)
                            sub_cli_fns[topaz_id] = f'adj_{sub_cli_fn}'
                    
                self.sub_cli_fns = sub_cli_fns

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_depnexrad(self, verbose=False, attrs=None):
        self.log('  running _build_climate_depnexrad... \n')

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)

            cli_dir = os.path.abspath(self.cli_dir)
            watershed = Watershed.getInstance(self.wd)

            # build a climate for the channels.
            lng, lat = watershed.centroid

            self.par_fn = '.par'
            self.cli_fn = cli_fn = f'{lng:.02f}x{lat:.02f}.cli'
            url = f'https://mesonet-dep.agron.iastate.edu/dl/climatefile.py?lon={lng:.02f}&lat={lat:.02f}'

            download_file(url, _join(cli_dir, cli_fn))

            # clip climate file
            cli = ClimateFile(_join(cli_dir, cli_fn))

            start_year = int(self.observed_start_year)
            end_year = int(self.observed_end_year)
            assert end_year >= start_year, (start_year, end_year)
            cli.clip(date(start_year, 1, 1), date(end_year, 12, 31))
            cli.write(_join(cli_dir, cli_fn))

            url = f'https://mesonet-dep.agron.iastate.edu/dl/climatefile.py?lon={lng:.02f}&lat={lat:.02f}&intensity=10,30,60'
            download_file(url, _join(cli_dir, f'{lng:.02f}x{lat:.02f}.intensities.csv'))

            self.log('Calculating monthlies...')
            cli = ClimateFile(_join(cli_dir, cli_fn))

            if self.climate_daily_temp_ds == 'prism':
                from wepppy.climates.prism.daily_client import retrieve_historical_timeseries
                df = retrieve_historical_timeseries(lng=lng, lat=lat, start_year=start_year, end_year=end_year)

                dates = df.index
                cli.replace_var('tmax', dates, df['tmax(degc)'])
                cli.replace_var('tmin', dates, df['tmin(degc)'])
                cli.replace_var('tdew', dates, df['tdmean(degc)'])

                self.cli_fn = cli_fn = cli_fn[:-4] + '.prism.cli'
                cli.write(_join(cli_dir, cli_fn))

            if self.climate_daily_temp_ds == 'gridmet':
                from wepppy.all_your_base import c_to_f
                df = gridmet_retrieve_historical_timeseries(lng, lat, start_year, end_year)

                dates = df.index
                cli.replace_var('tmax', dates, df['tmmx(degc)'])
                cli.replace_var('tmin', dates, df['tmmn(degc)'])
                cli.replace_var('rad', dates, df['srad(l/day)'])
                cli.replace_var('tdew', dates, df['tdew(degc)'])
                cli.replace_var('w-vl', dates, df['vs(m/s)'])
                cli.replace_var('w-dir', dates, df['th(DegreesClockwisefromnorth)'])

                self.cli_fn = cli_fn = cli_fn[:-4] + '.gridmet.cli'
                cli.write(_join(cli_dir, cli_fn))

            if self.climate_daily_temp_ds == 'daymet':
                from wepppy.all_your_base import c_to_f
                df = daymet_retrieve_historical_timeseries(lng, lat, start_year, end_year)

                dates = df.index
                cli.replace_var('tmax', dates, df['tmax(degc)'])
                cli.replace_var('tmin', dates, df['tmin(degc)'])
                cli.replace_var('rad', dates, df['srad(l/day)'])
                cli.replace_var('tdew', dates, df['tdew(degc)'])

                self.cli_fn = cli_fn = cli_fn[:-4] + '.daymet.cli'
                cli.write(_join(cli_dir, cli_fn))


            self._input_years = cli.input_years
            self.monthlies = cli.calc_monthlies()
            self.log_done()

            if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                self.log('  building climates for hillslopes... \n')

                # build a climate for each subcatchment
                sub_par_fns = {}
                sub_cli_fns = {}
                for topaz_id, ss in watershed._subs_summary.items():
                    self.log('submitting climate build for {}... '.format(topaz_id))

                    lng, lat = ss.centroid.lnglat

                    cli_fn = f'{lng:.02f}x{lat:.02f}.cli'
                    url = f'https://mesonet-dep.agron.iastate.edu/dl/climatefile.py?lon={lng:.02f}&lat={lat:.02f}'

                    if not _exists(_join(cli_dir, cli_fn)):
                        download_file(url, _join(cli_dir, cli_fn))

                        # clip climate file
                        cli = ClimateFile(_join(cli_dir, cli_fn))
                        cli.clip(date(start_year, 1, 1), date(end_year, 12, 31))
                        cli.write(_join(cli_dir, cli_fn))

 #                       breakpoint_file_fix(_join(cli_dir, cli_fn))

                    sub_par_fns[topaz_id] = '.par'
                    sub_cli_fns[topaz_id] = cli_fn

                    self.log_done()

                self.log_done()

                self.sub_par_fns = sub_par_fns
                self.sub_cli_fns = sub_cli_fns


            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_prism(self, verbose=False, attrs=None):
        self.log('  running _build_climate_prism... \n')

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)

            # cligen can accept a 5 digit random number seed
            # we want to specify this to ensure that the precipitation
            # events are synchronized across the subcatchments
            if self._cligen_seed is None:
                self._cligen_seed = random.randint(0, 99999)
                self.dump()

            randseed = self._cligen_seed

            cli_dir = os.path.abspath(self.cli_dir)
            watershed = Watershed.getInstance(self.wd)

            climatestation = self.climatestation
            years = self._input_years

            # build a climate for the channels.
            lng, lat = watershed.centroid

            self.par_fn = '{}.par'.format(climatestation)
            self.cli_fn = '{}.cli'.format(climatestation)

            self.monthlies = prism_mod(par=climatestation,
                                     years=years, lng=lng, lat=lat, wd=cli_dir,
                                     logger=self, nwds_method='')
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise


    def _prism_revision(self, verbose=False):

        wd = self.wd
        cli_dir = self.cli_dir

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('  running _prism_revision... ')
            wd = self.wd
            climatestation = self.climatestation
            years = self._input_years

            monthlies = self.monthlies
            par_fn = self.par_fn
            cli_fn = self.cli_fn
            cli_dir = self.cli_dir
            cli_path = self.cli_path

            _map = Ron.getInstance(self.wd).map

            ppt_fn = _join(cli_dir, 'ppt.tif')
            tmin_fn = _join(cli_dir, 'tmin.tif')
            tmax_fn = _join(cli_dir, 'tmax.tif')

            wmesque_retrieve('prism/ppt', _map.extent, ppt_fn, _map.cellsize, resample='cubic')
            ppt_data, _transform, _proj = read_raster(ppt_fn)
                    
            if np.any(ppt_data < 0):
                self.log('    prism/ppt contains < values do to cubic resampling, reacquiring with bilinear resampling... ')
                wmesque_retrieve('prism/ppt', _map.extent, ppt_fn, _map.cellsize, resample='bilinear')
                self.done()
            
            wmesque_retrieve('prism/ppt', _map.extent, ppt_fn, _map.cellsize, resample='bilinear')
            wmesque_retrieve('prism/tmin', _map.extent, _join(cli_dir, 'tmin.tif'), _map.cellsize, resample='cubic')
            wmesque_retrieve('prism/tmax', _map.extent, _join(cli_dir, 'tmax.tif'), _map.cellsize, resample='cubic')

            watershed = Watershed.getInstance(wd)
            ws_lng, ws_lat = watershed.centroid
            ws_ppts = get_monthlies(ppt_fn, ws_lng, ws_lat)
            ws_tmins = get_monthlies(tmin_fn, ws_lng, ws_lat)
            ws_tmaxs = get_monthlies(tmax_fn, ws_lng, ws_lat)


            self.log('  building climates for hillslopes... \n')


            cli = ClimateFile(cli_path)

            pool = multiprocessing.Pool(NCPU)
            jobs = []

            def callback(res):
                self.log(f'_prism_revision() -> {res}')
                self.log_done()

            # build a climate for each subcatchment
            sub_par_fns = {}
            sub_cli_fns = {}
            for topaz_id, ss in watershed._subs_summary.items():
                self.log('submitting climate build for {} to worker pool... '.format(topaz_id))

                hill_lng, hill_lat = ss.centroid.lnglat
                suffix = f'_{topaz_id}'
                new_cli_fn = f'{suffix}.cli'
                args = (cli, ws_ppts, ws_tmaxs, ws_tmins,
                        _join(cli_dir, 'ppt.tif'),
                        _join(cli_dir, 'tmin.tif'),
                        _join(cli_dir, 'tmax.tif'),
                        hill_lng, hill_lat, _join(cli_dir, new_cli_fn))

                result = pool.apply_async(cli_revision, args=args, callback=callback)
                jobs.append(result)

                sub_par_fns[topaz_id] = '.par'
                sub_cli_fns[topaz_id] = new_cli_fn

                self.log_done()

            pool.close()
            pool.join()

            self.log_done()

            self.sub_par_fns = sub_par_fns
            self.sub_cli_fns = sub_cli_fns

            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise


    def _post_defined_climate(self, verbose=False, attrs=None):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)

            self.log('Copying original climate file...')
            orig_cli_fn = self.orig_cli_fn
            cli_dir = self.cli_dir
            assert orig_cli_fn is not None
            assert _exists(orig_cli_fn)

            cli_dir = os.path.abspath(self.cli_dir)
            watershed = Watershed.getInstance(self.wd)

            cli_fn = _split(orig_cli_fn)[1]
            cli_path = _join(cli_dir, cli_fn)
            try:
                copyfile(orig_cli_fn, cli_path)
            except shutil.SameFileError:
                pass

            self.cli_fn = cli_fn
            assert _exists(cli_path)
            self.log_done()

            self.sub_par_fns = None
            self.sub_cli_fns = None

            self.log('Calculating monthlies...')
            cli = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = cli.calc_monthlies()
            self.log_done()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise



    def _build_climate_mod(self, mod_function, verbose=False, attrs=None):
        self.log('  running _build_climate_mod{}... \n'.format(mod_function.__name__))

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)

            # cligen can accept a 5 digit random number seed
            # we want to specify this to ensure that the precipitation
            # events are synchronized across the subcatchments
            if self._cligen_seed is None:
                self._cligen_seed = random.randint(0, 99999)
                self.dump()

            randseed = self._cligen_seed

            cli_dir = os.path.abspath(self.cli_dir)
            watershed = Watershed.getInstance(self.wd)

            climatestation = self.climatestation
            years = self._input_years

            # build a climate for the channels.
            lng, lat = watershed.centroid

            self.par_fn = '{}.par'.format(climatestation)
            self.cli_fn = '{}.cli'.format(climatestation)

            monthlies = mod_function(par=climatestation,
                                     years=years, lng=lng, lat=lat, wd=cli_dir,
                                     logger=self, nwds_method='')
            self.monthlies = monthlies

            if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                self.log('  building climates for hillslopes... \n')

                pool = multiprocessing.Pool(NCPU)
                jobs = []

                def callback(res):
                    ppts = ['%.2f' % p  for p in  res['ppts']]
                    self.log('job completed.  ppts: {} '.format(', '.join(ppts)))
                    self.log_done()

                # build a climate for each subcatchment
                sub_par_fns = {}
                sub_cli_fns = {}
                for topaz_id, ss in watershed._subs_summary.items():
                    self.log('submitting climate build for {} to worker pool... '.format(topaz_id))

                    lng, lat = ss.centroid.lnglat
                    suffix = f'_{topaz_id}'

                    kwds = dict(par=climatestation,
                                 years=years, lng=lng, lat=lat, wd=cli_dir,
                                 suffix=suffix, logger=None, nwds_method='')

                    sub_par_fns[topaz_id] = '{}{}.par'.format(climatestation, suffix)
                    sub_cli_fns[topaz_id] = '{}{}.cli'.format(climatestation, suffix)

                    jobs.append(pool.apply_async(mod_function, kwds=kwds, callback=callback))

                    self.log_done()

                [j.wait() for j in jobs]

                self.log_done()

                self.sub_par_fns = sub_par_fns
                self.sub_cli_fns = sub_cli_fns

            self.log('  finalizing climate build... ')
            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

    def set_user_defined_cli(self, cli_fn, verbose=False):
        self.lock()

        # noinspection PyBroadInspection
        try:

            self.log('  running set_userdefined_cli... ')
            self._orig_cli_fn = _join(self.cli_dir, cli_fn)
#            cli_path = self.cli_path
            cli = ClimateFile(self.orig_cli_fn)

            if cli.is_single_storm:
                self._climate_mode = ClimateMode.UserDefinedSingleStorm

            self._input_years = cli.input_years
            self.monthlies = cli.calc_monthlies()
            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

        self._post_defined_climate(verbose=verbose)

        if self.climate_spatialmode == ClimateSpatialMode.Multiple:
            self._prism_revision(verbose=verbose)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.build_climate)
        except FileNotFoundError:
            pass

    def _build_climate_vanilla(self, verbose=False, attrs=None):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)

            self.log('  running _build_climate_vanilla... ')
            years = self._input_years

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            cli_dir = self.cli_dir

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)
            cli_fn = cligen.run_multiple_year(years)

            climate = ClimateFile(_join(cli_dir, cli_fn))
            monthlies = climate.calc_monthlies()

            self.monthlies = monthlies
            self.par_fn = par_fn
            self.cli_fn = cli_fn
            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_observed_daymet(self, verbose=False, attrs=None):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)
            self.log('  running _build_climate_observed_daymet')

            watershed = Watershed.getInstance(self.wd)
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._observed_start_year, self._observed_end_year
            assert end_year <= self.daymet_last_available_year, end_year

            self._input_years = end_year - start_year + 1

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            ron = Ron.getInstance(self.wd)
            cli_fn = 'wepp.cli'
            prn_fn = 'ws.prn'
            self.log('  building {}... '.format(cli_fn))

            build_observed_daymet(cligen, ws_lng, ws_lat, start_year, end_year, cli_dir, prn_fn, cli_fn)

            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

            self.log_done()

            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise



    def _build_climate_observed_gridmet_multiple(self, verbose=False, attrs=None):
        from wepppy.climates.gridmet.client import (
            GridMetVariable,
            retrieve_nc,
            read_nc,
            interpolate_daily_timeseries_for_location,
            read_nc_longlat
        )

        import xarray as xr

        measures = [
            GridMetVariable.Precipitation,
            GridMetVariable.MinimumTemperature,
            GridMetVariable.MaximumTemperature,
            GridMetVariable.SurfaceRadiation,
            GridMetVariable.WindDirection,
            GridMetVariable.WindSpeed,
            GridMetVariable.MinimumRelativeHumidity,
            GridMetVariable.MaximumRelativeHumidity
        ]

        interpolation_spec = {
            'pr(mm)': {
                'method': 'cubic',
                'a_min': 0.0, # clip to 0.0
            },
            'tmmx(degc)':{
                'method': 'cubic',
            },
            'tmmn(degc)':{
                'method': 'cubic',
            },
            'rmin(%)':{
                'method': 'linear',
            },
            'rmax(%)':{
                'method': 'linear',
            },
            'srad(Wm-2)':{
                'method': 'linear',
                'a_min': 0.0, # clip to 0.0
            },
            'vs(m/s)':{
                'method': 'linear',
                'a_min': 0.0, # clip to 0.0
            },
            'th(DegreesClockwisefromnorth)':{
                'method': 'nearest'
            }
        }

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)
            self.log('  running _build_climate_observed_gridmet_multiple')

            ron = Ron.getInstance(self.wd)
            watershed = Watershed.getInstance(self.wd)
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._observed_start_year, self._observed_end_year

            self._input_years = end_year - start_year + 1

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            hillslope_locations = {'ws': {'longitude': ws_lng, 'latitude': ws_lat}}
            for topaz_id, ss in watershed._subs_summary.items():
                _lng, _lat = ss.centroid.lnglat
                hillslope_locations[topaz_id] = {'longitude': _lng, 'latitude': _lat}

            extent = ron.extent
            cellsize = 0.04166601298087771
            pad = cellsize * 2
            extent = [extent[0] - pad, extent[1] - pad, extent[2] + pad, extent[3] + pad]
            dates = pd.date_range(f'{start_year}-01-01', f'{end_year}-12-31')
            ndates = len(dates)

            # bbox = west, north, east, south
            bbox = [extent[0], extent[3], extent[2], extent[1]]

            with ProcessPoolExecutor(max_workers=12) as executor:
                futures = []
                for measure in measures:
                    for year in range(start_year, end_year + 1):
                        futures.append(
                            executor.submit(
                                retrieve_nc, measure, bbox, year, cli_dir, _id=f'{measure}_{year}'))

                try:
                    for future in as_completed(futures):
                        # This call raises an exception if the task failed.
                        future.result()
                except Exception as e:
                    # Cancel all pending futures.
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    # If using Python 3.9+, you can force cancellation of pending futures:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise


            # load into raw_data
            raw_data = {}
            columns = {}

            for measure in measures:
                for year in range(start_year, end_year + 1):
                    ts, abbrv, units = read_nc(_join(cli_dir, f'{measure}_{year}.nc'), measure)
                    ts = ts.transpose(2, 1, 0) # reorder dimensions to longs, lats, dates
                    ts_len = ts.shape[2]

                    if year == start_year:
                        ncols = ts.shape[0]
                        nrows = ts.shape[1]
                        raw_data[measure] = np.zeros((ncols, nrows, ndates))
                        indx = 0

                        columns[measure] = f'{abbrv}({units})'

                    raw_data[measure][:, :, indx: indx+ts_len] = ts
                    indx += ts_len
                    
            raw_data = {columns[k]: v for k, v in raw_data.items()}

            longitudes, latitudes = read_nc_longlat(_join(cli_dir, f'{measure}_{year}.nc'))

            # need to reverse latitudes and raw_data latitudes
            # would be good to revise wepppyo3 interpolator so this isn't neccessary
            latitudes = latitudes[::-1]
            raw_data = {k: v[:, ::-1, :] for k, v in raw_data.items()}

            with ProcessPoolExecutor(max_workers=28) as executor:
                futures = []

                for topaz_id, loc in hillslope_locations.items():
                    self.log(f'  interpolating topaz_id {topaz_id}...\n')
                        
                    # this interpolates the 3d grid using rust pyo3 and builds prn to be used by cligen
                    futures.append(
                        executor.submit(interpolate_daily_timeseries_for_location, 
                                        topaz_id, loc, dates, 
                                        longitudes, latitudes, raw_data, interpolation_spec, 
                                        self.cli_dir, start_year, end_year))
                    
                try:
                    for future in as_completed(futures):
                        # This call raises an exception if the task failed.
                        topaz_id = future.result()
                        self.log(f'  interpolated {topaz_id} done.\n')
                except Exception as e:
                    # Cancel all pending futures.
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    # If using Python 3.9+, you can force cancellation of pending futures:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise

            sub_par_fns = {}
            sub_cli_fns = {}
            with ProcessPoolExecutor(max_workers=NCPU) as executor:
                futures = []
                for topaz_id, ss in watershed._subs_summary.items():

                    _lng, _lat = ss.centroid.lnglat
                    _prn_fn = f'gridmet_observed_{topaz_id}_{start_year}-{end_year}.prn'
                    _cli_fn = f'gridmet_observed_{topaz_id}_{start_year}-{end_year}.cli'
                    
                    self.log(f'submitting climate build for {topaz_id} ...\n')

                    futures.append(
                        executor.submit(
                            build_observed_gridmet_interpolated, 
                            cligen, topaz_id, _lng, _lat, start_year, end_year, cli_dir, _cli_fn, _prn_fn))
                
                    sub_par_fns[topaz_id] = _prn_fn
                    sub_cli_fns[topaz_id] = _cli_fn

                topaz_id = 'ws'
                prn_fn = f'gridmet_observed_{topaz_id}_{start_year}-{end_year}.prn'
                cli_fn = 'wepp.cli'
                futures.append(
                    executor.submit(
                        build_observed_gridmet_interpolated, 
                        cligen, topaz_id, ws_lng, ws_lat, start_year, end_year, cli_dir, cli_fn, prn_fn))

                try:
                    for future in as_completed(futures):
                        # This call raises an exception if the task failed.
                        topaz_id = future.result()
                        self.log(f'  climate for {topaz_id} done.\n')
                except Exception as e:
                    # Cancel all pending futures.
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    # If using Python 3.9+, you can force cancellation of pending futures:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
                
            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

            self.sub_par_fns = sub_par_fns
            self.sub_cli_fns = sub_cli_fns
            self.log_done()

            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise


    def _build_climate_observed_daymet_multiple(self, verbose=False, attrs=None):
        from wepppy.climates.daymet.daily_interpolation import (
            identify_pixel_coords
        )
        from wepppy.climates.daymet.daymet_singlelocation_client import (
            interpolate_daily_timeseries
        )

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)
            self.log('  running _build_climate_observed_daymet_multiple')

            watershed = Watershed.getInstance(self.wd)
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._observed_start_year, self._observed_end_year
            assert end_year <= self.daymet_last_available_year, end_year

            self._input_years = end_year - start_year + 1

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            hillslope_locations = {'ws': {'longitude': ws_lng, 'latitude': ws_lat}}
            for topaz_id, ss in watershed._subs_summary.items():
                _lng, _lat = ss.centroid.lnglat
                hillslope_locations[topaz_id] = {'longitude': _lng, 'latitude': _lat}

            hillslope_locations = identify_pixel_coords(hillslope_locations, daymet_version=self.daymet_version)

            self.log('  interpolating daymet grids...\n')

            # this retrieves concurrently
            interpolate_daily_timeseries(hillslope_locations, 
                                         self.observed_start_year, self.observed_end_year,
                                         output_dir=cli_dir,
                                         output_type='prn parquet',
                                         status_channel=self._status_channel)


            self.log('  fetching gridmet wind...\n')
            wind_df = gridmet_retrieve_historical_wind(ws_lng, ws_lat, start_year, end_year)

            sub_par_fns = {}
            sub_cli_fns = {}
            with ProcessPoolExecutor(max_workers=40) as executor:
                futures = []
                for topaz_id, ss in watershed._subs_summary.items():

                    _lng, _lat = ss.centroid.lnglat
                    _prn_fn = f'daymet_observed_{topaz_id}_{start_year}-{end_year}.prn'
                    _cli_fn = f'daymet_observed_{topaz_id}_{start_year}-{end_year}.cli'
                    
                    self.log(f'submitting climate build for {topaz_id} ...\n')

                    futures.append(
                        executor.submit(
                            build_observed_daymet_interpolated, 
                            cligen, topaz_id, _lng, _lat, start_year, end_year, cli_dir, _cli_fn, _prn_fn, 
                            wind_vs=wind_df['vs(m/s)'], wind_dir=wind_df['th(DegreesClockwisefromnorth)']))
                
                    sub_par_fns[topaz_id] = _prn_fn
                    sub_cli_fns[topaz_id] = _cli_fn

                topaz_id = 'ws'
                prn_fn = f'daymet_observed_{topaz_id}_{start_year}-{end_year}.prn'
                cli_fn = 'wepp.cli'
                futures.append(
                    executor.submit(
                        build_observed_daymet_interpolated, 
                        cligen, topaz_id, ws_lng, ws_lat, start_year, end_year, cli_dir, cli_fn, prn_fn, 
                        wind_vs=wind_df['vs(m/s)'], wind_dir=wind_df['th(DegreesClockwisefromnorth)']))

                try:
                    for future in as_completed(futures):
                        # This call raises an exception if the task failed.
                        topaz_id = future.result()
                        self.log(f'  climate for {topaz_id} done.\n')
                except Exception as e:
                    # Cancel all pending futures.
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    # If using Python 3.9+, you can force cancellation of pending futures:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise

            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

            self.sub_par_fns = sub_par_fns
            self.sub_cli_fns = sub_cli_fns
            self.log_done()

            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_observed_gridmet(self, verbose=False, attrs=None):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)
            self.log('  running _build_climate_observed_gridmet')

            watershed = Watershed.getInstance(self.wd)
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._observed_start_year, self._observed_end_year

            self._input_years = end_year - start_year + 1

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            ron = Ron.getInstance(self.wd)
            cli_fn = 'wepp.cli'
            prn_fn = 'ws.prn'
            self.log('  building {}... '.format(cli_fn))

            build_observed_gridmet(cligen, ws_lng, ws_lat, start_year, end_year, cli_dir, prn_fn, cli_fn)

            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

            self.log_done()

            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise


    def _build_climate_future(self, verbose=False, attrs=None):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)
            self.log('  running _build_climate_future')

            watershed = Watershed.getInstance(self.wd)
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._future_start_year, self._future_end_year

            self._input_years = end_year - start_year + 1

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            ron = Ron.getInstance(self.wd)
            cli_fn = 'wepp.cli'
            prn_fn = 'ws.prn'
            self.log('  building {}... '.format(cli_fn))

            build_future(cligen, ws_lng, ws_lat, start_year, end_year, cli_dir, prn_fn, cli_fn)

            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

            self.log_done()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_single_storm_batch(self, verbose=False, attrs=None):
        """
        single storm
        """

        climatestation = self.climatestation

        ss_batch = self.ss_batch.split('\n')
        assert len(ss_batch) > 0, ss_batch

        specs = {}
        for L in [spec.split() for spec in ss_batch]:
            if len(L) == 0:
                continue

            assert len(L) == 7, L
            mo, da, yr, prcp, duration, tp, ip = L
            key ='ss_' + '_'.join(v.strip() for v in L)
            specs[key] = dict(ss_storm_date=f'{mo} {da} {yr}',
                              ss_design_storm_amount_inches=float(prcp),
                              ss_duration_of_storm_in_hours=float(duration),
                              ss_time_to_peak_intensity_pct=float(tp),
                              ss_max_intensity_inches_per_hour=float(tp))

        self.lock()
        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)

            self.log('  running _build_climate_single_storm... ')

            storms = []
            for i, (key, spec) in enumerate(specs.items()):

                result = cc.selected_single_storm(
                    climatestation,
                    spec['ss_storm_date'],
                    spec['ss_design_storm_amount_inches'],
                    spec['ss_duration_of_storm_in_hours'],
                    spec['ss_time_to_peak_intensity_pct'],
                    spec['ss_max_intensity_inches_per_hour'],
                    version=self.cligen_db
                )

                par_fn, cli_fn, monthlies = cc.unpack_json_result(
                    result,
                    key,
                    self.cli_dir
                )
                storms.append(dict(ss_batch_id=i+1, ss_batch_key=key, spec=spec, par_fn=par_fn, cli_fn=cli_fn))

            if len(storms) > 20:
                raise ValueError('Only 20 single storms can be ran in batch mode')

            self._ss_batch_storms = storms
            self.monthlies = monthlies
            self.par_fn = par_fn
            self.cli_fn = cli_fn
            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_single_storm(self, verbose=False, attrs=None):
        """
        single storm
        """
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.set_attrs(attrs)

            self.log('  running _build_climate_single_storm... ')
            climatestation = self.climatestation

            result = cc.selected_single_storm(
                climatestation,
                self._ss_storm_date,
                self._ss_design_storm_amount_inches,
                self._ss_duration_of_storm_in_hours,
                self._ss_time_to_peak_intensity_pct,
                self._ss_max_intensity_inches_per_hour,
                version=self.cligen_db
            )

            par_fn, cli_fn, monthlies = cc.unpack_json_result(
                result,
                climatestation,
                self.cli_dir
            )

            self.monthlies = monthlies
            self.par_fn = par_fn
            self.cli_fn = cli_fn
            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

    def sub_summary(self, topaz_id):
        if not self.has_climate:
            return None

        if self._climate_spatialmode == ClimateSpatialMode.Multiple:
            return dict(cli_fn=self.sub_cli_fns[str(topaz_id)],
                        par_fn=self.sub_par_fns[str(topaz_id)])
        else:
            return dict(cli_fn=self.cli_fn, par_fn=self.par_fn)

    def chn_summary(self, topaz_id):
        if not is_channel(topaz_id):
            raise ValueError('topaz_id is not channel')

        if not self.has_climate:
            return None

        return dict(cli_fn=self.cli_fn, par_fn=self.par_fn)

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id):
        if not self.has_climate:
            raise IndexError

        if self._climate_spatialmode == ClimateSpatialMode.Multiple:
            translator = Watershed.getInstance(self.wd).translator_factory()
            topaz_id = str(translator.top(wepp=int(wepp_id)))

            if topaz_id in self.sub_cli_fns:
                cli_fn = self.sub_cli_fns[topaz_id]
                par_fn = self.sub_par_fns[topaz_id]
                return dict(cli_fn=cli_fn, par_fn=par_fn)

        else:
            return dict(cli_fn=self.cli_fn,
                        par_fn=self.par_fn)

        raise IndexError
