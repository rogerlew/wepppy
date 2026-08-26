from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from wepppy.weppcloud.bootstrap import enable_jobs
from wepppy.weppcloud.bootstrap.enable_jobs import BootstrapLockBusyError
from wepppy.weppcloud.bootstrap.git_lock import bootstrap_enable_job_key, bootstrap_git_lock_key
from wepppy.rq.submission_recovery import RqEnqueueVerificationError

pytestmark = pytest.mark.unit


class DummyRedis:
    def __init__(self, store: dict[str, str]) -> None:
        self._store = store
        self.set_history: list[tuple[str, int | None, bool]] = []
        self.setex_history: list[tuple[str, int]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        self.set_history.append((key, ex, nx))
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True

    def setex(self, key: str, _ttl: int, value: str) -> bool:
        self.setex_history.append((key, _ttl))
        self._store[key] = str(value)
        return True

    def get(self, key: str):
        return self._store.get(key)

    def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    def eval(self, script: str, _numkeys: int, key: str, arg: str) -> int:
        if "cjson.decode" in script:
            raw = self._store.get(key)
            if raw is None:
                return 0
            payload = json.loads(raw)
            if payload.get("token") != arg:
                return 0
            del self._store[key]
            return 1

        raw = self._store.get(key)
        if raw is None or str(raw) != str(arg):
            return 0
        del self._store[key]
        return 1


def test_enqueue_bootstrap_enable_returns_sync_when_already_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(enable_jobs.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": True})())

    payload, status_code = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status_code == 200
    assert payload == {"enabled": True, "message": "Bootstrap already enabled."}


def test_enqueue_bootstrap_enable_returns_existing_job_when_dedupe_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: dict[str, str] = {bootstrap_enable_job_key("run-1"): "job-existing"}

    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(enable_jobs.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **kwargs: DummyRedis(store))
    monkeypatch.setattr(enable_jobs.Job, "fetch", lambda *args, **kwargs: SimpleNamespace(kwargs={}))
    monkeypatch.setattr(
        enable_jobs,
        "reconcile_deferred_workflow",
        lambda *args, **kwargs: SimpleNamespace(state="active"),
    )

    payload, status_code = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status_code == 202
    assert payload["job_id"] == "job-existing"
    assert payload["queued"] is True


def test_enqueue_bootstrap_enable_raises_when_git_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, str] = {
        bootstrap_git_lock_key("run-1"): json.dumps({"token": "existing"}),
    }

    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(enable_jobs.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **kwargs: DummyRedis(store))

    with pytest.raises(BootstrapLockBusyError, match="bootstrap lock busy"):
        enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")


def test_enqueue_bootstrap_enable_sets_dedupe_key_and_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, str] = {}
    enqueued: dict[str, str] = {}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            enqueued["args"] = str(args)
            return type("Job", (), {"id": "job-77"})()

    dummy_redis = DummyRedis(store)

    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(enable_jobs.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **kwargs: dummy_redis)
    monkeypatch.setattr(enable_jobs, "Queue", DummyQueue)
    monkeypatch.setattr(enable_jobs, "new_rq_job_id", lambda: "job-77")

    payload, status_code = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status_code == 202
    assert payload["job_id"] == "job-77"
    assert payload["queued"] is True
    assert store[bootstrap_enable_job_key("run-1")] == "job-77"
    assert bootstrap_git_lock_key("run-1") in store
    assert "bootstrap_enable_rq" in enqueued["args"]


def test_enqueue_bootstrap_enable_extends_ttls_for_long_rq_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: dict[str, str] = {}
    dummy_redis = DummyRedis(store)
    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(enable_jobs.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **kwargs: dummy_redis)
    monkeypatch.setattr(enable_jobs, "RQ_TIMEOUT", 7200)
    monkeypatch.setattr(enable_jobs, "BOOTSTRAP_GIT_LOCK_TTL_SECONDS", 900)
    monkeypatch.setattr(enable_jobs, "BOOTSTRAP_ENABLE_JOB_TTL_SECONDS", 900)

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            return type("Job", (), {"id": "job-88"})()

    monkeypatch.setattr(enable_jobs, "Queue", DummyQueue)

    payload, status_code = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status_code == 202
    assert payload["job_id"] == "job-88"

    lock_entries = [entry for entry in dummy_redis.set_history if entry[0] == bootstrap_git_lock_key("run-1")]
    assert lock_entries
    _, lock_ttl, _ = lock_entries[-1]
    assert lock_ttl == 7500

    dedupe_entries = [entry for entry in dummy_redis.setex_history if entry[0] == bootstrap_enable_job_key("run-1")]
    assert dedupe_entries
    _, dedupe_ttl = dedupe_entries[-1]
    assert dedupe_ttl == 7500


