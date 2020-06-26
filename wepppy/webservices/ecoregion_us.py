# Copyright (c) 2016-2018, University of Idaho
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
from osgeo import ogr

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
def query_ecoregion():
    from pyproj import CRS, Transformer

    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        lat = request.args.get('lat', None)
        lng = request.args.get('lng', None)
        srs = request.args.get('srs', None)
    else:  # POST
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

    wgs_proj = CRS.from_proj4('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    if srs is not None:

        try:
            p1 = CRS.from_epsg(srs)
        except:
            return jsonify({'Error': 'could not initialize projection'})

        proj2wgs_transformer = Transformer.from_crs(p1, wgs_proj, always_xy=True)
        lng, lat = proj2wgs_transformer.transform(lng, lat)

    shapefile = _join(geodata_dir, "ecoregions/us_eco_l3/us_eco_l3.shp")
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dataSource = driver.Open(shapefile, 0)
    layer = dataSource.GetLayer()

    sf_proj = CRS.from_proj4(layer.GetSpatialRef().ExportToProj4())

    wgs2sf_transformer = Transformer.from_crs(wgs_proj, sf_proj, always_xy=True)
    e, n = wgs2sf_transformer.transform(lng, lat)

    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint_2D(e, n)
    layer.SetSpatialFilter(ogr.CreateGeometryFromWkt(point.ExportToWkt()))

    n = layer.GetFeatureCount()

    l1 = []
    l2 = []
    l3 = []
    for i in range(n):
        feature = layer.GetNextFeature()
        l1.append(feature.GetField("L1_KEY"))
        l2.append(feature.GetField("L2_KEY"))
        l3.append(feature.GetField("L3_KEY"))

    return jsonify({'Level1': l1,
                    'Level2': l2,
                    'Level3': l3,
                    'Longitude': lng,
                    'Latitude': lat})


if __name__ == '__main__':
    app.run()

