from __future__ import annotations

import base64
import importlib
import time

import pytest

pytest.importorskip("flask")
from flask import Flask

pytestmark = pytest.mark.routes

RUN_ID = "ab-run"
CONFIG = "cfg"
PREFIX = RUN_ID[:2]


class DummyRun:
    def __init__(self, runid: str, owner_id: int, *, bootstrap_disabled: bool = False) -> None:
        self.runid = runid
        self.owner_id = owner_id
        self.bootstrap_disabled = bootstrap_disabled
        self.users: list[DummyUser] = []


class DummyUser:
    def __init__(self, user_id: int, email: str) -> None:
        self.id = user_id
        self.email = email

    def has_role(self, role: str) -> bool:
        return False


class DummyWepp:
    def __init__(self, enabled: bool = False) -> None:
        self.bootstrap_enabled = enabled
        self.init_calls = 0
        self.checkout_calls: list[str] = []

    def init_bootstrap(self) -> None:
        self.init_calls += 1
        self.bootstrap_enabled = True

    def mint_bootstrap_jwt(self, user_email: str, user_id: str) -> str:
        return f"clone://{user_id}@example.test/{user_email}"

    def get_bootstrap_commits(self) -> list[dict]:
        return [{"sha": "abc", "author": "user@example.com"}]

    def checkout_bootstrap_commit(self, sha: str) -> bool:
        self.checkout_calls.append(sha)
        return True

    def get_bootstrap_current_ref(self) -> str:
        return "main"


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

    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes.bootstrap"))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["EXTERNAL_HOST"] = "wepp.cloud"
    app.register_blueprint(module.bootstrap_bp)

    monkeypatch.setattr(module, "authorize", lambda runid, config: None)

    def _set_current_user(user: DummyUser) -> None:
        monkeypatch.setattr(module, "current_user", user)

    return app, module, _set_current_user


def _basic_auth(user_id: str, token: str) -> str:
    payload = f"{user_id}:{token}".encode("utf-8")
    return base64.b64encode(payload).decode("utf-8")


def _configure_jwt_env(monkeypatch: pytest.MonkeyPatch, module) -> None:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    monkeypatch.setenv("WEPP_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_DEFAULT_AUDIENCE", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_ISSUER", raising=False)
    module.auth_tokens.get_jwt_config.cache_clear()


def test_verify_token_success(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, _set_user = bootstrap_context
    user = DummyUser(10, "user@example.com")
    run = DummyRun(RUN_ID, owner_id=user.id)
    run.users.append(user)

    monkeypatch.setattr(module, "_resolve_run_record", lambda runid: run)
    monkeypatch.setattr(module, "_resolve_user_by_email", lambda email: user)
    monkeypatch.setattr(module.Wepp, "getInstance", lambda wd: DummyWepp(enabled=True))
    monkeypatch.setattr(
        module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {"sub": user.email, "runid": run.runid},
    )

    headers = {
        "Authorization": f"Basic {_basic_auth('u1', 'tok')}",
        "X-Forwarded-Uri": f"/git/{PREFIX}/{RUN_ID}",
    }

    with app.test_client() as client:
        response = client.get("/api/bootstrap/verify-token", headers=headers)

    assert response.status_code == 200
    assert response.headers.get("X-Auth-User") == user.email


def test_verify_token_rejects_disabled_run(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, _set_user = bootstrap_context
    user = DummyUser(11, "user@example.com")
    run = DummyRun(RUN_ID, owner_id=user.id, bootstrap_disabled=True)

    monkeypatch.setattr(module, "_resolve_run_record", lambda runid: run)
    monkeypatch.setattr(module, "_resolve_user_by_email", lambda email: user)
    monkeypatch.setattr(module.Wepp, "getInstance", lambda wd: DummyWepp(enabled=True))
    monkeypatch.setattr(
        module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {"sub": user.email, "runid": run.runid},
    )

    headers = {
        "Authorization": f"Basic {_basic_auth('u2', 'tok')}",
        "X-Forwarded-Uri": f"/git/{PREFIX}/{RUN_ID}",
    }

    with app.test_client() as client:
        response = client.get("/api/bootstrap/verify-token", headers=headers)

    assert response.status_code == 401
    assert b"bootstrap disabled" in response.data


def test_verify_token_rejects_expired_jwt(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, _set_user = bootstrap_context
    _configure_jwt_env(monkeypatch, module)

    now = int(time.time())
    token = module.auth_tokens.issue_token(
        "user@example.com",
        audience="wepp.cloud",
        expires_in=60,
        issued_at=now - 120,
        extra_claims={"runid": RUN_ID},
    )["token"]

    headers = {
        "Authorization": f"Basic {_basic_auth('u3', token)}",
        "X-Forwarded-Uri": f"/git/{PREFIX}/{RUN_ID}",
    }

    with app.test_client() as client:
        response = client.get("/api/bootstrap/verify-token", headers=headers)

    assert response.status_code == 401
    assert b"invalid token: Token has expired" in response.data


def test_verify_token_rejects_invalid_jwt(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, _set_user = bootstrap_context
    _configure_jwt_env(monkeypatch, module)

    token = "not-a-jwt"
    headers = {
        "Authorization": f"Basic {_basic_auth('u4', token)}",
        "X-Forwarded-Uri": f"/git/{PREFIX}/{RUN_ID}",
    }

    with app.test_client() as client:
        response = client.get("/api/bootstrap/verify-token", headers=headers)

    assert response.status_code == 401
    assert b"invalid token: Invalid token format" in response.data


def test_enable_bootstrap_calls_init(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, set_user = bootstrap_context
    user = DummyUser(20, "owner@example.com")
    set_user(user)
    wepp = DummyWepp(enabled=False)

    monkeypatch.setattr(module, "_validate_bootstrap_eligibility", lambda runid, email: (object(), user))
    monkeypatch.setattr(module, "get_wd", lambda runid: f"/tmp/{runid}")
    monkeypatch.setattr(module.Wepp, "getInstance", lambda wd: wepp)

    with app.test_client() as client:
        response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/enable")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"enabled": True}}
    assert wepp.init_calls == 1
    assert wepp.bootstrap_enabled is True


def test_mint_token_returns_clone_url(bootstrap_context, monkeypatch: pytest.MonkeyPatch) -> None:
    app, module, set_user = bootstrap_context
    user = DummyUser(30, "owner@example.com")
    set_user(user)
    wepp = DummyWepp(enabled=True)

    monkeypatch.setattr(module, "_validate_bootstrap_eligibility", lambda runid, email: (object(), user))
    monkeypatch.setattr(module, "get_wd", lambda runid: f"/tmp/{runid}")
    monkeypatch.setattr(module.Wepp, "getInstance", lambda wd: wepp)

    with app.test_client() as client:
        response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/mint-token")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"clone_url": f"clone://{user.id}@example.test/{user.email}"}}


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
