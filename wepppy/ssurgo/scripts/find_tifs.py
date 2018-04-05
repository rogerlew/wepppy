#!/usr/bin/python
from glob import glob

fns = glob('coverage/*.tif')

fid = open('raster_list.txt', 'w')
fid.write('\n'.join(fns))
fid.close()

