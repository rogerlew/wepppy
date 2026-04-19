from __future__ import annotations

import asyncio
import errno
import importlib
import json
import logging
import pickle
import signal
import subprocess
from types import SimpleNamespace

import pytest
from pyproj import CRS

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import (
    SENSITIVE_METADATA_MARKERS,
    build_minimal_line_dataset,
    build_minimal_point_dataset,
    build_sensitive_metadata_payload,
    build_xml_entity_expansion_payload,
    build_zip_bytes,
)
from wepppy.microservices.shape_converter import create_app


pytestmark = [pytest.mark.unit, pytest.mark.microservice]
shape_converter_app_module = importlib.import_module("wepppy.microservices.shape_converter.app")
shape_converter_convert_module = importlib.import_module("wepppy.microservices.shape_converter.convert")
shape_converter_crs_module = importlib.import_module("wepppy.microservices.shape_converter.crs")
shape_converter_serialization_module = importlib.import_module(
    "wepppy.microservices.shape_converter.serialization"
)
shape_converter_parser_worker_module = importlib.import_module(
    "wepppy.microservices.shape_converter.convert_parser_worker"
)


def test_convert_geojson_wgs84_download_and_metadata_sidecar() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/geo+json")
        assert "attachment;" in response.headers["content-disposition"]

        body = response.json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) == 1

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        metadata_response = client.get(metadata_path)

    assert metadata_response.status_code == 200
    metadata = metadata_response.json()
    assert metadata["target_crs"] == "wgs84"
    assert metadata["output_format"] == "geojson"
    assert metadata["rfc7946_compliant_geojson"] is True
    assert metadata["warnings"] == []


