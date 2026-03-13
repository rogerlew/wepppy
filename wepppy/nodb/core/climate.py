# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Climate data management and WEPP climate file generation.

This module provides the Climate NoDb controller for managing climate data
acquisition, processing, and WEPP .cli file generation. It supports multiple
climate data sources including CLIGEN, Daymet, GridMET, PRISM, and observed data.

Key Components:
    Climate: NoDb controller for climate data management
    ClimateMode: Enum defining climate data sources
    ClimateSpatialMode: Enum for spatial climate data handling
    ClimateStationMode: Enum for station selection methods
    ClimateSummary: Data structure for climate statistics

Climate Data Sources:
    - CLIGEN: Statistical weather generator
    - OBSERVED: Historical weather station data
    - DAYMET: Gridded daily meteorology (1 km)
    - GRIDMET: Gridded meteorology (4 km)
    - PRISM: Parameter-elevation Regressions on Independent Slopes Model
    - FUTURE: Climate projections (RCP scenarios)

Example:
    >>> from wepppy.nodb.core import Climate, ClimateMode
    >>> climate = Climate.getInstance('/wc1/runs/my-run')
    >>> climate.mode = ClimateMode.CLIGEN
    >>> climate.download_climate_data('14826')
    >>> climate.build_climate_files()

See Also:
    - wepppy.climates.cligen: CLIGEN climate generator
    - wepppy.climates.daymet: Daymet data client
    - wepppy.climates.gridmet: GridMET data client
    - wepppy.climates.prism: PRISM data client

Note:
    Climate files are generated per hillslope as p{wepp_id}.cli
    in the {wd}/wepp/runs/ directory.
