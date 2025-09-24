import shutil
from glob import glob

import socket
import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import inspect
import time
import shutil
import queue
import stat
import threading
from queue import Queue
from functools import wraps
from subprocess import Popen, PIPE, call
import zipfile
from pathlib import Path
from datetime import datetime

import redis
from rq import Queue, get_current_job

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.nodb import (
    Disturbed, Ron, 
    Wepp, Watershed, 
    Climate, ClimateMode, ClimateSpatialMode,
    WeppPost, Landuse, LanduseMode, 
    Soils, SoilsMode, Ash, DebrisFlow,
    Rhem, RAP_TS
)

from wepppy.topo.topaz import (
    WatershedBoundaryTouchesEdgeError,
    MinimumChannelLengthTooShortError
)

from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from .wepp_rq import run_wepp_rq

_hostname = socket.gethostname()

from dotenv import load_dotenv
_thisdir = os.path.dirname(__file__)

load_dotenv(_join(_thisdir, '.env'))

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

TIMEOUT = 43_200
DEFAULT_ZOOM = 12

def new_project_rq(runid: str, project_def: dict):
    """
    assumes a runid has been assigned and an empty wd has been created.
    """
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        wd = get_wd(runid)
        config = project_def['config']            
        cfg = "%s.cfg" % config

        ron = Ron(wd, cfg)
        
        name = project_def.get('name')
        scenario = project_def.get('scenario')
        if name:
            ron.name = name
        if scenario:
            ron.scenario = scenario

        # fetch dem
        extent = project_def['map']['extent']       # in wgs84: left, bottom, right, top
        center = project_def['map'].get('center')   # optional in wgs84
        zoom = project_def['map'].get('zoom')       # optional in wgs84
        fetch_dem_rq(runid, extent, center, zoom)

        # delineate channels
        build_channels_rq(runid)

        # set outlet
        outlet_lng, outlet_lat = project_def['watershed']['outlet'] # in wgs84: lng, lat
        build_channels_rq(runid, outlet_lng, outlet_lat)

        # delineate subcatchments
        build_subcatchments_rq(runid)

        # abstract watershed    
        abstract_watershed_rq(runid)

        # check for sbs map
        sbs_map = None
        disturbed_def = project_def.get('disturbed')
        if disturbed_def:
            sbs_map = disturbed_def.get('sbs_map')

        if sbs_map:
            if 'disturbed' not in ron.mods:
                raise Exception('disturbed module not defined in ron.mods')
            
            init_sbs_map_rq(runid, sbs_map)

        # build landuse
        landuse = Landuse.getInstance(wd)
        landuse.mode = LanduseMode.Gridded

        build_landuse_rq(runid)

        # build soil
        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode.Gridded

        build_soils_rq(runid)

        # build climate
        climate_mode = project_def['climate'].get('mode', 'vanilla')
        climate_spatialmode = project_def['climate'].get('spatial_mode', 'multiple')

        climate = Climate.getInstance(wd)
        climate.climate_mode = ClimateMode.parse(climate_mode)
        climate.climate_spatialmode = ClimateSpatialMode.parse(climate_spatialmode)

        climatestation = project_def['climate'].get('station_id')
        if climatestation:
            climate.climatestation = climatestation
            
            # validate climatestation id is in database
            climatestation_meta = climate.climatestation_meta
            assert climatestation_meta

        else:
            stations = climate.find_closest_stations()
            climate.climatestation = stations[0]['id']

        start_year = project_def['climate'].get('start_year')
        end_year = project_def['climate'].get('end_year')

        if start_year or end_year:
            if climate.climate_mode == ClimateMode.Future:
                climate.set_future_pars(start_year=start_year, end_year=end_year)
            else:
                climate.set_observed_pars(start_year=start_year, end_year=end_year)

        build_climate_rq(runid)

        run_wepp_rq(runid)

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
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
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.fetch_dem)
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

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_subcatchments)
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

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

            with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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


def archive_rq(runid: str):
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

# todo: observed
