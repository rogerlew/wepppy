from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

import wepppy.nodb.base as base

pytestmark = pytest.mark.unit


class _RedisStub:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._hash: dict[str, dict[str, str]] = {}

    def get(self, key: str):
        return self._kv.get(key)

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        if nx and key in self._kv:
            return False
        self._kv[key] = value
        return True

    def delete(self, key: str):
        self._kv.pop(key, None)

    def hset(self, name: str, key: str, value: str):
        bucket = self._hash.setdefault(name, {})
        bucket[key] = value

    def hget(self, name: str, key: str):
        return self._hash.get(name, {}).get(key)


class _DummyNoDb(base.NoDbBase):
    filename = "dummy.nodb"

    def _load_mods(self):  # noqa: ANN001 - matches production signature
        return None

    def _init_logging(self):  # noqa: ANN001 - matches production signature
        return None

    def __init__(self, wd: str, cfg_fn: str = "0.cfg") -> None:
        super().__init__(wd, cfg_fn)
        self.value = 0


@pytest.fixture()
def redis_lock_stub(monkeypatch: pytest.MonkeyPatch) -> _RedisStub:
    stub = _RedisStub()
    monkeypatch.setattr(base, "redis_lock_client", stub, raising=False)
    return stub


@pytest.fixture()
def disable_redis_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(base, "redis_nodb_cache_client", None, raising=False)


def _install_db_api_stub(
    monkeypatch: pytest.MonkeyPatch,
    *,
    update_last_modified,
) -> None:
    module = types.ModuleType("wepppy.weppcloud.db_api")
    module.update_last_modified = update_last_modified
    monkeypatch.setitem(sys.modules, "wepppy.weppcloud.db_api", module)


def test_locked_releases_lock_and_does_not_persist_on_exception(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
) -> None:
    nodb = _DummyNoDb(str(tmp_path))

    with pytest.raises(ValueError, match="boom"):
        with nodb.locked():
            nodb.value = 10
            raise ValueError("boom")

    assert not nodb.islocked()
    assert not (tmp_path / nodb.filename).exists()


def test_locked_persists_state_and_unlocks_on_success(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
) -> None:
    nodb = _DummyNoDb(str(tmp_path))

    with nodb.locked():
        nodb.value = 123

    assert not nodb.islocked()
    persisted = _DummyNoDb.load_detached(str(tmp_path))
    assert persisted is not None
    assert persisted.value == 123


def test_dump_swallows_redis_cache_mirror_write_errors(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _CacheStub:
        def set(self, *_args, **_kwargs):
            raise base.redis.exceptions.RedisError("boom")

    _install_db_api_stub(monkeypatch, update_last_modified=lambda *_args, **_kwargs: None)
    monkeypatch.setattr(base, "redis_nodb_cache_client", _CacheStub(), raising=False)

    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    assert (tmp_path / nodb.filename).exists()


def test_dump_swallows_update_last_modified_errors(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _update_last_modified(_runid: str):
        raise RuntimeError("db down")

    _install_db_api_stub(monkeypatch, update_last_modified=_update_last_modified)

    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    assert (tmp_path / nodb.filename).exists()


def test_dump_swallows_last_modified_redis_mirror_errors(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_db_api_stub(monkeypatch, update_last_modified=lambda *_args, **_kwargs: None)

    original_hset = redis_lock_stub.hset

    def _hset(name: str, key: str, value: str):
        if key == "last_modified":
            raise base.redis.exceptions.RedisError("boom")
        return original_hset(name, key, value)

    monkeypatch.setattr(redis_lock_stub, "hset", _hset)

    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    assert (tmp_path / nodb.filename).exists()


def test_load_detached_drops_corrupt_cache_payload_and_loads_from_disk(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.value = 7
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    class _CorruptCache:
        def __init__(self):
            self.deleted: list[str] = []

        def get(self, _key: str):
            return "this is not jsonpickle"

        def delete(self, key: str):
            self.deleted.append(key)

    cache = _CorruptCache()
    monkeypatch.setattr(base, "redis_nodb_cache_client", cache, raising=False)

    loaded = _DummyNoDb.load_detached(str(tmp_path))
    assert loaded is not None
    assert loaded.value == 7
    assert cache.deleted == [os.fspath(tmp_path / nodb.filename)]
