# Copyright (c) 2016-2023, University of Idaho
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

import math

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
import json

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *


from wepppyo3.wepp_viz import make_soil_loss_grid



try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except:
    send_discord_message = None


# wepppy
from wepppy.climates.cligen import ClimateFile
from wepp_runner.wepp_runner import (
    make_hillslope_run,
    make_ss_hillslope_run,
    make_ss_batch_hillslope_run,
    run_hillslope,
    run_ss_batch_hillslope,
    make_watershed_run,
    make_ss_watershed_run,
    make_ss_batch_watershed_run,
    run_watershed,
    run_ss_batch_watershed
)
from wepppy.wepp.management import (
    get_channel,
    pmetpara_prep,
    get_channel_management,
    Management
)

from wepppy.all_your_base import (
    isfloat,
    isnan,
    isinf,
    NCPU,
    IS_WINDOWS,
    NumpyEncoder
)
from wepppy.all_your_base import try_parse_float, isint
from wepppy.all_your_base.geo import read_raster, wgs84_proj4, RasterDatasetInterpolator, RDIOutOfBoundsException

from wepppy.wepp.soils.utils import WeppSoilUtil

from wepppy.wepp.out import (
    Loss,
    Ebe,
    PlotFile,
    correct_daily_hillslopes_pl_path, TotalWatSed2,
    HillPass
)

from wepppy.topo.watershed_abstraction.slope_file import clip_slope_file_length

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
from .redis_prep import RedisPrep as Prep

from wepppy.wepp.soils.utils import simple_texture

from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.nodb.mods.disturbed import Disturbed


def compress_fn(fn):
    if _exists(fn):
        p = call('gzip %s -f' % fn, shell=True)
        assert _exists(fn + '.gz')


def _copyfile(src_fn, dst_fn):
    if _exists(dst_fn):
        os.remove(dst_fn)

    if IS_WINDOWS:
        shutil.copyfile(src_fn, dst_fn)
    else:
        os.link(src_fn, dst_fn)


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
        for var in ('rst', 'newsnw', 'ssd'):
            _var = f'snow_opts_{var}'
            if var in kwds:
                setattr(self, var, try_parse_float(kwds[var], None))
            elif _var in kwds:
                setattr(self, var, try_parse_float(kwds[_var], None))

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
        for var in ('gwstorage', 'bfcoeff', 'dscoeff', 'bfthreshold'):
            _var = f'baseflow_opts_{var}'

            if var in kwds:
                setattr(self, var, try_parse_float(kwds[var], None))
            elif _var in kwds:
                setattr(self, var, try_parse_float(kwds[_var], None))

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
        for var in ('surf_runoff', 'lateral_flow', 'baseflow', 'sediment'):
            _var = f'phosphorus_opts_{var}'

            if var in kwds:
                setattr(self, var, try_parse_float(kwds[var], None))
            elif _var in kwds:
                setattr(self, var, try_parse_float(kwds[_var], None))

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


