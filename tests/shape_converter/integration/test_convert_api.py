from __future__ import annotations

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import (
    build_minimal_line_dataset,
    build_minimal_point_dataset,
    build_minimal_polygon_dataset,
    build_zip_bytes,
)
from wepppy.microservices.shape_converter import app
from wepppy.microservices.shape_converter import create_app


pytestmark = [pytest.mark.integration, pytest.mark.microservice]


@pytest.mark.parametrize(
    ("entries", "expected_geometry_type"),
    [
        (build_minimal_point_dataset(prefix="point"), "Point"),
        (build_minimal_line_dataset(prefix="line"), "LineString"),
        (build_minimal_polygon_dataset(prefix="poly"), "Polygon"),
    ],
)
def test_convert_endpoint_geojson_wgs84_success_for_core_geometry_types(
    entries: dict[str, bytes],
    expected_geometry_type: str,
) -> None:
    archive_bytes = build_zip_bytes(entries)

    with TestClient(app) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("geometry.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert payload["features"][0]["geometry"]["type"] == expected_geometry_type


def test_convert_endpoint_returns_unknown_source_crs_for_missing_prj() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="missing", include_prj=False))

    with TestClient(app) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("missing.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "unknown_source_crs"
    assert payload["error"]["details"]


def test_convert_endpoint_accepts_shp_xml_sidecar_and_surfaces_warning() -> None:
    entries = build_minimal_point_dataset(prefix="sample")
    entries["sample.shp.xml"] = b"<metadata><creator>alice</creator></metadata>"
    archive_bytes = build_zip_bytes(entries)

    with TestClient(app) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("sample.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )
        metadata_response = client.get(response.headers["x-shape-converter-metadata-path"])

    assert response.status_code == 200
    metadata_payload = metadata_response.json()
    assert any(".shp.xml" in warning for warning in metadata_payload["warnings"])


def test_convert_endpoint_rejects_deferred_json_body_mode() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="sample"))

    with TestClient(app) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("sample.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "json_body",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "response_mode_not_supported"


def test_convert_endpoint_returns_utm_not_supported_for_extent() -> None:
    archive_bytes = build_zip_bytes(
        build_minimal_point_dataset(
            prefix="polar",
            include_prj=True,
            x_coord=10.0,
            y_coord=89.8,
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("polar.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "utm_wepppy_upper_left",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "utm_not_supported_for_extent"


def test_convert_endpoint_reuses_archive_path_traversal_control() -> None:
    archive_bytes = build_zip_bytes(
        {
            "../escape.shp": b"x",
            "safe.shx": b"y",
            "safe.dbf": b"z",
        }
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("invalid.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "archive_path_traversal"


def test_convert_cleanup_success_leaves_no_request_artifacts(tmp_path) -> None:  # noqa: ANN001
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="cleanup-success"))

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/convert",
            files={"archive": ("cleanup-success.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 200
    assert list(tmp_path.iterdir()) == []


def test_convert_cleanup_failure_leaves_no_request_artifacts(tmp_path) -> None:  # noqa: ANN001
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="cleanup-failure", include_prj=False))

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/convert",
            files={"archive": ("cleanup-failure.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unknown_source_crs"
    assert list(tmp_path.iterdir()) == []
