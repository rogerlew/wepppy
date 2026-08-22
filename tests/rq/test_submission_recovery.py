from types import SimpleNamespace

import pytest

from wepppy.rq import submission_recovery

pytestmark = pytest.mark.unit


class _Lock:
    def __init__(self, events):
        self.events = events

    def acquire(self, **kwargs):
        self.events.append("lock")
        return True

    def release(self):
        self.events.append("unlock")

    def extend(self, additional_time, **kwargs):
        self.events.append(("extend", additional_time))
        return True


def _job_func():
    return None


def test_enqueue_tracks_preallocated_id_before_enqueue(monkeypatch):
    events = []

    class Connection:
        def hget(self, name, key):
            return None

        def lock(self, name, **kwargs):
            events.append(("lock-name", name))
            return _Lock(events)

    class Queue:
        connection = Connection()

        def enqueue_call(self, func, **kwargs):
            events.append(("enqueue", kwargs["job_id"]))
            return SimpleNamespace(id=kwargs["job_id"])

    monkeypatch.setattr(submission_recovery, "new_rq_job_id", lambda: "replacement-1")
    monkeypatch.setattr(
        submission_recovery,
        "prepare_redisprep_job_id",
        lambda *args, **kwargs: events.append(("persist", kwargs["replacement_job_id"])),
    )

    job = submission_recovery.enqueue_tracked_rq_job(
        Queue(),
        _job_func,
        prep=object(),
        job_key="build",
        runid="run-1",
        args=("run-1",),
    )

    assert job.id == "replacement-1"
    assert events == [
        (
            "lock-name",
            "rq:submission-lifecycle:66e4f52214380b24dd04f707af100e5afe8d5297ba91fa2e9ad1c83b45c01229",
        ),
        ("lock-name", "rq:submission:run-1:build"),
        "lock",
        "lock",
        ("extend", 120),
        ("extend", 120),
        ("persist", "replacement-1"),
        ("extend", 120),
        ("extend", 120),
            ("enqueue", "replacement-1"),
            "unlock",
        "unlock",
    ]


def test_enqueue_does_not_run_when_hint_persistence_fails(monkeypatch):
    events = []

    class Connection:
        def hget(self, name, key):
            return None

        def lock(self, name, **kwargs):
            return _Lock(events)

    class Queue:
        connection = Connection()

        def enqueue_call(self, func, **kwargs):
            events.append("enqueue")

    def fail_prepare(*args, **kwargs):
        raise OSError("durable hint write failed")

    monkeypatch.setattr(submission_recovery, "prepare_redisprep_job_id", fail_prepare)

    try:
        submission_recovery.enqueue_tracked_rq_job(
            Queue(),
            _job_func,
            prep=object(),
            job_key="build",
            runid="run-1",
            args=("run-1",),
        )
    except OSError:
        pass
    else:
        raise AssertionError("expected persistence failure")

    assert events == [
        "lock",
        "lock",
        ("extend", 120),
        ("extend", 120),
        "unlock",
        "unlock",
    ]


def test_enqueue_checkpoints_lease_before_enqueue(monkeypatch):
    events = []

    class Connection:
        def hget(self, name, key):
            return None

        def lock(self, name, **kwargs):
            return _Lock(events)

    class Queue:
        connection = Connection()

        def enqueue_call(self, func, **kwargs):
            events.append("enqueue")
            return SimpleNamespace(id=kwargs["job_id"])

    monkeypatch.setattr(submission_recovery, "new_rq_job_id", lambda: "replacement-1")
    monkeypatch.setattr(submission_recovery, "prepare_redisprep_job_id", lambda *args, **kwargs: None)

    submission_recovery.enqueue_tracked_rq_job(
        Queue(),
        _job_func,
        prep=object(),
        job_key="build",
        runid="run-1",
        args=("run-1",),
    )

    assert events == [
        "lock",
        "lock",
        ("extend", 120),
        ("extend", 120),
        ("extend", 120),
        ("extend", 120),
        "enqueue",
        "unlock",
        "unlock",
    ]
