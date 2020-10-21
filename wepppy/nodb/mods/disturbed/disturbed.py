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
from copy import deepcopy
from datetime import datetime
from subprocess import Popen, PIPE
from os.path import join as _join
from os.path import exists as _exists

import numpy as np
from osgeo import gdal

from wepppy.all_your_base import wgs84_proj4, isint, read_arc, isfloat
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import SoilReplacements, soil_specialization, simple_texture

from ...landuse import Landuse, LanduseMode
from ...soils import Soils, SoilsMode
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...mods.rred import Rred
from ...base import NoDbBase, TriggerEvents
from ..baer.sbs_map import SoilBurnSeverityMap
from ....wepp.management import get_management_summary

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


def read_disturbed_land_soil_lookup(fname):
    d = {}

    with open(fname) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            disturbed_class = row['disturbed_class']
            texid = row['texid']

            for k in row:
                v = row[k]
                if isinstance(v, str):
                    if v.lower().startswith('none'):
                        row[k] = None

            d[(texid, disturbed_class)] = row

    return d


def _replace_parameter(original, replacement):
    if replacement is None:
        return original

    elif replacement.strip().startswith('*'):
        return str(float(original) * float(replacement.replace('*', '')))

    else:
        return replacement


def disturbed_soil_specialization(src, dst, replacements, h0_min_depth=50):
    """
    Creates a new soil file based on soil_in_fname and makes replacements
    from the provided replacements namedtuple
    """
    # read the soil_in_fname file
    with open(src) as f:
        lines = f.readlines()

    header = [L for L in lines if L.startswith('#')]
    header.append('# {}\n'.format(repr(replacements)))

    lines = [L for L in lines if not L.startswith('#')]

    line4 = lines[3]
    line4 = line4.split()
    line4[-4] = _replace_parameter(line4[-4], replacements['ki'])
    line4[-3] = _replace_parameter(line4[-3], replacements['kr'])
    line4[-2] = _replace_parameter(line4[-2], replacements['shcrit'])
    line4 = ' '.join(line4) + '\n'

    line5 = lines[4]
    line5 = line5.split()
    if float(line5[0]) < 50:
        line5[0] = '50'
    line5[2] = _replace_parameter(line5[2], replacements['avke'])

    if len(line5) < 5:  # no horizons (e.g. rock)
        shutil.copyfile(src, dst)
        return

    line5 = ' '.join(line5) + '\n'

    if 'kslast' in replacements:
        if len(lines) > 5 and len(lines[-1]) == 3:
            lastline = lines[-1].split()
            lastline[-1] = '{}'.format(replacements['kslast'])
            lines[-1] = ' '.join(lastline)

    # Create new soil files
    with open(dst, 'w') as f:
        f.writelines(header)
        f.writelines(lines[:3])
        f.writelines(line4)
        f.writelines(line5)
        if len(lines) > 5:
            f.writelines(lines[5:])


