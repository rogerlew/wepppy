import subprocess
from wepppy.all_your_base.geo import RasterDatasetInterpolator


def rasterize(vec_fn, dst_fn, template_fn, attr='CFF_ID'):
    rdi = RasterDatasetInterpolator(template_fn)
    xorigin, xpxsize, xzero, yorigin, yzero, ypxsize = rdi.transform

    cmd = ['gdal_rasterize', '-a', attr, 
           '-te', rdi.left, rdi.lower, rdi.right, rdi.upper, 
           '-tr', abs(xpxsize), abs(ypxsize), vec_fn, dst_fn]
    cmd = [str(arg) for arg in cmd]
    p = subprocess.Popen(cmd)
    p.wait()


if __name__ == "__main__":
    vec_fn = '/geodata/salvage_logging/north_star/Skid_segments.utm.geojson'
    dem_fn = '/geodata/weppcloud_runs/lighter-than-air-rebound/dem/dem.tif'
    dst_fn = '/geodata/weppcloud_runs/lighter-than-air-rebound/salvage/skid.tif'

    rasterize(vec_fn, dst_fn, dem_fn, attr='CFF_ID')

