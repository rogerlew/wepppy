# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.
import math

from os.path import exists as _exists
from collections import Counter

import numpy as np
from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *

from wepppy.all_your_base import read_arc, read_raster


class ShrublandMap:
    def __init__(self, fname):
        assert _exists(fname)
        self.fname = fname

        data, transform, proj = read_raster(fname, dtype=np.int32)
        data = np.array(data, dtype=np.float)
        if 'height' in fname:
            data = np.ma.masked_greater(data, 997)
        else:
            data = np.ma.masked_greater(data, 100)

        self.data = data
        self.transform = transform
        self.proj = proj
        self.fname = fname

    def _get_median(self, indices):
        x = self.data[indices]
        if np.sum(x.mask) == np.prod(x.shape):
            return None

        retval = float(np.ma.median(x))
        if math.isnan(retval):
            return None

        return retval

    def spatial_aggregation(self, subwta_fn):
        assert _exists(subwta_fn)
        subwta, transform, proj = read_arc(subwta_fn, dtype=np.int32)
        _ids = sorted(list(set(subwta.flatten())))

        domlc_d = {}
        for _id in _ids:
            if _id == 0:
                continue

            _id = int(_id)
            indices = np.where(subwta == _id)
            dom = self._get_median(indices)

            domlc_d[str(_id)] = dom
        return domlc_d

    def spatial_stats(self, bounds_fn):
        assert _exists(bounds_fn)
        bounds, transform, proj = read_arc(bounds_fn, dtype=np.int32)
        indices = np.where(bounds == 1)

        x = self.data[indices]
        is_height = 'height' in self.fname

        if is_height:
            x *= 0.01

        return dict(num_pixels=len(indices[0]),
                    valid_pixels=len(indices[0]) - np.sum(x.mask),
                    mean=np.mean(x),
                    std=np.std(x),
                    units=('%', 'm')[is_height])
