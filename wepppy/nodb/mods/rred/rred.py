# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import ast
import shutil
from collections import Counter
import jsonpickle

from subprocess import Popen, PIPE
from os.path import join as _join
from os.path import exists as _exists

from glob import glob
from datetime import datetime

import numpy as np
from osgeo import gdal

from pyproj import Proj, transform

from wepppy.all_your_base import wgs84_proj4, isint, read_arc, translate_asc_to_tif, read_raster, raster_extent
from wepppy.landcover import LandcoverMap
from wepppy.nodb.mods.rred.rred_api import retrieve_rred
from wepppy.ssurgo import SoilSummary

from ...landuse import Landuse, LanduseMode
from ...soils import Soils, SoilsMode
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...base import NoDbBase, TriggerEvents


gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class RredNoDbLockedException(Exception):
    pass


class Rred(NoDbBase):
    __name__ = 'Rred'

    def __init__(self, wd, config):
        super(Rred, self).__init__(wd, config)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.rred_dir)
            self.rred_key = None
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
        with open(_join(wd, 'rred.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Rred), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'rred.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'rred.nodb.lock')

    @property
    def rred_dir(self):
        return _join(self.wd, 'rred')

    def import_project(self, rred_key):

        self.lock()

        # noinspection PyBroadException
        try:
            retrieve_rred(rred_key, self.rred_dir)
            self.rred_key = rred_key

            assert _exists(_join(self.rred_dir, 'dem.asc'))
            assert _exists(_join(self.rred_dir, 'dem.prj'))
            translate_asc_to_tif(_join(self.rred_dir, 'dem.asc'), self.dem_fn)

            data, _transform, proj = read_raster(self.dem_fn, dtype=np.uint8)
            utm_extent = raster_extent(self.dem_fn)

            assert 'utm' in proj
            utm_proj = Proj(proj)
            wgs_proj = Proj(wgs84_proj4)

            wgs_lr = transform(utm_proj, wgs_proj, utm_extent[0], utm_extent[1])
            wgs_ul = transform(utm_proj, wgs_proj, utm_extent[2], utm_extent[3])
            wgs_extent = [wgs_lr[0], wgs_lr[1], wgs_ul[0], wgs_ul[1]]
            wgs_center = (wgs_lr[0] + wgs_ul[0]) / 2.0, (wgs_lr[1] + wgs_ul[1]) / 2.0

            ron = Ron.getInstance(self.wd)
            ron.set_map(wgs_extent, wgs_center, 11)

            print(_transform)
            print(proj)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def build_landuse(self, landuse_mode):
        assert landuse_mode in [LanduseMode.RRED_Burned, LanduseMode.RRED_Unburned]

        landuse = Landuse.getInstance(self.wd)
        landuse.clean()

        # create LandcoverMap instance
        if landuse_mode == LanduseMode.RRED_Unburned:
            lc = LandcoverMap(_join(self.rred_dir, 'landcov_unburned.asc'))
        else:
            lc = LandcoverMap(_join(self.rred_dir, 'landcov_burned.asc'))

        landuse.lock()

        # noinspection PyBroadException
        try:
            landuse.domlc_d = lc.build_lcgrid(self.subwta_arc, None)
            landuse.dump_and_unlock()
        except Exception:
            landuse.unlock('-f')
            raise

    def copy_soils(self):
        soil_fns = glob(_join(self.rred_dir, '*', '*.sol'))
        for fn in soil_fns:
            shutil.copy(fn, self.soils_dir)

    def build_soils(self, soils_mode):
        assert soils_mode in [SoilsMode.RRED_Burned, SoilsMode.RRED_Unburned]

        soils = Soils.getInstance(self.wd)
        soils.clean()
        self.copy_soils()

        soilsmap_fn = _join(self.rred_dir, 'soilsmap.txt')

        assert _exists(soilsmap_fn)
        soilsmap = {}
        with open(soilsmap_fn) as fp:
            for line in fp.readlines():
                line = line.strip().split(',')
                if len(line) == 3:
                    soilsmap[line[0]] = line[2]

        # create LandcoverMap instance
        if soils_mode == SoilsMode.RRED_Unburned:
            lc = LandcoverMap(_join(self.rred_dir, 'soil_unburned.asc'))
        else:
            lc = LandcoverMap(_join(self.rred_dir, 'soil_burned.asc'))

        soils.lock()

        # noinspection PyBroadException
        try:
            domsoil_d = lc.build_lcgrid(self.subwta_arc, None)
            soils_summaries = {}
            for k, v in domsoil_d.items():
                sol = soilsmap[str(v)]
                domsoil_d[k] = sol
                soils_summaries[sol] = SoilSummary(
                    Mukey=sol,
                    FileName='%s.sol' % sol,
                    soils_dir=self.soils_dir,
                    BuildDate=str(datetime.now()),
                    Description='%s - RRED' % v
                )

            soils.domsoil_d = domsoil_d
            soils.soils = soils_summaries
            soils.dump_and_unlock()
        except Exception:
            soils.unlock('-f')
            raise

    def on(self, evt):
        pass
