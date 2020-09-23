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
from enum import IntEnum
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from subprocess import Popen, PIPE
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_EXCEPTION

from datetime import datetime
import time

import pickle

from glob import glob

import shutil

# non-standard
import jsonpickle

import numpy as np

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *

import wepppy

# wepppy
from wepppy.climates.cligen import ClimateFile
from wepppy.wepp.runner import (
    make_hillslope_run,
    make_ss_hillslope_run,
    run_hillslope,
    make_flowpath_run,
    run_flowpath,
    make_watershed_run,
    make_ss_watershed_run,
    run_watershed
)
from wepppy.wepp.management import (
    get_channel,
    merge_managements,
    pmetpara_prep
)


from wepppy.all_your_base import (
    isfloat,
    read_arc,
    wgs84_proj4,
    isnan,
    isinf
)

from wepppy.wepp.out import (
    Loss,
    Ebe,
    PlotFile,
    correct_daily_hillslopes_pl_path,
    NumYearsIsZeroException
)

from wepppy.wepp.stats import ChannelWatbal, HillslopeWatbal, ReturnPeriods, SedimentDelivery

# wepppy submodules
from wepppy.wepp.stats.frq_flood import FrqFlood
from .base import NoDbBase, TriggerEvents
from .landuse import Landuse, LanduseMode
from .soils import Soils, SoilsMode
from .climate import Climate, ClimateMode
from .watershed import Watershed
from .topaz import Topaz
from .wepppost import WeppPost
from .log_mixin import LogMixin

try:
    NCPU = int(os.environ['WEPPPY_NCPU'])
except KeyError:
    NCPU = math.floor(multiprocessing.cpu_count() * 0.5)
    if NCPU < 1:
        NCPU = 1


_RUN_WEPP_UI_DEFAULT = True
_RUN_PMET_DEFAULT = True
_RUN_FROST_DEFAULT = False
_RUN_TCR_DEFAULT = False
_RUN_BASEFLOW_DEFAULT = True
_RUN_SNOW_DEFAULT = False


class ChannelRoutingMethod(IntEnum):
    Creams = 2
    MuskingumCunge = 4


class SnowOpts(object):
    def __init__(self, rst=None, newsnw=None, ssd=None):
        """
        Stores the coeffs that go into snow.txt
        """
        # rain-snow threshold
        if rst is None:
            self.rst = 0.0
        else:
            self.rst = rst

        # density of new snow
        if newsnw is None:
            self.newsnw = 100.0
        else:
            self.newsnw = newsnw

        # snow settling density
        if ssd is None:
            self.ssd = 250.0
        else:
            self.ssd = ssd

    def parse_inputs(self, kwds):
        if 'rst' in kwds:
            self.rst = float(kwds['rst'])

        if 'newsnw' in kwds:
            self.newsnw = float(kwds['newsnw'])

        if 'ssd' in kwds:
            self.ssd = float(kwds['ssd'])

    @property
    def contents(self):
        return (
            '{0.rst}  # rain-snow threshold\n'
            '{0.newsnw}  # density of new snow\n'
            '{0.ssd}  # snow settling density\n'
            .format(self)
        )


class BaseflowOpts(object):
    def __init__(self, gwstorage=None, bfcoeff=None, dscoeff=None, bfthreshold=None):
        """
        Stores the coeffs that go into gwcoeff.txt
        """
        # Initial groundwater storage (mm)
        if gwstorage is None:
            self.gwstorage = 200
        else:
            self.gwstorage = gwstorage

        # Baseflow coefficient (per day)
        if bfcoeff is None:
            self.bfcoeff = 0.04
        else:
            self.bfcoeff = bfcoeff

        # Deep seepage coefficient (per day)
        if dscoeff is None:
            self.dscoeff = 0
        else:
            self.dscoeff = dscoeff

        # Watershed groundwater baseflow threshold area (ha)
        if bfthreshold is None:
            self.bfthreshold = 1
        else:
            self.bfthreshold = bfthreshold

    def parse_inputs(self, kwds):
        self.gwstorage = float(kwds['gwstorage'])
        self.bfcoeff = float(kwds['bfcoeff'])
        self.dscoeff = float(kwds['dscoeff'])
        self.bfthreshold = float(kwds['bfthreshold'])

    @property
    def contents(self):
        return (
            '{0.gwstorage}\tInitial groundwater storage (mm)\n'
            '{0.bfcoeff}\tBaseflow coefficient (per day)\n'
            '{0.dscoeff}\tDeep seepage coefficient (per day)\n'
            '{0.bfthreshold}\tWatershed groundwater baseflow threshold area (ha)\n\n'
            .format(self)
        )


