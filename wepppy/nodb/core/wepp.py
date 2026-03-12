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
import subprocess
from datetime import date
from contextlib import ExitStack
from enum import IntEnum
from pathlib import Path
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from typing import Optional, Dict, List, Tuple, Any, Set, TextIO

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

# nonstandard

import numpy as np
import json

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *

from wepppyo3.wepp_viz import make_soil_loss_grid, make_soil_loss_grid_fps

__all__ = [
    'ChannelRoutingMethod',
    'SnowOpts',
    'FrostOpts',
    'BaseflowOpts',
    'PhosphorusOpts',
    'TCROpts',
    'WeppNoDbLockedException',
    'Wepp',
]

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except ImportError:
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
    NumpyEncoder,
    NCPU,
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
from wepppy.nodb.core.management_overrides import apply_disturbed_management_overrides

from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.wepp.soils.utils import simple_texture
from wepppy.nodb.core.climate import ClimateMode
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.duckdb_agents import get_watershed_chns_summary
from wepppy.wepp.interchange.dss_dates import (
    format_dss_date,
    parse_dss_date,
)
from wepppy.wepp.interchange.versioning import Version, read_version_manifest
from wepppy.runtime_paths.wepp_inputs import (
    copy_input_file,
    glob_input_files,
    input_exists,
    materialize_input_file,
    open_input_text,
    with_input_file_path,
)
from wepppy.nodb.core.wepp_bootstrap_service import WeppBootstrapService
from wepppy.nodb.core.wepp_input_parser import WeppInputParser
from wepppy.nodb.core.wepp_postprocess_service import WeppPostprocessService
from wepppy.nodb.core.wepp_prep_service import WeppPrepService
from wepppy.nodb.core.wepp_run_service import WeppRunService

def _copyfile(src_fn: str, dst_fn: str) -> None:
    if _exists(dst_fn):
        os.remove(dst_fn)

    os.link(src_fn, dst_fn)


STORM_EVENT_ANALYZER_MIN_INTERCHANGE_VERSION = Version(major=1, minor=2)
BOOTSTRAP_JWT_EXPIRES_SECONDS = 180 * 24 * 60 * 60

_WEPP_INPUT_PARSER = WeppInputParser()
_WEPP_PREP_SERVICE = WeppPrepService()
_WEPP_RUN_SERVICE = WeppRunService()
_WEPP_POSTPROCESS_SERVICE = WeppPostprocessService()
_WEPP_BOOTSTRAP_SERVICE = WeppBootstrapService()


class ChannelRoutingMethod(IntEnum):
    Creams = 2
    MuskingumCunge = 4


class SnowOpts(object):
    rst: float
    newsnw: float
    ssd: float
    
    def __init__(self, rst: Optional[float] = None, newsnw: Optional[float] = None, ssd: Optional[float] = None) -> None:
        """
        Stores the coeffs that go into snow.txt
        """
        # rain-snow threshold
        if rst is None:
            self.rst = 0.0
        else:
            self.rst = rst

        # density of new snow (g/cm³)

        if newsnw is None:
            self.newsnw = 100.0
        else:
            self.newsnw = newsnw

        # snow settling density (g/cm³)
        if ssd is None:
            self.ssd = 250.0
        else:
            self.ssd = ssd

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        for var in ('rst', 'newsnw', 'ssd'):
            _var = f'snow_opts_{var}'
            if var in kwds:
                setattr(self, var, try_parse_float(kwds[var], None))
            elif _var in kwds:
                setattr(self, var, try_parse_float(kwds[_var], None))

    @property
    def contents(self) -> str:
        return (
            '{0.rst}  # rain-snow threshold\n'
            '{0.newsnw}  # density of new snow\n'
            '{0.ssd}  # snow settling density\n'
            .format(self)
        )


def _parse_optional_int(value: Any) -> Optional[int]:
    parsed = try_parse_float(value, None)
    if not isfloat(parsed):
        return None

    parsed_float = float(parsed)
    if isnan(parsed_float) or isinf(parsed_float):
        return None

    if not parsed_float.is_integer():
        return None

    return int(parsed_float)


class FrostOpts(object):
    """Stores the WEPP winter control coefficients for ``frost.txt``."""

    wintRed: int
    fineTop: int
    fineBot: int
    ksnowf: float
    kresf: float
    ksoilf: float
    kfactor1: float
    kfactor2: float
    kfactor3: float

    def __init__(
        self,
        wintRed: Optional[int] = None,
        fineTop: Optional[int] = None,
        fineBot: Optional[int] = None,
        ksnowf: Optional[float] = None,
        kresf: Optional[float] = None,
        ksoilf: Optional[float] = None,
        kfactor1: Optional[float] = None,
        kfactor2: Optional[float] = None,
        kfactor3: Optional[float] = None,
    ) -> None:
        # 1 = run water redistribution during frost simulation
        self.wintRed = 1 if wintRed is None else int(wintRed)

        # Number of fine layers in each top 10 cm section (1..10)
        self.fineTop = 10 if fineTop is None else int(fineTop)

        # Number of fine layers in deeper sections (1..10)
        self.fineBot = 10 if fineBot is None else int(fineBot)

        # Thermal conductivity multipliers
        self.ksnowf = 1.0 if ksnowf is None else float(ksnowf)
        self.kresf = 1.0 if kresf is None else float(kresf)
        self.ksoilf = 1.0 if ksoilf is None else float(ksoilf)

        # Frozen-soil conductivity lower limits by land cover class
        self.kfactor1 = 1e-5 if kfactor1 is None else float(kfactor1)
        self.kfactor2 = 1e-5 if kfactor2 is None else float(kfactor2)
        self.kfactor3 = 0.5 if kfactor3 is None else float(kfactor3)

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        int_fields = ('wintRed', 'fineTop', 'fineBot')
        float_fields = ('ksnowf', 'kresf', 'ksoilf', 'kfactor1', 'kfactor2', 'kfactor3')

        for var in int_fields:
            prefixed = f'frost_opts_{var}'
            if var in kwds:
                parsed = _parse_optional_int(kwds[var])
                if parsed is not None:
                    setattr(self, var, parsed)
            elif prefixed in kwds:
                parsed = _parse_optional_int(kwds[prefixed])
                if parsed is not None:
                    setattr(self, var, parsed)

        for var in float_fields:
            prefixed = f'frost_opts_{var}'
            if var in kwds:
                parsed = try_parse_float(kwds[var], None)
                if isfloat(parsed):
                    setattr(self, var, float(parsed))
            elif prefixed in kwds:
                parsed = try_parse_float(kwds[prefixed], None)
                if isfloat(parsed):
                    setattr(self, var, float(parsed))

    @property
    def contents(self) -> str:
        return (
            '{0.wintRed}  {0.fineTop}  {0.fineBot}\n'
            '{0.ksnowf}  {0.kresf}  {0.ksoilf}  {0.kfactor1}  {0.kfactor2}  {0.kfactor3}\n'
            .format(self)
        )


class BaseflowOpts(object):
    gwstorage: float
    bfcoeff: float
    dscoeff: float
    bfthreshold: float
    
    def __init__(self, gwstorage: Optional[float] = None, bfcoeff: Optional[float] = None, 
                 dscoeff: Optional[float] = None, bfthreshold: Optional[float] = None) -> None:
        """
        Stores the coeffs that go into gwcoeff.txt
        """
        # Initial groundwater storage (mm)
        if gwstorage is None:
            self.gwstorage = 200.0
        else:
            self.gwstorage = gwstorage

        # Baseflow coefficient (per day)
        if bfcoeff is None:
            self.bfcoeff = 0.04
        else:
            self.bfcoeff = bfcoeff

        # Deep seepage coefficient (per day)
        if dscoeff is None:
            self.dscoeff = 0.0
        else:
            self.dscoeff = dscoeff

        # Watershed groundwater baseflow threshold area (ha)
        if bfthreshold is None:
            self.bfthreshold = 1.0
        else:
            self.bfthreshold = bfthreshold

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        for var in ('gwstorage', 'bfcoeff', 'dscoeff', 'bfthreshold'):
            _var = f'baseflow_opts_{var}'

            if var in kwds:
                setattr(self, var, try_parse_float(kwds[var], None))
            elif _var in kwds:
                setattr(self, var, try_parse_float(kwds[_var], None))

    @property
    def contents(self) -> str:
        return (
            '{0.gwstorage}\tInitial groundwater storage (mm)\n'
            '{0.bfcoeff}\tBaseflow coefficient (per day)\n'
            '{0.dscoeff}\tDeep seepage coefficient (per day)\n'
            '{0.bfthreshold}\tWatershed groundwater baseflow threshold area (ha)\n\n'
            .format(self)
        )