def test_convert_geojson_wgs84_explicit_download_mode_is_backward_compatible() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads-explicit-download"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads-explicit-download.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "download",
            },
        )

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        metadata_response = client.get(metadata_path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/geo+json")
    assert "attachment;" in response.headers["content-disposition"]
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()
    assert metadata["output_format"] == "geojson"
    assert metadata["target_crs"] == "wgs84"


def test_convert_download_content_disposition_uses_rfc5987_filename_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads-special-name"))

    async def _fake_convert_uploaded_archive(**kwargs):  # noqa: ANN003
        return shape_converter_convert_module.ConvertedArtifact(
            request_id=str(kwargs["request_id"]),
            filename='roads "ß".geojson',
            content_type="application/geo+json",
            content=b'{"type":"FeatureCollection","features":[]}',
            metadata={"output_format": "geojson", "target_crs": "wgs84", "warnings": []},
        )

    monkeypatch.setattr(shape_converter_app_module, "convert_uploaded_archive", _fake_convert_uploaded_archive)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads-special-name.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 200
    content_disposition = response.headers["content-disposition"]
    assert "attachment;" in content_disposition
    assert "filename*=" in content_disposition
    assert "UTF-8''" in content_disposition
    assert "%C3%9F" in content_disposition
    assert "\n" not in content_disposition
    assert "\r" not in content_disposition


def test_convert_accepts_shp_xml_sidecar_and_warns_user() -> None:
    entries = build_minimal_point_dataset(prefix="roads")
    entries["roads.shp.xml"] = (
        b"<metadata><creator>alice</creator><path>/Users/alice/private</path></metadata>"
    )
    archive_bytes = build_zip_bytes(entries)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        metadata_response = client.get(metadata_path)

    assert response.status_code == 200
    metadata = metadata_response.json()
    assert any(".shp.xml" in warning for warning in metadata["warnings"])
    assert any("generally not advisable" in warning.lower() for warning in metadata["warnings"])


def test_convert_shp_xml_privacy_does_not_expose_sidecar_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    entries = build_minimal_point_dataset(prefix="roads")
    entries["roads.shp.xml"] = build_sensitive_metadata_payload(include_xml_shell=True)
    archive_bytes = build_zip_bytes(entries)
    caplog.set_level(logging.INFO, logger="wepppy.microservices.shape_converter.app")

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        metadata_response = client.get(metadata_path)

    assert response.status_code == 200
    metadata_payload = metadata_response.json()
    payload_text = json.dumps(metadata_payload, sort_keys=True)
    assert any(".shp.xml" in warning for warning in metadata_payload["warnings"])
    for marker in SENSITIVE_METADATA_MARKERS:
        assert marker not in payload_text
        assert marker not in caplog.text


def test_convert_accepts_qmd_sidecar_and_unlinks_it() -> None:
    entries = build_minimal_point_dataset(prefix="roads")
    entries["roads.qmd"] = b"qmd metadata should be stripped"
    archive_bytes = build_zip_bytes(entries)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        metadata_response = client.get(metadata_path)

    assert response.status_code == 200
    metadata = metadata_response.json()
    assert metadata["target_crs"] == "wgs84"
    assert not any(".qmd" in warning.lower() for warning in metadata["warnings"])


def test_convert_qmd_privacy_does_not_expose_sidecar_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    entries = build_minimal_point_dataset(prefix="roads")
    entries["roads.qmd"] = build_sensitive_metadata_payload(include_xml_shell=False)
    archive_bytes = build_zip_bytes(entries)
    caplog.set_level(logging.INFO, logger="wepppy.microservices.shape_converter.app")

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        metadata_response = client.get(metadata_path)

    assert response.status_code == 200
    metadata_payload = metadata_response.json()
    payload_text = json.dumps(metadata_payload, sort_keys=True)
    for marker in SENSITIVE_METADATA_MARKERS:
        assert marker not in payload_text
        assert marker not in caplog.text


def test_convert_json_body_returns_relay_payload_for_geojson_output() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "json_body",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "x-shape-converter-metadata-path" not in response.headers
    payload = response.json()
    assert payload["request_id"]
    assert payload["geojson"]["type"] == "FeatureCollection"
    assert payload["metadata"]["output_format"] == "geojson"
    assert payload["metadata"]["target_crs"] == "wgs84"
    assert payload["metadata"]["projection_status"] == "known"
    assert isinstance(payload["metadata"]["attribute_schema"], list)
    assert payload["metadata"]["attribute_schema"]
    assert "nullability_note" in payload["metadata"]["attribute_schema"][0]


def test_convert_preflight_options_returns_scoped_cors_headers_for_allowed_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SHAPE_CONVERTER_RELAY_CORS_ALLOWED_ORIGINS",
        "https://relay-client.example",
    )

    with TestClient(create_app()) as client:
        response = client.options(
            "/v1/convert",
            headers={
                "Origin": "https://relay-client.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 204
    assert response.headers["access-control-allow-origin"] == "https://relay-client.example"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]


def test_convert_preflight_options_without_requested_method_passes_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SHAPE_CONVERTER_RELAY_CORS_ALLOWED_ORIGINS",
        "https://relay-client.example",
    )

    with TestClient(create_app()) as client:
        response = client.options(
            "/v1/convert",
            headers={"Origin": "https://relay-client.example"},
        )

    assert response.status_code == 405
    assert response.headers["access-control-allow-origin"] == "https://relay-client.example"


def test_convert_json_body_includes_cors_headers_for_allowed_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SHAPE_CONVERTER_RELAY_CORS_ALLOWED_ORIGINS",
        "https://relay-client.example",
    )
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="relay-cors"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("relay-cors.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "json_body",
            },
            headers={"Origin": "https://relay-client.example"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://relay-client.example"
    assert "x-shape-converter-request-id" in response.headers["access-control-expose-headers"].lower()


def test_convert_json_body_disallowed_origin_does_not_include_cors_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SHAPE_CONVERTER_RELAY_CORS_ALLOWED_ORIGINS",
        "https://relay-client.example",
    )
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="relay-cors-disallowed"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("relay-cors-disallowed.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "json_body",
            },
            headers={"Origin": "https://not-allowed.example"},
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_convert_json_body_wildcard_origin_sets_star_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHAPE_CONVERTER_RELAY_CORS_ALLOWED_ORIGINS", "*")
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="relay-cors-wildcard"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("relay-cors-wildcard.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "json_body",
            },
            headers={"Origin": "https://any-origin.example"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_convert_json_body_rejects_non_geojson_output_format() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
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


def test_convert_geoparquet_download_success() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geoparquet",
                "target_crs": "wgs84",
            },
        )

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        metadata_response = client.get(metadata_path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.apache.parquet")
    metadata = metadata_response.json()
    assert metadata["output_format"] == "geoparquet"


def test_convert_missing_prj_wgs84_returns_unknown_source_crs() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="missing", include_prj=False))

    with TestClient(create_app()) as client:
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


