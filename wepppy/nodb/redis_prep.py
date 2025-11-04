"""Redis-backed metadata helper mirroring the legacy Prep controller."""

from __future__ import annotations

import json
import os
import time
from enum import Enum
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from typing import Dict, Optional

from wepppy.config.redis_settings import RedisDB, redis_client


class TaskEnum(Enum):
    """Enumerate workflow tasks mirrored into Redis progress keys."""

    if_exists_rmtree = 'rmtree'
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
    run_path_cost_effective = 'run_path_ce'

    def __str__(self) -> str:
        return self.value.replace('TaskEnum.', '')
    
    def label(self) -> str:
        """Return a human-friendly label for the task."""

        return {
            TaskEnum.if_exists_rmtree: 'Remove existing files',
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
            TaskEnum.run_path_cost_effective: 'Run PATH Cost-Effective',
        }.get(self, self.value)
    
    def emoji(self) -> str:
        """Return an emoji glyph representing the task."""

        return {
            TaskEnum.if_exists_rmtree: '🗑️',
            TaskEnum.project_init: '🚀',
            TaskEnum.set_outlet: '📍',
            TaskEnum.abstract_watershed: '💎',
            TaskEnum.build_channels: '🌊',
            TaskEnum.find_outlet: '📍',
            TaskEnum.build_subcatchments: '🧩',
            TaskEnum.build_landuse: '🌲',
            TaskEnum.build_soils: '🪱',
            TaskEnum.build_climate: '☁️',
            TaskEnum.fetch_rap_ts: '🗺️',
            TaskEnum.run_wepp_hillslopes: '💧',
            TaskEnum.run_wepp_watershed: '🏃',
            TaskEnum.run_observed: '📊',
            TaskEnum.run_debris: '🪨',
            TaskEnum.run_watar: '🌋',
            TaskEnum.run_rhem: '🌵',
            TaskEnum.fetch_dem: '🌍',
            TaskEnum.landuse_map: '🗺️',
            TaskEnum.init_sbs_map: '🔥',
            TaskEnum.run_omni_scenarios: '🪓',
            TaskEnum.run_omni_contrasts: '⚖️',
            TaskEnum.dss_export: '📤',
            TaskEnum.set_readonly: '🔒',
            TaskEnum.run_path_cost_effective: '🧮',
        }.get(self, self.value)

    def __getstate__(self) -> str:
        return self.value


class RedisPrep:
    """Cache limited Prep metadata in Redis for lightweight lookups."""

    def __init__(self, wd: str, cfg_fn: Optional[str] = None):
        self.wd = wd
        self.cfg_fn = cfg_fn
        self.redis = redis_client(RedisDB.LOCK, decode_responses=True)
        parent, run_id = _split(wd.rstrip('/'))
        self.run_id = run_id
        if not _exists(self.dump_filepath):
            self._set_bool_config('loaded', True)

    def __getstate__(self) -> Dict[str, Optional[str]]:
        return {
            'wd': self.wd,
            'cfg_fn': self.cfg_fn,
            'run_id': self.run_id,
        }

    @staticmethod
    def getInstance(wd: str = '.', allow_nonexistent: bool = False, ignore_lock: bool = False) -> 'RedisPrep':
        instance = RedisPrep(wd)
        instance.lazy_load()
        return instance

    @staticmethod
    def tryGetInstance(wd: str = '.', allow_nonexistent: bool = True, ignore_lock: bool = False) -> Optional['RedisPrep']:
        try:
            return RedisPrep.getInstance(wd, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)
        except FileNotFoundError:
            return None
        
    @staticmethod
    def getInstanceFromRunID(runid: str, allow_nonexistent: bool = False, ignore_lock: bool = False) -> 'RedisPrep':
        from wepppy.weppcloud.utils.helpers import get_wd
        return RedisPrep.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)

    @property
    def dump_filepath(self) -> str:
        return _join(self.wd, 'redisprep.dump')

    def dump(self) -> None:
        all_fields_and_values = self.redis.hgetall(self.run_id)
        filtered_fields_and_values = {k: v for k, v in all_fields_and_values.items() if not k.startswith('locked:')}

        if not _exists(self.wd):
            return
        
        with open(self.dump_filepath, 'w') as dump_file:
            json.dump(filtered_fields_and_values, dump_file)

    def lazy_load(self) -> None:
        if self._get_bool_config('loaded'):
            return

        if _exists(self.dump_filepath):
            with open(self.dump_filepath, 'r') as dump_file:
                all_fields_and_values = json.load(dump_file)

            for field, value in all_fields_and_values.items():
                self.redis.hset(self.run_id, field, value)
            self.redis.hset(self.run_id, 'attrs:loaded', 'true')

    @property
    def sbs_required(self) -> bool:
        return self._get_bool_config('sbs_required')

    @sbs_required.setter
    def sbs_required(self, value: bool) -> None:
        self._set_bool_config('sbs_required', value)

    @property
    def has_sbs(self) -> bool:
        return self._get_bool_config('has_sbs')

    @has_sbs.setter
    def has_sbs(self, value: bool) -> None:
        self._set_bool_config('has_sbs', value)

    def _get_bool_config(self, key: str) -> bool:
        value = self.redis.hget(self.run_id, f'attrs:{key}')
        return value.lower() == 'true' if value is not None else False

    def _set_bool_config(self, key: str, value: bool) -> None:
        self.redis.hset(self.run_id, f'attrs:{key}', str(bool(value)).lower())
        self.dump()

    def timestamp(self, key: TaskEnum) -> None:
        now = int(time.time())
        self.__setitem__(str(key), now)

    def timestamps_report(self) -> str:
        s = [f'RedisPrep Timestamps ({self.run_id}):']
        for key in TaskEnum:
            timestamp = self.redis.hget(self.run_id, f'timestamps:{key}')
            s.append(f'  {key}: {timestamp}')
        return '\n'.join(s)

    def remove_timestamp(self, key: TaskEnum) -> None:
        self.redis.hdel(self.run_id, f'timestamps:{key}')
        self.dump()

    def remove_all_timestamp(self) -> None:
        for task in TaskEnum:
            self.redis.hdel(self.run_id, f'timestamps:{task}')
        self.dump()

    def __setitem__(self, key: str, value: int) -> None:
        self.redis.hset(self.run_id, f'timestamps:{key}', value)
        self.dump()

    def __getitem__(self, key: str) -> Optional[int]:
        v = self.redis.hget(self.run_id, f'timestamps:{key}')
        if v is None:
            return None
        return int(v)
    
    def set_rq_job_id(self, key: str, job_id: str) -> None:
        self.redis.hset(self.run_id, f'rq:{key}', job_id)
        self.dump()

    def get_rq_job_id(self, key: str) -> Optional[str]:
        v = self.redis.hget(self.run_id, f'rq:{key}')
        if v is None:
            return None
        return v

    def get_rq_job_ids(self) -> Dict[str, str]:
        keys = self.redis.hkeys(self.run_id)
        job_ids: Dict[str, str] = {}
        for key in keys:
            if key.startswith('rq:'):
                job_ids[key[3:]] = self.redis.hget(self.run_id, key)
        return job_ids

    def set_archive_job_id(self, job_id: str) -> None:
        self.redis.hset(self.run_id, 'archive:job_id', job_id)
        self.dump()

    def get_archive_job_id(self) -> Optional[str]:
        return self.redis.hget(self.run_id, 'archive:job_id')

    def clear_archive_job_id(self) -> None:
        self.redis.hdel(self.run_id, 'archive:job_id')
        self.dump()
