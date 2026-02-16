from __future__ import annotations

import threading
import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.state import archive_fingerprint_from_path, read_state, write_state
from wepppy.nodir.thaw_freeze import freeze, maintenance_lock_key, thaw

pytestmark = pytest.mark.unit


class _RedisLockStub:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):  # noqa: ARG002
        with self._lock:
            if nx and key in self._store:
                return False
            self._store[key] = value
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


def test_thaw_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", lock_stub)

    state_payload = thaw(str(wd), "watershed")

    assert state_payload["state"] == "thawed"
    assert state_payload["dirty"] is True
    assert (wd / "watershed" / "hillslopes" / "h001.slp").read_text(encoding="utf-8") == "alpha"
    assert not (wd / "watershed.thaw.tmp").exists()

    persisted = read_state(wd, "watershed")
    assert persisted is not None
    assert persisted["state"] == "thawed"

    assert lock_stub.get(maintenance_lock_key(wd, "watershed")) is None


def test_thaw_rejects_duplicate_archive_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dup.txt", b"first")
        zf.writestr("dup.txt", b"second")

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())

    with pytest.raises(NoDirError) as exc:
        thaw(str(wd), "watershed")

    assert exc.value.http_status == 500
    assert exc.value.code == "NODIR_INVALID_ARCHIVE"
    assert not (wd / "watershed").exists()


def test_thaw_rejects_archive_file_dir_prefix_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a", b"root-file")
        zf.writestr("a/b.txt", b"nested")

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())

    with pytest.raises(NoDirError) as exc:
        thaw(str(wd), "watershed")

    assert exc.value.http_status == 500
    assert exc.value.code == "NODIR_INVALID_ARCHIVE"
    assert not (wd / "watershed").exists()


def test_freeze_happy_path_moves_sidecar_and_removes_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    root = wd / "watershed"
    root.mkdir(parents=True, exist_ok=False)
    (root / "hillslopes").mkdir(parents=True, exist_ok=False)
    (root / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")
    (root / "hillslopes.parquet").write_bytes(b"parquet-bytes")

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())

    state_payload = freeze(str(wd), "watershed")

    assert state_payload["state"] == "archived"
    assert state_payload["dirty"] is False
    assert not root.exists()
    assert (wd / "watershed.nodir").exists()
    assert (wd / "watershed.hillslopes.parquet").read_bytes() == b"parquet-bytes"

    with zipfile.ZipFile(wd / "watershed.nodir", "r") as zf:
        names = set(zf.namelist())
        assert "hillslopes/h001.slp" in names
        assert "hillslopes.parquet" not in names

    persisted = read_state(wd, "watershed")
    assert persisted is not None
    assert persisted["state"] == "archived"


def test_freeze_moves_uppercase_parquet_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    root = wd / "watershed"
    root.mkdir(parents=True, exist_ok=False)
    (root / "hillslopes").mkdir(parents=True, exist_ok=False)
    (root / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")
    (root / "hillslopes.PARQUET").write_bytes(b"upper-parquet")

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())

    freeze(str(wd), "watershed")

    assert (wd / "watershed.hillslopes.parquet").read_bytes() == b"upper-parquet"

    with zipfile.ZipFile(wd / "watershed.nodir", "r") as zf:
        names = zf.namelist()
        assert all(not name.casefold().endswith(".parquet") for name in names)


def test_thaw_recovers_stale_thaw_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"fresh.txt": "fresh"})

    stale_tmp = wd / "watershed.thaw.tmp"
    stale_tmp.mkdir(parents=True, exist_ok=False)
    (stale_tmp / "stale.txt").write_text("stale", encoding="utf-8")

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())

    thaw(str(wd), "watershed")

    assert (wd / "watershed" / "fresh.txt").read_text(encoding="utf-8") == "fresh"
    assert not (wd / "watershed" / "stale.txt").exists()
    assert not stale_tmp.exists()


def test_freeze_recovers_stale_nodir_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    root = wd / "watershed"
    root.mkdir(parents=True, exist_ok=False)
    (root / "a.txt").write_text("hello", encoding="utf-8")

    stale_tmp = wd / "watershed.nodir.tmp"
    stale_tmp.write_bytes(b"stale-archive")

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())

    freeze(str(wd), "watershed")

    assert not stale_tmp.exists()
    with zipfile.ZipFile(wd / "watershed.nodir", "r") as zf:
        assert zf.read("a.txt") == b"hello"


def test_freeze_recovers_missing_dir_when_state_is_freezing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    archive_path = wd / "watershed.nodir"
    _write_zip(archive_path, {"a.txt": "hello"})

    write_state(
        wd,
        "watershed",
        state="freezing",
        op_id="00000000-0000-4000-8000-000000000031",
        dirty=True,
        archive_fingerprint=archive_fingerprint_from_path(archive_path),
    )

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())

    payload = freeze(str(wd), "watershed")

    assert payload["state"] == "archived"
    assert payload["dirty"] is False

    persisted = read_state(wd, "watershed")
    assert persisted is not None
    assert persisted["state"] == "archived"
    assert persisted["dirty"] is False


def test_maintenance_lock_contention_fails_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "hello"})

    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    lock_stub = _RedisLockStub()
    lock_stub.force_set(maintenance_lock_key(wd, "watershed"), "held-by-other")
    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", lock_stub)

    with pytest.raises(NoDirError) as exc:
        thaw(str(wd), "watershed")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"
