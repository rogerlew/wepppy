from __future__ import annotations

import fnmatch
import logging
from queue import Empty
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterator, Optional
from weakref import WeakKeyDictionary

import pytest

import wepppy.nodb.base as base
from wepppy.nodb.base import (
    NoDbAlreadyLockedError,
    NoDbBase,
    clear_locks,
    clear_nodb_file_cache,
    lock_statuses,
)

pytestmark = pytest.mark.unit


class DummyController(NoDbBase):
    filename = "dummy.nodb"

    def __init__(self, wd: str, cfg_fn: str = "disturbed9002.cfg") -> None:
        super().__init__(wd, cfg_fn)
        self.values: Dict[str, Any] = {}

    def _init_logging(self) -> None:  # noqa: D401 - simplified logging hook
        logger_name = f"tests.nodb.dummy.{id(self)}"
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        self.logger = logger
        self.runid_logger = logger


class LoggingController(NoDbBase):
    filename = "logging.nodb"

    def __init__(self, wd: str, cfg_fn: str = "disturbed9002.cfg") -> None:
        super().__init__(wd, cfg_fn)


class FakeRedis:
    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}
        self.hashes: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any, *args: Any, **kwargs: Any) -> bool:
        nx = kwargs.get("nx", False)
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def get(self, key: str) -> Optional[Any]:
        return self.store.get(key)

    def delete(self, key: str) -> int:
        existed = key in self.store
        self.store.pop(key, None)
        return int(existed)

    def hset(self, name: str, key: str, value: Any) -> int:
        bucket = self.hashes.setdefault(name, {})
        bucket[key] = value
        return 1

    def hget(self, name: str, key: str) -> Optional[Any]:
        return self.hashes.get(name, {}).get(key)

    def hgetall(self, name: str) -> Dict[str, Any]:
        return dict(self.hashes.get(name, {}))

    def scan_iter(self, match: Optional[str] = None) -> Iterator[str]:
        keys = list(self.store.keys())
        if match is None:
            for key in keys:
                yield key
            return
        for key in keys:
            if fnmatch.fnmatch(str(key), match):
                yield key


