from __future__ import annotations

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from wepppy.microservices.shape_converter import create_app


pytestmark = [pytest.mark.unit, pytest.mark.microservice]


def test_ui_route_serves_shape_converter_shell() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert "Shape Converter" in body
    assert "inspect-form" in body
    assert "convert-form" in body
    assert "response_mode=download" in body
    assert "json_body" in body


@pytest.mark.parametrize(
    ("path", "expected_content_type", "expected_text"),
    [
        ("/assets/styles.css", "css", "--accent"),
        ("/assets/app.js", "javascript", "response_mode"),
    ],
)
def test_ui_assets_are_served(
    path: str,
    expected_content_type: str,
    expected_text: str,
) -> None:
    with TestClient(create_app()) as client:
        response = client.get(path)

    assert response.status_code == 200
    assert expected_content_type in response.headers["content-type"]
    assert expected_text in response.text


def test_ui_script_contains_warning_and_abuse_control_guidance() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    script = response.text
    assert ".shp.xml" in script
    assert "RFC 7946" in script
    assert "rate_limited" in script
    assert "service_saturated" in script
    assert "Retry-After" in script
    assert "buildUserFacingStatus" in script
    assert "zip again" in script
    assert "missing required shapefile files" in script
    assert "response_mode_not_supported" in script
    assert "Inspect could not run." in script
    assert "Convert could not run." in script


def test_ui_assets_still_serve_when_forwarded_prefix_header_is_present() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/assets/styles.css",
            headers={"X-Forwarded-Prefix": "/utils/shape-converter"},
        )

    assert response.status_code == 200
    assert "css" in response.headers["content-type"]
