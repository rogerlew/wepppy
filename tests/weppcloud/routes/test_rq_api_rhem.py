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
def rhem_rq_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Tuple[Flask, RQRecorder, Any, Any, Path]:
    import wepppy.weppcloud.routes.rq.api.api as api_module

    recorder = RQRecorder(job_ids=["job-999"])

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

    monkeypatch.setattr(api_module, "run_rhem_rq", lambda *args, **kwargs: None)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SITE_PREFIX"] = "/weppcloud"

    return app, recorder, prep_cls, api_module, tmp_path


def test_run_rhem_enqueues_without_payload(rhem_rq_app):
    app, recorder, prep_cls, api_module, tmp_path = rhem_rq_app

    with app.test_request_context(
        "/weppcloud/runs/demo/live/rq/api/run_rhem_rq",
        method="POST",
    ):
        response = api_module.api_run_rhem("demo", "live")

    assert response.status_code == 200
    assert response.get_json() == {"Success": True, "job_id": "job-999"}

    assert len(recorder.queue_calls) == 1
    call = recorder.queue_calls[0]
    assert call.func is api_module.run_rhem_rq
    assert call.kwargs["kwargs"] is None

    prep = prep_cls.getInstance(str(tmp_path / "demo"))
    assert ("remove_timestamp", api_module.TaskEnum.run_rhem) in prep.calls
    assert ("set_rq_job_id", "run_rhem_rq", "job-999") in prep.calls


def test_run_rhem_passes_boolean_payload(rhem_rq_app):
    app, recorder, _, api_module, _ = rhem_rq_app

    payload = {"clean": False, "prep": True, "run": False}

    with app.test_request_context(
        "/weppcloud/runs/demo/live/rq/api/run_rhem_rq",
        method="POST",
        data=json.dumps(payload),
        content_type="application/json",
    ):
        response = api_module.api_run_rhem("demo", "live")

    assert response.status_code == 200
    assert recorder.queue_calls, "Expected payload to enqueue job."
    call = recorder.queue_calls[-1]
    assert call.kwargs["kwargs"] == {"payload": payload}
