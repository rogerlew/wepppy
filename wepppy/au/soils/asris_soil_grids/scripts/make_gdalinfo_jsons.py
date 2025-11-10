"""Produce cached ``gdalinfo`` JSON files for each ASRIS raster."""

from __future__ import annotations

import json
from glob import glob
from os.path import isdir
from os.path import join as _join
from os.path import split as _split
from subprocess import check_output

_asris_grid_raster_dir = '/geodata/au/asris/'


def write_gdalinfo_metadata(raster_dir: str = _asris_grid_raster_dir) -> None:
    """Create ``*.json`` files mirroring ``gdalinfo -json`` output.

    Args:
        raster_dir: Directory containing one subdirectory per raster layer.
    """
    catalog = glob(_join(raster_dir, '*'))
    catalog = [path for path in catalog if isdir(path)]
    catalog_map = {_split(path)[-1]: path for path in catalog}

    for dataset_name, path in catalog_map.items():
        print(dataset_name)
        js = check_output('gdalinfo -json ' + _join(path, dataset_name), shell=True)
        info = json.loads(js.decode())
        with open(_join(raster_dir, dataset_name + '.json'), 'w') as fp:
            json.dump(info, fp, indent=4, sort_keys=True, allow_nan=False)


if __name__ == "__main__":
    write_gdalinfo_metadata()
