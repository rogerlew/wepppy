from __future__ import annotations

import pytest

from wepppy.nodb.geojson_crs_inference import infer_geojson_crs

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_infer_geojson_crs_prefers_project_utm_for_utm_like_coordinates() -> None:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [464000.0, 5024000.0],
                        [464050.0, 5024050.0],
                    ],
                },
                "properties": {},
            }
        ],
    }

    inferred = infer_geojson_crs(
        payload,
        explicit_crs=None,
        project_crs="EPSG:32610",
        configured_crs="EPSG:4326",
        project_bounds=(463900.0, 5023900.0, 464200.0, 5024200.0),
    )

    assert inferred.crs == "EPSG:32610"
    assert inferred.source == "inferred_project_utm_coordinates"


def test_infer_geojson_crs_falls_back_to_wgs_for_degree_coordinates() -> None:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-123.45, 45.12],
                        [-123.44, 45.11],
                    ],
                },
                "properties": {},
            }
        ],
    }

    inferred = infer_geojson_crs(
        payload,
        explicit_crs=None,
        project_crs="EPSG:32610",
        configured_crs="EPSG:3857",
        project_bounds=(463900.0, 5023900.0, 464200.0, 5024200.0),
    )

    assert inferred.crs == "EPSG:4326"
    assert inferred.source == "inferred_wgs84_coordinates"


def test_infer_geojson_crs_uses_configured_when_coordinates_are_ambiguous() -> None:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [2000000.0, 3000000.0],
                        [2000050.0, 3000100.0],
                    ],
                },
                "properties": {},
            }
        ],
    }

    inferred = infer_geojson_crs(
        payload,
        explicit_crs=None,
        project_crs=None,
        configured_crs="EPSG:3857",
        project_bounds=None,
    )

    assert inferred.crs == "EPSG:3857"
    assert inferred.source == "configured_input_crs"
