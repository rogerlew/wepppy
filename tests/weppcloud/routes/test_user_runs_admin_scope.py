from __future__ import annotations

import importlib
import logging
import types
import uuid
from datetime import datetime, timedelta

import pytest

pytest.importorskip("flask")
from flask import Flask
from flask_security import RoleMixin, SQLAlchemyUserDatastore, Security, UserMixin
from flask_security.utils import hash_password, login_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import Forbidden

pytestmark = pytest.mark.routes


@pytest.fixture()
def runs_scope_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="runs-scope-secret",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECURITY_PASSWORD_SALT="runs-scope-salt",
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

    runs_users = db.Table(
        "runs_users",
        db.Column("user_id", db.Integer(), db.ForeignKey("user.id"), primary_key=True),
        db.Column("run_id", db.Integer(), db.ForeignKey("run.id"), primary_key=True),
    )

    class Role(db.Model, RoleMixin):
        id = db.Column(db.Integer(), primary_key=True)
        name = db.Column(db.String(80), unique=True)

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(255), unique=True)
        first_name = db.Column(db.String(255))
        last_name = db.Column(db.String(255))
        password = db.Column(db.String(255))
        active = db.Column(db.Boolean(), default=True)
        fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
        roles = db.relationship("Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic"))

    class Run(db.Model):
        id = db.Column(db.Integer(), primary_key=True)
        runid = db.Column(db.String(255), unique=True)
        date_created = db.Column(db.DateTime())
        owner_id = db.Column(db.String(255))
        config = db.Column(db.String(255))
        last_modified = db.Column(db.DateTime(), nullable=True)

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
        admin_role = user_datastore.create_role(name="Admin")

        owner = user_datastore.create_user(
            email="owner@example.com",
            first_name="Owner",
            last_name="User",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[user_role],
        )
        other = user_datastore.create_user(
            email="other@example.com",
            first_name="Other",
            last_name="Person",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[user_role],
        )
        admin = user_datastore.create_user(
            email="admin@example.com",
            first_name="Admin",
            last_name="Viewer",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[admin_role],
        )
        user_datastore.commit()

        now = datetime.utcnow()
        owner_run = Run(
            runid="owner-run",
            config="cfg",
            owner_id=str(owner.id),
            date_created=now - timedelta(days=2),
            last_modified=now - timedelta(days=1),
        )
        other_run = Run(
            runid="other-run",
            config="cfg",
            owner_id=str(other.id),
            date_created=now - timedelta(days=3),
            last_modified=now,
        )
        admin_run = Run(
            runid="admin-run",
            config="cfg",
            owner_id=str(admin.id),
            date_created=now - timedelta(days=4),
            last_modified=now - timedelta(hours=2),
        )
        db.session.add_all([owner_run, other_run, admin_run])
        db.session.flush()
        db.session.execute(runs_users.insert().values(user_id=owner.id, run_id=owner_run.id))
        db.session.execute(runs_users.insert().values(user_id=other.id, run_id=other_run.id))
        db.session.execute(runs_users.insert().values(user_id=admin.id, run_id=admin_run.id))
        db.session.commit()

        owner_id = owner.id
        other_id = other.id
        admin_id = admin.id

    user_module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes.user"))

    app_module = importlib.import_module("wepppy.weppcloud.app")
    monkeypatch.setattr(app_module, "db", db, raising=False)
    monkeypatch.setattr(app_module, "User", User, raising=False)
    monkeypatch.setattr(app_module, "Run", Run, raising=False)
    monkeypatch.setattr(app_module, "runs_users", runs_users, raising=False)

    class DummyRon:
        def __init__(self, runid: str) -> None:
            self.name = f"Project {runid}"
            self.scenario = f"Scenario {runid}"
            self.readonly = False
            self.map = types.SimpleNamespace(center=[-115.0, 44.0], zoom=10)

        @classmethod
        def load_detached(cls, wd: str):
            runid = wd.rstrip("/").split("/")[-1]
            return cls(runid)

    monkeypatch.setattr(user_module, "Ron", DummyRon)
    monkeypatch.setattr(user_module, "get_wd", lambda runid: str(tmp_path / runid))

    app.register_blueprint(user_module.user_bp)

    with app.test_client() as client:
        yield {
            "client": client,
            "owner_id": owner_id,
            "other_id": other_id,
            "admin_id": admin_id,
            "module": user_module,
        }


def _login(client, user_id: int) -> None:
    response = client.get(f"/test-login/{user_id}")
    assert response.status_code == 200


def test_runs_users_requires_admin_role(runs_scope_client) -> None:
    client = runs_scope_client["client"]
    _login(client, runs_scope_client["owner_id"])

    with pytest.raises(Forbidden):
        client.get("/runs/users")


