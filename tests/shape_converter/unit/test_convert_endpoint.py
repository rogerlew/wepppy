from __future__ import annotations

import importlib

import pytest
from pyproj import CRS

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter import create_app


pytestmark = [pytest.mark.unit, pytest.mark.microservice]
shape_converter_app_module = importlib.import_module("wepppy.microservices.shape_converter.app")
shape_converter_convert_module = importlib.import_module("wepppy.microservices.shape_converter.convert")


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


def test_convert_rejects_response_mode_json_body_until_wp06b() -> None:
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

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "response_mode_not_supported"
    assert "WP-06B" in payload["error"]["details"]


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


def test_convert_returns_reprojection_failed_when_transformer_init_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))

    def _raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "wepppy.microservices.shape_converter.crs.Transformer.from_crs",
        _raise_runtime_error,
    )

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
    monkeypatch.setattr("wepppy.microservices.shape_converter.convert._MAX_UPLOAD_COMPRESSED_BYTES", 8)

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
    monkeypatch.setattr("wepppy.microservices.shape_converter.serialization._MAX_GEOJSON_OUTPUT_BYTES", 10)

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
    monkeypatch.setattr("wepppy.microservices.shape_converter.serialization._MAX_GEOPARQUET_OUTPUT_BYTES", 10)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/convert",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
            data={"output_format": "geoparquet", "target_crs": "wgs84"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "archive_quota_exceeded"


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


def test_load_shapefile_applies_parser_egress_guards(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # noqa: ANN001
    captured_options: dict[str, str] = {}

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

    monkeypatch.setattr(shape_converter_convert_module.fiona, "Env", _FakeEnv)
    monkeypatch.setattr(
        shape_converter_convert_module.fiona,
        "open",
        lambda _path: _FakeDataset(),  # noqa: ARG005
    )
    monkeypatch.setattr(
        shape_converter_convert_module,
        "parse_source_crs",
        lambda **_kwargs: None,
    )

    loaded = shape_converter_convert_module._load_shapefile(tmp_path / "roads.shp")

    assert loaded.source_bounds == (10.0, 20.0, 10.0, 20.0)
    assert captured_options["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] == ""
    assert captured_options["GDAL_DISABLE_READDIR_ON_OPEN"] == "EMPTY_DIR"
    assert captured_options["GDAL_HTTP_MAX_RETRY"] == "0"
