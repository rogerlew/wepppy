from __future__ import annotations

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter import app


pytestmark = [pytest.mark.integration, pytest.mark.microservice]


def test_inspect_endpoint_returns_success_for_valid_archive() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="integration"))

    with TestClient(app) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("integration.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["feature_count"] == 1
    assert payload["geometry_types"] == ["Point"]
    assert payload["projection_status"] == "known"


def test_inspect_endpoint_accepts_shp_xml_sidecar_and_returns_warning() -> None:
    entries = build_minimal_point_dataset(prefix="integration")
    entries["integration.shp.xml"] = b"<metadata><creator>alice</creator></metadata>"
    archive_bytes = build_zip_bytes(entries)

    with TestClient(app) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("integration.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert any(".shp.xml" in warning for warning in payload["warnings"])


def test_inspect_endpoint_returns_canonical_error_for_invalid_archive() -> None:
    archive_bytes = build_zip_bytes(
        {
            "../escape.shp": b"x",
            "safe.shx": b"y",
            "safe.dbf": b"z",
        }
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("invalid.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "archive_path_traversal"
    assert payload["error"]["details"]