def test_convert_invalid_prj_wgs84_returns_invalid_source_crs() -> None:
    archive_bytes = build_zip_bytes(
        build_minimal_point_dataset(
            prefix="invalid-prj",
            include_prj=True,
            prj_text="NOT_A_VALID_WKT",
        )
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("invalid-prj.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_source_crs"
    assert "malformed" in payload["error"]["details"].lower()


def test_convert_same_as_shapefile_unknown_source_crs_preserves_coordinates() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="unknown", include_prj=False))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("unknown.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "same_as_shapefile",
            },
        )
        metadata_response = client.get(response.headers["x-shape-converter-metadata-path"])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert payload.get("crs") is None

    metadata = metadata_response.json()
    assert metadata["output_crs"] is None
    assert metadata["rfc7946_compliant_geojson"] is False
    assert any("unknown" in warning.lower() for warning in metadata["warnings"])


def test_convert_same_as_shapefile_invalid_source_crs_preserves_coordinates() -> None:
    archive_bytes = build_zip_bytes(
        build_minimal_point_dataset(
            prefix="invalid-same-as",
            include_prj=True,
            prj_text="NOT_A_VALID_WKT",
        )
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("invalid-same-as.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "same_as_shapefile",
            },
        )
        metadata_response = client.get(response.headers["x-shape-converter-metadata-path"])

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert payload.get("crs") is None

    metadata = metadata_response.json()
    assert metadata["projection_status"] == "invalid"
    assert metadata["output_crs"] is None
    assert any("invalid" in warning.lower() for warning in metadata["warnings"])


