import json
import shutil
from glob import glob

import socket
import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import inspect
import time
import queue
import stat
import threading
from queue import Queue
from functools import wraps
from subprocess import Popen, PIPE, call
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional

import redis
from rq import Queue, get_current_job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.nodb.base import clear_locks, clear_nodb_file_cache
from wepppy.nodb.core import *
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.debris_flow import DebrisFlow
from wepppy.nodb.mods.rhem import Rhem
from wepppy.nodb.mods.rap import RAP_TS

from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from .wepp_rq import run_wepp_rq

_hostname = socket.gethostname()

from dotenv import load_dotenv
_thisdir = os.path.dirname(__file__)

load_dotenv(_join(_thisdir, '.env'))

REDIS_HOST = redis_host()
RQ_DB = int(RedisDB.RQ)

TIMEOUT = 43_200
DEFAULT_ZOOM = 12


def test_run_rq(runid: str):
    """
    assumes a runid has been assigned and an empty wd has been created.
    """
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        class TaskStub:
            @classmethod
            def is_task_enabled(cls, task: TaskEnum) -> bool:
                return True
            
        base_wd = get_wd(runid)

        new_runid = f'{runid}-latest'
        runid_wd = get_wd(new_runid)

        StatusMessenger.publish(status_channel, f'base_wd: {base_wd}')
        init_required = False
        if os.path.exists(runid_wd) and TaskStub.is_task_enabled(TaskEnum.fetch_dem):
            StatusMessenger.publish(status_channel, f'removing existing runid_wd: {runid_wd}')
            shutil.rmtree(runid_wd)
            init_required = True

        if not os.path.exists(runid_wd):
            init_required = True
        
        StatusMessenger.publish(status_channel, f'init_required: {init_required}')
        prep = None
        locks_cleared = None
        if init_required:
            StatusMessenger.publish(status_channel, f'copying base project to runid_wd: {runid_wd}')
            shutil.copytree(base_wd, runid_wd)

            for nodb_fn in glob(_join(runid_wd, '*.nodb')):
                with open(nodb_fn, 'r') as fp:
                    state = json.load(fp)
                state.setdefault('py/state', {})['wd'] = runid_wd
                with open(nodb_fn, 'w') as fp:
                    json.dump(state, fp)
                    fp.flush()
                    os.fsync(fp.fileno())
            clear_nodb_file_cache(runid)
            StatusMessenger.publish(status_channel, 'cleared NoDb file cache')
            try:
                locks_cleared = clear_locks(runid)
                StatusMessenger.publish(status_channel, f'cleared NoDb locks: {locks_cleared}')
            except RuntimeError:
                pass

        StatusMessenger.publish(status_channel, 'getting RedisPrep instance')
        prep = RedisPrep.getInstance(runid_wd)
        StatusMessenger.publish(status_channel, prep.timestamps_report())

        if init_required:
            StatusMessenger.publish(status_channel, f'init_required: {init_required} removing all RedisPrep timestamps')
            prep.remove_all_timestamp()
            StatusMessenger.publish(status_channel, prep.timestamps_report())

        StatusMessenger.publish(status_channel, 'getting NoDb instances')
        ron = Ron.getInstance(runid_wd)
        watershed = Watershed.getInstance(runid_wd)
        landuse = Landuse.getInstance(runid_wd)
        soils = Soils.getInstance(runid_wd)
        climate = Climate.getInstance(runid_wd)
        wepp = Wepp.getInstance(runid_wd)
        
        if TaskStub.is_task_enabled(TaskEnum.fetch_dem) and prep[str(TaskEnum.fetch_dem)] is None:
            StatusMessenger.publish(status_channel, 'fetching DEM')
            ron.fetch_dem()

        if TaskStub.is_task_enabled(TaskEnum.build_channels) and prep[str(TaskEnum.build_channels)] is None:
            StatusMessenger.publish(status_channel, f'building channels')
            watershed.build_channels()

        if TaskStub.is_task_enabled(TaskEnum.find_outlet) and prep[str(TaskEnum.find_outlet)] is None:
            StatusMessenger.publish(status_channel, f'setting outlet')
            watershed.set_outlet(
                lng=watershed.outlet.requested_loc.lng, 
                lat=watershed.outlet.requested_loc.lat
            )

        if TaskStub.is_task_enabled(TaskEnum.build_subcatchments) and prep[str(TaskEnum.build_subcatchments)] is None:
            StatusMessenger.publish(status_channel, f'building subcatchments')
            watershed.build_subcatchments()

        if TaskStub.is_task_enabled(TaskEnum.abstract_watershed) and prep[str(TaskEnum.abstract_watershed)] is None:
            StatusMessenger.publish(status_channel, f'abstracting watershed')
            watershed.abstract_watershed()

        if TaskStub.is_task_enabled(TaskEnum.build_landuse) and prep[str(TaskEnum.build_landuse)] is None:
            StatusMessenger.publish(status_channel, f'building landuse')
            landuse.build()

        if TaskStub.is_task_enabled(TaskEnum.build_soils) and prep[str(TaskEnum.build_soils)] is None:
            StatusMessenger.publish(status_channel, f'building soils')
            soils.build()

        if TaskStub.is_task_enabled(TaskEnum.build_climate) and prep[str(TaskEnum.build_climate)] is None:
            StatusMessenger.publish(status_channel, f'building climate')
            climate.build()

        rap_ts = RAP_TS.tryGetInstance(runid_wd)
        StatusMessenger.publish(status_channel, f'rap_ts: {rap_ts}')
        if rap_ts and TaskStub.is_task_enabled(TaskEnum.fetch_rap_ts) \
            and prep[str(TaskEnum.fetch_rap_ts)] is None:
            StatusMessenger.publish(status_channel, f'fetching RAP TS')
            rap_ts.acquire_rasters(
                start_year=climate.observed_start_year,
                end_year=climate.observed_end_year,
            )
            StatusMessenger.publish(status_channel, f'analyzing RAP TS')
            rap_ts.analyze()

        run_hillslopes = TaskStub.is_task_enabled(TaskEnum.run_wepp_hillslopes) \
            and prep[str(TaskEnum.run_wepp_hillslopes)] is None
        run_watershed = TaskStub.is_task_enabled(TaskEnum.run_wepp_watershed) \
            and prep[str(TaskEnum.run_wepp_watershed)] is None

        StatusMessenger.publish(status_channel, f'run_hillslopes: {run_hillslopes}')
        StatusMessenger.publish(status_channel, f'run_watershed: {run_watershed}')

        if run_hillslopes:
            StatusMessenger.publish(status_channel, 'calling wepp.clean()')
            wepp.clean()

        if run_hillslopes or run_watershed:
            StatusMessenger.publish(status_channel, 'calling wepp._check_and_set_baseflow_map()')
            wepp._check_and_set_baseflow_map()
            StatusMessenger.publish(status_channel, 'calling wepp._check_and_set_phosphorus_map()')
            wepp._check_and_set_phosphorus_map()

        if run_hillslopes:
            StatusMessenger.publish(status_channel, 'calling wepp.prep_hillslopes()')
            wepp.prep_hillslopes()
            StatusMessenger.publish(status_channel, 'calling wepp.run_hillslopes()')
            wepp.run_hillslopes()

        if run_watershed:
            StatusMessenger.publish(status_channel, 'calling wepp.prep_watershed()')
            wepp.prep_watershed()
            StatusMessenger.publish(status_channel, 'calling wepp.run_watershed()')
            wepp.run_watershed()  # also triggers post wepp processing

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')

        return tuple(locks_cleared) if locks_cleared else ()

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def set_run_readonly_rq(runid: str, readonly: bool):
    from wepppy.microservices.browse import create_manifest, remove_manifest, MANIFEST_FILENAME

    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, readonly={readonly})')

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    previous_state = ron.readonly
    prep = RedisPrep.tryGetInstance(wd)

    if prep is not None:
        try:
            prep.set_rq_job_id('set_readonly', job.id)
            prep.remove_timestamp(TaskEnum.set_readonly)
        except Exception:
            pass

    try:
        if readonly:
            if not previous_state:
                ron.readonly = True

            if ron.is_child_run:
                StatusMessenger.publish(
                    status_channel,
                    f'rq:{job.id} COMMAND_BAR_RESULT {MANIFEST_FILENAME} skipped (child run)'
                )
            else:
                StatusMessenger.publish(
                    status_channel,
                    f'rq:{job.id} STATUS {MANIFEST_FILENAME} creation started'
                )
                with ron.timed('Create manifest'):
                    create_manifest(wd)
                    if not _exists(_join(wd, MANIFEST_FILENAME)):
                        raise RuntimeError(f'{MANIFEST_FILENAME} was not created')
                StatusMessenger.publish(
                    status_channel,
                    f'rq:{job.id} COMMAND_BAR_RESULT {MANIFEST_FILENAME} creation finished'
                )
        else:
            if previous_state:
                ron.readonly = False

            remove_manifest(wd)
            if _exists(_join(wd, MANIFEST_FILENAME)):
                raise RuntimeError(f'Unable to remove {MANIFEST_FILENAME}')
            StatusMessenger.publish(
                status_channel,
                f'rq:{job.id} COMMAND_BAR_RESULT {MANIFEST_FILENAME} removed'
            )

        if prep is not None:
            try:
                prep.timestamp(TaskEnum.set_readonly)
            except Exception:
                pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, readonly={readonly})')
    except Exception:
        try:
            if ron.readonly != previous_state:
                ron.readonly = previous_state
        except Exception:
            pass

        failure_suffix = 'creation failed' if readonly else 'removal failed'
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} COMMAND_BAR_RESULT {MANIFEST_FILENAME} {failure_suffix}'
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, readonly={readonly})')
        raise


