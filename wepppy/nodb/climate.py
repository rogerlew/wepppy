# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import os
import math
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
import json
from enum import IntEnum
import random
from glob import glob

import shutil

from shutil import copyfile
import multiprocessing

# non-standard
import jsonpickle

# wepppy
from wepppy.climates import cligen_client as cc
from wepppy.climates.metquery_client import get_daily
from wepppy.climates.gridmet import client as gridmet_client
from wepppy.climates.prism import prism_mod, prism_revision
from wepppy.eu.climates.eobs import eobs_mod
from wepppy.au.climates.agdc import agdc_mod
from wepppy.climates.cligen import CligenStationsManager, ClimateFile, Cligen, build_daymet_prn, build_gridmet_prn
from wepppy.all_your_base import isint, isfloat, RasterDatasetInterpolator, haversine
from wepppy.watershed_abstraction import ischannel

# wepppy submodules
from .base import NoDbBase, DEFAULT_CLIGEN_DB
from .watershed import Watershed
from .ron import Ron
from .log_mixin import LogMixin

NCPU = math.floor(multiprocessing.cpu_count() * 0.5)
if NCPU < 1:
    NCPU = 1

CLIMATE_MAX_YEARS = 1000


class ClimateSummary(object):
    def __init__(self):
        self.par_fn = None
        self.description = None
        self.climatestation = None
        self._cli_fn = None


class ClimateNoDbLockedException(Exception):
    pass


class ClimateStationMode(IntEnum):
    Undefined = -1
    Closest = 0
    Heuristic = 1
    EUHeuristic = 2
    AUHeuristic = 3


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


class ClimateSpatialMode(IntEnum):
    Undefined = -1
    Single = 0
    Multiple = 1


def build_observed(kwds):
    lng = kwds['lng']
    lat = kwds['lat']
    observed_data = kwds['observed_data']
    start_year = kwds['start_year']
    end_year = kwds['end_year']
    prn_fn = kwds['prn_fn']
    cli_dir = kwds['cli_dir']
    cli_fn = kwds['cli_fn']
    climatestation = kwds['climatestation']
    version = kwds.get('version', '2015')

    build_daymet_prn(lng=lng, lat=lat,
                     observed_data=observed_data,
                     start_year=start_year, end_year=end_year,
                     prn_fn=_join(cli_dir, prn_fn))

    stationManager = CligenStationsManager(version=version)
    stationMeta = stationManager.get_station_fromid(climatestation)
    cligen = Cligen(stationMeta, wd=cli_dir)
    cligen.run_observed(prn_fn, cli_fn=cli_fn)

    return cli_fn


