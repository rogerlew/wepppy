"""Flask microservice that returns Level 1–3 U.S. EPA ecoregions.

The endpoint accepts either GET or POST requests with longitude/latitude pairs
plus an optional source spatial reference (``srs``). Coordinates can be in any
Proj4-compatible projection; inputs are reprojected to WGS84 before the query.
The service then intersects the point against the Level 3 shapefile stored
under :data:`geodata_dir`.
"""

from __future__ import annotations

from typing import Optional

from os.path import join as _join
from flask import Flask, Response, jsonify, request
from osgeo import ogr

from wepppy.all_your_base.geo import GeoTransformer, wgs84_proj4

geodata_dir = '/geodata/'


def safe_float_parse(value: object) -> Optional[float]:
    """Return ``float(value)`` or ``None`` if conversion fails."""
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return None


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def query_ecoregion() -> Response:
    """Return the EPA ecoregion identifiers covering the requested point."""

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

    if srs is not None:
        try:
            geo_transformer = GeoTransformer(src_proj4=srs,
                                             dst_proj4=wgs84_proj4)
            lng, lat = geo_transformer.transform(lng, lat)
        except:
            return jsonify({'Error': 'Could not transform lng, lat to wgs'})

    shapefile = _join(geodata_dir, "ecoregions/us_eco_l3/us_eco_l3.shp")
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dataSource = driver.Open(shapefile, 0)
    layer = dataSource.GetLayer()

    sf_proj = layer.GetSpatialRef().ExportToProj4()

    wgs2sf_transformer = GeoTransformer(src_proj4=wgs84_proj4, dst_proj4=sf_proj)
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
