from __future__ import annotations

import hashlib
import json
import threading
import time
import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError, nodir_invalid_archive, nodir_locked
from wepppy.nodir.fs import resolve
from wepppy.nodir.materialize import materialize_file
from wepppy.nodir.state import archive_fingerprint_from_path, write_state

pytestmark = pytest.mark.unit


class _RedisLockStub:
    def __init__(self, *, allow_acquire: bool = True) -> None:
        self.allow_acquire = allow_acquire
        self._store: dict[str, str] = {}
        self._mutex = threading.Lock()

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):  # noqa: ARG002
        with self._mutex:
            if not self.allow_acquire:
                return False
            if nx and key in self._store:
                return False
            self._store[key] = value
            return True

    def get(self, key: str):
        with self._mutex:
            return self._store.get(key)

    def delete(self, key: str):
        with self._mutex:
            self._store.pop(key, None)
            return 1

    def expire(self, key: str, seconds: int):  # noqa: ARG002
        with self._mutex:
            return 1 if key in self._store else 0

    def eval(self, script: str, numkeys: int, key: str, *args):  # noqa: ARG002
        expected = str(args[0]) if args else ""

        with self._mutex:
            current = self._store.get(key)
            if "redis.call('del', KEYS[1])" in script:
                if current == expected:
                    self._store.pop(key, None)
                    return 1
                return 0
            if "redis.call('expire', KEYS[1], ARGV[2])" in script:
                if current == expected:
                    return 1
                return 0

        raise AssertionError(f"unexpected eval script: {script}")

    def force_set(self, key: str, value: str) -> None:
        with self._mutex:
            self._store[key] = value



def _write_zip(path: Path, entries: dict[str, bytes | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            zf.writestr(name, data)


def _materialized_entry_dir(wd: Path, *, logical_rel: str) -> Path:
    target = resolve(str(wd), logical_rel, view="archive")
    assert target is not None
    assert target.archive_fp is not None
    inner = target.inner_path
    entry_id = hashlib.sha256(inner.encode("utf-8")).hexdigest()[:32]
    archive_fp = f"{target.archive_fp[0]}-{target.archive_fp[1]}"
    return wd / ".nodir" / "cache" / target.root / archive_fp / entry_id


def _materialize_lock_key(wd: Path, *, logical_rel: str) -> str:
    target = resolve(str(wd), logical_rel, view="archive")
    assert target is not None
    entry_hash = hashlib.sha256(target.inner_path.encode("utf-8")).hexdigest()[:32]
    runid = wd.name
    return f"nodb-lock:{runid}:nodir-materialize/{target.root}/{entry_hash}"


def test_materialize_cache_hit_avoids_reextract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    path = Path(materialize_file(str(wd), "watershed/hillslopes/h001.slp", purpose="test"))
    assert path.read_text(encoding="utf-8") == "alpha"

    def _should_not_extract(**kwargs):  # noqa: ARG001
        raise AssertionError("cache hit should not call extractor")

    monkeypatch.setattr(materialize_mod, "_extract_plans_to_cache", _should_not_extract)
    second = Path(materialize_file(str(wd), "watershed/hillslopes/h001.slp", purpose="test"))
    assert second == path


def test_materialize_cache_rebuilds_when_meta_mismatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    path = Path(materialize_file(str(wd), "watershed/hillslopes/h001.slp", purpose="test"))
    meta_path = path.parent / "meta.json"
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    payload["files"][0]["zip"]["crc32"] = -1
    meta_path.write_text(json.dumps(payload), encoding="utf-8")

    rebuilt = Path(materialize_file(str(wd), "watershed/hillslopes/h001.slp", purpose="test"))
    assert rebuilt == path

    refreshed = json.loads(meta_path.read_text(encoding="utf-8"))
    assert int(refreshed["files"][0]["zip"]["crc32"]) >= 0


def test_materialize_lock_contention_returns_503(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "hello"})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub(allow_acquire=False))

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/a.txt", purpose="test")

    err = exc.value
    assert err.http_status == 503
    assert err.code == "NODIR_LOCKED"


