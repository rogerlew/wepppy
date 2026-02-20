from __future__ import annotations

import json
import threading
import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.projections import (
    abort_mutation_projection,
    acquire_root_projection,
    commit_mutation_projection,
    release_root_projection,
    with_root_projection,
)

pytestmark = pytest.mark.unit


class _RedisLockStub:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._fail_get_keys: set[str] = set()
        self._mutex = threading.Lock()

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):  # noqa: ARG002
        with self._mutex:
            if nx and key in self._store:
                return False
            self._store[key] = value
            return True

    def get(self, key: str):
        with self._mutex:
            if key in self._fail_get_keys:
                raise RuntimeError("simulated redis get failure")
            return self._store.get(key)

    def delete(self, key: str):
        with self._mutex:
            self._store.pop(key, None)
            return 1

    def eval(self, script: str, numkeys: int, key: str, *args):  # noqa: ARG002
        expected = str(args[0]) if args else ""
        with self._mutex:
            current = self._store.get(key)
            if "redis.call('del', KEYS[1])" in script:
                if current == expected:
                    self._store.pop(key, None)
                    return 1
                return 0
        raise AssertionError(f"unexpected eval script: {script}")

    def force_set(self, key: str, value: str) -> None:
        with self._mutex:
            self._store[key] = value

    def fail_get_for(self, key: str) -> None:
        with self._mutex:
            self._fail_get_keys.add(key)


def _write_zip(path: Path, entries: dict[str, bytes | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            zf.writestr(name, data)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_read_projection_reuses_session_and_refcount(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    first = acquire_root_projection(wd, "watershed", mode="read", purpose="test-read")
    second = acquire_root_projection(wd, "watershed", mode="read", purpose="test-read")

    mount_path = Path(first.mount_path)
    assert mount_path.is_symlink()
    assert (mount_path / "a.txt").read_text(encoding="utf-8") == "alpha"

    meta = _read_json(Path(first.metadata_path))
    assert int(meta["refcount"]) == 2

    release_root_projection(second)
    meta = _read_json(Path(first.metadata_path))
    assert int(meta["refcount"]) == 1

    release_root_projection(first)
    assert not mount_path.exists()
    assert not Path(first.metadata_path).exists()


def test_with_root_projection_releases_on_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    with with_root_projection(wd, "watershed", mode="read", purpose="ctx") as handle:
        assert (Path(handle.mount_path) / "a.txt").read_text(encoding="utf-8") == "alpha"
        metadata_path = Path(handle.metadata_path)
        assert metadata_path.exists()

    assert not Path(handle.mount_path).exists()
    assert not metadata_path.exists()


def test_projection_lock_contention_without_metadata_returns_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(projections_mod, "redis_lock_client", lock_stub)

    probe = acquire_root_projection(wd, "watershed", mode="read", purpose="probe")
    lock_stub.force_set(probe.lock_key, "held-by-other")
    Path(probe.metadata_path).unlink(missing_ok=True)

    with pytest.raises(NoDirError) as exc:
        acquire_root_projection(wd, "watershed", mode="read", purpose="blocked")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"

    release_root_projection(probe)


def test_projection_explicit_none_override_disables_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr("wepppy.nodb.base.redis_lock_client", _RedisLockStub(), raising=False)
    monkeypatch.setattr(projections_mod, "redis_lock_client", None)

    with pytest.raises(NoDirError) as exc:
        projections_mod._acquire_lock("nodb-lock:test:key", purpose="unit-test")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"


def test_projection_rejects_unmanaged_mixed_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    (wd / "watershed").mkdir(parents=True, exist_ok=True)
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    with pytest.raises(NoDirError) as exc:
        acquire_root_projection(wd, "watershed", mode="read", purpose="mixed")

    assert exc.value.http_status == 409
    assert exc.value.code == "NODIR_MIXED_STATE"


def test_projection_preserves_invalid_archive_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    (wd / "watershed.nodir").write_bytes(b"not-a-zip")

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    with pytest.raises(NoDirError) as exc:
        acquire_root_projection(wd, "watershed", mode="read", purpose="invalid")

    assert exc.value.http_status == 500
    assert exc.value.code == "NODIR_INVALID_ARCHIVE"


def test_projection_preserves_transition_lock_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})
    (wd / "watershed.thaw.tmp").mkdir(parents=True, exist_ok=False)

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    with pytest.raises(NoDirError) as exc:
        acquire_root_projection(wd, "watershed", mode="read", purpose="locked")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"


def test_mutation_projection_commit_updates_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    handle = acquire_root_projection(wd, "watershed", mode="mutate", purpose="mutate")
    mount = Path(handle.mount_path)
    (mount / "b.txt").write_text("beta", encoding="utf-8")

    commit_mutation_projection(handle)
    release_root_projection(handle)

    with zipfile.ZipFile(wd / "watershed.nodir", "r") as zf:
        assert zf.read("a.txt") == b"alpha"
        assert zf.read("b.txt") == b"beta"


def test_mutation_projection_abort_discards_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    handle = acquire_root_projection(wd, "watershed", mode="mutate", purpose="mutate-abort")
    mount = Path(handle.mount_path)
    (mount / "b.txt").write_text("beta", encoding="utf-8")

    abort_mutation_projection(handle)
    release_root_projection(handle)

    with zipfile.ZipFile(wd / "watershed.nodir", "r") as zf:
        names = set(zf.namelist())
        assert "a.txt" in names
        assert "b.txt" not in names


def test_projection_acquire_sweeps_stale_metadata_and_orphan_mount(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(projections_mod, "redis_lock_client", lock_stub)

    stale_lower = wd / ".nodir" / "lower" / "watershed" / "1-1" / "data"
    stale_lower.mkdir(parents=True, exist_ok=True)
    mount_path = wd / "watershed"
    mount_path.symlink_to(stale_lower, target_is_directory=True)

    stale_meta = wd / ".nodir" / "projections" / "watershed" / "1-1" / "read.json"
    stale_meta.parent.mkdir(parents=True, exist_ok=True)
    stale_meta.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "root": "watershed",
                "mode": "read",
                "mount_path": str(mount_path),
                "lock_key": "nodb-lock:stale:key",
                "lock_value": "stale-value",
                "lower_path": str(stale_lower),
                "upper_path": None,
                "work_path": None,
            }
        ),
        encoding="utf-8",
    )

    handle = acquire_root_projection(wd, "watershed", mode="read", purpose="sweep")
    assert not stale_meta.exists()
    assert Path(handle.mount_path).is_symlink()
    assert (Path(handle.mount_path) / "a.txt").read_text(encoding="utf-8") == "alpha"

    release_root_projection(handle)


