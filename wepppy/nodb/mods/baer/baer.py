"""BAER (Burned Area Emergency Response) NoDb controller.

This module orchestrates burn severity rasters, soils replacements, and
post-fire landuse handling as part of the NoDb workflow. BAER predates the
Disturbed mod and remains in use for legacy projects that expect the
four-class Soil Burn Severity pipeline.

Responsibilities:
* Validate and reproject SBS rasters for map display and watershed alignment.
* Derive landuse/soil replacements from burn severity classes.
* Trigger optional RRED cost-effectiveness analyses.
"""

from __future__ import annotations

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import ast
import os
import shutil
from collections import Counter
from copy import deepcopy
from subprocess import PIPE, Popen
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from osgeo import gdal

from deprecated import deprecated

from os.path import exists as _exists
from os.path import join as _join

from wepppy.all_your_base import isint
from wepppy.all_your_base.geo import haversine, read_raster, wgs84_proj4
from wepppy.nodb.base import NoDbBase, TriggerEvents
from wepppy.nodb.core.landuse import Landuse, LanduseMode
from wepppy.nodb.core.ron import Ron
from wepppy.nodb.core.soils import Soils, SoilsMode
from wepppy.nodb.core.watershed import Watershed
from wepppy.nodb.mods.rred import Rred
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import SoilReplacements, WeppSoilUtil, simple_texture

from .sbs_map import SoilBurnSeverityMap

__all__ = [
    'BaerNoDbLockedException',
    'sbs_soil_replacements',
    'Baer',
]

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



