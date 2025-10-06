import json
from math import atan2, pi, hypot
from typing import Union, List
import os
from os.path import exists as _exists

import subprocess
import rasterio

import numpy as np
import utm
from osgeo import gdal, osr, ogr

import geopandas as gpd
import inspect

from wepppy.all_your_base import isfloat
from wepppy.all_your_base.geo import get_utm_zone, utm_srid
from wepppy.topo.watershed_abstraction.support import json_to_wgs

gdal.UseExceptions()

__all__ = ['polygonize_sub_fields']

def polygonize_sub_fields(
        sub_field_fn, 
        sub_field_translator,
        dst_fn):
    assert _exists(sub_field_fn)
    src_ds = gdal.Open(sub_field_fn)
    srcband = src_ds.GetRasterBand(1)

    # build a mask for the subcatchments
    arr = srcband.ReadAsArray().astype(np.float32)
    arr[~np.isfinite(arr)] = 0        # -inf / +inf / nan  → 0
    arr[arr <= 0] = 0                 # force <=0 values to 0
    arr = arr.astype(np.int32)

    drv_mem = gdal.GetDriverByName('MEM')
    mem_ds  = drv_mem.Create(
        '', src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_CFloat32
    )
    mem_ds.SetGeoTransform(src_ds.GetGeoTransform())
    mem_ds.SetProjection(src_ds.GetProjection())
    mem_ds.GetRasterBand(1).WriteArray(arr)

    # mask: 255 where arr>0, 0 otherwise
    mask_ds = drv_mem.Create(
        '', src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Byte
    )
    mask_ds.GetRasterBand(1).WriteArray((arr > 0).astype(np.uint8) * 255)

    drv = ogr.GetDriverByName("GeoJSON")
    dst_ds = drv.CreateDataSource(dst_fn)

    srs = osr.SpatialReference()
    srs.ImportFromWkt(src_ds.GetProjectionRef())
    datum, utm_zone, hemisphere = get_utm_zone(srs)
    epsg = utm_srid(utm_zone, hemisphere == 'N')

    dst_layer = dst_ds.CreateLayer("sub_fields", srs=srs)
    dst_fieldname = 'sub_field_id'

    fd = ogr.FieldDefn(dst_fieldname, ogr.OFTInteger)
    dst_layer.CreateField(fd)
    dst_field = 0

    prog_func = None

    gdal.Polygonize(
        mem_ds.GetRasterBand(1),               # src band
        mask_ds.GetRasterBand(1),              # mask band → ignore zeros
        dst_layer, dst_field, [], callback=prog_func
    )

    del src_ds
    del dst_ds

    # remove the sub_field_id = 0 feature defining a bounding box
    # and the channels
    with open(dst_fn) as fp:
        js = json.load(fp)

    if "crs" not in js:
        js["crs"] = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::%s" % epsg}}

    _features = []
    for f in js['features']:
        sub_field_id = str(f['properties']['sub_field_id'])

        field_id, topaz_id, wepp_id = sub_field_translator.get(sub_field_id)
        f['properties']['wepp_id'] = wepp_id
        f['properties']['topaz_id'] = topaz_id
        f['properties']['field_id'] = field_id
        _features.append(f)

    js['features'] = _features

    with open(dst_fn, 'w') as fp:
        json.dump(js, fp, allow_nan=False)

    json_to_wgs(dst_fn)

