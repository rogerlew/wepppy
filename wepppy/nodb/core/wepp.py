# Copyright (c) 2016-2023, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""WEPP model configuration, execution, and output processing.

This module provides the Wepp NoDb controller for managing Water Erosion
Prediction Project (WEPP) model configuration, input file generation, simulation
execution, and result analysis.

Key Components:
    Wepp: NoDb controller for WEPP model management
    PhosphorusOpts: Phosphorus transport modeling parameters
    BaseflowOpts: Baseflow routing configuration
    SnowOpts: Snow accumulation and melt parameters
    TCROpts: Total carbon routing options
    ChannelRoutingMethod: Enum for channel routing algorithms

WEPP Model Components:
    - Hillslope simulations (parallel execution)
    - Channel routing (watershed-scale)
    - Phosphorus transport (optional)
    - Baseflow modeling (optional)
    - Snow processes (optional)

Input Files Generated:
    - .man: Management/vegetation files
    - .sol: Soil parameter files
    - .slp: Slope profile files
    - .cli: Climate files
    - structure.txt: Watershed connectivity

Output Files Processed:
    - .wat: Water balance and runoff
    - .soil_loss: Erosion and sediment yield
    - .pass: Hillslope pass file
    - .element: Channel element output

Example:
    >>> from wepppy.nodb.core import Wepp, PhosphorusOpts
    >>> wepp = Wepp.getInstance('/wc1/runs/my-run')
    >>> wepp.phosphorus_opts = PhosphorusOpts(surf_runoff=0.01)
    >>> wepp.prep_hillslopes()
    >>> wepp.run_hillslopes()  # Parallel execution
    >>> wepp.run_watershed()
    >>> print(f"Soil loss: {wepp.avg_soil_loss_tha:.2f} t/ha")

See Also:
    - wepppy.wepp: WEPP input/output file management
    - wepppy.nodb.core.climate: Climate data for .cli files
    - wepppy.nodb.core.soils: Soil data for .sol files
    - wepppy.nodb.core.landuse: Management data for .man files

Note:
    WEPP simulations require completed watershed abstraction,
    climate data, soil data, and management assignments.
    
Warning:
    Hillslope runs must complete before watershed simulation.
    Use wepp.run_hillslopes() before wepp.run_watershed().
