from types import SimpleNamespace

import pytest

from wepppy.rq import submission_recovery

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def isolated_lifecycle_locks(tmp_path, monkeypatch):
    monkeypatch.setattr(submission_recovery, "_LIFECYCLE_LOCK_DIR", str(tmp_path))


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


def test_prepare_binds_workflow_descendants_to_recorded_root(monkeypatch):
    prior_id = "recorded-root"
    func_name = f"{_job_func.__module__}.{_job_func.__qualname__}"
    root = SimpleNamespace(
        id=prior_id,
        args=("run-1",),
        meta={"runid": "run-1"},
        func_name=func_name,
        origin="default",
    )
    owned_child = SimpleNamespace(
        id="owned-child",
        args=("run-1",),
        meta={
            "runid": "run-1",
            "wbt_subcatchment_admission_root": prior_id,
        },
        func_name=func_name,
        origin="default",
    )
    foreign_child = SimpleNamespace(
        id="foreign-child",
        args=("run-1",),
        meta={
            "runid": "run-1",
            "wbt_subcatchment_admission_root": "another-root",
        },
        func_name=func_name,
        origin="default",
    )

    def _reconcile(_root_id, **kwargs):
        assert kwargs["root_association"](root)
        assert kwargs["association"](root)
        assert kwargs["association"](owned_child)
        assert not kwargs["association"](foreign_child)
        return SimpleNamespace(state="missing", job_ids=())

    monkeypatch.setattr(submission_recovery, "reconcile_deferred_workflow", _reconcile)
    prep = SimpleNamespace(
        get_rq_job_id=lambda _key: prior_id,
        set_rq_job_id=lambda _key, _value: None,
    )
    submission_recovery.prepare_redisprep_job_id(
        prep,
        job_key="wbt",
        replacement_job_id="replacement",
        connection=object(),
        runid="run-1",
        allowed_origins=("default",),
        expected_root_func_name=func_name,
        allowed_workflow_func_names=(func_name,),
        workflow_root_meta_key="wbt_subcatchment_admission_root",
    )


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


def test_submission_lock_can_fail_fast_without_blocking() -> None:
    acquire_kwargs = []

    class BusyLock(_Lock):
        def acquire(self, **kwargs):
            acquire_kwargs.append(kwargs)
            return False

    class Connection:
        def lock(self, _name, **_kwargs):
            return BusyLock([])

    with pytest.raises(
        submission_recovery.RqSubmissionConflict,
        match="Another submission is already in progress",
    ):
        with submission_recovery.rq_submission_lock(
            Connection(),
            "run-1:request",
            lifecycle_key="run-1",
            lifecycle_type="batch",
            blocking_timeout=0,
        ):
            pytest.fail("busy lock must not enter")

    assert acquire_kwargs == [{"blocking": False}]
