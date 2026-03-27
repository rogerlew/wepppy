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
