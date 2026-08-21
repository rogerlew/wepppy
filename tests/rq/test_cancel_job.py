from __future__ import annotations

import pytest
from redis.exceptions import WatchError
from rq.exceptions import InvalidJobOperation

from wepppy.rq import cancel_job


pytestmark = pytest.mark.unit


class _FakeJob:
    def __init__(self, job_id: str, status: str, meta: dict[str, str] | None = None) -> None:
        self.id = job_id
        self._status = status
        self.meta = dict(meta or {})
        self.cancel_calls = 0

    def get_status(self) -> str:
        return self._status

    def cancel(self, pipeline=None) -> None:
        self.cancel_calls += 1
        if self._status == "finished":
            raise InvalidJobOperation

    def save_meta(self) -> None:
        pass


class _RedisContext:
    def __init__(self, *, present: bool = True, race: bool = False) -> None:
        self.present = present
        self.race = race

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def pipeline(self):
        return self

    def watch(self, key):
        return None

    def lpos(self, key, job_id):
        return 0 if self.present else None

    def multi(self):
        return None

    def execute(self):
        if self.race:
            raise WatchError
        return []


def _patch_job(monkeypatch: pytest.MonkeyPatch, job, *, present: bool = True, race: bool = False) -> None:
    context = _RedisContext(present=present, race=race)
    monkeypatch.setattr(cancel_job.redis, "Redis", lambda **kwargs: context)
    monkeypatch.setattr(cancel_job.Job, "fetch", lambda job_id, connection: job)


def test_non_admin_cancels_fork_archive_only_while_queued(monkeypatch: pytest.MonkeyPatch) -> None:
    class Job:
        id = "job-1"
        origin = "fork-archive"

        def __init__(self):
            self.canceled = False

        def get_status(self):
            return "queued"

        serializer = None

        def cancel(self, pipeline=None):
            self.canceled = True

    job = Job()
    _patch_job(monkeypatch, job)

    assert cancel_job.cancel_jobs("job-1", allow_started_fork_archive=False) == {"status": "ok"}
    assert job.canceled is True


@pytest.mark.parametrize("status", ["started", "intermediate"])
def test_non_admin_never_stops_handed_off_fork_archive_job(
    monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    class Job:
        id = "job-2"
        origin = "fork-archive"
        serializer = None

        def get_status(self):
            return status

    _patch_job(monkeypatch, Job())
    monkeypatch.setattr(
        cancel_job,
        "send_stop_job_command",
        lambda *args, **kwargs: pytest.fail("non-admin path issued stop"),
    )

    result = cancel_job.cancel_jobs("job-2", allow_started_fork_archive=False)
    assert result["code"] == "forbidden"


def test_non_admin_handoff_race_fails_closed_without_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    class Job:
        id = "job-3"
        origin = "fork-archive"
        serializer = None

        def get_status(self):
            return "queued"

        def cancel(self, pipeline=None):
            return None

    _patch_job(monkeypatch, Job(), race=True)
    monkeypatch.setattr(
        cancel_job,
        "send_stop_job_command",
        lambda *args, **kwargs: pytest.fail("handoff race issued stop"),
    )

    result = cancel_job.cancel_jobs("job-3", allow_started_fork_archive=False)
    assert result["code"] == "forbidden"


def test_non_admin_queued_status_but_missing_queue_entry_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Job:
        id = "job-4"
        origin = "fork-archive"
        serializer = None

        def __init__(self):
            self.canceled = False

        def get_status(self):
            return "queued"

        def cancel(self, pipeline=None):
            self.canceled = True

    job = Job()
    _patch_job(monkeypatch, job, present=False)
    monkeypatch.setattr(
        cancel_job,
        "send_stop_job_command",
        lambda *args, **kwargs: pytest.fail("handoff window issued stop"),
    )

    result = cancel_job.cancel_jobs("job-4", allow_started_fork_archive=False)
    assert result["code"] == "forbidden"
    assert job.canceled is False


def test_cancel_finished_dispatch_parent_still_cancels_descendants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _FakeJob("child", "queued")
    parent = _FakeJob("parent", "finished", {"jobs:0,scheme:concept_1": "child"})
    monkeypatch.setattr(
        cancel_job.Job,
        "fetch",
        lambda job_id, connection: child if job_id == "child" else parent,
    )

    cancel_job._cancel_job_recursive(parent, object())  # type: ignore[arg-type]

    assert parent.cancel_calls == 1
    assert child.cancel_calls == 1


def test_cancel_dispatch_parent_marks_request_under_shared_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str]] = []

    class _Lock:
        def __enter__(self):
            events.append(("lock", "enter"))

        def __exit__(self, exc_type, exc, tb):
            events.append(("lock", "exit"))
            return False

    class _Redis:
        def lock(self, key, *, timeout, blocking_timeout):
            assert key == "agfields:suite_dispatch:parent"
            assert (timeout, blocking_timeout) == (30, 30)
            return _Lock()

    child = _FakeJob("child", "queued")
    parent = _FakeJob(
        "parent",
        "finished",
        {
            "child_dispatch_lock_key": "agfields:suite_dispatch:parent",
            "jobs:0,scheme:concept_1": "child",
        },
    )

    def save_parent_meta() -> None:
        events.append(("parent", "saved"))

    parent.save_meta = save_parent_meta  # type: ignore[method-assign]
    monkeypatch.setattr(
        cancel_job.Job,
        "fetch",
        lambda job_id, connection: child if job_id == "child" else parent,
    )

    cancel_job._cancel_job_recursive(parent, _Redis())  # type: ignore[arg-type]

    assert parent.meta["cancel_requested"] is True
    assert events == [("lock", "enter"), ("parent", "saved"), ("lock", "exit")]
    assert child.cancel_calls == 1


