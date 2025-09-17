# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists

from collections import Counter

import numpy as np

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import GDT_UInt32

from deprecated import deprecated

from wepppy.all_your_base.geo import read_raster, raster_stacker

__version__ = 'v.0.1.0'

_thisdir = os.path.dirname(__file__)
_ssurgo_cache_db = _join(_thisdir, ':memory:')  # 'ssurgo_cache.db')
_statsco_cache_db = _join(_thisdir, 'statsco.db')

class NoValidSoilsException(Exception):
    """
    No valid soils could be found within the catchment boundary
    """
    
    __name__ = 'No Valid Soils Exception'


class SurgoMap:
    def __init__(self, fname):
        assert _exists(fname)
        self.fname = fname

        data, transform, proj = read_raster(fname, dtype=np.int32)
        
        self.data = data
        self.transform = transform
        self.proj = proj
        self.mukeys = list(set(self.data.flatten()))
        self.fname = fname

    def _get_dominant(self, indices=None, valid_mukeys=None):
        """
        Determines the dominant mukey for the given indices. If
        indices is None then the entire maps is examined
        """

        if indices is None:
            x = self.data
            
        else:
            x = self.data[indices]
        
        x = list(x.flatten())

        sorted_keys = Counter(x).most_common()[0]

        if valid_mukeys is None:
            return sorted_keys[0]
        else:  # not strictly necessary but makes the type checking happy
            for key in sorted_keys:
                if key in valid_mukeys:
                    return key
                
        return None
        