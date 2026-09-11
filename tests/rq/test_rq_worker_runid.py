from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pytest
import rq

from wepppy.rq.rq_worker import WepppyRqWorker

pytestmark = pytest.mark.unit


@dataclass
class _DummyJob:
    job_id: str
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    saved: bool = False

    @property
    def id(self) -> str:
        return self.job_id

    def save(self) -> None:
        self.saved = True


def _build_worker(monkeypatch: pytest.MonkeyPatch) -> WepppyRqWorker:
    worker = object.__new__(WepppyRqWorker)
    worker.log = logging.getLogger("tests.rq.test_rq_worker_runid")
    monkeypatch.setattr(rq.Worker, "perform_job", lambda _self, _job, _queue: True)
    monkeypatch.setattr(WepppyRqWorker, "_start_job_coverage", lambda _self, _job: None)
    monkeypatch.setattr("wepppy.rq.rq_worker.get_wd", lambda _runid: "/tmp/not-a-run")
    return worker


def test_perform_job_uses_positional_runid(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = _build_worker(monkeypatch)
    job = _DummyJob("job-positional", args=("alpha-run",))

    result = worker.perform_job(job, object())

    assert result is True
    assert job.saved is True
    assert job.meta["runid"] == "alpha-run"
    assert isinstance(job.meta["pid"], int)


def test_perform_job_uses_keyword_runid(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = _build_worker(monkeypatch)
    job = _DummyJob("job-kwargs", kwargs={"runid": "beta-run"})

    result = worker.perform_job(job, object())

    assert result is True
    assert job.saved is True
    assert job.meta["runid"] == "beta-run"
    assert isinstance(job.meta["pid"], int)


def test_perform_job_allows_jobs_without_runid(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = _build_worker(monkeypatch)
    job = _DummyJob("job-no-runid")

    result = worker.perform_job(job, object())

    assert result is True
    assert job.saved is True
    assert "runid" not in job.meta
    assert isinstance(job.meta["pid"], int)


def test_handle_job_failure_preserves_rq_exception_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = object.__new__(WepppyRqWorker)
    captured: dict[str, Any] = {}

    def _handle_job_failure(
        _self: object,
        _job: object,
        _queue: object,
        _registry: object,
        *,
        exc_string: str,
    ) -> None:
        captured["exc_string"] = exc_string

    monkeypatch.setattr(rq.Worker, "handle_job_failure", _handle_job_failure)
    monkeypatch.setattr(
        "wepppy.rq.rq_worker.StatusMessenger.publish",
        lambda _channel, _message: 0,
    )
    job = _DummyJob("job-failed")

    worker.handle_job_failure(job, object(), object(), exc_string="original traceback")

    assert captured["exc_string"] == "original traceback"


def test_fork_failure_status_refresh_error_does_not_interrupt_failure_handling(monkeypatch, caplog):
    import redis
    from types import SimpleNamespace

    worker = object.__new__(WepppyRqWorker)
    captured = []

    def superclass(_self, _job, _queue, _registry, *, exc_string):
        captured.append(exc_string)

    def unavailable(*, refresh):
        raise redis.ConnectionError("injected refresh failure")

    monkeypatch.setattr(rq.Worker, 'handle_job_failure', superclass)
    monkeypatch.setattr('wepppy.rq.rq_worker.StatusMessenger.publish', lambda *_args: captured.append('published'))
    job = SimpleNamespace(id='fork-child', meta={'fork_failure': {}}, get_status=unavailable)
    worker.handle_job_failure(job, object(), object(), exc_string='original task failure')
    assert captured == ['original task failure', 'published']
    assert 'Could not inspect failed fork prerequisite job_id=fork-child' in caplog.text


@pytest.mark.parametrize("stage", ["hillslopes", "watershed"])
def test_batch_stage_preserves_unvalidated_identity_without_run_access(monkeypatch, stage):
    worker = _build_worker(monkeypatch)
    job = _DummyJob("stage", args=("demo", object(), "upstream"),
                    meta={"runid": "batch;;demo;;unvalidated-leaf"})
    job.func_name = f"wepppy.rq.batch_rq.run_batch_{stage}_rq"
    def forbid_lookup(_runid):
        pytest.fail("worker must not access a batch leaf before task validation")
    monkeypatch.setattr("wepppy.rq.rq_worker.get_wd", forbid_lookup)
    assert worker.perform_job(job, object()) is True
    assert job.meta["runid"] == "batch;;demo;;unvalidated-leaf"
