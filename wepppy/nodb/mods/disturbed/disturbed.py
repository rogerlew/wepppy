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
from copy import deepcopy

import math
import numpy as np
from osgeo import gdal

from deprecated import deprecated

from wepppy.all_your_base import isint, isfloat
from wepppy.all_your_base.geo import wgs84_proj4, read_raster, haversine
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture, WeppSoilUtil, SoilMultipleOfeSynth

from ...landuse import Landuse, LanduseMode
from ...soils import Soils
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...prep import Prep
from ...base import NoDbBase, TriggerEvents
from ..baer.sbs_map import SoilBurnSeverityMap

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


@deprecated
def disturbed_soil_specialization(src, dst, replacements, h0_min_depth=None, h0_max_om=None):
    """
    Creates a new soil file based on soil_in_fname and makes replacements
    from the provided replacements dictionary
    """

    # TODO: Implement 7777/7778 YamlSoil and use YamlSoil to 
    # specialize soils instead of all this text processing nonsense.

    # read the soil_in_fname file
    with open(src) as f:
        lines = f.readlines()

    header = [L for L in lines if L.startswith('#')]
    header.append('# nodb.disturbed:disturbed_soil_specialization({})\n'.format(repr(replacements)))

    lines = [L for L in lines if not L.startswith('#')]

    pre7777 = lines[0].startswith('9') or lines[0].startswith('2006')
    line4 = lines[3]
    line4 = line4.split()
    line4[-4] = _replace_parameter(line4[-4], replacements['ki'])
    line4[-3] = _replace_parameter(line4[-3], replacements['kr'])
    line4[-2] = _replace_parameter(line4[-2], replacements['shcrit'])
    line4 = ' '.join(line4) + '\n'

    line5 = lines[4]
    line5 = line5.split()
    if h0_min_depth is not None:
        if float(line5[0]) < h0_min_depth:
            line5[0] = str(h0_min_depth)
    line5[2] = _replace_parameter(line5[2], replacements['avke'])
    h0_om = None
    if not pre7777:
        h0_om = float(line5[8])
 
    if len(line5) < 5:  # no horizons (e.g. rock)
        shutil.copyfile(src, dst)
        return

    # Don't really like this. This is getting messy
    if not pre7777:
        # make the layers easier to read by making cols fixed width
        # aligning to the right.
        line5 = '{0:>9}\t{1:>8}\t{2:>9}\t'\
                '{3:>5}\t{4:>9}\t{5:>9}\t'\
                '{6:>7}\t{7:>7}\t{8:>7}\t'\
                '{9:>7}\t{10:>7}'.format(*line5)
         
        line5 = '\t' + line5 + '\n'
    else:
        line5 = '\t' + '\t'.join(line5) + '\n'

    # for all horizons < 200 m replace avke
    for i in range(5, len(lines)):
        _line = lines[i].split()
        if len(_line) == 11:
            if float(_line[0]) <= 200:
                _line[2] = _replace_parameter(_line[2], replacements['avke'])

                # messy
                if not pre7777:
                    _line = '{0:>9}\t{1:>8}\t{2:>9}\t'\
                            '{3:>5}\t{4:>9}\t{5:>9}\t'\
                            '{6:>7}\t{7:>7}\t{8:>7}\t'\
                            '{9:>7}\t{10:>7}'.format(*_line)         
                    lines[i] = '\t' + _line + '\n'
                else:
                    lines[i] + '\t' + '\t'.join(_line) + '\n'

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

        if h0_max_om is not None:
            if h0_om < h0_max_om:
                f.writelines(line5)
        else:
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

            shutil.copyfile(_join(_data_dir, 'disturbed_land_soil_lookup.csv'),
                            self.lookup_fn)

            self.sbs_coverage = None
            self._h0_max_om = self.config_get_float('disturbed', 'h0_max_om')
            self._sol_ver = self.config_get_float('disturbed', 'sol_ver')
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
    def sbs_4class_path(self):
        return _join(self.disturbed_dir, 'sbs_4class.tif')

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

        cmd = ['gdaldem', 'color-relief', '-of', 'VRT',  
               self.disturbed_wgs, self.color_tbl_path, disturbed_rgb]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        disturbed_rgb_png = self.disturbed_rgb_png
        if _exists(disturbed_rgb_png):
            os.remove(disturbed_rgb_png)

        cmd = ['gdal_translate', '-of', 'PNG', disturbed_rgb, disturbed_rgb_png]
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

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('landuse_map')
            prep.has_sbs = True
        except FileNotFoundError:
            pass

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

            is256 = len(classes) > 7 or max(classes) >= 255

            if is256:
                breaks = [75, 109, 187, max(counts)]
            else:
                if max(counts) == 3:
                    breaks = [0, 1, 2, max(counts)]
                else:
                    breaks = [1, 2, 3, max(counts)]

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

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('landuse_map')
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    def on(self, evt):
        multi_ofe = self.multi_ofe

        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            if multi_ofe:
                self.remap_mofe_landuse()
            else:
                self.remap_landuse()
                self.spatialize_treecanopy()

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
        assert landuse.mode != LanduseMode.Single

        watershed = Watershed.getInstance(wd)

        sbs = self.get_sbs()

        if sbs is None:
            return

        # noinspection PyBroadException
        try:
            landuse.lock()

            self._calc_sbs_coverage(sbs)

            sbs_lc_d = sbs.build_lcgrid(watershed.subwta, None)

            for topaz_id, burn_class in sbs_lc_d.items():
                dom = landuse.domlc_d[topaz_id]
                man = landuse.managements[dom]

                # TODO: probably a better way to do this based on the disturbed_class
                if burn_class in ['131', '132', '133']:
                    if man.disturbed_class in ['forest', 'young forest']:
                        landuse.domlc_d[topaz_id] = {'131': '106', '132': '118', '133': '105'}[burn_class]

                    elif man.disturbed_class == 'shrub':
                        landuse.domlc_d[topaz_id] = {'131': '121', '132': '120', '133': '119'}[burn_class]

                    elif man.disturbed_class in ['short grass', 'tall grass']:
                        landuse.domlc_d[topaz_id] = {'131': '131', '132': '130', '133': '129'}[burn_class]

            landuse.dump_and_unlock()

        except Exception:
            landuse.unlock('-f')
            raise

        landuse = landuse.getInstance(wd)
        landuse.build_managements()

    def remap_mofe_landuse(self):
        wd = self.wd

        landuse = Landuse.getInstance(wd)
        assert landuse.mode != LanduseMode.Single

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

                    print(f'mofe:: {dom} {burn_class}')

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
        return _join(self.disturbed_dir, 'disturbed_land_soil_lookup.csv')

    @property
    def land_soil_replacements_d(self):
        default_fn = _join(_data_dir, 'disturbed_land_soil_lookup.csv')

        _lookup_fn = self.lookup_fn
        if not _exists(_lookup_fn):
            shutil.copyfile(default_fn, _lookup_fn)

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

        n = len(landuse.domlc_d)

        with open(_join(wepp.runs_dir, 'pmetpara.txt'), 'w') as fp:
            fp.write('{n}\n'.format(n=n))

            for i, (topaz_id, mukey) in enumerate(soils.domsoil_d.items()):
                dom = landuse.domlc_d[topaz_id]
                man_summary = landuse.managements[dom]
                man = man_summary.get_management() 

                _soil = soils.soils[mukey]
                clay = _soil.clay
                sand = _soil.sand

                assert isfloat(clay), clay
                assert isfloat(sand), sand

                texid = simple_texture(clay=clay, sand=sand)
                disturbed_class = man_summary.disturbed_class
                if disturbed_class is None:
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
            for topaz_id, k in soils.domsoil_d.items():
                if soils.soils[k].area is None:
                    soils.soils[k].area = 0.0
                soils.soils[k].area += watershed.area_of(topaz_id)

            for k in soils.soils:
                coverage = 100.0 * soils.soils[k].area / watershed.wsarea
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
                dom = landuse.domlc_d[topaz_id]
                man = landuse.managements[dom] 

                _soil = soils.soils[mukey]
                clay = _soil.clay
                sand = _soil.sand

                assert isfloat(clay), clay
                assert isfloat(sand), sand

                texid = simple_texture(clay=clay, sand=sand)

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
            for topaz_id, k in soils.domsoil_d.items():
                if soils.soils[k].area is None:
                    soils.soils[k].area = 0.0
                soils.soils[k].area += watershed.area_of(topaz_id)

            for k in soils.soils:
                coverage = 100.0 * soils.soils[k].area / watershed.wsarea
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
                    'noburn': 100.0,
                    'low': 0.0,
                    'moderate': 0.0,
                    'high': 0.0
                }
            else:
                watershed = Watershed.getInstance(self.wd)
                bounds, transform, proj = read_raster(watershed.bound)

                assert bounds.shape == sbs.data.shape

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
