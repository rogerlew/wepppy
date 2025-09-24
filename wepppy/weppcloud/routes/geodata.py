"""Routes for geodata blueprint extracted from app.py."""

from ast import literal_eval
from pathlib import Path

from ._common import *  # noqa: F401,F403

from wepppy.all_your_base.geo import crop_geojson


_THISDIR = Path(__file__).resolve().parents[1]

geodata_bp = Blueprint('geodata', __name__)


@geodata_bp.route('/resources/usgs/gage_locations/')
def resources_usgs_gage_locations():
    bbox = request.args.get('bbox')
    bbox = literal_eval(bbox)
    return jsonify(crop_geojson(_join(str(_THISDIR), 'static/resources/usgs/usgs_gage_locations.geojson'), bbox=bbox))


@geodata_bp.route('/resources/snotel/snotel_locations/')
def resources_snotel_locations():
    bbox = request.args.get('bbox')
    bbox = literal_eval(bbox)
    return jsonify(crop_geojson(_join(str(_THISDIR), 'static/resources/snotel/snotel_2024_anu.geojson'), bbox=bbox))
