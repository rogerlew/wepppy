import os
import json
import sqlite3
from os.path import join as _join
from os.path import exists as _exists
from glob import glob
from subprocess import Popen, PIPE

import numpy as np
import io

import rasterio
from rasterio import features
from rasterio.enums import MergeAlg

_thisdir = os.path.dirname(__file__)
_datadir = _join(_thisdir, "data")
_statsgo = _join(_thisdir, "statsgo")


geom_value = []

jsons = glob('../../spatial/*.json')

for js_fn in jsons:
    state = js_fn.split('/')[1].split('.')[0]
    print(state)
    with open(js_fn) as fp:
        data = json.load(fp)

    print(len(data['features']))
    for feature in data['features']:
        geom = feature['geometry']
        value = int(feature['properties']['MUKEY'])
        geom_value.append((geom, value))

# raster template
raster = rasterio.open('/geodata/ssurgo/201703/.vrt')

# Rasterize vector using the shape and transform of the raster
rasterized = features.rasterize(geom_value,
                                out_shape = raster.shape,
                                transform = raster.transform,
                                all_touched = True,
                                fill = 0,   # background value
                                merge_alg = MergeAlg.replace,
                                dtype = np.uint32)

with rasterio.open(
        "/geodata/ssurgo/statsgo/rasterized_mukeys.tif", "w",
        driver = "GTiff",
        transform = raster.transform,
        dtype = rasterio.uint8,
        count = 1,
        width = raster.width,
        height = raster.height) as dst:
    dst.write(rasterized, indexes = 1)

