# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import exists as _exists

import numpy as np

from wepppy.all_your_base.geo import read_raster        

from deprecated import deprecated

@deprecated(reason="Use wepppyo3.raster_characteristics instead")
class ParameterMap:
    def __init__(self, fname, nodata_vals=None):

        assert _exists(fname)
        self.fname = fname

        data, transform, proj = read_raster(fname, dtype=np.uint8)
       
        if nodata_vals is not None:
            
            for nodata_val in nodata_vals:
                data = np.ma.masked_values(data, nodata_val)
 
        self.data = data
        self.nodata_vals = nodata_vals
        self.transform = transform
        self.proj = proj
        self.fname = fname

    def build_ave_grid(self, subwta_fn, lcgrid_fn=None):
        """
        Generates a dominant lc map based on the subcatchment
        ids identified in the subwta_fn map
        """
        assert _exists(subwta_fn)
        subwta, transform, proj = read_raster(subwta_fn, dtype=np.int32)
        _ids = sorted(list(set(subwta.flatten())))
        data = self.data

        domlc_d = {}
        for _id in _ids:
            if _id == 0:
                continue
                
            _id = int(_id)
            indices = np.where(subwta == _id)
            ave = np.mean(data[indices]) 
                
            domlc_d[str(_id)] = float(ave)
            
        return domlc_d

