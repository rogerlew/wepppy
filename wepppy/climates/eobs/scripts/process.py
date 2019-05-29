import os
from os.path import join as _join
from os.path import exists as _exists

from datetime import date, timedelta

import numpy as np
from numpy.ma import masked_values

from scipy.stats import kurtosis

from osgeo import gdal, osr

import matplotlib.pyplot as plt

_eobs_dir = '/geodata/eu/E-OBS'

_epsg4326_wkt = '''\
GEOGCS["WGS 84",
    DATUM["WGS_1984",
        SPHEROID["WGS 84",6378137,298.257223563,
            AUTHORITY["EPSG","7030"]],
        AUTHORITY["EPSG","6326"]],
    PRIMEM["Greenwich",0,
        AUTHORITY["EPSG","8901"]],
    UNIT["degree",0.0174532925199433,
        AUTHORITY["EPSG","9122"]],
    AUTHORITY["EPSG","4326"]]'''


def dump_tif(data, fname, wkt, transform, mask=None, nodata=None):
    if hasattr(data, "mask"):
        mask = data.mask
        assert nodata is not None

    elif mask is not False and mask is not None:
        assert mask.shape == data.shape
        data[np.where(mask)] = nodata

    data = np.array(data)

    n, m = data.shape
    # initialize raster
    driver = gdal.GetDriverByName("GTiff")
    dst = driver.Create(fname, n, m,
                        1, gdal.GDT_Float32)

    dst.SetProjection(wkt)
    dst.SetGeoTransform(transform)
    band = dst.GetRasterBand(1)
    band.WriteArray(data.T)

    if nodata != None:
        band.SetNoDataValue(float(nodata))

    dst = None  # Writes and closes file

stats = dict(mean=np.mean, std=np.std) #, skew=kurtosis)

if __name__ == "__main__":
    out_dir = '/geodata/eu/E-OBS'

    for measure, scale_factor in [('tx', 0.0099999998),
                                  ('tn', 0.0099999998),
                                  ('rr', 0.1),
                                  ('pp', 0.1)]:

        measure_dir = _join(out_dir, measure)
        if not _exists(measure_dir):
            os.mkdir(measure_dir)

        fn = _join(_eobs_dir, '%s_ens_mean_0.1deg_reg_v19.0e.nc' % measure)

        date0 = date(1950, 1, 1)

        ds = gdal.Open(fn)
        assert ds is not None

        transform = ds.GetGeoTransform()
        wkt_text = ds.GetProjection()
        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt_text)
        proj = srs.ExportToProj4().strip()

        num_bands = ds.RasterCount

        print(transform, wkt_text, proj, num_bands)

        for month in range(1, 13):
            print(month)
            monthly = []
            for j in range(1, num_bands+1):
                _date = date0 + timedelta(days=j-1)

                if _date.month != month:
                    continue

                band = ds.GetRasterBand(j)
                nodata = band.GetNoDataValue()
                data = masked_values(band.ReadAsArray(), nodata)
                monthly.append(data)

            print(measure, np.mean(monthly[0]) * scale_factor, np.sum(data.mask))
            x = np.stack(monthly, axis=2) * scale_factor
            del monthly

            for stat, agg in stats.items():
                stat_dir = _join(measure_dir, stat)
                if not _exists(stat_dir):
                    os.mkdir(stat_dir)

                grid = agg(x, axis=2)
                print(measure, month, stat, x.shape, grid.shape)
                fn = _join(stat_dir,
                           '{measure}_{stat}_{month:02}.tif'
                           .format(measure=measure, stat=stat, month=month))

                dump_tif(grid.T, fn, _epsg4326_wkt, transform, nodata=nodata)

                del grid

            del x
