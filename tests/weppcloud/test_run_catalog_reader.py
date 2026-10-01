from datetime import timedelta
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import registry, scoped_session, sessionmaker
from flask import Flask

from tests.weppcloud.test_run_catalog_postgres import database
from wepppy.weppcloud.run_catalog.schema import catalog, runs
from wepppy.weppcloud.run_catalog import repository

pytestmark = pytest.mark.integration


@pytest.fixture
def reader_app(database, monkeypatch):
    import wepppy.weppcloud.app as app_module
    from wepppy.weppcloud.routes import user as user_routes
    mapping = registry()
    users = sa.Table("user", mapping.metadata, sa.Column("id", sa.Integer, primary_key=True), sa.Column("email", sa.Text))
    access = sa.Table("runs_users", mapping.metadata, sa.Column("run_id", sa.Integer, sa.ForeignKey(runs.c.id)), sa.Column("user_id", sa.Integer))
    mapping.metadata.create_all(database)

    class RegisteredRun:
        pass

    class Owner:
        pass

    mapping.map_imperatively(RegisteredRun, runs)
    mapping.map_imperatively(Owner, users)
    session = scoped_session(sessionmaker(bind=database))
    RegisteredRun.query = session.query_property()
    monkeypatch.setattr(app_module, "Run", RegisteredRun)
    monkeypatch.setattr(app_module, "User", Owner)
    monkeypatch.setattr(app_module, "runs_users", access)
    monkeypatch.setattr(app_module, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(user_routes, "_resolve_runs_user_id", lambda alias: (1, None))
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "postgres")

    def forbidden(*args, **kwargs):
        pytest.fail("Database reader invoked a project filesystem helper")

    monkeypatch.setattr(user_routes, "get_wd", forbidden)
    monkeypatch.setattr(user_routes, "_collect_run_rows", forbidden)
    monkeypatch.setattr(user_routes, "_collect_metas_for_runs", forbidden)
    monkeypatch.setattr(user_routes, "_collect_map_metas_for_runs", forbidden)
    monkeypatch.setattr(user_routes, "_ttl_deletion_at", forbidden)
    now = repository.utcnow()
    with database.begin() as connection:
        connection.execute(users.insert(), [{"id": 1, "email": "owner@example.test"}, {"id": 2, "email": "other@example.test"}])
        connection.execute(runs.insert(), [dict(id=identifier, runid=f"run-{identifier}", owner_id="1", config="cfg", last_modified=now.replace(tzinfo=None)) for identifier in range(1, 5)])
        connection.execute(access.insert(), [{"run_id": identifier, "user_id": 1 if identifier < 4 else 2} for identifier in range(1, 5)])
        repository.seed(connection)
        connection.execute(catalog.update().values(
            name="Visible", scenario="", readonly=False, ron_state="ready", readonly_state="ready", ttl_state="missing",
            source_versions={"ron": {"state": "ready"}}, ron_observed_at=now, readonly_observed_at=now,
            indexed_revision=1, last_attempt_at=now, refreshed_at=now))
        connection.execute(catalog.update().where(catalog.c.run_id == 2).values(dirty_revision=2))
        connection.execute(catalog.update().where(catalog.c.run_id == 3).values(ron_state="missing", source_versions={"ron": {"state": "missing"}}))
    app = Flask(__name__)
    app.secret_key = "isolated-test"
    yield app, user_routes, database
    session.remove()
    mapping.dispose()


@pytest.mark.parametrize("endpoint,path,key", [
    ("runs_catalog", "/runs/catalog", "runs"),
    ("runs_map_data", "/runs/map-data", "runs"),
    ("runs", "/runs?format=json&per_page=1", "metas"),
    ("runs", "/runs?format=json&sort=name&per_page=1", "metas"),
])
def test_real_sql_scope_counts_and_no_project_io(reader_app, endpoint, path, key):
    app, routes, engine = reader_app
    with app.test_request_context(path):
        response = getattr(routes, endpoint).__wrapped__()
        assert response.status_code == 200
        payload = response.get_json()
    assert {row["runid"] for row in payload[key]} <= {"run-1", "run-2"}
    assert payload["catalog_status"] == {"mode": "postgres", "pending": 0, "stale": 1, "unavailable": 1}
    assert "source_versions" not in str(payload)
    if endpoint == "runs" and "sort=name" not in path:
        assert payload["pagination"]["total"] == 3


def test_optional_ttl_failure_does_not_hide_initial_snapshot(reader_app):
    app, routes, engine = reader_app
    with engine.begin() as connection:
        connection.execute(catalog.update().where(catalog.c.run_id == 1).values(indexed_revision=0, ttl_state="unreadable"))
    with app.test_request_context("/runs/catalog"):
        payload = routes.runs_catalog.__wrapped__().get_json()
    row = next(row for row in payload["runs"] if row["runid"] == "run-1")
    assert row["catalog_state"] == "stale"
    assert row["ttl_deletion_at"] is None


def test_malformed_owner_label_keeps_legacy_anonymous_fallback(reader_app):
    app, routes, engine = reader_app
    with engine.begin() as connection:
        connection.execute(runs.update().where(runs.c.id == 1).values(owner_id="²"))
    with app.test_request_context("/runs/catalog"):
        response = routes.runs_catalog.__wrapped__()
    assert response.status_code == 200
    row = next(row for row in response.json["runs"] if row["runid"] == "run-1")
    assert row["owner"] == "<anonymous>"


