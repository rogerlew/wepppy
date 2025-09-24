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

from deprecated import deprecated


from ....base import NoDbBase, TriggerEvents, nodb_setter

from ..location_mixin import LocationMixin

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


@deprecated(reason='Use Disturbed instead')
class LakeTahoeNoDbLockedException(Exception):
    pass


DEFAULT_WEPP_TYPE = 'Granitic'

@deprecated(reason='Use Disturbed instead')
class LakeTahoe(NoDbBase, LocationMixin):
    __name__ = 'LakeTahoe'

    filename = 'lt.nodb'
    
    def __init__(self, wd, cfg_fn):
        super(LakeTahoe, self).__init__(wd, cfg_fn)

        with self.locked():
            self._lc_lookup_fn = 'landSoilLookup.csv'
            self._default_wepp_type = DEFAULT_WEPP_TYPE
            self._data_dir = _data_dir

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
    @nodb_setter
    def lc_lookup_fn(self, value):
        self._lc_lookup_fn = value

    @property
    def default_wepp_type(self):
        if not hasattr(self, '_default_wepp_type'):
            return DEFAULT_WEPP_TYPE

        return self._default_wepp_type

    @default_wepp_type.setter
    @nodb_setter
    def default_wepp_type(self, value):
        self._default_wepp_type = value

    @property
    def data_dir(self):
        global _data_dir

        if not hasattr(self, '_data_dir'):
            return _data_dir

        return self._data_dir
