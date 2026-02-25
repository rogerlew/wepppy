from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

import pytest

pytest.importorskip("flask")
from flask import Flask, redirect, request

pytestmark = pytest.mark.routes


class _DummyRon:
    config_stem = "cfg"

    @classmethod
    def getInstance(cls, _wd: str) -> "_DummyRon":
        return cls()


@pytest.fixture()
def run0_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp"))

    runid = "ab1234"
    run_root = tmp_path / runid
    run_root.mkdir(parents=True, exist_ok=True)

    def _fake_get_wd(requested_runid: str, **_kwargs) -> str:
        assert requested_runid == runid
        return str(run_root)

    url_for_calls: list[tuple[str, dict[str, str]]] = []

    def _fake_url_for_run(endpoint: str, **kwargs) -> str:
        url_for_calls.append((endpoint, kwargs))
        path = f"/weppcloud/runs/{kwargs['runid']}/{kwargs['config']}/"
        query: dict[str, str] = {}
        if kwargs.get("next"):
            query["next"] = kwargs["next"]
        if kwargs.get("pup"):
            query["pup"] = kwargs["pup"]
        return f"{path}?{urlencode(query)}" if query else path

    monkeypatch.setattr(module, "get_wd", _fake_get_wd)
    monkeypatch.setattr(module, "Ron", _DummyRon)
    monkeypatch.setattr(module, "url_for_run", _fake_url_for_run)

    app = Flask(__name__)
    app.config.update(SECRET_KEY="run0-test-secret", TESTING=True, SITE_PREFIX="/weppcloud")
    app.register_blueprint(module.run_0_bp)
    return app, module, runid, url_for_calls


@pytest.fixture()
def run0_prefixed_grouped_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp"))

    runid = "upset-reckoning;;omni;;undisturbed"
    config = "disturbed9002"
    run_root = tmp_path / "grouped"
    run_root.mkdir(parents=True, exist_ok=True)

    class _GroupedDummyRon:
        config_stem = config

        @classmethod
        def getInstance(cls, _wd: str) -> "_GroupedDummyRon":
            return cls()

    def _fake_get_wd(requested_runid: str, **_kwargs) -> str:
        assert requested_runid == runid
        return str(run_root)

    def _fake_url_for_run(endpoint: str, **kwargs) -> str:
        path = f"/weppcloud/runs/{kwargs['runid']}/{kwargs['config']}/"
        query: dict[str, str] = {}
        if kwargs.get("next"):
            query["next"] = kwargs["next"]
        if kwargs.get("pup"):
            query["pup"] = kwargs["pup"]
        return f"{path}?{urlencode(query)}" if query else path

    monkeypatch.setattr(module, "get_wd", _fake_get_wd)
    monkeypatch.setattr(module, "Ron", _GroupedDummyRon)
    monkeypatch.setattr(module, "url_for_run", _fake_url_for_run)

    app = Flask(__name__)
    app.config.update(SECRET_KEY="run0-test-secret", TESTING=True, SITE_PREFIX="/weppcloud")
    app.register_blueprint(module.run_0_bp, url_prefix="/weppcloud")
    return app, module, runid, config


