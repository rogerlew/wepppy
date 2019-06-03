
import json
from glob import glob
from os.path import join as _join
from os.path import split as _split
import os


from subprocess import Popen, check_output

_asris_grid_raster_dir = '/geodata/au/asris/'

catalog = glob(_join(_asris_grid_raster_dir, '*'))
catalog = [path for path in catalog if os.path.isdir(path)]
catalog = {_split(path)[-1]:path for path in catalog}

for ds, path in catalog.items():
    print(ds)
    js = check_output('gdalinfo -json ' + _join(path, ds), shell=True)
    info = json.loads(js.decode())
    with open(_join(_asris_grid_raster_dir, ds + '.json'), 'w') as fp:
        json.dump(info, fp, indent=4, sort_keys=True)
