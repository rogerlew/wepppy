# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from collections import Counter

from functools import lru_cache

import numpy as np
from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import GDT_Byte

from subprocess import Popen, PIPE

from wepppy.all_your_base import isint
from wepppy.all_your_base.geo import read_raster, wgs84_proj4, validate_srs

from wepppy.landcover import LandcoverMap


def get_sbs_color_table(fn, color_to_severity_map=None):
    ds = gdal.Open(fn)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
    counts = Counter(list(data.flatten())).most_common()

    if color_to_severity_map is None:
        color_to_severity_map = dict([((0, 100, 0), 'unburned'),
                                      ((0, 0, 0), 'unburned'),
                                      ((0, 115, 74), 'unburned'),
                                      ((0, 175, 166), 'unburned'),
                                      ((102, 204, 204), 'low'),
                                      ((102, 205, 205), 'low'),
                                      ((115, 255, 223), 'low'),
                                      ((127, 255, 212), 'low'),
                                      ((0, 255, 255), 'low'),
                                      ((102, 205, 205), 'low'),
                                      ((77, 230, 0), 'low'),
                                      ((255, 255, 0), 'mod'),
                                      ((255, 232, 32), 'mod'),
                                      ((255, 0, 0), 'high')])

    ct = band.GetRasterColorTable()
    if ct is None:
        return None, counts, None

    color_map = {}
    d = dict(unburned=[], low=[], mod=[], high=[])
    for i in range(ct.GetCount()):
        entry = [int(v) for v in ct.GetColorEntry(i)]
        entry = tuple(entry[:3])

        color_map[entry] = sev = color_to_severity_map.get(entry, None)

        if sev is not None and sev != "":
            d[sev].append(i)

    ds = None

    return d, counts, color_map

def make_hashable(v, breaks, nodata_vals, offset, nodata_val):
    return (v, tuple(breaks), tuple(nodata_vals) if nodata_vals is not None else None, offset, nodata_val)

@lru_cache(maxsize=None)
def memoized_classify(args):
    v, breaks, nodata_vals, offset, nodata_val = args
    return _classify(v, breaks, nodata_vals, offset, nodata_val)


def _classify(v, breaks, nodata_vals, offset=0, nodata_val=255):
    i = 0

    if nodata_vals is not None:
        for _no_data in nodata_vals:
            if int(v) == int(_no_data):
                return i + offset

    for i, brk in enumerate(breaks):
        if v <= brk:
            break
    return i + offset

def classify(v, breaks, nodata_vals=None, offset=0, nodata_val=255):
    args = make_hashable(v, breaks, nodata_vals, offset, nodata_val)
    return memoized_classify(args)


def make_hashable_ct(v, ct, offset, nodata_val):
    ct_tuple = tuple((key, tuple(values)) for key, values in ct.items())
    return (v, ct_tuple, offset, nodata_val)

@lru_cache(maxsize=None)
def memoized_ct_classify(args):
    v, ct, offset, nodata_val = args
    ct_dict = {key: list(values) for key, values in ct}
    return _ct_classify(v, ct_dict, offset, nodata_val)

def _ct_classify(v, ct, offset=0, nodata_val=255):
    for i, burn_class in enumerate(['unburned', 'low', 'mod', 'high']):
        for k in ct[burn_class]:
            if k == v:
                return i + offset
    return nodata_val

def ct_classify(v, ct, offset=0, nodata_val=255):
    args = make_hashable_ct(v, ct, offset, nodata_val)
    return memoized_ct_classify(args)

def sbs_map_sanity_check(fname):
    if not _exists(fname):
        return 1, 'File does not exist'

    if not validate_srs(fname):
        return 1, 'Map contains an invalid projection. Try reprojecting to UTM.'

    ds = gdal.Open(fname)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
    classes = np.unique(data)
    ds = None

    if len(classes) > 256:
        return 1, 'Map has more than 256 classes'

    for v in classes:
        if not isint(v):
            return 1, 'Map has non-integer classes'

    ct, counts, color_map = get_sbs_color_table(fname, color_to_severity_map=None)
    if ct is not None:
        for entry, sev in color_map.items():
            if sev in ('low', 'mod', 'high'):
                return 0, 'Map has valid color table'

        return 1, 'Map has no valid color table'

    return 0, 'Map has valid classes'

    