def test_runs0_nocfg_mints_cookie_and_redirects_to_next(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, url_for_calls = run0_app
    cookie_calls: list[tuple[str, str]] = []

    def _set_cookie(response, *, runid: str, config: str) -> bool:
        cookie_calls.append((runid, config))
        response.set_cookie("probe", "1")
        return True

    monkeypatch.setattr(module, "_set_run_session_jwt_cookie", _set_cookie)

    raw_next = f"/weppcloud/runs/{runid}/browse/private.txt?download=1"
    with app.test_client() as client:
        response = client.get(f"/runs/{runid}/?next={quote(raw_next, safe='')}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == f"/weppcloud/runs/{runid}/cfg/browse/private.txt?download=1"
    assert cookie_calls == [(runid, "cfg")]
    assert url_for_calls == []


def test_runs0_nocfg_falls_back_to_runs0_when_cookie_mint_fails(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, _url_for_calls = run0_app
    monkeypatch.setattr(module, "_set_run_session_jwt_cookie", lambda response, *, runid, config: False)

    raw_next = f"/weppcloud/runs/{runid}/browse/private.txt"
    with app.test_client() as client:
        response = client.get(f"/runs/{runid}/?next={quote(raw_next, safe='')}", follow_redirects=False)

    assert response.status_code == 302
    parsed = urlparse(response.headers["Location"])
    assert parsed.path == f"/weppcloud/runs/{runid}/cfg/"
    next_values = parse_qs(parsed.query).get("next", [])
    assert next_values == [f"/weppcloud/runs/{runid}/cfg/browse/private.txt"]


def test_runs0_nocfg_ignores_invalid_next_and_uses_canonical_redirect(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, _url_for_calls = run0_app

    called = False

    def _unexpected_cookie_call(response, *, runid: str, config: str) -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(module, "_set_run_session_jwt_cookie", _unexpected_cookie_call)

    with app.test_client() as client:
        response = client.get(f"/runs/{runid}/?next={quote('https://evil.example/path', safe='')}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == f"/weppcloud/runs/{runid}/cfg/"
    assert called is False


def test_runs0_nocfg_rejects_cross_run_next(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, _url_for_calls = run0_app

    called = False

    def _unexpected_cookie_call(response, *, runid: str, config: str) -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(module, "_set_run_session_jwt_cookie", _unexpected_cookie_call)

    with app.test_client() as client:
        response = client.get(
            f"/runs/{runid}/?next={quote('/weppcloud/runs/other-run/browse/private.txt', safe='')}",
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/weppcloud/runs/{runid}/cfg/"
    assert called is False


def test_runs0_nocfg_rejects_dot_segment_traversal_next(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, _url_for_calls = run0_app

    called = False

    def _unexpected_cookie_call(response, *, runid: str, config: str) -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(module, "_set_run_session_jwt_cookie", _unexpected_cookie_call)

    with app.test_client() as client:
        response = client.get(
            f"/runs/{runid}/?next={quote(f'/weppcloud/runs/{runid}/cfg/../browse/private.txt', safe='')}",
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/weppcloud/runs/{runid}/cfg/"
    assert called is False


def test_set_run_session_jwt_cookie_sets_secure_for_forwarded_https(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, _url_for_calls = run0_app
    monkeypatch.setattr(module, "_session_identity_claims", lambda: (42, ["User"]))
    monkeypatch.setattr(module, "_resolve_session_id_from_request", lambda: "sid-1")
    monkeypatch.setattr(module, "_session_user_authorized_for_run", lambda *_args: True)
    monkeypatch.setattr(module, "_store_session_marker", lambda *_args: None)
    monkeypatch.setattr(module.auth_tokens, "issue_token", lambda *_args, **_kwargs: {"token": "session-token"})

    with app.test_request_context(f"/runs/{runid}/", headers={"X-Forwarded-Proto": "https"}):
        response = app.make_response(("ok", 200))
        assert module._set_run_session_jwt_cookie(response, runid=runid, config="cfg") is True

    set_cookie = response.headers.get("Set-Cookie", "")
    assert "Secure" in set_cookie


def test_set_run_session_jwt_cookie_secure_can_be_disabled_with_env_override(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, _url_for_calls = run0_app
    monkeypatch.setattr(module, "_session_identity_claims", lambda: (42, ["User"]))
    monkeypatch.setattr(module, "_resolve_session_id_from_request", lambda: "sid-1")
    monkeypatch.setattr(module, "_session_user_authorized_for_run", lambda *_args: True)
    monkeypatch.setattr(module, "_store_session_marker", lambda *_args: None)
    monkeypatch.setattr(module.auth_tokens, "issue_token", lambda *_args, **_kwargs: {"token": "session-token"})
    monkeypatch.setenv("WEPP_AUTH_SESSION_COOKIE_SECURE", "false")

    with app.test_request_context(f"/runs/{runid}/", headers={"X-Forwarded-Proto": "https"}):
        response = app.make_response(("ok", 200))
        assert module._set_run_session_jwt_cookie(response, runid=runid, config="cfg") is True

    set_cookie = response.headers.get("Set-Cookie", "")
    assert "Secure" not in set_cookie


def test_set_run_session_jwt_cookie_scopes_grouped_run_cookie_without_semicolon_path(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, _runid, _url_for_calls = run0_app
    grouped_runid = "upset-reckoning;;omni;;undisturbed"
    config = "disturbed9002"

    monkeypatch.setattr(module, "_session_identity_claims", lambda: (42, ["User"]))
    monkeypatch.setattr(module, "_resolve_session_id_from_request", lambda: "sid-1")
    monkeypatch.setattr(module, "_session_user_authorized_for_run", lambda *_args: True)
    monkeypatch.setattr(module, "_store_session_marker", lambda *_args: None)
    monkeypatch.setattr(module.auth_tokens, "issue_token", lambda *_args, **_kwargs: {"token": "session-token"})

    with app.test_request_context(f"/runs/{grouped_runid}/", headers={"X-Forwarded-Proto": "https"}):
        response = app.make_response(("ok", 200))
        assert module._set_run_session_jwt_cookie(response, runid=grouped_runid, config=config) is True

    set_cookie = response.headers.get("Set-Cookie", "")
    digest = hashlib.sha256(f"{grouped_runid}\n{config}".encode("utf-8")).hexdigest()[:16]
    expected_cookie_key = f"{module.DEFAULT_BROWSE_JWT_COOKIE_NAME}_{digest}"
    assert set_cookie.startswith(f"{expected_cookie_key}=session-token;")
    assert "Path=/weppcloud/runs/" in set_cookie
    assert "%3B" not in set_cookie


def test_set_run_session_jwt_cookie_uses_current_user_fallback_when_session_identity_missing(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, _url_for_calls = run0_app

    class _Owner:
        id = 42

    class _CurrentUser:
        is_authenticated = True
        id = 42

        @staticmethod
        def get_id() -> str:
            return "42"

        @staticmethod
        def has_role(_role: str) -> bool:
            return False

    class _AuthRon:
        @staticmethod
        def ispublic(_wd: str) -> bool:
            return False

    monkeypatch.setattr(module, "_session_identity_claims", lambda: (None, []))
    monkeypatch.setattr(module, "_resolve_session_id_from_request", lambda: None)
    monkeypatch.setattr(module, "_store_session_marker", lambda *_args: None)
    monkeypatch.setattr(module.auth_tokens, "issue_token", lambda *_args, **_kwargs: {"token": "session-token"})
    monkeypatch.setattr(module, "get_wd", lambda *_args, **_kwargs: "/tmp/run")
    monkeypatch.setattr(module, "Ron", _AuthRon)
    monkeypatch.setattr(module, "get_run_owners_lazy", lambda _runid: [_Owner()])
    monkeypatch.setattr(module, "current_user", _CurrentUser())

    with app.test_request_context(f"/runs/{runid}/", headers={"X-Forwarded-Proto": "https"}):
        response = app.make_response(("ok", 200))
        assert module._set_run_session_jwt_cookie(response, runid=runid, config="cfg") is True

    set_cookie = response.headers.get("Set-Cookie", "")
    assert "session-token" in set_cookie


def test_session_user_authorized_for_grouped_run_uses_parent_public_flag(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, module, _runid, _url_for_calls = run0_app
    wd_calls: list[str] = []

    def fake_get_wd(runid: str, **_kwargs):
        wd_calls.append(runid)
        return f"/tmp/{runid}"

    class _AuthRon:
        @staticmethod
        def ispublic(wd: str) -> bool:
            return wd.endswith("/decimal-pleasing")

    monkeypatch.setattr(module, "get_wd", fake_get_wd)
    monkeypatch.setattr(module, "Ron", _AuthRon)
    monkeypatch.setattr(
        module,
        "get_run_owners_lazy",
        lambda _runid: pytest.fail("owner lookup should not run for public parent runs"),
    )

    assert module._session_user_authorized_for_run("decimal-pleasing;;omni;;treated", None, []) is True
    assert wd_calls == ["decimal-pleasing"]


def test_session_user_authorized_for_grouped_batch_run_uses_parent_public_flag(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, module, _runid, _url_for_calls = run0_app
    wd_calls: list[str] = []

    def fake_get_wd(runid: str, **_kwargs):
        wd_calls.append(runid)
        return f"/tmp/{runid}"

    class _AuthRon:
        @staticmethod
        def ispublic(wd: str) -> bool:
            return wd.endswith("/batch;;spring-2025;;run-001")

    monkeypatch.setattr(module, "get_wd", fake_get_wd)
    monkeypatch.setattr(module, "Ron", _AuthRon)
    monkeypatch.setattr(
        module,
        "get_run_owners_lazy",
        lambda _runid: pytest.fail("owner lookup should not run for public parent runs"),
    )

    assert (
        module._session_user_authorized_for_run(
            "batch;;spring-2025;;run-001;;omni;;treated",
            None,
            [],
        )
        is True
    )
    assert wd_calls == ["batch;;spring-2025;;run-001"]


def test_session_user_authorized_for_private_grouped_batch_run_without_owners_is_false(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, module, _runid, _url_for_calls = run0_app

    monkeypatch.setattr(module, "get_wd", lambda *_args, **_kwargs: "/tmp/private")
    monkeypatch.setattr(module, "Ron", type("RonStub", (), {"ispublic": staticmethod(lambda _wd: False)}))
    monkeypatch.setattr(module, "get_run_owners_lazy", lambda _runid: [])
    monkeypatch.setattr(module, "_request_current_user_identity", lambda: (None, set()))

    assert (
        module._session_user_authorized_for_run(
            "batch;;spring-2025;;run-001;;omni;;treated",
            None,
            [],
        )
        is False
    )


def test_session_user_authorized_for_grouped_run_uses_parent_owner_lookup(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, module, _runid, _url_for_calls = run0_app

    class _Owner:
        id = 42

    owner_calls: list[str] = []

    monkeypatch.setattr(module, "get_wd", lambda *_args, **_kwargs: "/tmp/private")
    monkeypatch.setattr(module, "Ron", type("RonStub", (), {"ispublic": staticmethod(lambda _wd: False)}))

    def fake_get_run_owners(runid: str):
        owner_calls.append(runid)
        return [_Owner()]

    monkeypatch.setattr(module, "get_run_owners_lazy", fake_get_run_owners)
    monkeypatch.setattr(module, "_request_current_user_identity", lambda: (None, set()))

    assert (
        module._session_user_authorized_for_run(
            "decimal-pleasing;;omni;;treated",
            42,
            ["User"],
        )
        is True
    )
    assert owner_calls == ["decimal-pleasing"]


def test_composite_browse_redirect_chain_terminates_after_cookie_mint(
    run0_prefixed_grouped_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, config = run0_prefixed_grouped_app
    digest = hashlib.sha256(f"{runid}\n{config}".encode("utf-8")).hexdigest()[:16]
    expected_cookie_key = f"{module.DEFAULT_BROWSE_JWT_COOKIE_NAME}_{digest}"

    def _set_cookie(response, *, runid: str, config: str) -> bool:
        response.set_cookie(
            key=expected_cookie_key,
            value="session-token",
            path=module._browse_jwt_cookie_path(runid, config),
        )
        return True

    monkeypatch.setattr(module, "_set_run_session_jwt_cookie", _set_cookie)

    @app.get("/weppcloud/runs/<string:requested_runid>/<string:requested_config>/browse/<path:subpath>")
    def _fake_browse(requested_runid: str, requested_config: str, subpath: str):
        assert requested_config == config
        _ = subpath
        if request.cookies.get(expected_cookie_key) == "session-token":
            return "ok", 200
        request_target = request.path
        if request.query_string:
            request_target = f"{request_target}?{request.query_string.decode('utf-8')}"
        return redirect(f"/weppcloud/runs/{requested_runid}/?next={quote(request_target, safe='')}")

    start_path = f"/weppcloud/runs/{runid}/{config}/browse/secret.txt"
    with app.test_client() as client:
        response = client.get(start_path, follow_redirects=True)

    assert response.status_code == 200
    assert response.data == b"ok"
    assert [item.status_code for item in response.history] == [302, 302]
    assert len(response.history) <= 3


@pytest.mark.parametrize(
    "next_path",
    [
        "/weppcloud/runs/{runid}/cfg/%2e%2e/browse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%252e%252e/browse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%25252e%25252e/browse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%2f..%2fbrowse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%252f..%252fbrowse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%25252f..%25252fbrowse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%5c..%5cbrowse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%255c..%255cbrowse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%25255c..%25255cbrowse/private.txt",
    ],
)
def test_runs0_nocfg_rejects_encoded_dot_segment_traversal_next(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
    next_path: str,
) -> None:
    app, module, runid, _url_for_calls = run0_app

    called = False

    def _unexpected_cookie_call(response, *, runid: str, config: str) -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(module, "_set_run_session_jwt_cookie", _unexpected_cookie_call)

    rendered = next_path.format(runid=runid)
    with app.test_client() as client:
        response = client.get(
            f"/runs/{runid}/?next={quote(rendered, safe='/%')}",
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/weppcloud/runs/{runid}/cfg/"
    assert called is False


def test_set_run_session_jwt_cookie_adds_fallback_admin_roles_to_claims(
    run0_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, runid, _url_for_calls = run0_app

    captured: dict[str, object] = {}

    class _CurrentUser:
        is_authenticated = True
        id = 7

        @staticmethod
        def get_id() -> str:
            return "7"

        @staticmethod
        def has_role(role: str) -> bool:
            return role in {"Admin", "Root"}

    monkeypatch.setattr(module, "_session_identity_claims", lambda: (None, []))
    monkeypatch.setattr(module, "_resolve_session_id_from_request", lambda: "sid-1")
    monkeypatch.setattr(module, "_session_user_authorized_for_run", lambda *_args: True)
    monkeypatch.setattr(module, "_store_session_marker", lambda *_args: None)
    monkeypatch.setattr(module, "current_user", _CurrentUser())

    def _issue_token(_subject, *, scopes, audience, expires_in, extra_claims):
        captured["extra_claims"] = extra_claims
        return {"token": "session-token"}

    monkeypatch.setattr(module.auth_tokens, "issue_token", _issue_token)

    with app.test_request_context(f"/runs/{runid}/", headers={"X-Forwarded-Proto": "https"}):
        response = app.make_response(("ok", 200))
        assert module._set_run_session_jwt_cookie(response, runid=runid, config="cfg") is True

    claims = captured["extra_claims"]
    assert claims["user_id"] == 7
    assert set(claims["roles"]) == {"admin", "root"}
