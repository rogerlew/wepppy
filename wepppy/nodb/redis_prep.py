import os
from enum import Enum

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import json
import time
import redis

from dotenv import load_dotenv
_thisdir = os.path.dirname(__file__)

load_dotenv(_join(_thisdir, '.env'))

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')


class TaskEnum(Enum):
    project_init = 'project_init'
    set_outlet = 'set_outlet'
    abstract_watershed = 'abstract_watershed'
    build_channels = 'build_channels'
    find_outlet = 'find_outlet'
    build_subcatchments = 'build_subcatchments'
    build_landuse = 'build_landuse'
    build_soils = 'build_soils'
    build_climate = 'build_climate'
    fetch_rap_ts = 'build_rap_ts'
    run_wepp_hillslopes = 'run_wepp_hillslopes'
    run_wepp_watershed = 'run_wepp_watershed'
    run_observed = 'run_observed'
    run_debris = 'run_debris'
    run_watar = 'run_watar'
    run_rhem = 'run_rhem'
    fetch_dem = 'fetch_dem'
    landuse_map = 'landuse_map'
    init_sbs_map = 'init_sbs_map'
    run_omni_scenarios = 'run_omni_scenarios'
    run_omni_contrasts = 'run_omni_contrasts'
    dss_export = 'dss_export'
    set_readonly = 'set_readonly'

    def __str__(self):
        return self.value.replace('TaskEnum.', '')
    
    def label(self):
        return {
            TaskEnum.project_init: 'Initialize Project',
            TaskEnum.set_outlet: 'Set Outlet',
            TaskEnum.abstract_watershed: 'Abstract Watershed',
            TaskEnum.build_channels: 'Build Channels',
            TaskEnum.find_outlet: 'Find Outlet',
            TaskEnum.build_subcatchments: 'Build Subcatchments',
            TaskEnum.build_landuse: 'Build Landuse',
            TaskEnum.build_soils: 'Build Soils',
            TaskEnum.build_climate: 'Build Climate',
            TaskEnum.fetch_rap_ts: 'Build RAP TS',
            TaskEnum.run_wepp_hillslopes: 'Run WEPP Hillslopes',
            TaskEnum.run_wepp_watershed: 'Run WEPP Watershed',
            TaskEnum.run_observed: 'Run Observed',
            TaskEnum.run_debris: 'Run Debris',
            TaskEnum.run_watar: 'Run WATAR',
            TaskEnum.run_rhem: 'Run RHEM',
            TaskEnum.fetch_dem: 'Fetch DEM',
            TaskEnum.landuse_map: 'Landuse Map',
            TaskEnum.init_sbs_map: 'Initialize SBS Map',
            TaskEnum.run_omni_scenarios: 'Run OMNI Scenarios',
            TaskEnum.run_omni_contrasts: 'Run OMNI Contrasts',
            TaskEnum.dss_export: 'Export DSS',
            TaskEnum.set_readonly: 'Set Readonly',
        }.get(self.value, self.value)


class RedisPrep:
    def __init__(self, wd, cfg_fn=None):
        self.wd = wd
        self.cfg_fn = cfg_fn
        self.redis = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
        parent, run_id = _split(wd.rstrip('/'))
        self.run_id = run_id
        if not _exists(self.dump_filepath):
            self._set_bool_config('loaded', True)

    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        instance = RedisPrep(wd)
        instance.lazy_load()
        return instance

    @staticmethod
    def tryGetInstance(wd='.', allow_nonexistent=True, ignore_lock=False):
        try:
            return RedisPrep.getInstance(wd, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)
        except FileNotFoundError:
            return None
        
    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return RedisPrep.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)

    @property
    def dump_filepath(self):
        return _join(self.wd, 'redisprep.dump')

    def dump(self):
        all_fields_and_values = self.redis.hgetall(self.run_id)
        filtered_fields_and_values = {k: v for k, v in all_fields_and_values.items() if not k.startswith('locked:')}

        with open(self.dump_filepath, 'w') as dump_file:
            json.dump(filtered_fields_and_values, dump_file)

    def lazy_load(self):
        if self._get_bool_config('loaded'):
            return

        if _exists(self.dump_filepath):
            with open(self.dump_filepath, 'r') as dump_file:
                all_fields_and_values = json.load(dump_file)

            for field, value in all_fields_and_values.items():
                self.redis.hset(self.run_id, field, value)
            self.redis.hset(self.run_id, 'attrs:loaded', 'true')

    @property
    def sbs_required(self):
        return self._get_bool_config('sbs_required')

    @sbs_required.setter
    def sbs_required(self, v: bool):
        self._set_bool_config('sbs_required', v)

    @property
    def has_sbs(self):
        return self._get_bool_config('has_sbs')

    @has_sbs.setter
    def has_sbs(self, v: bool):
        self._set_bool_config('has_sbs', v)

    def _get_bool_config(self, key):
        value = self.redis.hget(self.run_id, f'attrs:{key}')
        return value.lower() == 'true' if value is not None else False

    def _set_bool_config(self, key, value):
        self.redis.hset(self.run_id, f'attrs:{key}', str(bool(value)).lower())
        self.dump()

    def timestamp(self, key: TaskEnum):
        now = int(time.time())
        self.__setitem__(str(key), now)

    def remove_timestamp(self, key: TaskEnum):
        self.redis.hdel(self.run_id, f'timestamps:{key}')
        self.dump()

    def __setitem__(self, key, value: int):
        self.redis.hset(self.run_id, f'timestamps:{key}', value)
        self.dump()

    def __getitem__(self, key):
        v = self.redis.hget(self.run_id, f'timestamps:{key}')
        if v is None:
            return None
        return int(v)
    
    def set_rq_job_id(self, key, job_id):
        self.redis.hset(self.run_id, f'rq:{key}', job_id)
        self.dump()

    def get_rq_job_id(self, key):
        v = self.redis.hget(self.run_id, f'rq:{key}')
        if v is None:
            return None
        return v

    def get_rq_job_ids(self):
        keys = self.redis.hkeys(self.run_id)
        job_ids = {}
        for key in keys:
            if key.startswith('rq:'):
                job_ids[key[3:]] = self.redis.hget(self.run_id, key)
        return job_ids

    def set_archive_job_id(self, job_id):
        self.redis.hset(self.run_id, 'archive:job_id', job_id)
        self.dump()

    def get_archive_job_id(self):
        return self.redis.hget(self.run_id, 'archive:job_id')

    def clear_archive_job_id(self):
        self.redis.hdel(self.run_id, 'archive:job_id')
        self.dump()