class SoilBurnSeverityMap(LandcoverMap):
    def __init__(self, fname, breaks=None, nodata_vals=None, color_map=None, ignore_ct=False):
        if isinstance(nodata_vals, str):
            raise ValueError('nodata_vals should be a None or list, not a string')

        if nodata_vals is None:
            nodata_vals = []

            ds = gdal.Open(fname)
            band = ds.GetRasterBand(1)
            _nodata = band.GetNoDataValue()
            ds = None

            if _nodata is not None:
                if isint(_nodata):
                    nodata_vals.append(int(_nodata))
                else:
                    nodata_vals.append(_nodata)

        assert _exists(fname)

        ct, counts, color_map = get_sbs_color_table(fname, color_to_severity_map=color_map)
        if ignore_ct:
            ct = None

        classes = set()
        for v, c in counts:
            if isint(v):
                if isinstance(nodata_vals, list):
                    if int(v) in nodata_vals:
                        continue
                classes.add(int(v))
            else:
                if isinstance(nodata_vals, list):
                    if v in nodata_vals:
                        continue
                classes.add(v)

        is256 = None

        classes = sorted(classes)
        if ct is None:
            if breaks is None:
                # need to intuit breaks

                min_val = min(classes)
                max_val = max(classes)

                run = 1
                max_run_val = min_val
                while min_val + run in classes:
                    max_run_val = min_val + run
                    run += 1

                is256 = run > 5 or len(classes) > 7

                if is256:
                    breaks = [0, 75, 109, 187]
                else:
                    breaks = [max_run_val - i for i in range(3, -1, -1)]

                if max_val not in breaks and not is256 and max_val-1 not in classes:
                    nodata_vals.append(max_val)
                    classes.remove(max_val)

        else:
            breaks = None

        self.ct = ct
        self.is256 = bool(is256)
        self.classes = classes
        self.counts = counts
        self.color_map = color_map
        self.breaks = breaks
        self._data = None
        self.fname = fname
        self.nodata_vals = nodata_vals

    @property
    def transform(self):
        data, transform, proj = read_raster(self.fname, dtype=np.uint8)
        return transform

    @property
    def proj(self):
        data, transform, proj = read_raster(self.fname, dtype=np.uint8)
        return proj

    @property
    def burn_class_counts(self):
        # Using a Counter to sum the counts based on severity
        counter = Counter()
        for _, severity, count in self.class_map:
            counter[severity] += count
        return dict(counter)

    @property
    def data(self):
        if self._data is not None:
            return self._data

        fname = self.fname
        ct = self.ct
        breaks = self.breaks
        nodata_vals = self.nodata_vals

        data, transform, proj = read_raster(fname, dtype=np.uint8)
        n, m = data.shape

        if ct is None:
            for brk in breaks:
                assert isint(brk), breaks

            assert breaks is not None, breaks
            for i in range(n):
                for j in range(m):
                    data[i, j] = classify(data[i, j], breaks,
                                           nodata_vals, offset=130,
                                           nodata_val=130)
        else:
            for i in range(n):
                for j in range(m):
                    data[i, j] = ct_classify(data[i, j], ct,
                                              offset=130,
                                              nodata_val=130)

        self._data = data
        return data

    def export_wgs_map(self, fn):
        ds = gdal.Open(self.fname)
        assert ds is not None
        del ds

        # transform to WGS1984 to display on map
        if _exists(fn):
            os.remove(fn)

        cmd = ['gdalwarp', '-t_srs', wgs84_proj4,
               '-r', 'near', self.fname, fn]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(fn), ' '.join(cmd)

        ds = gdal.Open(fn)
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

        return [[sw_y, sw_x], [ne_y, ne_x]]

    @property
    def class_map(self):
        ct = self.ct
        breaks = self.breaks
        nodata_vals = self.nodata_vals

        _map = dict([('255', 'No Data'),
                     ('130', 'No Burn'),
                     ('131', 'Low Severity Burn'),
                     ('132', 'Moderate Severity Burn'),
                     ('133', 'High Severity Burn')])

        class_map = []
        for v, cnt in self.counts:
            if ct is None:
                k = classify(v, breaks, nodata_vals, offset=130, nodata_val=255)
            else:
                k = ct_classify(v, ct, offset=130, nodata_val=255)

            sev = _map[str(k)]
            class_map.append((int(v), sev, cnt))

        return sorted(class_map, key=lambda x: x[0])

    @property
    def class_pixel_map(self):
        ct = self.ct
        breaks = self.breaks
        nodata_vals = self.nodata_vals

        class_map = {}
        for v, cnt in self.counts:
            if ct is None:
                k = classify(v, breaks, nodata_vals, offset=130, nodata_val=255)
            else:
                k = ct_classify(v, ct, offset=130, nodata_val=255)

            _v = str(v)
            if _v.endswith('.0'):
                _v = _v[:-2]
            class_map[_v] = str(k)

        return class_map

    def _write_color_table(self, color_tbl_path):
        ct = self.ct

        if ct is None:
            breaks = self.breaks
            nodata_vals = self.nodata_vals

            _map = dict([('255', '0 0 0 0'),
                         ('130', '0 115 74 255'),
                         ('131', '77 230 0 255'),
                         ('132', '255 255 0 255'),
                         ('133', '255 0 0 255')])

            with open(color_tbl_path, 'w') as fp:
                for v, cnt in self.counts:
                    k = classify(v, breaks, nodata_vals, offset=130,  nodata_val=255)
                    fp.write('{} {}\n'.format(v, _map[str(k)]))
                fp.write("nv 0 0 0 0\n")
        else:
            _map = dict([('nv', '0 0 0 0'),
                         ('unburned', '0 115 74 255'),
                         ('low', '77 230 0 255'),
                         ('mod', '255 255 0 255'),
                         ('high', '255 0 0 255')])

            d = {}
            for burn_class in ct:
                color = _map[burn_class]
                for px in ct[burn_class]:
                    d[int(px)] = color

            with open(color_tbl_path, 'w') as fp:
                for v, color in sorted(d.items()):
                    fp.write(f'{v} {color}\n')
                fp.write("nv 0 0 0 0\n")


    def export_rgb_map(self, wgs_fn, fn, rgb_png):
        head, tail = _split(fn)

        color_tbl_path = _join(head, 'color_table.txt')
        self._write_color_table(color_tbl_path)

        disturbed_rgb = fn
        if _exists(disturbed_rgb):
            os.remove(disturbed_rgb)

        cmd = ['gdaldem', 'color-relief', '-of', 'VRT', '-alpha',
               wgs_fn, color_tbl_path, disturbed_rgb]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(disturbed_rgb), ' '.join(cmd)

        disturbed_rgb_png = rgb_png
        if _exists(disturbed_rgb_png):
            os.remove(disturbed_rgb_png)

        cmd = ['gdal_translate', '-of', 'PNG', disturbed_rgb, disturbed_rgb_png]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(disturbed_rgb_png), ' '.join(cmd)


    def export_4class_map(self, fn, cellsize=None):
        if cellsize is None:
            transform = self.transform
            assert round(transform[1], 1) == round(abs(transform[5]), 1)
            cellsize = transform[1]

        fname = self.fname
        assert _exists(fname)

        ct = self.ct

        _data, transform, proj = read_raster(fname, dtype=np.uint8)
        data = np.ones(_data.shape) * 255
        n, m = _data.shape

        if ct is None:
            for i in range(n):
                for j in range(m):
                    data[i, j] = classify(_data[i, j], self.breaks, self.nodata_vals)
        else:
            for i in range(n):
                for j in range(m):
                    data[i, j] = ct_classify(_data[i, j], ct)

        src_ds = gdal.Open(fname)
        wkt = src_ds.GetProjection()

        num_cols, num_rows = _data.shape
        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(fn, num_cols, num_rows,
                            1, GDT_Byte,
                            ["COMPRESS=LZW", "PHOTOMETRIC=PALETTE"])

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform)
        band = dst.GetRasterBand(1)

        color_table = gdal.ColorTable()
        color_table.SetColorEntry(0, (0, 100, 0, 255))  # unburned
        color_table.SetColorEntry(1, (127, 255, 212, 255))  # low
        color_table.SetColorEntry(2, (255, 255, 0, 255))  # moderate
        color_table.SetColorEntry(3, (255, 0, 0, 255))  # high
        color_table.SetColorEntry(255, (255, 255, 255, 0))  # n/a
        band.SetColorTable(color_table)
        band.SetNoDataValue(255)

        band.WriteArray(data.T)

        del dst

        assert _exists(fn)


if __name__ == "__main__":
    import sys
    print(sys.argv)
    assert len(sys.argv) >= 3
    sbs_fn = sys.argv[-2]
    dst_fn = sys.argv[-1]

    sbs = SoilBurnSeverityMap(sbs_fn)
    sbs.export_4class_map(dst_fn)