def test_runs_users_returns_user_table_for_admin(runs_scope_client) -> None:
    client = runs_scope_client["client"]
    _login(client, runs_scope_client["admin_id"])

    response = client.get("/runs/users")

    assert response.status_code == 200
    payload = response.get_json()
    users = payload["users"]
    assert payload["total"] == 3
    assert any(user["email"] == "owner@example.com" and user["name"] == "Owner User" for user in users)
    owner_entry = next(user for user in users if user["email"] == "owner@example.com")
    assert owner_entry["alias"] == str(runs_scope_client["owner_id"])
    assert "owner@example.com" in owner_entry["search_index"]


def test_runs_catalog_ignores_alias_for_non_admin(runs_scope_client) -> None:
    client = runs_scope_client["client"]
    _login(client, runs_scope_client["owner_id"])

    response = client.get(f"/runs/catalog?alias={runs_scope_client['other_id']}")

    assert response.status_code == 200
    payload = response.get_json()
    runids = {run["runid"] for run in payload["runs"]}
    assert runids == {"owner-run"}


def test_runs_catalog_applies_alias_for_admin(runs_scope_client) -> None:
    client = runs_scope_client["client"]
    _login(client, runs_scope_client["admin_id"])

    response = client.get(f"/runs/catalog?alias={runs_scope_client['other_id']}")

    assert response.status_code == 200
    payload = response.get_json()
    runids = {run["runid"] for run in payload["runs"]}
    assert runids == {"other-run"}


def test_runs_map_data_applies_alias_for_admin(runs_scope_client) -> None:
    client = runs_scope_client["client"]
    _login(client, runs_scope_client["admin_id"])

    response = client.get(f"/runs/map-data?alias={runs_scope_client['other_id']}")

    assert response.status_code == 200
    payload = response.get_json()
    runids = {run["runid"] for run in payload["runs"]}
    assert runids == {"other-run"}


def test_runs_catalog_skips_missing_run_metadata_and_logs_boundary(
    runs_scope_client,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = runs_scope_client["client"]
    module = runs_scope_client["module"]
    _login(client, runs_scope_client["admin_id"])

    class _MissingRon:
        @classmethod
        def load_detached(cls, _wd: str):
            raise FileNotFoundError("ron.nodb missing")

    monkeypatch.setattr(module, "Ron", _MissingRon)
    caplog.set_level(logging.INFO, logger=module.logger.name)

    response = client.get(f"/runs/catalog?alias={runs_scope_client['other_id']}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["runs"] == []
    assert "ron.nodb missing" in caplog.text


def test_runs_map_data_skips_missing_run_metadata_and_logs_boundary(
    runs_scope_client,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = runs_scope_client["client"]
    module = runs_scope_client["module"]
    _login(client, runs_scope_client["admin_id"])

    class _MissingRon:
        @classmethod
        def load_detached(cls, _wd: str):
            raise FileNotFoundError("ron.nodb missing")

    monkeypatch.setattr(module, "Ron", _MissingRon)
    caplog.set_level(logging.INFO, logger=module.logger.name)

    response = client.get(f"/runs/map-data?alias={runs_scope_client['other_id']}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["runs"] == []
    assert "ron.nodb missing" in caplog.text


def test_runs_catalog_skips_run_metadata_load_errors_and_logs_warning_boundary(
    runs_scope_client,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = runs_scope_client["client"]
    module = runs_scope_client["module"]
    _login(client, runs_scope_client["admin_id"])

    class _ExplodingRon:
        @classmethod
        def load_detached(cls, _wd: str):
            raise RuntimeError("boom")

    monkeypatch.setattr(module, "Ron", _ExplodingRon)
    caplog.set_level(logging.WARNING, logger=module.logger.name)

    response = client.get(f"/runs/catalog?alias={runs_scope_client['other_id']}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["runs"] == []
    assert "failed to load Ron" in caplog.text


def test_runs_map_data_skips_run_metadata_load_errors_and_logs_warning_boundary(
    runs_scope_client,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = runs_scope_client["client"]
    module = runs_scope_client["module"]
    _login(client, runs_scope_client["admin_id"])

    class _ExplodingRon:
        @classmethod
        def load_detached(cls, _wd: str):
            raise RuntimeError("boom")

    monkeypatch.setattr(module, "Ron", _ExplodingRon)
    caplog.set_level(logging.WARNING, logger=module.logger.name)

    response = client.get(f"/runs/map-data?alias={runs_scope_client['other_id']}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["runs"] == []
    assert "failed to load Ron" in caplog.text
