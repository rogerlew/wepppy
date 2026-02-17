from __future__ import annotations

import threading
import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.mutations import mutate_root, mutate_roots
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


def _write_zip(path: Path, entries: dict[str, bytes | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            zf.writestr(name, data)


def test_mutate_root_dir_form_runs_callback_without_thaw(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", lock_stub)

    called = {"value": False}

    def _callback() -> str:
        called["value"] = True
        return "ok"

    result = mutate_root(wd, "watershed", _callback, purpose="test-dir-form")

    assert result == "ok"
    assert called["value"] is True
    assert lock_stub.get(maintenance_lock_key(wd, "watershed")) is None


def test_mutate_root_archive_form_thaws_runs_and_freezes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", lock_stub)

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

    state = read_state(wd, "watershed")
    assert state is not None
    assert state["state"] == "archived"
    assert state["dirty"] is False


def test_mutate_root_failure_after_thaw_preserves_thawed_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", lock_stub)

    def _callback() -> None:
        (wd / "watershed" / "hillslopes" / "h002.slp").write_text("beta", encoding="utf-8")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        mutate_root(wd, "watershed", _callback, purpose="test-failure")

    assert (wd / "watershed").exists()
    assert (wd / "watershed.nodir").exists()

    state = read_state(wd, "watershed")
    assert state is not None
    assert state["state"] == "thawed"
    assert state["dirty"] is True


def test_mutate_root_mixed_state_fails_fast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    (wd / "watershed").mkdir(parents=True, exist_ok=False)
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())

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

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", lock_stub)

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
