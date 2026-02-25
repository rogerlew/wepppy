from __future__ import annotations

import threading
import time
import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.mutations import (
    default_archive_roots_path,
    enable_default_archive_roots,
    mutate_root,
    mutate_roots,
)
from wepppy.nodir.state import read_state
from wepppy.nodir.thaw_freeze import maintenance_lock_key

pytestmark = pytest.mark.unit


class _RedisLockStub:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._history: list[str] = []
        self._lock = threading.Lock()

    @property
    def history(self) -> list[str]:
        with self._lock:
            return list(self._history)

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):  # noqa: ARG002
        with self._lock:
            if nx and key in self._store:
                return False
            self._store[key] = value
            self._history.append(key)
            return True

    def get(self, key: str):
        with self._lock:
            return self._store.get(key)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)
            return 1

    def eval(self, script: str, numkeys: int, key: str, *args):  # noqa: ARG002
        expected = str(args[0]) if args else ""
        with self._lock:
            current = self._store.get(key)
            if "redis.call('del', KEYS[1])" in script:
                if current == expected:
                    self._store.pop(key, None)
                    return 1
                return 0
        raise AssertionError(f"unexpected eval script: {script}")

    def force_set(self, key: str, value: str) -> None:
        with self._lock:
            self._store[key] = value


def _write_zip(path: Path, entries: dict[str, bytes | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            zf.writestr(name, data)


def _patch_lock_clients(monkeypatch: pytest.MonkeyPatch, lock_stub: _RedisLockStub) -> None:
    import wepppy.nodir.projections as projections_mod
    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", lock_stub)
    monkeypatch.setattr(projections_mod, "redis_lock_client", lock_stub)


def test_mutate_root_dir_form_runs_callback_without_thaw(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    called = {"value": False}

    def _callback() -> str:
        called["value"] = True
        return "ok"

    result = mutate_root(wd, "watershed", _callback, purpose="test-dir-form")

    assert result == "ok"
    assert called["value"] is True
    assert lock_stub.get(maintenance_lock_key(wd, "watershed")) is None


def test_mutate_root_dir_form_keeps_directory_without_default_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    def _callback() -> str:
        (wd / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
        (wd / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")
        return "ok"

    result = mutate_root(wd, "watershed", _callback, purpose="test-dir-form-dir")

    assert result == "ok"
    assert (wd / "watershed").exists()
    assert not (wd / "watershed.nodir").exists()


def test_mutate_root_default_archive_roots_freezes_dir_form(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)
    enable_default_archive_roots(wd, roots=("watershed",))

    def _callback() -> str:
        (wd / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
        (wd / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")
        return "done"

    result = mutate_root(wd, "watershed", _callback, purpose="test-default-nodir")

    assert result == "done"
    assert not (wd / "watershed").exists()
    assert (wd / "watershed.nodir").exists()
    with zipfile.ZipFile(wd / "watershed.nodir", "r") as zf:
        assert "hillslopes/h001.slp" in set(zf.namelist())

    state = read_state(wd, "watershed")
    assert state is not None
    assert state["state"] == "archived"
    assert state["dirty"] is False


def test_mutate_root_default_archive_roots_skips_missing_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)
    enable_default_archive_roots(wd, roots=("watershed",))

    result = mutate_root(
        wd,
        "watershed",
        lambda: "done",
        purpose="test-default-nodir-missing-root",
    )

    assert result == "done"
    assert not (wd / "watershed").exists()
    assert not (wd / "watershed.nodir").exists()
    assert read_state(wd, "watershed") is None


def test_mutate_root_malformed_default_archive_marker_fails_fast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    marker_path = default_archive_roots_path(wd)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("{broken-json", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid NoDir defaults marker"):
        mutate_root(wd, "watershed", lambda: None, purpose="test-default-marker-invalid")


def test_mutate_root_archive_form_uses_projection_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    def _callback() -> str:
        assert (wd / "watershed" / "hillslopes" / "h001.slp").exists()
        (wd / "watershed" / "hillslopes" / "h002.slp").write_text("beta", encoding="utf-8")
        return "done"

    result = mutate_root(wd, "watershed", _callback, purpose="test-archive-form")

    assert result == "done"
    assert not (wd / "watershed").exists()
    assert (wd / "watershed.nodir").exists()
    with zipfile.ZipFile(wd / "watershed.nodir", "r") as zf:
        assert set(zf.namelist()) >= {"hillslopes/h001.slp", "hillslopes/h002.slp"}


def test_mutate_root_failure_aborts_projection_without_thawed_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    def _callback() -> None:
        (wd / "watershed" / "hillslopes" / "h002.slp").write_text("beta", encoding="utf-8")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        mutate_root(wd, "watershed", _callback, purpose="test-failure")

    assert not (wd / "watershed").exists()
    assert (wd / "watershed.nodir").exists()
    with zipfile.ZipFile(wd / "watershed.nodir", "r") as zf:
        names = set(zf.namelist())
        assert "hillslopes/h001.slp" in names
        assert "hillslopes/h002.slp" not in names

    assert read_state(wd, "watershed") is None


def test_mutate_root_mixed_state_fails_fast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    (wd / "watershed").mkdir(parents=True, exist_ok=False)
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    with pytest.raises(NoDirError) as exc:
        mutate_root(wd, "watershed", lambda: None, purpose="test-mixed")

    assert exc.value.http_status == 409
    assert exc.value.code == "NODIR_MIXED_STATE"


def test_mutate_roots_acquires_locks_in_sorted_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "landuse.nodir", {"nlcd.tif": "a"})
    _write_zip(wd / "soils.nodir", {"soilscov.asc": "b"})

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    def _callback() -> str:
        (wd / "landuse" / "new.txt").write_text("x", encoding="utf-8")
        (wd / "soils" / "new.txt").write_text("y", encoding="utf-8")
        return "ok"

    result = mutate_roots(
        wd,
        ("soils", "landuse"),
        _callback,
        purpose="test-multi",
    )

    assert result == "ok"
    assert not (wd / "landuse").exists()
    assert not (wd / "soils").exists()

    expected_prefix = [
        maintenance_lock_key(wd, "landuse"),
        maintenance_lock_key(wd, "soils"),
    ]
    assert lock_stub.history[:2] == expected_prefix


def test_mutate_root_waits_for_transient_lock_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    key = maintenance_lock_key(wd, "watershed")
    lock_stub.force_set(key, "held-by-peer")

    def _release_lock() -> None:
        time.sleep(0.05)
        lock_stub.delete(key)

    releaser = threading.Thread(target=_release_lock)
    releaser.start()
    try:
        result = mutate_root(
            wd,
            "watershed",
            lambda: "ok",
            purpose="test-lock-wait-success",
            lock_wait_seconds=1.0,
            lock_retry_interval_seconds=0.01,
        )
    finally:
        releaser.join(timeout=1.0)

    assert result == "ok"
    assert lock_stub.get(key) is None


def test_mutate_root_lock_wait_timeout_raises_nodir_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path

    lock_stub = _RedisLockStub()
    _patch_lock_clients(monkeypatch, lock_stub)

    key = maintenance_lock_key(wd, "watershed")
    lock_stub.force_set(key, "held-by-peer")

    with pytest.raises(NoDirError) as exc:
        mutate_root(
            wd,
            "watershed",
            lambda: "ok",
            purpose="test-lock-wait-timeout",
            lock_wait_seconds=0.05,
            lock_retry_interval_seconds=0.01,
        )

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"
