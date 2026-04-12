from __future__ import annotations

import importlib
import re

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter import create_app


pytestmark = [pytest.mark.unit, pytest.mark.microservice]
_REQUEST_ID_RE = re.compile(r"^[a-f0-9]{32}$")
shape_converter_app_module = importlib.import_module("wepppy.microservices.shape_converter.app")


def test_inspect_success_returns_required_metadata_fields() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="roads"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert _REQUEST_ID_RE.match(payload["request_id"])
    assert payload["projection_status"] == "known"
    assert payload["feature_count"] == 1
    assert payload["geometry_types"] == ["Point"]
    assert payload["bbox"] == [10.0, 20.0, 10.0, 20.0]
    assert isinstance(payload["attribute_schema"], list)
    assert isinstance(payload["warnings"], list)
    assert payload["detected_crs"]["authority"] == "EPSG:4326"


def test_inspect_accepts_shp_xml_sidecar_and_warns_user() -> None:
    entries = build_minimal_point_dataset(prefix="roads")
    entries["roads.shp.xml"] = (
        b"<metadata><creator>alice</creator><path>/Users/alice/private</path></metadata>"
    )
    archive_bytes = build_zip_bytes(entries)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("roads.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert any(".shp.xml" in warning for warning in payload["warnings"])
    assert any("generally not advisable" in warning.lower() for warning in payload["warnings"])


def test_inspect_requires_archive_field() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/inspect", data={"wrong": "field"})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_archive"
    assert payload["error"]["details"]


def test_inspect_reports_missing_sidecar_error() -> None:
    archive_bytes = build_zip_bytes(
        {
            "sample.shp": b"x",
            "sample.shx": b"y",
        }
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("missing.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "missing_required_sidecar"
    assert payload["error"]["details"]


def test_inspect_rejects_multiple_shapefile_prefixes() -> None:
    entries = build_minimal_point_dataset(prefix="one")
    entries.update(build_minimal_point_dataset(prefix="two", include_prj=False))
    archive_bytes = build_zip_bytes(entries)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("multi.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_shapefile"
    assert payload["error"]["details"]


def test_inspect_rejects_path_traversal_archive() -> None:
    archive_bytes = build_zip_bytes(
        {
            "../escape.shp": b"x",
            "safe.shx": b"y",
            "safe.dbf": b"z",
        }
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("traversal.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "archive_path_traversal"
    assert payload["error"]["details"]


def test_inspect_rejects_oversize_projection_file() -> None:
    huge_prj = ("GEOGCS[\"" + ("A" * 40000) + "\"]").encode("utf-8")
    archive_bytes = build_zip_bytes(
        {
            **build_minimal_point_dataset(prefix="oversize"),
            "oversize.prj": huge_prj,
        }
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("oversize-prj.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_shapefile"
    assert "size limit" in payload["error"]["message"].lower()


def test_inspect_rejects_oversize_upload_before_full_buffer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="oversize-upload"))
    monkeypatch.setattr("wepppy.microservices.shape_converter.inspect._MAX_UPLOAD_COMPRESSED_BYTES", 8)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("oversize-upload.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["code"] == "archive_quota_exceeded"


def test_inspect_returns_timeout_when_body_read_stalls(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="timeout-read"))

    async def _raise_body_timeout(_request):  # noqa: ANN001
        raise TimeoutError()

    monkeypatch.setattr(shape_converter_app_module, "_read_form_with_timeout", _raise_body_timeout)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("timeout-read.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 408
    payload = response.json()
    assert payload["error"]["code"] == "request_timeout"
    assert "body" in payload["error"]["message"].lower()
