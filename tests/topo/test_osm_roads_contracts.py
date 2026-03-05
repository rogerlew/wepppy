from __future__ import annotations

import inspect

import pytest

from wepppy.topo.osm_roads import (
    DEFAULT_INCLUDE_TAGS,
    OSMRoadsCacheError,
    OSMRoadsRequest,
    OSMRoadsResult,
    OSMRoadsService,
)
from wepppy.topo.osm_roads.errors import OSMRoadsValidationError

pytestmark = pytest.mark.unit


def test_request_defaults_match_contract() -> None:
    req = OSMRoadsRequest(
        aoi_wgs84_geojson={"type": "Polygon", "coordinates": [[[-116.0, 46.0], [-115.9, 46.0], [-115.9, 46.1], [-116.0, 46.1], [-116.0, 46.0]]]},
        target_epsg=32611,
        highway_filter=("motorway",),
    )

    assert req.include_tags == DEFAULT_INCLUDE_TAGS
    assert req.force_refresh is False
    assert req.allow_stale_on_error is True
    assert req.allow_expired_on_error is True


def test_result_shape_is_instantiable() -> None:
    result = OSMRoadsResult(
        roads_geojson_path="/tmp/roads.geojson",
        cache_key="osm_roads_v1:req:abc:def",
        cache_hit=True,
        stale_served=False,
        fetched_at_utc="2026-03-05T00:00:00+00:00",
        source="cache",
        feature_count=10,
        target_epsg=32611,
        bbox_wgs84=(-116.0, 46.0, -115.9, 46.1),
    )

    assert result.source == "cache"
    assert result.feature_count == 10


def test_service_protocol_signature_is_stable() -> None:
    signature = inspect.signature(OSMRoadsService.get_roads)
    assert list(signature.parameters) == ["self", "req", "logger"]
    assert signature.parameters["logger"].kind is inspect.Parameter.KEYWORD_ONLY


def test_typed_error_contract_fields() -> None:
    err = OSMRoadsCacheError("cache broken", code="cache_error", context={"cache_key": "abc"})
    assert err.code == "cache_error"
    assert err.message == "cache broken"
    assert err.context["cache_key"] == "abc"


def test_validation_error_defaults_code() -> None:
    err = OSMRoadsValidationError("bad request")
    assert err.code == "validation_error"
