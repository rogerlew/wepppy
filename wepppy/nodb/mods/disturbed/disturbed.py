# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import ast
import csv
import shutil
from collections import Counter
import jsonpickle
from datetime import datetime
from subprocess import Popen, PIPE
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from copy import deepcopy
from collections import Counter

import math
import numpy as np
from osgeo import gdal

from deprecated import deprecated

from wepppy.all_your_base import isint, isfloat
from wepppy.all_your_base.geo import wgs84_proj4, read_raster, haversine, raster_stacker, validate_srs
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture, WeppSoilUtil, SoilMultipleOfeSynth

from ...landuse import Landuse, LanduseMode
from ...soils import Soils
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...redis_prep import RedisPrep as Prep
from ...base import NoDbBase, TriggerEvents
from ..baer.sbs_map import SoilBurnSeverityMap

try:
    import wepppyo3
    from wepppyo3.raster_characteristics import identify_mode_single_raster_key
    from wepppyo3.raster_characteristics import identify_mode_multiple_raster_key
except:
    wepppyo3 = None

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


def read_disturbed_land_soil_lookup(fname):
    d = {}

    with open(fname) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            try:
                disturbed_class = row['luse']
            except KeyError:
                disturbed_class = row['disturbed_class']

            try:
                texid = row['stext']
            except KeyError:
                texid = row['texid']

            for k in row:
                v = row[k]
                if isinstance(v, str):
                    if v.lower().startswith('none'):
                        row[k] = None

            if texid != '' and disturbed_class != '':
                d[(texid, disturbed_class)] = row

    return d


def migrate_land_soil_lookup(src_fn, target_fn, pars, defaults):
    src = read_disturbed_land_soil_lookup(src_fn)
    target = read_disturbed_land_soil_lookup(target_fn)

    for k in src:
        if k not in target:
            target[k] = src[k]

    for par in pars:
        for k in target:
            if par in src[k]:
                v = src[k][par]
            else:
                v = defaults[par]
            target[k][par] = v

    fieldnames = list(target[k].keys())

    with open(target_fn, 'w') as fp:
        wtr = csv.DictWriter(fp, fieldnames)
        wtr.writeheader()

        for k, row in target.items():
            wtr.writerow(row)


def write_disturbed_land_soil_lookup(fname, data):
    with open(fname) as fp:
        rdr = csv.DictReader(fp)
        fieldnames = rdr.fieldnames

    with open(fname, 'w') as fp:
        wtr = csv.DictWriter(fp, fieldnames)
        wtr.writeheader()

        for row in data:
            wtr.writerow({k: v for k, v in zip(fieldnames, row)})


def _replace_parameter(original, replacement):
    if replacement is None:
        return original

    elif replacement.strip().startswith('*'):
        return str(float(original) * float(replacement.replace('*', '')))

    else:
        return replacement


class DisturbedNoDbLockedException(Exception):
    pass


class InvalidProjection(Exception):
    """
    Map contains an invalid projection. Try reprojecting to UTM.
    """

    __name__ = 'Invalid Projection'


