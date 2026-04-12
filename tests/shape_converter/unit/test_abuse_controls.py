from __future__ import annotations

import asyncio
import ipaddress

import pytest

pytest.importorskip("starlette")

from wepppy.microservices.shape_converter.abuse_controls import (
    AbuseControlConfig,
    AbuseControlState,
    ClientIdentityResolver,
    InflightRequestLimiter,
    SlidingWindowRateLimiter,
)


pytestmark = [pytest.mark.unit, pytest.mark.microservice]


def _run(coro):  # noqa: ANN001
    return asyncio.run(coro)


def test_client_identity_ignores_forwarded_header_when_source_is_untrusted() -> None:
    resolver = ClientIdentityResolver(
        trusted_proxy_cidrs=(),
        trusted_proxy_hops=1,
    )

    identity = resolver.resolve(
        peer_host="198.51.100.8",
        x_forwarded_for="203.0.113.9",
    )

    assert identity.source == "socket"
    assert identity.client_ip == "198.51.100.8"
    assert identity.limiter_key == "198.51.100.8"


def test_client_identity_uses_forwarded_chain_for_trusted_proxy() -> None:
    resolver = ClientIdentityResolver(
        trusted_proxy_cidrs=(
            # Trusted internal proxy range.
            ipaddress.ip_network("10.0.0.0/8"),
        ),
        trusted_proxy_hops=1,
    )

    identity = resolver.resolve(
        peer_host="10.9.0.5",
        x_forwarded_for="203.0.113.44",
    )

    assert identity.source == "forwarded"
    assert identity.client_ip == "203.0.113.44"
    assert identity.limiter_key == "203.0.113.44"


def test_client_identity_trusted_hops_selects_nth_from_right() -> None:
    resolver = ClientIdentityResolver(
        trusted_proxy_cidrs=(
            ipaddress.ip_network("10.0.0.0/8"),
        ),
        trusted_proxy_hops=2,
    )

    identity = resolver.resolve(
        peer_host="10.2.0.8",
        x_forwarded_for="203.0.113.1, 198.51.100.20",
    )

    assert identity.source == "forwarded"
    assert identity.client_ip == "203.0.113.1"
    assert identity.limiter_key == "203.0.113.1"


def test_client_identity_ipv6_addresses_are_aggregated_to_64() -> None:
    resolver = ClientIdentityResolver(
        trusted_proxy_cidrs=(
            ipaddress.ip_network("10.0.0.0/8"),
        ),
        trusted_proxy_hops=1,
    )

    identity = resolver.resolve(
        peer_host="10.1.2.3",
        x_forwarded_for="2001:db8:abcd:42:1::99",
    )

    assert identity.source == "forwarded"
    assert identity.client_ip == "2001:db8:abcd:42:1::99"
    assert identity.limiter_key == "2001:db8:abcd:42::/64"


def test_rate_limiter_returns_denied_after_limit_is_reached() -> None:
    limiter = SlidingWindowRateLimiter(limit_count=2, window_seconds=60)

    first = _run(limiter.check("203.0.113.9"))
    second = _run(limiter.check("203.0.113.9"))
    third = _run(limiter.check("203.0.113.9"))

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after_seconds >= 1


def test_inflight_limiter_enforces_per_ip_limit() -> None:
    limiter = InflightRequestLimiter(per_ip_limit=1, global_limit=5)

    first = _run(limiter.try_acquire("198.51.100.4"))
    second = _run(limiter.try_acquire("198.51.100.4"))
    _run(limiter.release("198.51.100.4"))
    third = _run(limiter.try_acquire("198.51.100.4"))

    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "per_ip"
    assert third.allowed is True


def test_inflight_limiter_enforces_global_limit() -> None:
    limiter = InflightRequestLimiter(per_ip_limit=5, global_limit=1)

    first = _run(limiter.try_acquire("198.51.100.1"))
    second = _run(limiter.try_acquire("198.51.100.2"))

    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "global"


def test_abuse_control_state_protects_only_public_post_endpoints() -> None:
    config = AbuseControlConfig(
        rate_limit_count=10,
        rate_limit_window_seconds=60,
        max_inflight_global=5,
        max_inflight_per_ip=2,
        trusted_proxy_hops=1,
        trusted_proxy_cidrs=(),
    )
    state = AbuseControlState(config)

    class _DummyUrl:
        def __init__(self, path: str) -> None:
            self.path = path

    class _DummyRequest:
        def __init__(self, *, method: str, path: str) -> None:
            self.method = method
            self.url = _DummyUrl(path)
            self.scope = {"path": path}

    assert state.protects(_DummyRequest(method="POST", path="/v1/inspect")) is True
    assert state.protects(_DummyRequest(method="POST", path="/v1/convert")) is True
    assert state.protects(_DummyRequest(method="GET", path="/v1/inspect")) is False
    assert state.protects(_DummyRequest(method="POST", path="/v1/convert/metadata/abc")) is False
