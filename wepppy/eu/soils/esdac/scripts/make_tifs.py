"""
run from ESDAC_soilsdb/esdac.jrc.ec.europa.eu/wyz_856/_02_rst/ESDB_1k_rasters_dom_val
after extracting zips.
"""

import json
from glob import glob
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import os

from osgeo import gdal

from subprocess import Popen, check_output

#wds = glob('*directory/*/w001001.adf')
wds = glob('/geodata/eu/ESDAC_STU_EU_Layers/*.rst')

for src in wds:
    
    dst = src[:-4] + '.tif'

    cmd = ['gdal_translate', src, dst, '-a_srs', 'epsg:3035']
    print(cmd)
    p = Popen(cmd)
    p.wait()

    js = check_output('gdalinfo -json ' + src, shell=True)
    info = json.loads(js.decode())
    with open(src[:-4] + '.json', 'w') as fp:
        json.dump(info, fp, indent=4, sort_keys=True, allow_nan=False)