class TCROpts(object):
    def __init__(self, taumin=None, taumax=None, kch=None, nch=None):
        """
        Stores the coeffs that go into tcr.txt
        """
        self.taumin = taumin
        self.taumax = taumax
        self.kch = kch
        self.nch = nch

    def parse_inputs(self, kwds):
        for var in ('taumin', 'taumax', 'kch', 'nch'):
            _var = f'tcr_opts_{var}'

            if var in kwds:
                setattr(self, var, try_parse_float(kwds[var], None))
            elif _var in kwds:
                setattr(self, var, try_parse_float(kwds[_var], None))

    @property
    def contents(self):
        if isfloat(self.taumax) and \
           isfloat(self.taumin) and \
           isfloat(self.kch) and \
           isfloat(self.nch):
            return (
                '{0.taumin}\ttaumin\n'
                '{0.taumax}\ttaumax\n'
                '{0.kch}\tkch\n'
                '{0.nch}\tnch\n'
                .format(self)
            )
        else:
            return '\n'


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

            self.phosphorus_opts = PhosphorusOpts(
                surf_runoff=self.config_get_float('phosphorus_opts', 'surf_runoff'),
                lateral_flow=self.config_get_float('phosphorus_opts', 'lateral_flow'),
                baseflow=self.config_get_float('phosphorus_opts', 'baseflow'),
                sediment=self.config_get_float('phosphorus_opts', 'sediment'))

            self.p_surf_runoff_map = self.config_get_path('phosphorus_opts', 'surf_runoff_map')
            self.p_lateral_flow_map = self.config_get_path('phosphorus_opts', 'lateral_flow_map')
            self.p_baseflow_map = self.config_get_path('phosphorus_opts', 'baseflow_map')
            self.p_sediment_map = self.config_get_path('phosphorus_opts', 'sediment_map')

            self.snow_opts = SnowOpts(
                rst=self.config_get_float('snow_opts', 'rst'),
                newsnw=self.config_get_float('snow_opts', 'newsnw'),
                ssd=self.config_get_float('snow_opts', 'ssd'))

            self.tcr_opts = TCROpts(
                taumin=self.config_get_float('tcr_opts', 'taumin'),
                taumax=self.config_get_float('tcr_opts', 'taumax'),
                kch=self.config_get_float('tcr_opts', 'kch'),
                nch=self.config_get_float('tcr_opts', 'nch'))
           
            self.channel_critical_shear_map = self.config_get_path('wepp', 'channel_critical_shear_map')

            self.baseflow_opts = BaseflowOpts(
                gwstorage=self.config_get_float('baseflow_opts', 'gwstorage'),
                bfcoeff = self.config_get_float('baseflow_opts', 'bfcoeff'),
                dscoeff = self.config_get_float('baseflow_opts', 'dscoeff'),
                bfthreshold = self.config_get_float('baseflows_opts', 'bfthreshold'))

            self.baseflow_gwstorage_map = self.config_get_path('baseflow_opts', 'gwstorage_map')
            self.baseflow_bfcoeff_map = self.config_get_path('baseflow_opts', 'bfcoeff_map')
            self.baseflow_dscoeff_map = self.config_get_path('baseflow_opts', 'dscoeff_map')
            self.baseflow_bfthreshold_map = self.config_get_path('baseflow_opts', 'bfthreshold_map')

            self._run_wepp_ui = self.config_get_bool('wepp', 'wepp_ui')
            self._run_pmet = self.config_get_bool('wepp', 'pmet')
            self._run_frost = self.config_get_bool('wepp', 'frost')
            self._run_tcr = self.config_get_bool('wepp', 'tcr')
            self._run_baseflow = self.config_get_bool('wepp', 'baseflow')
            self._run_snow = self.config_get_bool('wepp', 'snow')
            self._wepp_bin = self.config_get_str('wepp', 'bin')
            self._channel_erodibility =  self.config_get_float('wepp', 'channel_erodibility')
            self._channel_critical_shear = self.config_get_float('wepp', 'channel_critical_shear')
            self._channel_manning_roughness_coefficient_bare = self.config_get_float('wepp', 'channel_manning_roughness_coefficient_bare')
            self._channel_manning_roughness_coefficient_veg = self.config_get_float('wepp', 'channel_manning_roughness_coefficient_veg')
            self._kslast = self.config_get_float('wepp', 'kslast')
            self._kslast_map = self.config_get_path('wepp', 'kslast_map')

            self._pmet_kcb = self.config_get_float('wepp', 'pmet_kcb')
            self._pmet_kcb_map = self.config_get_path('wepp', 'pmet_kcb_map')
            self._pmet_rawp = self.config_get_float('wepp', 'pmet_rawp')

            self._multi_ofe = self.config_get_bool('wepp', 'multi_ofe')

            self._prep_details_on_run_completion = self.config_get_bool('wepp', 'prep_details_on_run_completion', False)
            self._arc_export_on_run_completion = self.config_get_bool('wepp', 'arc_export_on_run_completion', True)
            self._legacy_arc_export_on_run_completion = self.config_get_bool('wepp', 'legacy_arc_export_on_run_completion', False)

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
    def getInstance(wd, allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'wepp.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Wepp)

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @property
    def _status_channel(self):
        return f'{self.runid}:wepp'

    @property
    def multi_ofe(self):
        return getattr(self, "_multi_ofe", False)

    @multi_ofe.setter
    def multi_ofe(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._multi_ofe = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

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
    def prep_details_on_run_completion(self):
        return getattr(self, '_prep_details_on_run_completion',
                       self.config_get_bool('wepp', 'prep_details_on_run_completion', False))

    @property
    def arc_export_on_run_completion(self):
        return getattr(self, '_arc_export_on_run_completion',
                       self.config_get_bool('wepp', 'arc_export_on_run_completion', False))

    @property
    def legacy_arc_export_on_run_completion(self):
        return getattr(self, '_legacy_arc_export_on_run_completion',
                       self.config_get_bool('wepp', 'legacy_arc_export_on_run_completion', False))

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
    def channel_manning_roughness_coefficient_bare(self):
        return getattr(self, '_channel_manning_roughness_coefficient_bare', self.config_get_float('wepp', 'channel_manning_roughness_coefficient_bare'))

    @property
    def channel_manning_roughness_coefficient_veg(self):
        return getattr(self, '_channel_manning_roughness_coefficient_veg', self.config_get_float('wepp', 'channel_manning_roughness_coefficient_veg'))

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
            if hasattr(self, 'tcr_opts'):
                self.tcr_opts.parse_inputs(kwds)

            if hasattr(self, 'snow_opts'):
                self.snow_opts.parse_inputs(kwds)

            _channel_critical_shear = kwds.get('channel_critical_shear', None)
            if isfloat(_channel_critical_shear):
                self._channel_critical_shear = float(_channel_critical_shear)

            _channel_erodibility = kwds.get('channel_erodibility', None)
            if isfloat(_channel_erodibility):
                self._channel_erodibility = float(_channel_erodibility)

            _channel_manning_roughness_coefficient_bare = kwds.get('channel_manning_roughness_coefficient_bare', None)
            if isfloat(_channel_manning_roughness_coefficient_bare):
                self._channel_manning_roughness_coefficient_bare = float(_channel_manning_roughness_coefficient_bare)

            _channel_manning_roughness_coefficient_veg = kwds.get('channel_manning_roughness_coefficient_veg', None)
            if isfloat(_channel_manning_roughness_coefficient_veg):
                self._channel_manning_roughness_coefficient_veg = float(_channel_manning_roughness_coefficient_veg)

            _pmet_kcb = kwds.get('pmet_kcb', None)
            if isfloat(_pmet_kcb):
                self._pmet_kcb = float(_pmet_kcb)

            _pmet_rawp = kwds.get('pmet_rawp', None)
            if isfloat(_pmet_rawp):
                self._pmet_rawp = float(_pmet_rawp)

            _kslast = kwds.get('kslast', '')
            if isfloat(_kslast):
                self._kslast = float(_kslast)
            elif _kslast.lower().startswith('none') or _kslast == '':
                self._kslast = None

            _wepp_bin = kwds.get('wepp_bin', None)
            if _wepp_bin is not None:
                self._wepp_bin = _wepp_bin

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def has_run(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        if _exists(loss_pw0) and not self.islocked():
            return True

        climate = Climate.getInstance(self.wd)
        if climate.ss_batch_storms:
            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                if _exists(_join(output_dir, f'{ss_batch_key}/loss_pw0.txt')):
                    return True

        return False

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

        # get translator
        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        reveg = False
        disturbed = Disturbed.getInstance(self.wd, allow_nonexistent=True)
        if disturbed is not None:
            if disturbed.sol_ver == 9005.0:
                reveg = True

        if self.multi_ofe:
            self._prep_multi_ofe(translator)
        else:
            self._prep_slopes(translator, watershed.clip_hillslopes, watershed.clip_hillslope_length)
            self._prep_managements(translator)
            self._prep_soils(translator)

        self._prep_climates(translator)
        self._make_hillslope_runs(translator, reveg=reveg)

        if (frost is None and self.run_frost) or frost:
            self._prep_frost()
        else:
            self._remove_frost()

        self._prep_phosphorus()

        if (baseflow is None and self.run_baseflow) or baseflow:
            self._prep_baseflow()
        else:
            self._remove_baseflow()

        if (wepp_ui is None and self.run_wepp_ui) or wepp_ui:
            self._prep_wepp_ui()
        else:
            self._remove_wepp_ui()

        if (pmet is None and self.run_pmet) or pmet:
            self._prep_pmet()
        else:
            self._remove_pmet()

        if (snow is None and self.run_snow) or snow:
            self._prep_snow()
        else:
            self._remove_snow()

        if reveg:
            self._prep_revegetation()

        self.log_done()

    def _prep_revegetation(self):
        self.log('    _prep_revegetation... ')

        self.log('      prep pw0.cov... ')
        from wepppy.nodb.mods import RAP_TS
        rap_ts = RAP_TS.getInstance(self.wd)
        climate = Climate.getInstance(self.wd)
        cli = ClimateFile(climate.cli_path)
        years = cli.years
        assert min(years) == rap_ts.rap_start_year, 'RAP_TS start year does not match climate'
        assert max(years) == rap_ts.rap_end_year, 'RAP_TS end year does not match climate'

        rap_ts.prep_cover(self.runs_dir)
        self.log_done()

        self._prep_firedate()

        self.log_done()

    def _prep_firedate(self):

        self.log('    prep firedate.txt... ')
        disturbed = Disturbed.getInstance(self.wd)
        if disturbed.fire_date is not None:
            with open(_join(self.runs_dir, 'firedate.txt'), 'w') as fp:
                firedate = disturbed.fire_date
                mo, da, yr = firedate.split()
                assert isint(mo), mo
                assert isint(da), da
                assert isint(yr), yr
                fp.write(firedate)
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

    def _remove_wepp_ui(self):
        fn = _join(self.runs_dir, 'wepp_ui.txt')
        if _exists(fn):
            os.remove(fn)

    def _prep_frost(self):
        fn = _join(self.runs_dir, 'frost.txt')
        with open(fn, 'w') as fp:
            fp.write('1  1  1\n')
            fp.write('1.0   1.0  1.0   0.5\n\n')

    def _remove_frost(self):
        fn = _join(self.runs_dir, 'frost.txt')
        if _exists(fn):
            os.remove(fn)

    def _prep_tcr(self):
        fn = _join(self.runs_dir, 'tcr.txt')
        with open(fn, 'w') as fp:
            if hasattr(self, 'tcr_opts'):
                fp.write(self.tcr_opts.contents)
            else:
                fp.write('\n')

    def _remove_tcr(self):
        fn = _join(self.runs_dir, 'tcr.txt')
        if _exists(fn):
            os.remove(fn)

    @property
    def pmet_kcb(self):
        return getattr(self, '_pmet_kcb', self.config_get_float('wepp', 'pmet_kcb'))

    @property
    def pmet_kcb_map(self):
        return getattr(self, '_pmet_kcb_map', self.config_get_path('wepp', 'pmet_kcb_map'))

    @pmet_kcb.setter
    def pmet_kcb(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self._pmet_kcb = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def pmet_rawp(self):
        return getattr(self, '_pmet_rawp', self.config_get_float('wepp', 'pmet_rawp'))

    @pmet_rawp.setter
    def pmet_rawp(self, value):
        self.lock()

        # noinspection PyBroadInspection
        try:
            self._pmet_ramp = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _prep_pmet(self, kcb=None, rawp=None):

        if kcb is not None and rawp is not None:
            self.log(f'nodb.Wepp._prep_pmet::kwargs routine')
            pmetpara_prep(self.runs_dir, kcb=kcb, rawp=rawp)
            assert _exists(_join(self.runs_dir, 'pmetpara.txt'))
            self.log_done()
            return

        pmet_kcb_map = self.pmet_kcb_map
        if pmet_kcb_map is not None:
            rdi = RasterDatasetInterpolator(pmet_kcb_map)
            wd = self.wd
            watershed = Watershed.getInstance(wd)
            ws_lng, ws_lat = watershed.centroid

            try:
                kcb = rdi.get_location_info(ws_lng, ws_lat, method='nearest')
                if kcb < 0.0:
                    if self.pmet_kcb is not None:
                        kcb = self.pmet_kcb
                    else:
                        kcb = None
            except RDIOutOfBoundsException:
                kcb = None

            if kcb is not None:
                self.log(f'nodb.Wepp._prep_pmet::kcb_map routine')
                pmetpara_prep(self.runs_dir, kcb=kcb, rawp=self.pmet_rawp)
                assert _exists(_join(self.runs_dir, 'pmetpara.txt'))
                self.log_done()
                return

        if 'disturbed' not in self.mods:
            self.log(f'nodb.Wepp._prep_pmet::defaults routine')
            pmetpara_prep(self.runs_dir, kcb=self.pmet_kcb, rawp=self.pmet_rawp)
            assert _exists(_join(self.runs_dir, 'pmetpara.txt'))
            self.log_done()
            return

        self.log(f'nodb.Wepp._prep_pmet::disturbed routine')
        from wepppy.nodb.mods import Disturbed
        disturbed = Disturbed.getInstance(self.wd)
        disturbed.pmetpara_prep()
        assert _exists(_join(self.runs_dir, 'pmetpara.txt'))
        self.log_done()


    def _remove_pmet(self):
        fn = _join(self.runs_dir, 'pmet.txt')
        if _exists(fn):
            os.remove(fn)

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

    def _remove_phosphorus(self):
        fn = _join(self.runs_dir, 'phosphorus.txt')
        if _exists(fn):
            os.remove(fn)

    def _prep_snow(self):
        fn = _join(self.runs_dir, 'snow.txt')
        with open(fn, 'w') as fp:
            fp.write(self.snow_opts.contents)

    def _remove_snow(self):
        fn = _join(self.runs_dir, 'snow.txt')
        if _exists(fn):
            os.remove(fn)

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

    def _remove_baseflow(self):
        fn = _join(self.runs_dir, 'gwcoeff.txt')
        if _exists(fn):
            os.remove(fn)

    def clean(self):
        if _exists(self.status_log):
            os.remove(self.status_log)

        for _dir in (self.runs_dir, self.output_dir, self.plot_dir,
                     self.stats_dir, self.fp_runs_dir, self.fp_output_dir):
            if _exists(_dir):
                try:
                    shutil.rmtree(_dir)
                except:
                    sleep(1.0)
                    try:
                        shutil.rmtree(_dir, ignore_errors=True)
                    except:
                        pass

            if not _exists(_dir):
                os.makedirs(_dir)

        climate = Climate.getInstance(self.wd)
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                ss_batch_dir = _join(self.output_dir, ss_batch_key)
                if not _exists(ss_batch_dir):
                    os.makedirs(ss_batch_dir)

    def _prep_slopes_peridot(self, watershed, translator, clip_hillslopes, clip_hillslope_length):
        self.log('    Prepping _prep_slopes_peridot... ')
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, _ in watershed.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))

            src_fn = _join(wat_dir, 'slope_files/hillslopes/hill_{}.slp'.format(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            if clip_hillslopes:
                clip_slope_file_length(src_fn, dst_fn, clip_hillslope_length)
            else:
                _copyfile(src_fn, dst_fn)

        self.log_done()

    def _prep_slopes(self, translator, clip_hillslopes, clip_hillslope_length):
        self.log('    Prepping _prep_slopes... ')

        watershed = Watershed.getInstance(self.wd)
        if watershed.abstraction_backend == 'peridot':
            return self._prep_slopes_peridot(watershed, translator, clip_hillslopes, clip_hillslope_length)

        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, _ in watershed.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))

            src_fn = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            if clip_hillslopes:
                clip_slope_file_length(src_fn, dst_fn, clip_hillslope_length)
            else:
                _copyfile(src_fn, dst_fn)

        self.log_done()

    def _prep_multi_ofe(self, translator):
        self.log('    Prepping _prep_multi_ofe... ')
        wd = self.wd

        landuse = Landuse.getInstance(wd)
        climate = Climate.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        soils = Soils.getInstance(wd)

        clip_soils = soils.clip_soils
        clip_soils_depth = soils.clip_soils_depth
        initial_sat = soils.initial_sat

        try:
            disturbed = Disturbed.getInstance(wd)
        except:
            disturbed = None

        years = climate.input_years

        wat_dir = self.wat_dir
        soils_dir = self.soils_dir
        lc_dir = self.lc_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        kslast = self.kslast

        kslast_map_fn = self.kslast_map
        kslast_map = None
        if kslast_map_fn is not None:
            kslast_map = RasterDatasetInterpolator(kslast_map_fn)

        for topaz_id, sub in watershed.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))

            # slope files
            src_fn = _join(wat_dir, sub.fname.replace('.slp', '.mofe.slp'))
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            _copyfile(src_fn, dst_fn)

            # soils
            src_fn = _join(soils_dir, f'hill_{topaz_id}.mofe.sol')
            dst_fn = _join(runs_dir, 'p%i.sol' % wepp_id)

            _kslast = None

            if kslast_map is not None:
                lng, lat = watershed._subs_summary[topaz_id].centroid.lnglat

                try:
                    _kslast = kslast_map.get_location_info(lng, lat, method='nearest')
                except RDIOutOfBoundsException:
                    _kslast = None

                if not isfloat(_kslast):
                    if kslast is not None:
                        _kslast = kslast
                    else:
                        _kslast = None
                elif _kslast <= 0.0:
                    if kslast is not None:
                        _kslast = kslast
                    else:
                        _kslast = None
            elif kslast is not None:
                _kslast = kslast

            soilu = WeppSoilUtil(src_fn)
            soilu.modify_initial_sat(initial_sat)

            if _kslast is not None:
                soilu.modify_kslast(_kslast)

            if clip_soils:
                soilu.clip_soil_depth(clip_soils_depth)

            soilu.write(dst_fn)

            # managements
            man_fn = f'hill_{topaz_id}.mofe.man'
            man = Management(Key=f'hill_{topaz_id}',
                             ManagementFile=man_fn,
                             ManagementDir=lc_dir,
                             Description=f"hill_{topaz_id} Multiple OFE",
                             Color=(0,0,0))

            man = man.build_multiple_year_man(years)
            dst_fn = _join(runs_dir, 'p%i.man' % wepp_id)
            with open(dst_fn, 'w') as pf:
                pf.write(str(man))


    def _prep_managements(self, translator):
        self.log('    _prep_managements... ')

        wd = self.wd

        landuse = Landuse.getInstance(wd)
        hillslope_cancovs = landuse.hillslope_cancovs

        climate = Climate.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        soils = Soils.getInstance(wd)
        try:
            disturbed = Disturbed.getInstance(wd)
            _land_soil_replacements_d = disturbed.land_soil_replacements_d
        except:
            disturbed = None
            _land_soil_replacements_d = None

        try:
            from wepppy.nodb.mods import RAP_TS
            rap_ts = RAP_TS.getInstance(wd)
        except:
            rap_ts = None

        years = climate.input_years
        year0 = climate.year0

        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        bd_d = soils.bd_d

        build_d = {}

        for i, (topaz_id, mukey) in enumerate(soils.domsoil_d.items()):
            if (int(topaz_id) - 4) % 10 == 0:
                continue

            self.log(f'    _prep_managements:{topaz_id}:{mukey}... ')

            dom = landuse.domlc_d[topaz_id]
            man_summary = landuse.managements[dom]

            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.man' % wepp_id)

            meoization_key = (mukey,)
            if disturbed:
                disturbed_class = man_summary.disturbed_class
                meoization_key = (mukey, disturbed_class)

            if rap_ts is not None:
                meoization_key = (topaz_id, mukey)

            if meoization_key in build_d:
                shutil.copyfile(build_d[meoization_key], dst_fn)
                self.log_done()

            else:
                management = man_summary.get_management()
                sol_key = soils.domsoil_d[topaz_id]
                management.set_bdtill(bd_d[sol_key])

                # probably isn't the right location for this code. should be in nodb.disturbed
                if disturbed is not None:
                    disturbed_class = man_summary.disturbed_class

                    if hillslope_cancovs is not None and 'mulch' not in disturbed_class and 'thinning' not in disturbed_class:
                        assert rap_ts is None, 'project has rap and rap_ts'
                        management.set_cancov(hillslope_cancovs[str(topaz_id)])

                    _soil = soils.soils[mukey]
                    clay = _soil.clay
                    sand = _soil.sand
                    texid = simple_texture(clay=clay, sand=sand)

                    if (texid, disturbed_class) not in _land_soil_replacements_d:
                        texid = 'all'

                    if disturbed_class is None or 'developed' in disturbed_class:
                        rdmax = None
                        xmxlai = None
                    else:
                        rdmax = _land_soil_replacements_d[(texid, disturbed_class)]['rdmax']
                        xmxlai = _land_soil_replacements_d[(texid, disturbed_class)]['xmxlai']

                    if isfloat(rdmax):
                        management.set_rdmax(float(rdmax))

                    if isfloat(xmxlai):
                        management.set_xmxlai(float(xmxlai))

                    meoization_key = (mukey, disturbed_class)

                if rap_ts is not None:
                    if year0 >= rap_ts.rap_start_year and year0 <= rap_ts.rap_end_year:
                        cover = rap_ts.get_cover(topaz_id, year0)
                        management.set_cancov(cover)

                multi = management.build_multiple_year_man(years)

                fn_contents = str(multi)

                with open(dst_fn, 'w') as fp:
                    fp.write(fn_contents)

                build_d[meoization_key] = dst_fn

                self.log_done()

        if 'emapr_ts' in self.mods:
            self.log('    _prep_managements:emapr_ts.analyze... ')
            from wepppy.nodb.mods import OSUeMapR_TS
            assert climate.observed_start_year is not None
            assert climate.observed_end_year is not None

            emapr_ts = OSUeMapR_TS.getInstance(wd)
            emapr_ts.acquire_rasters(start_year=climate.observed_start_year,
                                     end_year=climate.observed_end_year)
            emapr_ts.analyze()
            self.log_done()

    def _prep_soils(self, translator):
        self.log('    _prep_soils... ')
        soils = Soils.getInstance(self.wd)
        soils_dir = self.soils_dir
        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        kslast = self.kslast
        clip_soils = soils.clip_soils
        clip_soils_depth = soils.clip_soils_depth
        initial_sat = soils.initial_sat

        kslast_map_fn = self.kslast_map

        kslast_map = None
        if kslast_map_fn is not None:
            kslast_map = RasterDatasetInterpolator(kslast_map_fn)

        for topaz_id, soil in soils.sub_iter():

            self.log(f'    _prep_soils:{topaz_id}:{soil}... ')
            wepp_id = translator.wepp(top=int(topaz_id))
            src_fn = _join(soils_dir, soil.fname)
            dst_fn = _join(runs_dir, 'p%i.sol' % wepp_id)

            _kslast = None

            pars = None
            if kslast_map is not None:
                lng, lat = watershed._subs_summary[topaz_id].centroid.lnglat

                try:
                    _kslast = kslast_map.get_location_info(lng, lat, method='nearest')
                    pars = dict(map_fn=kslast_map_fn, lng=lng, lat=lat, kslast=_kslast)
                except RDIOutOfBoundsException:
                    _kslast = None

                if not isfloat(_kslast):
                    if kslast is not None:
                        _kslast = kslast
                    else:
                        _kslast = None
                elif _kslast <= 0.0:
                    if kslast is not None:
                        _kslast = kslast
                    else:
                        _kslast = None
            elif kslast is not None:
                _kslast = kslast

            soilu = WeppSoilUtil(src_fn)
            soilu.modify_initial_sat(initial_sat)

            if _kslast is not None:
                soilu.modify_kslast(_kslast, pars=pars)
            if clip_soils:
                soilu.clip_soil_depth(clip_soils_depth)
            soilu.write(dst_fn)

            self.log_done()

        self.log_done()

    def _prep_climates(self, translator):
        climate = Climate.getInstance(self.wd)
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            return self._prep_climates_ss_batch(translator)

        self.log('    _prep_climates... ')
        watershed = Watershed.getInstance(self.wd)
        cli_dir = self.cli_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, _ in watershed.sub_iter():
            self.log(f'    _prep_climates:{topaz_id}... ')

            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.cli' % wepp_id)

            cli_summary = climate.sub_summary(topaz_id)
            src_fn = _join(cli_dir, cli_summary['cli_fn'])
            _copyfile(src_fn, dst_fn) 

            self.log_done()

        self.log_done()

    def _prep_climates_ss_batch(self, translator):
        climate = Climate.getInstance(self.wd)

        self.log('    _prep_climates_ss_batch... ')
        watershed = Watershed.getInstance(self.wd)
        cli_dir = self.cli_dir
        runs_dir = self.runs_dir

        for d in climate.ss_batch_storms:
            ss_batch_id = d['ss_batch_id']
            ss_batch_key = d['ss_batch_key']
            cli_fn = d['cli_fn']

            for topaz_id, _ in watershed.sub_iter():
                self.log(f'    _prep_climates:{topaz_id}... ')

                wepp_id = translator.wepp(top=int(topaz_id))
                dst_fn = _join(runs_dir, f'p{wepp_id}.{ss_batch_id}.cli')

                src_fn = _join(cli_dir, cli_fn)
                _copyfile(src_fn, dst_fn)

                self.log_done()

            dst_fn = _join(runs_dir, f'pw0.{ss_batch_id}.cli')
            src_fn = _join(cli_dir, cli_fn)
            _copyfile(src_fn, dst_fn)

        self.log_done()

    def _make_hillslope_runs(self, translator, reveg=False):
        self.log('    Prepping _make_hillslope_runs... ')
        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        climate = Climate.getInstance(self.wd)
        years = climate.input_years

        if climate.climate_mode in [ClimateMode.SingleStorm, ClimateMode.UserDefinedSingleStorm]:
            for topaz_id, _ in watershed.sub_iter():
                wepp_id = translator.wepp(top=int(topaz_id))

                make_ss_hillslope_run(wepp_id, runs_dir)

        elif climate.climate_mode == ClimateMode.SingleStormBatch:
            for topaz_id, _ in watershed.sub_iter():
                wepp_id = translator.wepp(top=int(topaz_id))

                for d in climate.ss_batch_storms:
                    ss_batch_id = d['ss_batch_id']
                    ss_batch_key = d['ss_batch_key']
                    make_ss_batch_hillslope_run(wepp_id, runs_dir, ss_batch_id=ss_batch_id, ss_batch_key=ss_batch_key)

        else:
            for topaz_id, _ in watershed.sub_iter():
                wepp_id = translator.wepp(top=int(topaz_id))
                make_hillslope_run(wepp_id, years, runs_dir, reveg=reveg)

        self.log_done()


    def run_hillslopes(self):
        self.log('Running Hillslopes\n')
        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()
        climate = Climate.getInstance(self.wd)
        runs_dir = os.path.abspath(self.runs_dir)
        fp_runs_dir = self.fp_runs_dir
        wepp_bin = self.wepp_bin

        self.log('    wepp_bin:{}'.format(wepp_bin))

        pool = ThreadPoolExecutor(NCPU)
        futures = []

        def oncomplete(wepprun):
            status, _id, elapsed_time = wepprun.result()
            assert status
            self.log('  {} completed run in {}s\n'.format(_id, elapsed_time))

        sub_n = watershed.sub_n
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            for i, (topaz_id, _) in enumerate(watershed.sub_iter()):

                ss_n = len(climate.ss_batch_storms)
                for d in climate.ss_batch_storms:
                    ss_batch_id = d['ss_batch_id']
                    ss_batch_key = d['ss_batch_key']

                    self.log(f'  submitting topaz={topaz_id} (hill {i+1} of {sub_n}, ss {ss_batch_id}  of {ss_n}).\n')
                    wepp_id = translator.wepp(top=int(topaz_id))
                    futures.append(pool.submit(lambda p: run_ss_batch_hillslope(*p), (wepp_id, runs_dir, wepp_bin, ss_batch_id)))
                    futures[-1].add_done_callback(oncomplete)

        else:
            for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
                self.log(f'  submitting topaz={topaz_id} (hill {i+1} of {sub_n})')
                wepp_id = translator.wepp(top=int(topaz_id))
                futures.append(pool.submit(lambda p: run_hillslope(*p), (wepp_id, runs_dir, wepp_bin)))
                futures[-1].add_done_callback(oncomplete)

        wait(futures, return_when=FIRST_EXCEPTION)

    #
    # watershed
    #
    def prep_watershed(self, erodibility=None, critical_shear=None,
                       tcr=None, avke=None,
                       channel_manning_roughness_coefficient_bare=None,
                       channel_manning_roughness_coefficient_veg=None):
        self.log('Prepping Watershed... ')

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        if critical_shear is None:
            crit_shear_map = getattr(self, 'channel_critical_shear_map', None)

            if crit_shear_map is not None:
                lng, lat = watershed.centroid
                rdi = RasterDatasetInterpolator(crit_shear_map)
                critical_shear = rdi.get_location_info(lng, lat, method='nearest')
                self.log(f'critical_shear from map {crit_shear_map} at {watershed.centroid} ={critical_shear}... ')
                self.log_done()
        if critical_shear is None:
            critical_shear = self.channel_critical_shear

        self._prep_structure(translator)
        self._prep_channel_slopes()
        self._prep_channel_chn(translator, erodibility, critical_shear, 
                               channel_manning_roughness_coefficient_bare=channel_manning_roughness_coefficient_bare, 
                               channel_manning_roughness_coefficient_veg=channel_manning_roughness_coefficient_veg)
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
        self.log('    Prepping _prep_structure... ')

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

        self.log_done()

    def _prep_channel_slopes(self):
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir

        src_fn = _join(wat_dir, 'slope_files/channels.slp')
        if not _exists(src_fn):
            src_fn = _join(wat_dir, 'channels.slp')

        dst_fn = _join(runs_dir, 'pw0.slp')
        _copyfile(src_fn, dst_fn)

    def _prep_channel_chn(self, translator, erodibility, critical_shear,
                          channel_routing_method=ChannelRoutingMethod.MuskingumCunge,
                          channel_manning_roughness_coefficient_bare=None,
                          channel_manning_roughness_coefficient_veg=None):

        if erodibility is not None or critical_shear is not None:
            self.log('nodb.Wepp._prep_channel_chn::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))
            self.log_done()

        if erodibility is None:
            erodibility = self.channel_erodibility

        if critical_shear is None:
            critical_shear = self.channel_critical_shear

        if channel_manning_roughness_coefficient_bare is None:
            channel_manning_roughness_coefficient_bare = self.channel_manning_roughness_coefficient_bare

        if channel_manning_roughness_coefficient_veg is None:
            channel_manning_roughness_coefficient_veg = self.channel_manning_roughness_coefficient_veg

        assert translator is not None

        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir

        chn_n = watershed.chn_n

        fp = open(_join(runs_dir, 'pw0.chn'), 'w')

        if channel_routing_method == ChannelRoutingMethod.MuskingumCunge:
            # this specifies the creation of the chanwb.out
            fp.write('99.1\r\n{chn_n}\r\n4\r\n1.500000\r\n'
                     .format(chn_n=chn_n))
        else:
            fp.write('99.1\r\n{chn_n}\r\n2\r\n1.00000\r\n'
                     .format(chn_n=chn_n))

        for topaz_id, chn_summary in watershed.chn_iter():
            # need to do this incase someone tries to run a pre peridot project
            if isinstance(chn_summary, dict):
                chn_key = chn_summary.get('channel_type', 'Default')
            else:
                chn_key = chn_summary.channel_type

            chn_d = get_channel(chn_key, erodibility, critical_shear, 
                                chnnbr=channel_manning_roughness_coefficient_bare, 
                                chnn=channel_manning_roughness_coefficient_veg)
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
        climate = Climate.getInstance(self.wd)

        chn_n = wat.chn_n
        sub_n = wat.sub_n
        total = chn_n + sub_n

        flag = 1
        rate = 600
        if climate.is_single_storm:  # and climate.is_breakpoint:
            flag = 3
            rate = 60

        runs_dir = self.runs_dir
        with open(_join(runs_dir, 'chan.inp'), 'w') as fp:
            # 1 is the Peak Flow time and rate, 600s is the interval
            # 2 Daily average discharge, 600 probably doesn't do anything

            fp.write(f'{flag} {rate}\n0\n1\n{total}\n')

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
        _copyfile(src_fn, dst_fn) 

    def _make_watershed_run(self, translator):
        runs_dir = self.runs_dir
        wepp_ids = list(translator.iter_wepp_sub_ids())
        wepp_ids.sort()

        climate = Climate.getInstance(self.wd)
        years = climate.input_years

        if climate.climate_mode in [ClimateMode.SingleStorm, ClimateMode.UserDefinedSingleStorm]:
            make_ss_watershed_run(wepp_ids, runs_dir)
        elif climate.climate_mode == ClimateMode.SingleStormBatch:
            for d in climate.ss_batch_storms:
                ss_batch_id = d['ss_batch_id']
                ss_batch_key = d['ss_batch_key']
                make_ss_batch_watershed_run(wepp_ids, runs_dir, ss_batch_id=ss_batch_id, ss_batch_key=ss_batch_key)
        else:
            make_watershed_run(years, wepp_ids, runs_dir)

    def run_watershed(self):
        from wepppy.export.prep_details import (
            export_channels_prep_details,
            export_hillslopes_prep_details
        )
        wd = self.wd
        climate = Climate.getInstance(wd)
        wepp_bin = self.wepp_bin
        self.log(f'Running Watershed wepp_bin:{self.wepp_bin}... ')

        runs_dir = self.runs_dir

        if climate.climate_mode == ClimateMode.SingleStormBatch:

            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                ss_batch_id = d['ss_batch_id']
                run_ss_batch_watershed(runs_dir, wepp_bin, ss_batch_id)

                self.log('    moving .out files...')
                for fn in glob(_join(self.runs_dir, '*.out')):
                    dst_path = _join(self.output_dir, ss_batch_key, _split(fn)[1])
                    shutil.move(fn, dst_path)
                self.log_done()

        else:
            assert run_watershed(runs_dir, wepp_bin, status_channel=self._status_channel)

            self.log('    moving .out files...')
            for fn in glob(_join(self.runs_dir, '*.out')):
                dst_path = _join(self.output_dir, _split(fn)[1])
                shutil.move(fn, dst_path)
            self.log_done()

        self.log_done()

        if self.prep_details_on_run_completion:
            self.log('    exporting prep details...')
            export_channels_prep_details(wd)
            export_hillslopes_prep_details(wd)
            self.log_done()

        if not _exists(_join(wd, 'wepppost.nodb')):
            WeppPost(wd, '0.cfg')

        climate = Climate.getInstance(wd)

        if not climate.is_single_storm:
            self.log(' running wepppost... ')
            self._run_wepppost()
            self.log_done()

            self.log(' running totalwatsed2... ')
            self._build_totalwatsed2()
            self.log_done()

            self.log(' running hillslope_watbal... ')
            self._run_hillslope_watbal()
            self.log_done()

            self.log(' compressing pass_pw0.txt... ')
            compress_fn(_join(self.output_dir, 'pass_pw0.txt'))
            self.log_done()

            self.log(' compressing soil_pw0.txt... ')
            compress_fn(_join(self.output_dir, 'soil_pw0.txt'))
            self.log_done()

            if self.legacy_arc_export_on_run_completion:
                self.log(' running legacy arcexport... ')
                from wepppy.export import  legacy_arc_export
                legacy_arc_export(self.wd)
                self.log_done()


        _ = self.loss_report # make the .parquet files for loss report

        if self.arc_export_on_run_completion:
            self.log(' running gpkg_export... ')
            from wepppy.export.gpkg_export import gpkg_export
            gpkg_export(self.wd)
            self.log_done()

            self.make_loss_grid()

        self.log('Watershed Run Complete')

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('run_wepp')
        except FileNotFoundError:
            pass

    def post_discord_wepp_run_complete(self):
        if send_discord_message is not None:
            from wepppy.nodb import Ron

            ron = Ron.getInstance(self.wd)
            name = ron.name
            scenario = ron.scenario
            runid = ron.runid
            config = ron.config_stem

            link = runid
            if name or scenario:
                if name and scenario:
                    link = f'{name} - {scenario} _{runid}_'
                elif name:
                    link = f'{name} _{runid}_'
                else:
                    link = f'{scenario} _{runid}_'

            send_discord_message(f':fireworks: [{link}](https://wepp.cloud/weppcloud/runs/{runid}/{config}/)')

    def _run_hillslope_watbal(self):
        self.log('Calculating Hillslope Water Balance...')
        HillslopeWatbal(self.wd)
        self.log_done()

    def _run_wepppost(self):
        self.log('Running WeppPost... ')
        wepppost = WeppPost.getInstance(self.wd)
        wepppost.run_post()
        self.log_done()

    def _build_totalwatsed2(self):
        self.log('Building totalwatsed2.pkl... ')
        totwatsed2 = TotalWatSed2(self.wd)
        fn = _join(self.export_dir, 'totalwatsed2.csv')
        totwatsed2.export(fn)
        self.log_done()

    def report_loss(self, exclude_yr_indxs=None):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        return Loss(loss_pw0, self.has_phosphorus, self.wd, exclude_yr_indxs=exclude_yr_indxs)

    def report_return_periods(self, rec_intervals=(25, 20, 10, 5, 2), exclude_yr_indxs=None):

        output_dir = self.output_dir


        if exclude_yr_indxs is None:
            return_periods_fn = _join(output_dir, 'return_periods.json')
        else:
            x = ','.join(str(v) for v in exclude_yr_indxs)
            return_periods_fn = _join(output_dir, f'return_periods__exclude_yr_indxs={x}.json')


        if _exists(return_periods_fn):
            with open(return_periods_fn) as fp:
                report = ReturnPeriods.from_dict(json.load(fp))
                if exclude_yr_indxs is None and report.exclude_yr_indxs is None:
                    return report
                elif exclude_yr_indxs is None or report.exclude_yr_indxs is None:
                    pass
                elif list(sorted(exclude_yr_indxs)) == list(sorted(report.exclude_yr_indxs)):
                    return report

        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        loss_rpt = Loss(loss_pw0, self.has_phosphorus, self.wd)

        ebe_pw0 = _join(output_dir, 'ebe_pw0.txt')
        ebe_rpt = Ebe(ebe_pw0)

        climate = Climate.getInstance(self.wd)
        cli = ClimateFile(_join(climate.cli_dir, climate.cli_fn))
        cli_df = cli.as_dataframe(calc_peak_intensities=True)

        return_periods = ReturnPeriods(ebe_rpt, loss_rpt, cli_df, recurrence=rec_intervals,
                                       exclude_yr_indxs=exclude_yr_indxs)

        with open(return_periods_fn, 'w') as fp:
            json.dump(return_periods.to_dict(), fp, cls=NumpyEncoder)

        return return_periods

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

    @property
    def loss_report(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')

        if not _exists(loss_pw0):
            return None

        if not hasattr(self, '_loss_report'):
            self._loss_report = Loss(loss_pw0, self.has_phosphorus, self.wd)

        return self._loss_report

    def query_sub_val(self, measure):
        wd = self.wd
        report = self.loss_report
        if report is None:
            return None

        translator = Watershed.getInstance(wd).translator_factory()

        d = {}
        for row in report.hill_tbl:
            topaz_id = translator.top(wepp=row['Hillslopes'])

            v = row.get(measure, None)
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

        if not hasattr(self, '_loss_report'):
            self._loss_report = Loss(loss_pw0, self.has_phosphorus, self.wd)

        report = self._loss_report

        d = {}
        for row in report.chn_tbl:
            topaz_id = translator.top(chn_enum=row['Channels and Impoundments'])

            v = row.get(measure, None)
            if isnan(v) or isinf(v):
                v = None

            d[str(topaz_id)] = dict(
                topaz_id=topaz_id,
                value=v
            )

        return d

    def make_loss_grid(self):
        watershed = Watershed.getInstance(self.wd)
        loss_grid_path = _join(self.plot_dir, 'loss.tif')
        make_soil_loss_grid(watershed.subwta, watershed.discha, self.output_dir, loss_grid_path)
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

    @property
    def kslast_map(self):
        if not hasattr(self, '_kslast_map'):
            return None

        return self._kslast_map

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

