# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard libraries
import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir

import shutil


# non-standard
import jsonpickle
import utm
import what3words
import requests

# wepppy
import wepppy
from wepppy.all_your_base import (
    wmesque_retrieve,
    haversine
)

# wepppy submodules
from .base import NoDbBase, TriggerEvents, DEFAULT_DEM_DB


_thisdir = os.path.dirname(__file__)


class Map(object):
    def __init__(self, extent, center, zoom, cellsize=30.0):
        assert len(extent) == 4

        _extent = [float(v) for v in extent]
        l, b, r, t = _extent
        assert l < r
        assert b < t

        self.extent = [float(v) for v in _extent]
        self.center = [float(v) for v in center]
        self.zoom = int(zoom)
        self.cellsize = cellsize

        # e.g. (395201.3103811303, 5673135.241182375, 32, 'U')
        self.utm = utm.from_latlon(t, l)

        self.utmzone = self.utm[2]

    @property
    def ul(self):
        return self.extent[0], self.extent[3]

    @property
    def shape(self):
        l, b, r, t = self.extent
        px_w = int(haversine((l, b), (l, t)) * 1000 / self.cellsize)
        px_h = int(haversine((l, b), (r, b)) * 1000 / self.cellsize)
        return px_w, px_h

    @property
    def bounds_str(self):
        """
        returns extent formatted leaflet
        """
        l, b, r, t = self.extent
        sw = [b, l]
        ne = [t, r]
        return str([sw, ne])


class RonNoDbLockedException(Exception):
    pass


