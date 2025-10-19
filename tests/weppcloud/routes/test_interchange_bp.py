from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.interchange_bp as interchange_module

RUN_ID = "test-run"
CONFIG = "cfg"


def test_sanitize_subpath_variants():
    sanitize = interchange_module._sanitize_subpath
    assert sanitize(None) is None
    assert sanitize("   ") is None
    assert sanitize("subdir/output") == "subdir/output"

    with pytest.raises(ValueError):
        sanitize("../bad")
    with pytest.raises(ValueError):
        sanitize("/absolute")
    with pytest.raises(ValueError):
        sanitize("\\windows")


@pytest.fixture()
def interchange_client(monkeypatch: pytest.MonkeyPatch):
    """Provide a Flask client with Redis/RQ dependencies stubbed out."""

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(interchange_module.interchange_bp)

    dispatched: Dict[str, Any] = {}

    monkeypatch.setattr(
        interchange_module,
        "load_run_context",
        lambda runid, config: dispatched.setdefault("context", (runid, config)),
    )

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    class DummyJob:
        def __init__(self, job_id: str) -> None:
            self.id = job_id

    class DummyQueue:
        def __init__(self, connection: Any) -> None:
            self.connection = connection
            dispatched["queue_connection"] = connection
            self.last_kwargs: Dict[str, Any] = {}

        def enqueue_call(self, func, args, timeout):
            dispatched["enqueue_args"] = args
            dispatched["enqueue_func"] = func
            dispatched["enqueue_timeout"] = timeout
            job = DummyJob("job-123")
            dispatched["job"] = job
            return job

    class DummyRedis:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            dispatched["redis_kwargs"] = kwargs

        def __enter__(self) -> "DummyRedis":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(interchange_module.redis, "Redis", DummyRedis)
    monkeypatch.setattr(interchange_module, "Queue", DummyQueue)

    with app.test_client() as client:
        yield client, dispatched


def test_migrate_default_interchange_enqueues_job(interchange_client):
    client, dispatched = interchange_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/interchange/migrate",
        json={"wepp_output_subpath": "subdir"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "job_id": "job-123"}

    assert dispatched["context"] == (RUN_ID, CONFIG)
    assert dispatched["enqueue_args"] == (RUN_ID, "subdir")
    assert dispatched["enqueue_func"] is interchange_module.run_interchange_migration
    assert dispatched["enqueue_timeout"] == interchange_module.TIMEOUT


def test_migrate_default_interchange_rejects_bad_path(interchange_client):
    client, _ = interchange_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/interchange/migrate",
        json={"wepp_output_subpath": "../hack"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["Success"] is False
