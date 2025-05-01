import shutil
from glob import glob

import socket
import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import inspect
import time

from functools import wraps
from subprocess import Popen, PIPE, call

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
        ron.fetch_dem()
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.fetch_dem)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def build_channels_rq(runid: str, csa: float, mcl: float):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed = Watershed.getInstance(wd)
        watershed.build_channels(csa, mcl)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   channel_delineation BUILD_CHANNELS_TASK_COMPLETED')
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_channels)
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def fetch_dem_and_build_channels_rq(runid: str, extent, center, zoom, csa, mcl):
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            
            ajob = q.enqueue_call(fetch_dem_rq, (runid, extent, center, zoom))
            job.meta['jobs:0,func:fetch_dem_rq'] = ajob.id
            job.save()

            bjob = q.enqueue_call(build_channels_rq, (runid, csa, mcl),  depends_on=ajob)
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

def fork_rq(runid: str, new_runid: str, undisturbify=False):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:fork'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')


        StatusMessenger.publish(status_channel, f'undisturbify: {undisturbify}')

        new_wd = get_wd(new_runid)

        run_left = wd
        if not run_left.endswith('/'):
            run_left += '/'

        run_right = new_wd
        if not run_right.endswith('/'):
            run_right += '/'

        right_parent = _split(run_right)[0]
        if not _exists(right_parent):
            os.makedirs(right_parent)

        cmd = ['rsync', '-av', '--progress', '.', run_right]

        if undisturbify:
            cmd.append('--exclude')
            cmd.append('wepp/runs')
            cmd.append('--exclude')
            cmd.append('wepp/output')

        _cmd = ' '.join(cmd)
        StatusMessenger.publish(status_channel, f'cmd: {_cmd}')

        p = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=run_left, bufsize=1, universal_newlines=True)

        # Process stdout in real-time
        for line in iter(p.stdout.readline, ''):
            StatusMessenger.publish(status_channel, line.strip())
        
        # Wait for process to complete
        p.wait()
        
        # Check for any errors
        if p.returncode != 0:
            for line in iter(p.stderr.readline, ''):
                StatusMessenger.publish(status_channel, f"ERROR: {line.strip()}")
            raise Exception(f"rsync command failed with return code {p.returncode}")
            
        StatusMessenger.publish(status_channel, 'Setting wd in .nodbs...\n')

        # replace the runid in the nodb files
        nodbs = glob(_join(new_wd, '*.nodb'))
        for fn in nodbs:
            StatusMessenger.publish(status_channel, f'  {fn}')
            with open(fn) as fp:
                s = fp.read()

            s = s.replace(wd, new_wd).replace(runid, new_runid)
            with open(fn, 'w') as fp:
                fp.write(s)
                
        StatusMessenger.publish(status_channel, 'Setting wd in .nodbs... done.\n')
        StatusMessenger.publish(status_channel, 'Cleanup locks, READONLY, PUBLIC...\n')

        # delete any active locks
        locks = glob(_join(new_wd, '*.lock'))
        for fn in locks:
            os.remove(fn)

        fn = _join(new_wd, 'READONLY')
        if _exists(fn):
            os.remove(fn)

        fn = _join(new_wd, 'PUBLIC')
        if _exists(fn):
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

            StatusMessenger.publish(status_channel, 'Running WEPP...\n')
            run_wepp_rq(new_runid)
            StatusMessenger.publish(status_channel, 'Running WEPP... done\n')

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_COMPLETE')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

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