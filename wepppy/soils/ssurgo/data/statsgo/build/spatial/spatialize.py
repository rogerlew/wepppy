import csv
import json
import pickle
import os
import sys
import shutil
from os.path import exists as _exists
from os.path import split as _split
from os.path import join as _join
import numpy as np
from pprint import pprint

from glob import glob

# https://github.com/rogerlew/all_your_base
from wepppy.all_your_base.geo import (
    raster_stacker, read_raster, RasterDatasetInterpolator
)
import subprocess
from glob import glob
from collections import Counter
from copy import deepcopy

from wepppy.soils.ssurgo import SurgoMap, SurgoSpatializer, SurgoSoilCollection, spatial_vars

if __name__ == "__main__":

    for i in range(11):
        for j in range(6):
            print(0, i, j)
            ssurgo_map = SurgoMap(f'_mukeys_{i:02}_{j:02}.tif')

            print(1)
            ssurgo_c = SurgoSoilCollection(ssurgo_map.mukeys, use_statsgo=True)

            print(2)
            ssurgo_c.makeWeppSoils(horizon_defaults=None)

            print(3)
            spatializer = SurgoSpatializer(ssurgo_c, ssurgo_map)

            print(4)
            for var in spatial_vars:
                print(var)
                os.makedirs(var, exist_ok=True)
                spatializer.spatialize_var(var, _join(var, f'_{var}_{i:02}_{j:02}.tif'))

