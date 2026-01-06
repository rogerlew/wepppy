import json
from pathlib import Path

import pytest

from wepppy.topo.watershed_collection import WatershedFeature


pytestmark = pytest.mark.unit


def _build_feature() -> dict:
    return {
        "type": "Feature",
        "properties": {"Point_ID": 1},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [0.0, 0.0],
                    [1.0, 0.0],
                    [1.0, 1.0],
                    [0.0, 1.0],
                    [0.0, 0.0],
                ]
            ],
        },
    }


def test_save_geojson_uses_feature_crs(tmp_path: Path) -> None:
    feature = WatershedFeature(_build_feature(), runid="run-1", index=0, crs="EPSG:32611")
    output_path = tmp_path / "feature.geojson"
    feature.save_geojson(str(output_path))

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["crs"]["properties"]["name"] == "EPSG:32611"


def test_save_geojson_defaults_to_crs84(tmp_path: Path) -> None:
    feature = WatershedFeature(_build_feature(), runid="run-2", index=0)
    output_path = tmp_path / "feature.geojson"
    feature.save_geojson(str(output_path))

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["crs"]["properties"]["name"] == "urn:ogc:def:crs:OGC:1.3:CRS84"
