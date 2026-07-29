from __future__ import annotations

import importlib
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, jsonify
from flask_security import RoleMixin, SQLAlchemyUserDatastore, Security, UserMixin
from flask_security.utils import hash_password, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf
from jinja2 import DictLoader

pytestmark = pytest.mark.routes

REPO_ROOT = Path(__file__).resolve().parents[3]
USERMOD_TEMPLATE = (
    REPO_ROOT / "wepppy" / "weppcloud" / "templates" / "user" / "usermod.html"
)


@pytest.fixture()
def usermod_client(monkeypatch: pytest.MonkeyPatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="usermod-secret",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECURITY_PASSWORD_SALT="usermod-salt",
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
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(80), unique=True)
        description = db.Column(db.String(255))

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(255), unique=True)
        first_name = db.Column(db.String(255))
        last_name = db.Column(db.String(255))
        password = db.Column(db.String(255))
        active = db.Column(db.Boolean(), default=True)
        fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
        last_login_at = db.Column(db.DateTime())
        login_count = db.Column(db.Integer)
        roles = db.relationship(
            "Role",
            secondary=roles_users,
            backref=db.backref("users", lazy="dynamic"),
        )

    datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, datastore)

    @app.login_manager.unauthorized_handler
    def unauthorized():
        return "Unauthorized", 401

    @app.errorhandler(403)
    def forbidden(_error):
        return jsonify({"error": {"message": "forbidden"}}), 403

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return jsonify({"error": {"message": error.description}}), 400

    @app.get("/test-login/<int:user_id>")
    def test_login(user_id: int):
        logout_user()
        user = db.session.get(User, user_id)
        login_user(user)
        db.session.commit()
        return "ok"

    @app.get("/test-csrf")
    def test_csrf():
        return generate_csrf()

    with app.app_context():
        db.create_all()
        user_role = datastore.create_role(name="User")
        root_role = datastore.create_role(name="Root")
        admin_role = datastore.create_role(name="Admin")
        power_role = datastore.create_role(name="PowerUser")
        root = datastore.create_user(
            email="root@example.test",
            first_name="Root",
            last_name="Operator",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[user_role, root_role],
            last_login_at=datetime(2026, 7, 28, 12, 30),
            login_count=5,
        )
        admin = datastore.create_user(
            email="admin@example.test",
            first_name="Admin",
            last_name="Viewer",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[user_role, admin_role],
        )
        target = datastore.create_user(
            email='target<script>alert("x")</script>@example.test',
            first_name="<b>Target</b>",
            last_name=None,
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[user_role, power_role],
        )
        datastore.commit()
        ids = {"root": root.id, "admin": admin.id, "target": target.id}

    admin_module = importlib.reload(
        importlib.import_module("wepppy.weppcloud.routes.admin")
    )
    app_module = importlib.import_module("wepppy.weppcloud.app")
    monkeypatch.setattr(app_module, "db", db)
    monkeypatch.setattr(app_module, "User", User)
    monkeypatch.setattr(app_module, "Role", Role)
    monkeypatch.setattr(app_module, "user_datastore", datastore)

    app.jinja_loader = DictLoader(
        {
            "base_pure.htm": "{% block body %}{% endblock %}",
            "user/usermod.html": USERMOD_TEMPLATE.read_text(encoding="utf-8"),
        }
    )

    @app.context_processor
    def usermod_context():
        return {
            "get_all_users": lambda: User.query.order_by(User.last_login_at).all()
        }

    app.register_blueprint(admin_module.admin_bp)
    CSRFProtect(app)

    with app.test_client() as client:
        yield {
            "app": app,
            "client": client,
            "db": db,
            "datastore": datastore,
            "User": User,
            "ids": ids,
        }


def _login(usermod_client, identity: str) -> None:
    response = usermod_client["client"].get(
        f"/test-login/{usermod_client['ids'][identity]}"
    )
    assert response.status_code == 200


def _csrf(usermod_client) -> str:
    token = usermod_client["client"].get("/test-csrf").get_data(as_text=True)
    assert token
    return token


def _post(usermod_client, payload: object, *, csrf: bool = True):
    headers = {}
    if csrf:
        headers["X-CSRFToken"] = _csrf(usermod_client)
    return usermod_client["client"].post(
        "/tasks/usermod/",
        json=payload,
        headers=headers,
    )