@pytest.fixture
def redis_env(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    lock = FakeRedis()
    cache = FakeRedis()
    status = FakeRedis()
    log_level = FakeRedis()

    monkeypatch.setattr(base, "redis_lock_client", lock, raising=False)
    monkeypatch.setattr(base, "redis_nodb_cache_client", cache, raising=False)
    monkeypatch.setattr(base, "redis_status_client", status, raising=False)
    monkeypatch.setattr(base, "redis_log_level_client", log_level, raising=False)
    monkeypatch.setattr(base, "_ACTIVE_LOCK_TOKENS", WeakKeyDictionary(), raising=False)

    return SimpleNamespace(lock=lock, cache=cache, status=status, log_level=log_level)


@pytest.fixture
def controller(tmp_path: Path, redis_env: SimpleNamespace) -> DummyController:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    instance = DummyController(str(run_dir))
    yield instance
    try:
        instance.unlock(flag="-f")
    except Exception:
        pass


@pytest.fixture
def logging_controller(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    redis_env: SimpleNamespace,
    request: pytest.FixtureRequest,
) -> tuple[LoggingController, SimpleNamespace]:
    state = SimpleNamespace(messages=[], handler=None, listener=None)

    class StubStatusMessengerHandler(logging.Handler):
        def __init__(self, channel: str) -> None:
            super().__init__()
            self.channel = channel
            state.handler = self

        def emit(self, record: logging.LogRecord) -> None:
            state.messages.append(record.getMessage())

    class StubQueueListener:
        def __init__(self, queue_obj, *handlers) -> None:
            self.queue = queue_obj
            self.handlers = handlers
            self.started = False
            state.listener = self

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.started = False

    monkeypatch.setattr(base, "StatusMessengerHandler", StubStatusMessengerHandler, raising=False)
    monkeypatch.setattr(base, "QueueListener", StubQueueListener, raising=False)

    run_dir = tmp_path / f"{request.node.name}-logging"
    run_dir.mkdir()
    instance = LoggingController(str(run_dir))

    yield instance, state

    listener = state.listener
    if listener is not None:
        listener.stop()

    for handler in list(instance.logger.handlers):
        instance.logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    runid_logger = logging.getLogger(f"wepppy.run.{instance.runid}")
    for handler in list(runid_logger.handlers):
        runid_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass


def _patch_get_wd(monkeypatch: pytest.MonkeyPatch, runid: str, target: Path) -> None:
    import wepppy.weppcloud.utils.helpers as helpers

    original_get_wd = helpers.get_wd

    def _fake_get_wd(requested: str, *, prefer_active: bool = True) -> str:
        if requested == runid:
            return str(target)
        return original_get_wd(requested, prefer_active=prefer_active)

    monkeypatch.setattr(helpers, "get_wd", _fake_get_wd)


def test_locked_context_round_trip(controller: DummyController, redis_env: SimpleNamespace) -> None:
    """Ensures lock context persists data to disk and Redis cache."""
    with controller.locked():
        controller.values["answer"] = 42

    assert not controller.islocked()
    nodb_path = Path(controller._nodb)
    assert nodb_path.exists()
    assert redis_env.cache.get(str(nodb_path)) is not None

    reloaded = DummyController.getInstance(controller.wd)
    assert reloaded.values == {"answer": 42}


def test_lock_conflict_raises(controller: DummyController) -> None:
    """Validates that a second lock attempt raises when already locked."""
    controller.lock()
    try:
        with pytest.raises(NoDbAlreadyLockedError):
            controller.lock()
    finally:
        controller.unlock(flag="-f")


def test_unlock_requires_matching_token(controller: DummyController) -> None:
    """Requires the local token to match the stored token during unlock."""
    controller.lock()
    try:
        base._set_local_lock_token(controller, None)
        with pytest.raises(RuntimeError):
            controller.unlock()
    finally:
        controller.unlock(flag="-f")


def test_clear_locks_resets_state(controller: DummyController, redis_env: SimpleNamespace) -> None:
    """Confirms clear_locks releases distributed keys and reset flags."""
    controller.lock()
    try:
        cleared = clear_locks(controller.runid)
        expected_field = f"locked:{controller._rel_nodb}"
        assert expected_field in cleared
        assert redis_env.lock.get(controller._distributed_lock_key) is None
        assert not controller.islocked()
    finally:
        base._set_local_lock_token(controller, None)


def test_lock_statuses_normalizes_legacy_flags(controller: DummyController, redis_env: SimpleNamespace) -> None:
    """Normalizes legacy hash entries when distributed locks are absent."""
    controller.lock()
    try:
        redis_env.lock.hset(controller.runid, "locked:stale.nodb", "true")
        statuses = lock_statuses(controller.runid)
        assert statuses[controller._rel_nodb] is True
        assert statuses["stale.nodb"] is False
        assert redis_env.lock.hget(controller.runid, "locked:stale.nodb") == "false"
    finally:
        controller.unlock(flag="-f")


def test_clear_nodb_file_cache_removes_cached_entries(
    controller: DummyController,
    redis_env: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures cache entries and filesystem artifacts clear for a run."""
    runid = controller.runid
    _patch_get_wd(monkeypatch, runid, Path(controller.wd))

    with controller.locked():
        controller.values["cached"] = True

    nodb_path = Path(controller._nodb)
    cache_key = str(nodb_path)
    assert cache_key in redis_env.cache.store

    cleared = clear_nodb_file_cache(runid)
    assert Path("dummy.nodb") in cleared
    assert cache_key not in redis_env.cache.store


def test_clear_nodb_file_cache_scoped_to_pup(
    controller: DummyController,
    redis_env: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scopes cache clearing to the requested pup subtree."""
    run_root = Path(controller.wd)
    runid = controller.runid
    _patch_get_wd(monkeypatch, runid, run_root)

    top_key = str(run_root / "top.nodb")
    redis_env.cache.set(top_key, "top-cache")

    pups_dir = run_root / "_pups" / "child"
    pups_dir.mkdir(parents=True)
    child_path = pups_dir / "dummy.nodb"
    child_path.write_text("stub", encoding="ascii")
    redis_env.cache.set(str(child_path), "child-cache")

    cleared = clear_nodb_file_cache(runid, pup_relpath="_pups/child")
    assert Path("_pups/child/dummy.nodb") in cleared
    assert top_key in redis_env.cache.store
    assert str(child_path) not in redis_env.cache.store


def test_init_logging_sets_up_queue_listener(
    logging_controller: tuple[LoggingController, SimpleNamespace]
) -> None:
    """Validates _init_logging wires queue listener and status handler for a run."""
    controller, state = logging_controller
    listener = state.listener
    handler = state.handler

    assert listener is not None
    assert handler is not None
    assert listener.started is True
    assert handler.channel == f"{controller.runid}:{controller.class_name}"

    log_path = Path(controller._nodb.replace(".nodb", ".log"))

    assert log_path.exists()


def test_logging_pipeline_flushes_to_status_handler(
    logging_controller: tuple[LoggingController, SimpleNamespace]
) -> None:
    """Ensures log records dequeued by listeners reach the messenger handler."""
    controller, state = logging_controller
    listener = state.listener
    assert listener is not None

    controller.logger.info("status update")

    try:
        record = listener.queue.get(timeout=0.1)
    except Empty:
        pytest.fail("Log record was not enqueued")

    for handler in listener.handlers:
        handler.handle(record)

    assert "status update" in state.messages