def test_materialize_lock_contention_waits_for_peer_cache_fill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    logical_rel = "watershed/big.bin"
    _write_zip(wd / "watershed.nodir", {"big.bin": b"x" * (3 * 1024 * 1024)})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())
    monkeypatch.setenv("NODIR_MATERIALIZE_LOCK_WAIT_SECONDS", "2")
    monkeypatch.setattr(materialize_mod, "_LOCK_RENEWAL_INTERVAL_SECONDS", 0.0)

    started = threading.Event()
    release = threading.Event()
    original_extract = materialize_mod._extract_file

    def _blocking_extract(*args, **kwargs):
        started.set()
        assert release.wait(timeout=5)
        return original_extract(*args, **kwargs)

    monkeypatch.setattr(materialize_mod, "_extract_file", _blocking_extract)

    worker_result: dict[str, object] = {}

    def _worker() -> None:
        try:
            worker_result["path"] = materialize_file(str(wd), logical_rel, purpose="test")
        except BaseException as exc:  # pragma: no cover - captured assertion path
            worker_result["exc"] = exc

    worker_thread = threading.Thread(target=_worker)
    worker_thread.start()
    assert started.wait(timeout=5)

    def _release_later() -> None:
        time.sleep(0.2)
        release.set()

    release_thread = threading.Thread(target=_release_later)
    release_thread.start()

    peer_path = materialize_file(str(wd), logical_rel, purpose="test")

    release_thread.join(timeout=5)
    assert not release_thread.is_alive()
    worker_thread.join(timeout=10)
    assert not worker_thread.is_alive()

    assert "exc" not in worker_result
    assert worker_result["path"] == peer_path


def test_materialize_explicit_none_override_disables_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr("wepppy.nodb.base.redis_lock_client", _RedisLockStub(), raising=False)
    monkeypatch.setattr(materialize_mod, "redis_lock_client", None)

    with pytest.raises(NoDirError) as exc:
        materialize_mod._acquire_materialize_lock("nodb-lock:test:key", purpose="unit-test")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"


def test_materialize_limit_exceeded_returns_413(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": b"1234567890"})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())
    monkeypatch.setenv("NODIR_MATERIALIZE_MAX_FILE_BYTES", "4")

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/a.txt", purpose="test")

    err = exc.value
    assert err.http_status == 413
    assert err.code == "NODIR_LIMIT_EXCEEDED"


def test_materialize_invalid_archive_entry_returns_500(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    with zipfile.ZipFile(wd / "watershed.nodir", "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../evil.txt", b"oops")

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/evil.txt", purpose="test")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"


def test_materialize_failure_leaves_no_partial_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "hello"})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    def _explode_extract(*args, **kwargs):  # noqa: ARG001
        dst_path = args[2]
        Path(dst_path).write_text("partial", encoding="utf-8")
        raise nodir_invalid_archive("simulated extraction failure")

    monkeypatch.setattr(materialize_mod, "_extract_file", _explode_extract)

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/a.txt", purpose="test")

    assert exc.value.code == "NODIR_INVALID_ARCHIVE"

    entry_dir = _materialized_entry_dir(wd, logical_rel="watershed/a.txt")
    assert not entry_dir.exists()


def test_materialize_shp_extracts_required_sidecars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(
        wd / "watershed.nodir",
        {
            "shapes/demo.shp": "shp",
            "shapes/demo.shx": "shx",
            "shapes/demo.dbf": "dbf",
            "shapes/demo.prj": "prj",
        },
    )

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    shp_path = Path(materialize_file(str(wd), "watershed/shapes/demo.shp", purpose="test"))
    extracted = {item.name for item in shp_path.parent.iterdir()}

    assert "demo.shp" in extracted
    assert "demo.shx" in extracted
    assert "demo.dbf" in extracted
    assert "demo.prj" in extracted


def test_materialize_shp_missing_required_sidecar_is_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(
        wd / "watershed.nodir",
        {
            "shapes/demo.shp": "shp",
            "shapes/demo.shx": "shx",
        },
    )

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/shapes/demo.shp", purpose="test")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"


