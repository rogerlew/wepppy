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
def interchange_client(
    monkeypatch: pytest.MonkeyPatch,
    rq_environment,
):
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

    env = rq_environment
    queue_cls = env.queue_class(default_job_id="job-123")
    monkeypatch.setattr(interchange_module, "Queue", queue_cls)
    redis_client_cls = env.redis_client_class()
    monkeypatch.setattr(interchange_module.redis, "Redis", redis_client_cls)

    with app.test_client() as client:
        yield client, dispatched, env


def test_migrate_default_interchange_enqueues_job(interchange_client):
    client, dispatched, env = interchange_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/interchange/migrate",
        json={"wepp_output_subpath": "subdir"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "job_id": "job-123"}

    assert dispatched["context"] == (RUN_ID, CONFIG)
    queue_call = env.recorder.queue_calls[0]
    assert queue_call.args == (RUN_ID, "subdir")
    assert queue_call.func is interchange_module.run_interchange_migration
    assert queue_call.timeout == interchange_module.TIMEOUT


def test_migrate_default_interchange_rejects_bad_path(interchange_client):
    client, _, _ = interchange_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/interchange/migrate",
        json={"wepp_output_subpath": "../hack"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["Success"] is False
