from __future__ import annotations

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter import create_app

pytestmark = [pytest.mark.integration, pytest.mark.microservice]


def test_ready_endpoint_reports_not_ready_when_sandbox_mode_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHAPE_CONVERTER_SANDBOX_MODE", "container")
    monkeypatch.setenv("SHAPE_CONVERTER_REQUIRED_SANDBOX_MODE", "gvisor")

    with TestClient(create_app()) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["reason"].startswith("sandbox_mode_mismatch")
    assert payload["sandbox_mode"] == "container"
    assert payload["required_sandbox_mode"] == "gvisor"


def test_hardening_readiness_enforcement_does_not_regress_inspect_convert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHAPE_CONVERTER_SANDBOX_MODE", "gvisor")
    monkeypatch.setenv("SHAPE_CONVERTER_REQUIRED_SANDBOX_MODE", "gvisor")
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="hardening-regression"))

    with TestClient(create_app()) as client:
        ready_response = client.get("/health/ready")
        inspect_response = client.post(
            "/v1/inspect",
            files={"archive": ("hardening-regression.zip", archive_bytes, "application/zip")},
        )
        convert_response = client.post(
            "/v1/convert",
            files={"archive": ("hardening-regression.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert ready_response.status_code == 200
    ready_payload = ready_response.json()
    assert ready_payload["sandbox_mode"] == "gvisor"
    assert ready_payload["required_sandbox_mode"] == "gvisor"

    assert inspect_response.status_code == 200
    inspect_payload = inspect_response.json()
    assert inspect_payload["feature_count"] == 1

    assert convert_response.status_code == 200
    convert_payload = convert_response.json()
    assert convert_payload["type"] == "FeatureCollection"
