import os

from os.path import join as _join
from os.path import exists as _exists

from wepppy.all_your_base import isfloat

_thisdir = os.path.dirname(__file__)

_map = {}

with open(_join(_thisdir, 'map.psv')) as fp:
    for line in fp:
        line = line.strip()
        if not line:
            continue
        k, v = line.split('|')
        _map[int(k)] = v

def get_soil_fn(soil_id):
    """
    Get the soil file name for a given soil ID.
    """
    if soil_id in _map:
        soil_path = os.path.abspath(_join(_thisdir, _map[soil_id] + '.sol'))
        if not _exists(soil_path):
            raise FileNotFoundError(f"File not found: {soil_path}")
        return soil_path

    else:
        raise ValueError(f"Unknown soil ID: {soil_id}")
    

if __name__ == "__main__":
    for soil_id in range(1,4):
        print(soil_id)
        print(get_soil_fn(soil_id))