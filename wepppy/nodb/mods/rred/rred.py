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

from glob import glob
from datetime import datetime

import numpy as np
from osgeo import gdal

from wepppy.all_your_base import wgs84_proj4, translate_asc_to_tif, read_raster, raster_extent, GeoTransformer
from wepppy.landcover import LandcoverMap
from wepppy.nodb.mods.rred import rred_api
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import YamlSoil

from ...landuse import Landuse, LanduseMode
from ...soils import Soils, SoilsMode
from ...watershed import Watershed
from ...base import NoDbBase

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
            self.wgs_extent = None
            self.wgs_center = None

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

    def request_project(self, sbs_4class_fn, srid):
        assert _exists(sbs_4class_fn)
        rred_proj = rred_api.send_request(sbs_4class_fn, srid)
        rred_key = rred_proj['key']
        self.import_project(rred_key)

    def import_project(self, rred_key):

        self.lock()

        # noinspection PyBroadException
        try:
            rred_api.retrieve_rred(rred_key, self.rred_dir)
            self.rred_key = rred_key

            assert _exists(_join(self.rred_dir, 'dem.asc'))
            assert _exists(_join(self.rred_dir, 'dem.prj'))
            translate_asc_to_tif(_join(self.rred_dir, 'dem.asc'), self.dem_fn)

            data, _transform, proj = read_raster(self.dem_fn, dtype=np.uint8)
            utm_extent = raster_extent(self.dem_fn)

            assert 'utm' in proj
            self.utm_proj = proj

            utm2wgs_transformer = GeoTransformer(proj, dst_proj4=wgs84_proj4)
            wgs_lr = utm2wgs_transformer.transform(utm_extent[0], utm_extent[1])
            wgs_ul = utm2wgs_transformer.transform(utm_extent[2], utm_extent[3])
            self.wgs_extent = [wgs_lr[0], wgs_lr[1], wgs_ul[0], wgs_ul[1]]
            self.wgs_center = (wgs_lr[0] + wgs_ul[0]) / 2.0, (wgs_lr[1] + wgs_ul[1]) / 2.0

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def build_landuse(self, landuse_mode=LanduseMode.RRED_Burned):
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
            landuse._mode = landuse_mode
            landuse.domlc_d = lc.build_lcgrid(self.subwta_arc, None)
            landuse.dump_and_unlock()
        except Exception:
            landuse.unlock('-f')
            raise

    def copy_soils(self):
        soil_fns = glob(_join(self.rred_dir, '*', '*.sol'))
        for fn in soil_fns:
            shutil.copy(fn, self.soils_dir)

    def build_soils(self, soils_mode=SoilsMode.RRED_Burned):
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
            _domsoil_d = lc.build_lcgrid(self.subwta_arc, None)
            _soils = {}
            for k, v in _domsoil_d.items():
                sol = soilsmap[str(v)]
                _domsoil_d[k] = sol

                soil_fn = '%s.sol' % sol
                soil_path = _join(self.soils_dir, soil_fn)

                yaml_soil = YamlSoil(soil_path)
                desc = '{slid} - {texid}'.format(**yaml_soil.obj['ofes'][0])

                _soils[sol] = SoilSummary(
                    Mukey=sol,
                    FileName=soil_fn,
                    soils_dir=self.soils_dir,
                    BuildDate=str(datetime.now()),
                    Description=desc
                )

            # need to recalculate the pct_coverages
            total_area = 0.0
            for k in _soils:
                _soils[k].area = 0.0

            watershed = Watershed.getInstance(self.wd)
            total_area += watershed.totalarea
            for topaz_id, k in _domsoil_d.items():
                _soils[k].area += watershed.area_of(topaz_id)

            for k in _soils:
                coverage = 100.0 * _soils[k].area / total_area
                _soils[k].pct_coverage = coverage

            soils._mode = soils_mode
            soils.domsoil_d = _domsoil_d
            soils.soils = _soils
            soils.dump_and_unlock()
        except Exception:
            soils.unlock('-f')
            raise

    def on(self, evt):
        pass
