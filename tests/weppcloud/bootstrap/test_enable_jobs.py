from __future__ import annotations

import json

import pytest

from wepppy.weppcloud.bootstrap import enable_jobs
from wepppy.weppcloud.bootstrap.enable_jobs import BootstrapLockBusyError
from wepppy.weppcloud.bootstrap.git_lock import bootstrap_enable_job_key, bootstrap_git_lock_key

pytestmark = pytest.mark.unit


class DummyRedis:
    def __init__(self, store: dict[str, str]) -> None:
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True

    def setex(self, key: str, _ttl: int, value: str) -> bool:
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
    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(enable_jobs.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": True})())

    payload, status_code = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status_code == 200
    assert payload == {"enabled": True, "message": "Bootstrap already enabled."}


def test_enqueue_bootstrap_enable_returns_existing_job_when_dedupe_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: dict[str, str] = {bootstrap_enable_job_key("run-1"): "job-existing"}

    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(enable_jobs.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **kwargs: DummyRedis(store))

    payload, status_code = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status_code == 202
    assert payload["job_id"] == "job-existing"
    assert payload["queued"] is True


def test_enqueue_bootstrap_enable_raises_when_git_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, str] = {
        bootstrap_git_lock_key("run-1"): json.dumps({"token": "existing"}),
    }

    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid: "/tmp/run")
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

    monkeypatch.setattr(enable_jobs, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(enable_jobs.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(enable_jobs.redis, "Redis", lambda **kwargs: DummyRedis(store))
    monkeypatch.setattr(enable_jobs, "Queue", DummyQueue)

    payload, status_code = enable_jobs.enqueue_bootstrap_enable("run-1", actor="user:1")

    assert status_code == 202
    assert payload["job_id"] == "job-77"
    assert payload["queued"] is True
    assert store[bootstrap_enable_job_key("run-1")] == "job-77"
    assert bootstrap_git_lock_key("run-1") in store
    assert "bootstrap_enable_rq" in enqueued["args"]
