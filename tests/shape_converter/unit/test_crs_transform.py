from __future__ import annotations

import pytest
from pyproj import CRS
from shapely.geometry import Point

from wepppy.microservices.shape_converter.crs import parse_source_crs, reproject_geometries, resolve_target_crs
from wepppy.microservices.shape_converter.errors import ShapeConverterError


pytestmark = [pytest.mark.unit, pytest.mark.microservice]


def test_resolve_target_crs_same_as_shapefile_unknown_source() -> None:
    plan = resolve_target_crs(
        target_crs_token="same_as_shapefile",
        source_crs=None,
        source_bounds=(10.0, 20.0, 10.0, 20.0),
    )

    assert plan.source_crs is None
    assert plan.target_crs is None
    assert plan.rfc7946_compliant_geojson is False
    assert plan.warnings


def test_parse_source_crs_falls_back_to_mapping_when_wkt_is_invalid() -> None:
    parsed = parse_source_crs(
        crs_wkt="NOT_A_VALID_WKT",
        crs_mapping="EPSG:4326",
    )

    assert parsed is not None
    assert parsed.to_epsg() == 4326


def test_resolve_target_crs_wgs84_requires_known_source() -> None:
    with pytest.raises(ShapeConverterError) as exc_info:
        resolve_target_crs(
            target_crs_token="wgs84",
            source_crs=None,
            source_bounds=(10.0, 20.0, 10.0, 20.0),
        )

    assert exc_info.value.code == "unknown_source_crs"


def test_resolve_target_crs_utm_uses_upper_left_corner_rule() -> None:
    plan = resolve_target_crs(
        target_crs_token="utm_wepppy_upper_left",
        source_crs=CRS.from_epsg(4326),
        source_bounds=(-121.0, 44.9, -120.5, 45.2),
    )

    assert plan.target_crs is not None
    assert plan.target_crs.to_epsg() == 32610


def test_resolve_target_crs_utm_rejects_out_of_domain_latitude() -> None:
    with pytest.raises(ShapeConverterError) as exc_info:
        resolve_target_crs(
            target_crs_token="utm_wepppy_upper_left",
            source_crs=CRS.from_epsg(4326),
            source_bounds=(10.0, 89.5, 10.2, 89.8),
        )

    assert exc_info.value.code == "utm_not_supported_for_extent"


def test_reproject_geometries_reprojects_wgs84_to_utm() -> None:
    source_point = Point(-121.0, 45.0)
    transformed = reproject_geometries(
        geometries=(source_point,),
        source_crs=CRS.from_epsg(4326),
        target_crs=CRS.from_epsg(32610),
    )

    assert transformed[0] is not None
    assert transformed[0].x != pytest.approx(source_point.x)
    assert transformed[0].y != pytest.approx(source_point.y)


def test_reproject_geometries_surfaces_reprojection_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_transformer_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "wepppy.microservices.shape_converter.crs.Transformer.from_crs",
        _raise_transformer_error,
    )

    with pytest.raises(ShapeConverterError) as exc_info:
        reproject_geometries(
            geometries=(Point(-121.0, 45.0),),
            source_crs=CRS.from_epsg(4326),
            target_crs=CRS.from_epsg(32610),
        )

    assert exc_info.value.code == "reprojection_failed"
