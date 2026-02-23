from __future__ import annotations

import importlib
import logging
import uuid

import pytest

pytest.importorskip("flask")
from flask import Flask
from flask_security import RoleMixin, SQLAlchemyUserDatastore, Security, UserMixin
from flask_security.utils import hash_password, login_user
from flask_sqlalchemy import SQLAlchemy

pytestmark = pytest.mark.routes


def _configure_jwt_env(monkeypatch: pytest.MonkeyPatch, module) -> None:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "profile-token-secret")
    monkeypatch.setenv("WEPP_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_DEFAULT_AUDIENCE", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_ISSUER", raising=False)
    module.auth_tokens.get_jwt_config.cache_clear()


@pytest.fixture()
def profile_auth_client(monkeypatch: pytest.MonkeyPatch):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="profile-secret",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECURITY_PASSWORD_SALT="profile-salt",
        SECURITY_PASSWORD_HASH="bcrypt",
        SECURITY_REGISTERABLE=False,
        SECURITY_SEND_REGISTER_EMAIL=False,
        SECURITY_TRACKABLE=False,
        SECURITY_UNAUTHORIZED_VIEW=None,
    )

    db = SQLAlchemy()
    db.init_app(app)

    roles_users = db.Table(
        "roles_users",
        db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
        db.Column("role_id", db.Integer(), db.ForeignKey("role.id")),
    )

    class Role(db.Model, RoleMixin):
        id = db.Column(db.Integer(), primary_key=True)
        name = db.Column(db.String(80), unique=True)

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(255), unique=True)
        password = db.Column(db.String(255))
        active = db.Column(db.Boolean(), default=True)
        fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
        roles = db.relationship("Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic"))

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, user_datastore)

    @app.login_manager.unauthorized_handler
    def unauthorized():
        return "Unauthorized", 401

    @app.get("/test-login/<int:user_id>")
    def test_login(user_id: int):
        user = db.session.get(User, user_id)
        login_user(user)
        db.session.commit()
        return "ok"

    with app.app_context():
        db.create_all()
        user_role = user_datastore.create_role(name="User")
        user = user_datastore.create_user(
            email="user@example.com",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[user_role],
        )
        user_datastore.commit()
        user_id = user.id

    user_module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes.user"))
    app.register_blueprint(user_module.user_bp)

    with app.test_client() as client:
        yield {
            "client": client,
            "module": user_module,
            "user_id": user_id,
            "app": app,
            "db": db,
            "user_datastore": user_datastore,
            "user_model": User,
        }


def _grant_role(profile_auth_client, role_name: str) -> None:
    app = profile_auth_client["app"]
    db = profile_auth_client["db"]
    user_datastore = profile_auth_client["user_datastore"]
    user_model = profile_auth_client["user_model"]
    user_id = profile_auth_client["user_id"]

    with app.app_context():
        role = user_datastore.find_role(role_name)
        if role is None:
            role = user_datastore.create_role(name=role_name)
        user = db.session.get(user_model, user_id)
        assert user is not None
        user_datastore.add_role_to_user(user, role)
        user_datastore.commit()


def test_profile_token_mint_requires_login(profile_auth_client) -> None:
    client = profile_auth_client["client"]

    response = client.post("/profile/mint-token")

    assert response.status_code == 401


def test_profile_token_mint_requires_privileged_role(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]

    _configure_jwt_env(monkeypatch, module)
    client.get(f"/test-login/{user_id}")

    response = client.post("/profile/mint-token")

    assert response.status_code == 403
    payload = response.get_json()
    assert "requires one of these roles" in payload["error"]["message"]


def test_profile_token_mint_issues_90_day_user_token(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]

    _configure_jwt_env(monkeypatch, module)
    _grant_role(profile_auth_client, "PowerUser")
    client.get(f"/test-login/{user_id}")

    response = client.post("/profile/mint-token")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    payload = response.get_json()
    content = payload["Content"]
    token = content["token"]
    claims = module.auth_tokens.decode_token(token, audience="rq-engine")

    assert content["token_class"] == "user"
    assert content["expires_in"] == 90 * 24 * 60 * 60
    assert content["audience"] == ["rq-engine", "query-engine"]
    assert content["scopes"] == [
        "runs:read",
        "queries:validate",
        "queries:execute",
        "rq:status",
        "rq:enqueue",
        "rq:export",
    ]

    assert claims["token_class"] == "user"
    assert claims["sub"] == str(user_id)
    assert claims["email"] == "user@example.com"
    assert set(claims["roles"]) == {"PowerUser", "User"}
    assert claims["groups"] == []
    assert claims["exp"] - claims["iat"] == 90 * 24 * 60 * 60


def test_profile_token_mint_errors_without_jwt_secret(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]

    monkeypatch.delenv("WEPP_AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    _grant_role(profile_auth_client, "PowerUser")
    module.auth_tokens.get_jwt_config.cache_clear()
    client.get(f"/test-login/{user_id}")

    response = client.post("/profile/mint-token")

    assert response.status_code == 500
    payload = response.get_json()
    assert "WEPP_AUTH_JWT_SECRET must be set to issue tokens" in payload["error"]["message"]


def test_profile_hides_token_controls_without_privileged_role(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    captured_context: dict = {}

    def _fake_render_template(_name: str, **context):
        captured_context.update(context)
        if context.get("can_mint_profile_token"):
            return "data-profile-token-root"
        return "token-controls-hidden"

    monkeypatch.setattr(module, "render_template", _fake_render_template)

    client.get(f"/test-login/{user_id}")
    response = client.get("/profile")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "token-controls-hidden"
    assert captured_context.get("can_mint_profile_token") is False
    assert captured_context.get("reset_browser_state_endpoint") is None
    assert captured_context.get("reset_browser_state_login_url") == "/login"


def test_profile_shows_token_controls_for_privileged_role(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    captured_context: dict = {}

    def _fake_render_template(_name: str, **context):
        captured_context.update(context)
        if context.get("can_mint_profile_token"):
            return "data-profile-token-root"
        return "token-controls-hidden"

    monkeypatch.setattr(module, "render_template", _fake_render_template)

    _grant_role(profile_auth_client, "Dev")
    client.get(f"/test-login/{user_id}")
    response = client.get("/profile")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "data-profile-token-root"
    assert captured_context.get("can_mint_profile_token") is True
    assert captured_context.get("reset_browser_state_endpoint") is None
    assert captured_context.get("reset_browser_state_login_url") == "/login"


def test_profile_returns_500_json_error_when_template_render_raises(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]

    def _explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "render_template", _explode)

    client.get(f"/test-login/{user_id}")
    response = client.get("/profile")

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "Error Handling Request"


def test_claim_names_logs_and_degrades_on_sqlalchemy_error(
    profile_auth_client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = profile_auth_client["module"]

    class _ExplodingClaims:
        def all(self):
            raise module.SQLAlchemyError("db down")

    caplog.set_level(logging.WARNING, logger=module.logger.name)
    assert module._claim_names(_ExplodingClaims()) == []
    assert "failed to evaluate dynamic relationship via .all()" in caplog.text
