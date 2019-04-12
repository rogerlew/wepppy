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

from wepppy.all_your_base import read_arc, read_raster


class SoilBurnSeverityMap:
    def __init__(self, fname, breaks, nodata_vals=None):

        def _classify(v, breaks, nodata_vals):
            i = 0

            if nodata_vals is not None:
                if v in nodata_vals:
                    return 130

            for i, brk in enumerate(breaks):
                if v <= brk:
                    break
            return i + 130

        assert _exists(fname)
        self.fname = fname

        data, transform, proj = read_raster(fname, dtype=np.uint8)

        n, m = data.shape
        for i in range(n):
            for j in range(m):
                data[i, j] = _classify(data[i, j], breaks, nodata_vals)
                
        self.data = data
        self.breaks = breaks
        self.nodata_vals = nodata_vals
        self.transform = transform
        self.proj = proj
        self.mukeys = list(set(self.data.flatten()))
        self.fname = fname

    def _get_dominant(self, indices):
        x = self.data[indices]
        return int(Counter(x).most_common()[0][0])
        
    def build_lcgrid(self, subwta_fn, lcgrid_fn=None):
        """
        Generates a dominant lc map based on the subcatchment
        ids identified in the subwta_fn map
        """
        assert _exists(subwta_fn)
        subwta, transform, proj = read_arc(subwta_fn, dtype=np.int32)
        _ids = sorted(list(set(subwta.flatten())))
        
        lcgrid = np.zeros(subwta.shape, np.int32)
        domlc_d = {}
        for _id in _ids:
            if _id == 0:
                continue
                
            _id = int(_id)
            indices = np.where(subwta == _id)
            dom = self._get_dominant(indices)
            lcgrid[indices] = dom
                
            domlc_d[str(_id)] = str(dom)
            
        if lcgrid_fn is not None:
            # initialize raster
            num_cols, num_rows = lcgrid.shape
            driver = gdal.GetDriverByName("GTiff")
            dst = driver.Create(lcgrid_fn, num_cols, num_rows,
                                1, GDT_Byte)

            srs = osr.SpatialReference()
            srs.ImportFromProj4(proj)
            wkt = srs.ExportToWkt()

            dst.SetProjection(wkt)
            dst.SetGeoTransform(transform)
            band = dst.GetRasterBand(1)
            band.WriteArray(lcgrid)
            del dst
            
            assert _exists(lcgrid_fn)
            
        return domlc_d

    def export_4class_map(self, fn):

        fname = self.fname
        assert _exists(fname)

        def _classify(v, breaks, nodata_vals):
            i = 0

            if nodata_vals is not None:
                if v in nodata_vals:
                    return 255

            for i, brk in enumerate(breaks):
                if v <= brk:
                    break

            return i + 1

        _data, transform, proj = read_raster(fname, dtype=np.uint8)
        print(proj)
        data = np.ones(_data.shape) * 255
        n, m = _data.shape
        for i in range(n):
            for j in range(m):
                data[i, j] = _classify(_data[i, j], self.breaks, self.nodata_vals)

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
        del dst

        assert _exists(fn)


if __name__ == "__main__":
    sbs_fn = '/home/weppdev/PycharmProjects/wepppy/wepppy/nodb/mods/baer/test/Rattlesnake.tif'
    sbs = SoilBurnSeverityMap(sbs_fn, [0, 75, 109, 187])
    sbs.export_4class_map(sbs_fn.replace('.tif', '.4class.tif'))
