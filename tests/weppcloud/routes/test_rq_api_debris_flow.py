from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
from flask import Flask

from tests.factories.rq import RQRecorder, make_queue, make_redis_conn
from tests.factories.singleton import singleton_factory

pytestmark = pytest.mark.unit


@pytest.fixture()
def debris_flow_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Tuple[Flask, RQRecorder, Any, Any, Path]:
    import wepppy.weppcloud.routes.rq.api.api as api_module

    recorder = RQRecorder(job_ids=["job-123"])

    monkeypatch.setattr(api_module, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(api_module, "_redis_conn", lambda: make_redis_conn(recorder))
    monkeypatch.setattr(api_module, "Queue", make_queue(recorder))

    prep_cls = singleton_factory(
        "RedisPrepStub",
        attrs={"calls": []},
        methods={
            "remove_timestamp": lambda self, task: self.calls.append(("remove_timestamp", task)),
            "set_rq_job_id": lambda self, name, job_id: self.calls.append(("set_rq_job_id", name, job_id)),
        },
    )
    prep_cls.reset_instances()
    monkeypatch.setattr(api_module, "RedisPrep", prep_cls)

    monkeypatch.setattr(api_module, "run_debris_flow_rq", lambda *args, **kwargs: None)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SITE_PREFIX"] = "/weppcloud"

    return app, recorder, prep_cls, api_module, tmp_path


def test_run_debris_flow_enqueues_with_payload(debris_flow_app):
    app, recorder, prep_cls, api_module, base_path = debris_flow_app
    payload = {"clay_pct": 12.5, "liquid_limit": "30.1", "datasource": "Holden WRF Atlas"}

    with app.test_request_context(
        "/weppcloud/runs/demo/live/rq/api/run_debris_flow",
        method="POST",
        data=json.dumps(payload),
        content_type="application/json",
    ):
        response = api_module.api_run_debris_flow("demo", "live")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"Success": True, "job_id": "job-123"}

    assert len(recorder.queue_calls) == 1
    call = recorder.queue_calls[0]
    assert call.func is api_module.run_debris_flow_rq
    assert call.timeout == api_module.TIMEOUT
    assert call.kwargs["kwargs"] == {
        "payload": {"clay_pct": 12.5, "liquid_limit": 30.1, "datasource": "Holden WRF Atlas"}
    }

    prep = prep_cls.getInstance(str(base_path / "demo"))
    assert ("remove_timestamp", api_module.TaskEnum.run_debris) in prep.calls
    assert ("set_rq_job_id", "run_debris_flow_rq", "job-123") in prep.calls


def test_run_debris_flow_rejects_invalid_numeric(debris_flow_app):
    app, recorder, prep_cls, api_module, _ = debris_flow_app

    with app.test_request_context(
        "/weppcloud/runs/demo/live/rq/api/run_debris_flow",
        method="POST",
        data=json.dumps({"clay_pct": "invalid"}),
        content_type="application/json",
    ):
        response = api_module.api_run_debris_flow("demo", "live")

    assert response.status_code == 500
    body = response.get_json()
    assert body["Success"] is False
    assert "clay_pct must be numeric" in body["Error"]
    assert recorder.queue_calls == []


def test_run_debris_flow_handles_blank_datasource(debris_flow_app):
    app, recorder, prep_cls, api_module, _ = debris_flow_app

    with app.test_request_context(
        "/weppcloud/runs/demo/live/rq/api/run_debris_flow",
        method="POST",
        data=json.dumps({"datasource": "  "}),
        content_type="application/json",
    ):
        response = api_module.api_run_debris_flow("demo", "live")

    assert response.status_code == 200
    call = recorder.queue_calls[0]
    job_kwargs = call.kwargs.get("kwargs")
    assert job_kwargs is None
