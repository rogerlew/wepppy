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
from typing import Union

from copy import deepcopy

import jsonpickle

from .....all_your_base import RasterDatasetInterpolator, isfloat, RDIOutOfBoundsException
from ....base import NoDbBase, TriggerEvents

from ..location_mixin import LocationMixin

from ....climate import Climate, ClimateMode, ClimateSpatialMode
from ....soils import Soils
from ....watershed import Watershed
from ....wepp import Wepp
from .....wepp.soils.utils import modify_ksat


_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir)


class SeattleModNoDbLockedException(Exception):
    pass


DEFAULT_WEPP_TYPE = 'Volcanic'
PMET__MID_SEASON_CROP_COEFF__DEFAULT = 0.95
CRITICAL_SHEAR_DEFAULT = 120.0
KSAT_DEFAULT = 0.05


class SeattleMod(NoDbBase, LocationMixin):
    __name__ = 'SeattleMod'

    def __init__(self, wd, cfg_fn):
        super(SeattleMod, self).__init__(wd, cfg_fn)

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
        with open(_join(wd, 'seattle.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, SeattleMod), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'seattle.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'seattle.nodb.lock')

    def on(self, evt):
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
        if evt == TriggerEvents.LANDUSE_BUILD_COMPLETE:
            pass
        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()
            self.modify_soils_ksat()
        # elif evt == TriggerEvents.PREPPING_PHOSPHORUS:
        #     self.determine_phosphorus()

        elif evt == TriggerEvents.WEPP_PREP_WATERSHED_COMPLETE:
            self.modify_erod_cs()
            self.modify_pmet()

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

    def modify_soils_ksat(self):
        wd = self.wd
        watershed = Watershed.getInstance(wd)


        lng, lat = watershed.centroid
        rdi = RasterDatasetInterpolator(_join(_data_dir, 'ksat.tif'))
        try:
            ksat = rdi.get_location_info(lng, lat)
        except RDIOutOfBoundsException:
            ksat = KSAT_DEFAULT

        if not isfloat(ksat):
            ksat = KSAT_DEFAULT
        else:
            if ksat < KSAT_DEFAULT:
                ksat = KSAT_DEFAULT

        soils = Soils.getInstance(wd)

        ksat_mod = 'f'

        _domsoil_d = soils.domsoil_d
        _soils = soils.soils
        for topaz_id, ss in watershed._subs_summary.items():
            lng, lat = ss.centroid.lnglat

            dom = _domsoil_d[str(topaz_id)]
            _soil = deepcopy(_soils[dom])

            _dom = '{dom}-{ksat_mod}' \
                .format(dom=dom, ksat_mod=ksat_mod)

            _soil.mukey = _dom

            if _dom not in _soils:
                _soil_fn = '{dom}.sol'.format(dom=_dom)
                src_soil_fn = _join(_soil.soils_dir, _soil.fname)
                dst_soil_fn = _join(_soil.soils_dir, _soil_fn)
                modify_ksat(src_soil_fn, dst_soil_fn, ksat)

                _soil.fname = _soil_fn
                _soils[_dom] = _soil

            _domsoil_d[str(topaz_id)] = _dom

        soils.lock()
        soils.domsoil_d = _domsoil_d
        soils.soils = _soils
        soils.dump_and_unlock()

    def modify_erod_cs(self):
        wd = self.wd
        wepp = Wepp.getInstance(wd)

        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()

        lng, lat = watershed.centroid
        rdi = RasterDatasetInterpolator(_join(_data_dir, 'critical_shear.tif'))

        try:
            critical_shear = rdi.get_location_info(lng, lat)
        except RDIOutOfBoundsException:
            critical_shear = CRITICAL_SHEAR_DEFAULT

        if not isfloat(critical_shear):
            critical_shear = CRITICAL_SHEAR_DEFAULT
        else:
            if critical_shear < 0.0 or critical_shear >= 255.0:
                critical_shear = CRITICAL_SHEAR_DEFAULT

        wepp._prep_channel_chn(translator, 0.000001, critical_shear)
        wepp._prep_impoundment()
        wepp._prep_channel_soils(translator, 0.000001, critical_shear)

    def modify_pmet(self):
        wd = self.wd
        wepp = Wepp.getInstance(wd)

        watershed = Watershed.getInstance(wd)

        lng, lat = watershed.centroid

        rdi = RasterDatasetInterpolator(_join(_data_dir, 'pmet__mid_season_crop_coeff.tif'))
        try:
            mid_season_crop_coeff = rdi.get_location_info(lng, lat)
        except RDIOutOfBoundsException:
            mid_season_crop_coeff = PMET__MID_SEASON_CROP_COEFF__DEFAULT

        if not isfloat(mid_season_crop_coeff):
            mid_season_crop_coeff = PMET__MID_SEASON_CROP_COEFF__DEFAULT
        else:
            if mid_season_crop_coeff < 0.0:
                mid_season_crop_coeff = PMET__MID_SEASON_CROP_COEFF__DEFAULT

        p_coeff = 0.75
        wepp._prep_pmet(mid_season_crop_coeff=mid_season_crop_coeff, p_coeff=p_coeff)
