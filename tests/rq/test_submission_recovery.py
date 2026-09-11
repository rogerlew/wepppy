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


def test_durable_job_identity_precedes_failed_receipt_write(monkeypatch):
    from redis.exceptions import ConnectionError
    events=[]
    class Connection:
        def hget(self,*args):return None
        def lock(self,*args,**kwargs):return _Lock(events)
    class Queue:
        connection=Connection()
        def enqueue_call(self,*args,**kwargs):raise AssertionError('Must not enqueue after failed receipt')
    def fail_receipt(*args,**kwargs):
        assert events[-1][0]=='durable-id'
        raise ConnectionError('unavailable before marker')
    monkeypatch.setattr(submission_recovery,'prepare_redisprep_job_id',fail_receipt)
    with pytest.raises(ConnectionError):
        submission_recovery.enqueue_tracked_rq_job(Queue(),_job_func,prep=object(),job_key='build',runid='run-1',args=('run-1',),
                                                   on_job_id=lambda identity:events.append(('durable-id',identity)))
    from uuid import UUID
    assert UUID(next(event[1] for event in events if isinstance(event,tuple) and event[0]=='durable-id'))


class _OwnedConnection:
    """Model owner-checked Redis locks, including release and contention."""
    def __init__(self):
        self.owners = {}
        self.acquired = []

    def hget(self, *args):
        return None

    def lock(self, name, **kwargs):
        from redis.exceptions import LockError
        connection = self
        class Lock:
            def acquire(self, **kwargs):
                if name in connection.owners:
                    return False
                connection.owners[name] = self
                connection.acquired.append(name)
                return True

            def extend(self, *args, **kwargs):
                if connection.owners.get(name) is not self:
                    raise LockError("Cannot extend an unlocked lock")
                return True

            def release(self):
                if connection.owners.get(name) is self:
                    del connection.owners[name]
        return Lock()


def test_new_http_admission_reacquires_after_inherited_request_closed():
    from contextvars import copy_context
    connection = _OwnedConnection()
    with submission_recovery.rq_submission_lock(connection, "run-1:request", lifecycle_key="run-1"):
        inherited = copy_context()
    assert not connection.owners

    def next_request():
        with submission_recovery.rq_submission_lock(connection, "run-1:request", lifecycle_key="run-1", inherit_lifecycle=False):
            submission_recovery.checkpoint_run_lifecycle("run-1")
            with submission_recovery.rq_submission_lock(connection, "run-1:model", lifecycle_key="run-1"):
                submission_recovery.checkpoint_run_lifecycle("run-1")
    inherited.run(next_request)
    assert len([name for name in connection.acquired if "submission-lifecycle:" in name]) == 2
    assert not connection.owners


def test_new_http_admission_does_not_bypass_active_owner():
    connection = _OwnedConnection()
    with submission_recovery.rq_submission_lock(connection, "run-1:request", lifecycle_key="run-1"):
        with pytest.raises(submission_recovery.RqSubmissionConflict, match="already in progress"):
            with submission_recovery.rq_submission_lock(connection, "run-1:request", lifecycle_key="run-1", inherit_lifecycle=False, blocking_timeout=0):
                pytest.fail("must acquire a real new lease")
        submission_recovery.checkpoint_run_lifecycle("run-1")


def test_nested_admission_still_rejects_lost_parent():
    connection = _OwnedConnection()
    with submission_recovery.rq_submission_lock(connection, "run-1:request", lifecycle_key="run-1"):
        connection.owners.clear()
        with pytest.raises(submission_recovery.RqSubmissionConflict, match="lock expired"):
            with submission_recovery.rq_submission_lock(connection, "run-1:model", lifecycle_key="run-1"):
                pytest.fail("lost parent must not permit nested mutation")


def test_http_middleware_uses_fresh_admission_context(monkeypatch):
    import asyncio
    from contextvars import copy_context
    from contextlib import contextmanager
    import wepppy.microservices.rq_engine as engine
    connection = _OwnedConnection()
    with submission_recovery.rq_submission_lock(connection, "run-1:request", lifecycle_key="run-1"):
        inherited = copy_context()

    @contextmanager
    def client(**kwargs):
        yield connection
    monkeypatch.setattr(engine, "_LIFECYCLE_REDIS_CLIENT", client)
    monkeypatch.setattr(engine, "_verify_lifecycle_bearer", lambda request: None)

    async def receive():
        return {"type": "http.request", "body": b"upload", "more_body": False}

    async def next_handler(request):
        assert (await request._receive())["body"] == b"upload"
        submission_recovery.checkpoint_run_lifecycle("run-1")
        return "accepted"

    request = SimpleNamespace(method="POST", url=SimpleNamespace(path="/api/runs/run-1/config/tasks/upload-sbs/"), headers={"Authorization": "Bearer test"}, _receive=receive)
    result = inherited.run(asyncio.run, engine.run_mutation_lifecycle_middleware(request, next_handler))
    assert result == "accepted"
    assert not connection.owners