"""

# standard library
import os
from enum import IntEnum
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

import math

from subprocess import Popen, PIPE, call
from concurrent.futures import (
    ThreadPoolExecutor, wait, FIRST_COMPLETED
)
from concurrent.futures.process import BrokenProcessPool
import time
import inspect
import pickle
from copy import deepcopy
from glob import glob

import shutil

from time import sleep

# non-standard

import numpy as np
import json

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *

from wepppyo3.wepp_viz import make_soil_loss_grid, make_soil_loss_grid_fps

__all__ = [
    'ChannelRoutingMethod',
    'SnowOpts',
    'BaseflowOpts',
    'PhosphorusOpts',
    'TCROpts',
    'WeppNoDbLockedException',
    'Wepp',
]

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
    make_watershed_omni_contrasts_run,
    make_ss_watershed_run,
    make_ss_batch_watershed_run,
    run_watershed,
    run_ss_batch_watershed,
    make_flowpath_run,
    run_flowpath
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
    IS_WINDOWS,
    NumpyEncoder
)
from wepppy.all_your_base import try_parse_float, isint
from wepppy.all_your_base.geo import read_raster, wgs84_proj4, RasterDatasetInterpolator, RDIOutOfBoundsException

from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.topo.watershed_abstraction.slope_file import clip_slope_file_length

from wepppy.wepp.reports import (
    ChannelWatbalReport,
    FrqFloodReport,
    HillslopeWatbalReport,
    ReturnPeriodDataset,
    ReturnPeriods,
    SedimentCharacteristics,
)
from wepppy.nodb.base import (
    NoDbBase,
    TriggerEvents,
    nodb_setter,
    nodb_timed,
    createProcessPoolExecutor,
)

from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.wepp.soils.utils import simple_texture
from wepppy.nodb.core.climate import ClimateMode
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.duckdb_agents import get_watershed_chns_summary

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


def prep_soil(args):
    t0 = time.time()
    # str,    str,    str,    float,  bool,               float,       bool,       float
    topaz_id, src_fn, dst_fn, kslast, modify_kslast_pars, initial_sat, clip_soils, clip_soils_depth = args

    soilu = WeppSoilUtil(src_fn)  # internally uses rosetta
    soilu.modify_initial_sat(initial_sat)

    if kslast is not None:
        soilu.modify_kslast(kslast, pars=modify_kslast_pars)
    if clip_soils:
        soilu.clip_soil_depth(clip_soils_depth)
    soilu.write(dst_fn)

    return topaz_id, time.time() - t0


class WeppNoDbLockedException(Exception):
    pass


def extract_slps_fn(slps_fn, fp_runs_dir):
    f = None
    with open(slps_fn) as fp:
        
        for line in fp:
            if line.startswith('# fp_') and line.endswith('.slp\n'):
                fp_fn = line.split()[1].strip()
                if f is not None:
                    f.close()

                f = open(_join(fp_runs_dir, fp_fn), 'w')

            else:
                f.write(line)

        if f is not None:
            f.close()


class Wepp(NoDbBase):
    __name__ = 'Wepp'

    filename = 'wepp.nodb'
    
    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(Wepp, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
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
            self._dss_export_mode = self.config_get_int('wepp', 'dss_export_mode', 2)  # view model property
            self._dss_export_on_run_completion = self.config_get_bool('wepp', 'dss_export_on_run_completion', False)  # view model property
            self._dss_excluded_channel_orders = self.config_get_list('wepp', 'dss_excluded_channel_orders', [1, 2])  # view model property
            self._dss_export_channel_ids = [] # specifies which channels are exported

            self._dtchr_override = None
            self._chn_topaz_ids_of_interest = [24]

            self.run_flowpaths = False
            self.loss_grid_d_path = None

            self.clean()

        
    @property
    def dss_export_mode(self) -> int:
        return getattr(self, '_dss_export_mode', self.config_get_int('wepp', 'dss_export_mode', 2))
    
    @dss_export_mode.setter
    @nodb_setter
    def dss_export_mode(self, value: isint):
        self._dss_export_mode = value

    @property
    def dss_excluded_channel_orders(self) -> list:
        return getattr(self, '_dss_excluded_channel_orders', 
                       self.config_get_list('wepp', 'dss_excluded_channel_orders'))

    @dss_excluded_channel_orders.setter
    @nodb_setter
    def dss_excluded_channel_orders(self, value):
        self._dss_excluded_channel_orders = value

    @property
    def dss_export_channel_ids(self) -> list:
        return getattr(self, '_dss_export_channel_ids', [])

    @dss_export_channel_ids.setter
    @nodb_setter
    def dss_export_channel_ids(self, value):
        self._dss_export_channel_ids = value

    @property
    def has_dss_zip(self):
        return _exists(_join(self.export_dir, 'dss.zip'))

    @property
    def multi_ofe(self):
        return getattr(self, "_multi_ofe", False)

    @multi_ofe.setter
    @nodb_setter
    def multi_ofe(self, value):
        self._multi_ofe = value

    @property
    def wepp_bin(self):
        if not hasattr(self, "_wepp_bin"):
            return None

        return self._wepp_bin

    @wepp_bin.setter
    @nodb_setter
    def wepp_bin(self, value):
        self._wepp_bin = value


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
    def dss_export_on_run_completion(self):
        return getattr(self, '_dss_export_on_run_completion',
                       self.config_get_bool('wepp', 'dss_export_on_run_completion', False))

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

    @property
    def is_omni_contrasts_run(self):
        run_dir = os.path.abspath(self.runs_dir)
        return 'omni/contrasts' in run_dir

    def set_baseflow_opts(self, gwstorage=None, bfcoeff=None, dscoeff=None, bfthreshold=None):
        with self.locked():
            self.baseflow_opts = BaseflowOpts(
                gwstorage=gwstorage,
                bfcoeff=bfcoeff,
                dscoeff=dscoeff,
                bfthreshold=bfthreshold)

    def set_phosphorus_opts(self, surf_runoff=None, lateral_flow=None, baseflow=None, sediment=None):
        with self.locked():
            self.phosphorus_opts = PhosphorusOpts(
                surf_runoff=surf_runoff,
                lateral_flow=lateral_flow,
                baseflow=baseflow,
                sediment=sediment)

    def parse_inputs(self, kwds):
        with self.locked():
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

            _dtchr_override = kwds.get('dtchr_override', None)
            if isfloat(_dtchr_override):
                _dtchr_override = int(_dtchr_override)
                if _dtchr_override < 60:
                    raise ValueError("dtchr_override must be at least 60")
                self._dtchr_override = _dtchr_override

            _chn_topaz_ids_of_interest = kwds.get('chn_topaz_ids_of_interest', None)
            if _chn_topaz_ids_of_interest is not None:
                if ',' in _chn_topaz_ids_of_interest:
                    _chn_topaz_ids_of_interest = _chn_topaz_ids_of_interest.split(',')
                elif ' ' in _chn_topaz_ids_of_interest:
                    _chn_topaz_ids_of_interest = _chn_topaz_ids_of_interest.split(' ')
                else:
                    _chn_topaz_ids_of_interest = [_chn_topaz_ids_of_interest]
                _chn_topaz_ids_of_interest = [int(v) for v in _chn_topaz_ids_of_interest]
                self._chn_topaz_ids_of_interest = _chn_topaz_ids_of_interest


    @property
    def has_run(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        if _exists(loss_pw0) and not self.islocked():
            return True

        climate = self.climate_instance
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
    def prep_hillslopes(self, frost=None, baseflow=None, wepp_ui=None, pmet=None, snow=None,
                  man_relpath='', cli_relpath='', slp_relpath='', sol_relpath='',
                  max_workers=None):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(frost={frost}, baseflow={baseflow}, wepp_ui={wepp_ui}, pmet={pmet}, snow={snow}, man_relpath={man_relpath}, cli_relpath={cli_relpath}, slp_relpath={slp_relpath}, sol_relpath={sol_relpath})')

        # get translator
        watershed = self.watershed_instance
        translator = watershed.translator_factory()

        reveg = False
        disturbed = Disturbed.getInstance(self.wd, allow_nonexistent=True)
        if disturbed is not None:
            if disturbed.sol_ver == 9005.0:
                reveg = True

        if self.multi_ofe:
            self._prep_multi_ofe(translator)
        else:
            if slp_relpath == '':
                self._prep_slopes(translator, watershed.clip_hillslopes, watershed.clip_hillslope_length)
            self._prep_managements(translator)
            self._prep_soils(translator, max_workers=max_workers)

        if cli_relpath == '':
            self._prep_climates(translator)

        self._make_hillslope_runs(translator, reveg=reveg,
                                  man_relpath=man_relpath, 
                                  cli_relpath=cli_relpath, 
                                  slp_relpath=slp_relpath, 
                                  sol_relpath=sol_relpath)

        if (frost is None and self.run_frost) or frost:
            self._prep_frost()
        else:
            self._remove_frost()

        self._check_and_set_phosphorus_map() # this locks
        self._prep_phosphorus()

        if (baseflow is None and self.run_baseflow) or baseflow:
            self._check_and_set_baseflow_map() # this locks
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


    def _prep_revegetation(self):
        self.logger.info('    _prep_revegetation... ')

        self.logger.info('      prep pw0.cov... ')
        from wepppy.nodb.mods import RAP_TS
        rap_ts = RAP_TS.getInstance(self.wd)
        climate = self.climate_instance
        cli = ClimateFile(climate.cli_path)
        years = cli.years
        assert min(years) == rap_ts.rap_start_year, 'RAP_TS start year does not match climate'
        assert max(years) == rap_ts.rap_end_year, 'RAP_TS end year does not match climate'

        rap_ts.prep_cover(self.runs_dir)
        self._prep_firedate()

    def _prep_firedate(self):

        self.logger.info('    prep firedate.txt... ')
        disturbed = Disturbed.getInstance(self.wd)
        if disturbed.fire_date is not None:
            with open(_join(self.runs_dir, 'firedate.txt'), 'w') as fp:
                firedate = disturbed.fire_date
                mo, da, yr = firedate.strip().replace('/', ' ').replace('-', ' ').split()
                assert isint(mo), mo
                assert isint(da), da
                assert isint(yr), yr
                fp.write(firedate)

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
        return getattr(self, '_pmet_kcb_map', None)

    @pmet_kcb.setter
    @nodb_setter
    def pmet_kcb(self, value):
        self._pmet_kcb = value

    @property
    def pmet_rawp(self):
        return getattr(self, '_pmet_rawp', self.config_get_float('wepp', 'pmet_rawp'))

    @pmet_rawp.setter
    @nodb_setter
    def pmet_rawp(self, value):
        self._pmet_rawp = value

    def _prep_pmet(self, kcb=None, rawp=None):

        if kcb is not None and rawp is not None:
            self.logger.info(f'nodb.Wepp._prep_pmet::kwargs routine')
            pmetpara_prep(self.runs_dir, kcb=kcb, rawp=rawp)
            assert _exists(_join(self.runs_dir, 'pmetpara.txt'))
            return

        pmet_kcb_map = self.pmet_kcb_map
        if pmet_kcb_map is not None:
            rdi = RasterDatasetInterpolator(pmet_kcb_map)
            wd = self.wd
            watershed = self.watershed_instance
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
                self.logger.info(f'nodb.Wepp._prep_pmet::kcb_map routine')
                pmetpara_prep(self.runs_dir, kcb=kcb, rawp=self.pmet_rawp)
                assert _exists(_join(self.runs_dir, 'pmetpara.txt'))
                return

        if 'disturbed' not in self.mods:
            self.logger.info(f'nodb.Wepp._prep_pmet::defaults routine')
            pmetpara_prep(self.runs_dir, kcb=self.pmet_kcb, rawp=self.pmet_rawp)
            assert _exists(_join(self.runs_dir, 'pmetpara.txt'))
            return

        self.logger.info(f'nodb.Wepp._prep_pmet::disturbed routine')
        from wepppy.nodb.mods import Disturbed
        disturbed = Disturbed.getInstance(self.wd)
        disturbed.pmetpara_prep()
        assert _exists(_join(self.runs_dir, 'pmetpara.txt'))


    def _remove_pmet(self):
        fn = _join(self.runs_dir, 'pmet.txt')
        if _exists(fn):
            os.remove(fn)

    def _check_and_set_phosphorus_map(self):

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
        watershed = self.watershed_instance
        lng, lat = watershed.outlet.actual_loc

        if p_surf_runoff_map is not None:
            p_surf_runoff = RasterDatasetInterpolator(p_surf_runoff_map).get_location_info(lng, lat, method='nearest')
            if p_surf_runoff > 0.0:
                self.logger.info('wepp:_prep_phosphorus setting surf_runoff to {} from map'.format(p_surf_runoff))
                phos_opts.surf_runoff = float(p_surf_runoff)

        if p_lateral_flow_map is not None:
            p_lateral_flow = RasterDatasetInterpolator(p_lateral_flow_map).get_location_info(lng, lat, method='nearest')
            if p_lateral_flow > 0.0:
                self.logger.info('wepp:_prep_phosphorus setting lateral_flow to {} from map'.format(p_lateral_flow))
                phos_opts.lateral_flow = float(p_lateral_flow)

        if p_baseflow_map is not None:
            p_baseflow = RasterDatasetInterpolator(p_baseflow_map).get_location_info(lng, lat, method='nearest')
            if p_baseflow > 0.0:
                self.logger.info('wepp:_prep_phosphorus setting baseflow to {} from map'.format(p_baseflow))
                phos_opts.baseflow = float(p_baseflow)

        if  p_sediment_map is not None:
            p_sediment = RasterDatasetInterpolator(p_sediment_map).get_location_info(lng, lat, method='nearest')
            if p_sediment > 0.0:
                self.logger.info('wepp:_prep_phosphorus setting sediment to {} from map'.format(p_sediment))
                phos_opts.sediment = float(p_sediment)

        # save the phosphorus parameters to the .nodb
        with self.locked():
            self.phosphorus_opts = phos_opts

    def _prep_phosphorus(self):
        phos_opts = self.phosphorus_opts

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

    def _check_and_set_baseflow_map(self):
        baseflow_opts = self.baseflow_opts

        gwstorage_map = getattr(self, 'baseflow_gwstorage_map', None)
        bfcoeff_map = getattr(self, 'baseflow_bfcoeff_map', None)
        dscoeff_map = getattr(self, 'baseflow_dscoeff_map', None)
        bfthreshold_map = getattr(self, 'baseflow_bfthreshold_map', None)

        watershed = self.watershed_instance
        lng, lat = watershed.outlet.actual_loc

        if gwstorage_map is not None:
            gwstorage = RasterDatasetInterpolator(gwstorage_map).get_location_info(lng, lat, method='nearest')
            if gwstorage >= 0.0:
                self.logger.info('wepp:_prep_baseflow setting gwstorage to {} from map'.format(gwstorage))
                baseflow_opts.gwstorage = float(gwstorage)

        if bfcoeff_map is not None:
            bfcoeff = RasterDatasetInterpolator(bfcoeff_map).get_location_info(lng, lat, method='nearest')
            if bfcoeff >= 0.0:
                self.logger.info('wepp:_prep_baseflow setting bfcoeff to {} from map'.format(bfcoeff))
                baseflow_opts.bfcoeff = float(bfcoeff)

        if dscoeff_map is not None:
            dscoeff = RasterDatasetInterpolator(dscoeff_map).get_location_info(lng, lat, method='nearest')
            if dscoeff >= 0.0:
                self.logger.info('wepp:_prep_baseflow setting dscoeff to {} from map'.format(dscoeff))
                baseflow_opts.dscoeff = float(dscoeff)

        if bfthreshold_map is not None:
            bfthreshold = RasterDatasetInterpolator(bfthreshold_map).get_location_info(lng, lat, method='nearest')
            if bfthreshold >= 0.0:
                self.logger.info('wepp:_prep_baseflow setting bfthreshold to {} from map'.format(bfthreshold))
                baseflow_opts.bfthreshold = float(bfthreshold)

        # save the baseflow parameters to the .nodb
        with self.locked():
            self.baseflow_opts = baseflow_opts

    def _prep_baseflow(self):
        climate = self.climate_instance
        if climate.is_single_storm:
            baseflow_opts = BaseflowOpts(gwstorage=0.0, bfcoeff=0.0)
        else:
            baseflow_opts = self.baseflow_opts

        fn = _join(self.runs_dir, 'gwcoeff.txt')
        with open(fn, 'w') as fp:
            fp.write(baseflow_opts.contents)

    def _remove_baseflow(self):
        fn = _join(self.runs_dir, 'gwcoeff.txt')
        if _exists(fn):
            os.remove(fn)

    def clean(self):
        for _dir in (self.runs_dir, self.output_dir, self.plot_dir,
                     self.stats_dir, self.fp_runs_dir, self.fp_output_dir):
            if _exists(_dir):
                try:
                    shutil.rmtree(_dir)
                except Exception as exc:
                    self.logger.warning(f'Cleanup unable to remove {_dir} on first attempt: {exc}', exc_info=True)
                    sleep(1.0)
                    try:
                        shutil.rmtree(_dir)
                    except Exception as retry_exc:
                        self.logger.error(f'Cleanup failed to remove {_dir} after retry: {retry_exc}', exc_info=True)
                        raise RuntimeError(f"Failed to clean directory '{_dir}'") from retry_exc

            try:
                os.makedirs(_dir, exist_ok=True)
            except Exception as exc:
                self.logger.error(f'Cleanup failed to recreate {_dir}: {exc}', exc_info=True)
                raise

        climate = self.climate_instance
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                ss_batch_dir = _join(self.output_dir, ss_batch_key)
                if not _exists(ss_batch_dir):
                    os.makedirs(ss_batch_dir)

    def prep_and_run_flowpaths(self, clean_after_run=True):
        self.logger.info('  Prepping _prep_flowpaths... ')
        wat_dir = self.wat_dir

        fp_slps_fns = glob(_join(self.wat_dir, 'slope_files/flowpaths/*.slps'))
        
        futures = []
        with ThreadPoolExecutor(max_workers=10) as pool:
            for fp_slps_fn in fp_slps_fns:
                futures.append(pool.submit(extract_slps_fn, fp_slps_fn, self.fp_runs_dir))

            futures_n = len(futures)
            count = 0
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)

                if not done:
                    self.logger.error('  Flowpath slope extraction still running after 5 seconds.')
                    continue

                for future in done:
                    try:
                        future.result()
                        count += 1
                        self.logger.info(f'  ({count}/{futures_n}) flowpath slopes prep complete')
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        self.logger.error(f'  Flowpath slope extraction failed with an error: {exc}')
                        raise
            

        watershed = self.watershed_instance
        translator = watershed.translator_factory()
        sim_years = self.climate_instance.input_years

        fps_summary = watershed.fps_summary

        futures = []
        with ThreadPoolExecutor(max_workers=10) as pool:
            for topaz_id in fps_summary:
                wepp_id = translator.wepp(top=int(topaz_id))
                for fp_enum  in fps_summary[topaz_id]:
                    fp_id = f'fp_{wepp_id}_{fp_enum}'
                    self.logger.info(f'  Creating {fp_id}.run... ')
                    futures.append(pool.submit(make_flowpath_run, fp_id, wepp_id, sim_years, self.fp_runs_dir))

            futures_n = len(futures)
            count = 0
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)

                if not done:
                    self.logger.error('  Flowpath runfile creation still running after 5 seconds.')
                    continue

                for future in done:
                    try:
                        future.result()
                        count += 1
                        self.logger.info(f'  ({count}/{futures_n}) flowpath run files complete')
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        self.logger.error(f'  Flowpath runfile creation failed with an error: {exc}')
                        raise

        self.logger.info('  Running _run_flowpaths... ')

        futures = []
        with ThreadPoolExecutor(max_workers=10) as pool:
            for topaz_id in fps_summary:
                wepp_id = translator.wepp(top=int(topaz_id))
                for fp_enum  in fps_summary[topaz_id]:
                    fp_id = f'fp_{wepp_id}_{fp_enum}'
                    self.logger.info(f'  Running {fp_id}... ')
                    futures.append(pool.submit(run_flowpath, fp_id, wepp_id, self.runs_dir, self.fp_runs_dir, self.wepp_bin))

            futures_n = len(futures)
            count = 0
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

                if not done:
                    # Flowpath simulations can legitimately run for a long time; warn rather than error.
                    self.logger.warning('  Flowpath simulation still running after 60 seconds; continuing to wait.')
                    continue

                for future in done:
                    try:
                        future.result()
                        count += 1
                        self.logger.info(f'  ({count}/{futures_n}) flowpaths ran')
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        self.logger.error(f'  Flowpath simulation failed with an error: {exc}')
                        raise

        with self.timed('  Generating flowpath loss grid'):
            loss_grid_path = _join(self.plot_dir, 'flowpaths_loss.tif')

            if _exists(loss_grid_path):
                os.remove(loss_grid_path)
                time.sleep(1)

            make_soil_loss_grid_fps(watershed.discha, self.fp_runs_dir, loss_grid_path)
    
            assert _exists(loss_grid_path)

            loss_grid_wgs = _join(self.plot_dir, 'flowpaths_loss.WGS.tif')

            if _exists(loss_grid_wgs):
                os.remove(loss_grid_wgs)
                time.sleep(1)

            cmd = ['gdalwarp', '-t_srs', wgs84_proj4,
                '-srcnodata', '-9999', '-dstnodata', '-9999',
                '-r', 'near', loss_grid_path, loss_grid_wgs]
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            p.wait()

            assert _exists(loss_grid_wgs)

        if clean_after_run:
            self.logger.info('  Cleaning up flowpath run files... ')
            shutil.rmtree(self.fp_runs_dir)
            shutil.rmtree(self.fp_output_dir)

            os.makedirs(self.fp_runs_dir)
            os.makedirs(self.fp_output_dir)

    def _prep_slopes_peridot(self, watershed, translator, clip_hillslopes, clip_hillslope_length):
        self.logger.info('    Prepping _prep_slopes_peridot... ')
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id in watershed._subs_summary:
            wepp_id = translator.wepp(top=int(topaz_id))

            src_fn = _join(wat_dir, 'slope_files/hillslopes/hill_{}.slp'.format(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            if clip_hillslopes:
                clip_slope_file_length(src_fn, dst_fn, clip_hillslope_length)
            else:
                _copyfile(src_fn, dst_fn)

    def _prep_slopes(self, translator, clip_hillslopes, clip_hillslope_length):
        self.logger.info('    Prepping _prep_slopes... ')

        watershed = self.watershed_instance
        if watershed.abstraction_backend == 'peridot':
            return self._prep_slopes_peridot(watershed, translator, clip_hillslopes, clip_hillslope_length)

        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id in watershed._subs_summary:
            wepp_id = translator.wepp(top=int(topaz_id))

            src_fn = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            if clip_hillslopes:
                clip_slope_file_length(src_fn, dst_fn, clip_hillslope_length)
            else:
                _copyfile(src_fn, dst_fn)

    def _prep_multi_ofe(self, translator):
        from wepppy.topo.watershed_abstraction import HillSummary as WatHillSummary

        self.logger.info('    Prepping _prep_multi_ofe... ')
        wd = self.wd

        landuse = self.landuse_instance
        climate = self.climate_instance
        watershed = self.watershed_instance
        soils = self.soils_instance

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

        for topaz_id, ss in watershed.subs_summary.items():
            wepp_id = translator.wepp(top=int(topaz_id))
            lng, lat = watershed.hillslope_centroid_lnglat(topaz_id)

            # slope files
            src_fn = _join(wat_dir, f'slope_files/hillslopes/hill_{topaz_id}.mofe.slp')
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            _copyfile(src_fn, dst_fn)

            # soils
            src_fn = _join(soils_dir, f'hill_{topaz_id}.mofe.sol')
            dst_fn = _join(runs_dir, 'p%i.sol' % wepp_id)

            _kslast = None

            if kslast_map is not None:
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
        self.logger.info('    _prep_managements... ')
        from wepppy.nodb.mods import RAP_TS

        wd = self.wd

        landuse = self.landuse_instance
        hillslope_cancovs = landuse.hillslope_cancovs

        climate = self.climate_instance
        watershed = self.watershed_instance
        soils = self.soils_instance
        disturbed = Disturbed.tryGetInstance(wd)
        if disturbed is not None:
            _land_soil_replacements_d = disturbed.land_soil_replacements_d
        else:
            _land_soil_replacements_d = None

        rap_ts = RAP_TS.tryGetInstance(wd)

        years = climate.input_years
        year0 = climate.year0

        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        bd_d = soils.bd_d

        build_d = {}

        for i, (topaz_id, mukey) in enumerate(soils.domsoil_d.items()):
            if (int(topaz_id) - 4) % 10 == 0:
                continue
            dom = landuse.domlc_d[topaz_id]

            self.logger.info(f'    _prep_managements:{topaz_id}:{mukey} - {dom}... ')

            man_summary = landuse.managements[dom]

            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.man' % wepp_id)
            
            meoization_key = (mukey, dom)
            if disturbed:
                disturbed_class = man_summary.disturbed_class
                meoization_key = (mukey, dom, disturbed_class)

            if rap_ts is not None:
                meoization_key = (topaz_id, mukey, dom)

            if meoization_key in build_d:
                shutil.copyfile(build_d[meoization_key], dst_fn)

                self.logger.info(f"     copying build_d['{meoization_key}'] -> {dst_fn}")

            else:
                management = man_summary.get_management()
                sol_key = soils.domsoil_d[topaz_id]
                management.set_bdtill(bd_d[sol_key])

                # probably isn't the right location for this code. should be in nodb.disturbed
                if disturbed is not None:
                    if isinstance(disturbed_class, str):  # occured with No Data class with c3s-disturbed map
                        if 'mulch' in disturbed_class:
                            disturbed_class = 'mulch'
                        elif 'thinning' in disturbed_class:
                            disturbed_class = 'thinning'

                    if hillslope_cancovs is not None and 'mulch' not in disturbed_class and 'thinning' not in disturbed_class:
                        assert rap_ts is None, 'project has rap and rap_ts'
                        management.set_cancov(hillslope_cancovs[str(topaz_id)])

                    _soil = soils.soils[mukey]
                    clay = _soil.clay
                    sand = _soil.sand
                    texid = simple_texture(clay=clay, sand=sand)

                    if (texid, disturbed_class) not in _land_soil_replacements_d:
                        self.logger.info(f'     _prep_managements: {texid}:{disturbed_class} not in replacements_d')

                    if disturbed_class is None or 'developed' in disturbed_class or disturbed_class == '':
                        rdmax = None
                        xmxlai = None
                    else:
                        rdmax = _land_soil_replacements_d[(texid, disturbed_class)].get('rdmax', None)
                        if man_summary.cancov_override is None:
                            xmxlai = _land_soil_replacements_d[(texid, disturbed_class)].get('xmxlai', None)
                        else:
                            rdmax = None
                            xmxlai = None

                    if isfloat(rdmax):
                        management.set_rdmax(float(rdmax))

                    if isfloat(xmxlai):
                        management.set_xmxlai(float(xmxlai))

                    if (texid, disturbed_class) in _land_soil_replacements_d:
                        for (attr, value) in _land_soil_replacements_d[(texid, disturbed_class)].items():
                            if attr.startswith('plant.data.') or attr.startswith('ini.data.'):
                                management[attr] = value

                    meoization_key = (mukey, dom, disturbed_class)

                if rap_ts is not None:
                    if year0 >= rap_ts.rap_start_year and year0 <= rap_ts.rap_end_year:
                        cover = rap_ts.get_cover(topaz_id, year0, fallback=True)
                        management.set_cancov(cover)

                multi = management.build_multiple_year_man(years)

                fn_contents = str(multi)

                with open(dst_fn, 'w') as fp:
                    fp.write(fn_contents)

                build_d[meoization_key] = dst_fn
                self.logger.info(f'     meoization_key: {meoization_key} -> {dst_fn}')

        if 'emapr_ts' in self.mods:
            self.logger.info('    _prep_managements:emapr_ts.analyze... ')
            from wepppy.nodb.mods import OSUeMapR_TS
            assert climate.observed_start_year is not None
            assert climate.observed_end_year is not None

            emapr_ts = OSUeMapR_TS.getInstance(wd)
            emapr_ts.acquire_rasters(start_year=climate.observed_start_year,
                                     end_year=climate.observed_end_year)
            emapr_ts.analyze()

    def _prep_soils(self, translator, max_workers=None):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(translator={translator})')
    
        cpu_count = os.cpu_count() or 1
        if max_workers is None:
            max_workers = cpu_count

        if max_workers < 1:
            max_workers = 1
        if max_workers > max(cpu_count, 20):
            max_workers = max(cpu_count, 20)

        self.logger.info(f'  Using max_workers={max_workers} for soil prep')

        soils = self.soils_instance
        soils_dir = self.soils_dir
        watershed = self.watershed_instance
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        kslast = self.kslast
        clip_soils = soils.clip_soils
        clip_soils_depth = soils.clip_soils_depth
        initial_sat = soils.initial_sat

        kslast_map_fn = self.kslast_map
        kslast_map = RasterDatasetInterpolator(kslast_map_fn) if kslast_map_fn is not None else None

        task_args_list = []
        for topaz_id, soil in soils.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            src_fn = _join(soils_dir, soil.fname)
            dst_fn = _join(runs_dir, f'p{wepp_id}.sol')

            _kslast = None
            modify_kslast_pars = None

            if kslast_map is not None:
                lng, lat = watershed.hillslope_centroid_lnglat(topaz_id)
                try:
                    _kslast = kslast_map.get_location_info(lng, lat, method='nearest')
                    modify_kslast_pars = dict(map_fn=kslast_map, lng=lng, lat=lat, kslast=_kslast)
                except RDIOutOfBoundsException:
                    _kslast = None

                if not isfloat(_kslast):
                    _kslast = kslast if kslast is not None else None
                elif _kslast <= 0.0:
                    _kslast = kslast if kslast is not None else None
            elif kslast is not None:
                _kslast = kslast

            task_args_list.append(
                (
                    topaz_id,
                    src_fn,
                    dst_fn,
                    _kslast,
                    modify_kslast_pars,
                    initial_sat,
                    clip_soils,
                    clip_soils_depth,
                )
            )

        if not task_args_list:
            self.logger.info('  No soils require preparation.')
            return

        run_concurrent = 1

        def _run_soil_prep_pool(prefer_spawn: bool):
            try:
                with createProcessPoolExecutor(
                    max_workers=max_workers,
                    logger=self.logger,
                    prefer_spawn=prefer_spawn,
                ) as executor:
                    futures = [executor.submit(prep_soil, args) for args in task_args_list]

                    futures_n = len(futures)
                    count = 0
                    pending_futures = set(futures)
                    last_progress_time = time.time()

                    while pending_futures:
                        done, pending_futures = wait(pending_futures, timeout=5, return_when=FIRST_COMPLETED)

                        if not done:
                            since_progress = time.time() - last_progress_time
                            pending_count = len(pending_futures)

                            if since_progress >= 60:
                                self.logger.error(
                                    '  Soil prep tasks still pending after %.1fs; %s tasks waiting.',
                                    round(since_progress, 1), pending_count,
                                )
                            else:
                                self.logger.info(
                                    '  Waiting on soil prep tasks (pending=%s, %.1fs since last completion).',
                                    pending_count,
                                    round(since_progress, 1),
                                )
                            continue

                        for future in done:
                            try:
                                topaz_id, elapsed_time = future.result()
                                count += 1
                                self.logger.info(
                                    f'  ({count}/{futures_n}) Completed soil prep for {topaz_id} in {elapsed_time}s'
                                )
                                last_progress_time = time.time()
                            except BrokenProcessPool as exc:
                                self.logger.error(
                                    '  Soil prep process pool terminated unexpectedly: %s', exc
                                )
                                for pending_future in pending_futures:
                                    pending_future.cancel()
                                return False, exc
                            except Exception as exc:
                                self.logger.error(
                                    f'  A soil prep task failed with an error: {exc}'
                                )
                                for pending_future in pending_futures:
                                    pending_future.cancel()
                                return False, exc

                    return True, None
            except BrokenProcessPool as exc:
                self.logger.error(
                    '  Failed to initialize soil prep process pool: %s', exc
                )
                return False, exc
            except Exception as exc:
                self.logger.error(
                    '  Unexpected error during soil prep pool execution: %s', exc
                )
                return False, exc

        def _run_soil_prep_sequential():
            total = len(task_args_list)
            self.logger.warning('  Running soil prep sequentially')
            for idx, task_args in enumerate(task_args_list, start=1):
                topaz_id, elapsed_time = prep_soil(task_args)
                self.logger.info(
                    f'  ({idx}/{total}) Completed soil prep for {topaz_id} in {elapsed_time}s [sequential]'
                )

        self.logger.info(f'  run_concurrent={run_concurrent}')
        if run_concurrent:
            self.logger.info('  Submitting soils for `prep_soil` to ProcessPoolExecutor')
            success, failure_exc = _run_soil_prep_pool(prefer_spawn=True)

            if not success and isinstance(failure_exc, BrokenProcessPool):
                self.logger.warning(
                    '  Retrying soil prep with fork-based executor after spawn failure'
                )
                success, failure_exc = _run_soil_prep_pool(prefer_spawn=False)

            if not success:
                if isinstance(failure_exc, BrokenProcessPool):
                    self.logger.warning(
                        '  Falling back to sequential soil prep after process pool failures'
                    )
                    _run_soil_prep_sequential()
                else:
                    raise failure_exc
        else:
            _run_soil_prep_sequential()


    @nodb_timed
    def _prep_climates(self, translator):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(translator={translator})')

        climate = self.climate_instance
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            self.logger.info('    _prep_climates_ss_batch... ')
            return self._prep_climates_ss_batch(translator)
        
        watershed = self.watershed_instance
        cli_dir = self.cli_dir
        runs_dir = self.runs_dir

        sub_n = watershed.sub_n
        count = 0
        for topaz_id in watershed._subs_summary:
            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.cli' % wepp_id)

            cli_summary = climate.sub_summary(topaz_id)
            src_fn = _join(cli_dir, cli_summary['cli_fn'])
            _copyfile(src_fn, dst_fn) 
            count += 1
            self.logger.info(f' ({count}/{sub_n}) topaz_id: {topaz_id} | {src_fn} -> {dst_fn}')

    def _prep_climates_ss_batch(self, translator):
        climate = self.climate_instance

        self.logger.info('    _prep_climates_ss_batch... ')
        watershed = self.watershed_instance
        cli_dir = self.cli_dir
        runs_dir = self.runs_dir

        for d in climate.ss_batch_storms:
            ss_batch_id = d['ss_batch_id']
            ss_batch_key = d['ss_batch_key']
            cli_fn = d['cli_fn']

            for topaz_id in watershed._subs_summary:
                self.logger.info(f'    _prep_climates:{topaz_id}... ')

                wepp_id = translator.wepp(top=int(topaz_id))
                dst_fn = _join(runs_dir, f'p{wepp_id}.{ss_batch_id}.cli')

                src_fn = _join(cli_dir, cli_fn)
                _copyfile(src_fn, dst_fn)

            dst_fn = _join(runs_dir, f'pw0.{ss_batch_id}.cli')
            src_fn = _join(cli_dir, cli_fn)
            _copyfile(src_fn, dst_fn)

    def _make_hillslope_runs(self, translator, reveg=False,
                  man_relpath='', cli_relpath='', slp_relpath='', sol_relpath=''):
        self.logger.info('    Prepping _make_hillslope_runs... ')
        watershed = self.watershed_instance
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        climate = self.climate_instance
        years = climate.input_years

        if climate.climate_mode in [ClimateMode.SingleStorm, ClimateMode.UserDefinedSingleStorm]:
            for topaz_id in watershed._subs_summary:
                wepp_id = translator.wepp(top=int(topaz_id))

                make_ss_hillslope_run(wepp_id, runs_dir,
                                      man_relpath=man_relpath,
                                      cli_relpath=cli_relpath,
                                      slp_relpath=slp_relpath,
                                      sol_relpath=sol_relpath)

        elif climate.climate_mode == ClimateMode.SingleStormBatch:
            for topaz_id in watershed._subs_summary:
                wepp_id = translator.wepp(top=int(topaz_id))

                for d in climate.ss_batch_storms:
                    ss_batch_id = d['ss_batch_id']
                    ss_batch_key = d['ss_batch_key']
                    make_ss_batch_hillslope_run(wepp_id, 
                                                runs_dir, 
                                                ss_batch_id=ss_batch_id, 
                                                ss_batch_key=ss_batch_key,
                                                man_relpath=man_relpath,
                                                cli_relpath=cli_relpath,
                                                slp_relpath=slp_relpath,
                                                sol_relpath=sol_relpath)
        else:
            for topaz_id in watershed._subs_summary:
                wepp_id = translator.wepp(top=int(topaz_id))
                make_hillslope_run(wepp_id, 
                                   years, 
                                   runs_dir, 
                                   reveg=reveg,
                                   man_relpath=man_relpath,
                                   cli_relpath=cli_relpath,
                                   slp_relpath=slp_relpath,
                                   sol_relpath=sol_relpath)

    def run_hillslopes(self,
                  man_relpath='', cli_relpath='', slp_relpath='', sol_relpath='',
                  max_workers=None):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        cpu_count = os.cpu_count() or 1
        if max_workers is None:
            max_workers = cpu_count
        if max_workers < 1:
            max_workers = 1
        if max_workers > max(cpu_count, 16):
            max_workers = max(cpu_count, 16)

        self.logger.info(f'Running Hillslopes with max_workers={max_workers}')
        watershed = self.watershed_instance
        translator = watershed.translator_factory()
        climate = self.climate_instance
        landuse = self.landuse_instance
        runs_dir = os.path.abspath(self.runs_dir)
        fp_runs_dir = self.fp_runs_dir
        wepp_bin = self.wepp_bin

        self.logger.info(f'    wepp_bin:{wepp_bin}')

        sub_n = watershed.sub_n

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = []
            if climate.climate_mode == ClimateMode.SingleStormBatch:
                self.logger.info(f'  Submitting {sub_n} hillslope runs to ThreadPoolExecutor - SS batch')
                for i, topaz_id in enumerate(watershed._subs_summary):
                    self.logger.info(f'  submitting {topaz_id} to executor')

                    dom = landuse.domlc_d[topaz_id]
                    man = landuse.managements[dom]
                    if man.disturbed_class in ["agriculture crops"]:
                        wepp_bin = "wepp_dcc52a6"
                    self.logger.info(f'  using {wepp_bin} for {topaz_id} ({man.disturbed_class})')
                        
                    ss_n = len(climate.ss_batch_storms)
                    for d in climate.ss_batch_storms:
                        ss_batch_id = d['ss_batch_id']
                        ss_batch_key = d['ss_batch_key']

                        wepp_id = translator.wepp(top=int(topaz_id))
                        futures.append(pool.submit(
                            run_ss_batch_hillslope,
                            wepp_id=wepp_id,
                            runs_dir=runs_dir,
                            wepp_bin=wepp_bin,
                            ss_batch_id=ss_batch_id,
                            man_relpath=man_relpath,
                            cli_relpath=cli_relpath,
                            slp_relpath=slp_relpath,
                            sol_relpath=sol_relpath
                        ))

            else:
                self.logger.info(f'  Submitting {sub_n} hillslope runs to ThreadPoolExecutor - no SS batch')
                for i, topaz_id in enumerate(watershed._subs_summary):
                    self.logger.info(f'  submitting {topaz_id} to executor')

                    dom = landuse.domlc_d[topaz_id]
                    man = landuse.managements[dom]
                    if man.disturbed_class in ["agriculture crops"]:
                        wepp_bin = "wepp_dcc52a6"
                    self.logger.info(f'  using {wepp_bin} for {topaz_id} ({man.disturbed_class})')

                    wepp_id = translator.wepp(top=int(topaz_id))
                    futures.append(pool.submit(
                        run_hillslope,
                        wepp_id=wepp_id,
                        runs_dir=runs_dir,
                        wepp_bin=wepp_bin,
                        man_relpath=man_relpath,
                        cli_relpath=cli_relpath,
                        slp_relpath=slp_relpath,
                        sol_relpath=sol_relpath
                    ))

            futures_n = len(futures)
            count = 0
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)

                if not done:
                    # Hillslope runs can legitimately extend well beyond 30s; this warning is purely observational.
                    self.logger.warning('  Hillslope simulations still running after 30 seconds; continuing to wait.')
                    continue

                for future in done:
                    try:
                        status, _id, elapsed_time = future.result()
                        count += 1
                        self.logger.info(f'  ({count}/{futures_n})  wepp hillslope {_id} completed in {elapsed_time}s with status={status}')
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        self.logger.error(f'  Hillslope simulation failed with an error: {exc}')
                        raise

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.run_wepp_hillslopes)
        except FileNotFoundError:
            pass

    #
    # watershed
    #
    def prep_watershed(self, erodibility=None, critical_shear=None,
                       tcr=None, avke=None,
                       channel_manning_roughness_coefficient_bare=None,
                       channel_manning_roughness_coefficient_veg=None):
        self.logger.info('Prepping Watershed... ')

        watershed = self.watershed_instance
        translator = watershed.translator_factory()

        if critical_shear is None:
            crit_shear_map = getattr(self, 'channel_critical_shear_map', None)

            if crit_shear_map is not None:
                lng, lat = watershed.centroid
                rdi = RasterDatasetInterpolator(crit_shear_map)
                critical_shear = rdi.get_location_info(lng, lat, method='nearest')
                self.logger.info(f'critical_shear from map {crit_shear_map} at {watershed.centroid} ={critical_shear}... ')

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

        self.trigger(TriggerEvents.WEPP_PREP_WATERSHED_COMPLETE)

    def _prep_structure(self, translator):
        self.logger.info('    Prepping _prep_structure... ')

        watershed = self.watershed_instance
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

        src_fn = _join(wat_dir, 'slope_files/channels.slp')
        if not _exists(src_fn):
            src_fn = _join(wat_dir, 'channels.slp')


        with open(src_fn) as f:
            lines = f.readlines()
            version = lines[0].strip()

            if version.startswith('2023'):
                with open(_join(runs_dir, 'pw0.slp'), 'w') as f:
                    f.write('99.1\n')
                    n_chns = int(lines[1].strip())
                    f.write(f'{n_chns}\n')

                    i = 2
                    for j in range(n_chns):
                        aspect, width, elevation, order = lines[i].strip().split()

                        aspect = float(aspect)
                        if aspect < 0.0:
                            aspect += 360.0

                        width = float(width)
                        if width < 0.305:
                            width = 0.305

                        f.write(f'{aspect} {width}\n')
                        f.write(lines[i + 1])
                        f.write(lines[i + 2])

                        i += 3
            else:
                dst_fn = _join(runs_dir, 'pw0.slp')
                _copyfile(src_fn, dst_fn)

    def _prep_channel_chn(self, translator, erodibility, critical_shear,
                          channel_routing_method=ChannelRoutingMethod.MuskingumCunge,
                          channel_manning_roughness_coefficient_bare=None,
                          channel_manning_roughness_coefficient_veg=None):

        if erodibility is not None or critical_shear is not None:
            self.logger.info('nodb.Wepp._prep_channel_chn::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))

        if erodibility is None:
            erodibility = self.channel_erodibility

        if critical_shear is None:
            critical_shear = self.channel_critical_shear

        if channel_manning_roughness_coefficient_bare is None:
            channel_manning_roughness_coefficient_bare = self.channel_manning_roughness_coefficient_bare

        if channel_manning_roughness_coefficient_veg is None:
            channel_manning_roughness_coefficient_veg = self.channel_manning_roughness_coefficient_veg

        assert translator is not None

        watershed = self.watershed_instance
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

        for topaz_id, chn_summary in watershed.chns_summary.items():
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

    @property
    def dtchr_override(self):
        if hasattr(self, '_dtchr_override'):
            return self._dtchr_override
        return None

    @dtchr_override.setter
    @nodb_setter
    def dtchr_override(self, value: int):
        if value < 60:
            raise ValueError(f"Expected dtchr_override to be at least 60, got {value}")
        self._dtchr_override = value

    @property
    def chn_topaz_ids_of_interest(self):
        if hasattr(self, '_chn_topaz_ids_of_interest'):
            if not self._chn_topaz_ids_of_interest:
                return [24]
            return self._chn_topaz_ids_of_interest
        return [24]
    
    @chn_topaz_ids_of_interest.setter
    @nodb_setter
    def chn_topaz_ids_of_interest(self, value: list[int]):
        for topaz_id in value:
            if not str(topaz_id).endswith("4"):
                raise ValueError(f"Expected topaz_id to end with '4', got {topaz_id}")
        self._chn_topaz_ids_of_interest = [int(v) for v in value]

    def _prep_channel_input(self):
        translator = self.watershed_instance.translator_factory()
        climate = self.climate_instance

        ichout = 1
        dtchr = 600
        if climate.is_single_storm:  # and climate.is_breakpoint:
            ichout = 3
            dtchr = 60

        if hasattr(self, '_dtchr_override'):
            if isint(self._dtchr_override):
                dtchr = self._dtchr_override

        ichnum = [int(translator.wepp(top=topaz_id)) for topaz_id in self.chn_topaz_ids_of_interest]
        nchnum = len(ichnum)
        ichnum_str = ' '.join(map(str, ichnum))

        runs_dir = self.runs_dir
        with open(_join(runs_dir, 'chan.inp'), 'w') as fp:
            fp.write(f'{ichout} {dtchr}\n0\n{nchnum}\n{ichnum_str}\n')

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
            self.logger.info('nodb.Wepp._prep_channel_soils::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))

        if erodibility is None:
            erodibility = self.channel_erodibility

        if critical_shear is None:
            critical_shear = self.channel_critical_shear

        runs_dir = self.runs_dir

        watershed = self.watershed_instance
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
            self.logger.info('nodb.Wepp._prep_channel_soils::erodibility = {}, critical_shear = {} '
                     .format(erodibility, critical_shear))

        if erodibility is None:
            erodibility = self.channel_erodibility

        if critical_shear is None:
            critical_shear = self.channel_critical_shear

        if avke is not None:
            self.logger.info('nodb.Wepp._prep_channel_soils::avke = {} '
                     .format(avke))

        if avke is None:
            avke = self.channel_2006_avke

        soils = self.soils_instance
        runs_dir = self.runs_dir

        watershed = self.watershed_instance
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
        landuse = self.landuse_instance
        runs_dir = self.runs_dir

        years = self.climate_instance.input_years

        chn_n = self.watershed_instance.chn_n
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
        climate = self.climate_instance
        dst_fn = _join(runs_dir, 'pw0.cli')
        src_fn = _join(self.cli_dir, climate.cli_fn)
        _copyfile(src_fn, dst_fn)

    def make_watershed_run(self, wepp_id_paths=None):
        translator = self.watershed_instance.translator_factory()
        self._make_watershed_run(translator, wepp_id_paths=wepp_id_paths)

    def _make_watershed_run(self, translator, wepp_id_paths=None):
        runs_dir = self.runs_dir
        wepp_ids = list(translator.iter_wepp_sub_ids())
        wepp_ids.sort()

        climate = self.climate_instance
        years = climate.input_years

        if wepp_id_paths is not None:
            make_watershed_omni_contrasts_run(years, wepp_id_paths, runs_dir)
        elif climate.climate_mode in [ClimateMode.SingleStorm, ClimateMode.UserDefinedSingleStorm]:
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
        climate = self.climate_instance
        wepp_bin = self.wepp_bin
        self.logger.info(f'Running Watershed wepp_bin:{self.wepp_bin}')
        self.logger.info(f'    climate_mode:{climate.climate_mode.name}')
        self.logger.info(f'    output_dir:{self.output_dir}')
        self.logger.info(f'    runs_dir:{self.runs_dir}')

        runs_dir = self.runs_dir

        if climate.climate_mode == ClimateMode.SingleStormBatch:
            with self.timed('  Running watershed ss batch runs'):
                for d in climate.ss_batch_storms:
                    ss_batch_key = d['ss_batch_key']
                    ss_batch_id = d['ss_batch_id']
                    run_ss_batch_watershed(runs_dir, wepp_bin, ss_batch_id)

                    self.logger.info('    moving .out files...')
                    for fn in glob(_join(self.runs_dir, '*.out')):
                        dst_path = _join(self.output_dir, ss_batch_key, _split(fn)[1])
                        shutil.move(fn, dst_path)

        else:
            with self.timed('  Running watershed run'):
                assert run_watershed(runs_dir, wepp_bin='wepp_50k_2', status_channel=self._status_channel)

                self.logger.info('    moving .out files...')
                for fn in glob(_join(self.runs_dir, '*.out')):
                    dst_path = _join(self.output_dir, _split(fn)[1])
                    shutil.move(fn, dst_path)

        if not self.is_omni_contrasts_run:
            self.logger.info('  Not omni contrasts run, running post processing... ')

            if self.prep_details_on_run_completion:
                with self.timed('  Exporting prep details'):
                    export_channels_prep_details(wd)
                    export_hillslopes_prep_details(wd)

            climate = self.climate_instance

            if not climate.is_single_storm:
                with self.timed('  running totalwatsed3'):
                    self._build_totalwatsed3()

                with self.timed('  running hillslope_watbal'):
                    self._run_hillslope_watbal()

                if self.legacy_arc_export_on_run_completion:
                    with self.timed('  running legacy_arc_export'):
                        from wepppy.export import  legacy_arc_export
                        legacy_arc_export(self.wd)

            with self.timed('  generating loss report'):
                _ = self.loss_report # make the .parquet files for loss report

            if self.arc_export_on_run_completion:
                with self.timed('  running gpkg_export'):
                    from wepppy.export.gpkg_export import gpkg_export
                    gpkg_export(self.wd)

                    self.make_loss_grid()

        self.logger.info('Watershed Run Complete')

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.run_wepp_watershed)
        except FileNotFoundError:
            pass

        from wepppy.wepp.interchange.watershed_interchange import run_wepp_watershed_interchange
        from wepppy.wepp.interchange.interchange_documentation import generate_interchange_documentation

        run_wepp_watershed_interchange(self.output_dir)
        generate_interchange_documentation(self.wepp_interchange_dir)

    def post_discord_wepp_run_complete(self):
        if send_discord_message is not None:
            from wepppy.nodb.core import Ron

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

    @nodb_timed
    def _run_hillslope_watbal(self):
        HillslopeWatbalReport(self.wd)

    @nodb_timed
    def _build_totalwatsed3(self):
        from wepppy.wepp.interchange import run_totalwatsed3, generate_interchange_documentation
        run_totalwatsed3(self.wepp_interchange_dir, baseflow_opts=self.baseflow_opts)
        generate_interchange_documentation(self.wepp_interchange_dir)

    @nodb_timed
    def _export_partitioned_totalwatsed2_dss(self):
        from wepppy.wepp.interchange import totalwatsed_partitioned_dss_export
        totalwatsed_partitioned_dss_export(self.wd)

    def report_loss(self):
        from wepppy.wepp.interchange.watershed_loss import Loss
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        return Loss(loss_pw0, self.has_phosphorus, self.wd)

    def report_return_periods(self, rec_intervals=(50, 25, 20, 10, 5, 2), 
                              exclude_yr_indxs=None, 
                              method='cta', gringorten_correction=True, 
                              meoization=True,
                              exclude_months=None,
                              chn_topaz_id_of_interest=None):

        output_dir = self.output_dir

        return_periods_fn = None
        cached_report: ReturnPeriods | None = None
        if meoization:
            req_yrs = None if not exclude_yr_indxs else tuple(sorted({int(x) for x in exclude_yr_indxs}))
            req_mos = None if not exclude_months else tuple(sorted({int(x) for x in exclude_months}))

            parts = []
            if req_yrs:
                parts.append("exclude_yr_indxs=" + ",".join(map(str, req_yrs)))
            if req_mos:
                parts.append("exclude_months=" + ",".join(map(str, req_mos)))
            if gringorten_correction:
                parts.append("gringorten=True")
            if chn_topaz_id_of_interest is not None:
                parts.append("chn_topaz_id=" + str(chn_topaz_id_of_interest))
            suffix = ("__" + "__".join(parts)) if parts else ""
            return_periods_fn = _join(output_dir, f"return_periods{suffix}.json")

            if _exists(return_periods_fn):
                with open(return_periods_fn) as fp:
                    cached_report = ReturnPeriods.from_dict(json.load(fp))

                rep_yrs = getattr(cached_report, "exclude_yr_indxs", None)
                rep_mos = getattr(cached_report, "exclude_months", None)
                rep_yrs = None if not rep_yrs else tuple(sorted({int(x) for x in rep_yrs}))
                rep_mos = None if not rep_mos else tuple(sorted({int(x) for x in rep_mos}))

                if req_yrs == rep_yrs and req_mos == rep_mos:
                    return cached_report

        dataset = ReturnPeriodDataset(self.wd, auto_refresh=True)
        return_periods = dataset.create_report(
            rec_intervals,
            exclude_yr_indxs=exclude_yr_indxs,
            exclude_months=exclude_months,
            method=method,
            gringorten_correction=gringorten_correction,
            topaz_id=chn_topaz_id_of_interest,
        )

        if return_periods_fn is not None:
            with open(return_periods_fn, 'w') as fp:
                json.dump(return_periods.to_dict(), fp, cls=NumpyEncoder)

        return return_periods

    def export_return_periods_tsv_summary(self, rec_intervals=(50, 25, 20, 10, 5, 2), 
                           exclude_yr_indxs=None, 
                           method='cta', 
                           gringorten_correction=True, 
                           meoization=True,
                           extraneous=False):

        return_periods = self.report_return_periods(
            rec_intervals=rec_intervals, 
            exclude_yr_indxs=exclude_yr_indxs,
            method=method,
            gringorten_correction=gringorten_correction,
            meoization=meoization)

        if exclude_yr_indxs is not None:
            x = ','.join(str(v) for v in exclude_yr_indxs)
            fn = f'return_periods__exclude_yr_indxs={x}.tsv'
        else:
            fn = 'return_periods.tsv'

        if extraneous:
            fn = fn.replace('.tsv', '_extraneous.tsv')

        return_periods.export_tsv_summary(_join(self.export_dir, fn), extraneous=extraneous)

    def report_frq_flood(self):
        return FrqFloodReport(self.wd)

    def report_sediment_delivery(self):
        return SedimentCharacteristics(self.wd)

    def report_hill_watbal(self):
        return HillslopeWatbalReport(self.wd)

    def report_chn_watbal(self):
        return ChannelWatbalReport(self.wd)

    def set_run_flowpaths(self, state):
        assert state in [True, False]
        with self.locked():
            self.run_flowpaths = state

    def set_run_wepp_ui(self, state):
        assert state in [True, False]
        with self.locked():
            self._run_wepp_ui = state

    def set_run_pmet(self, state):
        assert state in [True, False]
        with self.locked():
            self._run_pmet = state

    def set_run_frost(self, state):
        assert state in [True, False]
        with self.locked():
            self._run_frost = state

    def set_run_snow(self, state):
        assert state in [True, False]
        with self.locked():
            self._run_snow = state

    def set_run_tcr(self, state):
        assert state in [True, False]
        with self.locked():
            self._run_tcr = state

    def set_run_baseflow(self, state):
        assert state in [True, False]
        with self.locked():
            self._run_baseflow = state

    @property
    def loss_report(self):
        from wepppy.wepp.interchange.watershed_loss import Loss
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

        translator = self.watershed_instance.translator_factory()

        def _resolve_identifier(row, *candidates):
            for key in candidates:
                if key not in row:
                    continue
                value = row.get(key)
                if value is None:
                    continue
                invalid = False
                try:
                    if value != value:
                        invalid = True
                except TypeError:
                    invalid = True
                if invalid:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    try:
                        return int(float(value))
                    except (TypeError, ValueError):
                        continue
            raise KeyError(f"Missing identifier columns {candidates} in loss hill record: {row}")

        d = {}
        for row in report.hill_tbl:
            wepp_id = _resolve_identifier(row, "wepp_id", "WeppID", "weppId", "Hillslopes")
            topaz_id = translator.top(wepp=wepp_id)

            v = row.get(measure, None)
            if isnan(v) or isinf(v):
                v = None

            d[str(topaz_id)] = dict(
                topaz_id=topaz_id,
                value=v
            )

        return d

    def query_chn_val(self, measure):
        from wepppy.wepp.interchange.watershed_loss import Loss
        wd = self.wd

        translator = self.watershed_instance.translator_factory()
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')

        if not _exists(loss_pw0):
            return None

        if not hasattr(self, '_loss_report'):
            self._loss_report = Loss(loss_pw0, self.has_phosphorus, self.wd)

        report = self._loss_report

        def _resolve_identifier(row, *candidates):
            for key in candidates:
                if key not in row:
                    continue
                value = row.get(key)
                if value is None:
                    continue
                invalid = False
                try:
                    if value != value:
                        invalid = True
                except TypeError:
                    invalid = True
                if invalid:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    try:
                        return int(float(value))
                    except (TypeError, ValueError):
                        continue
            raise KeyError(f"Missing identifier columns {candidates} in loss channel record: {row}")

        d = {}
        for row in report.chn_tbl:
            chn_enum = _resolve_identifier(row, "chn_enum", "Channels and Impoundments")
            topaz_id = translator.top(chn_enum=chn_enum)

            v = row.get(measure, None)
            if isnan(v) or isinf(v):
                v = None

            d[str(topaz_id)] = dict(
                topaz_id=topaz_id,
                value=v
            )

        return d

    def make_loss_grid(self):
        watershed = self.watershed_instance
        loss_grid_path = _join(self.plot_dir, 'loss.tif')
        print(watershed.subwta, watershed.discha, self.output_dir, loss_grid_path)

        assert _exists(watershed.subwta), f"{watershed.subwta} does not exist"
        assert _exists(watershed.discha), f"{watershed.discha} does not exist"
        assert len(glob(_join(self.output_dir, 'H*'))) > 0, f"{self.output_dir} does not contain outputs"

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
    @nodb_setter
    def kslast(self, value):
        self._kslast = value