def validate_phosphorus_txt(fn: str) -> bool:

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
    surf_runoff: Optional[float]
    lateral_flow: Optional[float]
    baseflow: Optional[float]
    sediment: Optional[float]
    
    def __init__(self, surf_runoff: Optional[float] = None, lateral_flow: Optional[float] = None, 
                 baseflow: Optional[float] = None, sediment: Optional[float] = None) -> None:
        # Surface runoff concentration (mg/l)
        self.surf_runoff = surf_runoff

        # Subsurface lateral flow concentration (mg/l)
        self.lateral_flow = lateral_flow

        # Baseflow concentration (mg/l)
        self.baseflow = baseflow

        # Sediment concentration (mg/kg)
        self.sediment = sediment

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        for var in ('surf_runoff', 'lateral_flow', 'baseflow', 'sediment'):
            _var = f'phosphorus_opts_{var}'

            if var in kwds:
                setattr(self, var, try_parse_float(kwds[var], None))
            elif _var in kwds:
                setattr(self, var, try_parse_float(kwds[_var], None))

    @property
    def isvalid(self) -> bool:
        return isfloat(self.surf_runoff) and \
               isfloat(self.lateral_flow) and \
               isfloat(self.baseflow) and \
               isfloat(self.sediment)

    @property
    def contents(self) -> str:
        return (
            'Phosphorus concentration\n'
            '{0.surf_runoff}\tSurface runoff concentration (mg/l)\n'
            '{0.lateral_flow}\tSubsurface lateral flow concentration (mg/l)\n'
            '{0.baseflow}\tBaseflow concentration (mg/l)\n'
            '{0.sediment}\tSediment concentration (mg/kg)\n\n'
            .format(self)
        )

    def asdict(self) -> Dict[str, Optional[float]]:
        return dict(surf_runoff=self.surf_runoff,
                    lateral_flow=self.lateral_flow,
                    baseflow=self.baseflow,
                    sediment=self.sediment)


class TCROpts(object):
    taumin: Optional[float]
    taumax: Optional[float]
    kch: Optional[float]
    nch: Optional[float]
    
    def __init__(self, taumin: Optional[float] = None, taumax: Optional[float] = None, 
                 kch: Optional[float] = None, nch: Optional[float] = None) -> None:
        """
        Stores the coeffs that go into tcr.txt
        """
        self.taumin = taumin
        self.taumax = taumax
        self.kch = kch
        self.nch = nch

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        for var in ('taumin', 'taumax', 'kch', 'nch'):
            _var = f'tcr_opts_{var}'

            if var in kwds:
                setattr(self, var, try_parse_float(kwds[var], None))
            elif _var in kwds:
                setattr(self, var, try_parse_float(kwds[_var], None))

    @property
    def contents(self) -> str:
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


def prep_soil(args: Tuple[str, str, str, Optional[float], Optional[Dict[str, Any]], float, bool, float]) -> Tuple[str, float]:
    t0 = time.time()
    # str,    str,    str,    float,  dict|None,          float,       bool,       float
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


def extract_slps_fn(slps_fn: str, fp_runs_dir: str) -> None:
    f: Optional[TextIO] = None
    with open(slps_fn) as fp:
        
        for line in fp:
            if line.startswith('# fp_') and line.endswith('.slp\n'):
                fp_fn = line.split()[1].strip()
                if f is not None:
                    f.close()

                f = open(_join(fp_runs_dir, fp_fn), 'w')

            elif f is not None:
                f.write(line)

        if f is not None:
            f.close()


