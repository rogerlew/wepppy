# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard libraries

import os
from os.path import join as _join
from os.path import exists as _exists
import time

from deprecated import deprecated

# non-standard
import jsonpickle

# weppy submodules
from .base import NoDbBase

@deprecated
class PrepNoDbLockedException(Exception):
    pass

@deprecated
class Prep(NoDbBase):
    __name__ = 'Prep'

    def __init__(self, wd, cfg_fn):

        super(Prep, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._sbs_required = False
            self._has_sbs = False
            self._timestamps = {}
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd, allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'prep.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Prep), db

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
        return Prep.getInstance(
            get_wd(runid, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock))

    @property
    def sbs_required(self):
        return getattr(self, '_sbs_required', False)

    @sbs_required.setter
    def sbs_required(self, v: bool):
        self.lock()
        try:
            self._sbs_required = v
            self.dump_and_unlock()
        except:
            self.unlock('-f')
            raise

    @property
    def has_sbs(self):
        return getattr(self, '_has_sbs', False)

    @has_sbs.setter
    def has_sbs(self, v: bool):
        self.lock()
        try:
            self._has_sbs = v
            self.dump_and_unlock()
        except:
            self.unlock('-f')
            raise

    @property
    def _nodb(self):
        return _join(self.wd, 'prep.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'prep.nodb.lock')

    def timestamp(self, key):
        now = int(time.time())
        self.__setitem__(key, now)

    def __setitem__(self, key, value: int):
        self.lock()
        try:
            self._timestamps[key] = value
            self.dump_and_unlock()
        except:
            self.unlock('-f')
            raise

    def __getitem__(self, key):
        return self._timestamps.get(key, None)
