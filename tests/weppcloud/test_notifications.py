"""Real PostgreSQL and TTL boundary coverage for the private inbox."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from wepppy.weppcloud.configuration import _build_postgres_uri
from wepppy.weppcloud.notifications import repository as repo
from wepppy.weppcloud.notifications import producer
from wepppy.weppcloud.notifications.producer import reconcile_ttl_notifications
from wepppy.weppcloud.notifications.schema import users, runs, memberships, notifications as n, recipients as r
from wepppy.weppcloud.run_catalog.paths import Roots

pytestmark = pytest.mark.integration
NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
POSTGRES_URI = _build_postgres_uri()
MIGRATION = "wepppy.weppcloud.migrations.versions.f6b8d27a901c_add_notifications"


@pytest.fixture
def database(monkeypatch):
    schema = "notifications_test_" + uuid4().hex
    # Schemas do not isolate advisory locks. Never contend with a live sweep.
    monkeypatch.setattr(producer, "SWEEP_LOCK", uuid4().int % (2**63 - 1))
    url = POSTGRES_URI
    admin = sa.create_engine(url, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    engine = sa.create_engine(url, hide_parameters=True, connect_args={"options": "-csearch_path=" + schema})
    try:
        for table in (users, runs, memberships):
            table.create(engine)
        with engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                importlib.import_module(MIGRATION).upgrade()
            connection.execute(users.insert(), [{"id": 1}, {"id": 2}])
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))
        admin.dispose()


@pytest.fixture
def project(database, tmp_path):
    with database.begin() as connection:
        connection.execute(runs.insert(), [{"id": 1, "runid": "test-notice", "config": "test"}])
        connection.execute(memberships.insert(), [{"user_id": 1, "run_id": 1}])
    path = tmp_path / "te" / "test-notice"
    path.mkdir(parents=True)
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    write_ttl(path)
    return path, roots


def write_ttl(path, **changes):
    values = dict(policy="rolling_90d", user_disabled=False, delete_state="active",
                  expires_at=(NOW + timedelta(days=14)).isoformat())
    values.update(changes)
    (path / "TTL").write_text(json.dumps(values))


def sweep(database, project, **kwargs):
    return reconcile_ttl_notifications(database, now=NOW, roots=project[1], **kwargs)


def count(database, user=1):
    with database.connect() as connection:
        return repo.unread_count(connection, user, now=NOW)


def test_episode_retry_read_state_and_nonmutating_boundary(database, project):
    before = (project[0] / "TTL").read_bytes()
    assert sweep(database, project)["created"] == 1
    assert sweep(database, project)["created"] == 0
    assert count(database) == 1
    assert count(database, 2) == 0
    with database.connect() as connection:
        identifier = connection.scalar(sa.select(n.c.id))
    assert repo.set_read_state(database, 1, [identifier], True)["updated_count"] == 1
    sweep(database, project)
    assert count(database) == 0
    assert repo.set_read_state(database, 1, [identifier], True)["updated_count"] == 0
    assert repo.set_read_state(database, 1, [identifier], False)["updated_count"] == 1
    assert (project[0] / "TTL").read_bytes() == before
    write_ttl(project[0], expires_at=(NOW + timedelta(days=30)).isoformat())
    assert sweep(database, project)["resolved"] == 1
    assert count(database) == 0
    write_ttl(project[0])
    assert sweep(database, project)["created"] == 1
    with database.connect() as connection:
        assert connection.scalar(sa.select(sa.func.count()).select_from(n)) == 2


@pytest.mark.parametrize("changes", [
    {"policy": "disabled"}, {"policy": "excluded"}, {"user_disabled": True},
    {"delete_state": "queued"}, {"delete_state": "trash"}, {"delete_state": "purged"},
    {"expires_at": (NOW + timedelta(days=14, seconds=1)).isoformat()},
])
def test_ineligible_states(database, project, changes):
    write_ttl(project[0], **changes)
    assert sweep(database, project)["created"] == 0
    assert count(database) == 0


def test_readonly_and_missing_unknown_recover_without_new_episode(database, project):
    sweep(database, project)
    (project[0] / "TTL").write_text("broken")
    assert sweep(database, project)["unavailable"] == 1
    assert count(database) == 0

    write_ttl(project[0], expires_at=(NOW - timedelta(days=2)).isoformat())
    assert sweep(database, project)["updated"] == 1
    with database.connect() as connection:
        assert connection.scalar(sa.select(n.c.body)).endswith("overdue for deletion.")
    (project[0] / "READONLY").touch()
    assert sweep(database, project)["resolved"] == 1
    assert count(database) == 0


@pytest.mark.parametrize("changes", [{"policy": {}}, {"policy": []}, {"delete_state": {}}, {"delete_state": []}])
def test_malformed_ttl_types_mark_unavailable(database, project, changes):
    sweep(database, project)
    write_ttl(project[0], **changes)
    healthy = project[0].parent / "test-notice-2"
    healthy.mkdir()
    write_ttl(healthy)
    with database.begin() as connection:
        connection.execute(runs.insert().values(id=2, runid="test-notice-2", config="test"))
        connection.execute(memberships.insert().values(user_id=1, run_id=2))
    result = sweep(database, project)
    assert result["unavailable"] == 1
    assert result["created"] == 1 and result["status"] == "completed"
    assert count(database) == 1



def test_revoked_and_deleted_subjects_redact_without_filesystem_io(database, project):
    sweep(database, project)
    with database.begin() as connection:
        connection.execute(memberships.delete())
        assert repo.list_notifications(connection, 1, now=NOW)[0] == []
        identifier = connection.scalar(sa.select(n.c.id))
    with pytest.raises(repo.SelectionNotFound):
        repo.set_read_state(database, 1, [identifier], True)
    with database.begin() as connection:
        connection.execute(runs.delete())
        rows, _ = repo.list_notifications(connection, 1, now=NOW)
        assert rows[0]["title"] == "Project notification resolved"
        assert rows[0]["metadata"] == {}
        assert rows[0]["subject_id"] is None
        assert rows[0]["runid"] is None
        assert repo.unread_count(connection, 1, now=NOW) == 0
    assert sweep(database, project)["resolved"] == 1


def test_scope_empty_foreign_and_overlap_are_safe(database, project):
    assert sweep(database, project, registration_ids=[])["examined"] == 0
    assert sweep(database, project, registration_ids=[2])["created"] == 0
    with database.connect() as lock:
        lock.execute(sa.select(sa.func.pg_advisory_lock(producer.SWEEP_LOCK)))
        assert sweep(database, project)["status"] == "already_running"
        lock.execute(sa.select(sa.func.pg_advisory_unlock(producer.SWEEP_LOCK)))
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: sweep(database, project), range(2)))
    with database.connect() as connection:
        assert connection.scalar(sa.select(sa.func.count()).select_from(n)) == 1
    write_ttl(project[0], user_disabled=True)
    sweep(database, project, registration_ids=[2])
    assert count(database) == 1  # Out-of-scope reconciliation must not resolve it.


def seed_notices(database, number=1001):
    with database.begin() as connection:
        ids = list(connection.scalars(n.insert().returning(n.c.id), [
            dict(kind="planned_maintenance", source_key=f"test-{i}", title=f"Notice {i}", body="Plain text",
                 created_at=NOW, published_at=NOW) for i in range(number)]))
        connection.execute(r.insert(), [dict(notification_id=i, user_id=1) for i in ids])
        return ids


def test_pagination_sorts_100_bound_and_atomic_foreign_selection(database):
    ids = seed_notices(database)
    assert count(database) == 1001
    with database.connect() as connection:
        page, more = repo.list_notifications(connection, 1, now=NOW)
        assert len(page) == 100 and more
        assert page[0]["id"] == ids[-1]
    repo.set_read_state(database, 1, ids[-100:], True)
    with database.connect() as connection:
        page, _ = repo.list_notifications(connection, 1, sort="unread_first", now=NOW)
        assert page[0]["id"] == ids[-101]
        page, _ = repo.list_notifications(connection, 1, sort="read_first", now=NOW)
        assert page[0]["id"] == ids[-1] and page[0]["read_at"]
        page, more = repo.list_notifications(connection, 1, page=11, sort="newest", now=NOW)
        assert len(page) == 1 and not more
    with database.begin() as connection:
        connection.execute(r.delete().where(r.c.notification_id == ids[0]))
        connection.execute(r.insert().values(notification_id=ids[0], user_id=2))
    with pytest.raises(repo.SelectionNotFound):
        repo.set_read_state(database, 1, ids[:2], True)
    with database.connect() as connection:
        assert connection.scalar(sa.select(r.c.read_at).where(r.c.notification_id == ids[1])) is None
    with pytest.raises(ValueError):
        repo.set_read_state(database, 1, ids[:101], True)


@pytest.mark.parametrize("ids,read", [([], True), ([True], True), ([1, 1], True), ([1], "true"), ([-1], False)])
def test_selection_validation(ids, read):
    with pytest.raises(ValueError):
        repo.validate_selection(ids, read)


def test_migration_roundtrip_constraints(database):
    migration = importlib.import_module(MIGRATION)
    with database.begin() as connection:
        from alembic.autogenerate import compare_metadata
        from wepppy.weppcloud.notifications.schema import metadata
        assert not compare_metadata(MigrationContext.configure(connection), metadata)
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
            assert "notification" not in sa.inspect(connection).get_table_names()
            migration.upgrade()
        assert "notification_recipient" in sa.inspect(connection).get_table_names()
    ids = seed_notices(database, 1)
    with pytest.raises(sa.exc.IntegrityError):
        with database.begin() as connection:
            connection.execute(r.insert().values(notification_id=ids[0], user_id=1))
    with database.begin() as connection:
        connection.execute(users.delete().where(users.c.id == 1))
        assert connection.scalar(sa.select(sa.func.count()).select_from(r)) == 0
        assert connection.scalar(sa.select(sa.func.count()).select_from(n)) == 1


@pytest.fixture
def client(database, monkeypatch):
    from flask import Flask, jsonify
    from flask_login import LoginManager, UserMixin
    from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
    from wepppy.weppcloud.routes import notifications as routes
    # Exercise the existing global handler, including middleware precedence.
    from wepppy.weppcloud.app import _handle_csrf_error
    app = Flask(__name__, template_folder=str(Path(__file__).parents[2] / "wepppy/weppcloud/templates"))
    app.config.update(SECRET_KEY="test", TESTING=True)
    manager = LoginManager(app)

    class Account(UserMixin):
        def __init__(self, identifier):
            self.id = identifier

    manager.user_loader(lambda identifier: Account(identifier))
    manager.unauthorized_handler(lambda: ("Login", 302))
    CSRFProtect(app)
    app.register_error_handler(CSRFError, _handle_csrf_error)
    app.register_blueprint(routes.notifications_bp)
    app.add_url_rule("/token", view_func=lambda: jsonify(token=generate_csrf()))
    app.add_url_rule("/", endpoint="weppcloud_site.index", view_func=lambda: "home")
    app.add_url_rule("/runs", endpoint="user.runs", view_func=lambda: "projects")
    app.add_url_rule("/runs/<runid>/<config>", endpoint="run_0.runs0", view_func=lambda **_: "project")
    app.add_url_rule("/help/<doc_id>", endpoint="usersum.view_doc", view_func=lambda **_: "help")
    app.jinja_env.globals["static_url"] = lambda name: "/static/" + name
    monkeypatch.setattr(routes, "_engine", lambda: database)
    return app.test_client()


def sign_in(client, identifier=1):
    with client.session_transaction() as session:
        session["_user_id"] = str(identifier)
        session["_fresh"] = True
    return client.get("/token").json["token"]


def test_real_routes_csrf_auth_atomicity_and_escaping(database, client):
    ids = seed_notices(database, 101)
    assert client.get("/api/notifications/unread-count").status_code == 401
    denied = client.post("/api/notifications/read-state", json={"notification_ids": [ids[0]], "read": True})
    assert denied.status_code == 400 and denied.json["error"]["code"] == "csrf_failed"
    csrf = client.get("/token").json["token"]
    assert client.post("/api/notifications/read-state", headers={"X-CSRFToken": csrf},
                       json={"notification_ids": [ids[0]], "read": True}).status_code == 401
    csrf = sign_in(client)
    response = client.get("/api/notifications/unread-count")
    assert response.json["Content"]["unread_count"] == 101
    assert response.headers["Cache-Control"] == "private, no-store"
    with database.begin() as connection:
        connection.execute(n.update().where(n.c.id == ids[-1]).values(title="<script>bad()</script>"))
    rendered = client.get("/notifications").get_data(as_text=True)
    assert "&lt;script&gt;bad()&lt;/script&gt;" in rendered
    assert rendered.count("data-notification-id=") == 100
    assert client.get("/notifications?page=2").get_data(as_text=True).count("data-notification-id=") == 1
    assert count(database) == 101
    headers = {"X-CSRFToken": csrf}
    changed = client.post("/api/notifications/read-state", headers=headers,
                          json={"notification_ids": ids[-100:], "read": True})
    assert changed.json["Content"] == {"updated_count": 100, "unread_count": 1}
    assert client.get("/notifications?sort=invalid").status_code == 400
    assert client.get("/notifications?page=-1").status_code == 400
    for payload in ({"notification_ids": ids, "read": True}, [], {"notification_ids": [True], "read": True}):
        assert client.post("/api/notifications/read-state", headers=headers, json=payload).status_code == 400
    assert client.post("/api/notifications/read-state", headers=headers,
                       json={"notification_ids": [ids[0], 9999999], "read": True}).status_code == 404
    assert count(database) == 1
    sign_in(client, 2)
    assert client.get("/api/notifications/unread-count").json["Content"]["unread_count"] == 0


def test_failed_count_rolls_back_read_mutation(database, monkeypatch):
    ids = seed_notices(database, 1)
    def fail(*args, **kwargs):
        raise sa.exc.OperationalError("test failure", {}, None)
    monkeypatch.setattr(repo, "unread_count", fail)
    with pytest.raises(sa.exc.OperationalError):
        repo.set_read_state(database, 1, ids, True)
    with database.connect() as connection:
        assert connection.scalar(sa.select(r.c.read_at)) is None


def test_failed_batch_preserves_committed_work_and_retries(database, project, monkeypatch):
    healthy = project[0].parent / "test-notice-2"
    healthy.mkdir()
    write_ttl(healthy)
    with database.begin() as connection:
        connection.execute(runs.insert().values(id=2, runid="test-notice-2", config="test"))
        connection.execute(memberships.insert().values(user_id=1, run_id=2))
    monkeypatch.setattr(producer, "BATCH_SIZE", 1)
    reconcile = producer._reconcile
    def interrupted(connection, registration, *args):
        if registration == 2:
            raise RuntimeError("simulated interrupted batch")
        return reconcile(connection, registration, *args)
    monkeypatch.setattr(producer, "_reconcile", interrupted)
    with pytest.raises(RuntimeError, match="interrupted"):
        sweep(database, project)
    assert count(database) == 1
    with database.connect() as connection:
        first = connection.scalar(sa.select(n.c.id))
    repo.set_read_state(database, 1, [first], True)
    monkeypatch.setattr(producer, "_reconcile", reconcile)
    assert sweep(database, project)["created"] == 1
    assert count(database) == 1


def test_count_error_is_explicit_503(database, client, monkeypatch):
    sign_in(client)
    def fail(*args, **kwargs):
        raise sa.exc.OperationalError("simulated unavailable", {}, None)
    monkeypatch.setattr(repo, "unread_count", fail)
    response = client.get("/api/notifications/unread-count")
    assert response.status_code == 503
    assert "Content" not in response.json
    assert response.headers["Cache-Control"] == "private, no-store"