def init_sbs_map_rq(runid: str, sbs_map: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:watershed'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
            
        ron = Ron.getInstance(wd)
        ron.init_sbs_map(sbs_map, ron.disturbed)
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.init_sbs_map)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def fetch_dem_rq(runid: str, extent, center, zoom):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        
        if center is None:
            center = [(extent[0]+extent[2])/2, (extent[1]+extent[3])/2]
        
        if zoom is None:
            zoom = DEFAULT_ZOOM
            
        ron = Ron.getInstance(wd)
        ron.set_map(extent, center, zoom)

        if ron.map.num_cols > ron.max_map_dimension_px or ron.map.num_rows > ron.max_map_dimension_px:
            raise Exception(f'Map size too large: {ron.map.num_cols}x{ron.map.num_rows}. Maximum is {ron.max_map_dimension_px}x{ron.max_map_dimension_px}.')
        
        ron.fetch_dem()
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def build_channels_rq(runid: str, csa: float, mcl: float, wbt_fill_or_breach: None|str, wbt_blc_dist: None|int):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed = Watershed.getInstance(wd)
        if watershed.delineation_backend_is_wbt:
            if wbt_fill_or_breach is not None:
                StatusMessenger.publish(status_channel, f'Setting wbt_fill_or_breach to {wbt_fill_or_breach}')
                watershed.wbt_fill_or_breach = wbt_fill_or_breach
            if wbt_blc_dist is not None:
                StatusMessenger.publish(status_channel, f'Setting wbt_blc_dist to {wbt_blc_dist}')
                watershed.wbt_blc_dist = wbt_blc_dist
        StatusMessenger.publish(status_channel, f'Building channels with csa={csa}, mcl={mcl}')
        watershed.build_channels(csa, mcl)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   channel_delineation BUILD_CHANNELS_TASK_COMPLETED')
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_channels)
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def fetch_dem_and_build_channels_rq(runid: str, extent, center, zoom, csa, mcl, wbt_fill_or_breach, wbt_blc_dist, set_extent_mode, map_bounds_text):
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        watershed = Watershed.getInstance(get_wd(runid))
        watershed.set_extent_mode = set_extent_mode
        watershed.map_bounds_text = map_bounds_text

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            
            ajob = q.enqueue_call(fetch_dem_rq, (runid, extent, center, zoom))
            job.meta['jobs:0,func:fetch_dem_rq'] = ajob.id
            job.save()

            bjob = q.enqueue_call(build_channels_rq, (runid, csa, mcl, wbt_fill_or_breach, wbt_blc_dist),  depends_on=ajob)
            job.meta['jobs:1,func:build_channels_rq'] = bjob.id
            job.save()
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def set_outlet_rq(runid: str, outlet_lng: float, outlet_lat: float):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:outlet'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed = Watershed.getInstance(wd)
        watershed.set_outlet(outlet_lng, outlet_lat)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   outlet SET_OUTLET_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.set_outlet)

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def build_subcatchments_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:subcatchment_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed = Watershed.getInstance(wd)
        watershed.build_subcatchments()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        time.sleep(1)
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   subcatchment_delineation BUILD_SUBCATCHMENTS_TASK_COMPLETED')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def abstract_watershed_rq(runid: str):
    try:
        time.sleep(0.05)  # race condition where SUBWTA.ARC is not yet written
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:subcatchment_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed = Watershed.getInstance(wd)
        watershed.abstract_watershed()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   subcatchment_delineation WATERSHED_ABSTRACTION_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.abstract_watershed)
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def build_subcatchments_and_abstract_watershed_rq(runid: str):
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:subcatchment_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            
            ajob = q.enqueue_call(build_subcatchments_rq, (runid,), timeout=TIMEOUT)
            job.meta['jobs:0,func:build_subcatchments_rq'] = ajob.id
            job.save()

            bjob = q.enqueue_call(abstract_watershed_rq, (runid,), timeout=TIMEOUT, depends_on=ajob)
            job.meta['jobs:1,func:abstract_watershed_rq'] = bjob.id
            job.save()
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def build_landuse_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:landuse'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        landuse = Landuse.getInstance(wd)
        landuse.build()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   landuse LANDUSE_BUILD_TASK_COMPLETED')
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_landuse)
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def build_soils_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:soils'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        soils = Soils.getInstance(wd)
        soils.build()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   soils SOILS_BUILD_TASK_COMPLETED')
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_soils)
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

    
def build_climate_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:climate'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        climate = Climate.getInstance(wd)
        climate.build()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   climate CLIMATE_BUILD_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_climate)
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def run_ash_rq(runid: str, fire_date: str, ini_white_ash_depth_mm: float, ini_black_ash_depth_mm: float):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:ash'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        ash = Ash.getInstance(wd)
        ash.run_ash(fire_date, ini_white_ash_depth_mm, ini_black_ash_depth_mm)

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   ash ASH_RUN_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.run_watar)


    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def run_debris_flow_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:debris_flow'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        debris = DebrisFlow.getInstance(wd)
        debris.run_debris_flow()

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   debris_flow DEBRIS_FLOW_RUN_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.run_watar)

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def run_rhem_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:rhem'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        rhem = Rhem.getInstance(wd)
        rhem.clean()
        rhem.prep_hillslopes()
        rhem.run_hillslopes()

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   rhem RHEM_RUN_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.run_rhem)

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

