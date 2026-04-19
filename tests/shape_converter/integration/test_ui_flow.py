from __future__ import annotations

import pytest
from pyproj import CRS

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter import create_app
from wepppy.microservices.shape_converter.abuse_controls import InflightAcquireDecision, SlidingWindowRateLimiter


pytestmark = [pytest.mark.integration, pytest.mark.microservice]


def test_ui_route_and_assets_are_reachable() -> None:
    with TestClient(create_app()) as client:
        root_response = client.get("/")
        css_response = client.get("/assets/styles.css")
        js_response = client.get("/assets/app.js")

    assert root_response.status_code == 200
    assert root_response.headers["content-type"].startswith("text/html")
    assert "Shapefile Converter" in root_response.text
    assert "id=\"upload-form\"" in root_response.text
    assert "id=\"warnings-panel\"" in root_response.text
    assert css_response.status_code == 200
    assert "css" in css_response.headers["content-type"]
    assert js_response.status_code == 200
    assert "javascript" in js_response.headers["content-type"]


def test_ui_flow_inspect_then_convert_surfaces_required_warnings() -> None:
    projected_wkt = CRS.from_epsg(32611).to_wkt(version="WKT1_GDAL")
    entries = build_minimal_point_dataset(prefix="ui-flow", prj_text=projected_wkt)
    entries["ui-flow.shp.xml"] = b"<metadata><author>alice</author></metadata>"
    inspect_archive = build_zip_bytes(entries)
    convert_archive = build_zip_bytes(entries)

    with TestClient(create_app()) as client:
        inspect_response = client.post(
            "/v1/inspect",
            files={"archive": ("ui-flow.zip", inspect_archive, "application/zip")},
        )

        convert_response = client.post(
            "/v1/convert",
            files={"archive": ("ui-flow.zip", convert_archive, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "same_as_shapefile",
                "response_mode": "download",
            },
        )
        metadata_response = client.get(convert_response.headers["x-shape-converter-metadata-path"])

    assert inspect_response.status_code == 200
    inspect_payload = inspect_response.json()
    assert any(".shp.xml" in warning for warning in inspect_payload["warnings"])
    assert inspect_payload["attribute_schema"]
    assert "nullability_note" in inspect_payload["attribute_schema"][0]

    assert convert_response.status_code == 200
    assert convert_response.headers["content-type"].startswith("application/json")

    assert metadata_response.status_code == 200
    convert_metadata = metadata_response.json()
    warnings = convert_metadata["warnings"]
    assert any(".shp.xml" in warning for warning in warnings)
    assert any("RFC 7946" in warning for warning in warnings)


def test_ui_flow_exposes_rate_limit_retry_after_for_client_rendering() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="ui-rate"))

    with TestClient(create_app()) as client:
        client.app.state.abuse_controls.rate_limiter = SlidingWindowRateLimiter(
            limit_count=1,
            window_seconds=300,
        )

        first = client.post(
            "/v1/inspect",
            files={"archive": ("ui-rate.zip", archive_bytes, "application/zip")},
        )
        second = client.post(
            "/v1/inspect",
            files={"archive": ("ui-rate.zip", archive_bytes, "application/zip")},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers.get("retry-after")
    payload = second.json()
    assert payload["error"]["code"] == "rate_limited"


def test_ui_flow_exposes_service_saturated_response_for_client_rendering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="ui-saturated"))

    with TestClient(create_app()) as client:
        async def _reject_global(_key: str) -> InflightAcquireDecision:
            return InflightAcquireDecision(allowed=False, reason="global")

        monkeypatch.setattr(client.app.state.abuse_controls.inflight_limiter, "try_acquire", _reject_global)

        response = client.post(
            "/v1/convert",
            files={"archive": ("ui-saturated.zip", archive_bytes, "application/zip")},
            data={
                "output_format": "geojson",
                "target_crs": "wgs84",
                "response_mode": "download",
            },
        )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "service_saturated"
