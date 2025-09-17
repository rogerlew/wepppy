# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import exists as _exists
from collections import Counter

import numpy as np
from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *

from deprecated import deprecated

from wepppy.all_your_base.geo import read_raster, raster_stacker


class LandcoverMap:
    def __init__(self, fname):
        assert _exists(fname)
        self.fname = fname

        data, transform, proj = read_raster(fname, dtype=np.int32)

        self.data = data
        self.transform = transform
        self.proj = proj
        self.lc_types = list(set(self.data.flatten()))
        self.fname = fname

    def _get_dominant(self, indices):
        x = self.data[indices]
        return int(Counter(x).most_common()[0][0])
        
    def _get_fractionals(self, indices):
        x = self.data[indices]
        return {str(k): v for k,v in Counter(x).most_common()}
        
    def calc_fractionals(self, subwta_fn):
        """
        calc fractionals based on the subcatchment
        ids identified in the subwta_fn map
        """
        assert _exists(subwta_fn)
        subwta, transform, proj = read_raster(subwta_fn, dtype=np.int32)
        assert self.data.shape == subwta.shape

        _ids = sorted(list(set(subwta.flatten())))
        
        frac_d = {}
        for _id in _ids:
            if _id == 0:
                continue
                
            _id = int(_id)
            indices = np.where(subwta == _id)
            frac = self._get_fractionals(indices)
            frac_d[str(_id)] = frac

        return frac_d
            
    @deprecated("Use wepppyo3 instead")
    def build_lcgrid(self, subwta_fn, mofe_fn=None):
        """
        Generates a dominant lc map based on the subcatchment
        ids identified in the subwta_fn map
        """
        assert _exists(subwta_fn)
        subwta, transform, proj = read_raster(subwta_fn, dtype=np.int32)

        if not self.data.shape == subwta.shape:
            dst_fn = subwta_fn.replace('.ARC', '.fixed.tif')
            raster_stacker(self.fname, subwta_fn, dst_fn)
            subwta, transform, proj = read_raster(dst_fn, dtype=np.int32)

        assert self.data.shape == subwta.shape, [self.data.shape, subwta.shape]

        if mofe_fn is None:
            mofe_map = None
        else:
            mofe_map, transform_m, proj_m = read_raster(mofe_fn, dtype=np.int32)

        _ids = sorted([v for v in set(subwta.flatten()) if v > 0])

        domlc_d = {}
        for _id in _ids:
            if _id == 0:
                continue
                
            _id = int(_id)
            indices = np.where(subwta == _id)

            if mofe_map is None:
                dom = self._get_dominant(indices)
                domlc_d[str(_id)] = str(dom)
            else:
                mofes = sorted(list(set(mofe_map[indices].flatten())))
                mofes = [mofe for mofe in mofes if mofe != 0]

                domlc_d[str(_id)] = {}
                for mofe in mofes:
                    indices = np.where((subwta == _id) & (mofe_map == mofe))
                    dom = self._get_dominant(indices)
                    domlc_d[f'{_id}'][f'{mofe}'] = str(dom)
            
        return domlc_d


if __name__ == "__main__":
    fn = "/var/www/wepp/FlaskApp/static/runs/last/landuse/nlcd.asc"
    lc = LandcoverMap(fn)
    print(lc.data.shape)
