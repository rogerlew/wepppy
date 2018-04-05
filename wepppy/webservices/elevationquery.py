# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import math

from os.path import join as _join

from subprocess import Popen, PIPE
from flask import Flask, jsonify, request

geodata_dir = '/geodata/'


def safe_float_parse(x):
    """
    Tries to parse {x} as a float. Returns None if it fails.
    """
    try:
        return float(x)
    except:
        return None

        
app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def query_elevation():
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})
        
    if request.method == 'GET':
        lat = request.args.get('lat', None)
        lng = request.args.get('lng', None)
        srs = request.args.get('srs', None)
    else: # POST
        lat = request.json.get('lat', None)
        lng = request.json.get('lng', None)
        srs = request.json.get('srs', None)

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
        from pyproj import Proj, transform
        try:
            p1 = Proj(init=srs)
        except:
            return jsonify({'Error': 'could not initialize projection'})

        p2 = Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
        lng, lat = transform(p1, p2, lng, lat)

    img = 'n%02iw%03i' % (int(math.ceil(lat)), int(math.ceil(abs(lng))))
    src = _join(geodata_dir, 'ned1', '2016', img, 'img' + img + '_1.img')

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

