import json

import pytest

pytest.importorskip("flask")
from flask import Blueprint, Flask, abort, g, request

from wepppy.weppcloud.routes import _run_context
from wepppy.weppcloud.routes._run_config import register_run_config_hooks

pytestmark = pytest.mark.routes


@pytest.fixture
def run_app(tmp_path, monkeypatch):
    monkeypatch.setattr(_run_context, "get_wd", lambda *a, **k: str(tmp_path))
    (tmp_path / "ron.nodb").write_text(json.dumps({"py/state": {"_config": "disturbed9002-wbt-mofe.cfg"}}))
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_run_config_hooks(app)
    calls = []
    bp = Blueprint("probe", __name__)

    @bp.route("/runs/<runid>/<config>/report/<path:suffix>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def probe(runid, config, suffix):
        if request.headers.get("X-Deny"):
            abort(403)
        calls.append((config, request.get_data(), g.run_context.config))
        return {"config": config, "suffix": suffix}

    app.register_blueprint(bp)
    return app, tmp_path, calls


@pytest.mark.parametrize("stored", ["config.cfg", "preset", "preset.cfg?wepp:foo=true", "preset?wepp:foo=true"])
def test_stored_forms_and_readonly_lookup(run_app, stored):
    app, root, calls = run_app
    path = root / "ron.nodb"
    path.write_text(json.dumps({"py/state": {"_config": stored}}))
    original = path.read_bytes()
    response = app.test_client().get("/runs/run/stale/report/a")
    token = stored.split("?", 1)[0].removesuffix(".cfg")
    assert response.status_code == 302
    assert response.location == f"/runs/run/{token}/report/a"
    assert calls == [(token, b"", token)]
    assert path.read_bytes() == original


def test_prefix_suffix_and_repeated_query(run_app):
    app, _, _ = run_app
    response = app.test_client().get("/runs/run/stale/report/a/b?x=1&x=2&value=a%2Fb", environ_overrides={"SCRIPT_NAME": "/weppcloud"})
    assert response.location == "/weppcloud/runs/run/disturbed9002-wbt-mofe/report/a/b?x=1&x=2&value=a%2Fb"


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_mutation_dispatched_once_without_redirect(run_app, method):
    app, _, calls = run_app
    response = app.test_client().open("/runs/run/stale/report/a", method=method, data=b"payload")
    assert response.status_code == 200
    assert "Location" not in response.headers
    assert calls == [("disturbed9002-wbt-mofe", b"payload", "disturbed9002-wbt-mofe")]


def test_denied_response_not_redirected(run_app):
    app, _, calls = run_app
    response = app.test_client().get("/runs/run/stale/report/a", headers={"X-Deny": "yes"})
    assert response.status_code == 403
    assert "Location" not in response.headers
    assert not calls


@pytest.mark.parametrize("raw", [None, "broken", "{}", '{"py/state":{"_config":"../escape.cfg"}}', '{"py/state":{"_config":""}}'])
def test_invalid_identity_generic_404_no_dispatch(run_app, raw):
    app, root, calls = run_app
    path = root / "ron.nodb"
    if raw is None:
        path.unlink()
    else:
        path.write_text(raw)
    response = app.test_client().post("/runs/run/stale/report/a", data="must not execute")
    assert response.status_code == 404
    assert b"Run not found" in response.data
    assert "Location" not in response.headers
    assert not calls


def test_pup_identity_and_containment(run_app):
    app, root, _ = run_app
    pup = root / "_pups" / "child"
    pup.mkdir(parents=True)
    (pup / "ron.nodb").write_text('{"py/state":{"_config":"child.cfg"}}')
    client = app.test_client()
    assert "/child/report/a?pup=child" in client.get("/runs/run/stale/report/a?pup=child").location
    assert client.get("/runs/run/stale/report/a?pup=../../escape").status_code == 404


def test_composite_ignores_pup(run_app):
    app, _, _ = run_app
    response = app.test_client().get("/runs/batch;;demo;;leaf/stale/report/a?pup=missing")
    assert response.status_code == 302
    assert "disturbed9002-wbt-mofe" in response.location


def test_canonical_head_options_and_unmatched(run_app):
    app, root, calls = run_app
    client = app.test_client()
    assert client.get("/runs/run/disturbed9002-wbt-mofe/report/a").status_code == 200
    assert client.head("/runs/run/stale/report/a").status_code == 302
    (root / "ron.nodb").unlink()
    assert client.options("/runs/run/stale/report/a").status_code == 200
    assert client.get("/not-a-run").status_code == 404


def test_csrf_guard_retained(run_app):
    from flask_wtf.csrf import CSRFProtect, generate_csrf

    app, _, calls = run_app
    app.secret_key = "test-only-secret"
    CSRFProtect(app)

    @app.get("/csrf-token")
    def token():
        return generate_csrf()

    client = app.test_client()
    response = client.post("/runs/run/stale/report/a", data="payload")
    assert response.status_code == 400
    assert not calls
    csrf_token = client.get("/csrf-token").get_data(as_text=True)
    response = client.post("/runs/run/stale/report/a", data="payload", headers={"X-CSRFToken": csrf_token})
    assert response.status_code == 200
    assert calls == [("disturbed9002-wbt-mofe", b"payload", "disturbed9002-wbt-mofe")]


def test_response_cookie_and_resource_cleanup(run_app):
    from flask import Response

    app, _, _ = run_app
    closed = []

    @app.get("/runs/<runid>/<config>/stream")
    def stream(runid, config):
        response = Response(iter([b"result"]))
        response.set_cookie("run_cookie", "value")
        response.call_on_close(lambda: closed.append(True))
        return response

    response = app.test_client().get("/runs/run/stale/stream")
    assert response.status_code == 302
    assert "run_cookie=value" in response.headers["Set-Cookie"]
    assert closed == [True]


def test_blueprint_context_and_exact_alias(run_app):
    app, _, _ = run_app
    bp = Blueprint("aliases", __name__)
    _run_context.register_run_context_preprocessor(bp)

    @bp.route("/runs/<runid>/<config>/second")
    @bp.route("/runs/<runid>/<config>/first")
    def aliases(runid, config):
        assert g.run_context.config == config == "disturbed9002-wbt-mofe"
        return "ok"

    app.register_blueprint(bp)
    response = app.test_client().get("/runs/run/stale/second")
    assert response.location.endswith("/disturbed9002-wbt-mofe/second")


def test_existing_redirect_retained(run_app):
    from flask import redirect

    app, _, _ = run_app

    @app.get("/runs/<runid>/<config>/login-gate")
    def login_gate(runid, config):
        return redirect("/login")

    response = app.test_client().get("/runs/run/stale/login-gate")
    assert response.status_code == 302
    assert response.location == "/login"