@pytest.mark.parametrize(
    ("cleanup_state", "expected_status", "stop_expected"),
    [
        ("deleting", "accepted", False),
        ("complete", "ok", True),
    ],
)
def test_kubernetes_render_cancellation_waits_for_owned_pod_absence(
    monkeypatch: pytest.MonkeyPatch,
    cleanup_state: str,
    expected_status: str,
    stop_expected: bool,
) -> None:
    class Job(_FakeJob):
        origin = "weppcloudr-render"
        func_name = "wepppy.rq.weppcloudr_rq.render_deval_details_rq"
        kwargs = {
            "backend": "kubernetes-job",
            "control_plane_url": "https://render-controller",
            "control_plane_token_file": "/token",
        }

    job = Job("job-k8s", "started", {"render_request_digest": "a" * 64})
    _patch_job(monkeypatch, job)

    class _Client:
        def __init__(self, endpoint, token_file):
            assert endpoint == "https://render-controller"
            assert str(token_file) == "/token"

        def cancel(self, job_id, request_digest):
            assert job_id == "job-k8s"
            assert request_digest == "a" * 64
            return {
                "rq_job_id": job_id,
                "request_digest": request_digest,
                "cleanup_state": cleanup_state,
            }

    stops: list[str] = []
    monkeypatch.setattr(cancel_job, "HttpRenderControlPlaneClient", _Client)
    monkeypatch.setattr(
        cancel_job,
        "send_stop_job_command",
        lambda _connection, job_id: stops.append(job_id),
    )

    result = cancel_job.cancel_jobs("job-k8s")

    assert result["status"] == expected_status
    assert stops == (["job-k8s"] if stop_expected else [])
    assert job.meta["render_cleanup_state"] == cleanup_state


def test_kubernetes_render_without_durable_receipt_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Job(_FakeJob):
        origin = "weppcloudr-render"
        func_name = "wepppy.rq.weppcloudr_rq.render_deval_details_rq"
        kwargs = {"backend": "kubernetes-job"}

    job = Job("job-k8s", "started")
    _patch_job(monkeypatch, job)
    monkeypatch.setattr(
        cancel_job,
        "send_stop_job_command",
        lambda *_args: pytest.fail("workhorse must not stop before durable cleanup"),
    )

    result = cancel_job.cancel_jobs("job-k8s")

    assert result["code"] == "cleanup_pending"