@deprecated("supplanted by Disturbed, needed for Portland")
class Baer(NoDbBase):
    """Legacy BAER controller that coordinates burn severity workflows."""
    __name__ = 'Baer'

    filename = 'baer.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            if not _exists(self.baer_dir):
                os.mkdir(self.baer_dir)

            self._baer_fn: Optional[str] = None
            self._bounds: Optional[List[List[float]]] = None
            self._classes: Optional[List[int]] = None
            self._breaks: Optional[List[int]] = None
            self._counts: Optional[Dict[str, int]] = None
            self._nodata_vals: Optional[List[int]] = None
            self._is256: Optional[bool] = None

            self._legacy_mode: bool = self.config_get_bool('baer', 'legacy_mode')

            self.sbs_coverage: Optional[Dict[str, float]] = None

    @property
    def legacy_mode(self) -> bool:
        return getattr(self, '_legacy_mode', False)

    @property
    def baer_dir(self) -> str:
        return _join(self.wd, 'baer')

    @property
    def baer_soils_dir(self) -> str:
        return _join(_data_dir, 'soils')

    @property
    def baer_fn(self) -> Optional[str]:
        return self._baer_fn

    @property
    def has_map(self) -> bool:
        return self._baer_fn is not None

    @property
    def is256(self) -> bool:
        return self._is256 is not None

    @property
    def color_tbl_path(self) -> str:
        return _join(self.baer_dir, 'color_table.txt')

    @property
    def bounds(self) -> Optional[List[List[float]]]:
        return self._bounds

    @property
    def classes(self) -> Optional[List[int]]:
        return self._classes

    @property
    def breaks(self) -> Optional[List[int]]:
        return self._breaks

    @property
    def nodata_vals(self) -> str:
        if self._nodata_vals is None:
            return ''

        return ', '.join(str(v) for v in self._nodata_vals)

    def classify(self, value: int) -> str:

        if self._nodata_vals is not None:
            if value in self._nodata_vals:
                return 'No Data'

        i = 0
        breaks = self.breaks
        if breaks is None:
            raise ValueError('Burn class breaks are not defined.')

        for i, brk in enumerate(breaks):
            if value <= brk:
                break

        return ('No Burn',
                'Low Severity Burn',
                'Moderate Severity Burn',
                'High Severity Burn')[i]

    @property
    def baer_path(self) -> Optional[str]:
        if self._baer_fn is None:
            return None

        return _join(self.baer_dir, self._baer_fn)

    @property
    def baer_wgs(self) -> str:
        baer_path = self.baer_path
        if baer_path is None:
            raise ValueError('BAER raster has not been validated yet.')
        return baer_path[:-4] + '.wgs' + baer_path[-4:]

    @property
    def baer_rgb(self) -> str:
        return self.baer_wgs[:-4] + '.rgb.vrt'

    @property
    def baer_rgb_png(self) -> str:
        return _join(self.baer_dir, 'baer.wgs.rgba.png')

    @property
    def baer_cropped(self) -> str:
        return _join(self.baer_dir, 'baer.cropped.tif')

    @property
    def legend(self) -> List[Tuple[int, str, str]]:
        keys = [130, 131, 132, 133]

        descs = ['No Burn',
                'Low Severity Burn',
                'Moderate Severity Burn',
                'High Severity Burn']

        colors = ['#00734A', '#4DE600', '#FFFF00', '#FF0000']

        return list(zip(keys, descs, colors))

    def write_color_table(self) -> None:
        breaks = self.breaks
        if breaks is None:
            raise ValueError('Burn class breaks are not defined.')
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

    def build_color_map(self) -> None:
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
    def sbs_wgs_n(self) -> int:
        """
        number of pixels in the WGS projected SBS
        """
        if self._counts is None:
            raise ValueError('Burn severity map has not been validated.')
        return sum(self._counts.values())

    @property
    def sbs_wgs_area_ha(self) -> float:
        """
        area of the WGS projected SBS in ha
        """
        bounds = self.bounds
        if bounds is None:
            raise ValueError('Burn severity bounds are not available.')

        [[sw_y, sw_x], [ne_y, ne_x]] = bounds
        nw_y, nw_x = ne_y, sw_x

        width = haversine((nw_x, nw_y), (ne_x, ne_y)) * 1000
        height = haversine((nw_x, nw_y), (sw_x, sw_y)) * 1000
        return width * height * 0.0001

    @property
    def sbs_class_counts(self) -> Counter[str]:
        """
        dictionary with burn class keys and pixel counts of the WGS projected SBS
        """
        classes = self.classes
        counts_raw = self._counts
        if classes is None or counts_raw is None:
            raise ValueError('Burn severity classes are not available.')

        counts = Counter()
        for value in classes:
            counts[self.classify(value)] += counts_raw[str(value)]

        return counts

    @property
    def sbs_class_pcts(self) -> Dict[str, float]:
        """
        dictionary with burn class keys percentages of cover of the WGS projected SBS
        """
        counts = self.sbs_class_counts
        pcts = {}
        tot_px = counts.get('Low Severity Burn', 0) + \
                 counts.get('Moderate Severity Burn', 0) + \
                 counts.get('High Severity Burn', 0)

        for k in counts:
            if tot_px == 0:
                pcts[k] = 0.0
            else:
                pcts[k] = 100.0 * counts[k] / tot_px

        return pcts

    @property
    def sbs_class_areas(self) -> Dict[str, float]:
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
    def class_map(self) -> List[Tuple[int, str, int]]:
        if self.classes is None or self._counts is None:
            raise ValueError('Burn severity classes are not available.')
        return [(v, self.classify(v), self._counts[str(v)]) for v in self.classes]

    def modify_burn_class(self, breaks: Sequence[int], nodata_vals: Optional[str]) -> None:
        with self.locked():
            break_values = list(breaks)
            assert len(break_values) == 4
            assert break_values[0] <= break_values[1]
            assert break_values[1] <= break_values[2]
            assert break_values[2] <= break_values[3]

            self._breaks = break_values
            if nodata_vals is not None:
                if str(nodata_vals).strip() != '':
                    _nodata_vals = ast.literal_eval('[{}]'.format(nodata_vals))
                    assert all(isint(v) for v in _nodata_vals)
                    self._nodata_vals = _nodata_vals

            self.write_color_table()
            self.build_color_map()

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.landuse_map)
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    def remove_sbs(self) -> None:
        with self.locked():
            if _exists(self._baer_fn):
                os.remove(self._baer_fn)

            self._baer_fn = None
            self._nodata_vals = None
            self._bounds = None
            self._is256 = None
            self._classes = None
            self._counts = None
            self._breaks = None

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.landuse_map)
            prep.has_sbs = False
        except FileNotFoundError:
            pass

    def validate(self, fn: str) -> None:
        with self.locked():
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
            data = np.array(band.ReadAsArray(), dtype=np.int64)

            nodata = band.GetNoDataValue()
            if nodata is not None:
                self._nodata_vals = [np.int64(nodata)]

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

            is256 = len(classes) > 7 or max(classes) >= 255

            max_counts = max(classes)
            if is256:
                breaks = [75, 109, 187, max_counts]
            else:
                if max(counts) == 3:
                    breaks = [0, 1, 2, max_counts]
                else:
                    breaks = [1, 2, 3, max_counts]

            self._is256 = is256
            self._classes = classes
            self._counts = {str(k): v for k, v in counts.items()}
            self._breaks = breaks

            self.write_color_table()
            self.build_color_map()

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.landuse_map)
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    def on(self, evt: TriggerEvents) -> None:
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
            if 'rred' in self.mods:
                baer_cropped = self.baer_cropped
                sbs = SoilBurnSeverityMap(baer_cropped, self.breaks, self._nodata_vals, ignore_ct=True)

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

    @property
    def ct(self) -> Optional[str]:
        return None

    def remap_landuse(self) -> None:
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

        with landuse.locked():
            sbs = SoilBurnSeverityMap(baer_cropped, self.breaks, self._nodata_vals, ignore_ct=True)
            self._calc_sbs_coverage(sbs)

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
                    landuse.domlc_d = domlc_d

            landuse = landuse.getInstance(wd)
            landuse.build_managements(_map='default')

    def _assign_eu_soils(self) -> None:

        wd = self.wd

        ron = Ron.getInstance(wd)
        soils = Soils.getInstance(wd)
        landuse = Landuse.getInstance(wd)

        with soils.locked():
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
                    _soils[k].area += watershed.hillslope_area(topaz_id)

                for k in _soils:
                    coverage = 100.0 * _soils[k].area / total_area
                    _soils[k].pct_coverage = coverage

            soils.soils = _soils
            soils.domsoil_d = _domsoil_d

    def _assign_au_soils(self) -> None:

        wd = self.wd

        ron = Ron.getInstance(wd)
        soils = Soils.getInstance(wd)
        landuse = Landuse.getInstance(wd)

        with soils.locked():
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
                    _soils[k].area += watershed.hillslope_area(topaz_id)

                for k in _soils:
                    coverage = 100.0 * _soils[k].area / total_area
                    _soils[k].pct_coverage = coverage

            soils.soils = _soils
            soils.domsoil_d = _domsoil_d

    def modify_soils(self) -> None:

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
            yaml_soil = WeppSoilUtil(_join(baer_soils_dir, fn))

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

        with soils.locked():
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
                    _soils[k].area += watershed.hillslope_area(topaz_id)

                for k in _soils:
                    coverage = 100.0 * _soils[k].area / total_area
                    _soils[k].pct_coverage = coverage

            soils.soils.update(_soils)
            soils.domsoil_d = _domsoil_d

    def _calc_sbs_coverage(self, sbs: Optional[SoilBurnSeverityMap]) -> None:
        with self.locked():
            if sbs is None:
                self.sbs_coverage = {
                    'noburn': 1.0,
                    'low': 0.0,
                    'moderate': 0.0,
                    'high': 0.0
                }
            else:
                watershed = Watershed.getInstance(self.wd)
                bounds, transform, proj = read_raster(watershed.bound)

                if not sbs.data.shape == bounds.shape:
                    raise Exception("sbs map and watershed.bound do not align")

                assert sbs.data.shape == bounds.shape, [sbs.data.shape, bounds.shape]


                c = Counter(sbs.data[np.where(bounds == 1.0)])

                total_px = float(sum(c.values()))

                self.sbs_coverage = {
                                     'noburn': c[130] / total_px,
                                     'low': c[131] / total_px,
                                     'moderate': c[132] / total_px,
                                     'high': c[133] / total_px
                                     }
