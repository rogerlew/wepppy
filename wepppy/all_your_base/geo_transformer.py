from typing import Any

from pyproj import Proj, transform


class GeoTransformer(object):
    def __init__(self, src_proj4=None, src_epsg=None, dst_proj4=None, dst_epsg=None):
        assert src_proj4 or src_epsg
        assert dst_proj4 or dst_epsg
        
        if src_proj4:
            self.srcProj = Proj(src_proj4)
        else:
            self.srcProj = Proj(init=src_epsg)

        if dst_proj4:
            self.dstProj = Proj(dst_proj4)
        else:
            self.dstProj = Proj(init=dst_epsg)

    def transform(self, x, y,
                  z: Any=None,
                  tt: Any=None,
                  radians: bool=False,
                  errcheck: bool=False,
                  skip_equivalent: bool=False,
                  always_xy: bool=False):
        return transform(self.srcProj, self.dstProj, x, y, z=z, tt=tt, radians=radians, errcheck=errcheck,
                         skip_equivalent=skip_equivalent, always_xy=always_xy)