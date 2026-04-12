from __future__ import annotations

import io
import json

import pytest
from pyproj import CRS
from shapely.geometry import Point

from wepppy.microservices.shape_converter.serialization import serialize_geojson, serialize_geoparquet


pytestmark = [pytest.mark.unit, pytest.mark.microservice]


def test_serialize_geojson_wgs84_uses_rfc_content_type() -> None:
    artifact = serialize_geojson(
        properties=({"name": "demo"},),
        geometries=(Point(-121.0, 45.0),),
        target_crs=CRS.from_epsg(4326),
        rfc7946_compliant=True,
    )

    payload = json.loads(artifact.content.decode("utf-8"))
    assert artifact.content_type == "application/geo+json"
    assert payload["type"] == "FeatureCollection"
    assert "crs" not in payload
    assert artifact.warnings == ()


def test_serialize_geojson_projected_marks_non_rfc_warning() -> None:
    artifact = serialize_geojson(
        properties=({"name": "demo"},),
        geometries=(Point(500000.0, 4980000.0),),
        target_crs=CRS.from_epsg(32610),
        rfc7946_compliant=False,
    )

    payload = json.loads(artifact.content.decode("utf-8"))
    assert artifact.content_type == "application/json"
    assert payload["crs"]["properties"]["name"] == "EPSG:32610"
    assert any("RFC 7946" in warning for warning in artifact.warnings)


def test_serialize_geoparquet_sets_geo_metadata() -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")

    artifact = serialize_geoparquet(
        properties=({"name": "demo"},),
        geometries=(Point(-121.0, 45.0),),
        target_crs=CRS.from_epsg(4326),
    )

    table = pq.read_table(io.BytesIO(artifact.content))
    assert artifact.content_type == "application/vnd.apache.parquet"

    metadata = dict(table.schema.metadata or {})
    assert b"geo" in metadata
    geo = json.loads(metadata[b"geo"].decode("utf-8"))

    assert geo["primary_column"] == "geometry"
    assert "geometry" in geo["columns"]
    assert geo["columns"]["geometry"]["encoding"] == "WKB"
    assert geo["columns"]["geometry"]["geometry_types"] == ["Point"]
    assert "crs" in geo["columns"]["geometry"]

    # Sanity: parquet table contains geometry binary column.
    assert table.schema.field("geometry").type == pa.binary()


def test_serialize_geoparquet_unknown_crs_warning() -> None:
    artifact = serialize_geoparquet(
        properties=({"name": "demo"},),
        geometries=(Point(10.0, 20.0),),
        target_crs=None,
    )

    assert any("omitted" in warning for warning in artifact.warnings)
