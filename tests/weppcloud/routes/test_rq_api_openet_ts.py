from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple

import pytest
from flask import Flask

from tests.factories.rq import RQRecorder, make_queue, make_redis_conn
from tests.factories.singleton import singleton_factory

pytestmark = pytest.mark.unit


@pytest.fixture()
def openet_ts_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path
) -> Tuple[Flask, RQRecorder, Any, Any, Path]:
    import wepppy.weppcloud.routes.rq.api.api as api_module

    recorder = RQRecorder(job_ids=["job-xyz"])

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

    monkeypatch.setattr(api_module, "fetch_and_analyze_openet_ts_rq", lambda *args, **kwargs: None)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SITE_PREFIX"] = "/weppcloud"

    return app, recorder, prep_cls, api_module, tmp_path


def test_acquire_openet_ts_enqueues_with_payload(openet_ts_app):
    app, recorder, prep_cls, api_module, base_path = openet_ts_app

    payload = {"force_refresh": True}

    with app.test_request_context(
        "/weppcloud/runs/demo/live/rq/api/acquire_openet_ts",
        method="POST",
        data=json.dumps(payload),
        content_type="application/json",
    ):
        response = api_module.api_openet_ts_acquire("demo", "live")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"Success": True, "job_id": "job-xyz", "payload": {"force_refresh": True}}

    assert len(recorder.queue_calls) == 1
    call = recorder.queue_calls[0]
    assert call.func is api_module.fetch_and_analyze_openet_ts_rq
    assert call.timeout == api_module.TIMEOUT
    assert call.args == ("demo",)
    assert call.kwargs["kwargs"] == {"payload": {"force_refresh": True}}

    prep = prep_cls.getInstance(str(base_path / "demo"))
    assert ("remove_timestamp", api_module.TaskEnum.fetch_openet_ts) in prep.calls
    assert ("set_rq_job_id", "fetch_and_analyze_openet_ts_rq", "job-xyz") in prep.calls


def test_acquire_openet_ts_allows_empty_payload(openet_ts_app):
    app, recorder, prep_cls, api_module, base_path = openet_ts_app

    with app.test_request_context(
        "/weppcloud/runs/demo/live/rq/api/acquire_openet_ts",
        method="POST",
        data=json.dumps({}),
        content_type="application/json",
    ):
        response = api_module.api_openet_ts_acquire("demo", "live")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"Success": True, "job_id": "job-xyz"}

    call = recorder.queue_calls[0]
    assert call.kwargs["kwargs"] == {}

    prep = prep_cls.getInstance(str(base_path / "demo"))
    assert ("remove_timestamp", api_module.TaskEnum.fetch_openet_ts) in prep.calls