def test_materialize_tif_extracts_known_sidecars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(
        wd / "watershed.nodir",
        {
            "raster/elev.tif": "tif",
            "raster/elev.tif.ovr": "ovr",
            "raster/elev.tfw": "tfw",
            "raster/elev.aux.xml": "aux",
        },
    )

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    tif_path = Path(materialize_file(str(wd), "watershed/raster/elev.tif", purpose="test"))
    extracted = {item.name for item in tif_path.parent.iterdir()}

    assert "elev.tif" in extracted
    assert "elev.tif.ovr" in extracted
    assert "elev.tfw" in extracted
    assert "elev.aux.xml" in extracted


def test_materialize_uppercase_shp_ext_extracts_sidecars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(
        wd / "watershed.nodir",
        {
            "shapes/DEMO.SHP": "shp",
            "shapes/DEMO.SHX": "shx",
            "shapes/DEMO.DBF": "dbf",
            "shapes/DEMO.PRJ": "prj",
        },
    )

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    shp_path = Path(materialize_file(str(wd), "watershed/shapes/DEMO.SHP", purpose="test"))
    extracted = {item.name for item in shp_path.parent.iterdir()}

    assert "DEMO.SHP" in extracted
    assert "DEMO.SHX" in extracted
    assert "DEMO.DBF" in extracted
    assert "DEMO.PRJ" in extracted


def test_materialize_renews_lock_during_extraction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"big.bin": b"x" * (3 * 1024 * 1024)})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())
    monkeypatch.setattr(materialize_mod, "_LOCK_RENEWAL_INTERVAL_SECONDS", 0.0)

    renewal_calls = 0

    def _track_lock_renewal(lock_key: str, lock_value: str) -> None:  # noqa: ARG001
        nonlocal renewal_calls
        renewal_calls += 1

    monkeypatch.setattr(materialize_mod, "_renew_materialize_lock", _track_lock_renewal)

    materialize_file(str(wd), "watershed/big.bin", purpose="test")

    assert renewal_calls > 0


def test_create_ermit_input_mixed_state_fails_fast(tmp_path: Path) -> None:
    from wepppy.export.ermit_input import create_ermit_input

    wd = tmp_path
    (wd / "watershed").mkdir(parents=True)
    _write_zip(wd / "watershed.nodir", {"placeholder.txt": "x"})

    with pytest.raises(NoDirError) as exc:
        create_ermit_input(str(wd))

    err = exc.value
    assert err.http_status == 409
    assert err.code == "NODIR_MIXED_STATE"


def test_materialize_uppercase_tif_ext_extracts_sidecars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(
        wd / "watershed.nodir",
        {
            "raster/ELEV.TIF": "tif",
            "raster/ELEV.TIF.OVR": "ovr",
            "raster/ELEV.TFW": "tfw",
            "raster/ELEV.AUX.XML": "aux",
        },
    )

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    tif_path = Path(materialize_file(str(wd), "watershed/raster/ELEV.TIF", purpose="test"))
    extracted = {item.name for item in tif_path.parent.iterdir()}

    assert "ELEV.TIF" in extracted
    assert "ELEV.TIF.OVR" in extracted
    assert "ELEV.TFW" in extracted
    assert "ELEV.AUX.XML" in extracted


def test_materialize_renewal_loss_returns_503(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"big.bin": b"x" * (3 * 1024 * 1024)})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())
    monkeypatch.setattr(materialize_mod, "_LOCK_RENEWAL_INTERVAL_SECONDS", 0.0)

    def _lose_lock(lock_key: str, lock_value: str) -> None:  # noqa: ARG001
        raise nodir_locked("simulated lock ownership loss")

    monkeypatch.setattr(materialize_mod, "_renew_materialize_lock", _lose_lock)

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/big.bin", purpose="test")

    err = exc.value
    assert err.http_status == 503
    assert err.code == "NODIR_LOCKED"

    entry_dir = _materialized_entry_dir(wd, logical_rel="watershed/big.bin")
    assert not entry_dir.exists()


