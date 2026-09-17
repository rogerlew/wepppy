"""Prepare a minimal disposable normal Ron and two real georeferenced uploads."""
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import rasterio
from wepppy.nodb.core import Ron

root = Path('/wc1/runs/qa/qa-freshness-profile-7e24c8d1')
root.mkdir(exist_ok=False)
source_config = Path('/wc1/runs/th/thespian-cleanness/config.cfg')
source_raster = Path('/wc1/batch/qa-raster-consumers-0fa74f3f2f95/sbs-GrizzlyCreek_SBS_final/GrizzlyCreek_SBS_final.tif')
config_sha = hashlib.sha256(source_config.read_bytes()).hexdigest()
input_sha = hashlib.sha256(source_raster.read_bytes()).hexdigest()
shutil.copy2(source_config, root / 'config.cfg')
ron = Ron(str(root), 'config.cfg')
ron.profile_recorder_assembler_enabled = True
fixtures = root.parent / (root.name + '-inputs')
fixtures.mkdir(exist_ok=False)
first, second = fixtures / 'first.tif', fixtures / 'second.tif'
shutil.copy2(source_raster, first)
with rasterio.open(source_raster) as dataset:
    data = dataset.read()
    profile = dataset.profile
    valid = np.argwhere((data[0] == 1) | (data[0] == 2))
    row, column = valid[len(valid)//2]
    previous = int(data[0, row, column])
    data[0, row, column] = 3
    with rasterio.open(second, 'w', **profile) as output:
        output.write(data)
assert hashlib.sha256(source_config.read_bytes()).hexdigest() == config_sha
assert hashlib.sha256(source_raster.read_bytes()).hexdigest() == input_sha
record = {'runid': root.name, 'root': str(root), 'first': str(first), 'second': str(second),
          'config_source_sha256': config_sha, 'raster_source_sha256': input_sha,
          'changed_pixel': {'row': int(row), 'column': int(column), 'before': previous, 'after': 3}}
Path(__file__).with_name('runtime_profile_preparation.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record))
