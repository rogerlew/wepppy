import hashlib
import json
import string
import os
from os.path import split as _split
from os.path import join as _join

from glob import glob
from datetime import datetime
from copy import deepcopy

from wepppy.soils.ssurgo import SoilSummary
from wepppy.all_your_base import isfloat, RasterDatasetInterpolator

_asris_grid_raster_dir = '/geodata/au/asris/'


class ASRISgrid:
    def __init__(self):
        # { attr, raster_file_path}
        catalog = glob(_join(_asris_grid_raster_dir, '*'))
        catalog = [path for path in catalog if os.path.isdir(path)]
        catalog = {_split(path)[-1]:path for path in catalog}
        self.catalog = catalog

        # { attr, raster_attribute table}
        rats = {}
        for var, path in catalog.items():
            fn = _join(path + '.json')

            with open(fn) as fp:
                info = json.load(fp)

            if 'rat' not in info:
                continue

            rows = info['rat']['row']

            d = {}
            for row in rows:
                row = row['f']
                d[row[0]] = row[-1]

            rats[var] = d
        self.rats = rats

    def query(self, lng, lat):

        catalog = self.catalog
        rats = self.rats
        d = {}

        for var in catalog:
            rdi = RasterDatasetInterpolator(_join(catalog[var], var))
            x = rdi.get_location_info(lng, lat, method='near')
            px_val = int(x)
            if var in rats:
                value = rats[var][px_val]
            else:
                value = px_val

            d[var] = value

        return d


if __name__ == "__main__":
    asris = ASRISgrid()
    print(asris.catalog)
    print(asris.rats)
    d = asris.query(lng=146.27506256103518, lat=-37.713973374315984)
    print(d)