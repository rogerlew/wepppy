# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import exists as _exists
from collections import Counter

import numpy as np
from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import GDT_Byte

from collections import Counter

from wepppy.all_your_base.geo import read_raster

from wepppy.landcover import LandcoverMap


def get_sbs_color_table(fn):
    ds = gdal.Open(fn)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
    counts = Counter(list(data.flatten())).most_common()

    ct = band.GetRasterColorTable()
    if ct is None:
        return None, counts

    d = dict(unburned=[], low=[], mod=[], high=[])
    for i in range(ct.GetCount()):
        entry = [int(v) for v in ct.GetColorEntry(i)]

        if entry[:3] == [0, 100, 0]:
            d['unburned'].append(i)
        elif entry[:3] == [0, 115, 74]:
            d['unburned'].append(i)
        elif entry[:3] == [127, 255, 212]:
            d['low'].append(i)
        elif entry[:3] == [77, 230, 0]:
            d['low'].append(i)
        elif entry[:3] == [255, 255, 0]:
            d['mod'].append(i)
        elif entry[:3] == [255, 0, 0]:
            d['high'].append(i)
    
    ds = None

    return d, counts


def _ct_classify(v, ct, offset=0, nodata_val=255):
    for i, burn_class in enumerate(['unburned', 'low', 'mod', 'high']):
        for k in ct[burn_class]:
            if k == v:
                return i + offset
               
    return nodata_val


def _classify(v, breaks, nodata_vals, offset=0, nodata_val=255):
    i = 0

    if nodata_vals is not None:
        if v in np.array(nodata_vals):
            return nodata_val

    for i, brk in enumerate(breaks):
        if v <= brk:
            break
    return i + offset



class SoilBurnSeverityMap(LandcoverMap):
    def __init__(self, fname, breaks=None, nodata_vals=None):
        
        if nodata_vals is None:
            nodata_vals = []

            ds = gdal.Open(fname)
            band = ds.GetRasterBand(1)
            _nodata = band.GetNoDataValue()
            ds = None

            if _nodata is not None:
                nodata_vals.append(_nodata)

        assert _exists(fname)
        self.fname = fname

        self.ct, self.counts = get_sbs_color_table(fname)
        ct = self.ct

        if breaks is None:
            vals = set(v for v, c in self.counts)
            for k in [15, 255]:
                if k in vals:
                    nodata_vals.append(k)
                    vals.remove(k)
            if max(vals) == 3:
                breaks = [0, 1, 2, max(vals)]
            else:
                breaks = [1, 2, 3, max(vals)]  
        
        data, transform, proj = read_raster(fname, dtype=np.uint8)
        n, m = data.shape

        if ct is None:
            for i in range(n):
                for j in range(m):
                    data[i, j] = _classify(data[i, j], breaks, 
                                           nodata_vals, offset=130, 
                                           nodata_val=130)
        else:
            for i in range(n):
                for j in range(m):
                    data[i, j] = _ct_classify(data[i, j], ct, 
                                              offset=130, nodata_val=130)
        
        self.breaks = breaks
        self.data = data
        self.transform = transform
        self.proj = proj
        self.mukeys = list(set(self.data.flatten()))
        self.fname = fname
        self.nodata_vals = nodata_vals

    def export_4class_map(self, fn, cellsize=None):

        if cellsize is None:
            transform = self.transform
            assert transform[1] == abs(transform[5])
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
                    data[i, j] = _classify(_data[i, j], self.breaks, self.nodata_vals)
        else:
            for i in range(n):
                for j in range(m):
                    data[i, j] = _ct_classify(_data[i, j], ct)
        
        num_cols, num_rows = _data.shape
        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(fn, num_cols, num_rows,
                            1, GDT_Byte)

        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj)
        wkt = srs.ExportToWkt()

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform)
        band = dst.GetRasterBand(1)
        band.WriteArray(data.T)
        band.SetNoDataValue(255)

        color_table = gdal.ColorTable()
        color_table.SetColorEntry(0, (0, 100, 0, 255))  # unburned
        color_table.SetColorEntry(1, (127, 255, 212, 255))  # low
        color_table.SetColorEntry(2, (255, 255, 0, 255))  # moderate
        color_table.SetColorEntry(3, (255, 0, 0, 255))  # high
        color_table.SetColorEntry(255, (255, 255, 255, 0))  # n/a
        band.SetColorTable(color_table)

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
