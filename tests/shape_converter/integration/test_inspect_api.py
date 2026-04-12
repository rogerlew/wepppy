from __future__ import annotations

import json

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import (
    SENSITIVE_METADATA_MARKERS,
    build_minimal_point_dataset,
    build_sensitive_metadata_payload,
    build_xml_entity_expansion_payload,
    build_zip_bytes,
)
from wepppy.microservices.shape_converter import app
from wepppy.microservices.shape_converter import create_app


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


def test_inspect_endpoint_does_not_expose_shp_xml_sensitive_content() -> None:
    entries = build_minimal_point_dataset(prefix="integration")
    entries["integration.shp.xml"] = build_sensitive_metadata_payload(include_xml_shell=True)
    archive_bytes = build_zip_bytes(entries)

    with TestClient(app) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("integration.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 200
    payload_text = json.dumps(response.json(), sort_keys=True)
    for marker in SENSITIVE_METADATA_MARKERS:
        assert marker not in payload_text


def test_inspect_endpoint_does_not_expose_qmd_sensitive_content() -> None:
    entries = build_minimal_point_dataset(prefix="integration")
    entries["integration.qmd"] = build_sensitive_metadata_payload(include_xml_shell=False)
    archive_bytes = build_zip_bytes(entries)

    with TestClient(app) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("integration.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 200
    payload = response.json()
    payload_text = json.dumps(payload, sort_keys=True)
    assert not any(".qmd" in warning.lower() for warning in payload["warnings"])
    for marker in SENSITIVE_METADATA_MARKERS:
        assert marker not in payload_text


@pytest.mark.parametrize("suffix", [".xml", ".gml"])
def test_inspect_endpoint_rejects_entity_expansion_sidecars(suffix: str) -> None:
    entries = build_minimal_point_dataset(prefix="integration")
    entries[f"integration{suffix}"] = build_xml_entity_expansion_payload(root_tag="dataset")
    archive_bytes = build_zip_bytes(entries)

    with TestClient(app) as client:
        response = client.post(
            "/v1/inspect",
            files={"archive": ("integration.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_archive"
    assert "unsupported file extension" in payload["error"]["message"].lower()


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


def test_inspect_cleanup_success_leaves_no_request_artifacts(tmp_path) -> None:  # noqa: ANN001
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="cleanup-success"))

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/inspect",
            files={"archive": ("cleanup-success.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 200
    assert list(tmp_path.iterdir()) == []


def test_inspect_cleanup_failure_leaves_no_request_artifacts(tmp_path) -> None:  # noqa: ANN001
    archive_bytes = build_zip_bytes({"broken.shp": b"x", "broken.shx": b"y"})

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/inspect",
            files={"archive": ("cleanup-failure.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_required_sidecar"
    assert list(tmp_path.iterdir()) == []
