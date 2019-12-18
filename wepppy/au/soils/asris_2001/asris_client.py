import requests
import json
import os

from os.path import join as _join
from os.path import exists as _exists

_thisdir = os.path.dirname(__file__)
_cache_dir = _join(_thisdir, 'cache')

_url = 'http://www.asris.csiro.au/arcgis/rest/services/ASRIS/ASRIS_2001/MapServer/' \
       'identify?geometry={{x:{lng},y:{lat}}}&geometryType=esriGeometryPoint&' \
       'sr=4283&layers=all&layerDefs=&time=&layerTimeOptions=&tolerance=2&' \
       'mapExtent=110.43000000000004,-37.782905983857944,+156.07999999999905,-5.434188035140686&' \
       'imageDisplay=2048%2C2048%2C96&returnGeometry=false&maxAllowableOffset=&geometryPrecision=&' \
       'dynamicLayers=&returnZ=false&returnM=false&gdbVersion=&returnUnformattedValues=false&' \
       'returnFieldName=false&datumTransformations=&layerParameterValues=&mapRangeValues=&' \
       'layerRangeValues=&f=pjson'


def query_asris(lng, lat):
    global _url

    lng = round(lng, 2)
    lat = round(lat, 2)

    if not _exists(_cache_dir):
        os.mkdir(_cache_dir)

    d = None
    fn = _join(_cache_dir, '{lng:0.2f},{lat:0.2f}.json'.format(lng=lng, lat=lat))
    if _exists(fn):
        with open(fn) as fp:
            d = json.load(fp)

    else:
        r = requests.get(_url.format(lat=lat, lng=lng))
        assert r.status_code == 200
        d = json.loads(r.text)
        d = d['results']

        with open(fn, 'w') as fp:
            json.dump(d, fp)

    _d = {row['layerName'].replace(' (value/1000)', ''): row for row in d}
    for name in _d:
        _d[name]['Value'] = float(_d[name]['attributes']['Pixel Value']) / 1000

    return _d
