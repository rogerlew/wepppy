# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists

import json
from collections import Counter

import numpy as np

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import (
    GDT_Float32,
    GDT_UInt32
)

from wepppy.all_your_base import (
    read_arc,
    read_raster
)

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
        
    def build_soilgrid(self, subwta_fn, soilgrid_fn=None, bounds_fn=None, valid_mukeys=None):
        """
        Generates a dominant soil map based on the subcatchment
        ids identified in the subwta_fn map
        
        if valid_mukeys is None assumes all the keys in the map are valid
        if valid_mukeys are provided the keys that are not in valid_mukeys
        are masked before identifying the dominant soil.
        
        valid_mukeys can be provided by wepppy.wepp.soilbuilder.webClient.validatemukeys
        
        returns a dict with topaz id keys and mukey values.
        The topaz ids are strings 'cause javascript.
        """
        
        # probably not strictly necessary to verify these...
        mukeys = self.mukeys
        if valid_mukeys is not None:
            for key in valid_mukeys:
                assert key in mukeys
        
        assert _exists(subwta_fn)
        
        subwta, transform, proj = read_arc(subwta_fn, dtype=np.int32)
                
        top_ids = sorted(list(set(subwta.flatten())))

        assert sum([(0, 1)[str(k).endswith('4')] for k in top_ids]) > 0, 'subwta does not contain channels: %s' % str(top_ids)
        
        # determine dom for the watershed
        if bounds_fn is None:
            dom_dom = self._get_dominant(valid_mukeys=valid_mukeys)
        else:
            assert _exists(bounds_fn)
            bounds, transform2, proj2 = read_arc(bounds_fn, dtype=np.int32)
            indices = np.where(bounds == 1)
            dom_dom = self._get_dominant(indices, valid_mukeys)
            
        if dom_dom is None:
            raise NoValidSoilsException()
        
        soilgrid = np.zeros(subwta.shape, np.int32)
        domsoil_d = {}
        for _id in top_ids:
            if _id == 0:
                continue

            indices = np.where(subwta == _id)
            dom = self._get_dominant(indices, valid_mukeys)
            if dom is None:
                dom = dom_dom
            
            soilgrid[indices] = dom
                
            domsoil_d[str(_id)] = str(dom)
            
        if soilgrid_fn is not None:
            # initialize raster
            num_cols, num_rows = soilgrid.shape
            proj = self.proj

            driver = gdal.GetDriverByName("GTiff")
            dst = driver.Create(soilgrid_fn, num_cols, num_rows,
                                1, GDT_UInt32)

            srs = osr.SpatialReference()
            srs.ImportFromProj4(proj)
            wkt = srs.ExportToWkt()

            dst.SetProjection(wkt)
            dst.SetGeoTransform(self.transform)
            dst.GetRasterBand(1).WriteArray(soilgrid)

            del dst  # Writes and closes file
            
            assert _exists(soilgrid_fn)

        assert sum([(0, 1)[str(k).endswith('4')] for k in domsoil_d.keys()]) > 0, 'lost channels in domsoil_d'

        return domsoil_d
    
    def spatialize_var(self, func, dst_fname, drivername='GTiff'):
        """
        Creates a raster of the variable specified by var
        """
        data, mukeys = self.data, self.mukeys
        num_cols, num_rows = data.shape
        proj, transform = self.proj, self.transform
        
        # create empty array to hold data
        var_r = np.zeros(data.shape)
        
        # iterate over mukeys and fill data
        meta = Counter()
        for mukey in mukeys:
            indx = np.where(data == mukey)
            value = func(mukey)
            var_r[indx] = value
            
            meta[value] += len(indx[0])
            
        with open(dst_fname + '.meta', 'w') as fid:
            fid.write(json.dumps(meta, sort_keys=True,
                      indent=4, separators=(',', ': ')))
                
        # create raster
        driver = gdal.GetDriverByName(drivername)
        dst = driver.Create(dst_fname, num_cols, num_rows, 1, GDT_Float32)

        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj)
        wkt = srs.ExportToWkt()

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform)
        dst.GetRasterBand(1).WriteArray(var_r)
        
        del dst  # Writes and closes file