# noinspection PyUnusedLocal
class Climate(NoDbBase, LogMixin):
    def __init__(self, wd, cfg_fn):
        super(Climate, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._input_years = 30
            self._climatestation_mode = ClimateStationMode.Undefined
            self._climatestation = None

            if 'eu' in cfg_fn:
                self._climate_mode = ClimateMode.EOBS
            if 'au' in cfg_fn:
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

            from wepppy.nodb.mods import MODS_DIR
            config = self.config
            self._cligen_db = config.get('climate', 'cligen_db')

            _observed_clis_wc = config.get('climate', 'observed_clis_wc')
            if _observed_clis_wc is not None:
                _observed_clis_wc = _observed_clis_wc.replace('MODS_DIR', MODS_DIR)

            if _observed_clis_wc == 'None':
                _observed_clis_wc = None
            else:
                assert _exists(_observed_clis_wc), _observed_clis_wc

            _future_clis_wc = config.get('climate', 'future_clis_wc')
            if _future_clis_wc is not None:
                _future_clis_wc = _future_clis_wc.replace('MODS_DIR', MODS_DIR)

            if _future_clis_wc == 'None':
                _future_clis_wc = None
            else:
                assert _exists(_future_clis_wc)

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
    def getInstance(wd):
        with open(_join(wd, 'climate.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Climate)

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'climate.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'climate.nodb.lock')

    @property
    def cligen_db(self):
        return getattr(self, '_cligen_db', DEFAULT_CLIGEN_DB)

    @property
    def cli_path(self):
        return _join(self.cli_dir, self.cli_fn)

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
        return json.dumps(self.climatestation_mode is not
                          ClimateStationMode.Undefined)

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

            elif isinstance(value, int):
                self._climate_mode = ClimateMode(value)

            else:
                raise ValueError('most be ClimateMode or int')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def is_single_storm(self):
        return self._climate_mode == ClimateMode.SingleStorm

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
                raise ValueError('most be ClimateSpatialMode or int')

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
    def input_years(self):
        return self._input_years

    @input_years.setter
    def input_years(self, value):
        self._input_years = value

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

            if climate_mode == ClimateMode.Vanilla or \
               climate_mode == ClimateMode.SingleStorm or \
               climate_mode == ClimateMode.Future:
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
                self.orig_cli_fn = cli_path

            self._climate_mode = climate_mode
            self._climate_spatialmode = climate_spatialmode
            self._input_years = input_years

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
    """
    def set_original_climate_fn(self, **kwds):
        set the localized pars.
        must provide named keyword args to avoid mucking this up

        The kwds are coded such that:
            0 for station data
            1 for Daymet
            2 for prism
        
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.orig_cli_fn = kwds['climate_fn']

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
    """

    def set_orig_cli_fn(self, cli_fn):

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.orig_cli_fn = cli_fn
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

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
                assert ss_time_to_peak_intensity_pct > 0
                assert ss_time_to_peak_intensity_pct < 1

            self._ss_storm_date = ss_storm_date
            self._ss_design_storm_amount_inches = \
                ss_design_storm_amount_inches
            self._ss_duration_of_storm_in_hours = \
                ss_duration_of_storm_in_hours
            self._ss_max_intensity_inches_per_hour = \
                ss_max_intensity_inches_per_hour
            self._ss_time_to_peak_intensity_pct = \
                ss_time_to_peak_intensity_pct

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def build(self, verbose=False):
        cli_dir = self.cli_dir
        if _exists(cli_dir):
            try:
                shutil.rmtree(cli_dir)
            except:
                pass

        if not _exists(cli_dir):
            os.mkdir(cli_dir)

        climate_mode = self.climate_mode

        # vanilla Cligen
        if climate_mode == ClimateMode.Vanilla:
            self._build_climate_vanilla()

        # observed
        elif climate_mode == ClimateMode.Observed:
            self._build_climate_observed()

        # observed
        elif climate_mode == ClimateMode.ObservedPRISM:
            self._build_climate_observed_prism_revised()

        # future
        elif climate_mode == ClimateMode.Future:
            self._build_climate_future()

        # single storm
        elif climate_mode == ClimateMode.SingleStorm:
            self._build_climate_single_storm()

        # PRISM
        elif climate_mode == ClimateMode.PRISM:
            self._build_climate_mod(mod_function=prism_mod, verbose=verbose)

        elif climate_mode in [ClimateMode.ObservedDb, ClimateMode.FutureDb]:
            assert self.orig_cli_fn is not None
            self._build_climate_observed_cli_PRISM(verbose=verbose)

        # EOBS
        elif climate_mode == ClimateMode.EOBS:
            self._build_climate_mod(mod_function=eobs_mod, verbose=verbose)

        elif climate_mode == ClimateMode.AGDC:
            self._build_climate_mod(mod_function=agdc_mod, verbose=verbose)

        elif climate_mode == ClimateMode.GridMetPRISM:
            self._build_climate_observed_gridmet_prism_revised()

    def _build_climate_observed_cli_PRISM(self, verbose):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('Copying original climate file...')
            orig_cli_fn = self.orig_cli_fn
            cli_dir = self.cli_dir
            assert orig_cli_fn is not None
            assert _exists(orig_cli_fn)

            cli_dir = os.path.abspath(self.cli_dir)
            watershed = Watershed.getInstance(self.wd)

            cli_fn = _split(orig_cli_fn)[1]
            cli_path = _join(cli_dir, cli_fn)
            copyfile(orig_cli_fn, cli_path)
            assert _exists(cli_path)
            self.log_done()

            # build a climate for the channels.
            ws_lng, ws_lat = watershed.centroid

            self.par_fn = '.par'

            distance = 1e38
            closest_hill = None
            if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                # build a climate for each subcatchment
                sub_par_fns = {}
                sub_cli_fns = {}
                for topaz_id, ss in watershed._subs_summary.items():
                    self.log('    Using prism to spatialize {}...'.format(topaz_id))

                    hill_lng, hill_lat = ss.centroid.lnglat
                    suffix = '_{}'.format(topaz_id)
                    new_cli_fn = cli_path.replace('.cli', suffix + '.cli')

                    prism_revision(cli_path, ws_lng, ws_lat, hill_lng, hill_lat, new_cli_fn)

                    sub_par_fns[topaz_id] = '.par'
                    sub_cli_fns[topaz_id] = _split(new_cli_fn)[-1]

                    _d = haversine((ws_lng, ws_lat), (hill_lng, hill_lat))
                    if _d < distance:
                        closest_hill = topaz_id
                        distance = _d

                    self.log_done()

                self.sub_par_fns = sub_par_fns
                self.sub_cli_fns = sub_cli_fns

            # set the watershed climate file to be the one closest to the centroid
            assert closest_hill is not None
            self.cli_fn = cli_fn = sub_cli_fns[closest_hill]

            self.log('Calculating monthlies...')
            cli = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = cli.calc_monthlies()
            self.log_done()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_mod(self, mod_function, verbose):
        self.log('  running _build_climate_prism... \n')

        self.lock()

        # noinspection PyBroadInspection
        try:
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
                self.log('  building climates... \n')
                # build a climate for each subcatchment
                sub_par_fns = {}
                sub_cli_fns = {}
                for topaz_id, ss in watershed._subs_summary.items():
                    self.log('fetching climate for {}... '.format(topaz_id))

                    lng, lat = ss.centroid.lnglat
                    suffix = '_{}'.format(topaz_id)

                    mod_function(par=climatestation,
                                 years=years, lng=lng, lat=lat, wd=cli_dir,
                                 suffix=suffix, logger=self, nwds_method='')

                    sub_par_fns[topaz_id] = '{}{}.par'.format(climatestation, suffix)
                    sub_cli_fns[topaz_id] = '{}{}.cli'.format(climatestation, suffix)

                    self.log_done()

                self.sub_par_fns = sub_par_fns
                self.sub_cli_fns = sub_cli_fns

            self.log('  finalizing climate build... ')
            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_vanilla(self):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('  running _build_climate_vanilla... ')
            climatestation = self.climatestation
            years = self._input_years

            result = cc.fetch_multiple_year(climatestation, years)
            par_fn, cli_fn, monthlies = cc.unpack_json_result(result, climatestation,
                                                   self.cli_dir)

            self.monthlies = monthlies
            self.par_fn = par_fn
            self.cli_fn = cli_fn
            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_observed(self, verbose=False):

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('  running _build_climate_observed (watershed)... \n')
            watershed = Watershed.getInstance(self.wd)
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._observed_start_year, self._observed_end_year
            self._input_years = end_year - start_year

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            ron = Ron.getInstance(self.wd)
            # daymet is 1000m resolution. So each pixel is 0.06 degrees
            # 1 / ((6378.1 * 1000) / 1000 / 360) = 0.056 ~ 0.06
            # for cubic interpolation we need at least 5 pixels
            # so we pad 3 pixels in each direction to be on the safe side
            pad = 0.06 * 4
            bbox = ron.map.extent
            bbox = [bbox[0] - pad, bbox[1] - pad,
                    bbox[2] + pad, bbox[3] + pad]
            bbox = ','.join(str(v) for v in bbox)

            observed_data = {}
            daymet_base = self.config.get('climate', 'daymet_observed')
            for varname in ['prcp', 'tmin', 'tmax']:
                for year in range(start_year, end_year + 1):
                    dataset = _join(daymet_base, varname)
                    self.log('  fetching {} for year {}... '.format(dataset, year))
                    dst = _join(cli_dir, 'daymet_observed_{}_{}.nc4'.format(varname, year))
                    get_daily(dataset=dataset, bbox=bbox, year=year, dst=dst)
                    observed_data[(varname, year)] = dst
                    self.log_done()

            cli_fn = 'wepp.cli'
            self.log('  building {}... '.format(cli_fn))
            prn_fn = 'ws.prn'
            build_daymet_prn(lng=ws_lng, lat=ws_lat,
                             observed_data=observed_data,
                             start_year=start_year, end_year=end_year,
                             prn_fn=_join(cli_dir, prn_fn))

            cligen.run_observed(prn_fn, cli_fn=cli_fn)

            climate = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

            self.log_done()

            if self.climate_spatialmode == ClimateSpatialMode.Multiple:
                pool = multiprocessing.Pool(NCPU)
                sub_par_fns = {}
                sub_cli_fns = {}
                args = []
                for (topaz_id, ss) in watershed._subs_summary.items():
                    fn_base = '{}_{}'.format(topaz_id, climatestation)
                    cli_fn = '{}.cli'.format(fn_base)

                    lng, lat = ss.centroid.lnglat
                    prn_fn = '{}.prn'.format(fn_base)

                    kwds = dict(lng=lng, lat=lat,
                                observed_data=observed_data,
                                start_year=start_year, end_year=end_year,
                                prn_fn=prn_fn, cli_dir=cli_dir,
                                cli_fn=cli_fn,
                                climatestation=climatestation,
                                version=self.cligen_db)

                    args.append(kwds)
                    sub_par_fns[topaz_id] = par_fn
                    sub_cli_fns[topaz_id] = cli_fn

                for cli_fn in pool.imap_unordered(build_observed, args):
                    self.log('  done running {}\n'.format(cli_fn))

                self.sub_cli_fns = sub_cli_fns
                self.sub_par_fns = sub_par_fns

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_observed_prism_revised(self, verbose=False):

        assert self.climate_spatialmode == ClimateSpatialMode.Multiple

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('  running _build_climate_observed (watershed)... \n')
            watershed = Watershed.getInstance(self.wd)
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._observed_start_year, self._observed_end_year
            self._input_years = end_year - start_year

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            ron = Ron.getInstance(self.wd)
            # daymet is 1000m resolution. So each pixel is 0.06 degrees
            # 1 / ((6378.1 * 1000) / 1000 / 360) = 0.056 ~ 0.06
            # for cubic interpolation we need at least 5 pixels
            # so we pad 3 pixels in each direction to be on the safe side
            pad = 0.06 * 4
            bbox = ron.map.extent
            bbox = [bbox[0] - pad, bbox[1] - pad,
                    bbox[2] + pad, bbox[3] + pad]
            bbox = ','.join(str(v) for v in bbox)

            observed_data = {}
            daymet_base = self.config.get('climate', 'daymet_observed')
            for varname in ['prcp', 'tmin', 'tmax']:
                for year in range(start_year, end_year + 1):
                    dataset = _join(daymet_base, varname)
                    self.log('  fetching {} for year {}... '.format(dataset, year))
                    dst = _join(cli_dir, 'daymet_observed_{}_{}.nc4'.format(varname, year))
                    get_daily(dataset=dataset, bbox=bbox, year=year, dst=dst)
                    observed_data[(varname, year)] = dst
                    self.log_done()

            cli_fn = 'wepp.cli'
            self.log('  building {}... '.format(cli_fn))
            prn_fn = 'ws.prn'
            build_daymet_prn(lng=ws_lng, lat=ws_lat,
                             observed_data=observed_data,
                             start_year=start_year, end_year=end_year,
                             prn_fn=_join(cli_dir, prn_fn))

            cligen.run_observed(prn_fn, cli_fn=cli_fn)

            cli_path = _join(cli_dir, cli_fn)
            climate = ClimateFile(cli_path)
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

            self.log_done()

            # build a climate for the channels.
            ws_lng, ws_lat = watershed.centroid

            distance = 1e38
            closest_hill = None

            # build a climate for each subcatchment
            sub_par_fns = {}
            sub_cli_fns = {}
            for topaz_id, ss in watershed._subs_summary.items():
                self.log('    Using prism to spatialize {}...'.format(topaz_id))

                hill_lng, hill_lat = ss.centroid.lnglat
                suffix = '_{}'.format(topaz_id)
                new_cli_fn = cli_path.replace('.cli', suffix + '.cli')

                prism_revision(cli_path, ws_lng, ws_lat, hill_lng, hill_lat, new_cli_fn)

                sub_par_fns[topaz_id] = '.par'
                sub_cli_fns[topaz_id] = _split(new_cli_fn)[-1]

                _d = haversine((ws_lng, ws_lat), (hill_lng, hill_lat))
                if _d < distance:
                    closest_hill = topaz_id
                    distance = _d

                self.log_done()

                self.sub_par_fns = sub_par_fns
                self.sub_cli_fns = sub_cli_fns

            # set the watershed climate file to be the one closest to the centroid
            assert closest_hill is not None
            self.cli_fn = cli_fn = sub_cli_fns[closest_hill]

            self.log('Calculating monthlies...')
            cli = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = cli.calc_monthlies()
            self.log_done()

            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_observed_gridmet_prism_revised(self, verbose=False):

        assert self.climate_spatialmode == ClimateSpatialMode.Multiple

        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('  running _build_climate_observed (watershed)... \n')
            watershed = Watershed.getInstance(self.wd)
            ws_lng, ws_lat = watershed.centroid

            cli_dir = self.cli_dir
            start_year, end_year = self._observed_start_year, self._observed_end_year
            self._input_years = end_year - start_year

            stationManager = CligenStationsManager(version=self.cligen_db)
            climatestation = self.climatestation
            stationMeta = stationManager.get_station_fromid(climatestation)

            par_fn = stationMeta.par
            cligen = Cligen(stationMeta, wd=cli_dir)

            ron = Ron.getInstance(self.wd)

            variables = [gridmet_client.GridMetVariable.Precipitation,
                         gridmet_client.GridMetVariable.MinimumTemperature,
                         gridmet_client.GridMetVariable.MaximumTemperature]
            met_dir = _join(cli_dir, 'gridmet')

            self.log('  fetching gridmet timeseries...')
            gridmet_client.retrieve_timeseries(variables, {'pw0': watershed.centroid}, start_year, end_year, met_dir)
            self.log_done()

            cli_fn = 'wepp.cli'
            self.log('  building {}... '.format(cli_fn))
            prn_fn = 'ws.prn'
            build_gridmet_prn(_join(met_dir, 'pw0'),
                              start_year=start_year, end_year=end_year,
                              prn_fn=_join(cli_dir, prn_fn))

            cligen.run_observed(prn_fn, cli_fn=cli_fn)

            cli_path = _join(cli_dir, cli_fn)
            climate = ClimateFile(cli_path)
            self.monthlies = climate.calc_monthlies()
            self.cli_fn = cli_fn
            self.par_fn = par_fn

            self.log_done()

            # build a climate for the channels.
            ws_lng, ws_lat = watershed.centroid

            distance = 1e38
            closest_hill = None

            # build a climate for each subcatchment
            sub_par_fns = {}
            sub_cli_fns = {}
            for topaz_id, ss in watershed._subs_summary.items():
                self.log('    Using prism to spatialize {}...'.format(topaz_id))

                hill_lng, hill_lat = ss.centroid.lnglat
                suffix = '_{}'.format(topaz_id)
                new_cli_fn = cli_path.replace('.cli', suffix + '.cli')

                prism_revision(cli_path, ws_lng, ws_lat, hill_lng, hill_lat, new_cli_fn)

                sub_par_fns[topaz_id] = '.par'
                sub_cli_fns[topaz_id] = _split(new_cli_fn)[-1]

                _d = haversine((ws_lng, ws_lat), (hill_lng, hill_lat))
                if _d < distance:
                    closest_hill = topaz_id
                    distance = _d

                self.log_done()

                self.sub_par_fns = sub_par_fns
                self.sub_cli_fns = sub_cli_fns

            # set the watershed climate file to be the one closest to the centroid
            assert closest_hill is not None
            self.cli_fn = cli_fn = sub_cli_fns[closest_hill]

            self.log('Calculating monthlies...')
            cli = ClimateFile(_join(cli_dir, cli_fn))
            self.monthlies = cli.calc_monthlies()
            self.log_done()

            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_future(self):
        self.lock()

        # noinspection PyBroadInspection
        try:

            self.log('  running _build_climate_future... \n')
            assert self._input_years == (self._future_end_year - self._future_start_year) + 1
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            climatestation = self.climatestation

            self.log('  fetching future climate data... ')
            result = cc.future_rcp85(
                climatestation,
                self._future_start_year,
                self._future_end_year,
                lng=lng, lat=lat
            )
            self.log_done()

            self.log('  running cligen... ')
            par_fn, cli_fn, monthlies = cc.unpack_json_result(
                result,
                climatestation,
                self.cli_dir
            )

            self.monthlies = self.monthlies
            self.par_fn = par_fn
            self.cli_fn = cli_fn
            self.dump_and_unlock()
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_single_storm(self):
        """
        single storm
        """
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.log('  running _build_climate_single_storm... ')
            climatestation = self.climatestation

            result = cc.selected_single_storm(
                climatestation,
                self._ss_storm_date,
                self._ss_design_storm_amount_inches,
                self._ss_duration_of_storm_in_hours,
                self._ss_time_to_peak_intensity_pct,
                self._ss_max_intensity_inches_per_hour
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
        if not ischannel(topaz_id):
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