@pytest.mark.slow
def test_805_row_sql_reader_timing(reader_app):
    import json
    import time
    from concurrent.futures import ThreadPoolExecutor
    import wepppy.weppcloud.app as app_module
    app, routes, engine = reader_app
    now = repository.utcnow()
    with engine.begin() as connection:
        connection.execute(runs.insert(), [{"id": identifier, "runid": f"run-{identifier}", "owner_id": "1", "config": "cfg"} for identifier in range(5, 807)])
        connection.execute(app_module.runs_users.insert(), [{"run_id": identifier, "user_id": 1} for identifier in range(5, 807)])
        while repository.seed(connection):
            pass
        connection.execute(catalog.update().values(name="Timing", scenario="", readonly=False, ron_state="ready", readonly_state="ready", ttl_state="missing",
                                                  source_versions={"ron": {"state": "ready"}}, indexed_revision=catalog.c.dirty_revision, refreshed_at=now))

    def request(endpoint):
        started = time.perf_counter()
        with app.test_request_context("/runs/catalog"):
            response = getattr(routes, endpoint).__wrapped__()
            assert response.status_code == 200
            assert len(response.get_json()["runs"]) == 805
            size = len(response.data)
        return time.perf_counter() - started, size

    for endpoint in ("runs_catalog", "runs_map_data"):
        samples = [request(endpoint) for _ in range(100)]
        durations = sorted(duration for duration, _ in samples)
        with ThreadPoolExecutor(max_workers=4) as executor:
            concurrent = list(executor.map(request, [endpoint] * 20))
        print(json.dumps({"endpoint": endpoint, "scope": 805, "sequential_requests": 100,
                          "p95_seconds": durations[94], "p99_seconds": durations[98],
                          "payload_bytes": samples[-1][1], "concurrent_max_seconds": max(item[0] for item in concurrent)}))
        assert durations[94] <= 1
        assert durations[98] <= 2


@pytest.mark.slow
def test_real_file_sql_http_browser_chain(reader_app, tmp_path, monkeypatch):
    import os
    from pathlib import Path
    import subprocess
    import threading
    from jinja2 import DictLoader
    from werkzeug.serving import make_server
    from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub
    from wepppy.nodb import base, persistence_events
    from wepppy.weppcloud.run_catalog.adapter import Adapter, Settings
    from wepppy.weppcloud.run_catalog.paths import Roots

    app, routes, engine = reader_app
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    directory = tmp_path / "ru" / "run-1"
    directory.mkdir(parents=True)
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    monkeypatch.setattr(persistence_events, "_observer", Adapter(Settings("postgres", "catalog"), roots, lambda: engine))

    class MetadataController(_DummyNoDb):
        filename = "ron.nodb"

    controller = MetadataController(str(directory))
    with controller.locked(validate_on_success=False):
        controller._name = "Source to browser"
        controller._scenario = ""
        controller._map = None
    with engine.connect() as connection:
        assert connection.scalar(sa.select(catalog.c.dirty_revision).where(catalog.c.run_id == 1)) == 2
    assert repository.refresh(engine, 1, roots) == "ready"
    template = Path(__file__).parents[2] / "wepppy/weppcloud/templates/user/runs2.html"
    app.jinja_loader = DictLoader({"user/runs2.html": template.read_text(),
                                  "base_pure.htm": '{% block body %}{% endblock %}{% block script_extras %}{% endblock %}'})
    app.jinja_env.globals["static_url"] = lambda path: "/static/" + path
    monkeypatch.setattr(routes, "current_user", SimpleNamespace(id=1))
    monkeypatch.setattr(routes, "_is_admin_runs_viewer", lambda: False)
    for path, endpoint in (("/runs", "runs"), ("/runs/catalog", "runs_catalog"), ("/runs/map-data", "runs_map_data")):
        app.add_url_rule(path, "user." + endpoint, getattr(routes, endpoint).__wrapped__)
    app.add_url_rule("/runs/users", "user.runs_users", lambda: {})
    app.add_url_rule("/docs/<doc_id>", "usersum.view_doc", lambda doc_id: doc_id)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    source_root = Path(__file__).parents[2]
    static_source = source_root / "wepppy/weppcloud/static-src"
    environment = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(static_source / ".playwright-browsers"))
    javascript = """const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    const origin = process.argv[1];
    await page.route('**/*', route => route.request().url().startsWith(origin) ? route.continue() : route.abort());
    await page.goto(origin + '/runs', {waitUntil: 'domcontentloaded'});
    await page.getByRole('cell', {name: 'Source to browser', exact: true}).waitFor();
    await page.getByText('Visible (metadata updating)', {exact: true}).waitFor();
    const summary = await page.locator('#runs_catalog_status').textContent();
    if (!summary.includes('Metadata updating: 1. Unavailable projects: 1.')) throw new Error(summary);
    const payload = await page.evaluate(async () => (await fetch('/runs/map-data')).json());
    if (payload.runs.some(run => run.runid === 'run-4')) throw new Error('unauthorized run');
    console.log('file -> observer -> PostgreSQL -> HTTP -> Chromium: PASS');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""
    try:
        result = subprocess.run(["node", "-e", javascript, f"http://127.0.0.1:{server.server_port}"],
                                cwd=static_source, env=environment, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        assert "Chromium: PASS" in result.stdout
    finally:
        server.shutdown()
        thread.join(timeout=5)
