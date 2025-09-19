import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir

import json
import shutil

# non-standard
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
    filename = 'subbasins.nodb'
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
