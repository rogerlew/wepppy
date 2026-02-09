from __future__ import annotations

import importlib
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

import pytest

pytest.importorskip("flask")
from flask import Flask

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


@pytest.mark.parametrize(
    "next_path",
    [
        "/weppcloud/runs/{runid}/cfg/%2e%2e/browse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%252e%252e/browse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%2f..%2fbrowse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%252f..%252fbrowse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%5c..%5cbrowse/private.txt",
        "/weppcloud/runs/{runid}/cfg/%255c..%255cbrowse/private.txt",
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
