import os
from glob import glob
from subprocess import call

base_dir = '/geodata/daymet'

for var in ['dayl', 'prcp', 'srad', 'srld']:
    for stat in ['mean', 'std', 'skew', 'pwd', 'pww']:
        dir = os.path.join(base_dir, var, stat)

        if not os.path.exists(dir):
            continue

        os.chdir(dir)

        fns = glob('*.tif')
        if len(fns) > 0:
            cmd = ['gdalbuildvrt', '-separate', '.vrt'] + fns

            print cmd
            call(cmd)
