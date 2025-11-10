"""Landuse lookups for the 2010/2011 Australian national landuse grid."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from os.path import exists as _exists
from subprocess import check_output

from wepppy.all_your_base.geo import RasterDatasetInterpolator

__all__ = ["Lu10v5ua"]

_grid_path = '/geodata/au/landuse_201011/lu10v5ua'


class Lu10v5ua:
    """Expose pixel metadata for the Australian 2010/2011 landuse raster.

    Attributes:
        rat: Raster attribute table keyed by pixel value.
        rat_field_defs: Ordered list of RAT field names.
        landuse_map: Minimal legend keyed by dominant landuse code.
    """

    def __init__(self) -> None:
        assert _exists(_grid_path)

        js = check_output('gdalinfo -json ' + _grid_path, shell=True)
        rat = json.loads(js.decode())['rat']

        field_defs = rat['fieldDefn']

        data: Dict[int, Dict[str, Any]] = {}
        for row in rat['row']:
            fields = row['f']
            px_value = fields[0]
            data[px_value] = {fd['name']: value for fd, value in zip(field_defs, fields)}

        self.rat: Dict[int, Dict[str, Any]] = data
        self.rat_field_defs: List[str] = [fd['name'] for fd in field_defs]

        landuse_map: Dict[str, Dict[str, Any]] = {}
        for px_value, row in data.items():
            dom = self.get_dom(px_value)

            if dom not in landuse_map:
                if dom.startswith('f'):
                    desc = row['FOREST_TYPE_DESC']
                elif dom.startswith('a'):
                    desc = row['COMMODITIES_DESC']
                else:
                    desc = row['C18_DESCRIPTION']

                landuse_map[dom] = dict(Key=dom, Color=[0, 0, 0, 255], Description=desc, ManagementFile=None)

        self.landuse_map: Dict[str, Dict[str, Any]] = {k: landuse_map[k] for k in sorted(landuse_map)}

    def get_dom(self, px_value: int) -> str:
        """Return the dominant landuse identifier for a pixel value.

        Args:
            px_value: Raster pixel value drawn from the RAT.

        Returns:
            DOM code (``f#``, ``a#``, ``c#``) describing the landuse bucket.
        """
        row = self.rat[px_value]
        forest = row['FOREST_TYPE']
        commodities = row['COMMODITIES']
        if commodities == -1:
            commodities = 99
        c18 = row['CLASSES_18']

        if forest != 0:
            return 'f{forest:01}'.format(forest=forest)
        elif commodities != 99:
            return 'a{commodities:01}'.format(commodities=commodities)
        else:
            return 'c{c18:01}'.format(c18=c18)

    def query_dom(self, lng: float, lat: float) -> str:
        """Lookup the dominant landuse class for a lon/lat coordinate.

        Args:
            lng: Longitude in decimal degrees.
            lat: Latitude in decimal degrees.

        Returns:
            DOM code for the supplied coordinate.
        """
        rdi = RasterDatasetInterpolator(_grid_path)
        px_value = rdi.get_location_info(lng, lat, method='near')

        return self.get_dom(px_value)

    def query(self, lng: float, lat: float) -> Dict[str, Any]:
        """Return the entire raster attribute table row for a coordinate.

        Args:
            lng: Longitude in decimal degrees.
            lat: Latitude in decimal degrees.

        Returns:
            Dictionary of RAT attributes for the coordinate.
        """
        rdi = RasterDatasetInterpolator(_grid_path)
        px_value = rdi.get_location_info(lng, lat, method='near')

        return self.rat[px_value]


if __name__ == "__main__":
    import csv
    from pprint import pprint
    lu10v5ua = Lu10v5ua()

    print(lu10v5ua.rat_field_defs)
    fp = open('rat.csv', 'w')
    wtr = csv.DictWriter(fp, lu10v5ua.rat_field_defs)
    wtr.writeheader()

    for k, v in lu10v5ua.rat.items():
        wtr.writerow(v)

    print(lu10v5ua.landuse_map)
    print(len(lu10v5ua.landuse_map))
