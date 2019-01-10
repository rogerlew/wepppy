import os
from glob import glob
from subprocess import call

src = 'srld/mean/srld_mean_01.tif'
assert os.path.exists(src)

for var in ['dayl', 'prcp', 'srad']:
    for stat in ['mean', 'std', 'skew', 'pwd', 'pww']:
        for fn in glob('%s/%s/*.tif' % (var, stat)):
            cmd = ['gdalcopyproj.py', src, fn]
            print cmd
            call(cmd)