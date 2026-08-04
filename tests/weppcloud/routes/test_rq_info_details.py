from __future__ import annotations

from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
import uuid

import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_security")
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_security import RoleMixin, SQLAlchemyUserDatastore, Security, UserMixin
from flask_security.utils import login_user

rq_info_details_module = import_module("wepppy.weppcloud.routes.rq.info_details.routes")

pytestmark = pytest.mark.routes

REPO_ROOT = Path(__file__).resolve().parents[3]
INFO_DETAILS_TEMPLATE = (
    REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "rq" / "info_details" / "templates" / "info_details.htm"
)


def test_filter_failed_jobs_keeps_only_failed_entries() -> None:
    jobs = [
        {"job_id": "failed-status", "status": "failed", "registry": "finished"},
        {"job_id": "failed-registry", "status": "finished", "registry": "failed"},
        {"job_id": "uppercase-status", "status": "FAILED", "registry": "finished"},
        {"job_id": "finished", "status": "finished", "registry": "finished"},
        {"job_id": "stopped", "status": "stopped", "registry": "finished"},
    ]

    filtered = rq_info_details_module._filter_failed_jobs(jobs)

    assert [job["job_id"] for job in filtered] == [
        "failed-status",
        "failed-registry",
        "uppercase-status",
    ]


def test_template_includes_failed_jobs_panel() -> None:
    source = INFO_DETAILS_TEMPLATE.read_text(encoding="utf-8")

    assert "<h2>Failed Jobs (Last 24 Hours)</h2>" in source
    assert "{% if failed_jobs %}" in source
    assert "last {{ failed_lookback_seconds // 3600 }} hours" in source


