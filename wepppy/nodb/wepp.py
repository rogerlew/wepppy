# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import os
from enum import IntEnum
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from subprocess import Popen, PIPE, call
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION

import time

import pickle
from copy import deepcopy
from glob import glob

import shutil

from time import sleep

# non-standard
import jsonpickle

import numpy as np

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *

from wepppy.wepp.soils.utils import modify_kslast

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
    pmetpara_prep,
    get_channel_management
)


from wepppy.all_your_base import (
    isfloat,
    isnan,
    isinf,
    NCPU,
    IS_WINDOWS
)
from wepppy.all_your_base.geo import read_raster, wgs84_proj4, RasterDatasetInterpolator

from wepppy.wepp.out import (
    Loss,
    Ebe,
    PlotFile,
    correct_daily_hillslopes_pl_path
)

from wepppy.wepp.stats import ChannelWatbal, HillslopeWatbal, ReturnPeriods, SedimentDelivery

# wepppy submodules
from wepppy.wepp.stats.frq_flood import FrqFlood
from .base import (
    NoDbBase, 
    TriggerEvents
)

from .landuse import Landuse
from .soils import Soils
from .climate import Climate, ClimateMode
from .watershed import Watershed
from .wepppost import WeppPost
from wepppy.nodb.mixins.log_mixin import LogMixin


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
        elif 'snow_opts_rst' in kwds:
            self.rst = float(kwds['snow_opts_rst'])

        if 'newsnw' in kwds:
            self.newsnw = float(kwds['newsnw'])
        elif 'snow_opts_newsnw' in kwds:
            self.newsnw = float(kwds['snow_opts_newsnw'])

        if 'ssd' in kwds:
            self.ssd = float(kwds['ssd'])
        elif 'snow_opts_ssd' in kwds:
            self.ssd = float(kwds['snow_opts_ssd'])

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

            surf_runoff = self.config_get_float('phosphorus_opts', 'surf_runoff')
            lateral_flow = self.config_get_float('phosphorus_opts', 'lateral_flow')
            baseflow = self.config_get_float('phosphorus_opts', 'baseflow')
            sediment = self.config_get_float('phosphorus_opts', 'sediment')

            self.phosphorus_opts = PhosphorusOpts(
                surf_runoff=surf_runoff,
                lateral_flow=lateral_flow,
                baseflow=baseflow,
                sediment=sediment)

            self.p_surf_runoff_map = self.config_get_path('phosphorus_opts', 'surf_runoff_map')
            self.p_lateral_flow_map = self.config_get_path('phosphorus_opts', 'lateral_flow_map')
            self.p_baseflow_map = self.config_get_path('phosphorus_opts', 'baseflow_map')
            self.p_sediment_map = self.config_get_path('phosphorus_opts', 'sediment_map')

            snow_rst = self.config_get_float('snow_opts', 'rst')
            snow_newsnw = self.config_get_float('snow_opts', 'newsnw')
            snow_ssd = self.config_get_float('snow_opts', 'ssd')

            _wepp_ui = self.config_get_bool('wepp', 'wepp_ui')
            _pmet = self.config_get_bool('wepp', 'pmet')
            _frost = self.config_get_bool('wepp', 'frost')
            _tcr = self.config_get_bool('wepp', 'tcr')

            baseflow_gwstorage = self.config_get_float('baseflow_opts', 'gwstorage')
            baseflow_bfcoeff = self.config_get_float('baseflow_opts', 'bfcoeff')
            baseflow_dscoeff = self.config_get_float('baseflow_opts', 'dscoeff')
            baseflow_bfthreshold = self.config_get_float('baseflows_opts', 'bfthreshold')

            self.baseflow_opts = BaseflowOpts(
                gwstorage=baseflow_gwstorage,
                bfcoeff=baseflow_bfcoeff,
                dscoeff=baseflow_dscoeff,
                bfthreshold=baseflow_bfthreshold)

            self.baseflow_gwstorage_map = self.config_get_path('baseflow_opts', 'gwstorage_map')
            self.baseflow_bfcoeff_map = self.config_get_path('baseflow_opts', 'bfcoeff_map')
            self.baseflow_dscoeff_map = self.config_get_path('baseflow_opts', 'dscoeff_map')
            self.baseflow_bfthreshold_map = self.config_get_path('baseflow_opts', 'bfthreshold_map')

            _baseflow = self.config_get_bool('wepp', 'baseflow')
            _snow = self.config_get_bool('wepp', 'snow')

            _channel_erodibility = self.config_get_float('wepp', 'channel_erodibility')
            _channel_critical_shear = self.config_get_float('wepp', 'channel_critical_shear')

            self.channel_critical_shear_map = self.config_get_path('wepp', 'channel_critical_shear_map')

            _kslast = self.config_get_float('wepp', 'kslast')

            _wepp_bin = self.config_get_str('wepp', 'bin')

            self._run_wepp_ui = _wepp_ui
            self._run_pmet = _pmet
            self._run_frost = _frost
            self._run_tcr = _tcr
            self._run_baseflow = _baseflow
            self._run_snow = _snow
            self._wepp_bin = _wepp_bin
            self._channel_erodibility = _channel_erodibility
            self._channel_critical_shear = _channel_critical_shear
            self._kslast = _kslast

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
                db.wd = os.path.abspath(wd)
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
        return getattr(self, '_run_tcr', self.config_get_bool('wepp', 'tcr'))

    @property
    def run_wepp_ui(self):
        return getattr(self, '_run_wepp_ui', self.config_get_bool('wepp', 'wepp_ui'))

    @property
    def run_pmet(self):
        return getattr(self, '_run_pmet', self.config_get_bool('wepp', 'pmet'))

    @property
    def run_frost(self):
        return getattr(self, '_run_frost', self.config_get_bool('wepp', 'frost'))

    @property
    def run_baseflow(self):
        return getattr(self, '_run_baseflow', self.config_get_bool('wepp', 'baseflow'))

    @property
    def run_snow(self):
        return getattr(self, '_run_snow', self.config_get_bool('wepp', 'snow'))

    @property
    def channel_erodibility(self):
        return getattr(self, '_channel_erodibility', self.config_get_float('wepp', 'channel_erodibility'))

    @property
    def channel_critical_shear(self):
        return getattr(self, '_channel_critical_shear', self.config_get_float('wepp', 'channel_critical_shear'))

    @property
    def channel_2006_avke(self):
        return getattr(self, '_channel_2006_avke', self.config_get_float('wepp', 'channel_2006_avke'))

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

            if hasattr(self, 'snow_opts'):
                self.snow_opts.parse_inputs(kwds)

            _channel_critical_shear = kwds.get('channel_critical_shear', None)
            if isfloat(_channel_critical_shear):
                self._channel_critical_shear = float(_channel_critical_shear)

            _channel_erodibility = kwds.get('channel_erodibility', None)
            if isfloat(_channel_erodibility):
                self._channel_erodibility = float(_channel_erodibility)

            _kslast = kwds.get('kslast', '')
            if isfloat(_kslast):
                self._kslast = float(_kslast)
            elif _kslast.lower().startswith('none') or _kslast == '':
                self._kslast = None

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
        self._modify_soils_kslast()
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

    @property
    def sol_versions(self):
        sol_versions = set()

        sol_fns = glob(_join(self.runs_dir, '*.sol'))
        if len(sol_fns) == 0:
            raise Exception('Soils have not been prepped')

        for sol_fn in sol_fns:
            with open(sol_fn) as fp:
                for line in fp.readlines():
                    line = line.strip()
                    if line.startswith('#'):
                        continue

                    if line == '':
                        continue

                    sol_versions.add(line)
                    break

        return sol_versions

    def _prep_wepp_ui(self):

        for sol_version in self.sol_versions:
            if '2006' in sol_version:
                return

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

        # get references to PhosphorusOpts
        phos_opts = self.phosphorus_opts

        # check to see if p maps are available
        p_surf_runoff_map = getattr(self, 'p_surf_runoff_map', None)
        p_lateral_flow_map = getattr(self, 'p_lateral_flow_map', None)
        p_baseflow_map = getattr(self, 'p_baseflow_map', None)
        p_sediment_map = getattr(self, 'p_sediment_map', None)

        # if the maps are available read the p parameters from the maps
        watershed = Watershed.getInstance(self.wd)
        lng, lat = watershed.outlet.actual_loc
        
        if p_surf_runoff_map is not None:
            p_surf_runoff = RasterDatasetInterpolator(p_surf_runoff_map).get_location_info(lng, lat, method='nearest')
            if p_surf_runoff > 0.0:
                self.log('wepp:_prep_phosphorus setting surf_runoff to {} from map'.format(p_surf_runoff))
                phos_opts.surf_runoff = float(p_surf_runoff)
                self.log_done()
            
        if p_lateral_flow_map is not None:
            p_lateral_flow = RasterDatasetInterpolator(p_lateral_flow_map).get_location_info(lng, lat, method='nearest')
            if p_lateral_flow > 0.0:
                self.log('wepp:_prep_phosphorus setting lateral_flow to {} from map'.format(p_lateral_flow))
                phos_opts.lateral_flow = float(p_lateral_flow)
                self.log_done()

        if p_baseflow_map is not None: 
            p_baseflow = RasterDatasetInterpolator(p_baseflow_map).get_location_info(lng, lat, method='nearest')
            if p_baseflow > 0.0:
                self.log('wepp:_prep_phosphorus setting baseflow to {} from map'.format(p_baseflow))
                phos_opts.baseflow = float(p_baseflow)
                self.log_done()

        if  p_sediment_map is not None:
            p_sediment = RasterDatasetInterpolator(p_sediment_map).get_location_info(lng, lat, method='nearest')
            if p_sediment > 0.0:
                self.log('wepp:_prep_phosphorus setting sediment to {} from map'.format(p_sediment))
                phos_opts.sediment = float(p_sediment)
                self.log_done()

        # save the phosphorus parameters to the .nodb
        self.lock()

        # noinspection PyBroadException
        try:
            self.phosphorus_opts = phos_opts
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        # create the phosphorus.txt file
        fn = _join(self.runs_dir, 'phosphorus.txt')
        if phos_opts.isvalid:
            with open(fn, 'w') as fp:
                fp.write(phos_opts.contents)

        # make sure the file exists and validate the file
        if _exists(fn):
            if not validate_phosphorus_txt(fn):
                os.remove(fn)

    def _prep_snow(self):
        fn = _join(self.runs_dir, 'snow.txt')
        with open(fn, 'w') as fp:
            fp.write(self.snow_opts.contents)

    def _prep_baseflow(self):
        baseflow_opts = self.baseflow_opts

        gwstorage_map = getattr(self, 'baseflow_gwstorage_map', None)
        bfcoeff_map = getattr(self, 'baseflow_bfcoeff_map', None)
        dscoeff_map = getattr(self, 'baseflow_dscoeff_map', None)
        bfthreshold_map = getattr(self, 'baseflow_bfthreshold_map', None)

        watershed = Watershed.getInstance(self.wd)
        lng, lat = watershed.outlet.actual_loc

        if gwstorage_map is not None:
            gwstorage = RasterDatasetInterpolator(gwstorage_map).get_location_info(lng, lat, method='nearest')
            if gwstorage >= 0.0:
                self.log('wepp:_prep_baseflow setting gwstorage to {} from map'.format(gwstorage))
                baseflow_opts.gwstorage = float(gwstorage)
                self.log_done()

        if bfcoeff_map is not None:
            bfcoeff = RasterDatasetInterpolator(bfcoeff_map).get_location_info(lng, lat, method='nearest')
            if bfcoeff >= 0.0:
                self.log('wepp:_prep_baseflow setting bfcoeff to {} from map'.format(bfcoeff))
                baseflow_opts.bfcoeff = float(bfcoeff)
                self.log_done()

        if dscoeff_map is not None:
            dscoeff = RasterDatasetInterpolator(dscoeff_map).get_location_info(lng, lat, method='nearest')
            if dscoeff >= 0.0:
                self.log('wepp:_prep_baseflow setting dscoeff to {} from map'.format(dscoeff))
                baseflow_opts.dscoeff = float(dscoeff)
                self.log_done()

        if bfthreshold_map is not None:
            bfthreshold = RasterDatasetInterpolator(bfthreshold_map).get_location_info(lng, lat, method='nearest')
            if bfthreshold >= 0.0:
                self.log('wepp:_prep_baseflow setting bfthreshold to {} from map'.format(bfthreshold))
                baseflow_opts.bfthreshold = float(bfthreshold)
                self.log_done()

        # save the baseflow parameters to the .nodb
        self.lock()

        # noinspection PyBroadException
        try:
            self.baseflow_opts = baseflow_opts
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        fn = _join(self.runs_dir, 'gwcoeff.txt')
        with open(fn, 'w') as fp:
            fp.write(baseflow_opts.contents)

    def clean(self):
        if _exists(self.status_log):
            os.remove(self.status_log)

        for _dir in (self.runs_dir, self.output_dir, self.plot_dir,
                     self.stats_dir, self.fp_runs_dir, self.fp_output_dir):
            if _exists(_dir):
                try:
                    shutil.rmtree(_dir)
                except:
                    sleep(10.0)
                    try:
                        shutil.rmtree(_dir, ignore_errors=True)
                    except:
                        pass

            if not _exists(_dir):
                os.makedirs(_dir)

    def _prep_slopes(self, translator):
        watershed = Watershed.getInstance(self.wd)
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, _ in watershed.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))

            src_fn = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            
            if IS_WINDOWS:
                shutil.copyfile(src_fn, dst_fn)
            else:
                os.link(src_fn, dst_fn)

            # use getattr for old runs that don't have a run_flowpaths attribute
            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    fn = '{}.slp'.format(fp)
                    src_fn = _join(wat_dir, fn)
                    dst_fn = _join(fp_runs_dir, fn)
                    if IS_WINDOWS:
                        shutil.copyfile(src_fn, dst_fn)
                    else:
                        os.link(src_fn, dst_fn)

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
                for flowpath in watershed.fps_summary(topaz_id):
                    dst_fn = _join(fp_runs_dir, '{}.man'.format(flowpath))

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

            if IS_WINDOWS:
                shutil.copyfile(src_fn, dst_fn)
            else:
                os.link(src_fn, dst_fn)

            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    dst_fn = _join(fp_runs_dir, '{}.sol'.format(fp))

                    if IS_WINDOWS:
                        shutil.copyfile(src_fn, dst_fn)
                    else:
                        os.link(src_fn, dst_fn)

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
            src_fn = _join(cli_dir, cli_summary['cli_fn'])

            if IS_WINDOWS:
                shutil.copyfile(src_fn, dst_fn)
            else:
                os.link(src_fn, dst_fn)

            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    dst_fn = _join(fp_runs_dir, '{}.cli'.format(fp))

                    if IS_WINDOWS:
                        shutil.copyfile(src_fn, dst_fn)
                    else:
                        os.link(src_fn, dst_fn)

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
                       tcr=None, avke=None):
        self.log('Prepping Watershed... ')

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        if critical_shear is None:
            crit_shear_map = getattr(self, 'channel_critical_shear_map', None)
            if crit_shear_map is not None:
                lng, lat = watershed.outlet.actual_loc
                crit_shear = RasterDatasetInterpolator(crit_shear_map).get_location_info(lng, lat, method='nearest')
                if crit_shear > 0.0:
                    self.log('wepp:prep_watershed setting critical shear to {} from map'.format(crit_shear))
                    critical_shear = crit_shear
                    self.log_done()

        self._prep_structure(translator)
        self._prep_channel_slopes()
        self._prep_channel_chn(translator, erodibility, critical_shear)
        self._prep_impoundment()
        self._prep_channel_soils(translator, erodibility, critical_shear, avke)
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

        src_fn = _join(wat_dir, 'channels.slp')
        dst_fn = _join(runs_dir, 'pw0.slp')

        if IS_WINDOWS:
            shutil.copyfile(src_fn, dst_fn)
        else:
            os.link(src_fn, dst_fn)

    def _prep_channel_chn(self, translator, erodibility, critical_shear,
                          channel_routing_method=ChannelRoutingMethod.MuskingumCunge):

        if erodibility is not None or critical_shear is not None:
            self.log('nodb.Wepp._prep_channel_chn::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))
            self.log_done()

        if erodibility is None:
            erodibility = self.channel_erodibility

        if critical_shear is None:
            critical_shear = self.channel_critical_shear

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
            # 1 is the Peak Flow time and rate, 600s is the interval
            # 2 Daily average discharge, 600 probably doesn't do anything
            fp.write('1 600\n0\n1\n{}\n'.format(total))

    def _prep_channel_soils(self, translator, erodibility, critical_shear, avke=None):

        write_7778 = True
        for sol_version in self.sol_versions:
            if '2006' in sol_version:
                write_7778 = False

        if write_7778:
            self._prep_7778_channel_soils(erodibility, critical_shear)
        else:
            self._prep_2006_channel_soils(translator, erodibility, critical_shear, avke)

    def _prep_7778_channel_soils(self, erodibility, critical_shear):
        if erodibility is not None or critical_shear is not None:
            self.log('nodb.Wepp._prep_channel_soils::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))
            self.log_done()

        if erodibility is None:
            erodibility = self.channel_erodibility

        if critical_shear is None:
            critical_shear = self.channel_critical_shear

        runs_dir = self.runs_dir

        watershed = Watershed.getInstance(self.wd)
        chn_n = watershed.chn_n

        assert isfloat(erodibility)
        assert isfloat(critical_shear)

        # iterate over soils and append them together
        fp = open(_join(runs_dir, 'pw0.sol'), 'w')
        fp.write('7778.0\ncomments: soil file\n{chn_n} 1\n'
                 .format(chn_n=chn_n))

        for i in range(chn_n):
            fp.write('Bidart_1 MPM 1 0.02 0.75 4649000 {erodibility} {critical_shear}\n'
                     .format(erodibility=erodibility, critical_shear=critical_shear))
            fp.write('    400	1.5	0.5	1	0.242	0.1145	66.8	7	3	11.3	20\n')
            fp.write('1 10000 0.0001\n')

        fp.close()

    def _prep_2006_channel_soils(self, translator, erodibility, critical_shear, avke):
        if erodibility is not None or critical_shear is not None:
            self.log('nodb.Wepp._prep_channel_soils::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))
            self.log_done()

        if erodibility is None:
            erodibility = self.channel_erodibility

        if critical_shear is None:
            critical_shear = self.channel_critical_shear

        if avke is not None:
            self.log('nodb.Wepp._prep_channel_soils::avke = {} '
                     .format(avke))
            self.log_done()

        if avke is None:
            avke = self.channel_2006_avke

        soils = Soils.getInstance(self.wd)
        runs_dir = self.runs_dir

        watershed = Watershed.getInstance(self.wd)
        chn_n = watershed.chn_n

        # build list of soils
        soil_c = []
        for topaz_id, soil in soils.chn_iter():
            soil_c.append((translator.chn_enum(top=int(topaz_id)), soil))
        soil_c.sort(key=lambda x: x[0])

        assert isfloat(erodibility)
        assert isfloat(critical_shear)

        # iterate over soils and append them together
        fp = open(_join(runs_dir, 'pw0.sol'), 'w')
        fp.write('2006.2\ncomments: soil file\n{chn_n} 1\n'
                 .format(chn_n=chn_n))

        for chn_enum, soil in soil_c:
            _avke = soil.as_dict()['avke']
            if _avke is None:
                _avke = avke

            fp.write('Bidart_1 MPM 1 0.02 0.75 4649000 {erodibility} {critical_shear} {avke}\n'
                     .format(erodibility=erodibility, critical_shear=critical_shear, avke=_avke))
            fp.write('    400	66.8	7	3	11.3	20\n')
            fp.write('1 25 0.0001\n')

        fp.close()

    def _prep_watershed_managements(self, translator):
        landuse = Landuse.getInstance(self.wd)
        runs_dir = self.runs_dir

        years = Climate.getInstance(self.wd).input_years

        chn_n = Watershed.getInstance(self.wd).chn_n
        chn_man = get_channel_management()
        if chn_n > 1:
            chn_man.make_multiple_ofe(chn_n)

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
        src_fn = _join(self.cli_dir, climate.cli_fn)

        if IS_WINDOWS:
            shutil.copyfile(src_fn, dst_fn)
        else:
            os.link(src_fn, dst_fn)

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

        for fn in [_join(self.output_dir, 'pass_pw0.txt'),
                   _join(self.output_dir, 'soil_pw0.txt')]:
            if _exists(fn):
                 p = call('gzip %s -f' % fn, shell=True)
                 assert _exists(fn + '.gz')

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

        ebe_pw0 = _join(output_dir, 'ebe_pw0.txt')
        ebe_rpt = Ebe(ebe_pw0)

        climate = Climate.getInstance(self.wd)
        cli = ClimateFile(_join(climate.cli_dir, climate.cli_fn))
        cli_df = cli.as_dataframe(calc_peak_intensities=True)

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

    def set_run_snow(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self._run_snow = state
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

        if not _exists(loss_pw0):
            return None

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

        if not _exists(loss_pw0):
            return None

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
        watershed = Watershed.getInstance(self.wd)
        bound, transform, proj = read_raster(watershed.bound, dtype=np.int32)

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

    @property
    def kslast(self):
        if not hasattr(self, '_kslast'):
            return None

        return self._kslast

    @kslast.setter
    def kslast(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._kslast = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _modify_soils_kslast(self):
        wd = self.wd
        watershed = Watershed.getInstance(wd)

        kslast = self.kslast

        if kslast is None:
            return

        soils = Soils.getInstance(wd)

        ksat_mod = 'f'

        _domsoil_d = soils.domsoil_d
        _soils = soils.soils
        for topaz_id, ss in watershed._subs_summary.items():
            # lng, lat = ss.centroid.lnglat

            dom = _domsoil_d[str(topaz_id)]
            _soil = deepcopy(_soils[dom])

            _dom = '{dom}-{ksat_mod}' \
                .format(dom=dom, ksat_mod=ksat_mod)

            _soil.mukey = _dom

            if _dom not in _soils:
                _soil_fn = '{dom}.sol'.format(dom=_dom)
                src_soil_fn = _join(_soil.soils_dir, _soil.fname)
                dst_soil_fn = _join(_soil.soils_dir, _soil_fn)
                modify_kslast(src_soil_fn, dst_soil_fn, kslast, caller='nodb.wepp')

                _soil.fname = _soil_fn
                _soils[_dom] = _soil

            _domsoil_d[str(topaz_id)] = _dom

        soils.lock()
        soils.domsoil_d = _domsoil_d
        soils.soils = _soils
        soils.dump_and_unlock()
