from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable

import pytest

pytest.importorskip("flask")

FastAPITestClient = pytest.importorskip("fastapi.testclient").TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

StarletteTestClient = pytest.importorskip("starlette.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.browse import auth as browse_auth
from wepppy.microservices.browse import browse as browse_module
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine import session_routes as rq_session_routes
from wepppy.query_engine.app.mcp import auth as mcp_auth
from wepppy.weppcloud.routes import weppcloud_site as weppcloud_site_module
from wepppy.weppcloud.routes.weppcloud_site import weppcloud_site_bp
from wepppy.weppcloud.utils import auth_tokens


@dataclass(frozen=True)
class IntegrationRun:
    runid: str
    config: str
    wd: Path


class IntegrationRedisDouble:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}

    def _purge_expired_key(self, key: str) -> None:
        payload = self._store.get(key)
        if payload is None:
            return
        _, expires_at = payload
        if expires_at is None:
            return
        if time.time() >= expires_at:
            self._store.pop(key, None)

    def _purge_expired_keys(self) -> None:
        for key in list(self._store.keys()):
            self._purge_expired_key(key)

    def set(self, key: str, value: Any, *args: Any, **kwargs: Any) -> bool:
        expires_at: float | None = None
        ex = kwargs.get("ex")
        if ex is not None:
            expires_at = time.time() + float(ex)
        self._store[key] = (value, expires_at)
        return True

    def setex(self, key: str, ttl_seconds: int, value: Any) -> bool:
        self._store[key] = (value, time.time() + max(0, int(ttl_seconds)))
        return True

    def get(self, key: str) -> Any | None:
        self._purge_expired_key(key)
        payload = self._store.get(key)
        if payload is None:
            return None
        value, _expires_at = payload
        return value

    def exists(self, key: str) -> int:
        self._purge_expired_key(key)
        return 1 if key in self._store else 0

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._store:
                self._store.pop(key, None)
                deleted += 1
        return deleted

    def ttl(self, key: str) -> int:
        self._purge_expired_key(key)
        payload = self._store.get(key)
        if payload is None:
            return -2
        _value, expires_at = payload
        if expires_at is None:
            return -1
        remaining = int(expires_at - time.time())
        return max(0, remaining)

    def close(self) -> None:
        return None

    def flushall(self) -> None:
        self._store.clear()

    def __enter__(self) -> "IntegrationRedisDouble":
        self._purge_expired_keys()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.fixture(autouse=True)
def integration_auth_environment(monkeypatch: pytest.MonkeyPatch) -> Iterable[None]:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "integration-wepp-secret")
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    monkeypatch.setenv("WEPP_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("WEPP_AUTH_JWT_ISSUER", "weppcloud")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_AUDIENCE", "rq-engine")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS", "600")
    monkeypatch.setenv("WEPP_AUTH_JWT_LEEWAY", "0")

    monkeypatch.setenv("WEPP_MCP_JWT_SECRET", "integration-mcp-secret")
    monkeypatch.setenv("WEPP_MCP_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("WEPP_MCP_JWT_ISSUER", "query-engine")
    monkeypatch.setenv("WEPP_MCP_JWT_AUDIENCE", "query-engine-mcp")
    monkeypatch.setenv("WEPP_MCP_JWT_ALLOWED_SCOPES", "runs:read,queries:execute")
    monkeypatch.setenv("WEPP_MCP_JWT_LEEWAY", "0")

    monkeypatch.setenv("RQ_ENGINE_JWT_AUDIENCE", "rq-engine")
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")

    auth_tokens.get_jwt_config.cache_clear()
    mcp_auth.get_auth_config.cache_clear()
    yield
    auth_tokens.get_jwt_config.cache_clear()
    mcp_auth.get_auth_config.cache_clear()


@pytest.fixture(autouse=True)
def integration_redis(monkeypatch: pytest.MonkeyPatch) -> IntegrationRedisDouble:
    redis_double = IntegrationRedisDouble()

    monkeypatch.setattr(rq_auth.redis, "Redis", lambda **_kwargs: redis_double)
    monkeypatch.setattr(rq_session_routes.redis, "Redis", lambda **_kwargs: redis_double)
    monkeypatch.setattr(browse_auth.redis, "Redis", lambda **_kwargs: redis_double)
    monkeypatch.setattr(mcp_auth.redis, "Redis", lambda **_kwargs: redis_double)

    return redis_double


@pytest.fixture
def integration_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> IntegrationRun:
    runid = "run-integration"
    config = "cfg"
    run_root = tmp_path / runid
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "demo.txt").write_text("hello", encoding="utf-8")

    _install_run_context(monkeypatch, runid=runid, run_root=run_root)

    return IntegrationRun(runid=runid, config=config, wd=run_root)


