from __future__ import annotations

import asyncio
import importlib
import json

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import (
    SENSITIVE_METADATA_MARKERS,
    build_minimal_line_dataset,
    build_minimal_point_dataset,
    build_minimal_polygon_dataset,
    build_sensitive_metadata_payload,
    build_xml_entity_expansion_payload,
    build_zip_bytes,
)
from wepppy.microservices.shape_converter import app
from wepppy.microservices.shape_converter import create_app


pytestmark = [pytest.mark.integration, pytest.mark.microservice]
shape_converter_app_module = importlib.import_module("wepppy.microservices.shape_converter.app")


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


def test_convert_endpoint_does_not_expose_shp_xml_sensitive_content() -> None:
    entries = build_minimal_point_dataset(prefix="sample")
    entries["sample.shp.xml"] = build_sensitive_metadata_payload(include_xml_shell=True)
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
    payload_text = json.dumps(metadata_response.json(), sort_keys=True)
    for marker in SENSITIVE_METADATA_MARKERS:
        assert marker not in payload_text


def test_convert_endpoint_does_not_expose_qmd_sensitive_content() -> None:
    entries = build_minimal_point_dataset(prefix="sample")
    entries["sample.qmd"] = build_sensitive_metadata_payload(include_xml_shell=False)
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
    payload = metadata_response.json()
    payload_text = json.dumps(payload, sort_keys=True)
    assert not any(".qmd" in warning.lower() for warning in payload["warnings"])
    for marker in SENSITIVE_METADATA_MARKERS:
        assert marker not in payload_text


def test_convert_endpoint_returns_json_body_relay_payload_for_geojson_output() -> None:
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

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert payload["geojson"]["type"] == "FeatureCollection"
    assert payload["metadata"]["output_format"] == "geojson"
    assert payload["metadata"]["target_crs"] == "wgs84"


def test_convert_endpoint_rejects_json_body_for_geoparquet_output() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="sample"))

    with TestClient(app) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("sample.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geoparquet",
                "target_crs": "wgs84",
                "response_mode": "json_body",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_request"
    assert "json_body" in payload["error"]["details"]
    assert "geojson" in payload["error"]["details"].lower()


def test_convert_endpoint_explicit_download_mode_remains_backward_compatible() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="download-mode"))

    with TestClient(app) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("download-mode.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "download",
            },
        )
        metadata_response = client.get(response.headers["x-shape-converter-metadata-path"])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/geo+json")
    assert "attachment;" in response.headers["content-disposition"]
    assert metadata_response.status_code == 200
    assert metadata_response.json()["target_crs"] == "wgs84"


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


@pytest.mark.parametrize("suffix", [".xml", ".gml"])
def test_convert_endpoint_rejects_entity_expansion_sidecars(suffix: str) -> None:
    entries = build_minimal_point_dataset(prefix="sample")
    entries[f"sample{suffix}"] = build_xml_entity_expansion_payload(root_tag="dataset")
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

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_archive"
    assert "unsupported file extension" in payload["error"]["message"].lower()


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


def test_convert_parser_loop_timeout_returns_canonical_timeout_and_cleans_scratch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # noqa: ANN001
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="timeout-parser"))
    observed_cancel = {"value": False}

    async def _stalled_convert(**kwargs):  # noqa: ANN003
        scratch = kwargs["scratch"]
        scratch.extraction_root.mkdir(parents=True, exist_ok=True)
        (scratch.extraction_root / "partial.txt").write_text("partial", encoding="utf-8")
        try:
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            observed_cancel["value"] = True
            raise

    monkeypatch.setattr(shape_converter_app_module, "_CONVERT_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(shape_converter_app_module, "convert_uploaded_archive", _stalled_convert)

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/convert",
            files={"archive": ("timeout-parser.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 408
    payload = response.json()
    assert payload["error"]["code"] == "request_timeout"
    assert observed_cancel["value"] is True
    assert list(tmp_path.iterdir()) == []