def test_rq_info_details_route_wires_failed_jobs_context(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    completed_jobs = [
        {
            "job_id": "failed-recent",
            "status": "failed",
            "registry": "failed",
            "ended_at": (now - timedelta(hours=1)).isoformat(),
        },
        {
            "job_id": "finished-recent",
            "status": "finished",
            "registry": "finished",
            "ended_at": (now - timedelta(minutes=30)).isoformat(),
        },
        {
            "job_id": "failed-old",
            "status": "failed",
            "registry": "failed",
            "ended_at": (now - timedelta(hours=23)).isoformat(),
        },
        {
            "job_id": "finished-outside-recent",
            "status": "finished",
            "registry": "finished",
            "ended_at": (now - timedelta(hours=3)).isoformat(),
        },
    ]
    lookback_calls: list[int] = []
    captured_context: dict[str, object] = {}

    class _DummyRedis:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> object:
            return object()

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    def _fake_recently_completed(
        _redis_conn: object,
        *,
        queue_names: tuple[str, ...],
        lookback_seconds: int,
    ) -> list[dict[str, str]]:
        assert queue_names == ("default", "batch", "fork-archive")
        lookback_calls.append(lookback_seconds)
        return completed_jobs

    def _fake_render_template(_template_name: str, **context: object) -> str:
        captured_context.update(context)
        return "ok"

    app = Flask(__name__)

    monkeypatch.setattr(rq_info_details_module, "redis_connection_kwargs", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(rq_info_details_module.redis, "Redis", _DummyRedis)
    monkeypatch.setattr(rq_info_details_module, "list_recently_completed_jobs", _fake_recently_completed)
    monkeypatch.setattr(rq_info_details_module, "list_active_jobs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(rq_info_details_module, "render_template", _fake_render_template)
    monkeypatch.setattr(rq_info_details_module, "url_for_run", lambda endpoint, **_kwargs: f"/{endpoint}")

    with app.test_request_context("/rq/info-details"):
        response = rq_info_details_module.rq_info_details.__wrapped__.__wrapped__()

    assert response == "ok"
    assert lookback_calls == [rq_info_details_module.FAILED_JOBS_LOOKBACK_SECONDS]
    assert captured_context["failed_lookback_seconds"] == rq_info_details_module.FAILED_JOBS_LOOKBACK_SECONDS
    assert [job["job_id"] for job in captured_context["failed_jobs"]] == ["failed-recent", "failed-old"]
    assert [job["job_id"] for job in captured_context["recent_jobs"]] == ["failed-recent", "finished-recent"]


def test_group_active_jobs_by_queue_preserves_order_and_isolates_exact_names() -> None:
    jobs = [
        {"job_id": "default", "queue": " default "},
        {"job_id": "batch", "queue": "batch"},
        {"job_id": "case-different", "queue": "BATCH"},
        {"job_id": "unknown", "queue": "other"},
        {"job_id": "missing"},
    ]

    groups = rq_info_details_module._group_active_jobs_by_queue(
        (" batch ", "default", "batch"),
        jobs,
    )

    assert [group["name"] for group in groups] == ["batch", "default"]
    assert [[job["job_id"] for job in group["jobs"]] for group in groups] == [
        ["batch"],
        ["default"],
    ]


def test_rq_info_details_route_wires_ordered_active_queue_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_context: dict[str, object] = {}
    active_jobs = [
        {"job_id": "batch-job", "queue": "batch"},
        {"job_id": "default-job", "queue": "default"},
        {"job_id": "unrequested-job", "queue": "other"},
    ]

    class _DummyRedis:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> object:
            return object()

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    monkeypatch.setattr(rq_info_details_module, "redis_connection_kwargs", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(rq_info_details_module.redis, "Redis", _DummyRedis)
    monkeypatch.setattr(rq_info_details_module, "list_recently_completed_jobs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(rq_info_details_module, "list_active_jobs", lambda *_args, **_kwargs: active_jobs)
    monkeypatch.setattr(
        rq_info_details_module,
        "render_template",
        lambda _template_name, **context: captured_context.update(context) or "ok",
    )
    monkeypatch.setattr(rq_info_details_module, "url_for_run", lambda endpoint, **_kwargs: f"/{endpoint}")
    monkeypatch.setattr(rq_info_details_module, "_hydrate_submitter", lambda *_args, **_kwargs: None)

    app = Flask(__name__)
    with app.test_request_context("/rq/info-details?queues=batch,default,batch"):
        response = rq_info_details_module.rq_info_details.__wrapped__.__wrapped__()

    assert response == "ok"
    groups = captured_context["active_job_groups"]
    assert [group["name"] for group in groups] == ["batch", "default"]
    assert [[job["job_id"] for job in group["jobs"]] for group in groups] == [
        ["batch-job"],
        ["default-job"],
    ]


def test_rq_info_details_route_returns_explicit_error_on_listing_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logged: list[str] = []
    class _FailingRedis:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> object:
            raise RuntimeError("redis unavailable")

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    monkeypatch.setattr(rq_info_details_module, "redis_connection_kwargs", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(rq_info_details_module.redis, "Redis", _FailingRedis)
    monkeypatch.setattr(
        rq_info_details_module,
        "exception_factory",
        lambda message: (message, 500),
    )

    app = Flask(__name__)
    monkeypatch.setattr(
        app.logger,
        "exception",
        lambda message, *_args, **_kwargs: logged.append(message),
    )
    with app.test_request_context("/rq/info-details"):
        response = rq_info_details_module.rq_info_details.__wrapped__.__wrapped__()

    assert response == ("Failed to load RQ info details", 500)
    assert logged == ["Failed to load RQ info details page"]


@pytest.fixture()
def rq_info_auth_client(monkeypatch: pytest.MonkeyPatch):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test-secret",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECURITY_PASSWORD_SALT="test-salt",
        SECURITY_PASSWORD_HASH="plaintext",
        SECURITY_REGISTERABLE=False,
        SECURITY_SEND_REGISTER_EMAIL=False,
        SECURITY_TRACKABLE=False,
        SECURITY_UNAUTHORIZED_VIEW=None,
        PROPAGATE_EXCEPTIONS=False,
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
        id = db.Column(db.Integer(), primary_key=True)
        email = db.Column(db.String(255), unique=True)
        password = db.Column(db.String(255))
        active = db.Column(db.Boolean(), default=True)
        fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
        roles = db.relationship("Role", secondary=roles_users)

    datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, datastore)

    @app.login_manager.unauthorized_handler
    def unauthorized():
        return "Unauthorized", 401

    @app.errorhandler(403)
    def forbidden(_error):
        return "Forbidden", 403

    @app.get("/test-login/<int:user_id>")
    def test_login(user_id: int):
        login_user(db.session.get(User, user_id))
        return "ok"

    with app.app_context():
        db.create_all()
        admin_role = datastore.create_role(name="Admin")
        root_role = datastore.create_role(name="Root")
        users = {
            "user": datastore.create_user(
                email="user@example.com",
                password="password",
                fs_uniquifier=uuid.uuid4().hex,
            ),
            "admin": datastore.create_user(
                email="admin@example.com",
                password="password",
                fs_uniquifier=uuid.uuid4().hex,
                roles=[admin_role],
            ),
            "root": datastore.create_user(
                email="root@example.com",
                password="password",
                fs_uniquifier=uuid.uuid4().hex,
                roles=[root_role],
            ),
        }
        datastore.commit()
        user_ids = {key: value.id for key, value in users.items()}

    class _DummyRedis:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> object:
            return object()

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    monkeypatch.setattr(rq_info_details_module, "redis_connection_kwargs", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(rq_info_details_module.redis, "Redis", _DummyRedis)
    monkeypatch.setattr(rq_info_details_module, "list_recently_completed_jobs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(rq_info_details_module, "list_active_jobs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(rq_info_details_module, "render_template", lambda *_args, **_kwargs: "ok")
    monkeypatch.setattr(rq_info_details_module, "url_for_run", lambda endpoint, **_kwargs: f"/{endpoint}")
    app.register_blueprint(rq_info_details_module.rq_info_details_bp)

    with app.test_client() as client:
        yield client, user_ids


def test_rq_info_details_requires_login(rq_info_auth_client) -> None:
    client, _user_ids = rq_info_auth_client
    assert client.get("/rq/info-details").status_code == 401


@pytest.mark.parametrize(
    ("role_name", "expected_status"),
    [("user", 403), ("admin", 200), ("root", 200)],
)
def test_rq_info_details_requires_admin_or_root(
    rq_info_auth_client,
    role_name: str,
    expected_status: int,
) -> None:
    client, user_ids = rq_info_auth_client
    client.get(f"/test-login/{user_ids[role_name]}")
    assert client.get("/rq/info-details").status_code == expected_status
