"""Simple Flask endpoint for querying 1 arc-second NED elevation tiles."""

from __future__ import annotations

import math
from typing import Optional

from os.path import join as _join

from subprocess import Popen, PIPE
from flask import Flask, Response, jsonify, request

from wepppy.all_your_base.geo import GeoTransformer, wgs84_proj4

geodata_dir = '/geodata/'


def safe_float_parse(value: object) -> Optional[float]:
    """Return ``float(value)`` or ``None`` when parsing fails."""
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return None


app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify("OK")

@app.route('/', methods=['GET', 'POST'])
def query_elevation() -> Response:
    """Return the NED elevation at the provided lat/long."""
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    lat = request.args.get('lat', None)
    lng = request.args.get('lng', None)
    srs = request.args.get('srs', None)

    if lat is None:
        d = request.get_json(force=True)
        lat = d.get('lat', None)
        lng = d.get('lng', None)
        srs = d.get('srs', None)

    if lat is None:
        return jsonify({'Error': 'lat not supplied'})

    if lng is None:
        return jsonify({'Error': 'lng not supplied'})

    lat = safe_float_parse(lat)
    lng = safe_float_parse(lng)

    if lat is None:
        return jsonify({'Error': 'could not parse lat'})

    if lng is None:
        return jsonify({'Error': 'could not parse lng'})

    if srs is not None:
        try:
            geo_transformer = GeoTransformer(src_proj4=srs,
                                             dst_proj4=wgs84_proj4)
            lng, lat = geo_transformer.transform(lng, lat)
        except:
            return jsonify({'Error': 'Could not transform lng, lat to wgs'})

    img = 'n%02iw%03i' % (int(math.ceil(lat)), int(math.ceil(abs(lng))))
    src = _join(geodata_dir, 'ned1', '2016', img, 'img' + img + '_1.img')

#    src = _join(geodata_dir, 'ned13/2016/.vrt')

    cmd = ['gdallocationinfo', '-geoloc', '-valonly', src, str(lng), str(lat)]
#    print cmd

    p = Popen(cmd, stdout=PIPE)
    p.wait()

    try:
        elev = float(p.stdout.read().strip())
    except:
        elev = float('nan')

    return jsonify({'Elevation': elev,
                    'Units': 'm',
                    'Longitude': lng,
                    'Latitude': lat})


if __name__ == '__main__':
    app.run()
