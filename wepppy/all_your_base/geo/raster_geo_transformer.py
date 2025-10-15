import shutil
from os.path import exists as _exists

from osgeo import gdal, osr
import numpy as np

import utm

from ..all_your_base import isfloat
from .geo import get_utm_zone, utm_srid, wgs84_proj4
from .geo_transformer import GeoTransformer

gdal.UseExceptions()


class UtmGeoTransformer:
    def __init__(self, raster_fn):
        """
        provide a path to a directory to store the taudem files a
        path to a dem
        """

        # verify the dem exists
        if not _exists(raster_fn):
            raise Exception('raster_fn "%s" does not exist' % raster_fn)

        self.raster_fn = raster_fn

        # open the dataset
        ds = gdal.Open(raster_fn)

        # read and verify the num_cols and num_rows
        num_cols = ds.RasterXSize
        num_rows = ds.RasterYSize

        if num_cols <= 0 or num_rows <= 0:
            raise Exception('input is empty')

        # read and verify the _transform
        _transform = ds.GetGeoTransform()

        if abs(_transform[1]) != abs(_transform[5]):
            raise Exception('input cells are not square')

        cellsize = abs(_transform[1])
        ul_x = int(round(_transform[0]))
        ul_y = int(round(_transform[3]))

        lr_x = ul_x + cellsize * num_cols
        lr_y = ul_y - cellsize * num_rows

        ll_x = int(ul_x)
        ll_y = int(lr_y)

        # read the projection and verify dataset is in utm
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjectionRef())

        datum, utm_zone, hemisphere = get_utm_zone(srs)
        if utm_zone is None:
            raise Exception('input is not in utm')

        # get band
        band = ds.GetRasterBand(1)

        # get band dtype
        dtype = gdal.GetDataTypeName(band.DataType)

        # extract min and max elevation
        stats = band.GetStatistics(True, True)
        min_value = stats[0]
        max_value = stats[1]

        # store the relevant variables to the class
        self.transform = _transform
        self.num_cols = num_cols
        self.num_rows = num_rows
        self.cellsize = cellsize
        self.ul_x = ul_x  # in utm
        self.ul_y = ul_y
        self.lr_x = lr_x
        self.lr_y = lr_y
        self.ll_x = ll_x
        self.ll_y = ll_y

        self.dtype = dtype
        self.datum = datum
        self.hemisphere = hemisphere
        self.northern = northern = hemisphere == 'N'
        self.epsg = utm_srid(utm_zone, hemisphere)
        self.utm_zone = utm_zone
        self.srs_proj4 = srs.ExportToProj4()

        wgs_lr_y, wgs_ul_x = utm.to_latlon(easting=ul_x, northing=lr_y, zone_number=utm_zone, northern=northern)
        wgs_ul_y, wgs_lr_x = utm.to_latlon(easting=lr_x, northing=ul_y, zone_number=utm_zone, northern=northern)
        self.extent = wgs_ul_x, wgs_lr_y, wgs_lr_x, wgs_ul_y  # xmin, ymin, xmax, ymax

        srs.MorphToESRI()
        self.srs_wkt = srs.ExportToWkt()
        self.min_value = min_value
        self.max_value = max_value

        del ds

    def utm_to_px(self, easting, northing):
        """
        return the utm coords from pixel coords
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        if isfloat(easting):
            x = int(round((easting - ul_x) / cellsize))
            y = int(round((northing - ul_y) / -cellsize))

            assert 0 <= y < num_rows, (y, (num_rows, num_cols))
            assert 0 <= x < num_cols, (x, (num_rows, num_cols))
        else:
            x = np.array(np.round((np.array(easting) - ul_x) / cellsize), dtype=np.int)
            y = np.array(np.round((np.array(northing) - ul_y) / -cellsize), dtype=np.int)

        return x, y

    def lnglat_to_px(self, long, lat):
        """
        return the x,y pixel coords of long, lat
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        # find easting and northing
        x, y, _, _ = utm.from_latlon(lat, long, self.utm_zone)

        # assert this makes sense with the stored extent
        assert round(x) >= round(ul_x), (x, ul_x)
        assert round(x) <= round(lr_x), (x, lr_x)
        assert round(y) >= round(lr_y), (y, lr_y)
        assert round(y) <= round(y), (y, ul_y)

        # determine pixel coords
        _x = int(round((x - ul_x) / cellsize))
        _y = int(round((ul_y - y) / cellsize))

        # sanity check on the coords
        assert 0 <= _x < num_cols, str(x)
        assert 0 <= _y < num_rows, str(y)

        return _x, _y

    def px_to_utm(self, x, y):
        """
        return the utm coords from pixel coords
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        assert 0 <= x < num_cols
        assert 0 <= y < num_rows

        easting = ul_x + cellsize * x
        northing = ul_y - cellsize * y

        return easting, northing

    def lnglat_to_utm(self, lng, lat):
        """
        return the utm coords from lnglat coords
        """
        x, y, _, _ = utm.from_latlon(latitude=lat, longitude=lng, force_zone_number=self.utm_zone)
        return x, y

    def px_to_lnglat(self, x, y):
        """
        return the long/lat (WGS84) coords from pixel coords
        """

        easting, northing = self.px_to_utm(x, y)
        lat, lng, _, _ = utm.to_latlon(easting=easting, northing=northing,
                                       zone_number=self.utm_zone, northern=self.northern)
        return lng, lat
