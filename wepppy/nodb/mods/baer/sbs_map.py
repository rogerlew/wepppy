from os.path import exists as _exists
from collections import Counter

import numpy as np
from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import GDT_Byte

from wepppy.all_your_base import read_arc, read_raster


class SoilBurnSeverityMap:
    def __init__(self, fname, classify):
        assert _exists(fname)
        self.fname = fname

        data, transform, proj = read_raster(fname, dtype=np.uint8)

        n, m = data.shape
        for i in range(n):
            for j in range(m):
                data[i, j] = classify(data[i, j])
                
        self.data = data
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
