from __future__ import annotations

import pytest

pytest.importorskip("starlette")

from starlette.applications import Starlette
from starlette.testclient import TestClient

from wepppy.microservices.shape_converter import app as module_app
from wepppy.microservices.shape_converter import create_app

pytestmark = [pytest.mark.unit, pytest.mark.microservice]


def test_create_app_returns_starlette_instance() -> None:
    app = create_app()
    assert isinstance(app, Starlette)


def test_shape_converter_routes_registered() -> None:
    app = create_app()
    route_paths = {route.path for route in app.routes if hasattr(route, "path")}

    assert "/" in route_paths
    assert "/health/live" in route_paths
    assert "/health/ready" in route_paths
    assert "/v1/inspect" in route_paths
    assert "/v1/convert" in route_paths
    assert "/v1/convert/metadata/{request_id}" in route_paths


def test_module_level_app_bootstraps() -> None:
    with TestClient(module_app) as client:
        response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "shape-converter"
