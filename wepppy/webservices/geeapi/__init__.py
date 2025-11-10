"""Google Earth Engine helper endpoint for Net Primary Productivity queries."""

from __future__ import annotations

from typing import Any, Optional

from flask import Flask, Response, jsonify, request

try:  # pragma: no cover - optional dependency
    import ee  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    ee = None  # type: ignore[assignment]

geodata_dir = '/geodata/'


def safe_float_parse(value: object) -> Optional[float]:
    """Return ``float(value)`` or ``None`` when conversion fails."""
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return None


def safe_int_parse(value: object) -> Optional[int]:
    """Return ``int(value)`` or ``None`` on failure."""
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None

        
app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index() -> Response:
    """Query NPP from the ``UMT/NTSG/v2/LANDSAT/NPP`` collection at a location."""
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if ee is None:
        return jsonify({'Error': 'google-earth-engine client not installed'})

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
