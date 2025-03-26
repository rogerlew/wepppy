import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir

import json
import shutil

# non-standard
import jsonpickle
import utm
import what3words

# wepppy
import requests


from .base import (
    NoDbBase,
    TriggerEvents
)


class SubbasinsNoDbLockedException(Exception):
    pass



class Subbasins(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Subbasins'

    __exclude__ = ('_w3w', 
                   '_locales', 
                   '_enable_landuse_change',
                   '_dem_db',
                   '_boundary')

    def __init__(self, wd, cfg_fn='0.cfg'):
        super(Subbasins, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            
            if not _exists(self.subbasins_dir):
                os.makedirs(self.subbasins_dir)

            self._channels = []

        except Exception:
            self.unlock('-f')
            raise

    @property
    def channels(self):
        return self._channels
    
    @channels.setter
    def channels(self, value):
        self._channels = value

    @property
    def subbasins_dir(self):
        return _join(self.wd, 'wepp', 'subbasins')

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'subbasins.nodb')

        if not _exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Subbasins), db

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Subbasins.getInstance(
            get_wd(runid, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock))

    @property
    def _nodb(self):
        return _join(self.wd, 'subbasins.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'subbasins.nodb.lock')

    def _Subbasins_builder(self):
        for scenario in self.channels:
            _build_scenario(scenario, self.runid)


if __name__ == '__main__':
     _build_scenario('uniform low', '/geodata/weppcloud_runs/rlew-discretionary-pulsar/')