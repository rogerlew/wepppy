from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from flask import Flask

pytestmark = pytest.mark.routes


@pytest.fixture()
def run_sync_module(monkeypatch: pytest.MonkeyPatch):
    from wepppy.weppcloud.routes import _common

    monkeypatch.setattr(_common, "login_required", lambda fn: fn)
    monkeypatch.setattr(_common, "roles_required", lambda *args, **kwargs: (lambda fn: fn))
    module = importlib.reload(
        importlib.import_module("wepppy.weppcloud.routes.run_sync_dashboard.run_sync_dashboard")
    )
    return module


def test_api_run_sync_enqueues_job(
    run_sync_module,
    rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = run_sync_module
    app = Flask(__name__)
    app.config["TESTING"] = True

    env = rq_environment
    monkeypatch.setattr(module, "_redis_conn", env.redis_conn_factory())
    monkeypatch.setattr(module, "Queue", env.queue_class(default_job_id="job-run-sync"))
    monkeypatch.setattr(module, "run_sync_rq", lambda *args, **kwargs: None)

    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        module.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    app.register_blueprint(module.run_sync_dashboard_bp)

    with app.test_client() as client:
        response = client.post(
            "/rq/api/run-sync",
            json={
                "runid": "demo",
                "source_host": "wepp.cloud",
                "owner_email": "owner@example.com",
            },
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    assert payload["job_id"] == "job-run-sync"

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is module.run_sync_rq
    assert queue_call.args == (
        "demo",
        "wepp.cloud",
        "owner@example.com",
        module.DEFAULT_TARGET_ROOT,
        None,
    )
    assert published[0][0] == f"demo:{module.STATUS_CHANNEL_SUFFIX}"


def test_run_sync_status_lists_jobs_and_migrations(
    run_sync_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = run_sync_module
    app = Flask(__name__)
    app.config["TESTING"] = True

    module._collect_run_sync_jobs = lambda *_args, **_kwargs: [{"id": "job-1", "status": "queued"}]

    class QueryStub:
        def __init__(self, records):
            self.records = records

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            return self.records

    record = SimpleNamespace(
        id=1,
        runid="demo",
        config="cfg",
        local_path="/tmp/demo/cfg",
        source_host="wepp.cloud",
        original_url="https://wepp.cloud/weppcloud/runs/demo/cfg",
        pulled_at=None,
        owner_email="owner@example.com",
        version_at_pull=1000,
        last_status="REGISTERED",
        archive_before=None,
        archive_after=None,
        is_fixture=False,
        created_at=None,
        updated_at=None,
    )
    module.RunMigration = SimpleNamespace(query=QueryStub([record]))

    app.register_blueprint(module.run_sync_dashboard_bp)
    with app.test_client() as client:
        response = client.get("/rq/api/run-sync/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["jobs"][0]["id"] == "job-1"
    assert payload["migrations"][0]["runid"] == "demo"
