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

import numpy as np

from osgeo import gdal
from osgeo import osr
from osgeo.gdalconst import GA_ReadOnly

# import numpy as np

import utm

from .geo_transformer import GeoTransformer

wgs84_proj4 = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'


class RDIOutOfBoundsException(Exception):
    """
    location is not within map bounds
    """

    __name__ = 'RDIOutOfBoundsException'

    def __init__(self):
        pass


class RasterDatasetInterpolator:
    def __init__(self, fname, proj=None):
        self.lon_lat = False
        if fname.endswith('.nc'):
            import netCDF4
            nc = netCDF4.Dataset(fname)
            name = list(nc.variables.keys())[0]
            var = nc.variables[name]

            if not ('lat' in var.dimensions[-2].lower() and 'lon' in var.dimensions[-1]):
                self.lon_lat = True

        # open the image
        self.ds = ds = gdal.Open(fname, GA_ReadOnly)
        assert ds is not None, fname

        self.fname = fname
        self.nbands = nbands = ds.RasterCount
        self.band = [ds.GetRasterBand(i + 1) for i in range(nbands)]
        self.no_data_values = [band.GetNoDataValue() for band in self.band]
        self.transform = ds.GetGeoTransform()

        self.wkt_text = ds.GetProjection()
        self.srs = srs = osr.SpatialReference()
        srs.ImportFromWkt(self.wkt_text)
        self.proj4 = srs.ExportToProj4()

        if proj is not None:
            self.proj4 = proj

        if self.lon_lat:
            self.upper, self.left = self.get_geo_coord(ds.RasterXSize, ds.RasterYSize)
            self.lower, self.right = self.get_geo_coord(0, 0)
        else:
            self.left, self.upper = self.get_geo_coord(0, 0)
            self.right, self.lower = self.get_geo_coord(ds.RasterXSize, ds.RasterYSize)

        self.proj2wgs_transformer = proj2wgs_transformer = \
            GeoTransformer(src_proj4=self.proj4, dst_proj4=wgs84_proj4)

        lng0, lat0 = proj2wgs_transformer.transform(self.left, self.upper)
        _, _, self.utm_n, self.utm_h = utm.from_latlon(lat0, lng0)
        
    def get_geo_coord(self, x, y):
        assert self.transform is not None

        xorigin, xpxsize, xzero, yorigin, yzero, ypxsize = self.transform

        assert xzero == yzero == 0.0

        e = xorigin + xpxsize*x 
        n = yorigin + ypxsize*y  

        return e, n

    def get_px_coord_from_lnglat(self, lng, lat):
        proj2wgs_transformer = self.proj2wgs_transformer

        e, n = proj2wgs_transformer.reverse(lng, lat)
        px, py = self.get_px_coord(e, n)
        return int(px), int(py)

    def get_px_coord(self, e, n):
        assert self.transform is not None
        
        xorigin, xpxsize, xzero, yorigin, yzero, ypxsize = self.transform

        assert xzero == yzero == 0.0
        
        x = (e - xorigin) / xpxsize
        y = (n - yorigin) / ypxsize

        return x, y

    def get_nodata_value(self, band):
        return self.band[band].GetNoDataValue()

    @property
    def gt0_centroid(self):
        data = self.band[0].ReadAsArray(0,0, self.ds.RasterXSize, self.ds.RasterYSize) 
        y = np.zeros(data.shape)
        y[data > 0] = 1
        px, py = np.argwhere(y == 1).sum(0)/y.sum()
        e, n = self.get_geo_coord(px, py)
        lng, lat = self.proj2wgs_transformer.transform(e, n)
        return lng, lat

    @property
    def extent(self):
        proj2wgs_transformer = self.proj2wgs_transformer
        xmin, ymin = proj2wgs_transformer.transform(self.left, self.lower)
        xmax, ymax = proj2wgs_transformer.transform(self.right, self.upper)
        return xmin, ymin, xmax, ymax

    @property
    def width(self):
        return self.ds.RasterXSize

    @property
    def height(self):
        return self.ds.RasterYSize

    def __contains__(self, en):
        e, n = en
        return self.left < e < self.right and self.lower < n < self.upper

    def get_location_info(self, lng, lat, method='cubic'):
        proj2wgs_transformer = self.proj2wgs_transformer
        e, n = proj2wgs_transformer.reverse(lng, lat)

        if not (e, n) in self:
            raise RDIOutOfBoundsException

        x, y = self.get_px_coord(e, n)
        w, h = self.ds.RasterXSize, self.ds.RasterYSize
        nbands = self.nbands
        
        if x < 0 or x > w or y < 0 or y > h:
            return float('naan')
        
        if method == 'bilinear':
            _x = [int(floor(x))-1, int(ceil(x))-1]
            if _x[0] < 0:
                _x = [0, 1]
            
            _y = [int(floor(y))-1, int(ceil(y))-1]
            if _y[0] < 0:
                _y = [0, 1]
            
            z = []
            for i in range(nbands):
                _data = self.band[i].ReadAsArray(_x[0], _y[0], 2, 2)
                # RL- interploate.interp2d seems to ignore masked values
                # nodata = self.band[i].GetNoDataValue()
                # if nodata is not None:
                #     data = np.ma.masked_values(data, nodata)
                func = interpolate.interp2d(_x, _y, _data, kind='linear')
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
                _data = self.band[i].ReadAsArray(_x[0], _y[0], 5, 5)
                # nodata = self.band[i].GetNoDataValue()
                # if nodata is not None:
                #     data = np.ma.masked_values(data, nodata)
                try:
                    func = interpolate.interp2d(_x, _y, _data, kind='cubic')
                    z.append(func(x, y)[0])
                except:
                    return self.get_location_info(lng, lat, method='near')
        else:
            x, y = int(round(x)), int(round(y))

            if x == w:
                x = w-1
            if y == h:
                y = h-1
            
            z = []
            for i in range(nbands):
                _z = self.band[i].ReadAsArray(x, y, 1, 1)
                nodata = self.no_data_values[i]  # Get the NoData value for the current band
                if _z is not None:
                    if nodata is not None and _z[0, 0] == nodata:  # Check if the pixel value matches the NoData value
                        z.append(None)
                    else:
                        z.append(_z[0, 0])
                else:
                    z.append(None)
        
        if nbands == 1:
            return z[0]
        return z
