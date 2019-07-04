# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import shutil
import jsonpickle

from os.path import join as _join
from os.path import exists as _exists

from enum import IntEnum

from glob import glob
from datetime import datetime

import numpy as np
from osgeo import gdal

from pyproj import Proj, transform

from wepppy.all_your_base import wgs84_proj4, translate_asc_to_tif, read_raster, raster_extent, wmesque_retrieve
from wepppy.landcover import LandcoverMap

from ...ron import Ron
from ...base import NoDbBase, TriggerEvents

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class RangelandCoverNoDbLockedException(Exception):
    pass


class RangelandCoverMode(IntEnum):
    Undefined = -1
    Gridded = 0
    Single = 1


class RangelandCover(NoDbBase):
    __name__ = 'RangelandCover'

    def __init__(self, wd, config):
        super(RangelandCover, self).__init__(wd, config)

        self.lock()

        # noinspection PyBroadException
        try:
            self._mode = RangelandCoverMode.Gridded

            self._bunchgrass_cover_default = 15.0
            self._forbs_cover_default = 5.0
            self._sodgrass_cover_default = 20.0
            self._shrub_cover_default = 30.0

            self._basal_cover_default = 20.0
            self._rock_cover_default = 10.0
            self._litter_cover_default = 25.0
            self._cryptogams_cover_default = 5.0

            self.covers = None

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
        with open(_join(wd, 'rangeland_cover.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, RangelandCover), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'rangeland_cover.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'rangeland_cover.nodb.lock')

    def on(self, evt):
        pass

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            if isinstance(value, RangelandCoverMode):
                self._mode = value

            elif isinstance(value, int):
                self._mode = RangelandCoverMode(value)

            else:
                raise ValueError('most be RangelandCoverMode or int')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def bunchgrass_cover_default(self):
        return self._bunchgrass_cover_default

    @bunchgrass_cover_default.setter
    def bunchgrass_cover_default(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._bunchgrass_cover_default = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def forbs_cover_default(self):
        return self._forbs_cover_default

    @forbs_cover_default.setter
    def forbs_cover_default(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._forbs_cover_default = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def sodgrass_cover_default(self):
        return self._sodgrass_cover_default

    @sodgrass_cover_default.setter
    def sodgrass_cover_default(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._sodgrass_cover_default = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def shrub_cover_default(self):
        return self._shrub_cover_default

    @shrub_cover_default.setter
    def shrub_cover_default(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._shrub_cover_default = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def basal_cover_default(self):
        return self._basal_cover_default

    @basal_cover_default.setter
    def basal_cover_default(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._basal_cover_default = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def rock_cover_default(self):
        return self._rock_cover_default

    @rock_cover_default.setter
    def rock_cover_default(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._rock_cover_default = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def litter_cover_default(self):
        return self._litter_cover_default

    @litter_cover_default.setter
    def litter_cover_default(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._litter_cover_default = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def cryptogams_cover_default(self):
        return self._cryptogams_cover_default

    @cryptogams_cover_default.setter
    def cryptogams_cover_default(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._cryptogams_cover_default = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def parse_inputs(self, kwds):
        self.lock()

        # noinspection PyBroadInspection
        try:
            v = kwds['bunchgrass_cover']
            self._bunchgrass_cover_default = float(v)

            v = kwds['forbs_cover']
            self._forbs_cover_default = float(v)

            v = kwds['sodgrass_cover']
            self._sodgrass_cover_default = float(v)

            v = kwds['shrub_cover']
            self._shrub_cover_default = float(v)

            v = kwds['basal_cover']
            self._basal_cover_default = float(v)

            v = kwds['rock_cover']
            self._rock_cover_default = float(v)

            v = kwds['litter_cover']
            self._litter_cover_default = float(v)

            v = kwds['cryptogams_cover']
            self._cryptogams_cover_default = float(v)

        except Exception:
            self.unlock('-f')
            raise

    def build(self):
        wd = self.wd
        from wepppy.nodb.mods import Shrubland, nlcd_shrubland_layers

        self.lock()
        try:

            shrubland = Shrubland.getInstance(wd)
            shrubland.acquire_rasters()
            shrubland.analyze()

            covers = {}

            for topaz_id, shrubland_data in shrubland:
                if not shrubland_data.isvalid:
                    cover = dict(bunchgrass=self._bunchgrass_cover_default,
                                 forbs=self._forbs_cover_default,
                                 sodgrass=self._sodgrass_cover_default,
                                 shrub=self._shrub_cover_default,
                                 basal=self._basal_cover_default,
                                 rock=self._rock_cover_default,
                                 litter=self._litter_cover_default,
                                 cryptogams=self._cryptogams_cover_default)
                else:
                    print(topaz_id, shrubland_data)
                    herbaceous_normalized = shrubland_data.herbaceous_normalized
                    sagebrush_normalized = shrubland_data.sagebrush_normalized
                    shrub_normalized = shrubland_data.shrub_normalized
                    big_sagebrush_normalized = shrubland_data.big_sagebrush_normalized
                    bare_ground_normalized = shrubland_data.bare_ground_normalized
                    litter_normalized = shrubland_data.litter_normalized

                    bunchgrass = herbaceous_normalized * 0.2
                    sodgrass = herbaceous_normalized * 0.8
                    shrub_cover = sagebrush_normalized + \
                                  shrub_normalized + \
                                  big_sagebrush_normalized
                    basal = shrub_cover + herbaceous_normalized

                    assert basal + \
                           bare_ground_normalized + \
                           litter_normalized <= 100.01, shrubland_data

                    cryptogams = self._cryptogams_cover_default
                    if basal + \
                       bare_ground_normalized + \
                       litter_normalized + \
                       self._cryptogams_cover_default > 100.0:
                        cryptogams = 100.0 - basal - bare_ground_normalized - litter_normalized

                    rock = 100.0 - \
                           basal - \
                           bare_ground_normalized - \
                           litter_normalized - \
                           cryptogams

                    cover = dict(bunchgrass=bunchgrass,
                                 forbs=shrubland_data.annual_herb,
                                 sodgrass=sodgrass,
                                 shrub=shrub_cover,
                                 basal=basal,
                                 rock=rock,
                                 litter=shrubland_data.litter,
                                 cryptogams=self._cryptogams_cover_default)

                covers[topaz_id] = cover

            self.covers = covers
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
