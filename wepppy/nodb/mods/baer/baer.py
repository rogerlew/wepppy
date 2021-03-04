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
from copy import deepcopy

from subprocess import Popen, PIPE
from os.path import join as _join
from os.path import exists as _exists

import numpy as np
from osgeo import gdal

from wepppy.all_your_base import isint
from wepppy.all_your_base.geo import wgs84_proj4, read_raster, haversine
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import SoilReplacements, simple_texture, YamlSoil

from ...landuse import Landuse, LanduseMode
from ...soils import Soils, SoilsMode
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...mods.rred import Rred
from ...base import NoDbBase, TriggerEvents

from .sbs_map import SoilBurnSeverityMap

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class BaerNoDbLockedException(Exception):
    pass


# Replaceable parameters:
# Albedo, iniSatLev, interErod, rillErod, critSh, effHC, soilDepth, Sand, Clay, OM, CEC
sbs_soil_replacements = dict(
    low=SoilReplacements(interErod='*0.8', rillErod='*0.8', effHC='*0.8'),
    moderate=SoilReplacements(interErod='*0.6', rillErod='*0.6', effHC='*0.6'),
    high=SoilReplacements(interErod='*0.4', rillErod='*0.4', effHC='*0.4'))


class Baer(NoDbBase):
    __name__ = 'Baer'

    def __init__(self, wd, cfg_fn):
        super(Baer, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.baer_dir)

            self._baer_fn = None
            self._bounds = None
            self._classes = None
            self._breaks = None
            self._counts = None
            self._nodata_vals = None
            self._is256 = None

            self._legacy_mode = self.config_get_bool('baer', 'legacy_mode')

            self.sbs_coverage = None

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
        with open(_join(wd, 'baer.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Baer), db

            if _exists(_join(wd, 'READONLY')):
                db.wd = os.path.abspath(wd)
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'baer.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'baer.nodb.lock')

    @property
    def legacy_mode(self):
        return getattr(self, '_legacy_mode', False)

    @property
    def baer_dir(self):
        return _join(self.wd, 'baer')

    @property
    def baer_soils_dir(self):
        return _join(_data_dir, 'soils')

    @property
    def baer_fn(self):
        return self._baer_fn

    @property
    def has_map(self):
        return self._baer_fn is not None

    @property
    def is256(self):
        return self._is256 is not None

    @property
    def color_tbl_path(self):
        return _join(self.baer_dir, 'color_table.txt')

    @property
    def bounds(self):
        return self._bounds

    @property
    def classes(self):
        return self._classes

    @property
    def breaks(self):
        return self._breaks

    @property
    def nodata_vals(self):
        if self._nodata_vals is None:
            return ''

        return ', '.join(str(v) for v in self._nodata_vals)

    def classify(self, v):

        if self._nodata_vals is not None:
            if v in self._nodata_vals:
                return 'No Data'

        i = 0
        for i, brk in enumerate(self.breaks):
            if v <= brk:
                break

        return ('No Burn',
                'Low Severity Burn',
                'Moderate Severity Burn',
                'High Severity Burn')[i]

    @property
    def baer_path(self):
        if self._baer_fn is None:
            return None

        return _join(self.baer_dir, self._baer_fn)

    @property
    def baer_wgs(self):
        baer_path = self.baer_path
        return baer_path[:-4] + '.wgs' + baer_path[-4:]

    @property
    def baer_rgb(self):
        return self.baer_wgs[:-4] + '.rgb.vrt'

    @property
    def baer_rgb_png(self):
        return _join(self.baer_dir, 'baer.wgs.rgba.png')

    @property
    def baer_cropped(self):
        return _join(self.baer_dir, 'baer.cropped.tif')

    @property
    def legend(self):
        keys = [130, 131, 132, 133]

        descs = ['No Burn',
                'Low Severity Burn',
                'Moderate Severity Burn',
                'High Severity Burn']

        colors = ['#00734A', '#4DE600', '#FFFF00', '#FF0000']

        return list(zip(keys, descs, colors))

    def write_color_table(self):
        breaks = self.breaks
        assert len(breaks) == 4

        _map = dict([('No Data', '0 0 0'),
                     ('No Burn', '0 115 74'),
                     ('Low Severity Burn', '77 230 0'),
                     ('Moderate Severity Burn', '255 255 0'),
                     ('High Severity Burn', '255 0 0')])

        with open(self.color_tbl_path, 'w') as fp:
            for v, k, c in self.class_map:
                fp.write('{} {}\n'.format(v, _map[k]))

            fp.write("nv 0 0 0\n")

    def build_color_map(self):
        baer_rgb = self.baer_rgb
        if _exists(baer_rgb):
            os.remove(baer_rgb)

        cmd = ['gdaldem', 'color-relief', '-of', 'VRT',  self.baer_wgs, self.color_tbl_path, baer_rgb]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        baer_rgb_png = self.baer_rgb_png
        if _exists(baer_rgb_png):
            os.remove(baer_rgb_png)

        cmd = ['gdal_translate', '-of', 'PNG', baer_rgb, baer_rgb_png]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

     @property
     def sbs_wgs_n(self):
         """
         number of pixels in the WGS projected SBS
         """
         return sum(self._counts.values())

     @property
     def sbs_wgs_area_ha(self):
         """
         area of the WGS projected SBS in ha
         """
         [[sw_y, sw_x], [ne_y, ne_x]] = self.bounds
         nw_y, nw_x = ne_y, sw_x

         width = haversine((nw_x, nw_y), (ne_x, ne_y)) * 1000
         height = haversine((nw_x, nw_y), (sw_x, sw_y)) * 1000
         return width * height * 0.0001

     @property
     def sbs_class_counts(self):
         """
         dictionary with burn class keys and pixel counts of the WGS projected SBS
         """
         counts = Counter()
         for v in self.classes:
             counts[self.classify(v)] += self._counts[str(v)]

         return counts

     @property
     def sbs_class_pcts(self):
         """
         dictionary with burn class keys percentages of cover of the WGS projected SBS
         """
         counts = self.sbs_class_counts
         pcts = {}
         tot_px = counts['Low Severity Burn'] + counts['Moderate Severity Burn'] + counts['High Severity Burn']
         for k in counts:
             pcts[k] = 100.0 * counts[k] / tot_px

         return pcts

     @property
     def sbs_class_areas(self):
         """
         dictionary with burn class keys and areas (ha) of the WGS projected SBS
         """
         ha__px = self.sbs_wgs_area_ha / self.sbs_wgs_n
         counts = self.sbs_class_counts
         areas = {}
         tot_px = sum(counts.values()) # total count of non-nodata pixels 
         for k in counts:
             areas[k] = counts[k] * ha__px 

         return areas

    @property
    def class_map(self):
        return [(v, self.classify(v), self._counts[str(v)]) for v in self.classes]

    def modify_burn_class(self, breaks, nodata_vals):
        self.lock()

        # noinspection PyBroadException
        try:
            assert len(breaks) == 4
            assert breaks[0] <= breaks[1]
            assert breaks[1] <= breaks[2]
            assert breaks[2] <= breaks[3]

            self._breaks = breaks
            if nodata_vals is not None:
                if str(nodata_vals).strip() != '':
                    _nodata_vals = ast.literal_eval('[{}]'.format(nodata_vals))
                    assert all(isint(v) for v in _nodata_vals)
                    self._nodata_vals = _nodata_vals

            self.write_color_table()
            self.build_color_map()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def remove_sbs(self):
        self.lock()

        # noinspection PyBroadException
        try:
            if _exists(self._baer_fn):
                os.remove(self._baer_fn)

            self._baer_fn = None
            self._nodata_vals = None
            self._bounds = None
            self._is256 = None
            self._classes = None
            self._counts = None
            self._breaks = None

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def validate(self, fn):
        self.lock()

        # noinspection PyBroadException
        try:
            self._baer_fn = fn
            self._nodata_vals = None

            baer_path = self.baer_path
            assert _exists(baer_path), baer_path

            ds = gdal.Open(baer_path)
            assert ds is not None
            del ds

            # transform to WGS1984 to display on map
            baer_wgs = self.baer_wgs
            if _exists(baer_wgs):
                os.remove(baer_wgs)

            cmd = ['gdalwarp', '-t_srs', wgs84_proj4,
                   '-r', 'near', baer_path, baer_wgs]
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            p.wait()

            assert _exists(baer_wgs), ' '.join(cmd)

            ds = gdal.Open(baer_wgs)
            assert ds is not None

            transform = ds.GetGeoTransform()
            band = ds.GetRasterBand(1)
            data = np.array(band.ReadAsArray(), dtype=np.int)

            nodata = band.GetNoDataValue()
            if nodata is not None:
                self._nodata_vals = [np.int(nodata)]

            del ds

            # need the bounds for Leaflet
            sw_x = transform[0]
            sw_y = transform[3] + transform[5] * data.shape[0]

            ne_x = transform[0] + transform[1] * data.shape[1]
            ne_y = transform[3]

            self._bounds = [[sw_y, sw_x], [ne_y, ne_x]]

            # build rgba for interface

            # determine classes
            classes = list(set(data.flatten()))
            classes = [int(v) for v in classes]
            if self._nodata_vals is not None:
                classes = [v for v in classes if v not in self._nodata_vals]

            counts = Counter(data.flatten())

            is256 = len(classes) > 6 or max(classes) >= 255

            if is256:
                breaks = [75, 109, 187, 65535]
            else:
                breaks = [1, 2, 3, 65535]

            self._is256 = is256
            self._classes = classes
            self._counts = {str(k): v for k, v in counts.items()}
            self._breaks = breaks

            self.write_color_table()
            self.build_color_map()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def on(self, evt):
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
            if 'rred' in self.mods:
                baer_cropped = self.baer_cropped
                sbs = SoilBurnSeverityMap(baer_cropped, self.breaks, self._nodata_vals)

                baer_4class = baer_cropped.replace('.tif', '.4class.tif')
                sbs.export_4class_map(baer_4class)

                srid = Ron.getInstance(self.wd).map.srid

                rred = Rred.getInstance(self.wd)
                rred.request_project(baer_4class, srid=srid)
                rred.build_landuse()

        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            if 'rred' in self.mods:
                rred = Rred.getInstance(self.wd)
                rred.build_soils()
            elif self._config == 'eu-fire2.cfg':
                self._assign_eu_soils()
            elif self._config == 'au-fire.cfg' or self._config == 'au-fire60.cfg':
                self._assign_au_soils()
            else:
                self.modify_soils()

    def remap_landuse(self):
        wd = self.wd
        baer_path = self.baer_path

        watershed = Watershed.getInstance(wd)

        baer_cropped = self.baer_cropped
        if _exists(baer_cropped):
            os.remove(baer_cropped)

        map = Ron.getInstance(wd).map
        xmin, ymin, xmax, ymax = [str(v) for v in map.utm_extent]
        cellsize = str(map.cellsize)

        cmd = ['gdalwarp', '-t_srs',  'epsg:%s' % map.srid,
               '-tr', cellsize, cellsize,
               '-te', xmin, ymin, xmax, ymax,
               '-r', 'near', baer_path, baer_cropped]

        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(baer_cropped), ' '.join(cmd)

        landuse = Landuse.getInstance(wd)
        landuse.lock()

        # noinspection PyBroadException
        try:
            sbs = SoilBurnSeverityMap(baer_cropped, self.breaks, self._nodata_vals)
            self._calc_sbs_coverage(sbs.data)

            if landuse.mode != LanduseMode.Single:
                domlc_d = sbs.build_lcgrid(watershed.subwta, None)

                ron = Ron.getInstance(wd)
                if 'lt' in ron.mods or 'portland' in ron.mods or 'seattle' in ron.mods or 'general' in ron.mods:
                    for k, sbs in domlc_d.items():
                        # lt shrub
                        if landuse.domlc_d[k] == '104':
                            if sbs in ['131']:
                                landuse.domlc_d[k] = '121'  # lt low shrub
                            elif sbs in ['132']:
                                landuse.domlc_d[k] = '120'  # lt medium shrub
                            elif sbs in ['133']:
                                landuse.domlc_d[k] = '119'  # lt high shrub
                        # not shrub
                        else:
                            if sbs in ['131']:
                                landuse.domlc_d[k] = '106'  # lt low forest
                            elif sbs in ['132']:
                                landuse.domlc_d[k] = '118'  # lt medium forest
                            elif sbs in ['133']:
                                landuse.domlc_d[k] = '105'  # lt high forest

                else:
                    # TODO: implement shrub wepp-pep managements
                    landuse.domlc_d = domlc_d

            landuse.dump_and_unlock()
            landuse = landuse.getInstance(wd)
            landuse.build_managements(_map='default')

        except Exception:
            landuse.unlock('-f')
            raise

    def _assign_eu_soils(self):

        wd = self.wd

        ron = Ron.getInstance(wd)
        soils = Soils.getInstance(wd)
        landuse = Landuse.getInstance(wd)

        # noinspection PyBroadExpection
        try:
            soils.lock()

            _domsoil_d = deepcopy(soils.domsoil_d)
            _soils = deepcopy(soils.soils)

            domlc_d = landuse.domlc_d

            for topaz_id, mukey in soils.domsoil_d.items():
                dom = domlc_d[topaz_id]

                if dom in ['131', '132']:
                    _domsoil_d[topaz_id] = '{}_lowmod_sev'.format(_domsoil_d[topaz_id])
                elif dom in ['133']:
                    _domsoil_d[topaz_id] = '{}_high_sev'.format(_domsoil_d[topaz_id])

                # need to recalculate the pct_coverages
                # total_area = 0.0
                for k in _soils:
                    _soils[k].area = 0.0

                watershed = Watershed.getInstance(self.wd)
                total_area = watershed.wsarea
                for topaz_id, k in _domsoil_d.items():
                    _soils[k].area += watershed.area_of(topaz_id)

                for k in _soils:
                    coverage = 100.0 * _soils[k].area / total_area
                    _soils[k].pct_coverage = coverage

            soils.soils = _soils
            soils.domsoil_d = _domsoil_d
            soils.dump_and_unlock()

        except Exception:
            soils.unlock('-f')
            raise

    def _assign_au_soils(self):

        wd = self.wd

        ron = Ron.getInstance(wd)
        soils = Soils.getInstance(wd)
        landuse = Landuse.getInstance(wd)

        # noinspection PyBroadExpection
        try:
            soils.lock()

            _domsoil_d = deepcopy(soils.domsoil_d)
            _soils = deepcopy(soils.soils)

            domlc_d = landuse.domlc_d

            for topaz_id, mukey in soils.domsoil_d.items():
                dom = domlc_d[topaz_id]

                if dom in ['131', '132']:
                    _domsoil_d[topaz_id] = '{}_lowmod_sev'.format(_domsoil_d[topaz_id])
                elif dom in ['133']:
                    _domsoil_d[topaz_id] = '{}_high_sev'.format(_domsoil_d[topaz_id])

                # need to recalculate the pct_coverages
                # total_area = 0.0
                for k in _soils:
                    _soils[k].area = 0.0

                watershed = Watershed.getInstance(self.wd)
                total_area = watershed.wsarea
                for topaz_id, k in _domsoil_d.items():
                    _soils[k].area += watershed.area_of(topaz_id)

                for k in _soils:
                    coverage = 100.0 * _soils[k].area / total_area
                    _soils[k].pct_coverage = coverage

            soils.soils = _soils
            soils.domsoil_d = _domsoil_d
            soils.dump_and_unlock()

        except Exception:
            soils.unlock('-f')
            raise

    def modify_soils(self):

        wd = self.wd

        legacy_mode = self.legacy_mode

        ron = Ron.getInstance(wd)
        if 'lt' in ron.mods or 'portland' in ron.mods or 'seattle' in ron.mods or 'general' in ron.mods:
            return

        soils_dir = self.soils_dir
        baer_soils_dir = self.baer_soils_dir

        soils_dict = {"130-clay loam": "20-yr forest clay loam.sol",
                      "131-clay loam": "Low severity fire-clay loam.sol",
                      "132-clay loam": "Low severity fire-clay loam.sol",
                      "133-clay loam": "High severity fire-clay loam.sol",
                      "130-loam": "20-yr forest loam.sol",
                      "131-loam": "Low severity fire-loam.sol",
                      "132-loam": "Low severity fire-loam.sol",
                      "133-loam": "High severity fire-loam.sol",
                      "130-sand loam": "20-yr forest sandy loam.sol",
                      "131-sand loam": "Low severity fire-sandy loam.sol",
                      "132-sand loam": "Low severity fire-sandy loam.sol",
                      "133-sand loam": "High severity fire-sandy loam.sol",
                      "130-silt loam": "20-yr forest silt loam.sol",
                      "131-silt loam": "Low severity fire-silt loam.sol",
                      "132-silt loam": "Low severity fire-silt loam.sol",
                      "133-silt loam": "High severity fire-silt loam.sol"}

        _soils = {}
        for k, fn in soils_dict.items():
            yaml_soil = YamlSoil(_join(baer_soils_dir, fn))

            _soils[k] = SoilSummary(
                mukey=k,
                fname=fn,
                clay=yaml_soil.clay,
                sand=yaml_soil.sand,
                avke=yaml_soil.avke,
                soils_dir=soils_dir,
                build_date="N/A",
                desc=fn[:-4]
            )

            shutil.copyfile(_join(baer_soils_dir, fn),
                            _join(soils_dir, fn))

        soils = Soils.getInstance(wd)

        if soils.mode != SoilsMode.Gridded:
            return

        # noinspection PyBroadExpection
        try:
            soils.lock()

            _domsoil_d = {}
            landuse = Landuse.getInstance(wd)
            domlc_d = landuse.domlc_d

            for topaz_id, mukey in soils.domsoil_d.items():
                dom = domlc_d[topaz_id]

                if not legacy_mode:
                    _s = soils.soils[mukey]
                    clay, sand = _s.clay, _s.sand
                    assert clay is not None
                    assert sand is not None

                    _simple_texture = simple_texture(clay, sand)
                else:
                    _simple_texture = 'sand loam'

                _domsoil_d[topaz_id] = '{}-{}'.format(dom, _simple_texture)

                # need to recalculate the pct_coverages
                #total_area = 0.0
                for k in _soils:
                    _soils[k].area = 0.0

                watershed = Watershed.getInstance(self.wd)
                total_area = watershed.wsarea
                for topaz_id, k in _domsoil_d.items():
                    _soils[k].area += watershed.area_of(topaz_id)

                for k in _soils:
                    coverage = 100.0 * _soils[k].area / total_area
                    _soils[k].pct_coverage = coverage

            soils.soils.update(_soils)
            soils.domsoil_d = _domsoil_d
            soils.dump_and_unlock()

        except Exception:
            soils.unlock('-f')
            raise

    def _calc_sbs_coverage(self, sbs):

        self.lock()

        try:

            watershed = Watershed.getInstance(self.wd)
            bounds, transform, proj = read_raster(watershed.bound)

            assert bounds.shape == sbs.shape

            c = Counter(sbs[np.where(bounds == 1.0)])

            total_px = float(sum(c.values()))

            self.sbs_coverage = {
                                 'noburn': c[130] / total_px,
                                 'low': c[131] / total_px,
                                 'moderate': c[132] / total_px,
                                 'high': c[133] / total_px,
                                 }

            self.dump_and_unlock()

        except:
            self.unlock('-f')
            raise