class DisturbedNoDbLockedException(Exception):
    pass


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
        with open(_join(wd, 'disturbed.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Disturbed), db

            if _exists(_join(wd, 'READONLY')):
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
    def color_tbl_path(self):
        return _join(self.disturbed_dir, 'color_table.txt')

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
    def disturbed_path(self):
        if self._disturbed_fn is None:
            return None

        return _join(self.disturbed_dir, self._disturbed_fn)

    @property
    def disturbed_wgs(self):
        disturbed_path = self.disturbed_path
        return disturbed_path[:-4] + '.wgs' + disturbed_path[-4:]

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
        disturbed_rgb = self.disturbed_rgb
        if _exists(disturbed_rgb):
            os.remove(disturbed_rgb)

        cmd = ['gdaldem', 'color-relief', '-of', 'VRT',  self.disturbed_wgs, self.color_tbl_path, disturbed_rgb]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        disturbed_rgb_png = self.disturbed_rgb_png
        if _exists(disturbed_rgb_png):
            os.remove(disturbed_rgb_png)

        cmd = ['gdal_translate', '-of', 'PNG', disturbed_rgb, disturbed_rgb_png]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

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

    def validate(self, fn):
        self.lock()

        # noinspection PyBroadException
        try:
            self._disturbed_fn = fn
            self._nodata_vals = None

            disturbed_path = self.disturbed_path
            assert _exists(disturbed_path), disturbed_path

            ds = gdal.Open(disturbed_path)
            assert ds is not None
            del ds

            # transform to WGS1984 to display on map
            disturbed_wgs = self.disturbed_wgs
            if _exists(disturbed_wgs):
                os.remove(disturbed_wgs)

            cmd = ['gdalwarp', '-t_srs', wgs84_proj4,
                   '-r', 'near', disturbed_path, disturbed_wgs]
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            p.wait()

            assert _exists(disturbed_wgs), ' '.join(cmd)

            ds = gdal.Open(disturbed_wgs)
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

        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()

    def remap_landuse(self):
        wd = self.wd

        if not self.has_map:
            return

        disturbed_path = self.disturbed_path

        disturbed_cropped = self.disturbed_cropped
        if _exists(disturbed_cropped):
            os.remove(disturbed_cropped)

        topaz = Topaz.getInstance(wd)
        xmin, ymin, xmax, ymax = [str(v) for v in topaz.utmextent]
        cellsize = str(Ron.getInstance(wd).map.cellsize)

        cmd = ['gdalwarp', '-t_srs',  'epsg:%s' % topaz.srid,
               '-tr', cellsize, cellsize,
               '-te', xmin, ymin, xmax, ymax,
               '-r', 'near', disturbed_path, disturbed_cropped]

        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(disturbed_cropped), ' '.join(cmd)

        landuse = Landuse.getInstance(wd)
        assert landuse.mode != LanduseMode.Single

        # noinspection PyBroadException
        try:
            landuse.lock()

            sbs = SoilBurnSeverityMap(disturbed_cropped, self.breaks, self._nodata_vals)
            self._calc_sbs_coverage(sbs.data)

            sbs_lc_d = sbs.build_lcgrid(self.subwta_arc, None)

            for topaz_id, burn_class in sbs_lc_d.items():
                if burn_class in ['131', '132', '133']:
                    dom = landuse.domlc_d[topaz_id]
                    man = get_management_summary(dom, _map=landuse.mapping)
                    print(man.as_dict(), landuse.mapping)

                    if man.disturbed_class in ['forest', 'young forest']:
                        landuse.domlc_d[topaz_id] = {'131': '106', '132': '118', '133': '105'}[burn_class]

                    elif man.disturbed_class == 'shrub':
                        landuse.domlc_d[topaz_id] = {'131': '121', '132': '120', '133': '119'}[burn_class]

            landuse.dump_and_unlock()

        except Exception:
            landuse.unlock('-f')
            raise

        landuse = landuse.getInstance(wd)
        landuse.build_managements()

    def modify_soils(self):

        wd = self.wd

        ron = Ron.getInstance(wd)
        landuse = Landuse.getInstance(wd)
        soils = Soils.getInstance(wd)

        _land_soil_replacements_d = read_disturbed_land_soil_lookup(_join(_data_dir, 'disturbed_land_soil_lookup.csv'))

        try:
            soils.lock()

            for topaz_id, mukey in soils.domsoil_d.items():
                dom = landuse.domlc_d[topaz_id]
                man = get_management_summary(dom, _map=landuse.mapping)

                _soil = soils.soils[mukey]
                clay = _soil.clay
                sand = _soil.sand

                assert isfloat(clay), clay
                assert isfloat(sand), sand

                texid = simple_texture(clay=clay, sand=sand)

                key = (texid, man.disturbed_class)
                if key not in _land_soil_replacements_d:
                    continue

                disturbed_mukey = '{}-{}-{}'.format(mukey, texid, man.disturbed_class)

                if disturbed_mukey not in soils.soils:
                    disturbed_fn = disturbed_mukey + '.sol'
                    replacements = _land_soil_replacements_d[key]
                    disturbed_soil_specialization(_join(soils.soils_dir, _soil.fname),
                                                  _join(soils.soils_dir, disturbed_fn),
                                                  replacements)
                    desc = '{} - {}'.format(_soil.desc, man.disturbed_class)
                    soils.soils[disturbed_mukey] = SoilSummary(mukey=disturbed_mukey,
                                                               fname=disturbed_fn,
                                                               soils_dir=soils.soils_dir,
                                                               desc=desc,
                                                               build_date=str(datetime.now()))

                soils.domsoil_d[topaz_id] = disturbed_mukey

            # need to recalculate the pct_coverages
            watershed = Watershed.getInstance(self.wd)
            for topaz_id, k in soils.domsoil_d.items():
                if soils.soils[k].area is None:
                    soils.soils[k].area = 0.0
                soils.soils[k].area += watershed.area_of(topaz_id)

            for k in soils.soils:
                coverage = 100.0 * soils.soils[k].area / watershed.totalarea
                soils.soils[k].pct_coverage = coverage

            soils.dump_and_unlock()

        except Exception:
            soils.unlock('-f')
            raise

    def _calc_sbs_coverage(self, sbs):

        self.lock()

        try:

            topaz = Topaz.getInstance(self.wd)
            bounds, transform, proj = read_arc(topaz.bound_arc)

            assert bounds.shape == sbs.shape

            c = Counter(sbs[np.where(bounds == 1.0)])

            total_px = float(sum(c.values()))

            # todo: calcuate based on disturbed burn classes
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