@pytest.fixture
def grouped_integration_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> IntegrationRun:
    runid = "upset-reckoning;;omni;;undisturbed"
    config = "disturbed9002"
    run_root = tmp_path / "grouped-run"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "secret.txt").write_text("grouped-secret", encoding="utf-8")

    _install_run_context(monkeypatch, runid=runid, run_root=run_root)

    return IntegrationRun(runid=runid, config=config, wd=run_root)


def _install_run_context(monkeypatch: pytest.MonkeyPatch, *, runid: str, run_root: Path) -> None:
    allowed_runids = {runid}
    parts = runid.split(";;")
    if len(parts) >= 3 and parts[-2] in {"omni", "omni-contrast"} and parts[-1]:
        allowed_runids.add(";;".join(parts[:-2]))

    def _get_wd(requested_runid: str, **_kwargs: Any) -> str:
        if requested_runid not in allowed_runids:
            raise FileNotFoundError(requested_runid)
        return str(run_root)

    monkeypatch.setattr(rq_auth, "get_wd", _get_wd)
    monkeypatch.setattr(rq_auth, "get_run_owners_lazy", lambda _runid: [])
    monkeypatch.setattr(rq_auth.Ron, "ispublic", staticmethod(lambda _wd: False))

    monkeypatch.setattr(browse_auth, "get_wd", _get_wd)
    monkeypatch.setattr(browse_auth.NoDbBase, "ispublic", staticmethod(lambda _wd: False))
    monkeypatch.setattr(browse_module, "get_wd", _get_wd)


@pytest.fixture
def rq_engine_client() -> Iterable[FastAPITestClient]:
    with FastAPITestClient(rq_engine.app) as client:
        yield client


@pytest.fixture
def browse_client() -> Iterable[StarletteTestClient]:
    app = browse_module.create_app()
    with StarletteTestClient(app) as client:
        yield client


@pytest.fixture
def weppcloud_app():
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "integration-flask-secret"
    app.register_blueprint(weppcloud_site_bp, url_prefix="/weppcloud")
    return app


@pytest.fixture
def weppcloud_client(weppcloud_app):
    with weppcloud_app.test_client() as client:
        yield client


@pytest.fixture
def set_weppcloud_user(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Any]:
    def _set(
        *,
        authenticated: bool,
        user_id: int = 42,
        email: str = "user@example.com",
        roles: tuple[str, ...] = ("User",),
    ) -> Any:
        if not authenticated:
            user = SimpleNamespace(is_anonymous=True, is_authenticated=False)
        else:
            role_values = [SimpleNamespace(name=role) for role in roles]
            user = SimpleNamespace(
                is_anonymous=False,
                is_authenticated=True,
                id=user_id,
                email=email,
                roles=role_values,
                get_id=lambda: str(user_id),
            )
        monkeypatch.setattr(weppcloud_site_module, "current_user", user, raising=False)
        return user

    return _set


