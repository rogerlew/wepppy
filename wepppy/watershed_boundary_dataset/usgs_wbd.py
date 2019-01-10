
import sys
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import os
import shutil

import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt

from osgeo import gdal, osr, ogr
import pyproj

from wepppy.all_your_base import wgs84_proj4, read_raster
from wepppy.all_your_base import shapefile
from wepppy.nodb import Ron, Topaz

def build_mask(points, georef_fn):

    # This function is based loosely off of Frank's tests for
    # gdal.RasterizeLayer.
    # https://svn.osgeo.org/gdal/trunk/autotest/alg/rasterize.py

    # open the reference
    # we use this to find the size, projection,
    # spatial reference, and geotransform to
    # project the subcatchment to
    ds = gdal.Open(georef_fn)

    pszProjection = ds.GetProjectionRef()
    if pszProjection is not None:
        srs = osr.SpatialReference()
        if srs.ImportFromWkt(pszProjection) == gdal.CE_None:
            pszPrettyWkt = srs.ExportToPrettyWkt(False)


    geoTransform = ds.GetGeoTransform()

    # initialize a new raster in memory
    driver = gdal.GetDriverByName('MEM')
    target_ds = driver.Create('',
                              ds.RasterXSize,
                              ds.RasterYSize,
                              1, gdal.GDT_Byte)
    target_ds.SetGeoTransform(geoTransform)
    target_ds.SetProjection(pszProjection)

    # close the reference
    ds = None

    # Create a memory layer to rasterize from.
    rast_ogr_ds = ogr.GetDriverByName('Memory') \
        .CreateDataSource('wrk')
    rast_mem_lyr = rast_ogr_ds.CreateLayer('poly', srs=srs)

    # Add a polygon.
    coords = ','.join(['%f %f' % (lng, lat) for lng, lat in points])
    wkt_geom = 'POLYGON((%s))' % coords
    feat = ogr.Feature(rast_mem_lyr.GetLayerDefn())
    feat.SetGeometryDirectly(ogr.Geometry(wkt=wkt_geom))
    rast_mem_lyr.CreateFeature(feat)

    # Run the rasterization algorithm
    err = gdal.RasterizeLayer(target_ds, [1], rast_mem_lyr,
                              burn_values=[255])
    rast_ogr_ds = None
    rast_mem_lyr = None

    band = target_ds.GetRasterBand(1)
    data = band.ReadAsArray().T

    # find nonzero indices and return
    return -1 * (data / 255.0) + 1


class WatershedBoundaryDataset:
    def __init__(self, shp):
        sf = shapefile.Reader(shp)
        print(sf.shapeType)
        print(sf.fields)
        header = [field[0] for field in sf.fields][1:]

        """
        Field name: the name describing the data at this column index.
        Field type: the type of data at this column index. Types can be: Character, Numbers, Longs, Dates, or Memo.
        Field length: the length of the data found at this column index.
        Decimal length: the number of decimal places found in Number fields.
        """
#        shapes = sf.shapes()
#        print(len(shapes))
#        records = sf.records()
#        print(len(records))

        fails = 0
        for i, shape in enumerate(sf.iterShapes()):
            record = {k: v for k, v in zip(header, sf.record(i))}
            print(record)
            huc12 = record['HUC12']
            wd = _join('/geodata/pnw/', huc12)

            if _exists(wd):
                shutil.rmtree(wd)
            os.mkdir(wd)

            print('initializing nodbs')
            ron = Ron(wd, "lt.cfg")
            # ron = Ron(wd, "0.cfg")
            ron.name = wd

            print('setting map')
            bbox = shape.bbox
            pad = max(abs(bbox[0] - bbox[2]), abs(bbox[1] - bbox[3])) * 0.2
            map_center = (bbox[0] + bbox[2]) / 2.0,  (bbox[1] + bbox[3]) / 2.0
            l, b, r, t = bbox
            bbox = [l - pad, b - pad, r + pad, t + pad]
            ron.set_map(bbox, map_center, zoom=13)

            print('fetching dem')
            ron.fetch_dem()

            print('setting topaz parameters')
            topaz = Topaz.getInstance(wd)

            print('building channels')
            topaz.build_channels(csa=10, mcl=200)

            print('find raster indices')
            print('"', topaz.utmproj4, '"')
            utm_proj = pyproj.Proj(topaz.utmproj4)
            wgs_proj = pyproj.Proj(wgs84_proj4)
            points = [pyproj.transform(wgs_proj, utm_proj, lng, lat) for lng, lat in shape.points]
            mask = build_mask(points, ron.dem_fn)
            plt.figure()
            plt.imshow(mask)
            plt.savefig(_join(topaz.topaz_wd, 'mask.png'))
            print('finding lowest point in HUC')
            dem, transform, proj = read_raster(ron.dem_fn)
            print(mask.shape, dem.shape)
            print(np.sum(mask))
            demma = ma.masked_array(dem, mask=mask)

            px, py = np.unravel_index(demma.argmin(fill_value=1e38), demma.shape)
            px = int(px)
            py = int(py)
            print(px, py, px/dem.shape[0], py/dem.shape[1])

            print('building subcatchments')
            topaz.set_outlet(px, py, pixelcoords=True)
            try:
                topaz.build_subcatchments()
            except:
                fails += 1
                raise

            print(fails, i+1)


if __name__ == "__main__":

    wbd = WatershedBoundaryDataset("/geodata/wbd/WBD_17_HU2_Shape/Shape/WBDHU12")

