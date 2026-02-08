from __future__ import annotations

import importlib

import pytest

pytest.importorskip("flask")
from flask import Flask

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import bootstrap_routes as rq_bootstrap_routes
from wepppy.weppcloud.bootstrap.api_shared import (
    BootstrapForwardAuthContext,
    BootstrapOperationError,
    BootstrapOperationResult,
)

pytestmark = pytest.mark.routes

RUN_ID = "ab-run"
CONFIG = "cfg"


class DummyRun:
    def __init__(self, runid: str, owner_id: int, *, bootstrap_disabled: bool = False) -> None:
        self.runid = runid
        self.owner_id = owner_id
        self.bootstrap_disabled = bootstrap_disabled


class DummyUser:
    def __init__(self, user_id: int, email: str, roles: set[str] | None = None) -> None:
        self.id = user_id
        self.email = email
        self._roles = {role.lower() for role in (roles or set())}

    def has_role(self, role: str) -> bool:
        return role.lower() in self._roles


class ComparableAttribute:
    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.name)

    def __eq__(self, other):  # pragma: no cover - simple data holder
        return ("eq", self.name, other)


class DummyQuery:
    def __init__(self, run: DummyRun | None) -> None:
        self._run = run

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._run


class DummyDB:
    def __init__(self) -> None:
        self.commits = 0

    class Session:
        def __init__(self, outer: "DummyDB") -> None:
            self._outer = outer

        def commit(self) -> None:
            self._outer.commits += 1

    @property
    def session(self) -> "DummyDB.Session":
        return DummyDB.Session(self)


@pytest.fixture()
def bootstrap_context(monkeypatch: pytest.MonkeyPatch):
    import wepppy.weppcloud.routes._common as common

    monkeypatch.setattr(common, "login_required", lambda f: f)
    monkeypatch.setattr(common, "roles_required", lambda *args, **kwargs: (lambda f: f))
    monkeypatch.setattr(common, "roles_accepted", lambda *args, **kwargs: (lambda f: f))

    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes.bootstrap"))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["EXTERNAL_HOST"] = "wepp.cloud"
    app.register_blueprint(module.bootstrap_bp)

    monkeypatch.setattr(module, "authorize", lambda runid, config: None)

    def _set_current_user(user: DummyUser) -> None:
        monkeypatch.setattr(module, "current_user", user)

    return app, module, _set_current_user


def _stub_rq_auth(monkeypatch: pytest.MonkeyPatch, *, scope: str) -> None:
    monkeypatch.setattr(
        rq_bootstrap_routes,
        "require_jwt",
        lambda request, required_scopes=None: {
            "sub": "7",
            "email": "user@example.com",
            "scope": scope,
        },
    )
    monkeypatch.setattr(rq_bootstrap_routes, "authorize_run_access", lambda claims, runid: None)


