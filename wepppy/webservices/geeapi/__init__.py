# Copyright (c) 2016-2022, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import math

from os.path import join as _join

from subprocess import Popen, PIPE
from flask import Flask, jsonify, request

from wepppy.all_your_base.geo import GeoTransformer, wgs84_proj4

import ee

geodata_dir = '/geodata/'


def safe_float_parse(x):
    """
    Tries to parse {x} as a float. Returns None if it fails.
    """
    try:
        return float(x)
    except:
        return None


def safe_int_parse(x):
    """
    Tries to parse {x} as a int. Returns None if it fails.
    """
    try:
        return int(x)
    except:
        return None

        
app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    ee.Initialize()
            
    lat = safe_float_parse(request.args.get('lat', None))
    lng = safe_float_parse(request.args.get('lng', None))
    if lat is None or lng is None:
        return jsonify('Error: lng and lat are required')

    point = ee.Geometry.Point([lng, lat])

    start_date = request.args.get('start_date', '01-01')
    year = safe_int_parse(request.args.get('year', None))
    end_date = request.args.get('end_date', '12-31')
    if year is None:
        return jsonify('Error: year is required')

    dataset = ee.ImageCollection('UMT/NTSG/v2/LANDSAT/NPP')\
                .filter(ee.Filter.date(f'{year}-{start_date}', f'{year}-{end_date}'))
    npp = dataset.select('annualNPP').first()
    data = npp.sample(point, 30).first().getInfo()

    return jsonify({'year':year,
                    'start_date': start_date,
                    'end_date': end_date,
                    'lng': lng,
                    'lat': lat,
                    'data': data})


if __name__ == '__main__':
    app.run()

