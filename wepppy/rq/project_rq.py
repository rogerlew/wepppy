import shutil
from glob import glob

import socket
import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import inspect

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
    Soils, SoilsMode
)
from wepppy.nodb.redis_prep import RedisPrep

from wepppy.nodb.status_messenger import StatusMessenger

from .wepp_rq import run_wepp_rq

_hostname = socket.gethostname()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

DEFAULT_ZOOM = 12

project_def = {
    "config": "wepp",
    "name": "test",
    "scenario": "test",
    "map": {
        "extent": [-122.7, 45.5, -122.4, 45.7],
        "center": [-122.55, 45.6],
        "zoom": 12
    },
    "watershed": {
        "outlet": [-122.5, 45.6]
    },
    "disturbed": {
        "sbs_map": "sbs_map.tif"
    }

}

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
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def fetch_dem_rq(runid: str, extent, center, zoom):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:watershed'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        
        if center is None:
            center = [(extent[0]+extent[2])/2, (extent[1]+extent[3])/2]
        
        if zoom is None:
            zoom = DEFAULT_ZOOM
            
        ron = Ron.getInstance(wd)
        ron.set_map(extent, center, zoom)
        ron.fetch_dem()
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def build_channels_rq(runid: str, outlet_lng: float, outlet_lat: float):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:watershed'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed = Watershed.getInstance(wd)
        watershed.set_outlet(outlet_lng, outlet_lat)
        watershed.build_channels()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def build_subcatchments_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:watershed'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed = Watershed.getInstance(wd)
        watershed.build_subcatchments()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def abstract_watershed_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:watershed'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed = Watershed.getInstance(wd)
        watershed.abstract_watershed()
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
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def build_soils_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:climate'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        soils = Soils.getInstance(wd)
        soils.build()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
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
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