def test_convert_same_as_shapefile_projected_geojson_is_non_rfc() -> None:
    utm_wkt = CRS.from_epsg(32611).to_wkt(version="WKT1_GDAL")
    archive_bytes = build_zip_bytes(
        build_minimal_point_dataset(
            prefix="projected",
            include_prj=True,
            prj_text=utm_wkt,
        )
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("projected.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "same_as_shapefile",
            },
        )

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        metadata_response = client.get(metadata_path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["crs"]["properties"]["name"].startswith("EPSG:")

    metadata = metadata_response.json()
    assert metadata["rfc7946_compliant_geojson"] is False
    assert any("RFC 7946" in warning for warning in metadata["warnings"])


def test_convert_returns_archive_path_traversal_for_zip_slip_input() -> None:
    archive_bytes = build_zip_bytes(
        {
            "../escape.shp": b"x",
            "safe.shx": b"y",
            "safe.dbf": b"z",
        }
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("traversal.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "archive_path_traversal"


@pytest.mark.parametrize("suffix", [".xml", ".gml"])
def test_convert_rejects_entity_expansion_sidecars(suffix: str) -> None:
    entries = build_minimal_point_dataset(prefix="roads")
    entries[f"roads{suffix}"] = build_xml_entity_expansion_payload(root_tag="metadata")
    archive_bytes = build_zip_bytes(entries)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_archive"
    assert "unsupported file extension" in payload["error"]["message"].lower()


def test_convert_returns_missing_required_sidecar_error() -> None:
    archive_bytes = build_zip_bytes(
        {
            "sample.shp": b"x",
            "sample.shx": b"y",
        }
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("missing.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_required_sidecar"


def test_convert_returns_invalid_shapefile_for_corrupt_geometry_payload() -> None:
    archive_bytes = build_zip_bytes(
        {
            "sample.shp": b"not_a_real_shapefile",
            "sample.shx": b"still_bad",
            "sample.dbf": b"also_bad",
            "sample.prj": CRS.from_epsg(4326).to_wkt(version="WKT1_GDAL").encode("utf-8"),
        }
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("corrupt.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_shapefile"


def test_convert_returns_archive_quota_exceeded_for_member_count_limit() -> None:
    entries = build_minimal_point_dataset(prefix="base")
    for idx in range(198):
        entries[f"extras/extra_{idx}.cpg"] = b"utf-8"
    archive_bytes = build_zip_bytes(entries)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("members.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "archive_quota_exceeded"


def test_convert_rejects_vertex_heavy_features_with_archive_quota_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_line_dataset(prefix="vertex-limit"))
    monkeypatch.setattr(shape_converter_convert_module, "_MAX_VERTICES_PER_FEATURE", 1)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("vertex-limit.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["code"] == "archive_quota_exceeded"
    assert "vertex_limit_exceeded" in payload["error"]["details"]


def test_convert_rejects_multipart_payload_exceeding_part_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="multipart-parts"))
    monkeypatch.setattr(shape_converter_app_module, "_MULTIPART_MAX_PARTS", 3)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("multipart-parts.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "download",
            },
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["code"] == "invalid_request"
    assert "max-part limit" in payload["error"]["message"].lower()


def test_convert_rejects_multipart_string_field_exceeding_size_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="multipart-field"))
    monkeypatch.setattr(shape_converter_app_module, "_MULTIPART_MAX_FIELD_BYTES", 14)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("multipart-field.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "download-download-download",
            },
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["code"] == "invalid_request"
    assert "size limit" in payload["error"]["message"].lower()


def test_convert_returns_service_saturated_when_scratch_free_space_is_insufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="scratch-free-space"))
    disk_usage = SimpleNamespace(total=1024, used=1000, free=24)
    monkeypatch.setattr(shape_converter_convert_module.shutil, "disk_usage", lambda _path: disk_usage)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("scratch-free-space.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "service_saturated"


def test_convert_returns_archive_quota_exceeded_when_archive_write_exceeds_request_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="archive-write-quota"))
    monkeypatch.setattr(shape_converter_convert_module, "_REQUEST_SCRATCH_QUOTA_BYTES", 1)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("archive-write-quota.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["code"] == "archive_quota_exceeded"
    assert "archive_write" in payload["error"]["details"]


def test_convert_returns_archive_quota_exceeded_when_parser_budget_exceeds_request_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="parser-budget-quota"))
    monkeypatch.setattr(shape_converter_convert_module, "_REQUEST_SCRATCH_QUOTA_BYTES", 10_000)
    monkeypatch.setattr(shape_converter_convert_module, "_MAX_PARSER_PAYLOAD_BYTES", 20_000)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("parser-budget-quota.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["code"] == "archive_quota_exceeded"
    assert "parser_payload_budget" in payload["error"]["details"]


def test_convert_maps_enospc_os_error_to_service_saturated() -> None:
    mapped = shape_converter_convert_module._map_capacity_os_error(
        exc=OSError(errno.ENOSPC, "no space left on device"),
        stage="unit_test",
        fallback_code="reprojection_failed",
        fallback_message="fallback",
        fallback_status_code=500,
    )

    assert mapped.code == "service_saturated"
    assert mapped.status_code == 503


def test_convert_emits_structured_duration_observability_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="duration-log"))
    caplog.set_level(logging.INFO, logger="wepppy.microservices.shape_converter.app")

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("duration-log.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 200
    assert "\"event\":\"shape_converter_convert_completed\"" in caplog.text
    assert "\"convert_duration_ms\":" in caplog.text


def test_convert_returns_reprojection_failed_when_transformer_init_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))

    def _raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(shape_converter_crs_module.Transformer, "from_crs", _raise_runtime_error)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "utm_wepppy_upper_left"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "reprojection_failed"
    assert payload["error"]["details"]


def test_convert_rejects_oversize_upload_before_full_buffer(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))
    monkeypatch.setattr(shape_converter_convert_module, "_MAX_UPLOAD_COMPRESSED_BYTES", 8)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "archive_quota_exceeded"


def test_convert_rejects_oversize_geojson_output(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))
    monkeypatch.setattr(shape_converter_serialization_module, "_MAX_GEOJSON_OUTPUT_BYTES", 10)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "archive_quota_exceeded"


