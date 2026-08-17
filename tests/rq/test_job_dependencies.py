from __future__ import annotations

from types import SimpleNamespace

import pytest
from rq.job import Dependency, JobStatus

import wepppy.rq.job_dependencies as job_dependencies

pytestmark = pytest.mark.unit


def _job(job_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=job_id)


def test_failure_tolerant_depends_on_wraps_job_list() -> None:
    dependency = job_dependencies.failure_tolerant_depends_on([_job("a"), _job("b")])

    assert isinstance(dependency, Dependency)
    assert dependency.dependencies == ["a", "b"]
    assert dependency.allow_failure is True


def test_failure_tolerant_depends_on_wraps_single_job() -> None:
    dependency = job_dependencies.failure_tolerant_depends_on(_job("solo"))

    assert dependency.dependencies == ["solo"]
    assert dependency.allow_failure is True


def test_failure_tolerant_depends_on_accepts_raw_job_ids() -> None:
    dependency = job_dependencies.failure_tolerant_depends_on(["a", b"b"])

    assert dependency.dependencies == ["a", "b"]
    assert dependency.allow_failure is True


def test_failure_tolerant_depends_on_passes_through_existing_dependency() -> None:
    explicit = Dependency(jobs=["a"], allow_failure=False)

    assert job_dependencies.failure_tolerant_depends_on(explicit) is explicit


def test_failure_tolerant_depends_on_returns_none_when_empty() -> None:
    assert job_dependencies.failure_tolerant_depends_on(None) is None
    assert job_dependencies.failure_tolerant_depends_on([]) is None
    assert job_dependencies.failure_tolerant_depends_on([None]) is None


class _Registry:
    instances: list["_Registry"] = []

    def __init__(self, queue) -> None:
        self.queue = queue
        self.removed: list[object] = []
        _Registry.instances.append(self)

    def remove(self, job) -> None:
        self.removed.append(job)


class _Queue:
    def __init__(self) -> None:
        self.enqueued: list[object] = []

    def _enqueue_job(self, job) -> None:
        self.enqueued.append(job)


class _DeferredJob:
    def __init__(self, met: bool) -> None:
        self._met = met
        self._dependency_ids = ["upstream"]

    def get_status(self, refresh: bool = True):
        return JobStatus.DEFERRED

    def dependencies_are_met(self) -> bool:
        return self._met


@pytest.fixture(autouse=True)
def _reset_registry(monkeypatch: pytest.MonkeyPatch):
    _Registry.instances = []
    monkeypatch.setattr(job_dependencies, "DeferredJobRegistry", _Registry)


def test_release_deferred_job_if_ready_enqueues_met_dependencies() -> None:
    queue = _Queue()
    deferred_job = _DeferredJob(met=True)

    job_dependencies.release_deferred_job_if_ready(queue, deferred_job)

    assert _Registry.instances[0].removed == [deferred_job]
    assert queue.enqueued == [deferred_job]


def test_release_deferred_job_if_ready_keeps_unmet_dependencies_deferred() -> None:
    queue = _Queue()

    job_dependencies.release_deferred_job_if_ready(queue, _DeferredJob(met=False))

    assert _Registry.instances == []
    assert queue.enqueued == []


def test_release_deferred_job_if_ready_ignores_non_deferred_jobs() -> None:
    queue = _Queue()
    queued_job = SimpleNamespace(
        _dependency_ids=["upstream"],
        get_status=lambda refresh=True: JobStatus.QUEUED,
        dependencies_are_met=lambda: True,
    )

    job_dependencies.release_deferred_job_if_ready(queue, queued_job)

    assert _Registry.instances == []
    assert queue.enqueued == []


def test_release_deferred_job_if_ready_skips_jobs_without_dependencies() -> None:
    queue = _Queue()
    independent = SimpleNamespace(_dependency_ids=[])

    # No get_status attribute: proves the dependency-less short circuit fires
    # before any Redis round-trip.
    job_dependencies.release_deferred_job_if_ready(queue, independent)

    assert _Registry.instances == []
    assert queue.enqueued == []
