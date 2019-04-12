from os.path import join as _join
from os.path import exists as _exists

from wepppy.all_your_base import (
    RasterDatasetInterpolator,
    RDIOutOfBoundsException
)

_wd = '/geodata/Holden_WRF_atlas/'
_nc = _join(_wd, 'WRF_prcp_freq_atlas.nc')


def fetch_pf(lat, lng):

    rec_intervals = [2, 5, 25]
    durations = ['1-hour', '6-hour', '24-hour']

    precips = []
    for rec in rec_intervals:
        for dur in durations:
            fn = _join(_wd, 'precip_freq_{}_{}year.tif'.format(dur.replace('-', ''), rec))
            assert _exists(fn), fn

            raster = RasterDatasetInterpolator(fn)
            try:
                p = raster.get_location_info(lng, lat)
            except RDIOutOfBoundsException:
                return None

            precips.append(float(p))

    return dict(rec_intervals=rec_intervals,
                durations=durations,
                precips=precips,
                units='mm')

if __name__ == "__main__":
    import sys
    import netCDF4

    import os
    from subprocess import Popen, PIPE

    print(fetch_pf(46.5, -117.0))

    sys.exit()

    ds = netCDF4.Dataset(_nc)
    print(ds.variables)

    # extract tifs from netcdf
    lngs = ds.variables['longitude']
    lats = ds.variables['latitude']
    times = ds.variables['time']

    for var in ds.variables:
        print(var)
        if 'precip' in var:
            cmd = ['gdal_translate',
                   '-a_srs', '+proj=longlat +datum=WGS84 +no_defs +ellps=WGS84 +towgs84=0,0,0',
                   '-of', 'GTIFF',
                   'NETCDF:WRF_prcp_freq_atlas.nc:{}'.format(var),
                   '{}.tif'.format(var)]

            print(' '.join(cmd))
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=_wd)
            p.wait()