# Fork Functions

def _finish_fork_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:fork'
        StatusMessenger.publish(status_channel, 'Running WEPP... done\n')
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_COMPLETE')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _clean_env_for_system_tools():
    env = {
        "PATH": "/usr/sbin:/usr/bin:/bin",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        # Add anything else you *explicitly* need here (e.g., TZ)
    }
    return env


def fork_rq(runid: str, new_runid: str, undisturbify=False):
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:fork'

    # DEBUG HELPER: This function will run in a thread to read a stream
    # line-by-line and put the lines into a queue.
    def stream_reader(stream, queue):
        """Reads lines from a stream and puts them into a queue."""
        try:
            for line in iter(stream.readline, ''):
                queue.put(line)
        finally:
            stream.close()

    try:
        StatusMessenger.publish(
            status_channel, f'rq:{job.id} STARTED {func_name}({runid})'
        )
        StatusMessenger.publish(status_channel, f'undisturbify: {undisturbify}')

        # 1. Verify rsync exists
        rsync_path = shutil.which('rsync')
        StatusMessenger.publish(status_channel, f"Checking for rsync...")
        if not rsync_path:
            error_msg = "ERROR: 'rsync' command not found in PATH for rqworker user."
            StatusMessenger.publish(status_channel, error_msg)
            raise FileNotFoundError(error_msg)
        StatusMessenger.publish(status_channel, f"Found rsync at: {rsync_path}")

        wd = get_wd(runid)
        new_wd = get_wd(new_runid)

        run_left = wd if wd.endswith('/') else f'{wd}/'
        run_right = new_wd if new_wd.endswith('/') else f'{new_wd}/'

        # 2. Verify destination directory can be created
        right_parent = os.path.dirname(run_right.rstrip('/'))
        StatusMessenger.publish(
            status_channel, f"Destination parent directory: {right_parent}"
        )
        if not os.path.exists(right_parent):
            StatusMessenger.publish(
                status_channel, f"Parent does not exist. Creating..."
            )
            os.makedirs(right_parent)
        else:
            StatusMessenger.publish(status_channel, f"Parent already exists.")

        if not os.path.exists(right_parent):
            error_msg = f"FATAL: Failed to create parent directory: {right_parent}"
            StatusMessenger.publish(status_channel, error_msg)
            raise FileNotFoundError(error_msg)

        cmd = ['rsync', '-av', '--progress', '.', run_right]
        if undisturbify:
            cmd.extend(['--exclude', 'wepp/runs', '--exclude', 'wepp/output'])

        _cmd = ' '.join(cmd)
        StatusMessenger.publish(status_channel, f'Running cmd: {_cmd}')
        StatusMessenger.publish(status_channel, f'In directory: {run_left}')

        env = _clean_env_for_system_tools()
        # 3. Run rsync and process streams in real-time
        p = Popen(
            cmd,
            stdout=PIPE,
            stderr=PIPE,
            cwd=run_left,
            text=True,
            bufsize=1,
            env=env
        )

        # Create queues and threads to handle stdout and stderr
        stdout_q = queue.Queue()
        stderr_q = queue.Queue()
        stdout_thread = threading.Thread(
            target=stream_reader, args=(p.stdout, stdout_q)
        )
        stderr_thread = threading.Thread(
            target=stream_reader, args=(p.stderr, stderr_q)
        )
        stdout_thread.start()
        stderr_thread.start()

        stdout_output = []
        stderr_output = []

        # Process output until the command finishes
        while p.poll() is None:
            # Live stream stdout to the user
            while not stdout_q.empty():
                line = stdout_q.get()
                StatusMessenger.publish(status_channel, line)
                stdout_output.append(line)

            # Live stream stderr to the user
            while not stderr_q.empty():
                line = stderr_q.get()
                StatusMessenger.publish(status_channel, f"rsync stderr: {line}")
                stderr_output.append(line)

            time.sleep(0.01)  # Prevent busy-waiting

        # Wait for the process and threads to finish
        p.wait()
        stdout_thread.join()
        stderr_thread.join()

        # Process any remaining output in the queues
        while not stdout_q.empty():
            line = stdout_q.get()
            stripped_line = line.strip()
            if stripped_line:
                StatusMessenger.publish(status_channel, stripped_line)
            stdout_output.append(line)

        while not stderr_q.empty():
            line = stderr_q.get()
            stripped_line = line.strip()
            if stripped_line:
                StatusMessenger.publish(status_channel, f"rsync stderr: {stripped_line}")
            stderr_output.append(line)

        # 4. Check results and report errors
        if p.returncode != 0:
            full_stdout = "".join(stdout_output).strip()
            full_stderr = "".join(stderr_output).strip()
            error_msg = (
                f"ERROR: rsync failed with return code {p.returncode}:\n"
                f"stdout:\n---\n{full_stdout}\n---\n"
                f"stderr:\n---\n{full_stderr}\n---"
            )
            StatusMessenger.publish(status_channel, error_msg)
            raise Exception(error_msg)

        StatusMessenger.publish(status_channel, 'rsync successful. Setting wd in .nodbs...\n')

        nodbs = glob(os.path.join(new_wd, '*.nodb'))
        for fn in nodbs:
            StatusMessenger.publish(status_channel, f'  {fn}')
            with open(fn) as fp:
                s = fp.read()

            s = s.replace(wd, new_wd).replace(runid, new_runid)
            with open(fn, 'w') as fp:
                fp.write(s)

        StatusMessenger.publish(status_channel, 'Setting wd in .nodbs... done.\n')
        StatusMessenger.publish(status_channel, 'Cleanup locks, READONLY, PUBLIC...\n')

        for lock_file in glob(os.path.join(new_wd, '*.lock')):
            os.remove(lock_file)

        for special_file in ['READONLY', 'PUBLIC']:
            fn = os.path.join(new_wd, special_file)
            if os.path.exists(fn):
                os.remove(fn)

        StatusMessenger.publish(status_channel, 'Cleanup locks, READONLY, PUBLIC... done.\n')

        if undisturbify:
            StatusMessenger.publish(status_channel, 'Undisturbifying Project...\n')
            ron = Ron.getInstance(new_wd)
            ron.scenario = 'Undisturbed'
            
            StatusMessenger.publish(status_channel, 'Removing SBS...\n')
            disturbed = Disturbed.getInstance(new_wd)
            disturbed.remove_sbs()
            StatusMessenger.publish(status_channel, 'Removing SBS... done.\n')

            StatusMessenger.publish(status_channel, 'Rebuilding Landuse...\n')
            landuse = Landuse.getInstance(new_wd)
            landuse.build()
            StatusMessenger.publish(status_channel, 'Rebuilding Landuse... done.\n')

            StatusMessenger.publish(status_channel, 'Rebuilding Soils...\n')
            soils = Soils.getInstance(new_wd)
            soils.build()
            StatusMessenger.publish(status_channel, 'Rebuilding Soils... done.\n')

            StatusMessenger.publish(status_channel, 'Rerunning WEPP...\n')
            
            # Connect to Redis and enqueue the jobs
            final_wepp_job = run_wepp_rq(new_runid)

            conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
            with redis.Redis(**conn_kwargs) as redis_conn:
                q = Queue(connection=redis_conn)
            
                # Enqueue the final completion message job, dependent on the WEPP run
                q.enqueue(
                    _finish_fork_rq,
                    args=[runid], 
                    depends_on=final_wepp_job
                )

        else:
            StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_COMPLETE')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

