# Copyright (c) 2016-2020, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os

from os.path import join as _join
from os.path import exists as _exists

import jsonpickle

from ....base import NoDbBase, TriggerEvents

from ..location_mixin import LocationMixin

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class LakeTahoeNoDbLockedException(Exception):
    pass


DEFAULT_WEPP_TYPE = 'Granitic'


class LakeTahoe(NoDbBase, LocationMixin):
    __name__ = 'LakeTahoe'

    def __init__(self, wd, config):
        super(LakeTahoe, self).__init__(wd, config)

        self._lc_lookup_fn = 'landSoilLookup.csv'
        self._default_wepp_type = DEFAULT_WEPP_TYPE
        self._data_dir = _data_dir

        self.lock()

        # noinspection PyBroadException
        try:

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
            
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'lt.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, LakeTahoe), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'lt.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'lt.nodb.lock')

    def on(self, evt):
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
        if evt == TriggerEvents.LANDUSE_BUILD_COMPLETE:
            pass
        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()
        # elif evt == TriggerEvents.PREPPING_PHOSPHORUS:
        #     self.determine_phosphorus()

    @property
    def lc_lookup_fn(self):
        if not hasattr(self, '_lc_lookup_fn'):
            return 'landSoilLookup.csv'

        return self._lc_lookup_fn

    @lc_lookup_fn.setter
    def lc_lookup_fn(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._lc_lookup_fn = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def default_wepp_type(self):
        if not hasattr(self, '_default_wepp_type'):
            return DEFAULT_WEPP_TYPE

        return self._default_wepp_type

    @default_wepp_type.setter
    def default_wepp_type(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._default_wepp_type = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def data_dir(self):
        global _data_dir

        if not hasattr(self, '_data_dir'):
            return _data_dir

        return self._data_dir
