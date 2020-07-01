from typing import Any

from pyproj import Proj, transform


class GeoTransformer(object):
    def __init__(self, src_proj4=None, src_epsg=None, dst_proj4=None, dst_epsg=None):
        assert src_proj4 or src_epsg
        assert dst_proj4 or dst_epsg
        
        if src_proj4:
            self.srcProj = Proj(src_proj4)
        else:
            self.srcProj = Proj('EPSG:%i' % src_epsg)

        if dst_proj4:
            self.dstProj = Proj(dst_proj4)
        else:
            self.dstProj = Proj('EPSG:%i' % dst_epsg)

    def transform(self, x, y):
        return transform(self.srcProj, self.dstProj, x, y)