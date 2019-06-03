import json
import string
from os.path import split as _split
from os.path import join as _join

from glob import glob

from wepppy.all_your_base import RasterDatasetInterpolator

_esdac_esdb_raster_dir = '/geodata/eu/ESDAC_ESDB_rasters/'


def _attr_fmt(attr):
    _attr = ''.join(c for c in attr.lower() if
                   c in string.ascii_lowercase or c in string.digits)

    if 'lv' in _attr:
        _attr = _attr.replace('lv', 'lev')

    _replacements = {'txsrfdo': 'textsrfdom',
                     'txsrfse': 'textsrfsec',
                     'txsubdo': 'textsubdom',
                     'txsubse': 'textsubsec',
                     'txdepchg': 'textdepchg',
                     'usedo': 'usedom',
                     'erodi': 'erodibility'
                     }

    if _attr in _replacements:
        _attr = _replacements[_attr]

    return _attr


class ESDAC:
    def __init__(self):
        # { attr, raster_file_path}
        catalog = glob(_join(_esdac_esdb_raster_dir, '*.tif'))
        self.catalog = {_attr_fmt(_split(fn)[-1][:-4]): fn for fn in catalog}

        # { attr, raster_attribute table}
        rats = {}
        for fn in catalog:
            rats[_attr_fmt(_split(fn)[-1][:-4])] = self._rat_extract(fn[:-4] + '.json')
        self.rats = rats

    @staticmethod
    def _rat_extract(fn):
        with open(fn.replace('.tif', '.json')) as fp:
            info = json.load(fp)

        rows = info['rat']['row']

        d = {}
        for r in rows:
            r = r['f']

            if len(r) == 3:
                d[str(r[0])] = str(r[2])
            elif len(r) == 2:
                d[str(r[0])] = str(r[0])
            else:
                raise Exception

        return d

    def query(self, lng, lat, attrs):
        from .legends import get_legend

        catalog = self.catalog
        rats = self.rats
        d = {}

        for attr in attrs:
            attr = _attr_fmt(attr)
            assert attr in catalog, attr
            rdi = RasterDatasetInterpolator(catalog[attr])
            x = rdi.get_location_info(lng, lat, method='near')
            px_val = str(int(x))
            short = rats[attr][px_val]
            legend = get_legend(attr)
            try:
                long = legend['table'][short]
            except KeyError:
                long = 'None'

            d[attr] = px_val, short, long

        return d