def test_projection_cross_mode_conflict_returns_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    mutate_handle = acquire_root_projection(wd, "watershed", mode="mutate", purpose="mutate")
    try:
        with pytest.raises(NoDirError) as exc:
            acquire_root_projection(wd, "watershed", mode="read", purpose="read")

        assert exc.value.http_status == 503
        assert exc.value.code == "NODIR_LOCKED"
    finally:
        abort_mutation_projection(mutate_handle)
        release_root_projection(mutate_handle)


def test_release_projection_is_token_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    first = acquire_root_projection(wd, "watershed", mode="read", purpose="one")
    second = acquire_root_projection(wd, "watershed", mode="read", purpose="two")

    release_root_projection(first)
    release_root_projection(first)

    metadata = _read_json(Path(second.metadata_path))
    assert int(metadata["refcount"]) == 1
    assert second.token in metadata["sessions"]

    release_root_projection(second)
    assert not Path(second.mount_path).exists()


def test_projection_reuse_path_uses_serialized_metadata_updates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(projections_mod, "redis_lock_client", lock_stub)

    first = acquire_root_projection(wd, "watershed", mode="read", purpose="first")
    meta = _read_json(Path(first.metadata_path))
    reuse_lock_key = f"{meta['lock_key']}/reuse"
    lock_stub.force_set(reuse_lock_key, "held")

    with pytest.raises(NoDirError) as exc:
        acquire_root_projection(wd, "watershed", mode="read", purpose="second")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"

    release_root_projection(first)


def test_mutation_commit_requires_live_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(projections_mod, "redis_lock_client", lock_stub)

    handle = acquire_root_projection(wd, "watershed", mode="mutate", purpose="mutate")
    lock_stub.force_set(handle.lock_key, "other-owner")

    with pytest.raises(NoDirError) as exc:
        commit_mutation_projection(handle)

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"


def test_mutation_abort_requires_live_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(projections_mod, "redis_lock_client", lock_stub)

    handle = acquire_root_projection(wd, "watershed", mode="mutate", purpose="mutate")
    lock_stub.force_set(handle.lock_key, "other-owner")

    with pytest.raises(NoDirError) as exc:
        abort_mutation_projection(handle)

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"


def test_release_serializes_with_reuse_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(projections_mod, "redis_lock_client", lock_stub)

    first = acquire_root_projection(wd, "watershed", mode="read", purpose="one")
    second = acquire_root_projection(wd, "watershed", mode="read", purpose="two")

    lock_stub.force_set(f"{first.lock_key}/reuse", "held")
    release_root_projection(first)

    meta = _read_json(Path(second.metadata_path))
    assert int(meta["refcount"]) == 2

    lock_stub.delete(f"{first.lock_key}/reuse")
    release_root_projection(first)
    meta = _read_json(Path(second.metadata_path))
    assert int(meta["refcount"]) == 1

    release_root_projection(second)


def test_stale_sweep_fails_closed_on_redis_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "alpha"})

    import wepppy.nodir.projections as projections_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(projections_mod, "redis_lock_client", lock_stub)

    stale_lower = wd / ".nodir" / "lower" / "watershed" / "1-1" / "data"
    stale_lower.mkdir(parents=True, exist_ok=True)
    mount_path = wd / "watershed"
    mount_path.symlink_to(stale_lower, target_is_directory=True)

    stale_meta = wd / ".nodir" / "projections" / "watershed" / "1-1" / "read.json"
    stale_meta.parent.mkdir(parents=True, exist_ok=True)
    stale_key = "nodb-lock:stale:key"
    stale_meta.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "root": "watershed",
                "mode": "read",
                "mount_path": str(mount_path),
                "lock_key": stale_key,
                "lock_value": "stale-value",
                "lower_path": str(stale_lower),
                "upper_path": None,
                "work_path": None,
            }
        ),
        encoding="utf-8",
    )
    lock_stub.fail_get_for(stale_key)

    with pytest.raises(NoDirError) as exc:
        acquire_root_projection(wd, "watershed", mode="read", purpose="fails-closed")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"
    assert stale_meta.exists()
