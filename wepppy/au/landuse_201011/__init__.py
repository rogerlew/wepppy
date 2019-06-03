import json

from os.path import exists as _exists
from subprocess import check_output

from wepppy.all_your_base import RasterDatasetInterpolator

_grid_path = '/geodata/au/landuse_201011/lu10v5ua'


class Lu10v5ua:
    def __init__(self):
        assert _exists(_grid_path)

        js = check_output('gdalinfo -json ' + _grid_path, shell=True)
        rat = json.loads(js.decode())['rat']

        field_defs = rat['fieldDefn']

        d = {}
        for row in rat['row']:
            row = row['f']
            px_value = row[0]
            row = {fd['name']: v for fd, v in zip(field_defs, row)}
            d[px_value] = row

        self.rat = d
        self.rat_field_defs = [fd['name'] for fd in field_defs]

        landuse_map = {}
        for px_value, row in d.items():
            dom = self.get_dom(px_value)

            if dom not in landuse_map:
                if dom.startswith('f'):
                    desc = row['FOREST_TYPE_DESC']
                elif dom.startswith('a'):
                    desc = row['COMMODITIES_DESC']
                else:
                    desc = row['C18_DESCRIPTION']

                landuse_map[dom] = dict(Key=dom, Color=[0, 0, 0, 255], Description=desc, ManagementFile=None)

        self.landuse_map = {k: landuse_map[k] for k in sorted(landuse_map)}

    def get_dom(self, px_value):
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

    def query_dom(self, lng, lat):
        rdi = RasterDatasetInterpolator(_grid_path)
        px_value = rdi.get_location_info(lng, lat, method='near')

        return self.get_dom(px_value)

    def query(self, lng, lat):
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


