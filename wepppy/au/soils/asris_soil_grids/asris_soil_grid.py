"""Utilities for querying the ASRIS national soil grid rasters."""

from __future__ import annotations

import json
from glob import glob
from os.path import exists as _exists
from os.path import isdir as _isdir
from os.path import join as _join
from os.path import split as _split
from typing import Dict

from wepppy.all_your_base.geo import RasterDatasetInterpolator

__all__ = ["ASRISgrid"]

_asris_grid_raster_dir = '/geodata/au/asris/'


class ASRISgrid:
    """Expose soil attributes stored in the ASRIS raster catalog."""

    def __init__(self) -> None:
        catalog = glob(_join(_asris_grid_raster_dir, '*'))
        catalog = [path for path in catalog if _isdir(path)]
        catalog_dict = {_split(path)[-1]: path for path in catalog}
        self.catalog: Dict[str, str] = catalog_dict

        rats: Dict[str, Dict[int, float | int]] = {}
        for var, path in catalog_dict.items():
            fn = _join(path + '.json')

            if not _exists(fn):
                continue

            with open(fn) as fp:
                info = json.load(fp)

            if 'rat' not in info:
                continue

            rows = info['rat']['row']

            table: Dict[int, float | int] = {}
            for row in rows:
                fields = row['f']
                table[fields[0]] = fields[-1]

            rats[var] = table
        self.rats: Dict[str, Dict[int, float | int]] = rats

    def query(self, lng: float, lat: float) -> Dict[str, float | int]:
        """Return ASRIS soil attributes for a coordinate.

        Args:
            lng: Longitude in decimal degrees.
            lat: Latitude in decimal degrees.

        Returns:
            Dictionary keyed by raster short name with RAT values (when
            available) or the raw pixel value.
        """
        catalog = self.catalog
        rats = self.rats
        results: Dict[str, float | int] = {}

        for var in catalog:
            rdi = RasterDatasetInterpolator(_join(catalog[var], var))
            x = rdi.get_location_info(lng, lat, method='near')
            px_val = int(x)
            if var in rats:
                value: float | int = rats[var][px_val]
            else:
                value = px_val

            results[var] = value

        return results


if __name__ == "__main__":
    asris = ASRISgrid()
    print(asris.catalog)
    print(asris.rats)
    d = asris.query(lng=146.27506256103518, lat=-37.713973374315984)
    print(d)
