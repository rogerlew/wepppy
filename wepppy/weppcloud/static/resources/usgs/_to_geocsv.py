import json


def filter_geojson(fn, bbox):
    l, b, r, t = bbox

    assert l < r
    assert b < t

    fn = 'usgs_gage_locations.geojson'

    js = json.load(open(fn))

    _features = []
    for feature in js['features']:
        lng, lat = feature['geometry']['coordinates']
        if l < lng < r and b < lat < t:
            _features.append(feature)

    js['features'] = _features

    return js


if __name__ == "__main__":
    from pprint import pprint

    pprint(filter_geojson('usgs_gage_locations.geojson', [-117, 46.5, -116.5, 47]))
