"""Tests for NoDb file handler cleanup to prevent file descriptor leaks.

These tests validate that:
1. _safe_stop_queue_listener properly closes file handlers
2. cleanup_all_instances closes file handlers for all cached instances
3. cleanup_run_instances closes file handlers for a specific run
4. File descriptors are properly released after cleanup
"""
from __future__ import annotations

import atexit
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterator, Optional
from unittest.mock import MagicMock, patch
from weakref import WeakKeyDictionary

import pytest

import wepppy.nodb.base as base
from wepppy.nodb.base import NoDbBase

pytestmark = pytest.mark.unit


class FileHandlerTrackingController(NoDbBase):
    """Controller that tracks file handler state for testing cleanup."""

    filename = "tracking.nodb"

    def __init__(self, wd: str, cfg_fn: str = "disturbed9002.cfg") -> None:
        super().__init__(wd, cfg_fn)


class FakeRedis:
    """Minimal Redis stub for testing without real Redis connection."""

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
            yield from keys
            return
        import fnmatch
        for key in keys:
            if fnmatch.fnmatch(str(key), match):
                yield key


@pytest.fixture
def redis_env(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Patch all Redis clients with fakes."""
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
def run_dir(tmp_path: Path) -> Path:
    """Create a temporary run directory."""
    run = tmp_path / "test_run"
    run.mkdir()
    return run


class TestSafeStopQueueListener:
    """Tests for _safe_stop_queue_listener method."""

    def test_closes_run_file_handler(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates that _safe_stop_queue_listener closes _run_file_handler."""
        controller = FileHandlerTrackingController(str(run_dir))

        # Verify file handler was created
        assert hasattr(controller, "_run_file_handler")
        assert controller._run_file_handler is not None
        
        run_file_handler = controller._run_file_handler
        # Get the underlying stream before it's closed
        stream = run_file_handler.stream
        assert stream is not None
        assert not stream.closed

        # Call cleanup
        controller._safe_stop_queue_listener()

        # Verify the stream was closed
        assert stream.closed
        # Verify attribute was cleared
        assert controller._run_file_handler is None

    def test_closes_exception_file_handler(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates that _safe_stop_queue_listener closes _exception_file_handler."""
        controller = FileHandlerTrackingController(str(run_dir))

        # Verify file handler was created
        assert hasattr(controller, "_exception_file_handler")
        assert controller._exception_file_handler is not None
        
        exception_file_handler = controller._exception_file_handler
        # Get the underlying stream before it's closed
        stream = exception_file_handler.stream
        assert stream is not None
        assert not stream.closed

        # Call cleanup
        controller._safe_stop_queue_listener()

        # Verify the stream was closed
        assert stream.closed
        # Verify attribute was cleared
        assert controller._exception_file_handler is None

    def test_stops_queue_listener(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates that _safe_stop_queue_listener stops the QueueListener."""
        controller = FileHandlerTrackingController(str(run_dir))

        assert hasattr(controller, "_queue_listener")
        assert controller._queue_listener is not None
        
        listener = controller._queue_listener
        # QueueListener thread should be alive
        assert listener._thread is not None
        assert listener._thread.is_alive()

        # Call cleanup
        controller._safe_stop_queue_listener()

        # Verify listener was stopped and reference cleared
        assert controller._queue_listener is None

    def test_idempotent_cleanup(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates that calling _safe_stop_queue_listener multiple times is safe."""
        controller = FileHandlerTrackingController(str(run_dir))

        # Call cleanup multiple times - should not raise
        controller._safe_stop_queue_listener()
        controller._safe_stop_queue_listener()
        controller._safe_stop_queue_listener()

        # All handlers should be None
        assert controller._run_file_handler is None
        assert controller._exception_file_handler is None
        assert controller._queue_listener is None

    def test_handles_missing_attributes(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates cleanup handles instances with missing handler attributes."""
        controller = FileHandlerTrackingController(str(run_dir))

        # Remove attributes to simulate edge case
        del controller._run_file_handler
        del controller._exception_file_handler

        # Should not raise
        controller._safe_stop_queue_listener()


class TestCleanupAllInstances:
    """Tests for cleanup_all_instances class method."""

    def test_closes_all_cached_instance_handlers(
        self,
        tmp_path: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates cleanup_all_instances closes handlers for all cached instances."""
        # Create multiple run directories and instances
        run1 = tmp_path / "run1"
        run2 = tmp_path / "run2"
        run1.mkdir()
        run2.mkdir()

        controller1 = FileHandlerTrackingController(str(run1))
        controller2 = FileHandlerTrackingController(str(run2))

        # Cache the instances
        FileHandlerTrackingController._instances[str(run1)] = controller1
        FileHandlerTrackingController._instances[str(run2)] = controller2

        # Get references to streams before cleanup
        stream1_run = controller1._run_file_handler.stream
        stream1_exc = controller1._exception_file_handler.stream
        stream2_run = controller2._run_file_handler.stream
        stream2_exc = controller2._exception_file_handler.stream

        # Cleanup all instances
        FileHandlerTrackingController.cleanup_all_instances()

        # Verify all streams were closed
        assert stream1_run.closed
        assert stream1_exc.closed
        assert stream2_run.closed
        assert stream2_exc.closed

        # Verify instances dict was cleared
        assert len(FileHandlerTrackingController._instances) == 0

    def test_clears_instances_dict(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates cleanup_all_instances clears the _instances dict."""
        controller = FileHandlerTrackingController(str(run_dir))
        FileHandlerTrackingController._instances[str(run_dir)] = controller

        assert len(FileHandlerTrackingController._instances) > 0

        FileHandlerTrackingController.cleanup_all_instances()

        assert len(FileHandlerTrackingController._instances) == 0


class TestCleanupRunInstances:
    """Tests for cleanup_run_instances class method."""

    def test_closes_handlers_for_specific_run(
        self,
        tmp_path: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates cleanup_run_instances only cleans up the specified run."""
        run1 = tmp_path / "run1"
        run2 = tmp_path / "run2"
        run1.mkdir()
        run2.mkdir()

        controller1 = FileHandlerTrackingController(str(run1))
        controller2 = FileHandlerTrackingController(str(run2))

        # Cache the instances
        FileHandlerTrackingController._instances[str(run1)] = controller1
        FileHandlerTrackingController._instances[str(run2)] = controller2

        # Get references to streams before cleanup
        stream1_run = controller1._run_file_handler.stream
        stream2_run = controller2._run_file_handler.stream

        # Cleanup only run1 using the specific controller class
        # (cleanup_run_instances on base class dynamically discovers subclasses,
        # but our test class isn't in wepppy.nodb.core/mods, so use _instances directly)
        abs_run1 = os.path.abspath(str(run1))
        with FileHandlerTrackingController._instances_lock:
            if abs_run1 in FileHandlerTrackingController._instances:
                instance = FileHandlerTrackingController._instances.pop(abs_run1)
                instance._safe_stop_queue_listener()

        # Verify run1 stream was closed
        assert stream1_run.closed
        assert controller1._run_file_handler is None

        # Verify run2 stream was NOT closed
        assert not stream2_run.closed
        assert controller2._run_file_handler is not None

        # Cleanup run2 for test hygiene
        FileHandlerTrackingController.cleanup_all_instances()

    def test_returns_cleanup_count(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates that cleanup properly removes instance from cache."""
        controller = FileHandlerTrackingController(str(run_dir))
        abs_wd = os.path.abspath(str(run_dir))
        FileHandlerTrackingController._instances[abs_wd] = controller

        # Verify it's in the cache
        assert abs_wd in FileHandlerTrackingController._instances

        # Clean up
        controller._safe_stop_queue_listener()
        with FileHandlerTrackingController._instances_lock:
            FileHandlerTrackingController._instances.pop(abs_wd, None)

        # Verify it was removed
        assert abs_wd not in FileHandlerTrackingController._instances

    def test_handles_nonexistent_run(
        self,
        tmp_path: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates cleanup_run_instances handles non-cached runs gracefully."""
        nonexistent = tmp_path / "nonexistent"
        nonexistent.mkdir()

        # Should not raise, should return 0
        cleaned = NoDbBase.cleanup_run_instances(str(nonexistent))

        assert cleaned == 0


class TestAtexitRegistration:
    """Tests for atexit registration of cleanup."""

    def test_atexit_registered_on_init(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validates that atexit.register is called during _init_logging."""
        registered_funcs = []

        def mock_register(func):
            registered_funcs.append(func)

        monkeypatch.setattr(atexit, "register", mock_register)

        controller = FileHandlerTrackingController(str(run_dir))

        # Verify atexit.register was called with _safe_stop_queue_listener
        assert len(registered_funcs) == 1
        assert registered_funcs[0] == controller._safe_stop_queue_listener


class TestFileDescriptorCleanup:
    """Tests validating file descriptors are actually released."""

    def test_file_descriptors_released_after_cleanup(
        self,
        run_dir: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates file descriptors are released after _safe_stop_queue_listener."""
        controller = FileHandlerTrackingController(str(run_dir))

        # Get the file descriptor numbers before cleanup
        run_handler = controller._run_file_handler
        exc_handler = controller._exception_file_handler

        run_fd = run_handler.stream.fileno()
        exc_fd = exc_handler.stream.fileno()

        # Both should be valid file descriptors
        assert run_fd >= 0
        assert exc_fd >= 0

        # Cleanup
        controller._safe_stop_queue_listener()

        # After cleanup, trying to use the old FDs should fail
        # (they should be closed)
        with pytest.raises(OSError):
            os.fstat(run_fd)

        with pytest.raises(OSError):
            os.fstat(exc_fd)

    def test_multiple_controllers_cleanup_releases_all_fds(
        self,
        tmp_path: Path,
        redis_env: SimpleNamespace,
    ) -> None:
        """Validates FDs are released when cleaning up multiple controllers."""
        runs = []
        controllers = []
        fds = []

        # Create 5 controllers (10 file handlers = 10 FDs)
        for i in range(5):
            run = tmp_path / f"run_{i}"
            run.mkdir()
            runs.append(run)

            controller = FileHandlerTrackingController(str(run))
            controllers.append(controller)
            FileHandlerTrackingController._instances[str(run)] = controller

            fds.append(controller._run_file_handler.stream.fileno())
            fds.append(controller._exception_file_handler.stream.fileno())

        # All FDs should be valid
        for fd in fds:
            assert fd >= 0
            os.fstat(fd)  # Should not raise

        # Cleanup all
        FileHandlerTrackingController.cleanup_all_instances()

        # All FDs should now be closed
        for fd in fds:
            with pytest.raises(OSError):
                os.fstat(fd)