"""

# standard library
import csv
import time
from pathlib import Path
import os
import inspect
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from typing import Optional, Dict, List, Tuple, Any, Union

from functools import partial

from wepppy.all_your_base.geo import read_raster

from datetime import datetime, date

from subprocess import Popen, PIPE

from concurrent.futures import (
    ThreadPoolExecutor, wait, FIRST_COMPLETED, ProcessPoolExecutor
)

import json
from enum import IntEnum
import random
from glob import glob

import shutil

from shutil import copyfile
import pandas as pd

import rasterio
import requests


from wepppy.climates.downscaled_nmme_client import retrieve_rcp85_timeseries

from wepppy.climates.prism import prism_mod
from wepppy.climates.gridmet import retrieve_historical_timeseries as gridmet_retrieve_historical_timeseries
from wepppy.climates.gridmet import retrieve_historical_wind as gridmet_retrieve_historical_wind
from wepppy.climates.gridmet import retrieve_historical_precip as gridmet_retrieve_historical_precip
from wepppy.climates.prism.daily_client import retrieve_historical_timeseries as prism_retrieve_historical_timeseries
from wepppy.eu.climates.eobs import eobs_mod
from wepppy.au.climates.agdc import agdc_mod
from wepppy.climates.cligen import (
    CligenStationsManager, 
    ClimateFile, 
    Cligen,
    df_to_prn,
)
from wepppy.climates.cligen.single_storm import (
    SingleStormResult,
    build_single_storm_cli,
)
from wepppy.all_your_base import isint, isfloat, NCPU
from wepppy.all_your_base.stats import weibull_series
from wepppy.all_your_base.geo import RasterDatasetInterpolator
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.query_engine.activate import update_catalog_entry
from wepppy.topo.watershed_abstraction.support import is_channel
import numpy as np

from copy import deepcopy

import pyproj
from pyproj import Proj

from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.locales.climate_catalog import DAYMET_LAST_AVAILABLE_YEAR
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

import wepppyo3
from wepppyo3.climate import cli_revision as pyo3_cli_revision
from wepppyo3.climate import calculate_monthlies as pyo3_cli_calculate_monthlies
from wepppyo3.climate import calculate_p_annual_monthlies as pyo3_cli_calculate_annual_monthlies
from wepppyo3.climate import rust_cli_p_scale as pyo3_cli_p_scale
from wepppyo3.climate import rust_cli_p_scale_monthlies as pyo3_cli_p_scale_monthlies
from wepppyo3.climate import rust_cli_p_scale_annual_monthlies as pyo3_cli_p_scale_annual_monthlies

from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService
from wepppy.nodb.core.climate_build_router import ClimateBuildRouter
from wepppy.nodb.core.climate_gridmet_multiple_build_service import (
    ClimateGridmetMultipleBuildService,
)
from wepppy.nodb.core.climate_input_parser import ClimateInputParsingService
from wepppy.nodb.core.climate_mode_build_services import ClimateModeBuildServices
from wepppy.nodb.core.climate_scaling_service import ClimateScalingService
from wepppy.nodb.core.climate_station_catalog_service import ClimateStationCatalogService
from wepppy.nodb.core.climate_user_defined_station_meta_service import (
    ClimateUserDefinedStationMetaService,
)
from wepppy.nodb.core.climate_build_helpers import (
    breakpoint_file_fix,
    build_future,
    build_observed_daymet,
    build_observed_daymet_interpolated,
    build_observed_gridmet,
    build_observed_gridmet_interpolated,
    build_observed_prism,
    build_observed_snotel,
    cli_revision,
    daymet_pixel_center,
    download_file,
    get_daymet_p_annual_monthlies,
    get_gridmet_p_annual_monthlies,
    get_monthlies,
    get_prism_p_annual_monthlies,
    gridmet_pixel_center,
    lng_lat_to_pixel_center,
    nexrad_pixel_center,
    prism4k_pixel_center,
    run_depnexrad_build,
    run_mod_build,
    run_observed_daymet_multiple_build,
    run_prism_revision,
)

__all__ = [
    'lng_lat_to_pixel_center',
    'daymet_pixel_center',
    'gridmet_pixel_center',
    'prism4k_pixel_center',
    'nexrad_pixel_center',
    'download_file',
    'breakpoint_file_fix',
    'CLIMATE_MAX_YEARS',
    'ClimateSummary',
    'NoClimateStationSelectedError',
    'ClimateModeIsUndefinedError',
    'ClimateNoDbLockedException',
    'ClimateStationMode',
    'ClimateMode',
    'ClimateSpatialMode',
    'ClimatePrecipScalingMode',
    'get_prism_p_annual_monthlies',
    'build_observed_prism',
    'get_daymet_p_annual_monthlies',
    'build_observed_daymet',
    'build_observed_daymet_interpolated',
    'build_observed_snotel',
    'get_gridmet_p_annual_monthlies',
    'build_observed_gridmet',
    'build_observed_gridmet_interpolated',
    'build_future',
    'get_monthlies',
    'cli_revision',
    'Climate',
]


CLIMATE_MAX_YEARS = 1000

if NCPU > 24:
    NCPU = 24

_CLIMATE_INPUT_PARSER = ClimateInputParsingService()
_CLIMATE_MODE_BUILD_SERVICES = ClimateModeBuildServices()
_CLIMATE_SCALING_SERVICE = ClimateScalingService()
_CLIMATE_ARTIFACT_EXPORT_SERVICE = ClimateArtifactExportService()
_CLIMATE_STATION_CATALOG_SERVICE = ClimateStationCatalogService()
_CLIMATE_USER_DEFINED_STATION_META_SERVICE = ClimateUserDefinedStationMetaService()
_CLIMATE_GRIDMET_MULTIPLE_BUILD_SERVICE = ClimateGridmetMultipleBuildService()
_CLIMATE_BUILD_ROUTER = ClimateBuildRouter(
    mode_build_services=_CLIMATE_MODE_BUILD_SERVICES,
    scaling_service=_CLIMATE_SCALING_SERVICE,
    artifact_export_service=_CLIMATE_ARTIFACT_EXPORT_SERVICE,
)

class ClimateSummary(object):
    def __init__(self) -> None:
        self.par_fn: Optional[str] = None
        self.description: Optional[str] = None
        self.climatestation: Optional[str] = None
        self._cli_fn: Optional[str] = None

class NoClimateStationSelectedError(Exception):
    """
    Select a climate station before building climate.
    """

    __name__ = 'NoClimateStationSelectedError'

    def __init__(self) -> None:
        pass


class ClimateModeIsUndefinedError(Exception):
    """
    Select a climate mode before building climate.
    """

    __name__ = 'ClimateModeIsUndefinedError'

    def __init__(self) -> None:
        pass

class ClimateNoDbLockedException(Exception):
    pass


class ClimateStationMode(IntEnum):
    FindClosestAtRuntime = -1
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
    def parse(x: Optional[str]) -> 'ClimateMode':
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


_SINGLE_STORM_DEPRECATED_MESSAGE = (
    "Single-storm climate modes are deprecated and unsupported in WEPPcloud. "
    "Use continuous or multi-year climate datasets instead."
)


def _assert_supported_climate_mode(mode: ClimateMode) -> None:
    if mode in (
        ClimateMode.SingleStorm,
        ClimateMode.SingleStormBatch,
        ClimateMode.UserDefinedSingleStorm,
    ):
        raise ValueError(_SINGLE_STORM_DEPRECATED_MESSAGE)


class ClimateSpatialMode(IntEnum):
    Undefined = -1
    Single = 0
    Multiple = 1
    MultipleInterpolated = 2

    @staticmethod
    def parse(x: Optional[str]) -> 'ClimateSpatialMode':
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
    def parse(x: str) -> 'ClimatePrecipScalingMode':
        if   x == 'no_scaling':
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


_TENERIFE_CLIGEN_DB_BASENAME = "tenerife_stations.db"


# noinspection PyUnusedLocal
class Climate(NoDbBase):
    
    _js_decode_replacements = (("\"orig_cli_fn\"", "\"_orig_cli_fn\""),)

    filename = 'climate.nodb'
    
    def __init__(
        self, 
        wd: str, 
        cfg_fn: str, 
        run_group: Optional[str] = None, 
        group_name: Optional[str] = None
    ) -> None:
        super(Climate, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._input_years = 100
            self._climatestation_mode = ClimateStationMode.FindClosestAtRuntime
            self._climatestation = None

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
            self._ss_time_to_peak_intensity_pct = 40
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
            
            if self.config_get_str('climate', 'precip_scale_mode', None) is not None:
                self._precip_scaling_mode = ClimatePrecipScalingMode.parse(
                    self.config_get_str('climate', 'precip_scale_mode'))

            self._climate_daily_temp_ds = None

            self._orig_cli_fn = None

            self.monthlies = None
            self.par_fn = None
            self.cli_fn = None

            self.sub_par_fns = None
            self.sub_cli_fns = None

            self._closest_stations = None
            self._heuristic_stations = None

            self._cligen_db = self.config_get_path('climate', 'cligen_db')
            assert self._cligen_db is not None

            _observed_clis_wc = self.config_get_path('climate', 'observed_clis_wc')
            _future_clis_wc = self.config_get_path('climate', 'future_clis_wc')

            self._observed_clis_wc = _observed_clis_wc
            self._future_clis_wc = _future_clis_wc

            self._use_gridmet_wind_when_applicable = self.config_get_bool(
                'climate',
                'use_gridmet_wind_when_applicable',
            )
            self._adjust_mx_pt5 = self.config_get_bool('climate', 'adjust_mx_pt5', False)
            self._catalog_id = None
            self._user_station_meta = None

    @property
    def daymet_last_available_year(self) -> int:
        return DAYMET_LAST_AVAILABLE_YEAR

    @property
    def use_gridmet_wind_when_applicable(self) -> bool:
        return getattr(self, '_use_gridmet_wind_when_applicable', True)

    @property
    def adjust_mx_pt5(self) -> bool:
        return getattr(self, '_adjust_mx_pt5', False)

    @property
    def catalog_id(self) -> Optional[str]:
        return getattr(self, '_catalog_id', None)

    @catalog_id.setter
    @nodb_setter
    def catalog_id(self, value: Optional[str]) -> None:
        self._catalog_id = value

    @use_gridmet_wind_when_applicable.setter
    @nodb_setter
    def use_gridmet_wind_when_applicable(self, value: bool) -> None:
        self._use_gridmet_wind_when_applicable = value

    @adjust_mx_pt5.setter
    @nodb_setter
    def adjust_mx_pt5(self, value: bool) -> None:
        self._adjust_mx_pt5 = value

    @property
    def precip_scale_reference(self) -> Optional[str]:
        return getattr(self, '_precip_scale_reference', None)
    
    @precip_scale_reference.setter
    @nodb_setter
    def precip_scale_reference(self, value: Optional[str]) -> None:
        assert value is None or value in ['prism', 'daymet', 'gridmet']
        self._precip_scale_reference = value

    @property
    def precip_monthly_scale_factors(self) -> List[float]:
        return getattr(self, '_precip_monthly_scale_factors', [1 for i in range(12)])
    
    @precip_monthly_scale_factors.setter
    @nodb_setter
    def precip_monthly_scale_factors(self, value: Optional[List[float]]) -> None:
        assert value is None or len(value) == 12
        self._precip_monthly_scale_factors = value

    @property
    def precip_scale_factor(self) -> Optional[float]:
        return getattr(self, '_precip_scale_factor', None)

    @precip_scale_factor.setter
    @nodb_setter
    def precip_scale_factor(self, value: Optional[float]) -> None:
        self._precip_scale_factor = value

    @property
    def precip_scale_factor_map(self) -> Optional[str]:
        return getattr(self, '_precip_scale_factor_map', None)

    @property
    def gridmet_precip_scale_factor(self) -> Optional[float]:
        return getattr(self, '_gridmet_precip_scale_factor', None)

    @property
    def gridmet_precip_scale_factor_map(self) -> Optional[str]:
        return getattr(self, '_gridmet_precip_scale_factor_map', None)

    @property
    def daymet_precip_scale_factor(self) -> Optional[float]:
        return getattr(self, '_daymet_precip_scale_factor', None)

    @property
    def daymet_precip_scale_factor_map(self) -> Optional[str]:
        return getattr(self, '_daymet_precip_scale_factor_map', None)

    @property
    def cligen_db(self) -> str:
        return getattr(self, '_cligen_db', self.config_get_str('climate', 'cligen_db'))

    @property
    def uses_tenerife_station_catalog(self) -> bool:
        cligen_db = str(self.cligen_db or "").strip()
        if not cligen_db:
            return False
        basename = _split(cligen_db)[1] or cligen_db
        return basename.lower() == _TENERIFE_CLIGEN_DB_BASENAME

    def _validate_station_catalog_constraints(
        self,
        *,
        climate_mode: Optional[ClimateMode] = None,
        climate_spatialmode: Optional[ClimateSpatialMode] = None,
        climatestation_mode: Optional[ClimateStationMode] = None,
    ) -> None:
        if not self.uses_tenerife_station_catalog:
            return

        if climate_mode is not None and climate_mode not in (
            ClimateMode.Undefined,
            ClimateMode.Vanilla,
        ):
            raise ValueError(
                "Tenerife station catalog only supports Vanilla climate mode."
            )

        if climate_spatialmode is not None and climate_spatialmode not in (
            ClimateSpatialMode.Undefined,
            ClimateSpatialMode.Single,
        ):
            raise ValueError(
                "Tenerife station catalog only supports Single climate spatial mode."
            )

        if climatestation_mode is not None and climatestation_mode not in (
            ClimateStationMode.FindClosestAtRuntime,
            ClimateStationMode.Closest,
        ):
            raise ValueError(
                "Tenerife station catalog only supports auto and distance-ranking station modes."
            )

    @property
    def cli_path(self) -> str:
        return _join(self.cli_dir, self.cli_fn)

    @property
    def is_breakpoint(self) -> bool:
        cli = ClimateFile(self.cli_path)
        return cli.breakpoint

    @property
    def observed_clis(self) -> Optional[List[str]]:
        wc = getattr(self, '_observed_clis_wc', None)
        if wc is None:
            return None

        return glob(_join(wc, '*.cli'))

    @property
    def future_clis(self) -> Optional[List[str]]:
        wc = getattr(self, '_future_clis_wc', None)
        if wc is None:
            return None

        return glob(_join(wc, '*.cli'))

    @property
    def years(self) -> int:
        return self._input_years

    @property
    def observed_start_year(self) -> Union[str, int]:
        return self._observed_start_year

    @property
    def observed_end_year(self) -> Union[str, int]:
        return self._observed_end_year

    @property
    def future_start_year(self) -> Union[str, int]:
        return self._future_start_year

    @property
    def future_end_year(self) -> Union[str, int]:
        return self._future_end_year

    @property
    def calendar_start_year(self) -> Optional[int]:
        """Return the calendar start year for WEPP date calculations.
        
        Checks both observed and future start years, normalizing empty strings
        and invalid values to None. Prioritizes observed over future climate data.
        
        Returns:
            Integer year if valid start year exists, None otherwise.
        """
        def _normalize(value: object) -> Optional[int]:
            try:
                if value is None:
                    return None
                if isinstance(value, str) and value.strip() == '':
                    return None
                return int(value)
            except (TypeError, ValueError):
                return None
        
        for candidate in (self._observed_start_year, self._future_start_year):
            normalized = _normalize(candidate)
            if normalized is not None:
                return normalized

        # Fall back to the active CLI file when available. This is especially
        # important for user-defined uploads where observed/future start years
        # are unset but the CLI contains explicit calendar years.
        cli_fn = getattr(self, "cli_fn", None)
        cli_dir = getattr(self, "cli_dir", None)
        if cli_fn and cli_dir:
            cli_path = Path(str(cli_dir)) / str(cli_fn)
            try:
                if cli_path.exists():
                    seen_header = False
                    with cli_path.open() as fp:
                        for line in fp:
                            stripped = line.strip()
                            if not stripped:
                                continue
                            if not seen_header:
                                if stripped.lower().startswith("da"):
                                    seen_header = True
                                continue

                            tokens = stripped.split()
                            if len(tokens) < 3:
                                continue
                            try:
                                return int(tokens[2])
                            except (TypeError, ValueError):
                                continue
            except OSError:
                self.logger.debug(
                    "Failed inferring calendar_start_year from cli file",
                    extra={"cli_path": str(cli_path)},
                    exc_info=True,
                )
        return None

    @property
    def ss_storm_date(self) -> str:
        return self._ss_storm_date

    @property
    def ss_design_storm_amount_inches(self) -> float:
        return self._ss_design_storm_amount_inches

    @property
    def ss_duration_of_storm_in_hours(self) -> float:
        return self._ss_duration_of_storm_in_hours

    @property
    def ss_time_to_peak_intensity_pct(self) -> float:
        return self._ss_time_to_peak_intensity_pct

    @property
    def ss_max_intensity_inches_per_hour(self) -> float:
        return self._ss_max_intensity_inches_per_hour

    @property
    def ss_batch_storms(self) -> Optional[List[Dict[str, Any]]]:
        return getattr(self, '_ss_batch_storms', None)

    @property
    def ss_batch(self) -> str:
        return getattr(self, '_ss_batch', '')


    @ss_batch.setter
    @nodb_setter
    def ss_batch(self, value: str) -> None:
        self._ss_batch = value

    @property
    def climate_daily_temp_ds(self) -> str:
        return getattr(self, '_climate_daily_temp_ds', 'null')

    @climate_daily_temp_ds.setter
    @nodb_setter
    def climate_daily_temp_ds(self, value: str) -> None:
        self._climate_daily_temp_ds = value

    @property
    def daymet_version(self) -> str:
        return getattr(self, '_daymet_version', 'v4')


    @daymet_version.setter
    @nodb_setter
    def daymet_version(self, value: str) -> None:
        self._daymet_version = value

    #
    # climatestation_mode
    #
    @property
    def climatestation_mode(self) -> ClimateStationMode:
        return self._climatestation_mode

    @property
    def has_climatestation_mode(self) -> bool:
        return self._climatestation_mode \
               is not ClimateStationMode.FindClosestAtRuntime

    @climatestation_mode.setter
    @nodb_setter
    def climatestation_mode(self, value: Union[ClimateStationMode, int]) -> None:
        if isinstance(value, ClimateStationMode):
            mode = value
        elif isinstance(value, int):
            mode = ClimateStationMode(value)
        else:
            raise ValueError('most be ClimateStationMode or int')
        self._validate_station_catalog_constraints(climatestation_mode=mode)
        self._climatestation_mode = mode

    # noinspection PyPep8Naming
    @property
    def onLoad_refreshStationSelection(self) -> str:
        return json.dumps(self.climatestation_mode is not ClimateStationMode.FindClosestAtRuntime)

    def available_catalog_datasets(self, include_hidden: bool = False) -> List[Any]:
        return _CLIMATE_STATION_CATALOG_SERVICE.available_catalog_datasets(
            self, include_hidden=include_hidden
        )

    def catalog_datasets_payload(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        return [dataset.to_mapping() for dataset in self.available_catalog_datasets(include_hidden=include_hidden)]

    def _resolve_catalog_dataset(self, catalog_id: str, include_hidden: bool = False) -> Optional[Any]:
        return _CLIMATE_STATION_CATALOG_SERVICE.resolve_catalog_dataset(
            self, catalog_id, include_hidden=include_hidden
        )

    @property
    def year0(self) -> Optional[int]:
        try:
            cli_fn = self.cli_fn

            if cli_fn is None:
                return False

            cli_path = _join(self.cli_dir, self.cli_fn)
            cli = ClimateFile(cli_path)
            years = cli.years

            return years[0]
        except (OSError, ValueError, IndexError, TypeError):
            return None

    @property
    def has_observed(self) -> Optional[bool]:
        try:
            cli_fn = self.cli_fn

            if cli_fn is None:
                return False

            cli_path = _join(self.cli_dir, self.cli_fn)
            cli = ClimateFile(cli_path)
            years = cli.years

            return all(yr > 1900 for yr in years)
        except (OSError, ValueError, TypeError):
            return None

    #
    # climatestation
    #
    @property
    def climatestation(self) -> Optional[str]:
        return self._climatestation

    @climatestation.setter
    @nodb_setter
    def climatestation(self, value: Optional[str]) -> None:
        self._climatestation = value

    @property
    def climatestation_meta(self) -> Any:
        return _CLIMATE_STATION_CATALOG_SERVICE.climatestation_meta(self)

    @property
    def climatestation_par_contents(self) -> str:
        par_fn = self.climatestation_meta.parpath
        with open(par_fn) as fp:
            return fp.read()

    #
    # climate_mode
    #
    @property
    def climate_mode(self) -> ClimateMode:
        return self._climate_mode

    @climate_mode.setter
    @nodb_setter
    def climate_mode(self, value: Union[ClimateMode, int, str]) -> None:
        if isinstance(value, ClimateMode):
            mode = value
        elif isint(value):
            mode = ClimateMode(int(value))
        else:
            mode = ClimateMode.parse(value)
        _assert_supported_climate_mode(mode)
        self._validate_station_catalog_constraints(climate_mode=mode)
        self._climate_mode = mode

    @property
    def is_single_storm(self) -> bool:
        return self._climate_mode in (
    ClimateMode.SingleStorm,
    ClimateMode.SingleStormBatch,
    ClimateMode.UserDefinedSingleStorm)


    #
    # precip_scaling_mode
    #
    @property
    def precip_scaling_mode(self) -> ClimatePrecipScalingMode:
        if not hasattr(self, '_precip_scaling_mode'):
            return ClimatePrecipScalingMode.NoScaling
        
        return self._precip_scaling_mode

    @precip_scaling_mode.setter
    @nodb_setter
    def precip_scaling_mode(self, value: Union[ClimatePrecipScalingMode, int, str]) -> None:
        if isinstance(value, ClimatePrecipScalingMode):
            self._precip_scaling_mode = value
        elif isinstance(value, int):
            self._precip_scaling_mode = ClimatePrecipScalingMode(value)
        else:
            self._precip_scaling_mode = ClimatePrecipScalingMode.parse(value)

    #
    # precip_scaling_reference
    #
    @property
    def precip_scaling_reference(self) -> Optional[str]:
        if not hasattr(self, '_precip_scaling_reference'):
            return None
        
        return self._precip_scaling_reference

    @precip_scaling_reference.setter
    @nodb_setter
    def precip_scaling_reference(self, value: Optional[str]) -> None:
        self._precip_scaling_reference = value

    #
    # climate_spatial mode
    #
    @property
    def climate_spatialmode(self) -> ClimateSpatialMode:
        return self._climate_spatialmode

    @climate_spatialmode.setter
    @nodb_setter
    def climate_spatialmode(self, value: Union[ClimateSpatialMode, int, str]) -> None:
        if isinstance(value, ClimateSpatialMode):
            spatialmode = value
        elif isinstance(value, int):
            spatialmode = ClimateSpatialMode(value)
        else:
            spatialmode = ClimateSpatialMode.parse(value)
        self._validate_station_catalog_constraints(climate_spatialmode=spatialmode)
        self._climate_spatialmode = spatialmode

    #
    # station search
    #
    def find_closest_stations(self, num_stations: int = 10) -> Optional[List[Dict[str, Any]]]:
        self._validate_station_catalog_constraints(
            climatestation_mode=ClimateStationMode.Closest
        )
        return _CLIMATE_STATION_CATALOG_SERVICE.find_closest_stations(self, num_stations=num_stations)
        
    @property
    def closest_stations(self) -> Optional[List[Dict[str, Any]]]:
        """
        returns heuristic_stations as jsonifyable dicts
        """
        if self._closest_stations is None:
            return None

        return [s.as_dict() for s in self._closest_stations]

    def find_heuristic_stations(self, num_stations: int = 10) -> Optional[List[Dict[str, Any]]]:
        self._validate_station_catalog_constraints(
            climatestation_mode=ClimateStationMode.Heuristic
        )
        return _CLIMATE_STATION_CATALOG_SERVICE.find_heuristic_stations(self, num_stations=num_stations)

    def find_eu_heuristic_stations(self, num_stations: int = 10) -> Optional[List[Dict[str, Any]]]:
        self._validate_station_catalog_constraints(
            climatestation_mode=ClimateStationMode.EUHeuristic
        )
        return _CLIMATE_STATION_CATALOG_SERVICE.find_eu_heuristic_stations(
            self, num_stations=num_stations
        )

    def find_au_heuristic_stations(self, num_stations: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        self._validate_station_catalog_constraints(
            climatestation_mode=ClimateStationMode.AUHeuristic
        )
        return _CLIMATE_STATION_CATALOG_SERVICE.find_au_heuristic_stations(
            self, num_stations=num_stations
        )
        
    @property
    def heuristic_stations(self) -> Optional[List[Dict[str, Any]]]:
        """
        returns heuristic_stations as dicts
        """
        if self._heuristic_stations is None:
            return None

        return [s.as_dict() for s in self._heuristic_stations]

    @property
    def orig_cli_fn(self) -> Optional[str]:
        return self._orig_cli_fn

    @orig_cli_fn.setter
    @nodb_setter
    def orig_cli_fn(self, value: Optional[str]) -> None:
        self._orig_cli_fn = value

    @property
    def input_years(self) -> int:
        return self._input_years

    @input_years.setter
    @nodb_setter
    def input_years(self, value: int) -> None:
        self._input_years = int(value)

    @property
    def has_station(self) -> bool:
        return self.climatestation is not None

    #
    # has_climate
    #
    @property
    def has_climate(self) -> bool:
        if self.climate_spatialmode == ClimateSpatialMode.Multiple:
            return self.sub_par_fns is not None and \
                   self.sub_cli_fns is not None and \
                   self.cli_fn is not None
        else:
            return self.cli_fn is not None

    def _export_cli_parquet(self) -> Path | None:
        return _CLIMATE_ARTIFACT_EXPORT_SERVICE.export_cli_parquet(self)

    def _export_cli_precip_frequency_csv(self, parquet_path: Path) -> Optional[Path]:
        return _CLIMATE_ARTIFACT_EXPORT_SERVICE.export_cli_precip_frequency_csv(self, parquet_path)

    def _download_noaa_atlas14_intensity(self) -> Optional[Path]:
        return _CLIMATE_ARTIFACT_EXPORT_SERVICE.download_noaa_atlas14_intensity(self)

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        _CLIMATE_INPUT_PARSER.parse_inputs(self, kwds)

    def set_observed_pars(self, **kwds: Any) -> None:
        with self.locked():
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

    def set_future_pars(self,  **kwds: Any) -> None:
        with self.locked():
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

    def set_single_storm_pars(self, **kwds: Any) -> None:
        with self.locked():
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

    def build(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        _CLIMATE_BUILD_ROUTER.build(self, verbose=verbose, attrs=attrs)
        
    def _scale_precip(self, scale_factor: float) -> None:
        _CLIMATE_SCALING_SERVICE.scale_precip(self, scale_factor)

    def _scale_precip_monthlies(self, monthly_scale_factors: List[float], scale_func: Any) -> None:
        _CLIMATE_SCALING_SERVICE.scale_precip_monthlies(self, monthly_scale_factors, scale_func)

    def _spatial_scale_precip(self, scale_factor_map: str) -> None:
        _CLIMATE_SCALING_SERVICE.spatial_scale_precip(self, scale_factor_map)

    def _build_climate_depnexrad(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        run_depnexrad_build(self, verbose=verbose, attrs=attrs)

    def _build_climate_prism(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        self.logger.info('  running _build_climate_prism... ')

        with self.locked():
            self.set_attrs(attrs)

            # cligen can accept a 5 digit random number seed
            # we want to specify this to ensure that the precipitation
            # events are synchronized across the subcatchments
            if self._cligen_seed is None:
                self._cligen_seed = random.randint(0, 99999)
                self.dump()

            randseed = self._cligen_seed

            cli_dir = os.path.abspath(self.cli_dir)
            watershed = self.watershed_instance

            climatestation = self.climatestation
            years = self._input_years

            # build a climate for the channels.
            lng, lat = watershed.centroid

            self.par_fn = '{}.par'.format(climatestation)
            self.cli_fn = '{}.cli'.format(climatestation)

            self.monthlies = prism_mod(par=climatestation,
                                     years=years, lng=lng, lat=lat, wd=cli_dir,
                                     logger=self.logger, nwds_method='',
                                     adjust_mx_pt5=self.adjust_mx_pt5)

    def _prism_revision(self, verbose: bool = False):
        run_prism_revision(self, verbose=verbose)

    def _post_defined_climate(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        with self.locked():
            self.set_attrs(attrs)

            self.logger.info('Copying original climate file...')
            orig_cli_fn = self.orig_cli_fn
            cli_dir = self.cli_dir
            assert orig_cli_fn is not None
            assert _exists(orig_cli_fn)

            cli_dir = os.path.abspath(self.cli_dir)

            cli_fn = _split(orig_cli_fn)[1]
            cli_path = _join(cli_dir, cli_fn)
            try:
                copyfile(orig_cli_fn, cli_path)
            except shutil.SameFileError:
                pass

            self.cli_fn = cli_fn
            assert _exists(cli_path)

            self.sub_par_fns = None
            self.sub_cli_fns = None

            with self.timed('Calculating monthlies'):
                cli = ClimateFile(_join(cli_dir, cli_fn))
                self.monthlies = cli.calc_monthlies()

    def _build_climate_mod(self, mod_function: Any, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        run_mod_build(self, mod_function, verbose=verbose, attrs=attrs)

    def set_user_defined_cli(self, cli_fn: str, verbose: bool = False) -> None:
        with self.locked():
            self.logger.info('  running set_userdefined_cli... ')
            self._orig_cli_fn = _join(self.cli_dir, cli_fn)
#            cli_path = self.cli_path
            cli = ClimateFile(self.orig_cli_fn)

            if cli.is_single_storm:
                self._climate_mode = ClimateMode.UserDefinedSingleStorm

            self._input_years = cli.input_years
            monthlies = cli.calc_monthlies()
            self.monthlies = monthlies
            # Avoid nodb_setter recursion while already holding the lock.
            self._catalog_id = 'user_defined_cli'
            self._user_station_meta = _CLIMATE_USER_DEFINED_STATION_META_SERVICE.build_station_meta_from_cli(
                cli=cli,
                cli_filename=cli_fn,
                cli_dir=self.cli_dir,
                monthlies=monthlies,
            )
            
        self._post_defined_climate(verbose=verbose)

        if self.climate_spatialmode == ClimateSpatialMode.Multiple:
            self._prism_revision(verbose=verbose)

        # Ensure downstream interchange jobs see the correct calendar lookup for
        # the newly uploaded CLI. The interchange layer prefers `wepp_cli.parquet`
        # and will not regenerate it if an older copy exists.
        _CLIMATE_ARTIFACT_EXPORT_SERVICE.export_post_build_artifacts(self)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.build_climate)
        except FileNotFoundError:
            pass

    def _build_climate_vanilla(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        with self.locked():
            self.set_attrs(attrs)

            self.logger.info('  running _build_climate_vanilla... ')
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

    def _build_climate_observed_daymet(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        with self.locked():
            self.set_attrs(attrs)
            self.logger.info('  running _build_climate_observed_daymet')

            watershed = self.watershed_instance
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

            cli_fn = 'wepp.cli'
            prn_fn = 'ws.prn'
            self.logger.info('  building {}... '.format(cli_fn))

            
            build_observed_daymet(cligen, ws_lng, ws_lat, start_year, end_year, cli_dir, prn_fn, cli_fn,
                                  gridmet_wind=self.use_gridmet_wind_when_applicable,
                                  adjust_mx_pt5=self.adjust_mx_pt5)

            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

    def _build_climate_observed_gridmet_multiple(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        with self.locked():
            self.set_attrs(attrs)
            self.logger.info('  running _build_climate_observed_gridmet_multiple')
            _CLIMATE_GRIDMET_MULTIPLE_BUILD_SERVICE.build(
                self,
                build_observed_gridmet_interpolated_fn=build_observed_gridmet_interpolated,
                ncpu=NCPU,
            )

    def _build_climate_observed_daymet_multiple(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        run_observed_daymet_multiple_build(self, verbose=verbose, attrs=attrs)

    def _build_climate_observed_gridmet(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        with self.locked():
            self.set_attrs(attrs)
            self.logger.info('  running _build_climate_observed_gridmet')

            watershed = self.watershed_instance
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._observed_start_year, self._observed_end_year

            self._input_years = end_year - start_year + 1

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            cli_fn = 'wepp.cli'
            prn_fn = 'ws.prn'
            self.logger.info('  building {}... '.format(cli_fn))

            build_observed_gridmet(
                cligen, ws_lng, ws_lat, start_year, end_year, cli_dir, prn_fn, cli_fn,
                adjust_mx_pt5=self.adjust_mx_pt5,
            )

            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

    def _build_climate_future(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        with self.locked():
            self.set_attrs(attrs)
            self.logger.info('  running _build_climate_future')

            watershed = self.watershed_instance
            ws_lng, ws_lat = watershed.centroid
            self.logger.info(f'    watershed centroid: ({ws_lng:.4f}, {ws_lat:.4f})')

            cli_dir = self.cli_dir
            start_year, end_year = self._future_start_year, self._future_end_year

            self._input_years = end_year - start_year + 1
            self.logger.info(
                f'    generating future climate for {start_year}-{end_year} '
                f'({self._input_years} years total)'
            )

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)
            station_desc = getattr(stationMeta, 'desc', '').strip()
            try:
                station_lon = float(getattr(stationMeta, 'longitude', float('nan')))
                station_lat = float(getattr(stationMeta, 'latitude', float('nan')))
                station_coords = f'({station_lon:.3f}, {station_lat:.3f})'
            except (TypeError, ValueError):
                raw_lon = getattr(stationMeta, 'longitude', '?')
                raw_lat = getattr(stationMeta, 'latitude', '?')
                station_coords = f'({raw_lon}, {raw_lat})'
            self.logger.info(
                f'    using CLIGEN station {climatestation} {station_coords} '
                f'({station_desc}) from database {self.cligen_db}'
            )

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            cli_fn = 'wepp.cli'
            prn_fn = 'ws.prn'
            self.logger.info(
                f'    fetching CMIP5 RCP8.5 time series and building future CLI (prn={prn_fn}, cli={cli_fn})'
            )

            build_future(
                cligen, ws_lng, ws_lat, start_year, end_year, cli_dir, prn_fn, cli_fn,
                adjust_mx_pt5=self.adjust_mx_pt5,
            )
            self.logger.info('    CMIP5/CLIGEN processing complete')

            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn
            monthlies_size = len(self.monthlies) if self.monthlies is not None else 0
            self.logger.info(
                f'    monthlies computed (entries={monthlies_size}); future climate assets ready'
            )

    def _build_climate_single_storm_batch(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
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
            key = 'ss_' + '_'.join(v.strip() for v in L)
            specs[key] = dict(
                ss_storm_date=f'{mo} {da} {yr}',
                ss_design_storm_amount_inches=float(prcp),
                ss_duration_of_storm_in_hours=float(duration),
                ss_time_to_peak_intensity_pct=float(tp),
                ss_max_intensity_inches_per_hour=float(ip),
            )

        with self.locked():
            self.set_attrs(attrs)

            self.logger.info('  running _build_climate_single_storm... ')

            storms = []
            result: Optional[SingleStormResult] = None
            for i, (key, spec) in enumerate(specs.items()):

                result = build_single_storm_cli(
                    climatestation,
                    spec['ss_storm_date'],
                    spec['ss_design_storm_amount_inches'],
                    spec['ss_duration_of_storm_in_hours'],
                    spec['ss_time_to_peak_intensity_pct'],
                    spec['ss_max_intensity_inches_per_hour'],
                    output_dir=self.cli_dir,
                    filename_prefix=key,
                    version=self.cligen_db,
                )

                storms.append(
                    dict(
                        ss_batch_id=i + 1,
                        ss_batch_key=key,
                        spec=spec,
                        par_fn=result.par_fn,
                        cli_fn=result.cli_fn,
                    )
                )

            if len(storms) > 20:
                raise ValueError('Only 20 single storms can be ran in batch mode')

            if result is None:
                raise ValueError('Single storm batch specs were empty')

            self._ss_batch_storms = storms
            self.monthlies = result.monthlies
            self.par_fn = result.par_fn
            self.cli_fn = result.cli_fn

    def _build_climate_single_storm(self, verbose: bool = False, attrs: Optional[Dict[str, Any]] = None) -> None:
        """
        single storm
        """
        with self.locked():
            self.set_attrs(attrs)

            self.logger.info('  running _build_climate_single_storm... ')
            climatestation = self.climatestation

            result = build_single_storm_cli(
                climatestation,
                self._ss_storm_date,
                self._ss_design_storm_amount_inches,
                self._ss_duration_of_storm_in_hours,
                self._ss_time_to_peak_intensity_pct,
                self._ss_max_intensity_inches_per_hour,
                output_dir=self.cli_dir,
                filename_prefix=climatestation,
                version=self.cligen_db,
            )

            self.monthlies = result.monthlies
            self.par_fn = result.par_fn
            self.cli_fn = result.cli_fn

    def sub_summary(self, topaz_id: str) -> Optional[Dict[str, str]]:
        if not self.has_climate:
            return None

        if self.sub_cli_fns is None:
            cli_fn = self.cli_fn
        else:
            cli_fn = self.sub_cli_fns.get(str(topaz_id), self.cli_fn)


        if self.sub_par_fns is None:
            par_fn = self.cli_fn
        else:
            par_fn = self.sub_par_fns.get(str(topaz_id), self.par_fn)

        return dict(cli_fn=cli_fn, par_fn=par_fn)

    def chn_summary(self, topaz_id: str) -> Optional[Dict[str, str]]:
        if not is_channel(topaz_id):
            raise ValueError('topaz_id is not channel')

        if not self.has_climate:
            return None

        return dict(cli_fn=self.cli_fn, par_fn=self.par_fn)

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id: int) -> Dict[str, str]:
        if not self.has_climate:
            raise IndexError

        if self._climate_spatialmode == ClimateSpatialMode.Multiple:
            translator = self.watershed_instance.translator_factory()
            topaz_id = str(translator.top(wepp=int(wepp_id)))

            if topaz_id in self.sub_cli_fns:
                cli_fn = self.sub_cli_fns[topaz_id]
                par_fn = self.sub_par_fns[topaz_id]
                return dict(cli_fn=cli_fn, par_fn=par_fn)

        else:
            return dict(cli_fn=self.cli_fn,
                        par_fn=self.par_fn)

        raise IndexError
