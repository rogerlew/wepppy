from __future__ import annotations

import importlib
from pathlib import Path

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from wepppy.microservices.shape_converter import app as shape_converter_app
from wepppy.microservices.shape_converter import create_app

pytestmark = [pytest.mark.unit, pytest.mark.microservice]
shape_converter_app_module = importlib.import_module("wepppy.microservices.shape_converter.app")


def test_live_health_returns_ok_without_auth_headers() -> None:
    with TestClient(shape_converter_app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "scope": "shape-converter",
        "check": "live",
    }


def test_ready_health_returns_ok_when_scratch_is_writable() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["scope"] == "shape-converter"
    assert payload["check"] == "ready"
    assert payload["sandbox_mode"]
    assert payload["required_sandbox_mode"]
    assert payload["sandbox_mode"] == payload["required_sandbox_mode"]


def test_ready_health_returns_503_when_scratch_unwritable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_probe(_path: Path) -> tuple[bool, str | None]:
        return False, "scratch_root_not_writable: permission denied"

    monkeypatch.setattr(shape_converter_app_module, "_is_scratch_root_writable", _fake_probe)

    with TestClient(create_app()) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["scope"] == "shape-converter"
    assert payload["check"] == "ready"
    assert payload["reason"].startswith("scratch_root_not_writable")


def test_ready_health_returns_503_when_required_sandbox_mode_mismatches_active(
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


def test_ready_health_returns_503_when_required_sandbox_mode_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHAPE_CONVERTER_SANDBOX_MODE", "container")
    monkeypatch.setenv("SHAPE_CONVERTER_REQUIRED_SANDBOX_MODE", "")

    with TestClient(create_app()) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["reason"] == "sandbox_required_mode_unset"


def test_ready_health_returns_503_when_toolchain_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shape_converter_app_module, "_is_toolchain_available", lambda: (False, "ogr2ogr_not_found"))

    with TestClient(create_app()) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["reason"] == "ogr2ogr_not_found"