class Disturbed(NoDbBase):
    __name__ = 'Disturbed'

    def __init__(self, wd, cfg_fn):
        super(Disturbed, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.disturbed_dir)

            self._disturbed_fn = None
            self._bounds = None
            self._classes = None
            self._breaks = None
            self._counts = None
            self._nodata_vals = None
            self._is256 = None

            self.reset_land_soil_lookup()

            self.sbs_coverage = None
            self._h0_max_om = self.config_get_float('disturbed', 'h0_max_om')
            self._sol_ver = self.config_get_float('disturbed', 'sol_ver')

            self._fire_date = self.config_get_str('disturbed', 'fire_date')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def fire_date(self):
        return getattr(self, "_fire_date", None)

    @fire_date.setter
    def fire_date(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._fire_date = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def default_land_soil_lookup_fn(self):
        _lookup_path = self.config_get_path('disturbed', 'land_soil_lookup', None)
        if _lookup_path is None:
            _lookup_path = _join(_data_dir, 'disturbed_land_soil_lookup.csv')
        return _lookup_path

    def reset_land_soil_lookup(self):
        _lookup = _join(self.disturbed_dir, 'disturbed_land_soil_lookup.csv')

        if _exists(_lookup):
            os.remove(_lookup)

        shutil.copyfile(self.default_land_soil_lookup_fn, _lookup)

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd, allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'disturbed.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Disturbed), db

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @property
    def _nodb(self):
        return _join(self.wd, 'disturbed.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'disturbed.nodb.lock')

    @property
    def disturbed_dir(self):
        return _join(self.wd, 'disturbed')

    baer_dir = disturbed_dir

    @property
    def disturbed_soils_dir(self):
        return _join(_data_dir, 'soils')

    @property
    def disturbed_fn(self):
        return self._disturbed_fn

    @property
    def has_map(self):
        return self._disturbed_fn is not None

    @property
    def is256(self):
        return self._is256 is not None

    @property
    def ct(self):
        return getattr(self, '_ct', None)

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
    def h0_max_om(self):
        return getattr(self, '_h0_max_om', None)

    @property
    def sol_ver(self):
        return getattr(self, '_sol_ver', 7778.0)

    @sol_ver.setter
    def sol_ver(self, value):
        self.lock()
  
        try:
            self._sol_ver = float(value)            
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def nodata_vals(self):
        if self._nodata_vals is None:
            return ''

        return ', '.join(str(v) for v in self._nodata_vals)

    @property
    def disturbed_path(self):
        if self._disturbed_fn is None:
            return None

        return _join(self.disturbed_dir, self._disturbed_fn)

    def build_uniform_sbs(self, value=4):
        import rasterio
        sbs_fn = _join(self.disturbed_dir, 'uniform_sbs.tif')

        # Open the input raster file
        with rasterio.open(self.dem_fn) as src:
            # Read the input raster data as a numpy array
            dem = src.read(1)

            # Define the output raster metadata based on the input raster metadata
            out_meta = src.meta.copy()
            out_meta.update(dtype=rasterio.uint8, count=1, nodata=255)

            # Create the output raster data as a numpy array
            out_arr = np.full_like(dem, fill_value=value, dtype=rasterio.uint8)

            # Write the output raster data to a new geotiff file
            with rasterio.open(sbs_fn, 'w', **out_meta) as dst:
                dst.write(out_arr, 1)

        # Open the written raster file with GDAL to set color table
        ds = gdal.Open(sbs_fn, gdal.GA_Update)
        band = ds.GetRasterBand(1)
        color_table = gdal.ColorTable()
        color_table.SetColorEntry(0, (0, 100, 0, 255))  # unburned
        color_table.SetColorEntry(1, (127, 255, 212, 255))  # low
        color_table.SetColorEntry(2, (255, 255, 0, 255))  # moderate
        color_table.SetColorEntry(3, (255, 0, 0, 255))  # high
        color_table.SetColorEntry(255, (255, 255, 255, 0))  # n/a
        band.SetColorTable(color_table)
        band = None  # Dereference to make sure all data is written
        ds = None  # Dereference to make sure all data is written

        return sbs_fn

    @property
    def sbs_4class_path(self):
        return _join(self.disturbed_dir, 'sbs_4class.tif')

    @property
    def disturbed_wgs(self):
        disturbed_path = self.disturbed_path
        return disturbed_path[:-4] + '.wgs.tif'

    @property
    def disturbed_rgb(self):
        return self.disturbed_wgs[:-4] + '.rgb.vrt'

    @property
    def disturbed_rgb_png(self):
        return _join(self.disturbed_dir, 'baer.wgs.rgba.png')

    baer_rgb_png = disturbed_rgb_png

    @property
    def disturbed_cropped(self):
        return _join(self.disturbed_dir, 'baer.cropped.tif')

    @property
    def legend(self):
        keys = [130, 131, 132, 133]

        descs = ['No Burn',
                'Low Severity Burn',
                'Moderate Severity Burn',
                'High Severity Burn']

        colors = ['#00734A', '#4DE600', '#FFFF00', '#FF0000']

        return list(zip(keys, descs, colors))

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
    def sbs_class_pcts(self):
        """
        dictionary with burn class keys percentages of cover of the WGS projected SBS
        """
        counts = self._counts
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
    def sbs_class_areas(self):
        """
        dictionary with burn class keys and areas (ha) of the WGS projected SBS
        """
        ha__px = self.sbs_wgs_area_ha / self.sbs_wgs_n
        counts = self._counts
        areas = {}

        for k in counts:
            areas[k] = counts[k] * ha__px 

        return areas

    @property
    def class_map(self):
        sbs = SoilBurnSeverityMap(self.disturbed_path)
        return sbs.class_map

    def modify_burn_class(self, breaks, nodata_vals):
        assert len(breaks) == 4
        assert breaks[0] <= breaks[1]
        assert breaks[1] <= breaks[2]
        assert breaks[2] <= breaks[3]

        if nodata_vals is not None:
            if str(nodata_vals).strip() != '':
                nodata_vals = ast.literal_eval('[{}]'.format(nodata_vals))
                assert all(isint(v) for v in nodata_vals)

        self.validate(self.disturbed_path, breaks, nodata_vals)

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('landuse_map')
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    def modify_color_map(self, color_map):

        self.validate(self.disturbed_path, color_map=color_map)

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('landuse_map')
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    @property
    def color_to_severity_map(self):
        if getattr(self, '_ct', None) is None:
            return None

        color_map = getattr(self, '_color_map', None)

        if color_map is None:
            self.validate(self.disturbed_path, self.breaks, self.nodata_vals)
            color_map = getattr(self, '_color_map', None)

        return {tuple(rgb.split('_')): v for rgb, v in color_map.items()}

    def remove_sbs(self):
        self.lock()

        # noinspection PyBroadException
        try:
            disturbed_fn = getattr(self, '_disturbed_fn', None)

            if disturbed_fn is not None and  _exists(disturbed_fn):
                os.remove(disturbed_fn)


            self._disturbed_fn = None
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

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('landuse_map')
            prep.has_sbs = False
        except FileNotFoundError:
            pass

    def validate(self, fn, breaks=None, nodata_vals=None, color_map=None):
        self.lock()

        # noinspection PyBroadException
        try:
            self._disturbed_fn = fn
            self._nodata_vals = nodata_vals

            disturbed_path = self.disturbed_path
            assert _exists(disturbed_path), disturbed_path

            if not validate_srs(disturbed_path):
                raise InvalidProjection("Map contains an invalid projection. Try reprojecting to UTM.")

            sbs = SoilBurnSeverityMap(disturbed_path, breaks=breaks, nodata_vals=nodata_vals, color_map=color_map)
            self._bounds = sbs.export_wgs_map(self.disturbed_wgs)
            sbs.export_rgb_map(self.disturbed_wgs, self.disturbed_rgb, self.disturbed_rgb_png)

            self._ct = sbs.ct
            self._is256 = sbs.is256
            self._classes = sorted([int(x) for x in sbs.classes])
            self._counts = sbs.burn_class_counts
            if sbs.color_map is None:
                self._color_map = None
            else:
                self._color_map = {'_'.join(str(x) for x in rgb): v for rgb, v in sbs.color_map.items()}
            self._breaks = sbs.breaks

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('landuse_map')
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    def on(self, evt):
        multi_ofe = self.multi_ofe

        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
            self.spatialize_treecanopy()

            if multi_ofe:
                self.remap_mofe_landuse()

        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            if self.multi_ofe:
                self.modify_mofe_soils()
            else:
                self.modify_soils()

    def spatialize_treecanopy(self):
        wd = self.wd

        if 'treecanopy' in self.mods:
            import wepppy
            treecanopy = wepppy.nodb.mods.Treecanopy.getInstance(wd)
            treecanopy.acquire_raster()
            treecanopy.analyze()
        else:
            return

        landuse = Landuse.getInstance(wd)

        try:
            landuse.lock()

            for topaz_id, treecanopy_pointdata in treecanopy:
                dom = landuse.domlc_d[topaz_id]
                man = landuse.managements[dom]

                if man.disturbed_class in ['forest', 'young forest'] and treecanopy:
                    _dom = '{}-{}'.format(dom, topaz_id)
                    _man = deepcopy(man)
                    _man.key = _dom
                    # this it not the right way to do it, because it will keep overwriting.
                    _man.cancov_override = round(treecanopy.data[topaz_id]) / 100.0
                    landuse.domlc_d[topaz_id] = _dom
                    landuse.managements[_dom] = _man

            landuse.dump_and_unlock()

        except Exception:
            landuse.unlock('-f')
            raise

    def get_sbs(self):

        wd = self.wd

        if not self.has_map:
            return

        disturbed_path = self.disturbed_path

        disturbed_cropped = self.disturbed_cropped
        if _exists(disturbed_cropped):
            os.remove(disturbed_cropped)

        map = Ron.getInstance(wd).map
        xmin, ymin, xmax, ymax = [str(v) for v in map.utm_extent]
        cellsize = str(Ron.getInstance(wd).map.cellsize)

        cmd = ['gdalwarp', '-t_srs',  'epsg:%s' % map.srid,
               '-tr', cellsize, cellsize,
               '-te', xmin, ymin, xmax, ymax,
               '-r', 'near', disturbed_path, disturbed_cropped]

        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(disturbed_cropped), ' '.join(cmd)

        return SoilBurnSeverityMap(disturbed_cropped, self.breaks, self._nodata_vals)
     
    def get_sbs_4class(self):
        sbs = self.get_sbs()
        sbs.export_4class_map(self.sbs_4class_path)
        return SoilBurnSeverityMap(self.sbs_4class_path)

    def remap_landuse(self):
        wd = self.wd

        landuse = Landuse.getInstance(wd)
        #assert landuse.mode != LanduseMode.Single

        watershed = Watershed.getInstance(wd)

        sbs = self.get_sbs()
        meta = {}

        if sbs is None:
            return

        # noinspection PyBroadException
        try:
            landuse.lock()

            self._calc_sbs_coverage(sbs)

            if wepppyo3 is None:
                sbs_lc_d = sbs.build_lcgrid(watershed.subwta, None)

                for topaz_id, burn_class in sbs_lc_d.items():
                    if (int(topaz_id) - 4) % 10 == 0:
                        continue

                    dom = landuse.domlc_d[topaz_id]
                    man = landuse.managements[dom]

                    # TODO: probably a better way to do this based on the disturbed_class
                    if burn_class in ['131', '132', '133']:
                        if man.disturbed_class in ['forest', 'young forest']:
                            landuse.domlc_d[topaz_id] = {'131': '106', '132': '118', '133': '105'}[burn_class]

                        elif man.disturbed_class == 'shrub':
                            landuse.domlc_d[topaz_id] = {'131': '121', '132': '120', '133': '119'}[burn_class]

                        elif man.disturbed_class in ['tall grass']:
                            landuse.domlc_d[topaz_id] = {'131': '131', '132': '130', '133': '129'}[burn_class]

                    meta[topaz_id] = dict(burn_class=burn_class, disturbed_class=man.disturbed_class)

            else:
                sbs_lc_d = identify_mode_single_raster_key(
                    key_fn=watershed.subwta, parameter_fn=self.disturbed_cropped, ignore_channels=True, ignore_keys=set())
                sbs_lc_d = {k: str(v) for k, v in sbs_lc_d.items()}

                class_pixel_map = sbs.class_pixel_map

                for topaz_id, val in sbs_lc_d.items():
                    if (int(topaz_id) - 4) % 10 == 0:
                        continue

                    dom = landuse.domlc_d[topaz_id]
                    man = landuse.managements[dom]

                    burn_class = class_pixel_map[val]

                    # TODO: probably a better way to do this based on the disturbed_class
                    if burn_class in ['131', '132', '133']:
                        if man.disturbed_class in ['forest', 'young forest']:
                            landuse.domlc_d[topaz_id] = {'131': '106', '132': '118', '133': '105'}[burn_class]

                        elif man.disturbed_class == 'shrub':
                            landuse.domlc_d[topaz_id] = {'131': '121', '132': '120', '133': '119'}[burn_class]

                        elif man.disturbed_class in ['tall grass']:
                            landuse.domlc_d[topaz_id] = {'131': '131', '132': '130', '133': '129'}[burn_class]

                    meta[topaz_id] = dict(burn_class=burn_class, disturbed_class=man.disturbed_class)

            landuse.dump_and_unlock()

        except Exception:
            landuse.unlock('-f')
            raise

        # noinspection PyBroadException
        try:
            self.lock()
            self._meta = meta
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

        landuse = landuse.getInstance(wd)
        landuse.build_managements()

    @property
    def meta(self):
        if not hasattr(self, '_meta'):
            self.remap_landuse()

        return self._meta

    def remap_mofe_landuse(self):
        wd = self.wd

        landuse = Landuse.getInstance(wd)
        #assert landuse.mode != LanduseMode.Single

        watershed = Watershed.getInstance(wd)

        sbs = self.get_sbs()

        if sbs is None:
            return

        # noinspection PyBroadException
        try:
            landuse.lock()

            self._calc_sbs_coverage(sbs)

            sbs_lc_d = sbs.build_lcgrid(watershed.subwta, watershed.mofe_map)

            for topaz_id in landuse.domlc_mofe_d:
                for _id in landuse.domlc_mofe_d[topaz_id]:
                    burn_class = str(sbs_lc_d[topaz_id][_id])
                    dom = landuse.domlc_mofe_d[topaz_id][_id]
                    man = landuse.managements[dom]

                    # TODO: probably a better way to do this based on the disturbed_class
                    if burn_class in ['131', '132', '133']:
                        if man.disturbed_class in ['forest', 'young forest']:
                            landuse.domlc_mofe_d[topaz_id][_id] = {'131': '106', '132': '118', '133': '105'}[burn_class]

                        elif man.disturbed_class == 'shrub':
                            landuse.domlc_mofe_d[topaz_id][_id] = {'131': '121', '132': '120', '133': '119'}[burn_class]

                        elif man.disturbed_class in ['short grass', 'tall grass']:
                            landuse.domlc_mofe_d[topaz_id][_id] = {'131': '131', '132': '130', '133': '129'}[burn_class]

            landuse.dump_and_unlock()

        except Exception:
            landuse.unlock('-f')
            raise

        landuse = landuse.getInstance(wd)
        landuse.build_managements()

    @property
    def lookup_fn(self):
        _lookup = _join(self.disturbed_dir, 'disturbed_land_soil_lookup.csv')

        if not _exists(_lookup):
            self.reset_land_soil_lookup()

        return _lookup

    @property
    def land_soil_replacements_d(self):
        default_fn = self.default_land_soil_lookup_fn
        _lookup_fn = self.lookup_fn

        lookup = read_disturbed_land_soil_lookup(_lookup_fn)
        for k in lookup:
            if 'pmet_kcb' not in lookup[k]:
                migrate_land_soil_lookup(
                    default_fn, _lookup_fn, ['pmet_kcb', 'pmet_rawp', 'rdmax', 'xmxlai'], {})
                return read_disturbed_land_soil_lookup(_lookup_fn)
                
            elif 'rdmax' not in lookup[k]:
                migrate_land_soil_lookup(
                    default_fn, _lookup_fn, ['rdmax', 'xmxlai'], {})
                return read_disturbed_land_soil_lookup(_lookup_fn)

            elif 'xmxlai' not in lookup[k]:
                migrate_land_soil_lookup(
                    default_fn, _lookup_fn, ['xmxlai'], {})
                return read_disturbed_land_soil_lookup(_lookup_fn)

            elif 'keffflag' not in lookup[k]:
                migrate_land_soil_lookup(
                    default_fn, _lookup_fn, ['keffflag', 'lkeff'], {})
                return read_disturbed_land_soil_lookup(_lookup_fn)

        if ('loam', 'forest moderate sev fire') not in lookup:
            migrate_land_soil_lookup(
                    default_fn, _lookup_fn, [], {})
            return read_disturbed_land_soil_lookup(_lookup_fn)

        return lookup

    def pmetpara_prep(self):
        from wepppy.nodb import Wepp
        _land_soil_replacements_d = self.land_soil_replacements_d

        wd = self.wd
        landuse = Landuse.getInstance(wd)
        soils = Soils.getInstance(wd)
        wepp = Wepp.getInstance(wd)

        domlc_d = {}
        for topaz_id, dom in landuse.domlc_d.items():
            if (int(topaz_id) - 4) % 10 == 0:
                continue
            domlc_d[topaz_id] = dom

        n = len(domlc_d)

        with open(_join(wepp.runs_dir, 'pmetpara.txt'), 'w') as fp:
            fp.write('{n}\n'.format(n=n))

            for i, (topaz_id, dom) in enumerate(domlc_d.items()):

                man_summary = landuse.managements[dom]
                man = man_summary.get_management()

                mukey = soils.domsoil_d[topaz_id]
                _soil = soils.soils[mukey]
                clay = _soil.clay
                sand = _soil.sand

                assert isfloat(clay), clay
                assert isfloat(sand), sand

                texid = simple_texture(clay=clay, sand=sand)
                disturbed_class = man_summary.disturbed_class

                if (texid, disturbed_class) not in _land_soil_replacements_d:
                    texid = 'all'

                if disturbed_class is None or 'developed' in disturbed_class:
                    kcb = 0.95
                    rawb = 0.80
                else:
                    kcb = _land_soil_replacements_d[(texid, disturbed_class)]['pmet_kcb']        
                    rawb = _land_soil_replacements_d[(texid, disturbed_class)]['pmet_rawp']        

                description = f'{texid}-{disturbed_class}'.replace(' ', '_')
                plant_name = man.plants[0].name
                fp.write(f'{plant_name},{kcb},{rawb},{i+1},{description}\n')

    def modify_mofe_soils(self):
        wd = self.wd
        sol_ver = self.sol_ver

        ron = Ron.getInstance(wd)
        landuse = Landuse.getInstance(wd)
        soils = Soils.getInstance(wd)

        _land_soil_replacements_d = self.land_soil_replacements_d

        try:
            soils.lock()

            for topaz_id, mukey in soils.domsoil_d.items():
                if str(topaz_id).endswith('4'):
                    continue

                stack = []
                desc = []

                _soil = soils.soils[mukey]
                clay = _soil.clay
                sand = _soil.sand

                assert isfloat(clay), clay
                assert isfloat(sand), sand

                texid = simple_texture(clay=clay, sand=sand)

                assert len(landuse.domlc_mofe_d[topaz_id]) > 0, topaz_id

                for _id in landuse.domlc_mofe_d[topaz_id]:
                    dom = landuse.domlc_mofe_d[topaz_id][_id]
                    man = landuse.managements[dom]

                    assert man is not None, dom

                    key = (texid, man.disturbed_class)

                    if key not in _land_soil_replacements_d:
                        texid = 'all'
                        key = (texid, man.disturbed_class)

                    replacements = _land_soil_replacements_d.get(key, None)

                    if replacements is None:
                        disturbed_mukey = f'{mukey}-{texid}'
                    else:
                        disturbed_mukey = f'{mukey}-{texid}-{man.disturbed_class}'

                    disturbed_fn = f'{disturbed_mukey}.sol'

                    if disturbed_mukey not in soils.soils:
                        _h0_max_om = None
                        if man.disturbed_class is not None:
                            if 'fire' in man.disturbed_class:
                                _h0_max_om = self.h0_max_om
     
                        soil_u = WeppSoilUtil(_join(soils.soils_dir, _soil.fname))
                        if sol_ver == 7778.0:
                            new = soil_u.to_7778disturbed(replacements, h0_max_om=_h0_max_om)
                        else:
                            new = soil_u.to_over9000(replacements, h0_max_om=_h0_max_om, 
                                                     version=sol_ver)

                        new.write(_join(soils.soils_dir, disturbed_fn))

                        _desc = f'{_soil.desc} - {man.disturbed_class}'
                        soils.soils[disturbed_mukey] = SoilSummary(mukey=disturbed_mukey,
                                                               fname=disturbed_fn,
                                                               soils_dir=soils.soils_dir,
                                                               desc=_desc,
                                                               meta_fn=_soil.meta_fn,
                                                               build_date=str(datetime.now()))

                    desc.append(f'{man.disturbed_class}')
                    stack.append(_join(soils.soils_dir, disturbed_fn))

                key = f'hill_{topaz_id}.mofe'
                sol_fn = f'{key}.sol'
                mofe_synth = SoilMultipleOfeSynth()
                mofe_synth.stack = stack
                mofe_synth.write(_join(soils.soils_dir, sol_fn))
               
                soils.domsoil_d[topaz_id] = key
                soils.soils[key] = SoilSummary(mukey=key,
                                               fname=sol_fn,
                                               soils_dir=soils.soils_dir,
                                               desc='|'.join(desc),
                                               meta_fn=None,
                                               build_date=str(datetime.now()))
           

            # need to recalculate the pct_coverages
            watershed = Watershed.getInstance(self.wd)

            for k in soils.soils:
                soils.soils[k].area = 0.0

            total_area = 0.0
            for topaz_id, k in soils.domsoil_d.items():
                sub_area = watershed.area_of(topaz_id)
                soils.soils[k].area += sub_area
                total_area += sub_area

            for k in soils.soils:
                coverage = 100.0 * soils.soils[k].area / total_area
                soils.soils[k].pct_coverage = coverage

            soils.dump_and_unlock()

        except Exception:
            soils.unlock('-f')
            raise

    def modify_soils(self):
        wd = self.wd
        sol_ver = self.sol_ver

        ron = Ron.getInstance(wd)
        landuse = Landuse.getInstance(wd)
        soils = Soils.getInstance(wd)

        _land_soil_replacements_d = self.land_soil_replacements_d

        try:
            soils.lock()

            for topaz_id, mukey in soils.domsoil_d.items():
                if (int(topaz_id) - 4) % 10 == 0:
                    continue

                dom = landuse.domlc_d[topaz_id]
                man = landuse.managements[dom]

                if man.sol_path:
                    disturbed_mukey = _split(man.sol_fn)[-1].replace('.sol', '')
                    sol_fn =  f'{disturbed_mukey}.sol'
                    new_sol_path = _join(soils.soils_dir, sol_fn)

                    if not _exists(new_sol_path):
                        shutil.copyfile(man.sol_path, new_sol_path)

                    if disturbed_mukey not in soils.soils:
                        soils.soils[disturbed_mukey] = SoilSummary(mukey=disturbed_mukey,
                                                                   fname=sol_fn,
                                                                   soils_dir=soils.soils_dir,
                                                                   desc=disturbed_mukey,
                                                                   meta_fn=None,
                                                                   build_date=str(datetime.now()))
                else:
                    _soil = soils.soils[mukey]
                    clay = _soil.clay
                    sand = _soil.sand

                    assert isfloat(clay), clay
                    assert isfloat(sand), sand

                    texid = simple_texture(clay=clay, sand=sand)

                    key = (texid, man.disturbed_class)

                    if key not in _land_soil_replacements_d:
                        texid = 'all'
                        key = (texid, man.disturbed_class)

                    if key not in _land_soil_replacements_d:
                        continue

                    disturbed_mukey = f'{mukey}-{texid}-{man.disturbed_class}'

                    if disturbed_mukey not in soils.soils:
                        disturbed_fn = disturbed_mukey + '.sol'
                        replacements = _land_soil_replacements_d[key]

                        if 'fire' in man.disturbed_class:
                            _h0_max_om = self.h0_max_om
                        else:
                            _h0_max_om = None

                        soil_u = WeppSoilUtil(_join(soils.soils_dir, _soil.fname))
                        if sol_ver == 7778.0:
                            new = soil_u.to_7778disturbed(replacements, h0_max_om=_h0_max_om)
                        else:
                            new = soil_u.to_over9000(replacements, h0_max_om=_h0_max_om,
                                                     version=sol_ver)

                        new.write(_join(soils.soils_dir, disturbed_fn))

                        desc = f'{_soil.desc} - {man.disturbed_class}'
                        soils.soils[disturbed_mukey] = SoilSummary(mukey=disturbed_mukey,
                                                                   fname=disturbed_fn,
                                                                   soils_dir=soils.soils_dir,
                                                                   desc=desc,
                                                                   meta_fn=_soil.meta_fn,
                                                                   build_date=str(datetime.now()))

                soils.domsoil_d[topaz_id] = disturbed_mukey

            # need to recalculate the pct_coverages
            watershed = Watershed.getInstance(self.wd)

            for k in soils.soils:
                soils.soils[k].area = 0.0

            total_area = 0.0
            for topaz_id, k in soils.domsoil_d.items():
                sub_area = watershed.area_of(topaz_id)
                soils.soils[k].area += sub_area
                total_area += sub_area

            for k in soils.soils:
                coverage = 100.0 * soils.soils[k].area / total_area
                soils.soils[k].pct_coverage = coverage

            soils.dump_and_unlock()

        except Exception:
            soils.unlock('-f')
            raise

    def _calc_sbs_coverage(self, sbs):

        self.lock()

        try:
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
                    dst_fn = watershed.bound.replace('.ARC', '.fixed.tif')
                    raster_stacker(watershed.bound, sbs.fname, dst_fn)
                    bounds, transform, proj = read_raster(dst_fn, dtype=np.int32)

                assert sbs.data.shape == bounds.shape, [sbs.data.shape, bounds.shape]


                c = Counter(sbs.data[np.where(bounds == 1.0)])

                total_px = float(sum(c.values()))

                # todo: calcuate based on disturbed burn classes
                self.sbs_coverage = {
                                     'noburn': c[130] / total_px,
                                     'low': c[131] / total_px,
                                     'moderate': c[132] / total_px,
                                     'high': c[133] / total_px
                                     }
            self.dump_and_unlock()

        except:
            self.unlock('-f')
            raise
