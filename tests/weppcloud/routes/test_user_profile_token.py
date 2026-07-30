from __future__ import annotations

import importlib
import logging
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest
from jinja2 import DictLoader, Environment
from werkzeug.exceptions import Forbidden

pytest.importorskip("flask")
from flask import Blueprint, Flask
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError, generate_csrf
from flask_security import RoleMixin, SQLAlchemyUserDatastore, Security, UserMixin
from flask_security.utils import hash_password, login_user
from flask_sqlalchemy import SQLAlchemy

pytestmark = pytest.mark.routes

REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILE_TEMPLATE = REPO_ROOT / "wepppy" / "weppcloud" / "templates" / "user" / "profile.html"


def test_profile_template_links_to_diagnostics_without_reset_control() -> None:
    source = PROFILE_TEMPLATE.read_text(encoding="utf-8")

    assert "weppcloud_site.diagnostics" in source
    assert "url_for('user.preferences')" in source
    assert "data-browser-reset-root" not in source
    assert "data-browser-reset-action" not in source
    assert "reset_browser_state_endpoint" not in source


def _configure_jwt_env(monkeypatch: pytest.MonkeyPatch, module) -> None:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "profile-token-secret")
    monkeypatch.setenv("WEPP_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_DEFAULT_AUDIENCE", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_ISSUER", raising=False)
    module.auth_tokens.get_jwt_config.cache_clear()


@pytest.fixture()
def profile_auth_client(monkeypatch: pytest.MonkeyPatch):
    app = Flask(
        __name__,
        template_folder=str(REPO_ROOT / "wepppy" / "weppcloud" / "templates"),
    )
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
    app.jinja_env.globals["static_url"] = lambda path: f"/static/{path}"
    app.jinja_env.globals["csrf_token"] = lambda: "test-csrf-token"
    app.jinja_env.globals["usersum_doc_link"] = (
        lambda _category, _filename, label: label
    )

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
    site_bp = Blueprint("weppcloud_site", __name__)

    @site_bp.get("/", endpoint="index")
    def index():
        return "index"

    @site_bp.get("/diagnostics/", endpoint="diagnostics")
    def diagnostics():
        return "diagnostics"

    app.register_blueprint(site_bp, url_prefix="/weppcloud")
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


def test_preferences_requires_login(profile_auth_client) -> None:
    response = profile_auth_client["client"].get("/preferences")

    assert response.status_code == 401


def test_preferences_get_renders_exact_choices(profile_auth_client, monkeypatch) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    monkeypatch.setattr(
        module,
        "load_user_preferences",
        lambda _user_id: module.UserPreferenceValues("si", "error"),
    )
    client.get(f"/test-login/{user_id}")

    response = client.get("/preferences")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Auto — use project configuration" in body
    assert "SI — metric defaults" in body
    assert "English — US customary defaults" in body
    assert "Warn and continue" in body
    assert "Stop with an error" in body
    assert 'value="si" selected' in body
    assert 'value="error" selected' in body
    assert "These preferences follow your account" in body
    assert "Changes save automatically." in body
    assert "changes display units for you only" in body
    assert "choose a different outlet or enlarge the project extent" in body
    assert 'data-user-preferences-status' in body
    assert 'data-user-preferences-status-message' in body
    assert 'wc-alert--info wc-user-preferences__status' in body
    assert 'data-user-preferences-error' in body
    assert 'class="wc-user-preferences__fields"' in body
    assert 'src="/static/js/user_preferences.js"' in body
    assert "<noscript>" in body


def test_preferences_invalid_post_reports_both_fields_without_write(
    profile_auth_client,
    monkeypatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    writes = []
    monkeypatch.setattr(module, "save_user_preferences", lambda *args: writes.append(args))
    client.get(f"/test-login/{user_id}")

    response = client.post(
        "/preferences",
        data={
            "unit_system": "<invalid>",
            "wbt_boundary_touch_behavior": "",
        },
    )

    assert response.status_code == 400
    assert writes == []
    body = response.get_data(as_text=True)
    assert "Select a valid default unit system." in body
    assert "Select a valid WBT DEM-boundary behavior." in body
    assert "<invalid>" not in body
    assert 'aria-invalid="true"' in body


def test_preferences_success_uses_prg_and_atomic_save(
    profile_auth_client,
    monkeypatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    writes = []
    monkeypatch.setattr(module, "save_user_preferences", lambda *args: writes.append(args))
    client.get(f"/test-login/{user_id}")

    response = client.post(
        "/preferences",
        data={
            "unit_system": "english",
            "wbt_boundary_touch_behavior": "error",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/preferences")
    assert writes == [(user_id, "english", "error")]
    with client.session_transaction() as session:
        assert ("success", "User preferences saved.") in session["_flashes"]


def test_preferences_json_success_returns_saved_complete_record(
    profile_auth_client,
    monkeypatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    writes = []

    def save_preferences(*args):
        writes.append(args)
        return module.UserPreferenceValues("english", "warn")

    monkeypatch.setattr(module, "save_user_preferences", save_preferences)
    client.get(f"/test-login/{user_id}")

    response = client.post(
        "/preferences",
        data={
            "unit_system": "english",
            "wbt_boundary_touch_behavior": "warn",
        },
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 200
    assert writes == [(user_id, "english", "warn")]
    assert response.get_json() == {
        "ok": True,
        "message": "Preferences saved.",
        "preferences": {
            "unit_system": "english",
            "wbt_boundary_touch_behavior": "warn",
        },
    }


def test_preferences_json_validation_error_is_bounded_and_does_not_write(
    profile_auth_client,
    monkeypatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    writes = []
    monkeypatch.setattr(
        module,
        "save_user_preferences",
        lambda *args: writes.append(args),
    )
    client.get(f"/test-login/{user_id}")

    response = client.post(
        "/preferences",
        data={
            "unit_system": "invalid",
            "wbt_boundary_touch_behavior": "",
        },
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 400
    assert writes == []
    assert response.get_json() == {
        "ok": False,
        "message": "Correct the highlighted preference values.",
        "errors": {
            "unit_system": "Select a valid default unit system.",
            "wbt_boundary_touch_behavior": (
                "Select a valid WBT DEM-boundary behavior."
            ),
        },
    }


def test_preferences_post_enforces_csrf(profile_auth_client) -> None:
    app = profile_auth_client["app"]
    client = profile_auth_client["client"]
    user_id = profile_auth_client["user_id"]

    @app.errorhandler(CSRFError)
    def handle_preferences_csrf_error(error):
        return {"error": error.description}, 400

    CSRFProtect(app)
    client.get(f"/test-login/{user_id}")

    response = client.post(
        "/preferences",
        data={
            "unit_system": "si",
            "wbt_boundary_touch_behavior": "error",
        },
    )

    assert response.status_code == 400


def test_rendered_profile_links_to_diagnostics_route(profile_auth_client) -> None:
    app = profile_auth_client["app"]
    template_source = PROFILE_TEMPLATE.read_text(encoding="utf-8")
    env = Environment(
        loader=DictLoader({
            "security/_layout.html": "{% block content %}{% endblock %}",
            "security/_macros.html": (
                "{% macro render_field_with_errors() %}{% endmacro %}"
                "{% macro render_checkbox_with_errors() %}{% endmacro %}"
                "{% macro render_field() %}{% endmacro %}"
            ),
            "user/profile.html": template_source,
        })
    )
    user = SimpleNamespace(
        oauth_accounts=SimpleNamespace(all=lambda: []),
        first_name="Test",
        last_name="User",
        email="user@example.com",
        roles=[],
        has_role=lambda _role: False,
    )
    with app.test_request_context():
        env.globals.update(
            url_for=lambda endpoint, **values: (
                "/change"
                if endpoint == "security.change_password"
                else "/preferences"
                if endpoint == "user.preferences"
                else app.jinja_env.globals["url_for"](endpoint, **values)
            ),
            user=user,
            oauth_providers={},
            can_mint_profile_token=False,
        )
        rendered = env.get_template("user/profile.html").render()

    assert 'href="/weppcloud/diagnostics/"' in rendered


def test_profile_token_mint_requires_login(profile_auth_client) -> None:
    client = profile_auth_client["client"]

    response = client.post("/profile/mint-token")

    assert response.status_code == 401


def test_profile_token_mint_enforces_csrf_before_role_gate(
    profile_auth_client,
) -> None:
    app = profile_auth_client["app"]
    client = profile_auth_client["client"]
    user_id = profile_auth_client["user_id"]

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return {"error": error.description}, 400

    CSRFProtect(app)

    @app.get("/test-csrf")
    def test_csrf() -> str:
        return generate_csrf()

    client.get(f"/test-login/{user_id}")
    missing_csrf = client.post("/profile/mint-token")
    assert missing_csrf.status_code == 400

    csrf_token = client.get("/test-csrf").get_data(as_text=True)
    valid_csrf = client.post(
        "/profile/mint-token",
        headers={"X-CSRFToken": csrf_token},
    )
    assert valid_csrf.status_code == 403
    assert "requires one of these roles" in valid_csrf.get_json()["error"]["message"]


def test_run_token_mint_requires_login(profile_auth_client) -> None:
    client = profile_auth_client["client"]

    response = client.post("/runs/run-1/cfg/mint-run-token")

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


def test_run_token_mint_requires_admin_role(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]

    _configure_jwt_env(monkeypatch, module)
    monkeypatch.setattr(module, "authorize", lambda runid, config: None)
    client.get(f"/test-login/{user_id}")

    response = client.post("/runs/run-1/cfg/mint-run-token")

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Minting run-scoped tokens requires Admin or Root role."


def test_run_token_mint_preserves_authorize_forbidden(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]

    _configure_jwt_env(monkeypatch, module)
    _grant_role(profile_auth_client, "Admin")
    def _forbidden_authorize(runid: str, config: str) -> None:
        raise Forbidden()

    monkeypatch.setattr(module, "authorize", _forbidden_authorize)
    client.get(f"/test-login/{user_id}")

    with pytest.raises(Forbidden):
        client.post("/runs/run-1/cfg/mint-run-token")


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


def test_run_token_mint_issues_24_hour_service_token(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    authorize_calls: list[tuple[str, str]] = []

    _configure_jwt_env(monkeypatch, module)
    _grant_role(profile_auth_client, "Admin")
    monkeypatch.setattr(module, "authorize", lambda runid, config: authorize_calls.append((runid, config)))
    client.get(f"/test-login/{user_id}")

    response = client.post("/runs/run-1/cfg/mint-run-token")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert authorize_calls == [("run-1", "cfg")]

    payload = response.get_json()
    content = payload["Content"]
    token = content["token"]
    claims = module.auth_tokens.decode_token(token, audience="rq-engine")

    assert content["runid"] == "run-1"
    assert content["config"] == "cfg"
    assert content["token_class"] == "service"
    assert content["expires_in"] == 24 * 60 * 60
    assert content["audience"] == ["rq-engine", "query-engine"]
    assert content["runs"] == ["run-1"]
    assert content["scopes"] == [
        "runs:read",
        "queries:validate",
        "queries:execute",
        "rq:status",
        "rq:enqueue",
        "rq:export",
        "bootstrap:enable",
        "bootstrap:token:mint",
        "bootstrap:read",
        "bootstrap:checkout",
    ]

    assert claims["token_class"] == "service"
    assert claims["sub"] == f"admin-run-token:{user_id}"
    assert claims["email"] == "user@example.com"
    assert claims["runs"] == ["run-1"]
    assert claims["service_groups"] == ["admin-run-token"]
    assert set(claims["roles"]) == {"Admin", "User"}
    assert claims["groups"] == []
    assert claims["exp"] - claims["iat"] == 24 * 60 * 60


def test_run_token_mint_allows_lowercase_admin_role(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]
    authorize_calls: list[tuple[str, str]] = []

    _configure_jwt_env(monkeypatch, module)
    _grant_role(profile_auth_client, "admin")
    monkeypatch.setattr(module, "authorize", lambda runid, config: authorize_calls.append((runid, config)))
    client.get(f"/test-login/{user_id}")

    response = client.post("/runs/run-1/cfg/mint-run-token")

    assert response.status_code == 200
    assert authorize_calls == [("run-1", "cfg")]
    payload = response.get_json()
    content = payload["Content"]
    claims = module.auth_tokens.decode_token(content["token"], audience="rq-engine")
    assert set(claims["roles"]) == {"admin", "User"}


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


def test_run_token_mint_errors_without_jwt_secret(
    profile_auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = profile_auth_client["client"]
    module = profile_auth_client["module"]
    user_id = profile_auth_client["user_id"]

    monkeypatch.delenv("WEPP_AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    _grant_role(profile_auth_client, "Admin")
    monkeypatch.setattr(module, "authorize", lambda runid, config: None)
    module.auth_tokens.get_jwt_config.cache_clear()
    client.get(f"/test-login/{user_id}")

    response = client.post("/runs/run-1/cfg/mint-run-token")

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
    assert "reset_browser_state_endpoint" not in captured_context
    assert "reset_browser_state_login_url" not in captured_context


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
    assert "reset_browser_state_endpoint" not in captured_context
    assert "reset_browser_state_login_url" not in captured_context


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
