import sys
import netCDF4

import os
from os.path import exists as _exists
from os.path import join as _join
import shutil
from subprocess import Popen, PIPE
from glob import glob
import numpy as np


if __name__ == "__main__":

    measures = ['rain', 'tmax', 'tmin', 'rad']

    for measure in measures:
        print(measure)

        ncs = glob('/geodata/au/agdc/monthly_series/{}/*.nc'.format(measure))

        print(ncs)

        agg = np.zeros((12, 681, 841))
        count = np.zeros((12, 681, 841))

        for i, _nc in enumerate(ncs):
            ds = netCDF4.Dataset(_nc)
            if i == 0:
                print(ds.variables)
                lat = ds.variables['latitude']
                lng = ds.variables['longitude']
                print(lat[0], lat[-1])
                print(lng[0], lng[-1])
            data = ds.variables['{}_month'.format(measure)]
            data = np.array(data)
            data = np.ma.masked_where(data <= -999.0, data)
            data = np.ma.masked_where(data > 1e30, data)

            print(_nc, i, len(ncs), np.min(data), np.max(data))
            agg += data
            count += 1 - data.mask

        indx = np.where(count > 0)
        agg[indx] = agg[indx] / count[indx]
        print(agg.shape, np.min(agg), np.max(agg))

        dst_dir = '/geodata/au/agdc/monthlies/{}'.format(measure)

        if _exists(dst_dir):
           shutil.rmtree(dst_dir)

        os.mkdir(dst_dir)

        for i in range(12):
            with netCDF4.Dataset(_join(dst_dir, '{:02}.nc'.format(i+1)), 'w') as dst:
                for name, dimension in ds.dimensions.items():
                    dst.createDimension(name, len(dimension) if not dimension.isunlimited() else None)

                for name, variable in ds.variables.items():

                    if name == '{}_month'.format(measure):
                        x = dst.createVariable(measure, np.float64, ('latitude', 'longitude'))
                        dst.variables[measure][:] = agg[i, :, :]

                    elif name == 'time':
                        continue

                    else:
                        x = dst.createVariable(name, variable.datatype, variable.dimensions)
                        dst.variables[name][:] = ds.variables[name][:]

            cmd = ['gdal_translate',
                   '-a_srs', '+proj=longlat +datum=WGS84 +no_defs +ellps=WGS84 +towgs84=0,0,0',
                   '-of', 'GTIFF',
                   'NETCDF:{nc_fn}:{measure}'.format(nc_fn='{:02}.nc'.format(i+1), measure=measure),
                   '{:02}.tif'.format(i+1)]

            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=dst_dir)
            p.wait()
            assert _exists(_join(dst_dir, '{:02}.tif'.format(i+1)))
