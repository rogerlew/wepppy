from __future__ import annotations

import ipaddress

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter import create_app
from wepppy.microservices.shape_converter.abuse_controls import (
    ClientIdentityResolver,
    InflightAcquireDecision,
    SlidingWindowRateLimiter,
)


pytestmark = [pytest.mark.integration, pytest.mark.microservice]


def test_inspect_rate_limit_returns_429_with_retry_after_header() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="inspect-rate"))

    with TestClient(create_app()) as client:
        client.app.state.abuse_controls.rate_limiter = SlidingWindowRateLimiter(
            limit_count=1,
            window_seconds=300,
        )

        first = client.post(
            "/v1/inspect",
            files={"archive": ("inspect-rate.zip", archive_bytes, "application/zip")},
        )
        second = client.post(
            "/v1/inspect",
            files={"archive": ("inspect-rate.zip", archive_bytes, "application/zip")},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers.get("retry-after")
    payload = second.json()
    assert payload["error"]["code"] == "rate_limited"
    assert payload["error"]["details"]


def test_convert_per_ip_inflight_saturation_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="convert-per-ip"))

    with TestClient(create_app()) as client:
        async def _reject_per_ip(_key: str) -> InflightAcquireDecision:
            return InflightAcquireDecision(allowed=False, reason="per_ip")

        monkeypatch.setattr(client.app.state.abuse_controls.inflight_limiter, "try_acquire", _reject_per_ip)

        response = client.post(
            "/v1/convert",
            files={"archive": ("convert-per-ip.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 429
    payload = response.json()
    assert payload["error"]["code"] == "rate_limited"
    assert "in-flight" in payload["error"]["message"].lower()


def test_convert_global_inflight_saturation_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="convert-global"))

    with TestClient(create_app()) as client:
        async def _reject_global(_key: str) -> InflightAcquireDecision:
            return InflightAcquireDecision(allowed=False, reason="global")

        monkeypatch.setattr(client.app.state.abuse_controls.inflight_limiter, "try_acquire", _reject_global)

        response = client.post(
            "/v1/convert",
            files={"archive": ("convert-global.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "service_saturated"
    assert payload["error"]["details"]


def test_spoofed_forwarded_header_does_not_bypass_untrusted_identity_policy() -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="spoof"))

    with TestClient(create_app()) as client:
        client.app.state.abuse_controls.identity_resolver = ClientIdentityResolver(
            trusted_proxy_cidrs=(ipaddress.ip_network("10.0.0.0/8"),),
            trusted_proxy_hops=1,
        )
        client.app.state.abuse_controls.rate_limiter = SlidingWindowRateLimiter(
            limit_count=1,
            window_seconds=300,
        )

        first = client.post(
            "/v1/inspect",
            files={"archive": ("spoof.zip", archive_bytes, "application/zip")},
            headers={"X-Forwarded-For": "1.2.3.4"},
        )
        second = client.post(
            "/v1/inspect",
            files={"archive": ("spoof.zip", archive_bytes, "application/zip")},
            headers={"X-Forwarded-For": "5.6.7.8"},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
