# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""
python version of gdal's locationinfo with resampling:
    cubic, bicubic, near
"""

# standard library
from math import ceil, floor

# 3rd party modules
from scipy import interpolate

from osgeo import gdal
from osgeo import osr
from osgeo.gdalconst import GA_ReadOnly

import utm
from pyproj import Proj, transform


class RDIOutOfBoundsException(Exception):
    """
    location is not within map bounds
    """

    __name__ = 'RDIOutOfBoundsException'

    def __init__(self):
        pass


class RasterDatasetInterpolator:
    def __init__(self, fname, epsg=None):

        # open the image
        self.ds = ds = gdal.Open(fname, GA_ReadOnly)
        assert ds is not None
        
        self.fname = fname
        self.nbands = nbands = ds.RasterCount
        self.band = [ds.GetRasterBand(i+1) for i in range(nbands)]
        self.transform = ds.GetGeoTransform()
        self.wkt_text = ds.GetProjection()
        self.srs = srs = osr.SpatialReference()
        srs.ImportFromWkt(self.wkt_text)
        self.proj4 = srs.ExportToProj4()

        self.proj = Proj(self.proj4)
        self.wgs84 = Proj(init='EPSG:4326')
        
        self.left, self.upper = self.get_geo_coord(0, 0)
        self.right, self.lower = self.get_geo_coord(ds.RasterXSize, ds.RasterYSize)
        
        lng0, lat0 = transform(self.proj, self.wgs84, self.left, self.upper)
        _, _, self.utm_n, self.utm_h = utm.from_latlon(lat0, lng0)
        
    def get_geo_coord(self, x, y):
        assert self.transform is not None

        xorigin, xpxsize, xzero, yorigin, yzero, ypxsize = self.transform

        assert xzero == yzero == 0.0

        e = xorigin + xpxsize*x 
        n = yorigin + ypxsize*y  

        return e, n

    def get_px_coord(self, e, n):
        assert self.transform is not None
        
        xorigin, xpxsize, xzero, yorigin, yzero, ypxsize = self.transform

        assert xzero == yzero == 0.0
        
        x = (e - xorigin) / xpxsize
        y = (n - yorigin) / ypxsize

        return x, y

    def __contains__(self, en):
        e, n = en
        return self.left < e < self.right and self.lower < n < self.upper

    def get_location_info(self, lng, lat, method='cubic'):
        e, n = transform(self.wgs84, self.proj,  lng, lat)

        if not (e, n) in self:
            raise RDIOutOfBoundsException

        x, y = self.get_px_coord(e, n)
        w, h = self.ds.RasterXSize, self.ds.RasterYSize
        nbands = self.nbands
        
        if x < 0 or x > w or y < 0 or y > h:
            return float('nan')
        
        if method == 'bilinear':
            _x = [int(floor(x))-1, int(ceil(x))-1]
            if _x[0] < 0:
                _x = [0, 1]
            
            _y = [int(floor(y))-1, int(ceil(y))-1]
            if _y[0] < 0:
                _y = [0, 1]
            
            z = []
            for i in range(nbands):
                data = self.band[i].ReadAsArray(_x[0], _y[0], 2, 2)
                func = interpolate.interp2d(_x, _y, data, kind='linear')
                z.append(func(x, y)[0])
                
        elif method == 'cubic':
            xr, yr = int(round(x)), int(round(y))

            if xr - 2 < 0:
                _x = [0, 1, 2, 3, 4]
            elif xr + 2 > w:
                _x = [w-5, w-4, w-3, w-2, w-1]
            else:
                _x = [xr-3, xr-2, xr-1, xr, xr+1]
                
            if yr - 2 < 0:
                _y = [0, 1, 2, 3, 4]
            elif yr + 2 >= h:
                _y = [h-5, h-4, h-3, h-2, h-1]
            else:
                _y = [yr-3, yr-2, yr-1, yr, yr+1]
              
            z = []
            for i in range(nbands):
                data = self.band[i].ReadAsArray(_x[0], _y[0], 5, 5)
                func = interpolate.interp2d(_x, _y, data, kind='cubic')
                z.append(func(x, y)[0])
        else:
            x, y = int(round(x)), int(round(y))

            if x == w:
                x = w-1
            if y == h:
                y = h-1
            
            z = []
            for i in range(nbands):
                _z = self.band[i].ReadAsArray(x, y, 1, 1)
                if _z is not None:
                    z.append(_z[0, 0])
                else:
                    z.append(float('nan'))
        
        if nbands == 1:
            return z[0]
        return z

if __name__ == "__main__":
    #rds = RasterDatasetInterpolator('/home/weppdev/PycharmProjects/wepppy/wepppy/all_your_base/tests/8b2cd722b5444271a203229b1597b941.nc4')
    rds = RasterDatasetInterpolator('/geodata/ESDAC_ESDB_rasters/usedo.tif')
    data = rds.get_location_info(lng=-7.915447803023927, lat=43.528076324743296, method='near')
    print(data)