class Ron(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Ron'

    def __init__(self, wd, cfg_fn="0.cfg"):
        super(Ron, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            config = self.config
            self._configname = config.get('general', 'name')
            self._cellsize = float(config.get('general', 'cellsize'))
            self._center0 = config.get('map', 'center0')
            self._zoom0 = config.get('map', 'zoom0')

            _boundary = config.get('map', 'boundary')
            if _boundary is not None:
                _boundary = _boundary

            self._boundary = _boundary
            self._dem_db = config.get('general', 'dem_db')

            self._enable_landuse_change = config.getboolean('landuse', 'enable_landuse_change')

            self._name = ''
            self._map = None
            self._w3w = None

            dem_dir = self.dem_dir
            if not _exists(dem_dir):
                os.mkdir(dem_dir)

            export_dir = self.export_dir
            if not _exists(export_dir):
                os.mkdir(export_dir)

            # initialize the other controllers here
            # this will create the other .nodb files

            # gotcha: need to import the nodb submodules
            # through wepppy to avoid circular references
            wepppy.nodb.Topaz(wd, cfg_fn)
            wepppy.nodb.Watershed(wd, cfg_fn)
            wepppy.nodb.Landuse(wd, cfg_fn)
            wepppy.nodb.Soils(wd, cfg_fn)
            wepppy.nodb.Climate(wd, cfg_fn)
            wepppy.nodb.Wepp(wd, cfg_fn)
            wepppy.nodb.Unitizer(wd, cfg_fn)
            wepppy.nodb.WeppPost(wd, cfg_fn)
            wepppy.nodb.Observed(wd, cfg_fn)

            if "lt" in self.mods:
                wepppy.nodb.mods.LakeTahoe(wd, cfg_fn)

            if "portland" in self.mods:
                wepppy.nodb.mods.Portland(wd, cfg_fn)

            if "baer" in self.mods:
                wepppy.nodb.mods.Baer(wd, cfg_fn)
                sbs_map = config.get('landuse', 'sbs_map')

                if sbs_map == '':
                    sbs_map = None

                if sbs_map is not None:
                    from wepppy.nodb.mods import MODS_DIR
                    sbs_map = sbs_map.replace('MODS_DIR', MODS_DIR)

                    # sbs_map = _join(_thisdir, sbs_map)
                    assert _exists(sbs_map), (sbs_map, os.path.abspath(sbs_map))
                    assert not isdir(sbs_map)
                    baer = wepppy.nodb.mods.Baer.getInstance(wd)

                    sbs_path = _join(baer.baer_dir, 'sbs.tif')
                    shutil.copyfile(sbs_map, sbs_path)

                    baer.validate(_split(sbs_path)[-1])

                    baer.modify_burn_class([0, 1, 2, 3], None)

            if 'rred' in self.mods:
                wepppy.nodb.mods.Rred(wd, cfg_fn)

            if 'debris_flow' in self.mods:
                wepppy.nodb.mods.DebrisFlow(wd, cfg_fn)

            if 'ash' in self.mods:
                wepppy.nodb.mods.Ash(wd, cfg_fn)
                wepppy.nodb.mods.AshPost(wd, cfg_fn)

            if 'shrubland' in self.mods:
                wepppy.nodb.mods.Shrubland(wd, cfg_fn)

            if 'rangeland_cover' in self.mods:
                wepppy.nodb.mods.RangelandCover(wd, cfg_fn)

            if 'rhem' in self.mods:
                wepppy.nodb.mods.Rhem(wd, cfg_fn)
                wepppy.nodb.mods.RhemPost(wd, cfg_fn)

            self.dump_and_unlock()

            self.trigger(TriggerEvents.ON_INIT_FINISH)

        except Exception:
            self.unlock('-f')
            raise
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'ron.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Ron), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'ron.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'ron.nodb.lock')

    @property
    def configname(self) -> str:
        return self._configname

    @property
    def enable_landuse_change(self) -> bool:
        return self._enable_landuse_change

    #
    # map
    #
    @property
    def center0(self):
        if self.map is None:
            return self._center0
        else:
            return self.map.center[::-1]

    @property
    def zoom0(self):
        if self.map is None:
            return self._zoom0
        else:
            return self.map.zoom

    @property
    def cellsize(self):
        return self._cellsize

    @property
    def boundary(self):
        return self._boundary

    @property
    def map(self):
        return self._map

    def set_map(self, extent, center, zoom):
        self.lock()

        # noinspection PyBroadException
        try:
            self._map = Map(extent, center, zoom, self.cellsize)

            config = self.config
            w3w_api_key = config.get('general', 'w3w_api_key')

            lng, lat = self.map.center
            w3w_geocoder = what3words.Geocoder(w3w_api_key)
            try:
                self._w3w = w3w_geocoder.reverse(lat=lat, lng=lng)
            except:
                coord = what3words.Coordinates(lat=lat, lng=lng)
                self._w3w = w3w_geocoder.convert_to_3wa(coord)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def w3w(self):
        if self._w3w is None:
            return ''

        return self._w3w.get('words', '')

    @property
    def extent(self):
        if self.map is None:
            return None

        return self.map.extent

    #
    # name
    #
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._name = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def has_ash_results(self):
        if 'ash' not in self.mods:
            return False

        from wepppy.nodb.mods import Ash
        ash = Ash.getInstance(self.wd)
        return ash.has_ash_results

    @property
    def has_sbs(self):
        if "baer" not in self.mods:
            return False

        from wepppy.nodb.mods import Baer
        baer = Baer.getInstance(self.wd)
        return baer.has_map


    @property
    def dem_db(self):
        if not hasattr(self, "_dem_db"):
            return DEFAULT_DEM_DB

        return self._dem_db

    @dem_db.setter
    def dem_db(self, value):
        return

        self.lock()

        # noinspection PyBroadException
        try:
            self._dem_db = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # dem
    #
    def fetch_dem(self):
        assert self.map is not None
        wmesque_retrieve(self.dem_db, self.map.extent,
                         self.dem_fn, self.map.cellsize)

        assert _exists(self.dem_fn)

    @property
    def has_dem(self):
        return _exists(self.dem_fn)

    #
    # summary
    #
    def subs_summary(self):
        wd = self.wd
        watershed = wepppy.nodb.Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        soils = wepppy.nodb.Soils.getInstance(wd)
        climate = wepppy.nodb.Climate.getInstance(wd)
        landuse = wepppy.nodb.Landuse.getInstance(wd)

        summaries = []
        for wepp_id in translator.iter_wepp_sub_ids():
            topaz_id = translator.top(wepp=wepp_id)

            summaries.append(
                dict(meta=dict(hill_type='Hillslope',
                               topaz_id=topaz_id,
                               wepp_id=wepp_id),
                     watershed=watershed.sub_summary(topaz_id),
                     soil=soils.sub_summary(topaz_id),
                     climate=climate.sub_summary(topaz_id),
                     landuse=landuse.sub_summary(topaz_id)))

        return summaries

    def sub_summary(self, topaz_id=None, wepp_id=None):
        wd = self.wd
        watershed = wepppy.nodb.Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        soils = wepppy.nodb.Soils.getInstance(wd)
        climate = wepppy.nodb.Climate.getInstance(wd)
        landuse = wepppy.nodb.Landuse.getInstance(wd)

        if topaz_id is None:
            topaz_id = translator.top(wepp=wepp_id)

        if wepp_id is None:
            wepp_id = translator.wepp(top=topaz_id)

        return dict(
            meta=dict(hill_type='Hillslope', topaz_id=topaz_id,
                      wepp_id=wepp_id),
            watershed=watershed.sub_summary(topaz_id),
            soil=soils.sub_summary(topaz_id),
            climate=climate.sub_summary(topaz_id),
            landuse=landuse.sub_summary(topaz_id)
        )

    def chns_summary(self):
        wd = self.wd
        watershed = wepppy.nodb.Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        soils = wepppy.nodb.Soils.getInstance(wd)
        climate = wepppy.nodb.Climate.getInstance(wd)
        landuse = wepppy.nodb.Landuse.getInstance(wd)

        summaries = []
        for wepp_id in translator.iter_wepp_chn_ids():
            topaz_id = translator.top(wepp=wepp_id)
            chn_enum = translator.chn_enum(top=topaz_id)

            summaries.append(
                dict(meta=dict(hill_type='Channel',
                               topaz_id=topaz_id,
                               wepp_id=wepp_id,
                               chn_enum=chn_enum),
                     watershed=watershed.chn_summary(topaz_id),
                     soil=soils.chn_summary(topaz_id),
                     climate=climate.chn_summary(topaz_id),
                     landuse=landuse.chn_summary(topaz_id)))

        return summaries

    def chn_summary(self, topaz_id=None, wepp_id=None):
        wd = self.wd
        watershed = wepppy.nodb.Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        soils = wepppy.nodb.Soils.getInstance(wd)
        climate = wepppy.nodb.Climate.getInstance(wd)
        landuse = wepppy.nodb.Landuse.getInstance(wd)

        if topaz_id is None:
            topaz_id = translator.top(wepp=wepp_id)

        if wepp_id is None:
            wepp_id = translator.wepp(top=topaz_id)

        chn_enum = translator.chn_enum(top=topaz_id)

        return dict(
            meta=dict(hill_type='Channel', topaz_id=topaz_id,
                      wepp_id=wepp_id, chn_enum=chn_enum),
            watershed=watershed.chn_summary(topaz_id),
            soil=soils.chn_summary(topaz_id),
            climate=climate.chn_summary(topaz_id),
            landuse=landuse.chn_summary(topaz_id)
        )