def test_convert_rejects_oversize_geoparquet_output(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))
    monkeypatch.setattr(shape_converter_serialization_module, "_MAX_GEOPARQUET_OUTPUT_BYTES", 10)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={"output_format": "geoparquet", "target_crs": "wgs84"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "archive_quota_exceeded"


def test_convert_parser_worker_uses_minimal_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # noqa: ANN001
    observed_env: dict[str, str] = {}

    class _Process:
        pid = 1234
        returncode = 0

        def communicate(self, timeout=None):  # noqa: ANN001
            return "", ""

    def _fake_popen(*args, **kwargs):  # noqa: ANN002, ANN003
        observed_env.update(dict(kwargs["env"]))
        return _Process()

    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("PYTHONPATH", "/workdir/wepppy")
    monkeypatch.setenv("SHAPE_CONVERTER_TEST_SECRET", "do-not-leak")
    monkeypatch.setattr(shape_converter_convert_module.subprocess, "Popen", _fake_popen)

    worker_stdout, worker_stderr = shape_converter_convert_module._run_parser_worker(
        shp_path=tmp_path / "roads.shp",
        output_path=tmp_path / "payload.pickle",
        scratch=SimpleNamespace(request_dir=tmp_path),
    )

    assert worker_stdout == ""
    assert worker_stderr == ""
    assert observed_env["PATH"] == "/usr/bin"
    assert observed_env["PYTHONPATH"] == "/workdir/wepppy"
    assert observed_env["LC_ALL"] == "C"
    assert observed_env["LANG"] == "C"
    assert "SHAPE_CONVERTER_TEST_SECRET" not in observed_env


def test_convert_rejects_oversize_parser_worker_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # noqa: ANN001
    payload_path = tmp_path / "parser_worker_payload.pickle"
    payload_path.write_bytes(b"0123456789")
    monkeypatch.setattr(shape_converter_convert_module, "_MAX_PARSER_PAYLOAD_BYTES", 4)

    with pytest.raises(shape_converter_convert_module.ShapeConverterError) as exc_info:
        shape_converter_convert_module._read_parser_payload(
            payload_path=payload_path,
            worker_stdout="",
            worker_stderr="",
        )

    error = exc_info.value
    assert error.code == "invalid_shapefile"
    assert "exceeds limit" in error.details


def test_convert_metadata_path_honors_forwarded_prefix() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))
    headers = {"X-Forwarded-Prefix": "/utils/shape-converter"}

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
            headers=headers,
        )

        metadata_path = response.headers["x-shape-converter-metadata-path"]
        assert metadata_path.startswith("/utils/shape-converter/v1/convert/metadata/")

        local_metadata_path = metadata_path.removeprefix("/utils/shape-converter")
        metadata_response = client.get(local_metadata_path, headers=headers)

    assert metadata_response.status_code == 200
    assert metadata_response.json()["target_crs"] == "wgs84"


