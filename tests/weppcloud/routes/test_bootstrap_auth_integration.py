from __future__ import annotations

import importlib
import uuid

import pytest

pytest.importorskip("flask")
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_security import RoleMixin, SQLAlchemyUserDatastore, Security, UserMixin
from flask_security.utils import hash_password, login_user

pytestmark = pytest.mark.routes

RUN_ID = "ab-run"
CONFIG = "cfg"


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
    def __init__(self, run):
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


class DummyRun:
    def __init__(self, runid: str) -> None:
        self.runid = runid
        self.bootstrap_disabled = False


class DummyWepp:
    def __init__(self) -> None:
        self.bootstrap_enabled = False
        self.init_calls = 0

    def init_bootstrap(self) -> None:
        self.init_calls += 1
        self.bootstrap_enabled = True


@pytest.fixture()
def auth_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test-secret",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECURITY_PASSWORD_SALT="test-salt",
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
        admin_role = user_datastore.create_role(name="Admin")
        root_role = user_datastore.create_role(name="Root")
        user = user_datastore.create_user(
            email="user@example.com",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
        )
        admin = user_datastore.create_user(
            email="admin@example.com",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[admin_role],
        )
        root = user_datastore.create_user(
            email="root@example.com",
            password=hash_password("password"),
            fs_uniquifier=uuid.uuid4().hex,
            roles=[root_role],
        )
        user_datastore.commit()
        user_id = user.id
        admin_id = admin.id
        root_id = root.id

    bootstrap_module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes.bootstrap"))
    app.register_blueprint(bootstrap_module.bootstrap_bp)

    def _fake_validate(runid: str, email: str):
        from flask_security import current_user

        return object(), current_user

    monkeypatch.setattr(bootstrap_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(bootstrap_module, "_validate_bootstrap_eligibility", _fake_validate)
    monkeypatch.setattr(bootstrap_module, "_ensure_bootstrap_opt_in", lambda runid: None)
    monkeypatch.setattr(bootstrap_module, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(bootstrap_module.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(
        bootstrap_module,
        "enqueue_bootstrap_enable",
        lambda runid, actor: (
            {"enabled": False, "queued": True, "job_id": "job-auth", "message": "Bootstrap enable job enqueued."},
            202,
        ),
    )

    dummy_run = DummyRun(RUN_ID)

    class DummyRunModel:
        runid = ComparableAttribute("runid")
        query = DummyQuery(dummy_run)

    app_module = importlib.import_module("wepppy.weppcloud.app")
    monkeypatch.setattr(app_module, "Run", DummyRunModel)
    monkeypatch.setattr(app_module, "db", DummyDB())

    with app.test_client() as client:
        yield {
            "client": client,
            "user_id": user_id,
            "admin_id": admin_id,
            "root_id": root_id,
            "dummy_run": dummy_run,
        }


def test_login_required_blocks_unauthenticated(auth_client) -> None:
    client = auth_client["client"]
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/enable")
    assert response.status_code == 401


def test_login_required_allows_authenticated(auth_client) -> None:
    client = auth_client["client"]
    user_id = auth_client["user_id"]

    client.get(f"/test-login/{user_id}")
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/enable")

    assert response.status_code == 202
    assert response.get_json() == {
        "Content": {
            "enabled": False,
            "queued": True,
            "job_id": "job-auth",
            "message": "Bootstrap enable job enqueued.",
            "status_url": "/rq-engine/api/jobstatus/job-auth",
        }
    }


def test_roles_accepted_blocks_non_admin(auth_client) -> None:
    client = auth_client["client"]
    user_id = auth_client["user_id"]

    client.get(f"/test-login/{user_id}")
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/disable", json={"disabled": True})

    assert response.status_code == 403


def test_roles_accepted_allows_admin(auth_client) -> None:
    client = auth_client["client"]
    admin_id = auth_client["admin_id"]
    dummy_run = auth_client["dummy_run"]

    client.get(f"/test-login/{admin_id}")
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/disable", json={"disabled": True})

    assert response.status_code == 200
    assert response.get_json() == {"Content": {"bootstrap_disabled": True}}
    assert dummy_run.bootstrap_disabled is True


def test_roles_accepted_allows_root(auth_client) -> None:
    client = auth_client["client"]
    root_id = auth_client["root_id"]
    dummy_run = auth_client["dummy_run"]

    client.get(f"/test-login/{root_id}")
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/bootstrap/disable", json={"disabled": True})

    assert response.status_code == 200
    assert response.get_json() == {"Content": {"bootstrap_disabled": True}}
    assert dummy_run.bootstrap_disabled is True
