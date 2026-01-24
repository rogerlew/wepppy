"""Routes for geodata blueprint extracted from app.py."""

import json
from pathlib import Path
from typing import Sequence

from ._common import *  # noqa: F401,F403

from wepppy.all_your_base.geo import crop_geojson


_THISDIR = Path(__file__).resolve().parents[1]

geodata_bp = Blueprint('geodata', __name__)


def _parse_bbox(raw: str) -> Sequence[float]:
    if raw is None:
        raise ValueError("bbox is required")
    text = str(raw).strip()
    if not text:
        raise ValueError("bbox is required")

    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip()
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = f"[{cleaned[1:-1]}]"
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1]
        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        data = parts

    if not isinstance(data, (list, tuple)) or len(data) != 4:
        raise ValueError("bbox must be a 4-item array")

    try:
        bbox = [float(value) for value in data]
    except (TypeError, ValueError) as exc:
        raise ValueError("bbox values must be numeric") from exc

    return bbox


@geodata_bp.route('/resources/usgs/gage_locations/')
def resources_usgs_gage_locations():
    bbox = _parse_bbox(request.args.get('bbox'))
    return jsonify(crop_geojson(_join(str(_THISDIR), 'static/resources/usgs/usgs_gage_locations.geojson'), bbox=bbox))


@geodata_bp.route('/resources/snotel/snotel_locations/')
def resources_snotel_locations():
    bbox = _parse_bbox(request.args.get('bbox'))
    return jsonify(crop_geojson(_join(str(_THISDIR), 'static/resources/snotel/snotel_2024_anu.geojson'), bbox=bbox))
