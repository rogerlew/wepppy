from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

pytest.importorskip("starlette")

from starlette.routing import Route

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_DOCS_DIR = REPO_ROOT / "wepppy" / "query_engine" / "docs"
MCP_OPENAPI_PATH = MCP_DOCS_DIR / "mcp_openapi.yaml"
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _normalize_starlette_path(path: str) -> str:
    """Convert Starlette path converters to OpenAPI-compatible template paths."""
    return re.sub(r"{([^}:]+):[^}]+}", r"{\1}", path)


def _openapi_route_signatures(openapi_doc: dict) -> set[tuple[str, str]]:
    signatures: set[tuple[str, str]] = set()
    for path, operations in openapi_doc.get("paths", {}).items():
        if not isinstance(path, str) or not isinstance(operations, dict):
            continue
        for method in operations:
            method_upper = str(method).upper()
            if method_upper in HTTP_METHODS:
                signatures.add((path, method_upper))
    return signatures


def _mcp_app_route_signatures(app_routes: list[Route]) -> set[tuple[str, str]]:
    signatures: set[tuple[str, str]] = set()
    for route in app_routes:
        if not isinstance(route, Route):
            continue
        normalized_path = _normalize_starlette_path(route.path)
        for method in route.methods or set():
            method_upper = method.upper()
            if method_upper in HTTP_METHODS:
                signatures.add((normalized_path, method_upper))
    return signatures


def test_mcp_openapi_single_source_file() -> None:
    candidates = sorted(path.name for path in MCP_DOCS_DIR.glob("mcp_openapi*.yaml"))
    assert candidates == ["mcp_openapi.yaml"], (
        "MCP OpenAPI contract must be a single canonical file. "
        f"Found: {candidates}"
    )


def test_mcp_openapi_matches_mounted_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEPP_MCP_JWT_SECRET", "unit-test-secret")
    monkeypatch.setenv("WEPP_MCP_JWT_ALGORITHMS", "HS256")

    from wepppy.query_engine.app.mcp import auth as mcp_auth
    from wepppy.query_engine.app.mcp import router as mcp_router

    mcp_auth.get_auth_config.cache_clear()
    try:
        openapi_doc = yaml.safe_load(MCP_OPENAPI_PATH.read_text(encoding="utf-8"))
        assert isinstance(openapi_doc, dict), "MCP OpenAPI file must parse to a mapping."

        openapi_signatures = _openapi_route_signatures(openapi_doc)
        app = mcp_router.create_mcp_app()
        route_signatures = _mcp_app_route_signatures(app.routes)

        assert openapi_signatures == route_signatures, (
            "MCP OpenAPI path/method signatures are out of sync with mounted routes. "
            f"spec_only={sorted(openapi_signatures - route_signatures)} "
            f"route_only={sorted(route_signatures - openapi_signatures)}"
        )
    finally:
        mcp_auth.get_auth_config.cache_clear()
