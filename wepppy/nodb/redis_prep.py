import os

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import time
import redis


class RedisPrep:
    def __init__(self, wd, cfg_fn=None):
        wd = wd.rstrip('/')
        self.wd = wd
        self.cfg_fn = cfg_fn
        self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        parent, run_id = _split(wd)
        self.run_id = run_id
    
        if not _exists(self.dump_filepath):
            self._set_bool_config('loaded', v)

    @staticmethod
    def getInstance(wd):
        self = RedisPrep(wd)
        self.lazy_load()
        return self

    @property
    def dump_filepath(self):
        return os.path.join(self.wd, 'redisprep.dump')

    def dump(self):
        all_fields_and_values = self.redis.hgetall(self.run_id)

        with open(self.dump_filepath, 'w') as dump_file:
            json.dump(all_fields_and_values, dump_file)

    def lazy_load(self):
        if self._get_bool_config('loaded'):
            return

        if _exists(self.dump_filepath):
            with open(dump_filepath, 'r') as dump_file:
                all_fields_and_values = json.load(dump_file)
            
            for field, value in all_fields_and_values.items():
                self.redis.hset(self.run_id, field, value)

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

    def timestamp(self, key):
        now = int(time.time())
        self.__setitem__(key, now)
    
    def __setitem__(self, key, value: int):
        self.redis.hset(self.run_id, f'timestamps:{key}', value)
        self.dump()
    
    def __getitem__(self, key):
        v = self.redis.hget(self.run_id, f'timestamps:{key}')
        if v is None:
            return None
        return int(v)
    