# Archive Backend Functions
# see wepppy/weppcloud/routes/usersum/dev-notes/weppcloud-project-archiving.md for archive architecture
def archive_rq(runid: str, comment: Optional[str] = None):
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:archive'
    StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

    prep = None
    archive_path_tmp = None
    try:
        prep = RedisPrep.getInstanceFromRunID(runid)
        wd = get_wd(runid)

        archives_dir = os.path.join(wd, 'archives')
        os.makedirs(archives_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        archive_name = f'{runid}.{timestamp}.zip'
        archive_path = os.path.join(archives_dir, archive_name)
        archive_path_tmp = archive_path + '.tmp'

        for candidate in (archive_path, archive_path_tmp):
            if os.path.exists(candidate):
                os.remove(candidate)

        StatusMessenger.publish(status_channel, f'Creating archive {archive_name}')

        comment_bytes = (comment or '').encode('utf-8')

        with zipfile.ZipFile(archive_path_tmp, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(wd):
                rel_root = os.path.relpath(root, wd)
                if rel_root == '.':
                    rel_root = ''

                # Skip the archives directory entirely
                if rel_root.startswith('archives'):
                    dirs[:] = []
                    continue

                dirs[:] = [d for d in dirs if not os.path.relpath(os.path.join(root, d), wd).startswith('archives')]

                for filename in files:
                    abs_path = os.path.join(root, filename)
                    arcname = os.path.relpath(abs_path, wd)
                    if arcname.startswith('archives'):
                        continue

                    StatusMessenger.publish(status_channel, f'Adding {arcname}')
                    zf.write(abs_path, arcname)

            if comment_bytes:
                zf.comment = comment_bytes

        os.replace(archive_path_tmp, archive_path)
        StatusMessenger.publish(status_channel, f'Archive ready: {archive_name}')
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   archive ARCHIVE_COMPLETE')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
    finally:
        if archive_path_tmp and os.path.exists(archive_path_tmp):
            try:
                os.remove(archive_path_tmp)
            except OSError:
                pass

        if prep is None:
            try:
                prep = RedisPrep.getInstanceFromRunID(runid)
            except Exception:
                prep = None

        if prep is not None:
            try:
                prep.clear_archive_job_id()
            except Exception:
                pass


def restore_archive_rq(runid: str, archive_name: str):
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:archive'
    StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, {archive_name})')

    prep = None
    try:
        prep = RedisPrep.getInstanceFromRunID(runid)
        wd = Path(get_wd(runid)).resolve()

        archives_dir = wd / 'archives'
        archive_path = (archives_dir / archive_name).resolve()

        if not archive_path.exists() or not archive_path.is_file():
            raise FileNotFoundError(f'Archive not found: {archive_name}')

        # Ensure the archive resides inside the archives directory
        if archives_dir not in archive_path.parents:
            raise ValueError('Invalid archive path')

        StatusMessenger.publish(status_channel, f'Preparing to restore from {archive_name}')

        # Remove all existing contents except the archives directory itself.
        for entry in sorted(wd.iterdir()):
            if entry.name == 'archives':
                continue

            try:
                if entry.is_dir() and not entry.is_symlink():
                    StatusMessenger.publish(status_channel, f'Removing directory {entry.relative_to(wd)}')
                    shutil.rmtree(entry)
                else:
                    StatusMessenger.publish(status_channel, f'Removing file {entry.relative_to(wd)}')
                    entry.unlink()
            except FileNotFoundError:
                continue

        with zipfile.ZipFile(archive_path, mode='r') as zf:
            for member in zf.infolist():
                arcname = member.filename
                if not arcname:
                    continue

                # Normalize name to avoid traversal attempts
                target_path = (wd / arcname).resolve()
                if wd not in target_path.parents and target_path != wd:
                    raise ValueError(f'Unsafe archive member path: {arcname}')

                # Skip anything targeting the archives directory to avoid overwriting archives
                try:
                    relative_target = target_path.relative_to(wd)
                except ValueError:
                    raise ValueError(f'Unsafe archive member path: {arcname}')

                if relative_target.parts and relative_target.parts[0] == 'archives':
                    continue

                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    StatusMessenger.publish(status_channel, f'Restored directory {relative_target}')
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member, 'r') as src, open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

                perm = member.external_attr >> 16
                if perm:
                    try:
                        os.chmod(target_path, perm)
                    except OSError:
                        pass

                StatusMessenger.publish(status_channel, f'Restored file {relative_target}')

        try:
            cleared_entries = clear_nodb_file_cache(runid)
        except Exception as exc:
            StatusMessenger.publish(status_channel, f'Warning: failed to clear NoDb cache after restore ({exc})')
        else:
            StatusMessenger.publish(
                status_channel,
                f'Cleared NoDb cache entries after restore ({len(cleared_entries)})'
            )

        StatusMessenger.publish(status_channel, f'Restore complete: {archive_name}')
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   archive RESTORE_COMPLETE')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
    finally:
        if prep is None:
            try:
                prep = RedisPrep.getInstanceFromRunID(runid)
            except Exception:
                prep = None

        if prep is not None:
            try:
                prep.clear_archive_job_id()
            except Exception:
                pass

# RAP_TS Functions

def fetch_and_analyze_rap_ts_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:rap_ts'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        climate = Climate.getInstance(wd)
        assert climate.observed_start_year is not None
        assert climate.observed_end_year is not None

        rap_ts = RAP_TS.getInstance(wd)
        rap_ts.acquire_rasters(start_year=climate.observed_start_year,
                               end_year=climate.observed_end_year)
        rap_ts.analyze()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   rap_ts RAP_TS_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.run_rhem)

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