def validate_phosphorus_txt(fn):

    with open(fn) as fp:
        lines = fp.readlines()
    lines = [L for L in lines if not L.strip() == '']
    if 'Phosphorus concentration' != lines[0].strip():
        return False

    opts = [isfloat(L.split()[0]) for L in lines[1:]]
    if len(opts) != 4:
        return False

    if not all(opts):
        return False

    return True


class PhosphorusOpts(object):
    def __init__(self, surf_runoff=None, lateral_flow=None, baseflow=None, sediment=None):
        # Surface runoff concentration (mg/l)
        self.surf_runoff = surf_runoff

        # Subsurface lateral flow concentration (mg/l)
        self.lateral_flow = lateral_flow

        # Baseflow concentration (mg/l)
        self.baseflow = baseflow

        # Sediment concentration (mg/kg)
        self.sediment = sediment

    def parse_inputs(self, kwds):
        # noinspection PyBroadException
        try:
            self.surf_runoff = float(kwds['surf_runoff'])
            self.lateral_flow = float(kwds['lateral_flow'])
            self.baseflow = float(kwds['baseflow'])
            self.sediment = float(kwds['sediment'])
        except Exception:
            pass

    @property
    def isvalid(self):
        return isfloat(self.surf_runoff) and \
               isfloat(self.lateral_flow) and \
               isfloat(self.baseflow) and \
               isfloat(self.sediment)

    @property
    def contents(self):
        return (
            'Phosphorus concentration\n'
            '{0.surf_runoff}\tSurface runoff concentration (mg/l)\n'
            '{0.lateral_flow}\tSubsurface lateral flow concentration (mg/l)\n'
            '{0.baseflow}\tBaseflow concentration (mg/l)\n'
            '{0.sediment}\tSediment concentration (mg/kg)\n\n'
            .format(self)
        )

    def asdict(self):
        return dict(surf_runoff=self.surf_runoff,
                    lateral_flow=self.lateral_flow,
                    baseflow=self.baseflow,
                    sediment=self.sediment)


class WeppNoDbLockedException(Exception):
    pass