def test_usermod_get_is_root_only_and_renders_contract(usermod_client) -> None:
    client = usermod_client["client"]
    _login(usermod_client, "admin")
    assert client.get("/usermod").status_code == 403

    _login(usermod_client, "root")
    response = client.get("/usermod")
    assert response.status_code == 200
    rendered = response.get_data(as_text=True)

    target_id = usermod_client["ids"]["target"]
    root_id = usermod_client["ids"]["root"]
    assert "<script>alert" not in rendered
    assert "&lt;script&gt;alert" in rendered
    assert "&lt;b&gt;Target&lt;/b&gt;" in rendered
    assert "2026-07-28 12:30" in rendered
    assert f'name="usermod_PowerUser_{target_id}"' in rendered
    assert f'name="usermod_Root_{root_id}"' in rendered
    root_control = rendered.split(f'name="usermod_Root_{root_id}"', 1)[1].split(
        ">", 1
    )[0]
    assert "checked" in root_control
    assert "disabled" in root_control
    assert 'data-usermod-status' in rendered
    assert 'aria-live="polite"' in rendered


def test_usermod_context_producer_returns_all_users(
    usermod_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    context_module = importlib.import_module("wepppy.weppcloud._context_processors")
    monkeypatch.setattr(context_module, "UserModel", usermod_client["User"])
    with usermod_client["app"].app_context():
        users = context_module._get_all_users()
    assert {user.id for user in users} == set(usermod_client["ids"].values())


def test_usermod_template_renders_empty_inventory(usermod_client) -> None:
    app = usermod_client["app"]
    root = SimpleNamespace(has_role=lambda role: role == "Root")
    with app.test_request_context("/usermod"):
        rendered = app.jinja_env.get_template("user/usermod.html").render(
            user=root,
            get_all_users=lambda: [],
        )
    assert "No users found." in rendered


def test_usermod_post_requires_root_and_csrf_before_role_gate(usermod_client) -> None:
    _login(usermod_client, "admin")
    payload = {
        "user_id": usermod_client["ids"]["target"],
        "role": "Dev",
        "role_state": True,
    }
    assert _post(usermod_client, payload, csrf=False).status_code == 400
    assert _post(usermod_client, payload).status_code == 403


@pytest.mark.parametrize(
    "payload, message",
    [
        (None, "JSON object required"),
        ([], "JSON object required"),
        ({"user_id": 1, "role": "Dev"}, "role_state must be a boolean"),
        (
            {"user_id": 1, "role": "Dev", "role_state": "false"},
            "role_state must be a boolean",
        ),
        (
            {"user_id": "1", "role": "Dev", "role_state": True},
            "user_id must be an integer",
        ),
        (
            {"user_id": 1, "role": "Owner", "role_state": True},
            "unsupported role",
        ),
        (
            {"role": "Dev", "role_state": True},
            "user_id or user_email required",
        ),
    ],
)
def test_usermod_rejects_invalid_payloads(
    usermod_client, payload: object, message: str
) -> None:
    _login(usermod_client, "root")
    response = _post(usermod_client, payload)
    assert response.status_code == 400
    assert message in response.get_json()["error"]["message"]


def test_usermod_prevents_acting_root_from_removing_root(usermod_client) -> None:
    _login(usermod_client, "root")
    response = _post(
        usermod_client,
        {
            "user_id": usermod_client["ids"]["root"],
            "role": "Root",
            "role_state": False,
        },
    )
    assert response.status_code == 400
    assert "own Root role" in response.get_json()["error"]["message"]

    with usermod_client["app"].app_context():
        root = usermod_client["db"].session.get(
            usermod_client["User"], usermod_client["ids"]["root"]
        )
        assert root.has_role("Root")


def test_usermod_grant_revoke_persists_and_rerenders(usermod_client) -> None:
    _login(usermod_client, "root")
    target_id = usermod_client["ids"]["target"]

    granted = _post(
        usermod_client,
        {"user_id": target_id, "role": "Dev", "role_state": True},
    )
    assert granted.status_code == 200
    assert granted.get_json() == {}
    rendered = usermod_client["client"].get("/usermod").get_data(as_text=True)
    dev_control = rendered.split(f'name="usermod_Dev_{target_id}"', 1)[1].split(
        ">", 1
    )[0]
    assert "checked" in dev_control

    revoked = _post(
        usermod_client,
        {"user_id": target_id, "role": "PowerUser", "role_state": False},
    )
    assert revoked.status_code == 200
    rendered = usermod_client["client"].get("/usermod").get_data(as_text=True)
    power_control = rendered.split(
        f'name="usermod_PowerUser_{target_id}"', 1
    )[1].split(">", 1)[0]
    assert "checked" not in power_control

    redundant = _post(
        usermod_client,
        {"user_id": target_id, "role": "PowerUser", "role_state": False},
    )
    assert redundant.status_code == 400
    assert "already is False" in redundant.get_json()["error"]["message"]
