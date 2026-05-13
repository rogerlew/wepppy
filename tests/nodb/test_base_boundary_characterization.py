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


def _prime_stable_dummy_payload_signature(controller: _DummyNoDb, value: str = "A") -> None:
    """Warm up dummy payload serialization so subsequent writes are size-stable."""

    for _ in range(3):
        controller.lock()
        try:
            controller.value = value
            controller.dump()
        finally:
            controller.unlock(flag="-f")


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


def test_getinstance_ignores_stale_cache_signature_and_rehydrates_from_disk(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.value = 17
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    nodb_path = tmp_path / nodb.filename
    disk_stat = nodb_path.stat()

    stale_cached = _DummyNoDb.load_detached(str(tmp_path))
    assert stale_cached is not None
    stale_cached.value = 99
    stale_cached._nodb_mtime = disk_stat.st_mtime - 30
    stale_cached._nodb_size = disk_stat.st_size

    class _StaleCache:
        def __init__(self, payload: str) -> None:
            self.payload = payload
            self.set_calls: list[str] = []

        def get(self, _key: str):
            return self.payload

        def set(self, _key: str, value: str, *, ex=None, nx: bool = False):
            self.payload = value
            self.set_calls.append(value)
            return True

        def delete(self, _key: str):
            return 1

    stale_cache = _StaleCache(base.jsonpickle.encode(stale_cached))
    monkeypatch.setattr(base, "redis_nodb_cache_client", stale_cache, raising=False)

    _DummyNoDb.cleanup_run_instances(str(tmp_path))
    loaded = _DummyNoDb.getInstance(str(tmp_path))

    assert loaded.value == 17
    assert stale_cache.set_calls, "expected disk rehydrate path to refresh Redis cache"
    refreshed_cached = base.jsonpickle.decode(stale_cache.payload)
    assert refreshed_cached.value == 17


def test_load_detached_ignores_stale_cache_signature_and_rehydrates_from_disk(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.value = 23
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    nodb_path = tmp_path / nodb.filename
    disk_stat = nodb_path.stat()

    stale_cached = _DummyNoDb.load_detached(str(tmp_path))
    assert stale_cached is not None
    stale_cached.value = 404
    stale_cached._nodb_mtime = disk_stat.st_mtime - 30
    stale_cached._nodb_size = disk_stat.st_size

    class _ReadOnlyStaleCache:
        def __init__(self, payload: str) -> None:
            self.payload = payload

        def get(self, _key: str):
            return self.payload

        def delete(self, _key: str):
            return 1

    monkeypatch.setattr(
        base,
        "redis_nodb_cache_client",
        _ReadOnlyStaleCache(base.jsonpickle.encode(stale_cached)),
        raising=False,
    )

    loaded = _DummyNoDb.load_detached(str(tmp_path))
    assert loaded is not None
    assert loaded.value == 23


def test_getinstance_accepts_fresh_cache_signature_without_disk_rehydrate(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.value = 31
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    cached = _DummyNoDb.load_detached(str(tmp_path))
    assert cached is not None

    class _FreshCache:
        def __init__(self, payload: str) -> None:
            self.payload = payload
            self.set_calls: list[str] = []

        def get(self, _key: str):
            return self.payload

        def set(self, _key: str, value: str, *, ex=None, nx: bool = False):
            self.payload = value
            self.set_calls.append(value)
            return True

        def delete(self, _key: str):
            return 1

    cache = _FreshCache(base.jsonpickle.encode(cached))
    monkeypatch.setattr(base, "redis_nodb_cache_client", cache, raising=False)

    _DummyNoDb.cleanup_run_instances(str(tmp_path))
    loaded = _DummyNoDb.getInstance(str(tmp_path))

    assert loaded.value == 31
    assert not cache.set_calls, "fresh cache hit should not force disk rehydrate"


def test_getinstance_disk_hydrate_populates_cache_with_reusable_signature(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.value = 47
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    class _CountingCache:
        def __init__(self) -> None:
            self.store: dict[str, str] = {}
            self.set_count = 0

        def get(self, key: str):
            return self.store.get(key)

        def set(self, key: str, value: str, *, ex=None, nx: bool = False):
            self.store[key] = value
            self.set_count += 1
            return True

        def delete(self, key: str):
            self.store.pop(key, None)
            return 1

    cache = _CountingCache()
    monkeypatch.setattr(base, "redis_nodb_cache_client", cache, raising=False)

    _DummyNoDb.cleanup_run_instances(str(tmp_path))
    first = _DummyNoDb.getInstance(str(tmp_path))
    assert first.value == 47
    assert cache.set_count == 1, "first load should hydrate disk and populate cache"

    _DummyNoDb.cleanup_run_instances(str(tmp_path))
    second = _DummyNoDb.getInstance(str(tmp_path))
    assert second.value == 47
    assert cache.set_count == 1, "second load should accept cache without disk rehydrate"


def test_locked_releases_lock_when_dump_fails_after_successful_context_body(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_db_api_stub(monkeypatch, update_last_modified=lambda *_args, **_kwargs: None)
    nodb = _DummyNoDb(str(tmp_path))

    def _raise_stale_dump(_self) -> None:
        raise base.NoDbStaleWriteError("stale-write")

    monkeypatch.setattr(_DummyNoDb, "dump", _raise_stale_dump)

    with pytest.raises(base.NoDbStaleWriteError):
        with nodb.locked():
            nodb.value = 9

    assert not nodb.islocked()


def test_dump_rejects_stale_overwrite_when_on_disk_payload_changed(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_db_api_stub(monkeypatch, update_last_modified=lambda *_args, **_kwargs: None)

    nodb = _DummyNoDb(str(tmp_path))
    nodb.lock()
    try:
        nodb.value = 1
        nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    nodb_path = tmp_path / nodb.filename
    nodb_path.write_text('{"external":"newer"}', encoding="utf-8")

    nodb.value = 2
    nodb.lock()
    try:
        with pytest.raises(base.NoDbStaleWriteError):
            nodb.dump()
    finally:
        nodb.unlock(flag="-f")

    assert nodb_path.read_text(encoding="utf-8") == '{"external":"newer"}'


def test_dump_forces_mtime_advance_on_unchanged_signature_then_rejects_stale_writer(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_db_api_stub(monkeypatch, update_last_modified=lambda *_args, **_kwargs: None)

    nodb_path = tmp_path / _DummyNoDb.filename
    writer = _DummyNoDb(str(tmp_path))
    _prime_stable_dummy_payload_signature(writer, value="A")

    stale_writer = _DummyNoDb.load_detached(str(tmp_path))
    assert stale_writer is not None
    stale_expected_mtime = stale_writer._nodb_mtime
    stale_expected_size = stale_writer._nodb_size
    assert stale_expected_mtime is not None
    assert stale_expected_size is not None

    real_fstat = base.os.fstat
    forced_signature_once = {"done": False}

    def _fstat_with_stale_signature(fd: int):
        stat_result = real_fstat(fd)
        if not forced_signature_once["done"]:
            forced_signature_once["done"] = True
            return types.SimpleNamespace(
                st_mtime=stale_expected_mtime,
                st_size=stale_expected_size,
                st_atime_ns=getattr(stat_result, "st_atime_ns", int(stale_expected_mtime * 1_000_000_000)),
            )
        return stat_result

    monkeypatch.setattr(base.os, "fstat", _fstat_with_stale_signature)

    writer.lock()
    try:
        writer.value = "A"
        writer.dump()
    finally:
        writer.unlock(flag="-f")

    refreshed_stat = nodb_path.stat()
    # Serialized payload width can drift when signature field text length changes.
    # The stale-write safety contract is the monotonic post-write mtime.
    assert refreshed_stat.st_mtime > stale_expected_mtime

    stale_writer.value = "C"
    stale_writer.lock()
    try:
        with pytest.raises(base.NoDbStaleWriteError):
            stale_writer.dump()
    finally:
        stale_writer.unlock(flag="-f")


def test_dump_raises_when_mtime_advance_attempt_fails(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_db_api_stub(monkeypatch, update_last_modified=lambda *_args, **_kwargs: None)

    writer = _DummyNoDb(str(tmp_path))
    _prime_stable_dummy_payload_signature(writer, value="A")

    expected_mtime = writer._nodb_mtime
    expected_size = writer._nodb_size
    assert expected_mtime is not None
    assert expected_size is not None

    real_fstat = base.os.fstat
    forced_signature_once = {"done": False}

    def _fstat_with_stale_signature(fd: int):
        stat_result = real_fstat(fd)
        if not forced_signature_once["done"]:
            forced_signature_once["done"] = True
            return types.SimpleNamespace(
                st_mtime=expected_mtime,
                st_size=expected_size,
                st_atime_ns=getattr(stat_result, "st_atime_ns", int(expected_mtime * 1_000_000_000)),
            )
        return stat_result

    def _raising_utime(_path, *, ns, follow_symlinks=True):  # noqa: ANN001 - signature matches os.utime usage
        raise OSError("utime unavailable")

    monkeypatch.setattr(base.os, "fstat", _fstat_with_stale_signature)
    monkeypatch.setattr(base.os, "utime", _raising_utime)

    writer.lock()
    try:
        writer.value = "A"
        with pytest.raises(base.NoDbStaleWriteError, match="deterministic mtime advance failed"):
            writer.dump()
    finally:
        writer.unlock(flag="-f")


def test_dump_forces_monotonic_signature_after_second_same_size_rewrite(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    disable_redis_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_db_api_stub(monkeypatch, update_last_modified=lambda *_args, **_kwargs: None)

    nodb_path = tmp_path / _DummyNoDb.filename
    writer = _DummyNoDb(str(tmp_path))
    _prime_stable_dummy_payload_signature(writer, value="A")

    stale_writer = _DummyNoDb.load_detached(str(tmp_path))
    assert stale_writer is not None
    stale_expected_mtime = stale_writer._nodb_mtime
    stale_expected_size = stale_writer._nodb_size
    assert stale_expected_mtime is not None
    assert stale_expected_size is not None

    real_fstat = base.os.fstat

    def _fstat_with_signature_once(signature_mtime: float, signature_size: int):
        state = {"done": False}

        def _inner(fd: int):
            stat_result = real_fstat(fd)
            if not state["done"]:
                state["done"] = True
                return types.SimpleNamespace(
                    st_mtime=signature_mtime,
                    st_size=signature_size,
                    st_atime_ns=getattr(stat_result, "st_atime_ns", int(signature_mtime * 1_000_000_000)),
                )
            return stat_result

        return _inner

    monkeypatch.setattr(
        base.os,
        "fstat",
        _fstat_with_signature_once(stale_expected_mtime, stale_expected_size),
    )
    writer.lock()
    try:
        writer.value = "A"
        writer.dump()
    finally:
        writer.unlock(flag="-f")

    first_rewrite_mtime = writer._nodb_mtime
    assert first_rewrite_mtime is not None

    monkeypatch.setattr(
        base.os,
        "fstat",
        _fstat_with_signature_once(stale_expected_mtime, stale_expected_size),
    )
    writer.lock()
    try:
        writer.value = "A"
        writer.dump()
    finally:
        writer.unlock(flag="-f")

    refreshed_stat = nodb_path.stat()
    # Serialized payload width can drift when signature field text length changes.
    # The stale-write safety contract is monotonic signature advancement.
    assert writer._nodb_mtime is not None
    assert writer._nodb_mtime > first_rewrite_mtime

    stale_writer.value = "D"
    stale_writer.lock()
    try:
        with pytest.raises(base.NoDbStaleWriteError):
            stale_writer.dump()
    finally:
        stale_writer.unlock(flag="-f")


def test_dump_cache_mirror_uses_post_write_signature(
    tmp_path: Path,
    redis_lock_stub: _RedisStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_db_api_stub(monkeypatch, update_last_modified=lambda *_args, **_kwargs: None)

    class _CacheRecorder:
        def __init__(self) -> None:
            self.payloads: list[str] = []

        def set(self, _key: str, value: str, *, ex=None, nx: bool = False):
            self.payloads.append(value)
            return True

    cache = _CacheRecorder()
    monkeypatch.setattr(base, "redis_nodb_cache_client", cache, raising=False)

    writer = _DummyNoDb(str(tmp_path))
    _prime_stable_dummy_payload_signature(writer, value="A")

    expected_mtime = writer._nodb_mtime
    expected_size = writer._nodb_size
    assert expected_mtime is not None
    assert expected_size is not None

    real_fstat = base.os.fstat
    forced_signature_once = {"done": False}

    def _fstat_with_stale_signature(fd: int):
        stat_result = real_fstat(fd)
        if not forced_signature_once["done"]:
            forced_signature_once["done"] = True
            return types.SimpleNamespace(
                st_mtime=expected_mtime,
                st_size=expected_size,
                st_atime_ns=getattr(stat_result, "st_atime_ns", int(expected_mtime * 1_000_000_000)),
            )
        return stat_result

    monkeypatch.setattr(base.os, "fstat", _fstat_with_stale_signature)

    writer.lock()
    try:
        writer.value = "A"
        writer.dump()
    finally:
        writer.unlock(flag="-f")

    assert cache.payloads, "expected Redis cache mirror writes"
    cached = base.jsonpickle.decode(cache.payloads[-1])
    assert cached._nodb_mtime == writer._nodb_mtime
    assert cached._nodb_size == writer._nodb_size