class Wepp(NoDbBase):
    __name__ = 'Wepp'

    filename = 'wepp.nodb'

    _BASEFLOW_BFCOEFF_BOUNDS = (0.01, 0.1)
    _SNOW_NEWSNW_BOUNDS = (25.0, 500.0)
    _SNOW_SSD_BOUNDS = (75.0, 750.0)
    _TCR_TAUMIN_BOUNDS = (5.0, 400.0)
    _TCR_TAUMAX_BOUNDS = (5.0, 400.0)
    _FROST_WINTRED_BOUNDS = (0, 1)
    _FROST_FINETOP_BOUNDS = (1, 10)
    _FROST_FINEBOT_BOUNDS = (1, 10)
    _FROST_K_ADJUST_BOUNDS = (0.1, 10.0)
    _FROST_KFACTOR_BOUNDS = (0.0, 1.0)

    _SNOW_NEWSNW_DEFAULT = 100.0
    _SNOW_SSD_DEFAULT = 250.0
    _TCR_TAUMIN_DEFAULT = 35.0
    _TCR_TAUMAX_DEFAULT = 70.0
    _FROST_WINTRED_DEFAULT = 1
    _FROST_FINETOP_DEFAULT = 10
    _FROST_FINEBOT_DEFAULT = 10
    _FROST_KSNOWF_DEFAULT = 1.0
    _FROST_KRESF_DEFAULT = 1.0
    _FROST_KSOILF_DEFAULT = 1.0
    _FROST_KFACTOR1_DEFAULT = 1e-5
    _FROST_KFACTOR2_DEFAULT = 1e-5
    _FROST_KFACTOR3_DEFAULT = 0.5
    _BASEFLOW_BFCOEFF_DEFAULT = 0.04
    
    def __init__(self, wd: str, cfg_fn: str, run_group: Optional[str] = None, group_name: Optional[str] = None) -> None:
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

            self.frost_opts = FrostOpts(
                wintRed=self.config_get_int('frost_opts', 'wintRed'),
                fineTop=self.config_get_int('frost_opts', 'fineTop'),
                fineBot=self.config_get_int('frost_opts', 'fineBot'),
                ksnowf=self.config_get_float('frost_opts', 'ksnowf'),
                kresf=self.config_get_float('frost_opts', 'kresf'),
                ksoilf=self.config_get_float('frost_opts', 'ksoilf'),
                kfactor1=self.config_get_float('frost_opts', 'kfactor1'),
                kfactor2=self.config_get_float('frost_opts', 'kfactor2'),
                kfactor3=self.config_get_float('frost_opts', 'kfactor3'),
            )

            self.tcr_opts = TCROpts(
                taumin=self.config_get_float('tcr_opts', 'taumin'),
                taumax=self.config_get_float('tcr_opts', 'taumax'),
                kch=self.config_get_float('tcr_opts', 'kch'),
                nch=self.config_get_float('tcr_opts', 'nch'))

            self._guard_unitized_bounds()
           
            self.channel_critical_shear_map = self.config_get_path('wepp', 'channel_critical_shear_map')

            self.baseflow_opts = BaseflowOpts(
                gwstorage=self.config_get_float('baseflow_opts', 'gwstorage'),
                bfcoeff = self.config_get_float('baseflow_opts', 'bfcoeff'),
                dscoeff = self.config_get_float('baseflow_opts', 'dscoeff'),
                bfthreshold = self.config_get_float('baseflow_opts', 'bfthreshold'))

            self.baseflow_gwstorage_map = self.config_get_path('baseflow_opts', 'gwstorage_map')
            self.baseflow_bfcoeff_map = self.config_get_path('baseflow_opts', 'bfcoeff_map')
            self.baseflow_dscoeff_map = self.config_get_path('baseflow_opts', 'dscoeff_map')
            self.baseflow_bfthreshold_map = self.config_get_path('baseflow_opts', 'bfthreshold_map')
            self._guard_baseflow_bounds()

            self._run_wepp_ui = self.config_get_bool('wepp', 'wepp_ui')
            self._run_wepp_watershed = self.config_get_bool('wepp', 'run_wepp_watershed', True)
            self._run_pmet = self.config_get_bool('wepp', 'pmet')
            self._run_frost = self.config_get_bool('wepp', 'frost')
            self._run_tcr = self.config_get_bool('wepp', 'tcr')
            self._run_baseflow = self.config_get_bool('wepp', 'baseflow')
            self._run_snow = self.config_get_bool('wepp', 'snow')
            self._wepp_bin = self.config_get_str('wepp', 'bin')
            self._delete_after_interchange = self.config_get_bool(
                'interchange', 'delete_after_interchange', False
            )
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
            self._dss_export_mode = self.config_get_int('wepp', 'dss_export_mode', 1)  # view model property
            self._dss_export_on_run_completion = self.config_get_bool('wepp', 'dss_export_on_run_completion', False)  # view model property
            self._dss_excluded_channel_orders = self.config_get_list('wepp', 'dss_excluded_channel_orders', [1, 2])  # view model property
            self._dss_export_channel_ids = [] # specifies which channels are exported

            self._dtchr_override = None
            self._ichout_override = None
            self._chn_topaz_ids_of_interest = [24]

            self.run_flowpaths = False
            self.loss_grid_d_path = None
            self._bootstrap_enabled = False

            self.clean()
            self._mint_default_frost_file()

    @classmethod
    def _post_instance_loaded(cls, instance: 'Wepp') -> 'Wepp':
        instance = super()._post_instance_loaded(instance)

        if not hasattr(instance, '_dss_excluded_channel_orders') or instance._dss_excluded_channel_orders is None:
            instance._dss_excluded_channel_orders = instance.config_get_list(
                'wepp',
                'dss_excluded_channel_orders',
                [1, 2],
            )

        if not hasattr(instance, '_bootstrap_enabled'):
            instance._bootstrap_enabled = False
        if not hasattr(instance, "_delete_after_interchange"):
            instance._delete_after_interchange = instance.config_get_bool(
                "interchange",
                "delete_after_interchange",
                False,
            )
        if not hasattr(instance, 'frost_opts') or instance.frost_opts is None:
            instance.frost_opts = FrostOpts(
                wintRed=instance.config_get_int('frost_opts', 'wintRed'),
                fineTop=instance.config_get_int('frost_opts', 'fineTop'),
                fineBot=instance.config_get_int('frost_opts', 'fineBot'),
                ksnowf=instance.config_get_float('frost_opts', 'ksnowf'),
                kresf=instance.config_get_float('frost_opts', 'kresf'),
                ksoilf=instance.config_get_float('frost_opts', 'ksoilf'),
                kfactor1=instance.config_get_float('frost_opts', 'kfactor1'),
                kfactor2=instance.config_get_float('frost_opts', 'kfactor2'),
                kfactor3=instance.config_get_float('frost_opts', 'kfactor3'),
            )
        instance._guard_frost_bounds()
        instance._guard_baseflow_bounds()

        return instance

    def _bootstrap_git_dir(self) -> str:
        return _join(self.wd, ".git")

    def _bootstrap_repo_exists(self) -> bool:
        return _exists(self._bootstrap_git_dir())

    def _bootstrap_push_log_path(self) -> str:
        return _join(self._bootstrap_git_dir(), "bootstrap", "push-log.ndjson")

    def _load_bootstrap_push_log(self) -> dict[str, str]:
        return _WEPP_BOOTSTRAP_SERVICE.load_bootstrap_push_log(self)

    def _run_git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return _WEPP_BOOTSTRAP_SERVICE.run_git(self, args)

    def _write_bootstrap_gitignore(self) -> None:
        _WEPP_BOOTSTRAP_SERVICE.write_bootstrap_gitignore(self)

    def _install_bootstrap_hook(self) -> None:
        _WEPP_BOOTSTRAP_SERVICE.install_bootstrap_hook(self)

    @property
    def bootstrap_enabled(self) -> bool:
        return bool(getattr(self, "_bootstrap_enabled", False))

    @bootstrap_enabled.setter
    @nodb_setter
    def bootstrap_enabled(self, value: bool) -> None:
        self._bootstrap_enabled = bool(value)

    def init_bootstrap(self) -> None:
        _WEPP_BOOTSTRAP_SERVICE.init_bootstrap(self)

    def mint_bootstrap_jwt(self, user_email: str, user_id: str) -> str:
        return _WEPP_BOOTSTRAP_SERVICE.mint_bootstrap_jwt(
            self,
            user_email,
            user_id,
            expires_seconds=BOOTSTRAP_JWT_EXPIRES_SECONDS,
        )

    def get_bootstrap_commits(self) -> list[dict]:
        return _WEPP_BOOTSTRAP_SERVICE.get_bootstrap_commits(self)

    def checkout_bootstrap_commit(self, sha: str) -> bool:
        return _WEPP_BOOTSTRAP_SERVICE.checkout_bootstrap_commit(self, sha)

    def get_bootstrap_current_ref(self) -> str:
        return _WEPP_BOOTSTRAP_SERVICE.get_bootstrap_current_ref(self)

    def ensure_bootstrap_main(self) -> None:
        _WEPP_BOOTSTRAP_SERVICE.ensure_bootstrap_main(self)

    def _bootstrap_managed_paths(self) -> list[str]:
        paths: list[str] = []
        if _exists(_join(self.wd, "wepp", "runs")):
            paths.append("wepp/runs")
        if _exists(_join(self.wd, "swat", "TxtInOut")):
            paths.append("swat/TxtInOut")
        return paths

    def bootstrap_commit_inputs(self, stage: str) -> str | None:
        return _WEPP_BOOTSTRAP_SERVICE.bootstrap_commit_inputs(self, stage)

    def disable_bootstrap(self) -> None:
        _WEPP_BOOTSTRAP_SERVICE.disable_bootstrap(self)

    @property
    def dss_export_mode(self) -> int:
        return getattr(self, '_dss_export_mode', self.config_get_int('wepp', 'dss_export_mode', 1))
    
    @dss_export_mode.setter
    @nodb_setter
    def dss_export_mode(self, value: isint):
        self._dss_export_mode = value

    @property
    def dss_excluded_channel_orders(self) -> list:
        orders = getattr(self, '_dss_excluded_channel_orders', None)
        if orders is None:
            return self.config_get_list('wepp', 'dss_excluded_channel_orders', [1, 2])
        return orders

    @dss_excluded_channel_orders.setter
    @nodb_setter
    def dss_excluded_channel_orders(self, value: List[int]) -> None:
        self._dss_excluded_channel_orders = value

    @property
    def dss_export_channel_ids(self) -> List[int]:
        return getattr(self, '_dss_export_channel_ids', [])

    @dss_export_channel_ids.setter
    @nodb_setter
    def dss_export_channel_ids(self, value: List[int]) -> None:
        self._dss_export_channel_ids = value

    @property
    def dss_start_date(self) -> Optional[str]:
        stored = self._resolve_serialized_dss_date_attr("_dss_start_date")
        if stored:
            return stored
        return self._default_dss_date("start")

    @dss_start_date.setter
    @nodb_setter
    def dss_start_date(self, value: Optional[str]) -> None:
        parsed = parse_dss_date(value)
        self._dss_start_date = format_dss_date(parsed)

    @property
    def dss_end_date(self) -> Optional[str]:
        stored = self._resolve_serialized_dss_date_attr("_dss_end_date")
        if stored:
            return stored
        return self._default_dss_date("end")

    @dss_end_date.setter
    @nodb_setter
    def dss_end_date(self, value: Optional[str]) -> None:
        parsed = parse_dss_date(value)
        self._dss_end_date = format_dss_date(parsed)

    def _resolve_serialized_dss_date_attr(self, attr_name: str) -> Optional[str]:
        raw_value = getattr(self, attr_name, None)
        if not raw_value:
            return None
        try:
            parsed = parse_dss_date(raw_value)
        except ValueError:
            return None
        return format_dss_date(parsed)

    def _default_dss_date(self, which: str) -> Optional[str]:
        start, end = self._resolve_simulation_date_range()
        target = start if which == "start" else end
        return format_dss_date(target)

    def _resolve_simulation_date_range(self) -> Tuple[Optional[date], Optional[date]]:
        cached = getattr(self, "_dss_simulation_date_range", None)
        if cached is not None:
            return cached

        events_path = Path(self.wepp_interchange_dir) / "pass_pw0.events.parquet"
        default_range: Tuple[Optional[date], Optional[date]] = (None, None)

        if events_path.exists():
            try:
                import pyarrow.parquet as pq
            except ModuleNotFoundError:
                pq = None

            if pq is not None:
                try:
                    parquet_file = pq.ParquetFile(str(events_path))
                except (OSError, ValueError, TypeError):
                    self.logger.debug(
                        "WEPP DSS date range: unable to open events parquet at %s",
                        events_path,
                        exc_info=True,
                    )
                    parquet_file = None

                if (
                    parquet_file is not None
                    and parquet_file.num_row_groups > 0
                    and parquet_file.metadata is not None
                    and parquet_file.metadata.num_rows > 0
                ):
                    columns = ["year", "month", "day_of_month"]
                    start_date = self._read_parquet_date_row(
                        parquet_file.read_row_group(0, columns=columns), 0
                    )
                    end_date: Optional[date] = None
                    for group_idx in range(parquet_file.num_row_groups - 1, -1, -1):
                        table = parquet_file.read_row_group(group_idx, columns=columns)
                        if table.num_rows == 0:
                            continue
                        end_date = self._read_parquet_date_row(table, table.num_rows - 1)
                        if end_date is not None:
                            break
                    default_range = (start_date, end_date)

        self._dss_simulation_date_range = default_range
        return default_range

    @staticmethod
    def _read_parquet_date_row(table, index: int) -> Optional[date]:
        try:
            data = table.to_pydict()
            year = int(data["year"][index])
            month = int(data["month"][index])
            day = int(data["day_of_month"][index])
            return date(year, month, day)
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    @property
    def has_dss_zip(self) -> bool:
        return _exists(_join(self.export_dir, 'dss.zip'))

    @property
    def storm_event_analyzer_ready(self) -> bool:
        return self._interchange_version_at_least(
            STORM_EVENT_ANALYZER_MIN_INTERCHANGE_VERSION
        )

    def _interchange_version_at_least(self, minimum: Version) -> bool:
        interchange_dir = Path(self.wepp_interchange_dir)
        if not interchange_dir.exists():
            return False
        try:
            stored = read_version_manifest(interchange_dir)
        except ValueError:
            return False
        if stored is None:
            return False
        return (stored.major, stored.minor) >= (minimum.major, minimum.minor)

    @property
    def delete_after_interchange(self) -> bool:
        return bool(
            getattr(
                self,
                "_delete_after_interchange",
                self.config_get_bool("interchange", "delete_after_interchange", False),
            )
        )

    @delete_after_interchange.setter
    @nodb_setter
    def delete_after_interchange(self, value: bool) -> None:
        self._delete_after_interchange = bool(value)

    @property
    def multi_ofe(self) -> bool:
        return getattr(self, "_multi_ofe", False)

    @multi_ofe.setter
    @nodb_setter
    def multi_ofe(self, value: bool) -> None:
        self._multi_ofe = value

    @property
    def wepp_bin(self) -> Optional[str]:
        if not hasattr(self, "_wepp_bin"):
            return None

        return self._wepp_bin

    @wepp_bin.setter
    @nodb_setter
    def wepp_bin(self, value: str) -> None:
        self._wepp_bin = value


    @property
    def prep_details_on_run_completion(self) -> bool:
        return getattr(self, '_prep_details_on_run_completion',
                       self.config_get_bool('wepp', 'prep_details_on_run_completion', False))

    @property
    def arc_export_on_run_completion(self) -> bool:
        return getattr(self, '_arc_export_on_run_completion',
                       self.config_get_bool('wepp', 'arc_export_on_run_completion', False))

    @property
    def legacy_arc_export_on_run_completion(self) -> bool:
        return getattr(self, '_legacy_arc_export_on_run_completion',
                       self.config_get_bool('wepp', 'legacy_arc_export_on_run_completion', False))

    @property
    def dss_export_on_run_completion(self) -> bool:
        return getattr(self, '_dss_export_on_run_completion',
                       self.config_get_bool('wepp', 'dss_export_on_run_completion', False))

    @property
    def run_tcr(self) -> bool:
        return getattr(self, '_run_tcr', self.config_get_bool('wepp', 'tcr'))

    @property
    def run_wepp_ui(self) -> bool:
        return getattr(self, '_run_wepp_ui', self.config_get_bool('wepp', 'wepp_ui'))

    @property
    def run_wepp_watershed(self) -> bool:
        return getattr(self, '_run_wepp_watershed', self.config_get_bool('wepp', 'run_wepp_watershed', True))

    @property
    def run_pmet(self) -> bool:
        return getattr(self, '_run_pmet', self.config_get_bool('wepp', 'pmet'))

    @property
    def run_frost(self) -> bool:
        return getattr(self, '_run_frost', self.config_get_bool('wepp', 'frost'))

    @property
    def run_baseflow(self) -> bool:
        return getattr(self, '_run_baseflow', self.config_get_bool('wepp', 'baseflow'))

    @property
    def run_snow(self) -> bool:
        return getattr(self, '_run_snow', self.config_get_bool('wepp', 'snow'))

    @property
    def channel_erodibility(self) -> Optional[float]:
        return getattr(self, '_channel_erodibility', self.config_get_float('wepp', 'channel_erodibility'))

    @property
    def channel_critical_shear(self) -> Optional[float]:
        return getattr(self, '_channel_critical_shear', self.config_get_float('wepp', 'channel_critical_shear'))

    @property
    def channel_manning_roughness_coefficient_bare(self) -> Optional[float]:
        return getattr(self, '_channel_manning_roughness_coefficient_bare', self.config_get_float('wepp', 'channel_manning_roughness_coefficient_bare'))

    @property
    def channel_manning_roughness_coefficient_veg(self) -> Optional[float]:
        return getattr(self, '_channel_manning_roughness_coefficient_veg', self.config_get_float('wepp', 'channel_manning_roughness_coefficient_veg'))

    @property
    def channel_2006_avke(self) -> Optional[float]:
        return getattr(self, '_channel_2006_avke', self.config_get_float('wepp', 'channel_2006_avke'))

    @property
    def is_omni_contrasts_run(self) -> bool:
        run_dir = os.path.abspath(self.runs_dir)
        return 'omni/contrasts' in run_dir

    def set_baseflow_opts(self, gwstorage: Optional[float] = None, bfcoeff: Optional[float] = None, 
                          dscoeff: Optional[float] = None, bfthreshold: Optional[float] = None) -> None:
        with self.locked():
            self.baseflow_opts = BaseflowOpts(
                gwstorage=gwstorage,
                bfcoeff=bfcoeff,
                dscoeff=dscoeff,
                bfthreshold=bfthreshold)
            self._guard_baseflow_bounds()

    def set_phosphorus_opts(self, surf_runoff: Optional[float] = None, lateral_flow: Optional[float] = None, 
                            baseflow: Optional[float] = None, sediment: Optional[float] = None) -> None:
        with self.locked():
            self.phosphorus_opts = PhosphorusOpts(
                surf_runoff=surf_runoff,
                lateral_flow=lateral_flow,
                baseflow=baseflow,
                sediment=sediment)

    def _resolve_unitized_default(self, section: str, option: str, fallback: float,
                                  min_value: float, max_value: float) -> float:
        value = self.config_get_float(section, option, fallback)
        if not isfloat(value):
            return fallback
        value_float = float(value)
        if isnan(value_float) or isinf(value_float) or value_float < min_value or value_float > max_value:
            return fallback
        return value_float

    def _guard_unitized_value(self, section: str, option: str, value: Optional[float],
                              min_value: float, max_value: float, fallback: float) -> float:
        default_value = self._resolve_unitized_default(section, option, fallback, min_value, max_value)
        if not isfloat(value):
            self.logger.warning(
                'Resetting %s.%s from %s to %s (bounds %s..%s)',
                section,
                option,
                value,
                default_value,
                min_value,
                max_value,
            )
            return default_value
        value_float = float(value)
        if isnan(value_float) or isinf(value_float) or value_float < min_value or value_float > max_value:
            self.logger.warning(
                'Resetting %s.%s from %s to %s (bounds %s..%s)',
                section,
                option,
                value,
                default_value,
                min_value,
                max_value,
            )
            return default_value
        return value_float

    def _resolve_positive_default(self, section: str, option: str, fallback: float, max_value: float) -> float:
        value = self.config_get_float(section, option, fallback)
        if not isfloat(value):
            return fallback
        value_float = float(value)
        if isnan(value_float) or isinf(value_float) or value_float <= 0.0 or value_float > max_value:
            return fallback
        return value_float

    def _guard_positive_value(self, section: str, option: str, value: Optional[float], max_value: float, fallback: float) -> float:
        default_value = self._resolve_positive_default(section, option, fallback, max_value)
        if not isfloat(value):
            self.logger.warning(
                'Resetting %s.%s from %s to %s (bounds >0..%s)',
                section,
                option,
                value,
                default_value,
                max_value,
            )
            return default_value
        value_float = float(value)
        if isnan(value_float) or isinf(value_float) or value_float <= 0.0 or value_float > max_value:
            self.logger.warning(
                'Resetting %s.%s from %s to %s (bounds >0..%s)',
                section,
                option,
                value,
                default_value,
                max_value,
            )
            return default_value
        return value_float

    def _resolve_integer_default(self, section: str, option: str, fallback: int,
                                 min_value: int, max_value: int) -> int:
        value = self.config_get_int(section, option, fallback)
        if not isint(value):
            return fallback
        value_int = int(value)
        if value_int < min_value or value_int > max_value:
            return fallback
        return value_int

    def _guard_integer_value(self, section: str, option: str, value: Any,
                             min_value: int, max_value: int, fallback: int) -> int:
        default_value = self._resolve_integer_default(section, option, fallback, min_value, max_value)
        if not isint(value):
            if isfloat(value):
                value_float = float(value)
                if not isnan(value_float) and not isinf(value_float) and value_float.is_integer():
                    value = int(value_float)
                else:
                    self.logger.warning(
                        'Resetting %s.%s from %s to %s (bounds %s..%s)',
                        section,
                        option,
                        value,
                        default_value,
                        min_value,
                        max_value,
                    )
                    return default_value
            else:
                self.logger.warning(
                    'Resetting %s.%s from %s to %s (bounds %s..%s)',
                    section,
                    option,
                    value,
                    default_value,
                    min_value,
                    max_value,
                )
                return default_value
        value_int = int(value)
        if value_int < min_value or value_int > max_value:
            self.logger.warning(
                'Resetting %s.%s from %s to %s (bounds %s..%s)',
                section,
                option,
                value,
                default_value,
                min_value,
                max_value,
            )
            return default_value
        return value_int

    def _guard_frost_bounds(self) -> None:
        if not hasattr(self, 'frost_opts') or self.frost_opts is None:
            self.frost_opts = FrostOpts()

        self.frost_opts.wintRed = self._guard_integer_value(
            'frost_opts',
            'wintRed',
            self.frost_opts.wintRed,
            self._FROST_WINTRED_BOUNDS[0],
            self._FROST_WINTRED_BOUNDS[1],
            self._FROST_WINTRED_DEFAULT,
        )
        self.frost_opts.fineTop = self._guard_integer_value(
            'frost_opts',
            'fineTop',
            self.frost_opts.fineTop,
            self._FROST_FINETOP_BOUNDS[0],
            self._FROST_FINETOP_BOUNDS[1],
            self._FROST_FINETOP_DEFAULT,
        )
        self.frost_opts.fineBot = self._guard_integer_value(
            'frost_opts',
            'fineBot',
            self.frost_opts.fineBot,
            self._FROST_FINEBOT_BOUNDS[0],
            self._FROST_FINEBOT_BOUNDS[1],
            self._FROST_FINEBOT_DEFAULT,
        )

        self.frost_opts.ksnowf = self._guard_unitized_value(
            'frost_opts',
            'ksnowf',
            self.frost_opts.ksnowf,
            self._FROST_K_ADJUST_BOUNDS[0],
            self._FROST_K_ADJUST_BOUNDS[1],
            self._FROST_KSNOWF_DEFAULT,
        )
        self.frost_opts.kresf = self._guard_unitized_value(
            'frost_opts',
            'kresf',
            self.frost_opts.kresf,
            self._FROST_K_ADJUST_BOUNDS[0],
            self._FROST_K_ADJUST_BOUNDS[1],
            self._FROST_KRESF_DEFAULT,
        )
        self.frost_opts.ksoilf = self._guard_unitized_value(
            'frost_opts',
            'ksoilf',
            self.frost_opts.ksoilf,
            self._FROST_K_ADJUST_BOUNDS[0],
            self._FROST_K_ADJUST_BOUNDS[1],
            self._FROST_KSOILF_DEFAULT,
        )
        self.frost_opts.kfactor1 = self._guard_positive_value(
            'frost_opts',
            'kfactor1',
            self.frost_opts.kfactor1,
            self._FROST_KFACTOR_BOUNDS[1],
            self._FROST_KFACTOR1_DEFAULT,
        )
        self.frost_opts.kfactor2 = self._guard_positive_value(
            'frost_opts',
            'kfactor2',
            self.frost_opts.kfactor2,
            self._FROST_KFACTOR_BOUNDS[1],
            self._FROST_KFACTOR2_DEFAULT,
        )
        self.frost_opts.kfactor3 = self._guard_positive_value(
            'frost_opts',
            'kfactor3',
            self.frost_opts.kfactor3,
            self._FROST_KFACTOR_BOUNDS[1],
            self._FROST_KFACTOR3_DEFAULT,
        )

    def _guard_baseflow_bounds(self) -> None:
        if not hasattr(self, 'baseflow_opts') or self.baseflow_opts is None:
            self.baseflow_opts = BaseflowOpts()

        self.baseflow_opts.bfcoeff = self._guard_unitized_value(
            'baseflow_opts',
            'bfcoeff',
            self.baseflow_opts.bfcoeff,
            self._BASEFLOW_BFCOEFF_BOUNDS[0],
            self._BASEFLOW_BFCOEFF_BOUNDS[1],
            self._BASEFLOW_BFCOEFF_DEFAULT,
        )

    def _guard_unitized_bounds(self) -> None:
        if hasattr(self, 'snow_opts'):
            self.snow_opts.newsnw = self._guard_unitized_value(
                'snow_opts',
                'newsnw',
                self.snow_opts.newsnw,
                self._SNOW_NEWSNW_BOUNDS[0],
                self._SNOW_NEWSNW_BOUNDS[1],
                self._SNOW_NEWSNW_DEFAULT,
            )
            self.snow_opts.ssd = self._guard_unitized_value(
                'snow_opts',
                'ssd',
                self.snow_opts.ssd,
                self._SNOW_SSD_BOUNDS[0],
                self._SNOW_SSD_BOUNDS[1],
                self._SNOW_SSD_DEFAULT,
            )
        if hasattr(self, 'tcr_opts'):
            self.tcr_opts.taumin = self._guard_unitized_value(
                'tcr_opts',
                'taumin',
                self.tcr_opts.taumin,
                self._TCR_TAUMIN_BOUNDS[0],
                self._TCR_TAUMIN_BOUNDS[1],
                self._TCR_TAUMIN_DEFAULT,
            )
            self.tcr_opts.taumax = self._guard_unitized_value(
                'tcr_opts',
                'taumax',
                self.tcr_opts.taumax,
                self._TCR_TAUMAX_BOUNDS[0],
                self._TCR_TAUMAX_BOUNDS[1],
                self._TCR_TAUMAX_DEFAULT,
            )
        self._guard_frost_bounds()
        self._guard_baseflow_bounds()

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        with self.locked():
            _WEPP_INPUT_PARSER.parse(self, kwds)


    @property
    def has_run(self) -> bool:
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        if _exists(loss_pw0) and not self.islocked():
            return True

        # When interchange conversion is configured to delete raw WEPP text outputs
        # (see `[interchange] delete_after_interchange=true`), `loss_pw0.txt` will be
        # removed after successful Parquet conversion. Treat the interchange loss
        # products as equivalent evidence that a watershed run has completed.
        interchange_loss_out = _join(output_dir, 'interchange', 'loss_pw0.out.parquet')
        if _exists(interchange_loss_out) and not self.islocked():
            return True

        climate = self.climate_instance
        if climate.ss_batch_storms:
            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                if _exists(_join(output_dir, f'{ss_batch_key}/loss_pw0.txt')):
                    return True
                if _exists(_join(output_dir, ss_batch_key, 'interchange', 'loss_pw0.out.parquet')):
                    return True

        return False

    @property
    def has_phosphorus(self) -> bool:
        return self.has_run and \
               self.phosphorus_opts.isvalid and \
               _exists(_join(self.runs_dir, 'phosphorus.txt'))

    #
    # hillslopes
    #
    def prep_hillslopes(self, frost: Optional[bool] = None, baseflow: Optional[bool] = None, 
                        wepp_ui: Optional[bool] = None, pmet: Optional[bool] = None, snow: Optional[bool] = None,
                        man_relpath: str = '', cli_relpath: str = '', slp_relpath: str = '', sol_relpath: str = '',
                        max_workers: Optional[int] = None) -> None:
        _WEPP_PREP_SERVICE.prep_hillslopes(
            self,
            frost=frost,
            baseflow=baseflow,
            wepp_ui=wepp_ui,
            pmet=pmet,
            snow=snow,
            man_relpath=man_relpath,
            cli_relpath=cli_relpath,
            slp_relpath=slp_relpath,
            sol_relpath=sol_relpath,
            max_workers=max_workers,
        )


    def _prep_revegetation(self) -> None:
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

    def _prep_firedate(self) -> None:

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
    def sol_versions(self) -> Set[str]:
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

    def _prep_wepp_ui(self) -> None:
        for sol_version in self.sol_versions:
            if '2006' in sol_version:
                return

        fn = _join(self.runs_dir, 'wepp_ui.txt')
        with open(fn, 'w') as fp:
            fp.write('')

    def _remove_wepp_ui(self) -> None:
        fn = _join(self.runs_dir, 'wepp_ui.txt')
        if _exists(fn):
            os.remove(fn)

    def _prep_frost(self) -> None:
        if not hasattr(self, 'frost_opts') or self.frost_opts is None:
            self.frost_opts = FrostOpts()
        self._guard_frost_bounds()
        fn = _join(self.runs_dir, 'frost.txt')
        with open(fn, 'w') as fp:
            fp.write(self.frost_opts.contents)

    def _mint_default_frost_file(self) -> None:
        fn = _join(self.runs_dir, 'frost.txt')
        if _exists(fn):
            return

        if not _exists(self.runs_dir):
            os.makedirs(self.runs_dir, exist_ok=True)

        if not hasattr(self, 'frost_opts') or self.frost_opts is None:
            self.frost_opts = FrostOpts()
        self._guard_frost_bounds()

        with open(fn, 'w') as fp:
            fp.write(self.frost_opts.contents)

    def _remove_frost(self) -> None:
        fn = _join(self.runs_dir, 'frost.txt')
        if _exists(fn):
            os.remove(fn)

    def _prep_tc(self) -> None:
        fn = _join(self.runs_dir, 'tc.txt')
        with open(fn, 'w') as fp:
            fp.write('')

    def _prep_tcr(self) -> None:
        fn = _join(self.runs_dir, 'tcr.txt')
        with open(fn, 'w') as fp:
            if hasattr(self, 'tcr_opts'):
                fp.write(self.tcr_opts.contents)
            else:
                fp.write('\n')

    def _remove_tcr(self) -> None:
        fn = _join(self.runs_dir, 'tcr.txt')
        if _exists(fn):
            os.remove(fn)

    @property
    def pmet_kcb(self) -> Optional[float]:
        return getattr(self, '_pmet_kcb', self.config_get_float('wepp', 'pmet_kcb'))

    @property
    def pmet_kcb_map(self) -> Optional[str]:
        return getattr(self, '_pmet_kcb_map', None)

    @pmet_kcb.setter
    @nodb_setter
    def pmet_kcb(self, value: float) -> None:  # type: ignore[no-redef]
        self._pmet_kcb = value

    @property
    def pmet_rawp(self) -> Optional[float]:
        return getattr(self, '_pmet_rawp', self.config_get_float('wepp', 'pmet_rawp'))

    @pmet_rawp.setter
    @nodb_setter
    def pmet_rawp(self, value: float) -> None:  # type: ignore[no-redef]
        self._pmet_rawp = value

    def _prep_pmet(self, kcb: Optional[float] = None, rawp: Optional[float] = None) -> None:

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


    def _remove_pmet(self) -> None:
        fn = _join(self.runs_dir, 'pmetpara.txt')
        if _exists(fn):
            os.remove(fn)

    def _check_and_set_phosphorus_map(self) -> None:

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

    def _prep_phosphorus(self) -> None:
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

    def _remove_phosphorus(self) -> None:
        fn = _join(self.runs_dir, 'phosphorus.txt')
        if _exists(fn):
            os.remove(fn)

    def _prep_snow(self) -> None:
        fn = _join(self.runs_dir, 'snow.txt')
        with open(fn, 'w') as fp:
            fp.write(self.snow_opts.contents)

    def _remove_snow(self) -> None:
        fn = _join(self.runs_dir, 'snow.txt')
        if _exists(fn):
            os.remove(fn)

    def _check_and_set_baseflow_map(self) -> None:
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

    def _prep_baseflow(self) -> None:
        climate = self.climate_instance
        if climate.is_single_storm:
            baseflow_opts = BaseflowOpts(gwstorage=0.0, bfcoeff=0.0)
        else:
            baseflow_opts = self.baseflow_opts

        fn = _join(self.runs_dir, 'gwcoeff.txt')
        with open(fn, 'w') as fp:
            fp.write(baseflow_opts.contents)

    def _remove_baseflow(self) -> None:
        fn = _join(self.runs_dir, 'gwcoeff.txt')
        if _exists(fn):
            os.remove(fn)

    def clean(self) -> None:
        for _dir in (self.runs_dir, self.output_dir, self.plot_dir,
                     self.stats_dir, self.fp_runs_dir, self.fp_output_dir):
            if _exists(_dir):
                try:
                    shutil.rmtree(_dir)
                except OSError as exc:
                    self.logger.warning(f'Cleanup unable to remove {_dir} on first attempt: {exc}', exc_info=True)
                    sleep(1.0)
                    try:
                        shutil.rmtree(_dir)
                    except OSError as retry_exc:
                        self.logger.error(f'Cleanup failed to remove {_dir} after retry: {retry_exc}', exc_info=True)
                        raise RuntimeError(f"Failed to clean directory '{_dir}'") from retry_exc

            try:
                os.makedirs(_dir, exist_ok=True)
            except OSError as exc:
                self.logger.error(f'Cleanup failed to recreate {_dir}: {exc}', exc_info=True)
                raise

        climate = self.climate_instance
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                ss_batch_dir = _join(self.output_dir, ss_batch_key)
                if not _exists(ss_batch_dir):
                    os.makedirs(ss_batch_dir)

    def prep_and_run_flowpaths(self, clean_after_run: bool = True) -> None:
        _WEPP_RUN_SERVICE.prep_and_run_flowpaths(self, clean_after_run=clean_after_run)

    def _prep_slopes_peridot(self, watershed, translator, clip_hillslopes, clip_hillslope_length):
        self.logger.info('    Prepping _prep_slopes_peridot... ')
        runs_dir = self.runs_dir

        for topaz_id in watershed._subs_summary:
            wepp_id = translator.wepp(top=int(topaz_id))

            src_candidates = (
                f"watershed/slope_files/hillslopes/hill_{topaz_id}.slp",
                f"watershed/hill_{topaz_id}.slp",
            )
            src_rel = src_candidates[0]
            for rel in src_candidates:
                if _exists(_join(self.wd, rel)):
                    src_rel = rel
                    break
                if input_exists(self.wd, rel, tolerate_mixed=True, mixed_prefer='archive'):
                    src_rel = rel
                    break

            dst_fn = _join(runs_dir, "p%i.slp" % wepp_id)
            src_fn = str(Path(self.wd) / src_rel)
            if _exists(src_fn):
                if clip_hillslopes:
                    clip_slope_file_length(src_fn, dst_fn, clip_hillslope_length)
                else:
                    shutil.copyfile(src_fn, dst_fn)
                continue

            with with_input_file_path(
                self.wd,
                src_rel,
                purpose='wepp-prep-slopes',
                tolerate_mixed=True,
                mixed_prefer='archive',
                allow_materialize_fallback=True,
            ) as projected_src_fn:
                if clip_hillslopes:
                    clip_slope_file_length(projected_src_fn, dst_fn, clip_hillslope_length)
                else:
                    shutil.copyfile(projected_src_fn, dst_fn)

    def _prep_slopes(self, translator, clip_hillslopes, clip_hillslope_length):
        self.logger.info('    Prepping _prep_slopes... ')

        watershed = self.watershed_instance
        if watershed.abstraction_backend == 'peridot':
            return self._prep_slopes_peridot(watershed, translator, clip_hillslopes, clip_hillslope_length)

        runs_dir = self.runs_dir

        for topaz_id in watershed._subs_summary:
            wepp_id = translator.wepp(top=int(topaz_id))

            src_rel = f'watershed/hill_{topaz_id}.slp'
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            src_fn = str(Path(self.wd) / src_rel)
            if _exists(src_fn):
                if clip_hillslopes:
                    clip_slope_file_length(src_fn, dst_fn, clip_hillslope_length)
                else:
                    shutil.copyfile(src_fn, dst_fn)
                continue

            with with_input_file_path(
                self.wd,
                src_rel,
                purpose='wepp-prep-slopes',
                tolerate_mixed=True,
                mixed_prefer='archive',
                allow_materialize_fallback=True,
            ) as projected_src_fn:
                if clip_hillslopes:
                    clip_slope_file_length(projected_src_fn, dst_fn, clip_hillslope_length)
                else:
                    shutil.copyfile(projected_src_fn, dst_fn)

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

        disturbed = Disturbed.tryGetInstance(wd)

        years = climate.input_years

        runs_dir = self.runs_dir

        kslast = self.kslast

        kslast_map_fn = self.kslast_map
        kslast_map = None
        if kslast_map_fn is not None:
            kslast_map = RasterDatasetInterpolator(kslast_map_fn)

        for topaz_id, ss in watershed.subs_summary.items():
            wepp_id = translator.wepp(top=int(topaz_id))
            lng, lat = watershed.hillslope_centroid_lnglat(topaz_id)

            # slope files
            src_rel = f'watershed/slope_files/hillslopes/hill_{topaz_id}.mofe.slp'
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            copy_input_file(self.wd, src_rel, dst_fn)

            # soils
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

            with with_input_file_path(
                self.wd,
                f'soils/hill_{topaz_id}.mofe.sol',
                purpose='wepp-prep-multi-ofe-soils',
                tolerate_mixed=True,
                mixed_prefer='archive',
                allow_materialize_fallback=True,
            ) as src_fn:
                soilu = WeppSoilUtil(src_fn)
                soilu.modify_initial_sat(initial_sat)

                if _kslast is not None:
                    soilu.modify_kslast(_kslast)

                if clip_soils:
                    soilu.clip_soil_depth(clip_soils_depth)

                soilu.write(dst_fn)

            # managements
            man_fn = f'hill_{topaz_id}.mofe.man'
            with with_input_file_path(
                self.wd,
                f'landuse/{man_fn}',
                purpose='wepp-prep-multi-ofe-management',
                tolerate_mixed=True,
                mixed_prefer='archive',
                allow_materialize_fallback=True,
            ) as man_src:
                man = Management(Key=f'hill_{topaz_id}',
                                 ManagementFile=Path(man_src).name,
                                 ManagementDir=str(Path(man_src).parent),
                                 Description=f"hill_{topaz_id} Multiple OFE",
                                 Color=(0, 0, 0, 255))

                man = man.build_multiple_year_man(years)
                dst_fn = _join(runs_dir, 'p%i.man' % wepp_id)
                with open(dst_fn, 'w') as pf:
                    pf.write(str(man))


    def _prep_managements(self, translator):
        _WEPP_PREP_SERVICE.prep_managements(self, translator)

    def _prep_soils(self, translator, max_workers=None):
        _WEPP_PREP_SERVICE.prep_soils(self, translator, max_workers=max_workers)


    @nodb_timed
    def _prep_climates(self, translator):
        _WEPP_PREP_SERVICE.prep_climates(self, translator)

    def _prep_climates_ss_batch(self, translator):
        _WEPP_PREP_SERVICE.prep_climates_ss_batch(self, translator)

    def _make_hillslope_runs(self, translator, reveg=False,
                  man_relpath='', cli_relpath='', slp_relpath='', sol_relpath=''):
        _WEPP_PREP_SERVICE.make_hillslope_runs(
            self,
            translator,
            reveg=reveg,
            man_relpath=man_relpath,
            cli_relpath=cli_relpath,
            slp_relpath=slp_relpath,
            sol_relpath=sol_relpath,
        )

    def run_hillslopes(self,
                  man_relpath: str = '', cli_relpath: str = '', slp_relpath: str = '', sol_relpath: str = '',
                  max_workers: Optional[int] = None) -> None:
        _WEPP_RUN_SERVICE.run_hillslopes(
            self,
            man_relpath=man_relpath,
            cli_relpath=cli_relpath,
            slp_relpath=slp_relpath,
            sol_relpath=sol_relpath,
            max_workers=max_workers,
        )

    #
    # watershed
    #
    def prep_watershed(self, erodibility: Optional[float] = None, critical_shear: Optional[float] = None,
                       tcr: Optional[bool] = None, avke: Optional[float] = None,
                       channel_manning_roughness_coefficient_bare: Optional[float] = None,
                       channel_manning_roughness_coefficient_veg: Optional[float] = None) -> None:
        _WEPP_PREP_SERVICE.prep_watershed(
            self,
            erodibility=erodibility,
            critical_shear=critical_shear,
            tcr=tcr,
            avke=avke,
            channel_manning_roughness_coefficient_bare=channel_manning_roughness_coefficient_bare,
            channel_manning_roughness_coefficient_veg=channel_manning_roughness_coefficient_veg,
        )

    def _prep_structure(self, translator):
        self.logger.info('    Prepping _prep_structure... ')

        watershed = self.watershed_instance
        runs_dir = self.runs_dir

        # Handle minimal watershed case: 1 hillslope, 1 channel, no network.txt
        if watershed.abstraction_backend == 'peridot' and \
           not input_exists(self.wd, 'watershed/network.txt', tolerate_mixed=True, mixed_prefer='archive') and \
           watershed.sub_n == 1 and \
           watershed.chn_n == 1:
            self.logger.info('    Writing minimal structure (1 hillslope, 1 channel)')
            with open(_join(runs_dir, 'pw0.str'), 'w') as fp:
                fp.write('# watershed structure (1 hillslope, 1 channel)\n')
                fp.write('94.301\n')
                fp.write('2 0 0 1 0 0 0 0 0 0\n')
            return

        structure = watershed.structure
        if structure is None:
            raise RuntimeError(
                "Watershed structure is missing. Run the watershed migration to regenerate structure.json."
            )

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


    @property
    def minimum_channel_width_m(self) -> float:
        if hasattr(self, '_minimum_channel_width_m'):
            return self._minimum_channel_width_m
        return 0.305  # 1 foot

    @minimum_channel_width_m.setter
    @nodb_setter
    def minimum_channel_width_m(self, value: float):
        if value <= 0.0:
            raise ValueError(f"Expected minimum_channel_width_m to be positive, got {value}")
        self._minimum_channel_width_m = value

    def _prep_channel_slopes(self):
        minimum_channel_width_m = self.minimum_channel_width_m
        runs_dir = self.runs_dir

        src_rel = 'watershed/slope_files/channels.slp'
        if not input_exists(self.wd, src_rel, tolerate_mixed=True, mixed_prefer='archive'):
            src_rel = 'watershed/channels.slp'

        with open_input_text(self.wd, src_rel, tolerate_mixed=True, mixed_prefer='archive') as fp:
            version_line = fp.readline().strip()
            version = float(version_line)

            if version >= 2023.1:
                with open(_join(runs_dir, 'pw0.slp'), 'w') as out_fp:
                    out_fp.write('99.1\n')
                    n_chns = int(fp.readline().strip())
                    out_fp.write(f'{n_chns}\n')

                    for _ in range(n_chns):
                        aspect, width, elevation, order = fp.readline().strip().split()

                        aspect = float(aspect)
                        if aspect < 0.0:
                            aspect += 360.0

                        width = float(width)
                        if width < minimum_channel_width_m:
                            width = minimum_channel_width_m

                        out_fp.write(f'{aspect} {width}\n')
                        out_fp.write(fp.readline())
                        out_fp.write(fp.readline())
            elif version >= 2023.0:
                # this version produces suspiciously small channel widths
                raise ValueError(
                    f'Unsupported channel slope file version {version} in {src_rel}. '
                    'Please update the PERIDOT to compatible version.'
                )
            else:
                dst_fn = _join(runs_dir, 'pw0.slp')
                with open(dst_fn, 'w') as out_fp:
                    out_fp.write(version_line + "\n")
                    out_fp.write(fp.read())

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
    def ichout_override(self) -> Optional[int]:
        if hasattr(self, '_ichout_override'):
            return self._ichout_override
        return None

    @ichout_override.setter
    @nodb_setter
    def ichout_override(self, value: int | str | None):
        if isinstance(value, str):
            value = value.strip()
            if value == '':
                value = None
            elif value.isdigit():
                value = int(value)
        if value is None:
            self._ichout_override = None
            return
        if value not in (1, 3):
            raise ValueError(f"Expected ichout_override to be 1 or 3, got {value}")
        self._ichout_override = value

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

        if hasattr(self, '_ichout_override'):
            if self._ichout_override in (1, 3):
                ichout = self._ichout_override

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
        src_rel = f'climate/{climate.cli_fn}'
        copy_input_file(self.wd, src_rel, dst_fn)

    def make_watershed_run(self, wepp_id_paths=None, output_options: Optional[Dict[str, Any]] = None):
        translator = self.watershed_instance.translator_factory()
        self._make_watershed_run(translator, wepp_id_paths=wepp_id_paths, output_options=output_options)

    def _make_watershed_run(self, translator, wepp_id_paths=None, output_options: Optional[Dict[str, Any]] = None):
        runs_dir = self.runs_dir
        wepp_ids = list(translator.iter_wepp_sub_ids())
        wepp_ids.sort()

        climate = self.climate_instance
        years = climate.input_years

        if wepp_id_paths is not None:
            if output_options is None:
                output_options = getattr(self, "_contrast_output_options", None)
            make_watershed_omni_contrasts_run(years, wepp_id_paths, runs_dir, output_options=output_options)
        elif climate.climate_mode in [ClimateMode.SingleStorm, ClimateMode.UserDefinedSingleStorm]:
            make_ss_watershed_run(wepp_ids, runs_dir)
        elif climate.climate_mode == ClimateMode.SingleStormBatch:
            for d in climate.ss_batch_storms:
                ss_batch_id = d['ss_batch_id']
                ss_batch_key = d['ss_batch_key']
                make_ss_batch_watershed_run(wepp_ids, runs_dir, ss_batch_id=ss_batch_id, ss_batch_key=ss_batch_key)
        else:
            make_watershed_run(years, wepp_ids, runs_dir)

    def run_watershed(self) -> None:
        _WEPP_RUN_SERVICE.run_watershed(self)

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
        from wepppy.wepp.interchange import (
            totalwatsed_partitioned_dss_export,
            chanout_dss_export,
            archive_dss_export_zip,
        )

        start_date = parse_dss_date(self.dss_start_date)
        end_date = parse_dss_date(self.dss_end_date)
        totalwatsed_partitioned_dss_export(
            self.wd,
            start_date=start_date,
            end_date=end_date,
        )
        chanout_dss_export(
            self.wd,
            start_date=start_date,
            end_date=end_date,
        )
        archive_dss_export_zip(self.wd)

    def report_loss(self) -> Any:
        from wepppy.wepp.interchange.watershed_loss import Loss
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        return Loss(loss_pw0, self.has_phosphorus, self.wd)

    def report_return_periods(self, rec_intervals: Tuple[int, ...] = (50, 25, 20, 10, 5, 2), 
                              exclude_yr_indxs: Optional[List[int]] = None, 
                              method: str = 'cta', gringorten_correction: bool = True, 
                              meoization: bool = True,
                              exclude_months: Optional[List[int]] = None,
                              chn_topaz_id_of_interest: Optional[int] = None,
                              wait_for_inputs: bool = True) -> ReturnPeriods:
        return _WEPP_POSTPROCESS_SERVICE.report_return_periods(
            self,
            rec_intervals=rec_intervals,
            exclude_yr_indxs=exclude_yr_indxs,
            method=method,
            gringorten_correction=gringorten_correction,
            meoization=meoization,
            exclude_months=exclude_months,
            chn_topaz_id_of_interest=chn_topaz_id_of_interest,
            wait_for_inputs=wait_for_inputs,
        )

    def export_return_periods_tsv_summary(self, rec_intervals: Tuple[int, ...] = (50, 25, 20, 10, 5, 2), 
                           exclude_yr_indxs: Optional[List[int]] = None, 
                           method: str = 'cta', 
                           gringorten_correction: bool = True, 
                           meoization: bool = True,
                           extraneous: bool = False) -> None:

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

    def report_frq_flood(self) -> FrqFloodReport:
        return FrqFloodReport(self.wd)

    def report_sediment_delivery(self) -> SedimentCharacteristics:
        return SedimentCharacteristics(self.wd)

    def report_hill_watbal(self) -> HillslopeWatbalReport:
        return HillslopeWatbalReport(self.wd)

    def report_chn_watbal(self) -> ChannelWatbalReport:
        return ChannelWatbalReport(self.wd)

    def set_run_flowpaths(self, state: bool) -> None:
        assert state in [True, False]
        with self.locked():
            self.run_flowpaths = state

    def set_run_wepp_watershed(self, state: bool) -> None:
        assert state in [True, False]
        with self.locked():
            self._run_wepp_watershed = state

    def set_run_wepp_ui(self, state: bool) -> None:
        assert state in [True, False]
        with self.locked():
            self._run_wepp_ui = state

    def set_run_pmet(self, state: bool) -> None:
        assert state in [True, False]
        with self.locked():
            self._run_pmet = state

    def set_run_frost(self, state: bool) -> None:
        assert state in [True, False]
        with self.locked():
            self._run_frost = state

    def set_run_snow(self, state: bool) -> None:
        assert state in [True, False]
        with self.locked():
            self._run_snow = state

    def set_run_tcr(self, state: bool) -> None:
        assert state in [True, False]
        with self.locked():
            self._run_tcr = state

    def set_run_baseflow(self, state: bool) -> None:
        assert state in [True, False]
        with self.locked():
            self._run_baseflow = state

    @property
    def loss_report(self) -> Optional[Any]:
        from wepppy.wepp.interchange.watershed_loss import Loss
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')

        if not _exists(loss_pw0):
            return None

        if not hasattr(self, '_loss_report'):
            self._loss_report = Loss(loss_pw0, self.has_phosphorus, self.wd)

        return self._loss_report

    def query_sub_val(self, measure: str) -> Optional[Dict[str, Dict[str, Any]]]:
        return _WEPP_POSTPROCESS_SERVICE.query_sub_val(self, measure)

    def query_chn_val(self, measure: str) -> Optional[Dict[str, Dict[str, Any]]]:
        return _WEPP_POSTPROCESS_SERVICE.query_chn_val(self, measure)

    def make_loss_grid(self) -> None:
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
    def kslast(self) -> Optional[float]:
        if not hasattr(self, '_kslast'):
            return None

        return self._kslast

    @property
    def kslast_map(self) -> Optional[str]:
        if not hasattr(self, '_kslast_map'):
            return None

        return self._kslast_map

    @kslast.setter
    @nodb_setter
    def kslast(self, value: Optional[float]) -> None:  # type: ignore[no-redef]
        self._kslast = value
