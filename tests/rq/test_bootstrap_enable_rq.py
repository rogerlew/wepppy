from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import wepppy.rq.wepp_rq as wepp_rq
from wepppy.weppcloud.bootstrap.git_lock import bootstrap_enable_job_key, bootstrap_git_lock_key

pytestmark = pytest.mark.unit


class DummyRedis:
    def __init__(self, store: dict[str, str]) -> None:
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

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


def test_bootstrap_enable_rq_initializes_and_releases_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    store = {
        bootstrap_git_lock_key("ab-run"): json.dumps({"token": "lock-1"}),
        bootstrap_enable_job_key("ab-run"): "job-1",
    }
    init_calls: list[str] = []

    class DummyWepp:
        bootstrap_enabled = False

        def init_bootstrap(self) -> None:
            init_calls.append("called")

    monkeypatch.setattr(wepp_rq, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(wepp_rq.redis, "Redis", lambda **kwargs: DummyRedis(store))

    result = wepp_rq.bootstrap_enable_rq("ab-run", actor="user:1", lock_token="lock-1")

    assert result == {"enabled": True, "runid": "ab-run"}
    assert init_calls == ["called"]
    assert bootstrap_git_lock_key("ab-run") not in store
    assert bootstrap_enable_job_key("ab-run") not in store


def test_bootstrap_enable_rq_clears_scoped_cache_before_wepp_hydration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = {
        bootstrap_git_lock_key("ab-run"): json.dumps({"token": "lock-1"}),
        bootstrap_enable_job_key("ab-run"): "job-1",
    }
    call_order: list[tuple[str, str, str]] = []

    class DummyWepp:
        bootstrap_enabled = True

        def init_bootstrap(self) -> None:
            raise AssertionError("init_bootstrap should not run when bootstrap is already enabled")

    def _clear_cache(runid: str, *, pup_relpath: str) -> None:
        call_order.append(("clear", runid, pup_relpath))

    def _get_instance(_wd: str) -> DummyWepp:
        call_order.append(("get_instance", "ab-run", "wepp.nodb"))
        return DummyWepp()

    monkeypatch.setattr(wepp_rq, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(wepp_rq, "clear_nodb_file_cache", _clear_cache)
    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", _get_instance)
    monkeypatch.setattr(wepp_rq, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(wepp_rq.redis, "Redis", lambda **kwargs: DummyRedis(store))

    result = wepp_rq.bootstrap_enable_rq("ab-run", actor="user:1", lock_token="lock-1")

    assert result == {"enabled": True, "runid": "ab-run"}
    assert call_order == [
        ("clear", "ab-run", "wepp.nodb"),
        ("get_instance", "ab-run", "wepp.nodb"),
    ]


def test_bootstrap_enable_rq_skips_init_when_already_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    store = {
        bootstrap_git_lock_key("ab-run"): json.dumps({"token": "lock-2"}),
        bootstrap_enable_job_key("ab-run"): "job-2",
    }
    init_calls: list[str] = []

    class DummyWepp:
        bootstrap_enabled = True

        def init_bootstrap(self) -> None:
            init_calls.append("called")

    monkeypatch.setattr(wepp_rq, "get_current_job", lambda: SimpleNamespace(id="job-2"))
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(wepp_rq.redis, "Redis", lambda **kwargs: DummyRedis(store))

    result = wepp_rq.bootstrap_enable_rq("ab-run", actor="user:1", lock_token="lock-2")

    assert result == {"enabled": True, "runid": "ab-run"}
    assert init_calls == []
    assert bootstrap_git_lock_key("ab-run") not in store
    assert bootstrap_enable_job_key("ab-run") not in store
