from __future__ import annotations

from importlib import reload

import pytest

pytest.importorskip("starlette")

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

try:
    from starlette.testclient import TestClient
except (ImportError, RuntimeError) as exc:
    pytest.skip(f"starlette.testclient unavailable: {exc}", allow_module_level=True)

from wepppy.query_engine.app.mcp import auth as auth_module


@pytest.fixture(autouse=True)
def clear_auth_cache():
    auth_module.get_auth_config.cache_clear()
    yield
    auth_module.get_auth_config.cache_clear()


@pytest.fixture
def auth_env(monkeypatch):
    monkeypatch.setenv("WEPP_MCP_JWT_SECRET", "unit-test-secret")
    monkeypatch.setenv("WEPP_MCP_JWT_ALGORITHMS", "HS256")
    auth_module.get_auth_config.cache_clear()
    module = reload(auth_module)
    module.get_auth_config.cache_clear()
    return module.get_auth_config()


def _make_app(config):
    async def handler(request):
        principal = request.state.mcp_principal
        return JSONResponse(
            {
                "subject": principal.subject,
                "scopes": sorted(principal.scopes),
                "runs": sorted(principal.run_ids) if principal.run_ids is not None else None,
            }
        )

    app = Starlette(routes=[Route("/mcp/ping", handler)])
    app.add_middleware(auth_module.MCPAuthMiddleware, config=config, path_prefix="/mcp")
    return app


def _issue_token(config, claims: dict[str, object]) -> str:
    base_claims = {
        "sub": "user-123",
        "scope": "runs:read queries:execute",
        "runs": ["alpha", "beta"],
    }
    base_claims.update(claims)
    return auth_module.encode_jwt(base_claims, config.secret, algorithm=config.algorithms[0])


def test_valid_token(auth_env):
    app = _make_app(auth_env)
    token = _issue_token(auth_env, {})
    client = TestClient(app)

    response = client.get("/mcp/ping", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"] == "user-123"
    assert payload["scopes"] == ["queries:execute", "runs:read"]
    assert payload["runs"] == ["alpha", "beta"]


def test_missing_authorization_header(auth_env):
    app = _make_app(auth_env)
    client = TestClient(app)

    response = client.get("/mcp/ping")

    assert response.status_code == 401
    body = response.json()
    assert body["errors"][0]["code"] == "unauthorized"


def test_invalid_signature(auth_env):
    app = _make_app(auth_env)
    other_secret = "other-secret"
    token = auth_module.encode_jwt({"sub": "user-456"}, other_secret, algorithm="HS256")
    client = TestClient(app)

    response = client.get("/mcp/ping", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    body = response.json()
    assert body["errors"][0]["code"] == "unauthorized"


def test_scope_validation(auth_env, monkeypatch):
    monkeypatch.setenv("WEPP_MCP_JWT_ALLOWED_SCOPES", "runs:read,queries:execute")
    auth_module.get_auth_config.cache_clear()
    reload(auth_module)
    config = auth_module.get_auth_config()
    app = _make_app(config)
    token = _issue_token(config, {"scope": "runs:read unknown:scope"})

    client = TestClient(app)
    response = client.get("/mcp/ping", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    body = response.json()
    assert "unsupported scope" in body["errors"][0]["detail"]
