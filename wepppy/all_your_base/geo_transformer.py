from typing import Any
import os

IS_WINDOWS = os.name == 'nt'

class GeoTransformer(object):
    def __init__(self, src_proj4=None, src_epsg=None, dst_proj4=None, dst_epsg=None):
        assert src_proj4 or src_epsg
        assert dst_proj4 or dst_epsg
        
        self.src_proj4 = src_proj4
        self.src_epsg = src_epsg
        self.dst_proj4 = dst_proj4
        self.dst_epsg = dst_epsg

    def transform(self, x, y):
        src_proj4 = self.src_proj4
        src_epsg = self.src_epsg
        dst_proj4 = self.dst_proj4
        dst_epsg = self.dst_epsg

        if IS_WINDOWS:
            from pyproj import Proj, transform
            if self.src_proj4:
                srcProj = Proj(src_proj4)
            else:
                srcProj = Proj('EPSG:%i' % src_epsg)
    
            if dst_proj4:
                dstProj = Proj(dst_proj4)
            else:
                dstProj = Proj('EPSG:%i' % dst_epsg)
                
            return transform(srcProj, dstProj, x, y)
        else:
            if self.src_proj4:
                s_srs = src_proj4
            else:
                s_srs = 'EPSG:%i' % src_epsg

            if dst_proj4:
                t_srs = dst_proj4
            else:
                t_srs = 'EPSG:%i' % dst_epsg

            from subprocess import Popen, PIPE, STDOUT
            cmd = ['gdaltransform', '-s_srs', s_srs, '-t_srs', t_srs, '-output_xy']
            p = Popen(cmd, bufsize=0, stdin=PIPE, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
            ret = p.communicate('{x} {y}'.format(x=x, y=y))
            return map(float, ret[0].split().strip())


if __name__ == "__main__":

    _wgs_2_lcc = GeoTransformer(src_epsg=4326, dst_proj4='+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs')