from __future__ import annotations

from types import SimpleNamespace
import uuid
import pytest
import redis
from rq import Queue
from rq.job import Dependency, JobStatus

import wepppy.rq.job_dependencies as job_dependencies
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

pytestmark = pytest.mark.integration


@pytest.fixture
def rq_connection():
    connection = redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ))
    try:
        connection.ping()
    except redis.RedisError as exc:
        pytest.skip(f"compose Redis is unavailable: {exc}")
    return connection


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


def _noop() -> None:
    return None


@pytest.mark.parametrize(
    ("dependency_status", "expected_status"),
    [
        (JobStatus.FAILED, JobStatus.QUEUED),
        (JobStatus.CANCELED, JobStatus.DEFERRED),
        (JobStatus.STOPPED, JobStatus.DEFERRED),
    ],
)
def test_release_deferred_job_if_ready_requires_finished_or_failed_dependencies(
    rq_connection,
    dependency_status: JobStatus,
    expected_status: JobStatus,
) -> None:
    queue = Queue(f"dependency-release-{uuid.uuid4().hex}", connection=rq_connection)
    dependency = queue.create_job(_noop)
    dependency.set_status(dependency_status)
    dependency.save()
    deferred_job = queue.enqueue(
        _noop,
        depends_on=Dependency(jobs=[dependency], allow_failure=True),
    )
    try:
        assert deferred_job.get_status(refresh=True) == JobStatus.DEFERRED
        job_dependencies.release_deferred_job_if_ready(queue, deferred_job)
        assert deferred_job.get_status(refresh=True) == expected_status
        if expected_status == JobStatus.QUEUED:
            assert deferred_job.id not in dependency.dependent_ids
            assert rq_connection.smembers(deferred_job.dependencies_key) == set()
    finally:
        deferred_job.delete(remove_from_queue=True)
        dependency.delete(remove_from_queue=True)
        queue.delete(delete_jobs=True)


def test_release_deferred_job_if_ready_rejects_missing_dependency(rq_connection) -> None:
    queue = Queue(f"dependency-missing-{uuid.uuid4().hex}", connection=rq_connection)
    dependency = queue.create_job(_noop)
    dependency.set_status(JobStatus.FAILED)
    dependency.save()
    deferred_job = queue.enqueue(
        _noop,
        depends_on=Dependency(jobs=[dependency], allow_failure=True),
    )
    dependency.delete(remove_from_queue=True)
    try:
        job_dependencies.release_deferred_job_if_ready(queue, deferred_job)
        assert deferred_job.get_status(refresh=True) == JobStatus.DEFERRED
    finally:
        deferred_job.delete(remove_from_queue=True)
        queue.delete(delete_jobs=True)


def test_release_deferred_job_if_ready_skips_jobs_without_dependencies() -> None:
    independent = SimpleNamespace(_dependency_ids=[])
    job_dependencies.release_deferred_job_if_ready(SimpleNamespace(), independent)


@pytest.mark.parametrize(
    ("allow_failure", "other_status", "cancel_observer", "expected"),
    [
        (True, JobStatus.FINISHED, False, JobStatus.QUEUED),
        (True, JobStatus.FAILED, False, JobStatus.QUEUED),
        (False, JobStatus.FINISHED, False, JobStatus.DEFERRED),
        (True, JobStatus.QUEUED, False, JobStatus.DEFERRED),
        (True, JobStatus.CANCELED, False, JobStatus.DEFERRED),
        (True, JobStatus.STOPPED, False, JobStatus.DEFERRED),
        (True, JobStatus.FINISHED, True, JobStatus.CANCELED),
    ],
)
def test_stopped_parent_release_only_admits_authorized_terminal_observers(
    rq_connection, allow_failure, other_status, cancel_observer, expected,
):
    queue = Queue(f"stop-observer-{uuid.uuid4().hex}", connection=rq_connection)
    parent = queue.create_job(_noop)
    parent.set_status(JobStatus.STOPPED)
    parent.save()
    other = queue.create_job(_noop)
    other.set_status(other_status)
    other.save()
    observer = queue.enqueue(
        _noop,
        depends_on=Dependency(jobs=[parent, other], allow_failure=allow_failure),
    )
    try:
        assert observer.get_status() == JobStatus.DEFERRED
        if cancel_observer:
            observer.cancel()
        job_dependencies.release_deferred_job_if_ready(
            queue, observer, stopped_parent_id=parent.id,
        )
        assert observer.get_status(refresh=True) == expected
        if expected == JobStatus.QUEUED:
            assert queue.job_ids.count(observer.id) == 1
            job_dependencies.release_deferred_job_if_ready(
                queue, observer, stopped_parent_id=parent.id,
            )
            assert queue.job_ids.count(observer.id) == 1
    finally:
        for job in (observer, other, parent):
            job.delete(remove_from_queue=True)
        queue.delete(delete_jobs=True)


def test_failed_prerequisite_never_released_by_strict_helper(rq_connection):
    queue = Queue(f"strict-helper-{uuid.uuid4().hex}", connection=rq_connection)
    parent = queue.create_job(_noop)
    parent.set_status(JobStatus.FAILED)
    parent.save()
    child = queue.enqueue(_noop, depends_on=parent)
    try:
        job_dependencies.release_deferred_job_if_ready(queue, child)
        assert child.get_status(refresh=True) == JobStatus.DEFERRED
    finally:
        child.delete(remove_from_queue=True)
        parent.delete(remove_from_queue=True)
        queue.delete(delete_jobs=True)
