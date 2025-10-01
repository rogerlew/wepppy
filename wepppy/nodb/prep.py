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

# weppy submodules
from .base import NoDbBase, nodb_setter

@deprecated
class PrepNoDbLockedException(Exception):
    pass

@deprecated
class Prep(NoDbBase):
    __name__ = 'Prep'

    filename = 'prep.nodb'

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):

        super(Prep, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._sbs_required = False
            self._has_sbs = False
            self._timestamps = {}

    @property
    def sbs_required(self):
        return getattr(self, '_sbs_required', False)

    @sbs_required.setter
    @nodb_setter
    def sbs_required(self, v: bool):
        self._sbs_required = v

    @property
    def has_sbs(self):
        return getattr(self, '_has_sbs', False)

    @has_sbs.setter
    @nodb_setter
    def has_sbs(self, v: bool):
        self._has_sbs = v

    def timestamp(self, key):
        now = int(time.time())
        self.__setitem__(key, now)

    def __setitem__(self, key, value: int):
        with self.locked():
            self._timestamps[key] = value

    def __getitem__(self, key):
        return self._timestamps.get(key, None)