def test_materialize_no_eval_backend_fails_closed_on_renewal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"big.bin": b"x" * (3 * 1024 * 1024)})

    import wepppy.nodir.materialize as materialize_mod

    class _NoEvalRedisLockStub:
        def __init__(self) -> None:
            self._delegate = _RedisLockStub()

        def set(self, *args, **kwargs):
            return self._delegate.set(*args, **kwargs)

        def get(self, *args, **kwargs):
            return self._delegate.get(*args, **kwargs)

        def delete(self, *args, **kwargs):
            return self._delegate.delete(*args, **kwargs)

        def expire(self, *args, **kwargs):
            return self._delegate.expire(*args, **kwargs)

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _NoEvalRedisLockStub())
    monkeypatch.setattr(materialize_mod, "_LOCK_RENEWAL_INTERVAL_SECONDS", 0.0)

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/big.bin", purpose="test")

    err = exc.value
    assert err.http_status == 503
    assert err.code == "NODIR_LOCKED"

    entry_dir = _materialized_entry_dir(wd, logical_rel="watershed/big.bin")
    assert not entry_dir.exists()


def test_materialize_multiworker_lock_handoff_fails_fast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    logical_rel = "watershed/big.bin"
    _write_zip(wd / "watershed.nodir", {"big.bin": b"x" * (3 * 1024 * 1024)})

    import wepppy.nodir.materialize as materialize_mod

    lock_stub = _RedisLockStub()
    monkeypatch.setattr(materialize_mod, "redis_lock_client", lock_stub)
    monkeypatch.setattr(materialize_mod, "_LOCK_RENEWAL_INTERVAL_SECONDS", 0.0)

    started = threading.Event()
    release = threading.Event()
    original_extract = materialize_mod._extract_file

    def _blocking_extract(*args, **kwargs):
        started.set()
        assert release.wait(timeout=5)
        return original_extract(*args, **kwargs)

    monkeypatch.setattr(materialize_mod, "_extract_file", _blocking_extract)

    worker_result: dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            materialize_file(str(wd), logical_rel, purpose="test")
        except BaseException as exc:  # pragma: no cover - captured assertion path
            worker_result["exc"] = exc

    worker_thread = threading.Thread(target=_worker)
    worker_thread.start()

    assert started.wait(timeout=5)

    with pytest.raises(NoDirError) as peer_exc:
        materialize_file(str(wd), logical_rel, purpose="test")

    assert peer_exc.value.http_status == 503
    assert peer_exc.value.code == "NODIR_LOCKED"

    lock_key = _materialize_lock_key(wd, logical_rel=logical_rel)
    lock_stub.force_set(lock_key, "stolen-owner")
    release.set()
    worker_thread.join(timeout=10)
    assert not worker_thread.is_alive()

    assert "exc" in worker_result
    assert isinstance(worker_result["exc"], NoDirError)
    assert worker_result["exc"].http_status == 503
    assert worker_result["exc"].code == "NODIR_LOCKED"

    entry_dir = _materialized_entry_dir(wd, logical_rel=logical_rel)
    assert not entry_dir.exists()


def test_materialize_missing_state_with_temp_sentinel_returns_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "hello"})
    (wd / "watershed.thaw.tmp").mkdir(parents=True, exist_ok=False)

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/a.txt", purpose="test")

    err = exc.value
    assert err.http_status == 503
    assert err.code == "NODIR_LOCKED"


@pytest.mark.parametrize("state_name", ["thawing", "freezing"])
def test_materialize_transition_state_returns_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state_name: str,
) -> None:
    wd = tmp_path
    archive_path = wd / "watershed.nodir"
    _write_zip(archive_path, {"a.txt": "hello"})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    write_state(
        wd,
        "watershed",
        state=state_name,
        op_id="00000000-0000-4000-8000-000000000021" if state_name == "thawing" else "00000000-0000-4000-8000-000000000022",
        dirty=True,
        archive_fingerprint=archive_fingerprint_from_path(archive_path),
    )

    with pytest.raises(NoDirError) as exc:
        materialize_file(str(wd), "watershed/a.txt", purpose="test")

    err = exc.value
    assert err.http_status == 503
    assert err.code == "NODIR_LOCKED"
