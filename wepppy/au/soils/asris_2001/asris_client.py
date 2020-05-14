import requests
import json
import os

from os.path import join as _join
from os.path import exists as _exists

from wepppy.all_your_base import isfloat

_thisdir = os.path.dirname(__file__)
_cache_dir = '/geodata/au/asris_2001/cache'

if not _exists(_cache_dir):
    _join(_thisdir, 'cache')

_url = 'http://www.asris.csiro.au/arcgis/rest/services/ASRIS/ASRIS_2001/MapServer/' \
       'identify?geometry={{x:{lng},y:{lat}}}&geometryType=esriGeometryPoint&' \
       'sr=4283&layers=all&layerDefs=&time=&layerTimeOptions=&tolerance=2&' \
       'mapExtent=110.43000000000004,-37.782905983857944,+156.07999999999905,-5.434188035140686&' \
       'imageDisplay=2048%2C2048%2C96&returnGeometry=false&maxAllowableOffset=&geometryPrecision=&' \
       'dynamicLayers=&returnZ=false&returnM=false&gdbVersion=&returnUnformattedValues=false&' \
       'returnFieldName=false&datumTransformations=&layerParameterValues=&mapRangeValues=&' \
       'layerRangeValues=&f=pjson'


_defaults = {
    'Bulk Density Topsoil g/cm3': 0.975,
    'Bulk Density Subsoil g/cm3': 1.2,
    'Clay Content Topsoil %': 21.0,
    'Clay Content Subsoil %': 39.0,
    'Silt Content Topsoil': 27.0,
    'Silt Content Subsoil': 33.0,
    'Sand Content Topsoil': 52.0,
    'Sand Content Subsoil': 29.0,
    'Texture Topsoil': 4.0,
    'Texture Subsoil': 2.0,
    'Available Water Topsoil mm': 41.0,
    'Available Water Subsoil mm': 80.75,
    'Saturated Hydraulic Topsoil mm/hr': 97.5,
    'Saturated Hydraulic Subsoil mm/hr': 100.0,
    'Topsoil Thickness m': 0.2,
    'Subsoil Thickness m': 0.475,
    'Solum Thickness m': 0.65,
    'Organic Carbon Topsoil %': 7.227,
    'Organic Carbon Subsoil %': 1.75,
    'Total Nitrogen Topsoil %': 0.396,
    'Extractable Phosphorus (NSW/VIC)': 0.001,
    'Total Phosphorus Topsoil': 0.036,
    'pH Topsoil': 4.25,
    'pH Subsoil': 4.3
}


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
            json.dump(d, fp, allow_nan=False)

    _d = {row['layerName'].replace(' (value/1000)', ''): row for row in d}
    for name in _d:
        if isfloat(_d[name]['attributes']['Pixel Value']):
            _d[name]['Value'] = float(_d[name]['attributes']['Pixel Value']) / 1000
        else:
            _d[name]['Value'] = _defaults[name]

    return _d