def test_verify_token_success(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, _set_user = bootstrap_context
    monkeypatch.setattr(
        module,
        "verify_forward_auth_context",
        lambda **kwargs: BootstrapForwardAuthContext(runid=RUN_ID, email="user@example.com"),
    )
    monkeypatch.setattr(module, "ensure_bootstrap_eligibility", lambda *args, **kwargs: (object(), object()))
    monkeypatch.setattr(module, "ensure_bootstrap_opt_in", lambda runid: object())

    headers = {
        "Authorization": "Basic token",
        "X-Forwarded-Uri": f"/git/{RUN_ID[:2]}/{RUN_ID}/.git/info/refs",
    }

    with app.test_client() as client:
        response = client.get("/api/bootstrap/verify-token", headers=headers)

    assert response.status_code == 200
    assert response.headers.get("X-Auth-User") == "user@example.com"


def test_verify_token_uses_x_original_uri_when_forwarded_missing(
    bootstrap_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, _set_user = bootstrap_context
    seen: dict[str, str | None] = {"forwarded_path": None}

    def _verify(**kwargs):
        seen["forwarded_path"] = kwargs["forwarded_path"]
        return BootstrapForwardAuthContext(runid=RUN_ID, email="user@example.com")

    monkeypatch.setattr(module, "verify_forward_auth_context", _verify)
    monkeypatch.setattr(module, "ensure_bootstrap_eligibility", lambda *args, **kwargs: (object(), object()))
    monkeypatch.setattr(module, "ensure_bootstrap_opt_in", lambda runid: object())

    with app.test_client() as client:
        response = client.get(
            "/api/bootstrap/verify-token",
            headers={
                "Authorization": "Basic token",
                "X-Original-Uri": f"/git/{RUN_ID[:2]}/{RUN_ID}/.git/info/refs",
            },
        )

    assert response.status_code == 200
    assert seen["forwarded_path"] == f"/git/{RUN_ID[:2]}/{RUN_ID}/.git/info/refs"


def test_verify_token_prefers_x_forwarded_uri_when_both_headers_present(
    bootstrap_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, _set_user = bootstrap_context
    seen: dict[str, str | None] = {"forwarded_path": None}

    def _verify(**kwargs):
        seen["forwarded_path"] = kwargs["forwarded_path"]
        return BootstrapForwardAuthContext(runid=RUN_ID, email="user@example.com")

    monkeypatch.setattr(module, "verify_forward_auth_context", _verify)
    monkeypatch.setattr(module, "ensure_bootstrap_eligibility", lambda *args, **kwargs: (object(), object()))
    monkeypatch.setattr(module, "ensure_bootstrap_opt_in", lambda runid: object())

    with app.test_client() as client:
        response = client.get(
            "/api/bootstrap/verify-token",
            headers={
                "Authorization": "Basic token",
                "X-Forwarded-Uri": "/git/ab/forwarded/.git/info/refs",
                "X-Original-Uri": "/git/ab/original/.git/info/refs",
            },
        )

    assert response.status_code == 200
    assert seen["forwarded_path"] == "/git/ab/forwarded/.git/info/refs"


def test_verify_token_contract_returns_401_for_forward_auth_failures(
    bootstrap_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, _set_user = bootstrap_context

    monkeypatch.setattr(
        module,
        "verify_forward_auth_context",
        lambda **kwargs: (_ for _ in ()).throw(BootstrapOperationError("invalid git path", status_code=400)),
    )

    with app.test_client() as client:
        response = client.get(
            "/api/bootstrap/verify-token",
            headers={"Authorization": "Basic token", "X-Forwarded-Uri": "/git/ab/run/.git"},
        )

    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == 'Basic realm="Bootstrap"'
    assert b"invalid git path" in response.data


def test_verify_token_missing_forwarded_path_returns_401(
    bootstrap_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, _set_user = bootstrap_context

    monkeypatch.setattr(
        module,
        "verify_forward_auth_context",
        lambda **kwargs: (_ for _ in ()).throw(BootstrapOperationError("missing forwarded path", status_code=401)),
    )

    with app.test_client() as client:
        response = client.get(
            "/api/bootstrap/verify-token",
            headers={"Authorization": "Basic token"},
        )

    assert response.status_code == 401
    assert b"missing forwarded path" in response.data


def test_enable_bootstrap_enqueues_job(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, set_user = bootstrap_context
    set_user(DummyUser(20, "owner@example.com"))

    monkeypatch.setattr(
        module,
        "enable_bootstrap_operation",
        lambda runid, actor, email, require_user_access: BootstrapOperationResult(
            payload={
                "enabled": False,
                "queued": True,
                "job_id": "job-22",
                "message": "Bootstrap enable job enqueued.",
                "status_url": "/rq-engine/api/jobstatus/job-22",
            },
            status_code=202,
        ),
    )

    with app.test_client() as client:
        response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/enable")

    assert response.status_code == 202
    payload = response.get_json()
    assert payload == {
        "Content": {
            "enabled": False,
            "queued": True,
            "job_id": "job-22",
            "message": "Bootstrap enable job enqueued.",
            "status_url": "/rq-engine/api/jobstatus/job-22",
        }
    }


def test_mint_token_returns_clone_url(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, set_user = bootstrap_context
    user = DummyUser(30, "owner@example.com")
    set_user(user)

    monkeypatch.setattr(
        module,
        "mint_bootstrap_token_operation",
        lambda runid, user_email, user_id, require_user_access: BootstrapOperationResult(
            payload={"clone_url": f"clone://{user_id}@example.test/{user_email}"},
            status_code=200,
        ),
    )

    with app.test_client() as client:
        response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/mint-token")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"clone_url": f"clone://{user.id}@example.test/{user.email}"}}


def test_checkout_requires_sha(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, set_user = bootstrap_context
    set_user(DummyUser(32, "owner@example.com"))

    monkeypatch.setattr(
        module,
        "bootstrap_checkout_operation",
        lambda runid, sha, actor: (_ for _ in ()).throw(BootstrapOperationError("sha required", status_code=400)),
    )

    with app.test_client() as client:
        response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/checkout", json={})

    assert response.status_code == 400
    assert response.get_json() == {"error": {"message": "sha required"}}


def test_checkout_returns_conflict_when_lock_busy(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, set_user = bootstrap_context
    set_user(DummyUser(31, "owner@example.com"))

    monkeypatch.setattr(
        module,
        "bootstrap_checkout_operation",
        lambda runid, sha, actor: (_ for _ in ()).throw(
            BootstrapOperationError("bootstrap lock busy", status_code=409)
        ),
    )

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/bootstrap/checkout",
            json={"sha": "abc1234"},
        )

    assert response.status_code == 409
    assert response.get_json() == {"error": {"message": "bootstrap lock busy"}}


def test_bootstrap_disable_sets_flag(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, _set_user = bootstrap_context
    run = DummyRun(RUN_ID, owner_id=1)

    class DummyRunModel:
        runid = ComparableAttribute("runid")
        query = DummyQuery(run)

    db = DummyDB()
    app_module = importlib.import_module("wepppy.weppcloud.app")
    monkeypatch.setattr(app_module, "Run", DummyRunModel)
    monkeypatch.setattr(app_module, "db", db)

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/bootstrap/disable",
            json={"disabled": True},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"bootstrap_disabled": True}}
    assert run.bootstrap_disabled is True
    assert db.commits == 1


def test_bootstrap_disable_returns_404_for_missing_run(
    bootstrap_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, module, _set_user = bootstrap_context

    class DummyRunModel:
        runid = ComparableAttribute("runid")
        query = DummyQuery(None)

    db = DummyDB()
    app_module = importlib.import_module("wepppy.weppcloud.app")
    monkeypatch.setattr(app_module, "Run", DummyRunModel)
    monkeypatch.setattr(app_module, "db", db)

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/bootstrap/disable",
            json={"disabled": True},
        )

    assert response.status_code == 404
    assert response.get_json() == {"error": {"message": "run not found"}}
    assert db.commits == 0


def test_parity_enable_wrapper_matches_rq_engine(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, flask_module, set_user = bootstrap_context
    set_user(DummyUser(70, "owner@example.com"))

    result = BootstrapOperationResult(
        payload={"queued": True, "job_id": "job-enable", "status_url": "/rq-engine/api/jobstatus/job-enable"},
        status_code=202,
    )

    monkeypatch.setattr(flask_module, "enable_bootstrap_operation", lambda *args, **kwargs: result)
    monkeypatch.setattr(rq_bootstrap_routes, "enable_bootstrap_operation", lambda *args, **kwargs: result)
    _stub_rq_auth(monkeypatch, scope=rq_bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE)

    with app.test_client() as flask_client, TestClient(rq_engine.app) as rq_client:
        flask_response = flask_client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/enable")
        rq_response = rq_client.post(f"/api/runs/{RUN_ID}/{CONFIG}/bootstrap/enable")

    assert flask_response.status_code == rq_response.status_code == 202
    assert flask_response.get_json()["Content"] == rq_response.json()


def test_parity_mint_token_wrapper_matches_rq_engine(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, flask_module, set_user = bootstrap_context
    set_user(DummyUser(71, "owner@example.com"))

    result = BootstrapOperationResult(payload={"clone_url": "clone://71@example.test"}, status_code=200)

    monkeypatch.setattr(flask_module, "mint_bootstrap_token_operation", lambda *args, **kwargs: result)
    monkeypatch.setattr(rq_bootstrap_routes, "mint_bootstrap_token_operation", lambda *args, **kwargs: result)
    _stub_rq_auth(monkeypatch, scope=rq_bootstrap_routes.BOOTSTRAP_TOKEN_MINT_SCOPE)

    with app.test_client() as flask_client, TestClient(rq_engine.app) as rq_client:
        flask_response = flask_client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/mint-token")
        rq_response = rq_client.post(f"/api/runs/{RUN_ID}/{CONFIG}/bootstrap/mint-token")

    assert flask_response.status_code == rq_response.status_code == 200
    assert flask_response.get_json()["Content"] == rq_response.json()


def test_parity_commits_wrapper_matches_rq_engine(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, flask_module, set_user = bootstrap_context
    set_user(DummyUser(72, "owner@example.com"))

    result = BootstrapOperationResult(payload={"commits": [{"sha": "abc"}]}, status_code=200)

    monkeypatch.setattr(flask_module, "bootstrap_commits_operation", lambda *args, **kwargs: result)
    monkeypatch.setattr(rq_bootstrap_routes, "bootstrap_commits_operation", lambda *args, **kwargs: result)
    _stub_rq_auth(monkeypatch, scope=rq_bootstrap_routes.BOOTSTRAP_READ_SCOPE)

    with app.test_client() as flask_client, TestClient(rq_engine.app) as rq_client:
        flask_response = flask_client.get(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/commits")
        rq_response = rq_client.get(f"/api/runs/{RUN_ID}/{CONFIG}/bootstrap/commits")

    assert flask_response.status_code == rq_response.status_code == 200
    assert flask_response.get_json()["Content"] == rq_response.json()


def test_parity_current_ref_wrapper_matches_rq_engine(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, flask_module, set_user = bootstrap_context
    set_user(DummyUser(73, "owner@example.com"))

    result = BootstrapOperationResult(payload={"ref": "main"}, status_code=200)

    monkeypatch.setattr(flask_module, "bootstrap_current_ref_operation", lambda *args, **kwargs: result)
    monkeypatch.setattr(rq_bootstrap_routes, "bootstrap_current_ref_operation", lambda *args, **kwargs: result)
    _stub_rq_auth(monkeypatch, scope=rq_bootstrap_routes.BOOTSTRAP_READ_SCOPE)

    with app.test_client() as flask_client, TestClient(rq_engine.app) as rq_client:
        flask_response = flask_client.get(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/current-ref")
        rq_response = rq_client.get(f"/api/runs/{RUN_ID}/{CONFIG}/bootstrap/current-ref")

    assert flask_response.status_code == rq_response.status_code == 200
    assert flask_response.get_json()["Content"] == rq_response.json()


def test_parity_checkout_wrapper_matches_rq_engine(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, flask_module, set_user = bootstrap_context
    set_user(DummyUser(74, "owner@example.com"))

    result = BootstrapOperationResult(payload={"checked_out": "abc1234"}, status_code=200)

    monkeypatch.setattr(flask_module, "bootstrap_checkout_operation", lambda *args, **kwargs: result)
    monkeypatch.setattr(rq_bootstrap_routes, "bootstrap_checkout_operation", lambda *args, **kwargs: result)
    _stub_rq_auth(monkeypatch, scope=rq_bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE)

    with app.test_client() as flask_client, TestClient(rq_engine.app) as rq_client:
        flask_response = flask_client.post(
            f"/runs/{RUN_ID}/{CONFIG}/bootstrap/checkout",
            json={"sha": "abc1234"},
        )
        rq_response = rq_client.post(
            f"/api/runs/{RUN_ID}/{CONFIG}/bootstrap/checkout",
            json={"sha": "abc1234"},
        )

    assert flask_response.status_code == rq_response.status_code == 200
    assert flask_response.get_json()["Content"] == rq_response.json()