@pytest.fixture
def issue_user_token() -> Callable[..., str]:
    def _issue(
        *,
        subject: str = "42",
        scopes: tuple[str, ...] = ("rq:status",),
        audience: str = "rq-engine",
        runs: tuple[str, ...] | None = None,
        roles: tuple[str, ...] = ("User",),
        email: str = "user@example.com",
        jti: str | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        claims: dict[str, Any] = {
            "token_class": "user",
            "roles": list(roles),
            "email": email,
            "jti": jti or uuid.uuid4().hex,
        }
        if extra_claims:
            claims.update(extra_claims)

        payload = auth_tokens.issue_token(
            subject,
            scopes=scopes,
            audience=audience,
            runs=list(runs) if runs else None,
            extra_claims=claims,
        )
        return str(payload["token"])

    return _issue


@pytest.fixture
def issue_session_token() -> Callable[..., str]:
    def _issue(
        *,
        runid: str,
        config: str,
        session_id: str = "session-1",
        scopes: tuple[str, ...] = ("rq:status",),
        audience: str = "rq-engine",
        jti: str | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        claims: dict[str, Any] = {
            "token_class": "session",
            "session_id": session_id,
            "runid": runid,
            "config": config,
            "jti": jti or uuid.uuid4().hex,
        }
        if extra_claims:
            claims.update(extra_claims)

        payload = auth_tokens.issue_token(
            session_id,
            scopes=scopes,
            audience=audience,
            runs=(runid,),
            extra_claims=claims,
        )
        return str(payload["token"])

    return _issue


@pytest.fixture
def issue_service_token() -> Callable[..., str]:
    def _issue(
        *,
        subject: str = "svc-integration",
        scopes: tuple[str, ...] = ("rq:status",),
        audience: str = "rq-engine",
        runs: tuple[str, ...] | None = None,
        jti: str | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        claims: dict[str, Any] = {
            "token_class": "service",
            "jti": jti or uuid.uuid4().hex,
        }
        if extra_claims:
            claims.update(extra_claims)

        payload = auth_tokens.issue_token(
            subject,
            scopes=scopes,
            audience=audience,
            runs=list(runs) if runs else None,
            extra_claims=claims,
        )
        return str(payload["token"])

    return _issue


@pytest.fixture
def issue_mcp_token() -> Callable[..., str]:
    def _issue(
        *,
        subject: str = "mcp-client",
        scopes: tuple[str, ...] = ("runs:read",),
        runs: tuple[str, ...] | None = None,
        jti: str | None = None,
        token_class: str = "mcp",
        expires_in: int = 600,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        config = mcp_auth.get_auth_config()
        now = int(time.time())
        claims: dict[str, Any] = {
            "sub": subject,
            "token_class": token_class,
            "scope": " ".join(scopes),
            "jti": jti or uuid.uuid4().hex,
            "iat": now,
            "exp": now + expires_in,
        }
        if config.issuer:
            claims["iss"] = config.issuer
        if config.audience:
            claims["aud"] = config.audience
        if runs is not None:
            claims["runs"] = list(runs)
        if extra_claims:
            claims.update(extra_claims)

        return mcp_auth.encode_jwt(claims, config.secret, algorithm=config.algorithms[0])

    return _issue


@pytest.fixture
def make_mcp_client() -> Callable[[], StarletteTestClient]:
    clients: list[StarletteTestClient] = []

    def _build() -> StarletteTestClient:
        config = mcp_auth.get_auth_config()

        async def _handler(request):
            principal = request.state.mcp_principal
            payload = {
                "subject": principal.subject,
                "scopes": sorted(principal.scopes),
                "runs": sorted(principal.run_ids) if principal.run_ids is not None else None,
            }
            return JSONResponse(payload)

        app = Starlette(routes=[Route("/mcp/ping", _handler)])
        app.add_middleware(mcp_auth.MCPAuthMiddleware, config=config, path_prefix="/mcp")
        client = StarletteTestClient(app)
        clients.append(client)
        return client

    yield _build

    for client in clients:
        client.close()