def test_enqueue_bootstrap_enable_replaces_deferred_and_releases_old_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_lock = json.dumps({"token": "old-token"})
    store = {
        bootstrap_enable_job_key("run-1"): "old-job",
        bootstrap_git_lock_key("run-1"): old_lock,
    }
    redis_conn = DummyRedis(store)
    monkeypatch.setattr(enable_jobs, "get_wd", lambda *_args, **_kwargs: "/tmp/run")
    monkeypatch.setattr(
        enable_jobs.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(bootstrap_enabled=False),
    )
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **_kwargs: redis_conn)
    monkeypatch.setattr(
        enable_jobs.Job,
        "fetch",
        lambda *_args, **_kwargs: SimpleNamespace(kwargs={"lock_token": "old-token"}),
    )
    monkeypatch.setattr(
        enable_jobs,
        "reconcile_deferred_workflow",
        lambda *_args, **_kwargs: SimpleNamespace(state="canceled"),
    )
    monkeypatch.setattr(enable_jobs, "new_rq_job_id", lambda: "replacement-job")

    class QueueStub:
        name = "default"

        def __init__(self, **_kwargs):
            pass

        def enqueue_call(self, *_args, **_kwargs):
            return SimpleNamespace(id="replacement-job")

    monkeypatch.setattr(enable_jobs, "Queue", QueueStub)

    payload, status = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status == 202
    assert payload["job_id"] == "replacement-job"
    assert store[bootstrap_enable_job_key("run-1")] == "replacement-job"
    assert store[bootstrap_git_lock_key("run-1")] != old_lock


def test_enqueue_bootstrap_enable_preserves_receipt_and_lock_when_commit_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: dict[str, str] = {}
    redis_conn = DummyRedis(store)
    monkeypatch.setattr(enable_jobs, "get_wd", lambda *_args, **_kwargs: "/tmp/run")
    monkeypatch.setattr(
        enable_jobs.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(bootstrap_enabled=False),
    )
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **_kwargs: redis_conn)
    monkeypatch.setattr(enable_jobs, "new_rq_job_id", lambda: "planned-job")

    class QueueStub:
        name = "default"

        def __init__(self, **_kwargs):
            pass

        def enqueue_call(self, *_args, **_kwargs):
            raise RqEnqueueVerificationError("commit unknown")

    monkeypatch.setattr(enable_jobs, "Queue", QueueStub)

    with pytest.raises(RqEnqueueVerificationError, match="commit unknown"):
        enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert store[bootstrap_enable_job_key("run-1")] == "planned-job"
    assert json.loads(store[bootstrap_git_lock_key("run-1")])["token"] == "planned-job"


def test_enqueue_bootstrap_enable_recovers_missing_commit_unknown_lock_owner_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: dict[str, str] = {
        bootstrap_enable_job_key("run-1"): "planned-job",
        bootstrap_git_lock_key("run-1"): json.dumps({"token": "planned-job"}),
    }
    redis_conn = DummyRedis(store)
    monkeypatch.setattr(enable_jobs, "get_wd", lambda *_args, **_kwargs: "/tmp/run")
    monkeypatch.setattr(
        enable_jobs.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(bootstrap_enabled=False),
    )
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **_kwargs: redis_conn)
    monkeypatch.setattr(
        enable_jobs.Job,
        "fetch",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(enable_jobs.NoSuchJobError),
    )
    monkeypatch.setattr(
        enable_jobs,
        "reconcile_deferred_workflow",
        lambda *_args, **_kwargs: SimpleNamespace(state="missing"),
    )
    monkeypatch.setattr(enable_jobs, "new_rq_job_id", lambda: "replacement-job")

    class QueueStub:
        name = "default"

        def __init__(self, **_kwargs): pass
        def enqueue_call(self, *_args, **_kwargs):
            return SimpleNamespace(id="replacement-job")

    monkeypatch.setattr(enable_jobs, "Queue", QueueStub)

    payload, status = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status == 202
    assert payload["job_id"] == "replacement-job"
    assert store[bootstrap_enable_job_key("run-1")] == "replacement-job"
    assert json.loads(store[bootstrap_git_lock_key("run-1")])["token"] == "replacement-job"

    # A stale receipt must not delete a lock already replaced by another owner.
    store[bootstrap_enable_job_key("run-1")] = "planned-job"
    store[bootstrap_git_lock_key("run-1")] = json.dumps({"token": "newer-owner"})
    with pytest.raises(BootstrapLockBusyError, match="bootstrap lock busy"):
        enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")
    assert json.loads(store[bootstrap_git_lock_key("run-1")])["token"] == "newer-owner"


def test_enqueue_bootstrap_enable_releases_terminal_legacy_lock_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = {
        bootstrap_enable_job_key("run-1"): "legacy-job",
        bootstrap_git_lock_key("run-1"): json.dumps({"token": "legacy-random-token"}),
    }
    redis_conn = DummyRedis(store)
    monkeypatch.setattr(enable_jobs, "get_wd", lambda *_args, **_kwargs: "/tmp/run")
    monkeypatch.setattr(
        enable_jobs.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(bootstrap_enabled=False),
    )
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **_kwargs: redis_conn)
    monkeypatch.setattr(
        enable_jobs.Job,
        "fetch",
        lambda *_args, **_kwargs: SimpleNamespace(
            kwargs={"lock_token": "legacy-random-token"}
        ),
    )
    monkeypatch.setattr(
        enable_jobs,
        "reconcile_deferred_workflow",
        lambda *_args, **_kwargs: SimpleNamespace(state="terminal"),
    )
    monkeypatch.setattr(enable_jobs, "new_rq_job_id", lambda: "replacement-job")

    class QueueStub:
        name = "default"

        def __init__(self, **_kwargs): pass
        def enqueue_call(self, *_args, **_kwargs):
            return SimpleNamespace(id="replacement-job")

    monkeypatch.setattr(enable_jobs, "Queue", QueueStub)

    payload, status = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status == 202
    assert payload["job_id"] == "replacement-job"
    assert json.loads(store[bootstrap_git_lock_key("run-1")])["token"] == "replacement-job"
