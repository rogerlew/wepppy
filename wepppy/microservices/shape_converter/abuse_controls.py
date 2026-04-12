"""Abuse-control primitives for public shape-converter endpoints."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import time
from collections import Counter, deque
from dataclasses import dataclass

from starlette.requests import Request

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

_DEFAULT_PROTECTED_PATHS = frozenset({"/v1/inspect", "/v1/convert"})
_DEFAULT_TRUSTED_PROXY_CIDRS = (
    "127.0.0.1/32,::1/128,"
    "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
)


def _safe_int_env(name: str, *, default: int, minimum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(minimum, parsed)


def _parse_ip_token(value: str) -> IPAddress | None:
    token = str(value or "").strip()
    if not token:
        return None

    if token.startswith("[") and "]" in token:
        token = token[1 : token.index("]")]

    if "%" in token:
        token = token.split("%", maxsplit=1)[0]

    try:
        return ipaddress.ip_address(token)
    except ValueError:
        pass

    if token.count(":") == 1:
        host, maybe_port = token.rsplit(":", maxsplit=1)
        if maybe_port.isdigit():
            try:
                return ipaddress.ip_address(host)
            except ValueError:
                return None
    return None


def _parse_networks(raw_value: str) -> tuple[IPNetwork, ...]:
    parsed_networks: list[IPNetwork] = []
    for token in raw_value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        try:
            parsed_network = ipaddress.ip_network(stripped, strict=False)
        except ValueError:
            continue
        parsed_networks.append(parsed_network)
    return tuple(parsed_networks)


def _parse_forwarded_chain(x_forwarded_for: str | None) -> tuple[IPAddress, ...]:
    raw_value = str(x_forwarded_for or "").strip()
    if not raw_value:
        return ()

    parsed_chain: list[IPAddress] = []
    for token in raw_value.split(","):
        parsed_ip = _parse_ip_token(token)
        if parsed_ip is None:
            # Fail closed: malformed forwarded chain is treated as untrusted input.
            return ()
        parsed_chain.append(parsed_ip)
    return tuple(parsed_chain)


def _aggregate_limiter_key(address: IPAddress) -> str:
    if isinstance(address, ipaddress.IPv6Address):
        aggregated = ipaddress.ip_network(f"{address.compressed}/64", strict=False)
        return f"{aggregated.network_address.compressed}/64"
    return address.compressed


@dataclass(frozen=True, slots=True)
class AbuseControlConfig:
    """Configuration for public-endpoint abuse controls."""

    rate_limit_count: int
    rate_limit_window_seconds: int
    max_inflight_global: int
    max_inflight_per_ip: int
    trusted_proxy_hops: int
    trusted_proxy_cidrs: tuple[IPNetwork, ...]
    protected_paths: frozenset[str] = _DEFAULT_PROTECTED_PATHS


@dataclass(frozen=True, slots=True)
class ClientIdentity:
    """Resolved client identity used for abuse controls."""

    client_ip: str
    limiter_key: str
    source: str


class ClientIdentityResolver:
    """Resolve client identity with trusted forwarding-header boundaries."""

    def __init__(
        self,
        *,
        trusted_proxy_cidrs: tuple[IPNetwork, ...],
        trusted_proxy_hops: int,
    ) -> None:
        self._trusted_proxy_cidrs = trusted_proxy_cidrs
        self._trusted_proxy_hops = max(1, trusted_proxy_hops)

    def resolve(self, *, peer_host: str | None, x_forwarded_for: str | None) -> ClientIdentity:
        peer_ip = _parse_ip_token(peer_host or "")
        if peer_ip is None:
            fallback = (peer_host or "unknown").strip() or "unknown"
            return ClientIdentity(client_ip=fallback, limiter_key=fallback, source="socket")

        if not self._is_trusted_proxy(peer_ip):
            return ClientIdentity(
                client_ip=peer_ip.compressed,
                limiter_key=_aggregate_limiter_key(peer_ip),
                source="socket",
            )

        forwarded_chain = _parse_forwarded_chain(x_forwarded_for)
        if len(forwarded_chain) < self._trusted_proxy_hops:
            return ClientIdentity(
                client_ip=peer_ip.compressed,
                limiter_key=_aggregate_limiter_key(peer_ip),
                source="socket",
            )

        trusted_client = forwarded_chain[-self._trusted_proxy_hops]
        return ClientIdentity(
            client_ip=trusted_client.compressed,
            limiter_key=_aggregate_limiter_key(trusted_client),
            source="forwarded",
        )

    def _is_trusted_proxy(self, address: IPAddress) -> bool:
        for network in self._trusted_proxy_cidrs:
            if address in network:
                return True
        return False


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    """Simple in-memory sliding-window rate limiter."""

    def __init__(self, *, limit_count: int, window_seconds: int) -> None:
        self._limit_count = max(1, limit_count)
        self._window_seconds = max(1, window_seconds)
        self._lock = asyncio.Lock()
        self._buckets: dict[str, deque[float]] = {}

    async def check(self, key: str) -> RateLimitDecision:
        now = time.monotonic()
        cutoff = now - float(self._window_seconds)

        async with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self._limit_count:
                oldest = bucket[0]
                retry_after = max(1, int((oldest + self._window_seconds) - now))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)

            bucket.append(now)
            return RateLimitDecision(allowed=True, retry_after_seconds=0)


@dataclass(frozen=True, slots=True)
class InflightAcquireDecision:
    allowed: bool
    reason: str | None = None


class InflightRequestLimiter:
    """In-memory admission control for per-client and global inflight limits."""

    def __init__(self, *, per_ip_limit: int, global_limit: int) -> None:
        self._per_ip_limit = max(1, per_ip_limit)
        self._global_limit = max(1, global_limit)
        self._lock = asyncio.Lock()
        self._global_inflight = 0
        self._per_ip_inflight: Counter[str] = Counter()

    async def try_acquire(self, key: str) -> InflightAcquireDecision:
        async with self._lock:
            if self._global_inflight >= self._global_limit:
                return InflightAcquireDecision(allowed=False, reason="global")

            if self._per_ip_inflight.get(key, 0) >= self._per_ip_limit:
                return InflightAcquireDecision(allowed=False, reason="per_ip")

            self._global_inflight += 1
            self._per_ip_inflight[key] += 1
            return InflightAcquireDecision(allowed=True, reason=None)

    async def release(self, key: str) -> None:
        async with self._lock:
            current_per_ip = self._per_ip_inflight.get(key, 0)
            if current_per_ip > 1:
                self._per_ip_inflight[key] = current_per_ip - 1
            elif current_per_ip == 1:
                del self._per_ip_inflight[key]

            if self._global_inflight > 0:
                self._global_inflight -= 1


class AbuseControlState:
    """Runtime state for trusted identity and abuse controls."""

    def __init__(self, config: AbuseControlConfig) -> None:
        self.config = config
        self.identity_resolver = ClientIdentityResolver(
            trusted_proxy_cidrs=config.trusted_proxy_cidrs,
            trusted_proxy_hops=config.trusted_proxy_hops,
        )
        self.rate_limiter = SlidingWindowRateLimiter(
            limit_count=config.rate_limit_count,
            window_seconds=config.rate_limit_window_seconds,
        )
        self.inflight_limiter = InflightRequestLimiter(
            per_ip_limit=config.max_inflight_per_ip,
            global_limit=config.max_inflight_global,
        )

    def protects(self, request: Request) -> bool:
        if request.method.upper() != "POST":
            return False
        scope_path = str(request.scope.get("path") or "")
        return scope_path in self.config.protected_paths

    def resolve_identity(self, request: Request) -> ClientIdentity:
        peer_host = request.client.host if request.client else None
        return self.identity_resolver.resolve(
            peer_host=peer_host,
            x_forwarded_for=request.headers.get("X-Forwarded-For"),
        )


def load_abuse_control_config() -> AbuseControlConfig:
    trusted_proxy_raw = os.getenv("SHAPE_CONVERTER_TRUSTED_PROXY_CIDRS")
    if trusted_proxy_raw is None:
        trusted_proxy_cidrs = _parse_networks(_DEFAULT_TRUSTED_PROXY_CIDRS)
    else:
        trusted_proxy_cidrs = _parse_networks(trusted_proxy_raw)

    return AbuseControlConfig(
        rate_limit_count=_safe_int_env(
            "SHAPE_CONVERTER_RATE_LIMIT_COUNT",
            default=120,
            minimum=1,
        ),
        rate_limit_window_seconds=_safe_int_env(
            "SHAPE_CONVERTER_RATE_LIMIT_WINDOW_SECONDS",
            default=60,
            minimum=1,
        ),
        max_inflight_global=_safe_int_env(
            "SHAPE_CONVERTER_MAX_INFLIGHT_GLOBAL",
            default=32,
            minimum=1,
        ),
        max_inflight_per_ip=_safe_int_env(
            "SHAPE_CONVERTER_MAX_INFLIGHT_PER_IP",
            default=8,
            minimum=1,
        ),
        trusted_proxy_hops=_safe_int_env(
            "SHAPE_CONVERTER_TRUSTED_PROXY_HOPS",
            default=1,
            minimum=1,
        ),
        trusted_proxy_cidrs=trusted_proxy_cidrs,
    )


__all__ = [
    "AbuseControlConfig",
    "AbuseControlState",
    "ClientIdentity",
    "ClientIdentityResolver",
    "InflightAcquireDecision",
    "InflightRequestLimiter",
    "RateLimitDecision",
    "SlidingWindowRateLimiter",
    "load_abuse_control_config",
]