def test_convert_metadata_cache_is_bounded_by_max_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))
    monkeypatch.setattr(shape_converter_app_module, "_CONVERT_METADATA_MAX_ENTRIES", 1)

    with TestClient(create_app()) as client:
        first = client.post(
            "/v1/convert",
            files={"archive": ("roads1.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )
        second = client.post(
            "/v1/convert",
            files={"archive": ("roads2.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

        first_metadata = client.get(first.headers["x-shape-converter-metadata-path"])
        second_metadata = client.get(second.headers["x-shape-converter-metadata-path"])

    assert first_metadata.status_code == 404
    assert first_metadata.json()["error"]["code"] == "metadata_not_found"
    assert second_metadata.status_code == 200


def test_convert_rejects_unknown_response_mode() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "streaming",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_request"


def test_convert_metadata_endpoint_returns_404_for_unknown_request_id() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/v1/convert/metadata/not-real")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "metadata_not_found"
    assert payload["error"]["details"]


def test_convert_returns_timeout_when_body_read_stalls(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="timeout-read"))

    async def _raise_body_timeout(_request):  # noqa: ANN001
        raise TimeoutError()

    monkeypatch.setattr(shape_converter_app_module, "_read_form_with_timeout", _raise_body_timeout)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("timeout-read.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 408
    payload = response.json()
    assert payload["error"]["code"] == "request_timeout"
    assert "body" in payload["error"]["message"].lower()


def test_convert_parser_loop_timeout_cancels_processing_and_cleans_scratch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # noqa: ANN001
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="timeout-parser"))
    observed_cancel = {"value": False}

    async def _stalled_convert(**kwargs):  # noqa: ANN003
        scratch = kwargs["scratch"]
        scratch.extraction_root.mkdir(parents=True, exist_ok=True)
        (scratch.extraction_root / "parser-loop.tmp").write_text("partial", encoding="utf-8")
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


def test_parser_worker_applies_parser_egress_guards_and_driver_allowlist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # noqa: ANN001
    captured_options: dict[str, str] = {}
    captured_open: dict[str, object] = {}

    class _FakeEnv:
        def __init__(self, **kwargs):  # noqa: ANN003
            captured_options.update({str(key): str(value) for key, value in kwargs.items()})

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

    class _FakeDataset:
        bounds = (10.0, 20.0, 10.0, 20.0)
        crs_wkt = None
        crs = {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def __iter__(self):
            return iter(())

    monkeypatch.setattr(shape_converter_parser_worker_module.fiona, "Env", _FakeEnv)

    def _fake_open(path: str, *, enabled_drivers: list[str] | None = None):  # noqa: ANN001
        captured_open["path"] = path
        captured_open["enabled_drivers"] = enabled_drivers
        return _FakeDataset()

    monkeypatch.setattr(shape_converter_parser_worker_module.fiona, "open", _fake_open)
    monkeypatch.setattr(
        shape_converter_parser_worker_module,
        "parse_source_crs",
        lambda **_kwargs: None,
    )

    payload = shape_converter_parser_worker_module._load_shapefile_payload(
        shp_path=tmp_path / "roads.shp",
        max_features=10,
        max_vertices_per_feature=250000,
    )

    assert payload["source_bounds"] == (10.0, 20.0, 10.0, 20.0)
    assert captured_open["enabled_drivers"] == ["ESRI Shapefile"]
    assert captured_options["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] == ""
    assert captured_options["GDAL_DISABLE_READDIR_ON_OPEN"] == "EMPTY_DIR"
    assert captured_options["GDAL_HTTP_MAX_RETRY"] == "0"


def test_load_shapefile_invokes_worker_subprocess_with_new_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    captured_popen_kwargs: dict[str, object] = {}
    payload_path = tmp_path / "parser_worker_payload.pickle"
    expected_payload = {
        "properties": [{"NAME": "roads"}],
        "geometries": [{"type": "Point", "coordinates": [10.0, 20.0]}],
        "source_bounds": [10.0, 20.0, 10.0, 20.0],
        "source_crs_wkt": CRS.from_epsg(4326).to_wkt(),
    }

    class _FakeProcess:
        pid = 99123
        returncode = 0

        def communicate(self, timeout=None):  # noqa: ANN001
            payload_path.write_bytes(pickle.dumps(expected_payload, protocol=pickle.HIGHEST_PROTOCOL))
            return "", ""

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):  # noqa: ANN001
            return self.returncode

    def _fake_popen(*args, **kwargs):  # noqa: ANN002, ANN003
        captured_popen_kwargs.update(kwargs)
        return _FakeProcess()

    monkeypatch.setattr(shape_converter_convert_module.subprocess, "Popen", _fake_popen)
    scratch = SimpleNamespace(request_dir=tmp_path)

    loaded = shape_converter_convert_module._load_shapefile(
        shp_path=tmp_path / "roads.shp",
        scratch=scratch,
    )

    assert loaded.source_bounds == (10.0, 20.0, 10.0, 20.0)
    assert loaded.source_crs is not None
    assert loaded.source_crs.to_epsg() == 4326
    assert captured_popen_kwargs["start_new_session"] is True
    assert captured_popen_kwargs["cwd"] == tmp_path.as_posix()
    assert captured_popen_kwargs["text"] is True


def test_load_shapefile_timeout_kills_worker_process_group(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    signals_sent: list[int] = []

    class _TimeoutProcess:
        pid = 55223
        returncode = None

        def __init__(self):
            self._communicate_calls = 0

        def communicate(self, timeout=None):  # noqa: ANN001
            self._communicate_calls += 1
            if self._communicate_calls == 1:
                raise subprocess.TimeoutExpired(cmd=["parser"], timeout=timeout)
            return "", ""

        def poll(self):
            return None

        def wait(self, timeout=None):  # noqa: ANN001
            raise subprocess.TimeoutExpired(cmd=["parser"], timeout=timeout)

    monkeypatch.setattr(shape_converter_convert_module.subprocess, "Popen", lambda *a, **k: _TimeoutProcess())  # noqa: ANN002, ANN003
    monkeypatch.setattr(
        shape_converter_convert_module.os,
        "killpg",
        lambda _pid, sig: signals_sent.append(sig),
    )
    scratch = SimpleNamespace(request_dir=tmp_path)

    with pytest.raises(shape_converter_convert_module.ShapeConverterError) as exc_info:
        shape_converter_convert_module._load_shapefile(
            shp_path=tmp_path / "roads.shp",
            scratch=scratch,
        )

    exc = exc_info.value
    assert exc.code == "request_timeout"
    assert exc.status_code == 408
    assert signal.SIGTERM in signals_sent
    assert signal.SIGKILL in signals_sent
