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
from copy import deepcopy

from .....all_your_base import isfloat
from ....base import NoDbBase, TriggerEvents, config_get_path, config_get_str, config_get_float
from ....soils import Soils
from ....watershed import Watershed

from .....wepp.soils.utils import modify_kslast

from ..location_mixin import LocationMixin

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class GeneralModNoDbLockedException(Exception):
    pass


DEFAULT_WEPP_TYPE = 'Granitic'


class GeneralMod(NoDbBase, LocationMixin):
    __name__ = 'General'

    def __init__(self, wd, cfg_fn):
        super(GeneralMod, self).__init__(wd, cfg_fn)

        config = self.config

        self._lc_lookup_fn = config_get_path(config, 'nodb', 'lc_lookup_fn', 'landSoilLookup.csv')
        self._default_wepp_type = config_get_str(config, 'nodb', 'default_wepp_type', DEFAULT_WEPP_TYPE)
        self._kslast = config_get_float(config, 'nodb', 'kslast')

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
        with open(_join(wd, 'general.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, GeneralMod), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'general.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'general.nodb.lock')

    def on(self, evt):
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
        if evt == TriggerEvents.LANDUSE_BUILD_COMPLETE:
            pass
        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()
            self.modify_soils_kslast()
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
    def kslast(self):
        if not hasattr(self, '_kslast'):
            return None

        return self._kslast

    @kslast.setter
    def kslast(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._kslast = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def modify_soils_kslast(self):
        wd = self.wd
        watershed = Watershed.getInstance(wd)

        kslast = self.kslast

        if kslast is None:
            return

        soils = Soils.getInstance(wd)

        ksat_mod = 'general_kslast'

        _domsoil_d = soils.domsoil_d
        _soils = soils.soils
        for topaz_id, ss in watershed._subs_summary.items():
            # lng, lat = ss.centroid.lnglat

            dom = _domsoil_d[str(topaz_id)]
            _soil = deepcopy(_soils[dom])

            _dom = '{dom}-{ksat_mod}' \
                .format(dom=dom, ksat_mod=ksat_mod)

            _soil.mukey = _dom

            if _dom not in _soils:
                _soil_fn = '{dom}.sol'.format(dom=_dom)
                src_soil_fn = _join(_soil.soils_dir, _soil.fname)
                dst_soil_fn = _join(_soil.soils_dir, _soil_fn)
                modify_kslast(src_soil_fn, dst_soil_fn, kslast)

                _soil.fname = _soil_fn
                _soils[_dom] = _soil

            _domsoil_d[str(topaz_id)] = _dom

        soils.lock()
        soils.domsoil_d = _domsoil_d
        soils.soils = _soils
        soils.dump_and_unlock()

    @property
    def default_wepp_type(self):
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
