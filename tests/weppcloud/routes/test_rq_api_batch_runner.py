from __future__ import annotations

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

from tests.factories.singleton import singleton_factory

BATCH_NAME = "demo"


@pytest.fixture()
def rq_batch_client(monkeypatch: pytest.MonkeyPatch, rq_environment):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(rq_api_module.rq_api_bp)

    batch_runner_stub = singleton_factory(
        "BatchRunnerStub",
        methods={
            "getInstanceFromBatchName": classmethod(lambda cls, name: cls.getInstance(name)),
        },
    )

    monkeypatch.setattr(rq_api_module, "BatchRunner", batch_runner_stub)

    env = rq_environment
    env.patch_module(monkeypatch, rq_api_module, default_job_id="batch-job-1")

    with app.test_client() as client:
        yield client, env, batch_runner_stub

    batch_runner_stub.reset_instances()
    env.redis_prep_class.reset_instances()
    env.recorder.reset()


def test_run_batch_enqueue_job(rq_batch_client):
    client, env, _batch_runner_stub = rq_batch_client

    response = client.post(f"/batch/_/{BATCH_NAME}/rq/api/run-batch")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["job_id"] == "batch-job-1"

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is rq_api_module.run_batch_rq
    assert queue_call.args == (BATCH_NAME,)

    assert env.recorder.redis_entries.count("enter") == env.recorder.redis_entries.count("exit")


def test_run_batch_returns_404_for_missing_batch(monkeypatch, rq_batch_client):
    client, env, _batch_runner_stub = rq_batch_client

    def missing(batch_name: str):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(
        rq_api_module,
        "BatchRunner",
        type(
            "MissingBatchRunner",
            (),
            {"getInstanceFromBatchName": staticmethod(missing)},
        ),
    )

    response = client.post("/batch/_/unknown/rq/api/run-batch")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
