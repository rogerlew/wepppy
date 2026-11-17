from __future__ import annotations

import pytest

from wepppy.topo.watershed_collection import validate_new_upload_polygon_geojson


pytestmark = pytest.mark.unit


def _payload(geometry: object) -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": geometry}],
    }


@pytest.mark.parametrize(
    "geometry",
    [
        None,
        {"type": "Point", "coordinates": [0, 0]},
        {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
        {"type": "GeometryCollection", "geometries": []},
        {"type": "Polygon", "coordinates": []},
    ],
)
def test_new_batch_upload_rejects_unsupported_geometry(geometry: object) -> None:
    with pytest.raises(ValueError, match="Polygon or MultiPolygon"):
        validate_new_upload_polygon_geojson(_payload(geometry))


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 1], [0, 0]]]},
        {
            "type": "MultiPolygon",
            "coordinates": [[[[0, 0], [1, 0], [0, 1], [0, 0]]]],
        },
    ],
)
def test_new_batch_upload_accepts_polygonal_geometry(geometry: object) -> None:
    validate_new_upload_polygon_geojson(_payload(geometry))
