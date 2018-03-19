# standard library
import os
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
import json
from enum import IntEnum
import random

from shutil import copyfile

from concurrent.futures import ThreadPoolExecutor, as_completed

# non-standard
import jsonpickle

# wepppy
from wepppy.climates import cligen_client as cc
from wepppy.climates.prism import prism_optimized2, prism_revision
from wepppy.climates.cligen import CligenStationsManager
from wepppy.all_your_base import isint, isfloat
from wepppy.watershed_abstraction import ischannel

# wepppy submodules
from .base import NoDbBase
from .watershed import Watershed

CLIMATE_MAX_YEARS = 100


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


class ClimateMode(IntEnum):
    Undefined = -1
    Single = 0
    Localized = 1
    Observed = 2
    Future = 3
    SingleStorm = 4
    SinglePRISM = 5
    Optimized = 6
    ObservedPRISM = 7
    MultipleObserved = 8


# noinspection PyUnusedLocal
class Climate(NoDbBase):
    def __init__(self, wd, cfg_fn):
        super(Climate, self).__init__(wd, cfg_fn)
        
        self.lock()

        # noinspection PyBroadException
        try:
            self._input_years = 1
            self._climatestation_mode = ClimateStationMode.Undefined
            self._climatestation = None
            self._climate_mode = ClimateMode.Undefined
            self._input_years = 1  # in years
            self._cligen_seed = None
            self._localized_p_mean = 2  # 012
            self._localized_p_std = 0  # 01
            self._localized_p_skew = 0  # 01
            self._localized_p_ww = 0  # 01
            self._localized_p_wd = 0  # 01
            self._localized_tmax = 2  # 02
            self._localized_tmin = 2  # 02
            self._localized_solrad = 1  # 01
            self._localized_dewpoint = 0  # 01
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
            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'climate.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'climate.nodb.lock')

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
            self._climatestation = int(value)
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def climatestation_meta(self):
        climatestation = self.climatestation
    
        if climatestation is None:
            return None
    
        station_manager = CligenStationsManager()
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

    #
    # station search
    #

    def find_closest_stations(self, num_stations=10):
        self.lock()

        # noinspection PyBroadInspection
        try:
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            results = self._closest_stations
            if results is None:
                station_manager = CligenStationsManager()
                results = station_manager\
                    .get_closest_stations((lng, lat), num_stations)
                self._closest_stations = results

            self._climatestation = int(results[0].id)
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
            results = self._heuristic_stations
            if results is None:
                station_manager = CligenStationsManager()
                results = station_manager\
                    .get_stations_heuristic_search((lng, lat), num_stations)
                self._heuristic_stations = results

            self._climatestation = int(results[0].id)
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
    # localization
    #
    @property
    def localized_p_mean(self):
        return self._localized_p_mean  # 012

    @property
    def localized_p_std(self):
        return self._localized_p_std  # 01

    @property
    def localized_p_skew(self):
        return self._localized_p_skew  # 01

    @property
    def localized_p_ww(self):
        return self._localized_p_ww  # 01

    @property
    def localized_p_wd(self):
        return self._localized_p_wd  # 01

    @property
    def localized_tmax(self):
        return self._localized_tmax  # 02

    @property
    def localized_tmin(self):
        return self._localized_tmin  # 02

    @property
    def localized_solrad(self):
        return self._localized_solrad  # 01

    @property
    def localized_dewpoint(self):
        return self._localized_dewpoint  # 01

    #
    # has_climate
    #
    @property
    def has_climate(self):
        mode = self.climate_mode

        assert isinstance(mode, ClimateMode)

        if mode == ClimateMode.Undefined:
            return False

        if self.climate_mode == ClimateMode.Localized:
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

            input_years = kwds['input_years']
            if isint(input_years):
                input_years = int(input_years)

            if climate_mode in [ClimateMode.Single, ClimateMode.Localized]:
                assert isint(input_years)
                assert input_years > 0
                assert input_years < CLIMATE_MAX_YEARS

            self._climate_mode = climate_mode
            self._input_years = input_years

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        # mode 1: localized
        self.set_localized_pars(
            **dict(p_mean=kwds['localized_p_mean'],
                   p_std=kwds['localized_p_std'],
                   p_skew=kwds['localized_p_skew'],
                   p_ww=kwds['localized_p_ww'],
                   p_wd=kwds['localized_p_wd'],
                   solrad=kwds['localized_solrad'],
                   tmax=kwds['localized_tmax'],
                   tmin=kwds['localized_tmin'],
                   dewpoint=kwds['localized_dewpoint']))

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

    def set_original_climate_fn(self, **kwds):
        """
        set the localized pars.
        must provide named keyword args to avoid mucking this up

        The kwds are coded such that:
            0 for station data
            1 for Daymet
            2 for prism
        """
        self.lock()

        # noinspection PyBroadInspection
        try:
            self.orig_cli_fn = kwds['climate_fn']

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_localized_pars(self, **kwds):
        """
        set the localized pars.
        must provide named keyword args to avoid mucking this up

        The kwds are coded such that:
            0 for station data
            1 for Daymet
            2 for prism
        """
        self.lock()

        # noinspection PyBroadInspection
        try:
            p_mean = kwds['p_mean']
            p_std = kwds['p_std']
            p_skew = kwds['p_skew']
            p_ww = kwds['p_ww']
            p_wd = kwds['p_wd']
            solrad = kwds['solrad']
            tmax = kwds['tmax']
            tmin = kwds['tmin']
            dewpoint = kwds['dewpoint']

            p_mean = int(p_mean)
            assert p_mean in [0, 1, 2]

            p_std = int(p_std)
            assert p_std in [0, 1]

            p_skew = int(p_skew)
            assert p_skew in [0, 1]

            p_wd = int(p_wd)
            assert p_wd in [0, 1]

            p_ww = int(p_ww)
            assert p_ww in [0, 1]

            solrad = int(solrad)
            assert solrad in [0, 1]

            tmax = int(tmax)
            assert tmax in [0, 2]

            tmin = int(tmin)
            assert tmin in [0, 2]

            dewpoint = int(dewpoint)
            assert dewpoint in [0, 1]

            if p_mean + p_std + p_skew + p_wd + p_ww + \
               solrad + tmin + tmax + dewpoint == 0:
                raise Exception('No localizations are defined, \
                                 run single climate')

            self._localized_p_mean = p_mean
            self._localized_p_std = p_std
            self._localized_p_skew = p_skew
            self._localized_p_wd = p_wd
            self._localized_p_ww = p_ww
            self._localized_solrad = solrad
            self._localized_tmin = tmin
            self._localized_tmax = tmax
            self._localized_dewpoint = dewpoint

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
                assert start_year <= 2016

                assert isint(end_year)
                assert end_year >= 1980
                assert end_year <= 2016

                assert end_year >= start_year
                assert end_year - start_year <= CLIMATE_MAX_YEARS

            self._observed_start_year = start_year
            self._observed_end_year = end_year
            self._input_years = end_year - start_year + 1

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

            self._future_start_year = start_year
            self._future_end_year = end_year
            self._input_years = end_year - start_year + 1

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

            if self.climate_mode == ClimateMode.SingleStorm:
                ss_storm_date = ss_storm_date.split()
                assert len(ss_storm_date) == 3
                assert all([isint(token) for token in ss_storm_date])
                ss_storm_date = ' '.join(ss_storm_date)

                assert isfloat(ss_design_storm_amount_inches)
                assert ss_design_storm_amount_inches > 0

                assert isfloat(ss_duration_of_storm_in_hours)
                assert ss_duration_of_storm_in_hours > 0

                assert isfloat(ss_max_intensity_inches_per_hour)
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
        climate_mode = self.climate_mode

        # vanilla Cligen
        if climate_mode == ClimateMode.Single:
            self._build_climate_single()

        # localized
        elif climate_mode == ClimateMode.Localized:
            self._build_climate_localized(verbose=verbose)

        # observed
        elif climate_mode == ClimateMode.Observed:
            self._build_climate_observed()

        # observed
        elif climate_mode == ClimateMode.MultipleObserved:
            self._build_climate_multiple_observed()

        # future
        elif climate_mode == ClimateMode.Future:
            self._build_climate_future()

        # single storm
        elif climate_mode == ClimateMode.SingleStorm:
            self._build_climate_single_storm()

        # single PRISM
        elif climate_mode == ClimateMode.SinglePRISM:
            self._build_climate_single_PRISM()

        # single PRISM
        elif climate_mode == ClimateMode.Optimized:
            self._build_climate_optimized(verbose=verbose)

        # multiple observed PRISM
        elif climate_mode == ClimateMode.ObservedPRISM:
            self._build_climate_observed_PRISM(verbose=verbose)

    def _build_climate_observed_PRISM(self, verbose):
        self.lock()

        # noinspection PyBroadInspection
        try:
            orig_cli_fn = self.orig_cli_fn
            assert _exists(orig_cli_fn)

            cli_dir = os.path.abspath(self.cli_dir)
            watershed = Watershed.getInstance(self.wd)

            climatestation = self.climatestation
            years = self._input_years

            # build a climate for the channels.
            ws_lng, ws_lat = watershed.centroid

            head, tail = _split(orig_cli_fn)
            cli_path = _join(cli_dir, tail)

            print('cli_path: ' + cli_path)

            copyfile(orig_cli_fn, cli_path)

            self.par_fn = '.par'
            self.cli_fn = tail

            # build a climate for each subcatchment
            sub_par_fns = {}
            sub_cli_fns = {}
            for topaz_id, ss in watershed._subs_summary.items():
                if verbose:
                    print('fetching climate for {}'.format(topaz_id))

                hill_lng, hill_lat = ss.centroid.lnglat
                suffix = '_{}'.format(topaz_id)
                new_cli_fn = cli_path.replace('.cli', suffix + '.cli')

                prism_revision(orig_cli_fn, ws_lng, ws_lat, hill_lng, hill_lat, new_cli_fn)

                sub_par_fns[topaz_id] = '.par'
                sub_cli_fns[topaz_id] = _split(new_cli_fn)[-1]

            self.sub_par_fns = sub_par_fns
            self.sub_cli_fns = sub_cli_fns

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_optimized(self, verbose):
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

            self.opt_pars = prism_optimized2(
                    par=climatestation,
                    years=years, lng=lng, lat=lat, wd=cli_dir)

            # build a climate for each subcatchment
            sub_par_fns = {}
            sub_cli_fns = {}
            for topaz_id, ss in watershed._subs_summary.items():
                if verbose:
                    print('fetching climate for {}'.format(topaz_id))

                lng, lat = ss.centroid.lnglat
                suffix = '_{}'.format(topaz_id)

                prism_optimized2(
                    par=climatestation,
                    years=years, lng=lng, lat=lat, wd=cli_dir,
                    run_opt=False, x0=self.opt_pars, suffix=suffix)

                sub_par_fns[topaz_id] = '{}{}.par'.format(climatestation, suffix)
                sub_cli_fns[topaz_id] = '{}{}.cli'.format(climatestation, suffix)

            self.sub_par_fns = sub_par_fns
            self.sub_cli_fns = sub_cli_fns

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_single(self):
        self.lock()

        # noinspection PyBroadInspection
        try:
            climatestation = self.climatestation
            years = self._input_years

            result = cc.fetch_multiple_year(climatestation, years)
            par_fn, cli_fn, monthlies = cc.unpack_json_result(result, climatestation,
                                                   self.cli_dir)

            self.monthlies = monthlies
            self.par_fn = par_fn
            self.cli_fn = cli_fn
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_single_PRISM(self):
        self.lock()

        # noinspection PyBroadInspection
        try:
            climatestation = self.climatestation
            years = self._input_years

            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid

            result = cc.fetch_multiple_year(
                climatestation, years,
                lng=lng, lat=lat,
                p_mean='prism', tmax='prism', tmin='prism', p_ww='daymet'
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

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_localized(self, verbose):
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

            cli_dir = self.cli_dir
            watershed = Watershed.getInstance(self.wd)

            climatestation = self.climatestation
            years = self._input_years

            # the climates are built with the wepppy cligen
            # webservice. The webservice accepts localization
            # parameters as strings. This assigns parameters
            # from the localized attributes
            opts = [None, 'daymet', 'prism']

            p_mean = opts[self._localized_p_mean]
            p_std = opts[self._localized_p_std]
            p_skew = opts[self._localized_p_skew]
            p_wd = opts[self._localized_p_wd]
            p_ww = opts[self._localized_p_ww]
            solrad = opts[self._localized_solrad]
            tmin = opts[self._localized_tmin]
            tmax = opts[self._localized_tmax]
            dewpoint = opts[self._localized_dewpoint]
            kwargs = dict(p_mean=p_mean, p_std=p_std, p_skew=p_skew,
                          p_wd=p_wd, p_ww=p_ww, tmax=tmax, tmin=tmin,
                          solrad=solrad, dewpoint=dewpoint,
                          randseed='%05i' % randseed)

            # build a climate for each subcatchment
            sub_par_fns = {}
            sub_cli_fns = {}
            for topaz_id, ss in watershed._subs_summary.items():
                if verbose:
                    print('fetching climate for {}'.format(topaz_id))

                lng, lat = ss.centroid.lnglat

                result = cc.fetch_multiple_year(climatestation, years,
                                                lng=lng, lat=lat, **kwargs)

                fn_base = '{}_{}'.format(topaz_id, climatestation)
                par_fn, cli_fn, _ = cc.unpack_json_result(result, fn_base, cli_dir)

                sub_par_fns[topaz_id] = par_fn
                sub_cli_fns[topaz_id] = cli_fn

            # build a climate for the channels.
            lng, lat = watershed.centroid
            result = cc.fetch_multiple_year(climatestation, years,
                                            lng=lng, lat=lat, **kwargs)
            fn_base = str(climatestation)
            par_fn, cli_fn, monthlies = cc.unpack_json_result(result, fn_base, cli_dir)

            self.monthlies = monthlies
            self.par_fn = par_fn
            self.cli_fn = cli_fn
            
            self.sub_par_fns = sub_par_fns
            self.sub_cli_fns = sub_cli_fns
            
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_observed(self):
        self.lock()

        # noinspection PyBroadInspection
        try:
            assert self._input_years == (self._observed_end_year - self._observed_start_year) + 1

            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            climatestation = self.climatestation

            result = cc.observed_daymet(
                climatestation,
                self._observed_start_year,
                self._observed_end_year,
                lng=lng, lat=lat
            )

            par_fn, cli_fn, monthlies = cc.unpack_json_result(
                result,
                climatestation,
                self.cli_dir
            )

            self.monthlies = self.monthlies
            self.cli_fn = cli_fn
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_multiple_observed(self, verbose=True):
        self.lock()

        # noinspection PyBroadInspection
        try:
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            climatestation = self.climatestation
            cli_dir = self.cli_dir


            sub_par_fns = {}
            sub_cli_fns = {}

            # We can use a with statement to ensure threads are cleaned up promptly
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Start the load operations and mark each future with its URL
                results = {executor.submit(cc.observed_daymet,
                                           climatestation,
                                           self._observed_start_year,
                                           self._observed_end_year,
                                           ss.centroid.lnglat[0],
                                           ss.centroid.lnglat[1]):
                           (topaz_id, ss) for (topaz_id, ss) in watershed._subs_summary.items()}

                for res in as_completed(results):
                    (topaz_id, ss) = results[res]
                    data = res.result()

                    fn_base = '{}_{}'.format(topaz_id, climatestation)
                    par_fn, cli_fn, _ = cc.unpack_json_result(data, fn_base, cli_dir)

                    if verbose:
                        print(topaz_id, ss, cli_fn)

                    sub_par_fns[topaz_id] = par_fn
                    sub_cli_fns[topaz_id] = cli_fn

            """
            # build a climate for each subcatchment
            sub_par_fns = {}
            sub_cli_fns = {}
            for topaz_id, ss in watershed._subs_summary.items():
                if verbose:
                    print('fetching climate for {}'.format(topaz_id))

                lng, lat = ss.centroid.lnglat

                result = cc.observed_daymet(
                    climatestation,
                    self._observed_start_year,
                    self._observed_end_year,
                    lng=lng, lat=lat
                )

                fn_base = '{}_{}'.format(topaz_id, climatestation)
                par_fn, cli_fn, _ = cc.unpack_json_result(result, fn_base, cli_dir)

                sub_par_fns[topaz_id] = par_fn
                sub_cli_fns[topaz_id] = cli_fn
            """

            lng, lat = watershed.centroid

            result = cc.observed_daymet(
                climatestation,
                self._observed_start_year,
                self._observed_end_year,
                lng=lng, lat=lat
            )

            par_fn, cli_fn, monthlies = cc.unpack_json_result(
                result,
                climatestation,
                self.cli_dir
            )

            self.monthlies = self.monthlies
            self.cli_fn = cli_fn
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_climate_future(self):
        self.lock()

        # noinspection PyBroadInspection
        try:

            assert self._input_years == (self._future_end_year - self._future_start_year) + 1
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            climatestation = self.climatestation

            result = cc.future_rcp85(
                climatestation,
                self._future_start_year,
                self._future_end_year,
                lng=lng, lat=lat
            )

            par_fn, cli_fn, monthlies = cc.unpack_json_result(
                result,
                climatestation,
                self.cli_dir
            )

            self.monthlies = self.monthlies
            self.par_fn = par_fn
            self.cli_fn = cli_fn
            self.dump_and_unlock()

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

        except Exception:
            self.unlock('-f')
            raise

    def sub_summary(self, topaz_id):
        if not self.has_climate:
            return None
        
        if self.climate_mode == ClimateMode.Localized:
            return dict(cli_fn=self.sub_cli_fns[topaz_id],
                        par_fn=self.sub_par_fns[topaz_id])
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
            
        if self.climate_mode == ClimateMode.Localized:
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
