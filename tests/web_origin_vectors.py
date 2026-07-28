from __future__ import annotations

from typing import TypedDict


class SameOriginVector(TypedDict, total=False):
    name: str
    base_url: str
    origin: str
    referer: str
    fetch_site: str
    forwarded_proto: str
    forwarded_host: str
    external_host: str
    external_scheme: str
    expected: bool


SAME_ORIGIN_VECTORS: tuple[SameOriginVector, ...] = (
    {
        "name": "same-origin metadata without origin",
        "base_url": "http://guard.test",
        "fetch_site": "same-origin",
        "expected": True,
    },
    {
        "name": "exact https origin",
        "base_url": "https://guard.test",
        "origin": "https://guard.test",
        "expected": True,
    },
    {
        "name": "exact referer fallback",
        "base_url": "https://guard.test",
        "referer": "https://guard.test/page",
        "expected": True,
    },
    {
        "name": "upstream tls bridge",
        "base_url": "http://guard.test",
        "origin": "https://guard.test",
        "fetch_site": "same-origin",
        "expected": True,
    },
    {
        "name": "cross-site metadata",
        "base_url": "https://guard.test",
        "origin": "https://guard.test",
        "fetch_site": "cross-site",
        "expected": False,
    },
    {
        "name": "opaque origin",
        "base_url": "https://guard.test",
        "origin": "null",
        "expected": False,
    },
    {
        "name": "scheme mismatch without bridge metadata",
        "base_url": "http://guard.test",
        "origin": "https://guard.test",
        "expected": False,
    },
    {
        "name": "explicit port conflict",
        "base_url": "https://guard.test",
        "origin": "https://guard.test:444",
        "fetch_site": "same-origin",
        "expected": False,
    },
    {
        "name": "subdomain conflict",
        "base_url": "https://guard.test",
        "origin": "https://sub.guard.test",
        "fetch_site": "same-origin",
        "expected": False,
    },
    {
        "name": "raw forwarded aliases are inert",
        "base_url": "http://guard.test",
        "origin": "https://forwarded.test",
        "forwarded_proto": "https",
        "forwarded_host": "forwarded.test",
        "expected": False,
    },
    {
        "name": "configured public origin",
        "base_url": "http://internal.test",
        "origin": "https://public.test",
        "external_host": "public.test",
        "external_scheme": "https",
        "expected": True,
    },
    {
        "name": "configured public host upstream tls bridge",
        "base_url": "http://internal.test",
        "origin": "https://public.test",
        "fetch_site": "same-origin",
        "external_host": "public.test",
        "external_scheme": "http",
        "expected": True,
    },
    {
        "name": "origin with user information",
        "base_url": "https://guard.test",
        "origin": "https://attacker@guard.test",
        "expected": False,
    },
    {
        "name": "origin with path",
        "base_url": "https://guard.test",
        "origin": "https://guard.test/unexpected",
        "expected": False,
    },
    {
        "name": "origin with query",
        "base_url": "https://guard.test",
        "origin": "https://guard.test?unexpected=1",
        "expected": False,
    },
    {
        "name": "origin with fragment",
        "base_url": "https://guard.test",
        "origin": "https://guard.test#unexpected",
        "expected": False,
    },
    {
        "name": "referer with user information",
        "base_url": "https://guard.test",
        "referer": "https://attacker@guard.test/page",
        "expected": False,
    },
    {
        "name": "missing every signal",
        "base_url": "https://guard.test",
        "expected": False,
    },
)


def vector_headers(vector: SameOriginVector) -> dict[str, str]:
    mapping = {
        "Origin": vector.get("origin", ""),
        "Referer": vector.get("referer", ""),
        "Sec-Fetch-Site": vector.get("fetch_site", ""),
        "X-Forwarded-Proto": vector.get("forwarded_proto", ""),
        "X-Forwarded-Host": vector.get("forwarded_host", ""),
    }
    return {key: value for key, value in mapping.items() if value}