class Wepp(NoDbBase, LogMixin):
    __name__ = 'Wepp'

    def __init__(self, wd, cfg_fn):
        super(Wepp, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            wepp_dir = self.wepp_dir
            if not _exists(wepp_dir):
                os.mkdir(wepp_dir)

            config = self.config

            try:
                surf_runoff = config.getfloat('phosphorus_opts', 'surf_runoff')
            except:
                surf_runoff = None
            try:
                lateral_flow = config.getfloat('phosphorus_opts', 'lateral_flow')
            except:
                lateral_flow = None
            try:
                baseflow = config.getfloat('phosphorus_opts', 'baseflow')
            except:
                baseflow = None
            try:
                sediment = config.getfloat('phosphorus_opts', 'sediment')
            except:
                sediment = None

            try:
                snow_rst = config.getfloat('snow_opts', 'rst')
            except:
                snow_rst = None

            try:
                snow_newsnw = config.getfloat('snow_opts', 'newsnw')
            except:
                snow_newsnw = None

            try:
                snow_ssd = config.getfloat('snow_opts', 'ssd')
            except:
                snow_ssd = None

            try:
                _wepp_ui = config.getboolean('wepp', 'wepp_ui')
            except:
                _wepp_ui = _RUN_WEPP_UI_DEFAULT
            try:
                _pmet = config.getboolean('wepp', 'pmet')
            except:
                _pmet = _RUN_PMET_DEFAULT
            try:
                _frost = config.getboolean('wepp', 'frost')
            except:
                _frost = _RUN_FROST_DEFAULT
            try:
                _tcr = config.getboolean('wepp', 'tcr')
            except:
                _tcr = _RUN_TCR_DEFAULT
            try:
                _baseflow = config.getboolean('wepp', 'baseflow')
            except:
                _baseflow = _RUN_BASEFLOW_DEFAULT
            try:
                _snow = config.getboolean('wepp', 'snow')
            except:
                _snow = _RUN_SNOW_DEFAULT


            try:
                _wepp_bin = config.get('wepp', 'bin')
            except:
                _wepp_bin = None

            self.phosphorus_opts = PhosphorusOpts(
                surf_runoff=surf_runoff,
                lateral_flow=lateral_flow,
                baseflow=baseflow,
                sediment=sediment)

            self._run_wepp_ui = _wepp_ui
            self._run_pmet = _pmet
            self._run_frost = _frost
            self._run_tcr = _tcr
            self._run_baseflow = _baseflow
            self._run_snow = _snow
            self._wepp_bin = _wepp_bin

            self.baseflow_opts = BaseflowOpts()
            self.snow_opts = SnowOpts(rst=snow_rst,
                                      newsnw=snow_newsnw,
                                      ssd=snow_ssd)
            self.run_flowpaths = False
            self.loss_grid_d_path = None

            self.clean()

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
        with open(_join(wd, 'wepp.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Wepp)

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db
    @property
    def wepp_bin(self):
        if not hasattr(self, "_wepp_bin"):
            return None

        return self._wepp_bin

    @wepp_bin.setter
    def wepp_bin(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._wepp_bin = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise


    @property
    def _nodb(self):
        return _join(self.wd, 'wepp.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'wepp.nodb.lock')

    @property
    def status_log(self):
        return os.path.abspath(_join(self.runs_dir, 'status.log'))

    @property
    def run_tcr(self):
        if not hasattr(self, "_run_tcr"):
            return _RUN_TCR_DEFAULT

        return self._run_tcr

    @property
    def run_wepp_ui(self):
        if not hasattr(self, "_run_wepp_ui"):
            return _RUN_WEPP_UI_DEFAULT

        return self._run_wepp_ui

    @property
    def run_pmet(self):
        if not hasattr(self, "_run_pmet"):
            return _RUN_PMET_DEFAULT

        return self._run_pmet

    @property
    def run_frost(self):
        if not hasattr(self, "_run_frost"):
            return _RUN_FROST_DEFAULT

        return self._run_frost

    @property
    def run_tcr(self):
        if not hasattr(self, "_run_tcr"):
            return _RUN_TCR_DEFAULT

        return self._run_tcr

    @property
    def run_baseflow(self):
        if not hasattr(self, "_run_baseflow"):
            return _RUN_BASEFLOW_DEFAULT

        return self._run_baseflow

    @property
    def run_snow(self):
        if not hasattr(self, "_run_snow"):
            return _RUN_SNOW_DEFAULT

        return self._run_snow

    def set_baseflow_opts(self, gwstorage=None, bfcoeff=None, dscoeff=None, bfthreshold=None):
        self.lock()

        # noinspection PyBroadException
        try:
            self.baseflow_opts = BaseflowOpts(
                gwstorage=gwstorage,
                bfcoeff=bfcoeff,
                dscoeff=dscoeff,
                bfthreshold=bfthreshold)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_phosphorus_opts(self, surf_runoff=None, lateral_flow=None, baseflow=None, sediment=None):
        self.lock()

        # noinspection PyBroadException
        try:
            self.phosphorus_opts = PhosphorusOpts(
                surf_runoff=surf_runoff,
                lateral_flow=lateral_flow,
                baseflow=baseflow,
                sediment=sediment)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def parse_inputs(self, kwds):
        self.lock()

        # noinspection PyBroadException
        try:
            self.baseflow_opts.parse_inputs(kwds)
            self.phosphorus_opts.parse_inputs(kwds)
            self.snow_opts.parse_inputs(kwds)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def has_run(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        return _exists(loss_pw0)

    @property
    def has_phosphorus(self):
        return self.has_run and \
               self.phosphorus_opts.isvalid and \
               _exists(_join(self.runs_dir, 'phosphorus.txt'))

    #
    # hillslopes
    #
    def prep_hillslopes(self, frost=None, baseflow=None, wepp_ui=None, pmet=None, snow=None):
        self.log('Prepping Hillslopes... ')

        translator = Watershed.getInstance(self.wd).translator_factory()

        # get translator
        self._prep_slopes(translator)
        self._prep_managements(translator)
        self._prep_soils(translator)
        self._prep_climates(translator)
        self._make_hillslope_runs(translator)

        if (frost is None and self.run_frost) or frost:
            self._prep_frost()

        self._prep_phosphorus()

        if (baseflow is None and self.run_baseflow) or baseflow:
            self._prep_baseflow()

        if (wepp_ui is None and self.run_wepp_ui) or wepp_ui:
            self._prep_wepp_ui()
            
        if (pmet is None and self.run_pmet) or pmet:
            self._prep_pmet()

        if (snow is None and self.run_snow) or snow:
            self._prep_snow()

        self.log_done()

    def _prep_wepp_ui(self):
        fn = _join(self.runs_dir, 'wepp_ui.txt')
        with open(fn, 'w') as fp:
            fp.write('')

    def _prep_frost(self):
        fn = _join(self.runs_dir, 'frost.txt')
        with open(fn, 'w') as fp:
            fp.write('1  1  1\n')
            fp.write('1.0   1.0  1.0   0.5\n\n')

    def _prep_tcr(self):
        fn = _join(self.runs_dir, 'tcr.txt')
        with open(fn, 'w') as fp:
            fp.write('\n')

    def _prep_pmet(self, mid_season_crop_coeff=0.95, p_coeff=0.80):
        self.log('nodb.Wepp._prep_pmet::mid_season_crop_coeff = {}, p_coeff = {} '
                 .format(mid_season_crop_coeff, p_coeff))
        self.log_done()

        pmetpara_prep(self.runs_dir,
                      mid_season_crop_coeff=mid_season_crop_coeff,
                      p_coeff=p_coeff)

        assert _exists(_join(self.runs_dir, 'pmetpara.txt'))

    def _prep_phosphorus(self):

        # noinspection PyMethodFirstArgAssignment
        self = self.getInstance(self.wd)

        fn = _join(self.runs_dir, 'phosphorus.txt')
        if self.phosphorus_opts.isvalid:
            with open(fn, 'w') as fp:
                fp.write(self.phosphorus_opts.contents)

        if _exists(fn):
            if not validate_phosphorus_txt(fn):
                os.remove(fn)

    def _prep_snow(self):
        fn = _join(self.runs_dir, 'snow.txt')
        with open(fn, 'w') as fp:
            fp.write(self.snow_opts.contents)

    def _prep_baseflow(self):
        fn = _join(self.runs_dir, 'gwcoeff.txt')
        with open(fn, 'w') as fp:
            fp.write(self.baseflow_opts.contents)

    def clean(self):
        if _exists(self.status_log):
            os.remove(self.status_log)

        runs_dir = self.runs_dir
        if _exists(runs_dir):
            shutil.rmtree(runs_dir)
        os.mkdir(runs_dir)

        output_dir = self.output_dir
        if _exists(output_dir):
            shutil.rmtree(output_dir)
        os.mkdir(output_dir)

        plot_dir = self.plot_dir
        if _exists(plot_dir):
            shutil.rmtree(plot_dir)
        os.mkdir(plot_dir)

        stats_dir = self.stats_dir
        if _exists(stats_dir):
            shutil.rmtree(stats_dir)
        os.mkdir(stats_dir)

        fp_runs_dir = self.fp_runs_dir
        if _exists(fp_runs_dir):
            shutil.rmtree(fp_runs_dir)
        os.makedirs(fp_runs_dir)

        fp_output_dir = self.fp_output_dir
        if _exists(fp_output_dir):
            shutil.rmtree(fp_output_dir)
        os.mkdir(fp_output_dir)

    def _prep_slopes(self, translator):
        watershed = Watershed.getInstance(self.wd)
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, _ in watershed.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))

            src_fn = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            shutil.copyfile(src_fn, dst_fn)

            # use getattr for old runs that don't have a run_flowpaths attribute
            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    fn = '{}.slp'.format(fp)
                    src_fn = _join(wat_dir, fn)
                    dst_fn = _join(fp_runs_dir, fn)
                    shutil.copyfile(src_fn, dst_fn)

    def _prep_managements(self, translator):
        landuse = Landuse.getInstance(self.wd)
        years = Climate.getInstance(self.wd).input_years
        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, man_summary in landuse.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.man' % wepp_id)

            management = man_summary.get_management()
            multi = management.build_multiple_year_man(years)
            fn_contents = str(multi)

            with open(dst_fn, 'w') as fp:
                fp.write(fn_contents)

            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    dst_fn = _join(fp_runs_dir, '{}.man'.format(fp))

                    with open(dst_fn, 'w') as fp:
                        fp.write(fn_contents)

    def _prep_soils(self, translator):
        soils = Soils.getInstance(self.wd)
        soils_dir = self.soils_dir
        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, soil in soils.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            src_fn = _join(soils_dir, soil.fname)
            dst_fn = _join(runs_dir, 'p%i.sol' % wepp_id)
            shutil.copyfile(src_fn, dst_fn)

            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    dst_fn = _join(fp_runs_dir, '{}.sol'.format(fp))
                    shutil.copyfile(src_fn, dst_fn)

    def _prep_climates(self, translator):
        watershed = Watershed.getInstance(self.wd)
        climate = Climate.getInstance(self.wd)
        cli_dir = self.cli_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, _ in watershed.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.cli' % wepp_id)

            cli_summary = climate.sub_summary(topaz_id)
            cli_path = _join(cli_dir, cli_summary['cli_fn'])
            shutil.copyfile(cli_path, dst_fn)

            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    dst_fn = _join(fp_runs_dir, '{}.cli'.format(fp))
                    shutil.copyfile(cli_path, dst_fn)

    def _make_hillslope_runs(self, translator):
        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        climate = Climate.getInstance(self.wd)
        years = climate.input_years

        if climate.is_single_storm:
            for topaz_id, _ in watershed.sub_iter():
                wepp_id = translator.wepp(top=int(topaz_id))

                make_ss_hillslope_run(wepp_id, runs_dir)

                if getattr(self, 'run_flowpaths', False):
                    for fp in watershed.fps_summary(topaz_id):
                        make_ss_hillslope_run(fp, fp_runs_dir)
        else:
            for topaz_id, _ in watershed.sub_iter():
                wepp_id = translator.wepp(top=int(topaz_id))

                make_hillslope_run(wepp_id, years, runs_dir)

                if getattr(self, 'run_flowpaths', False):
                    for fp in watershed.fps_summary(topaz_id):
                        make_flowpath_run(fp, years, fp_runs_dir)

    def run_hillslopes(self):
        self.log('Running Hillslopes\n')
        translator = Watershed.getInstance(self.wd).translator_factory()
        watershed = Watershed.getInstance(self.wd)
        topaz = Topaz.getInstance(self.wd)
        runs_dir = os.path.abspath(self.runs_dir)
        fp_runs_dir = self.fp_runs_dir
        run_flowpaths = getattr(self, 'run_flowpaths', False)
        wepp_bin = self.wepp_bin

        self.log('    wepp_bin:{}'.format(wepp_bin))

        pool = ThreadPoolExecutor(NCPU)
        futures = []

        def oncomplete(wepprun):
            status, _id, elapsed_time = wepprun.result()
            assert status
            self.log('  {} completed run in {}s\n'.format(_id, elapsed_time))

        sub_n = watershed.sub_n
        for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
            self.log('  submitting topaz={} (hill {} of {})\n'.format(topaz_id, i+1, sub_n))
            wepp_id = translator.wepp(top=int(topaz_id))
            futures.append(pool.submit(lambda p: run_hillslope(*p), (wepp_id, runs_dir, wepp_bin)))
            futures[-1].add_done_callback(oncomplete)

            # run flowpaths if specified
            if run_flowpaths:

                # iterate over the flowpath ids
                fps_summary = watershed.fps_summary(topaz_id)
                fp_n = len(fps_summary)
                for j, fp in enumerate(fps_summary):
                    self.log('    submitting flowpath={} (hill {} of {}, fp {} of {})... '
                             .format(fp, i+1, sub_n, j + 1, fp_n))

                    # run wepp for flowpath
                    futures.append(pool.submit(lambda p: run_flowpath(*p), (fp, fp_runs_dir, wepp_bin)))
                    futures[-1].add_done_callback(oncomplete)

                    self.log_done()

        wait(futures, return_when=FIRST_EXCEPTION)

        # Flowpath post-processing
        if run_flowpaths:
            self.log('    building loss grid')

            # data structure to contain flowpath soil loss results
            # keys are (x, y) pixel locations
            # values are lists of soil loss/deposition from flow paths
            loss_grid_d = {}

            for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
                fps_summary = watershed.fps_summary(topaz_id)
                for j, fp in enumerate(fps_summary):

                    # read plot file data
                    plo = PlotFile(_join(self.fp_output_dir, '%s.plot.dat' % fp))

                    # interpolate soil loss to cell locations of flowpath
                    d = fps_summary[fp].distance_p
                    loss = plo.interpolate(d)

                    # store non-zero values in loss_grid_d
                    for L, coord in zip(loss, fps_summary[fp].coords):
                        if L != 0.0:
                            if coord in loss_grid_d:
                                loss_grid_d[coord].append(L)
                            else:
                                loss_grid_d[coord] = [L]

            self.log_done()

            self.log('Processing flowpaths... ')

            self._pickle_loss_grid_d(loss_grid_d)
            self.make_loss_grid()

            self.log_done()

    def _pickle_loss_grid_d(self, loss_grid_d):
        plot_dir = self.plot_dir
        loss_grid_d_path = _join(plot_dir, 'loss_grid_d.pickle')

        with open(loss_grid_d_path, 'wb') as fp:
            pickle.dump(loss_grid_d, fp)

        self.lock()

        # noinspection PyBroadException
        try:
            self.loss_grid_d_path = loss_grid_d_path
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def loss_grid_d(self):
        loss_grid_d_path = self.loss_grid_d_path

        assert loss_grid_d_path is not None
        assert _exists(loss_grid_d_path)

        with open(loss_grid_d_path, 'rb') as fp:
            _loss_grid_d = pickle.load(fp)

        return _loss_grid_d

    #
    # watershed
    #
    def prep_watershed(self, erodibility=None, critical_shear=None,
                       tcr=None):
        self.log('Prepping Watershed... ')

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        self._prep_structure(translator)
        self._prep_channel_slopes()
        self._prep_channel_chn(translator, erodibility, critical_shear)
        self._prep_impoundment()
        self._prep_channel_soils(translator, erodibility, critical_shear)
        self._prep_channel_climate(translator)
        self._prep_channel_input()

        if (tcr is None and self.run_tcr) or tcr:
            self._prep_tcr()

        self._prep_watershed_managements(translator)
        self._make_watershed_run(translator)

        self.log_done()

        self.trigger(TriggerEvents.WEPP_PREP_WATERSHED_COMPLETE)

    def _prep_structure(self, translator):
        watershed = Watershed.getInstance(self.wd)
        structure = watershed.structure
        runs_dir = self.runs_dir

        s = ['99.1']
        for L in structure:
            s2 = "2    {} {} {}   "\
                 .format(*[translator.wepp(top=v) for v in L[1:4]])

            s2 += "{} {} {}   {} {} {}"\
                  .format(*[translator.wepp(top=v) for v in L[4:]])
#                .format(*[translator.chn_enum(top=v) for v in L[4:]])

            s.append(s2)

        with open(_join(runs_dir, 'pw0.str'), 'w') as fp:
            fp.write('\n'.join(s) + '\n')

    def _prep_channel_slopes(self):
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir

        shutil.copyfile(_join(wat_dir, 'channels.slp'),
                        _join(runs_dir, 'pw0.slp'))

    def _prep_channel_chn(self, translator, erodibility, critical_shear,
                          channel_routing_method=ChannelRoutingMethod.MuskingumCunge):

        if erodibility is not None or critical_shear is not None:
            self.log('nodb.Wepp._prep_channel_chn::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))
            self.log_done()

        assert translator is not None

        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir

        chn_n = watershed.chn_n

        fp = open(_join(runs_dir, 'pw0.chn'), 'w')

        if channel_routing_method == ChannelRoutingMethod.MuskingumCunge:
            fp.write('99.1\r\n{chn_n}\r\n4\r\n1.500000\r\n'
                     .format(chn_n=chn_n))
        else:
            fp.write('99.1\r\n{chn_n}\r\n2\r\n1.00000\r\n'
                     .format(chn_n=chn_n))

        for topaz_id, chn_summary in watershed.chn_iter():
            chn_key = chn_summary.channel_type
            chn_d = get_channel(chn_key, erodibility, critical_shear)
            contents = chn_d['contents']

            fp.write(contents)
            fp.write('\n')
        fp.close()

    def _prep_impoundment(self):
        runs_dir = self.runs_dir
        with open(_join(runs_dir, 'pw0.imp'), 'w') as fp:
            fp.write('99.1\n0\n')

    def _prep_channel_input(self):

        wat = Watershed.getInstance(self.wd)
        chn_n = wat.chn_n
        sub_n = wat.sub_n
        total = chn_n + sub_n

        runs_dir = self.runs_dir
        with open(_join(runs_dir, 'chan.inp'), 'w') as fp:
            fp.write('1 600\n0\n1\n{}\n'.format(total))

    def _prep_channel_soils(self, translator, erodibility, critical_shear):
        if erodibility is not None or critical_shear is not None:
            self.log('nodb.Wepp._prep_channel_soils::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))
            self.log_done()

        soils = Soils.getInstance(self.wd)
        soils_dir = self.soils_dir
        runs_dir = self.runs_dir

        watershed = Watershed.getInstance(self.wd)
        chn_n = watershed.chn_n

        translator = watershed.translator_factory()
        outlet_chn_enum = translator.chn_enum(top=watershed.outlet_top_id)

        # build list of soils
        soil_c = []
        for topaz_id, soil in soils.chn_iter():
            soil_c.append((translator.chn_enum(top=int(topaz_id)), soil))
        soil_c.sort(key=lambda x: x[0])
        #
        # versions = []
        # for chn_enum, soil in soil_c:
        #     soil_fn = _join(soils_dir, soil.fname)
        #     lines = open(soil_fn).readlines()
        #     version = lines[0].replace('#', '').strip()
        #     versions.append(version)
        #
        # versions = set(versions)
        # if len(versions) > 1:
        #     raise Exception('Do not know how to merge '
        #                     'soils of different versions')
        #
        # if len(versions) == 0:
        #     raise Exception('Could not find any soils for channels.')
        #
        # version = versions.pop()

        if erodibility is None:
            erodibility = 1E-6
        if critical_shear is None:
            critical_shear = 50.0

        # iterate over soils and append them together
        fp = open(_join(runs_dir, 'pw0.sol'), 'w')
        fp.write('7778.0\ncomments: soil file\n{chn_n} 1\n'
                 .format(chn_n=chn_n))
        i = 0
        for chn_enum, soil in soil_c:
            soil_fn = _join(soils_dir, soil.fname)

            with open(soil_fn) as fp2:
                contents = fp2.read()
                is_water = 'water' in contents.lower()

            fp.write("""\
Bidart_1 MPM 1 0.02 0.75 4649000 {erodibility} {critical_shear}
    400	1.5	0.5	1	0.242	0.1145	66.8	7	3	11.3	20
1 10000 0.0001
""".format(erodibility=erodibility, critical_shear=critical_shear))

        fp.close()

    def _prep_watershed_managements(self, translator):
        landuse = Landuse.getInstance(self.wd)
        runs_dir = self.runs_dir

        years = Climate.getInstance(self.wd).input_years

        """
        # build list of managements
        mans_c = []
        for topaz_id, man in landuse.chn_iter():
            man_obj = get_management(man.key)
            chn_enum = translator.chn_enum(top=int(topaz_id))
            mans_c.append((chn_enum, man_obj))
            
        # sort list of (chn_enum, Management) by chn_enum
        mans_c.sort(key=lambda x: x[0]) 
        mans_c = [v for k, v in mans_c]  # <- list of Management
        
        if len(mans_c) > 1:
            chn_man = merge_managements(mans_c)
        else:
            chn_man = mans_c[0]
            
        """

        # Look at all the channel managements and use the most common channel type for all the channels
        keys = [man.key for topaz_id, man in landuse.chn_iter()]
        from collections import Counter
        mankey = Counter(keys).most_common()[0][0]

        chn_man = landuse.managements[str(mankey)].get_management()
        if len(keys) > 1:
            chn_man.make_multiple_ofe(len(keys))

        if years > 1:
            multi = chn_man.build_multiple_year_man(years)
            fn_contents = str(multi)
        else:
            fn_contents = str(chn_man)

        with open(_join(runs_dir, 'pw0.man'), 'w') as fp:
            fp.write(fn_contents)

    def _prep_channel_climate(self, translator):
        assert translator is not None

        runs_dir = self.runs_dir
        climate = Climate.getInstance(self.wd)
        dst_fn = _join(runs_dir, 'pw0.cli')
        cli_path = _join(self.cli_dir, climate.cli_fn)
        shutil.copyfile(cli_path, dst_fn)

    def _make_watershed_run(self, translator):
        runs_dir = self.runs_dir
        wepp_ids = list(translator.iter_wepp_sub_ids())
        wepp_ids.sort()

        climate = Climate.getInstance(self.wd)
        years = climate.input_years

        if climate.is_single_storm:
            make_ss_watershed_run(wepp_ids, runs_dir)
        else:
            make_watershed_run(years, wepp_ids, runs_dir)

    def run_watershed(self):
        wd = self.wd
        self.log('Running Watershed... ')

        self.log('    wepp_bin:{}'.format(self.wepp_bin))

        runs_dir = self.runs_dir
        assert run_watershed(runs_dir, self.wepp_bin)

        for fn in glob(_join(self.runs_dir, '*.out')):
            dst_path = _join(self.output_dir, _split(fn)[1])
            shutil.move(fn, dst_path)

        if not _exists(_join(wd, 'wepppost.nodb')):
            WeppPost(wd, '0.cfg')

        self.log_done()

        climate = Climate.getInstance(wd)

        if climate.climate_mode != ClimateMode.SingleStorm:
            self.log('Building totalsedwat.txt... ')
            self._build_totalsedwat()
            self.log_done()

            self.log('Running WeppPost... ')
            wepppost = WeppPost.getInstance(wd)
            wepppost.run_post()
            self.log_done()

            self.log('Calculating hill streamflow measures... ')
            wepppost.calc_hill_streamflow()
            self.log_done()

            self.log('Calculating channel streamflow measures... ')
            wepppost.calc_channel_streamflow()
            self.log_done()

    def _build_totalsedwat(self):
        output_dir = self.output_dir
        erin_pl = _join(output_dir, 'correct_daily_hillslopes.pl')
        if not _exists(erin_pl):
            shutil.copyfile(correct_daily_hillslopes_pl_path, erin_pl)

        cmd = ['perl', 'correct_daily_hillslopes.pl']
        _log = open(_join(output_dir, 'correct_daily_hillslopes.log'), 'w')

        p = Popen(cmd, stdout=_log, stderr=_log, cwd=output_dir)
        p.wait()
        _log.close()

        totalwatsed_fn = _join(output_dir, 'totalwatsed.txt')
        assert _exists(totalwatsed_fn), 'Failed running correct_daily_hillslopes.pl'
        assert os.stat(totalwatsed_fn).st_size > 0, 'totalwatsed.txt is empty'

    def report_loss(self, exclude_yr_indxs=None):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        return Loss(loss_pw0, self.has_phosphorus, self.wd, exclude_yr_indxs=exclude_yr_indxs)

    def report_return_periods(self, rec_intervals=(25, 20, 10, 5, 2)):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        loss_rpt = Loss(loss_pw0, self.has_phosphorus, self.wd)

        print(1)

        ebe_pw0 = _join(output_dir, 'ebe_pw0.txt')
        ebe_rpt = Ebe(ebe_pw0)

        print(2)

        climate = Climate.getInstance(self.wd)
        print(3)

        cli = ClimateFile(_join(climate.cli_dir, climate.cli_fn))

        print(4, _join(climate.cli_dir, climate.cli_fn))

        cli_df = cli.as_dataframe(calc_peak_intensities=True)

        print(3)

        return ReturnPeriods(ebe_rpt, loss_rpt, cli_df, recurrence=rec_intervals)

    def report_frq_flood(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        loss_rpt = Loss(loss_pw0, self.has_phosphorus, self.wd)

        ebe_pw0 = _join(output_dir, 'ebe_pw0.txt')
        ebe_rpt = Ebe(ebe_pw0)

        return FrqFlood(ebe_rpt, loss_rpt)

    def report_sediment_delivery(self):
        return SedimentDelivery(self.wd)

    def report_hill_watbal(self):
        return HillslopeWatbal(self.wd)

    def report_chn_watbal(self):
        return ChannelWatbal(self.wd)

    def set_run_flowpaths(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self.run_flowpaths = state
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_run_wepp_ui(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self._run_wepp_ui = state
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_run_pmet(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self._run_pmet = state
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_run_frost(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self._run_frost = state
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_run_tcr(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self._run_tcr = state
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_run_baseflow(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self._run_baseflow = state
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def query_sub_val(self, measure):
        wd = self.wd

        translator = Watershed.getInstance(wd).translator_factory()
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')

        report = Loss(loss_pw0, self.has_phosphorus, self.wd)

        d = {}
        for row in report.hill_tbl:
            topaz_id = translator.top(wepp=row['Hillslopes'])

            v = row[measure]
            if isnan(v) or isinf(v):
                v = None

            d[str(topaz_id)] = dict(
                topaz_id=topaz_id,
                value=v
            )

        return d

    def query_chn_val(self, measure):
        wd = self.wd

        translator = Watershed.getInstance(wd).translator_factory()
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')

        report = Loss(loss_pw0, self.has_phosphorus, self.wd)

        d = {}
        for row in report.chn_tbl:
            topaz_id = translator.top(chn_enum=row['Channels and Impoundments'])

            v = row[measure]
            if isnan(v) or isinf(v):
                v = None

            d[str(topaz_id)] = dict(
                topaz_id=topaz_id,
                value=v
            )

        return d

    def make_loss_grid(self):
        bound, transform, proj = read_arc(self.bound_arc, dtype=np.int32)

        num_cols, num_rows = bound.shape
        loss_grid = np.zeros((num_cols, num_rows))

        _loss_grid_d = self.loss_grid_d
        for (x, y) in _loss_grid_d:
            loss = np.mean(np.array(_loss_grid_d[(x, y)]))
            loss_grid[x, y] = loss

        indx = np.where(bound == 0.0)
        loss_grid[indx] = -9999

        loss_grid_path = _join(self.plot_dir, 'loss.tif')
        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(loss_grid_path, num_cols, num_rows,
                            1, GDT_Float32)

        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj)
        wkt = srs.ExportToWkt()

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform)
        band = dst.GetRasterBand(1)
        band.SetNoDataValue(-1e38)
        band.WriteArray(loss_grid.T)
        del dst

        assert _exists(loss_grid_path)

        loss_grid_wgs = _join(self.plot_dir, 'loss.WGS.tif')

        if _exists(loss_grid_wgs):
            os.remove(loss_grid_wgs)
            time.sleep(1)

        cmd = ['gdalwarp', '-t_srs', wgs84_proj4,
               '-srcnodata', '-9999', '-dstnodata', '-9999',
               '-r', 'near', loss_grid_path, loss_grid_wgs]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(loss_grid_wgs)
