"""Crash-safe NoDir thaw/freeze workflows."""

from __future__ import annotations

import json
import os
import shutil
import socket
import stat as statmod
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from time import time

from .errors import nodir_invalid_archive, nodir_locked
from .fs import _load_zip_index, _stat_ctime_ns, _stat_mtime_ns, _validate_zip_entry_name, _validate_zip_info
from .parquet_sidecars import logical_parquet_to_sidecar_relpath
from .paths import NODIR_ROOTS, NoDirRoot
from .state import (
    NoDirArchiveFingerprint,
    NoDirStateName,
    NoDirStatePayload,
    archive_fingerprint_from_path,
    freeze_temp_path,
    read_state,
    thaw_temp_path,
    write_state,
)
from .symlinks import _derive_allowed_symlink_roots, _is_within_any_root, _resolve_path_safely

__all__ = [
    "NoDirMaintenanceLock",
    "maintenance_lock_key",
    "acquire_maintenance_lock",
    "release_maintenance_lock",
    "maintenance_lock",
    "thaw_locked",
    "thaw",
    "freeze_locked",
    "freeze",
]


_BUFFER_SIZE = 1024 * 1024

# Test harnesses monkeypatch this module attribute directly.
_REDIS_LOCK_CLIENT_UNSET = object()
redis_lock_client = _REDIS_LOCK_CLIENT_UNSET


@dataclass(frozen=True, slots=True)
class NoDirMaintenanceLock:
    key: str
    value: str
    root: NoDirRoot
    runid: str
    host: str
    pid: int
    owner: str
    token: str


def _normalize_root(root: str) -> NoDirRoot:
    if root not in NODIR_ROOTS:
        raise ValueError(f"unsupported NoDir root: {root}")
    return root


def _runid_from_wd(wd_path: Path) -> str:
    # Mirror NoDbBase.runid semantics for pup workspaces so distributed lock
    # keys stay run-scoped instead of colliding on scenario leaf names.
    parts = str(wd_path).split(os.sep)
    if "_pups" in parts:
        pups_idx = parts.index("_pups")
        if pups_idx > 0:
            return parts[pups_idx - 1]
    return wd_path.name


def _lock_owner(host: str, pid: int) -> str:
    return f"{host}:{pid}"


def _redis_value_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _maintenance_lock_backend() -> tuple[int, object | None]:
    override = globals().get("redis_lock_client", _REDIS_LOCK_CLIENT_UNSET)
    if override is not _REDIS_LOCK_CLIENT_UNSET:
        from wepppy.nodb.base import LOCK_DEFAULT_TTL

        return LOCK_DEFAULT_TTL, override

    # Delay import to avoid query-engine bootstrap cycles during module import.
    from wepppy.nodb.base import LOCK_DEFAULT_TTL, redis_lock_client

    return LOCK_DEFAULT_TTL, redis_lock_client


def maintenance_lock_key(wd: str | Path, root: str) -> str:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)
    runid = _runid_from_wd(wd_path)
    return f"nodb-lock:{runid}:nodir/{normalized_root}"


def acquire_maintenance_lock(
    wd: str | Path,
    root: str,
    *,
    purpose: str = "nodir-maintenance",
    ttl_seconds: int | None = None,
) -> NoDirMaintenanceLock:
    normalized_root = _normalize_root(root)
    wd_path = Path(os.path.abspath(str(wd)))
    runid = _runid_from_wd(wd_path)
    key = maintenance_lock_key(wd_path, normalized_root)

    lock_default_ttl, redis_client = _maintenance_lock_backend()
    if redis_client is None:
        raise nodir_locked("NoDir maintenance lock backend unavailable")

    ttl = max(1, int(ttl_seconds if ttl_seconds is not None else lock_default_ttl))
    host = socket.gethostname()
    pid = os.getpid()
    owner = _lock_owner(host, pid)
    token = uuid.uuid4().hex
    value = json.dumps(
        {
            "token": token,
            "owner": owner,
            "purpose": purpose,
            "acquired_at": int(time()),
            "ttl": ttl,
        },
        separators=(",", ":"),
    )

    try:
        acquired = redis_client.set(key, value, nx=True, ex=ttl)
    except Exception as exc:
        raise nodir_locked("failed to acquire NoDir maintenance lock") from exc
    if not acquired:
        raise nodir_locked(f"NoDir maintenance lock is currently held: {key}")

    return NoDirMaintenanceLock(
        key=key,
        value=value,
        root=normalized_root,
        runid=runid,
        host=host,
        pid=pid,
        owner=owner,
        token=token,
    )


def release_maintenance_lock(lock: NoDirMaintenanceLock) -> None:
    _, redis_client = _maintenance_lock_backend()
    if redis_client is None:
        return

    release_lua = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then "
        "return redis.call('del', KEYS[1]) "
        "else return 0 end"
    )

    try:
        if hasattr(redis_client, "eval"):
            redis_client.eval(release_lua, 1, lock.key, lock.value)
            return
    except Exception:
        pass

    try:
        current = redis_client.get(lock.key)
    except Exception:
        return

    if _redis_value_text(current) != lock.value:
        return

    try:
        redis_client.delete(lock.key)
    except Exception:
        pass


class _MaintenanceLockContext:
    def __init__(
        self,
        wd: str | Path,
        root: str,
        *,
        purpose: str,
        ttl_seconds: int | None,
    ) -> None:
        self._wd = wd
        self._root = root
        self._purpose = purpose
        self._ttl_seconds = ttl_seconds
        self._lock: NoDirMaintenanceLock | None = None

    def __enter__(self) -> NoDirMaintenanceLock:
        self._lock = acquire_maintenance_lock(
            self._wd,
            self._root,
            purpose=self._purpose,
            ttl_seconds=self._ttl_seconds,
        )
        return self._lock

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        if self._lock is not None:
            release_maintenance_lock(self._lock)
            self._lock = None
        return False


def maintenance_lock(
    wd: str | Path,
    root: str,
    *,
    purpose: str = "nodir-maintenance",
    ttl_seconds: int | None = None,
) -> _MaintenanceLockContext:
    return _MaintenanceLockContext(
        wd,
        root,
        purpose=purpose,
        ttl_seconds=ttl_seconds,
    )


def _remove_tree_or_file(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return

    try:
        st = path.lstat()
    except FileNotFoundError:
        return

    if statmod.S_ISDIR(st.st_mode) and not statmod.S_ISLNK(st.st_mode):
        shutil.rmtree(path, ignore_errors=False)
        return

    path.unlink(missing_ok=True)


def _best_effort_archive_fingerprint(
    archive_path: Path,
    *,
    fallback: NoDirArchiveFingerprint | None = None,
) -> NoDirArchiveFingerprint:
    try:
        return archive_fingerprint_from_path(archive_path)
    except (FileNotFoundError, OSError, ValueError):
        if fallback is not None:
            return {
                "mtime_ns": int(fallback.get("mtime_ns", 0)),
                "size_bytes": int(fallback.get("size_bytes", 0)),
            }
        return {"mtime_ns": 0, "size_bytes": 0}


def _write_locked_state(
    wd_path: Path,
    root: NoDirRoot,
    *,
    state: NoDirStateName,
    op_id: str,
    dirty: bool,
    lock: NoDirMaintenanceLock,
    archive_fingerprint: NoDirArchiveFingerprint,
) -> NoDirStatePayload:
    return write_state(
        wd_path,
        root,
        state=state,
        op_id=op_id,
        dirty=dirty,
        host=lock.host,
        pid=lock.pid,
        lock_owner=lock.owner,
        archive_fingerprint=archive_fingerprint,
    )


def _ensure_within_root(root_path: Path, candidate: Path) -> None:
    root_real = root_path.resolve(strict=False)
    candidate_real = candidate.resolve(strict=False)
    try:
        candidate_real.relative_to(root_real)
    except ValueError as exc:
        raise nodir_invalid_archive("archive entry escapes thaw root") from exc


def _extract_archive_to_thaw_tmp(*, archive_path: Path, thaw_tmp_path: Path) -> None:
    thaw_tmp_path.mkdir(parents=False, exist_ok=False)

    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            entry_name, is_dir = _validate_zip_info(info)
            normalized = entry_name if not is_dir else f"{entry_name}/"
            _validate_zip_entry_name(normalized)

            out_path = thaw_tmp_path / entry_name.replace("/", os.sep)
            _ensure_within_root(thaw_tmp_path, out_path)

            if is_dir:
                out_path.mkdir(parents=True, exist_ok=True)
                continue

            out_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = out_path.with_name(f"{out_path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
            try:
                with zf.open(info, "r") as src, temp_path.open("wb") as dst:
                    while True:
                        chunk = src.read(_BUFFER_SIZE)
                        if not chunk:
                            break
                        dst.write(chunk)
                os.replace(temp_path, out_path)
            finally:
                temp_path.unlink(missing_ok=True)


def _move_parquet_sidecars(wd_path: Path, root: NoDirRoot, root_path: Path) -> None:
    for path in sorted(root_path.rglob("*")):
        name = path.name
        if not name.casefold().endswith(".parquet"):
            continue

        try:
            rel = path.relative_to(root_path).as_posix()
        except ValueError as exc:
            raise nodir_invalid_archive("parquet path escaped NoDir root during freeze") from exc

        if not rel.casefold().endswith(".parquet"):
            raise nodir_invalid_archive(f"unsupported parquet entry: {rel}")

        logical_rel = f"{rel[:-8]}.parquet"
        logical = f"{root}/{logical_rel}"
        sidecar_rel = logical_parquet_to_sidecar_relpath(logical)
        if sidecar_rel is None:
            raise nodir_invalid_archive(f"unsupported parquet sidecar mapping: {logical}")

        st = path.lstat()
        if not statmod.S_ISREG(st.st_mode):
            raise nodir_invalid_archive("parquet entries must be regular files during freeze")

        sidecar_path = wd_path / sidecar_rel
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(path, sidecar_path)


def _write_archive_from_directory(*, wd_path: Path, root_path: Path, tmp_archive: Path) -> None:
    allowed_roots = _derive_allowed_symlink_roots(wd_path)

    with tmp_archive.open("wb") as handle:
        with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for current_dir, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False):
                current_dir_path = Path(current_dir)

                kept_dirs: list[str] = []
                for dirname in sorted(dirnames):
                    child_dir = current_dir_path / dirname
                    child_st = child_dir.lstat()
                    if statmod.S_ISLNK(child_st.st_mode):
                        raise nodir_invalid_archive(
                            f"symlinked directories are not supported during freeze: {child_dir}"
                        )
                    if not statmod.S_ISDIR(child_st.st_mode):
                        raise nodir_invalid_archive(f"unexpected directory entry type: {child_dir}")
                    kept_dirs.append(dirname)
                dirnames[:] = kept_dirs

                rel_dir = current_dir_path.relative_to(root_path).as_posix()
                if rel_dir != "." and not filenames and not dirnames:
                    dir_entry = f"{rel_dir}/"
                    _validate_zip_entry_name(dir_entry)
                    zf.writestr(dir_entry, b"")

                for filename in sorted(filenames):
                    source_path = current_dir_path / filename
                    rel_file = source_path.relative_to(root_path).as_posix()
                    _validate_zip_entry_name(rel_file)
                    if rel_file.casefold().endswith(".parquet"):
                        # Canonical parquet paths live at WD-level sidecars.
                        continue

                    st = source_path.lstat()
                    if statmod.S_ISLNK(st.st_mode):
                        resolved = _resolve_path_safely(source_path)
                        if resolved is None or not _is_within_any_root(resolved, allowed_roots):
                            raise nodir_invalid_archive(
                                f"symlink target escaped allowed roots during freeze: {source_path}"
                            )
                        try:
                            resolved_st = resolved.stat()
                        except OSError as exc:
                            raise nodir_invalid_archive(
                                f"symlink target unavailable during freeze: {source_path}"
                            ) from exc
                        if not statmod.S_ISREG(resolved_st.st_mode):
                            raise nodir_invalid_archive(
                                f"symlink target is not a regular file during freeze: {source_path}"
                            )
                        source_path = resolved
                    elif not statmod.S_ISREG(st.st_mode):
                        raise nodir_invalid_archive(f"unsupported file type during freeze: {source_path}")

                    zf.write(source_path, arcname=rel_file, compress_type=zipfile.ZIP_DEFLATED)

        handle.flush()
        os.fsync(handle.fileno())


def _verify_archive(path: Path) -> None:
    st = path.stat()
    _load_zip_index(
        str(path),
        _stat_mtime_ns(st),
        int(st.st_size),
        int(st.st_ino),
        _stat_ctime_ns(st),
        int(st.st_dev),
    )




def _thaw_impl(
    wd_path: Path,
    normalized_root: NoDirRoot,
    lock: NoDirMaintenanceLock,
) -> NoDirStatePayload:
    archive_path = wd_path / f"{normalized_root}.nodir"
    dir_path = wd_path / normalized_root
    thaw_tmp = thaw_temp_path(wd_path, normalized_root)
    freeze_tmp = freeze_temp_path(wd_path, normalized_root)
    op_id = str(uuid.uuid4())

    if freeze_tmp.exists() or freeze_tmp.is_symlink():
        _remove_tree_or_file(freeze_tmp)

    if thaw_tmp.exists() or thaw_tmp.is_symlink():
        _remove_tree_or_file(thaw_tmp)

    if not archive_path.exists():
        raise FileNotFoundError(str(archive_path))

    archive_fp = archive_fingerprint_from_path(archive_path)

    if dir_path.exists():
        return _write_locked_state(
            wd_path,
            normalized_root,
            state="thawed",
            op_id=op_id,
            dirty=True,
            lock=lock,
            archive_fingerprint=archive_fp,
        )

    _verify_archive(archive_path)

    _write_locked_state(
        wd_path,
        normalized_root,
        state="thawing",
        op_id=op_id,
        dirty=True,
        lock=lock,
        archive_fingerprint=archive_fp,
    )

    _extract_archive_to_thaw_tmp(archive_path=archive_path, thaw_tmp_path=thaw_tmp)
    os.replace(thaw_tmp, dir_path)

    final_fp = _best_effort_archive_fingerprint(archive_path, fallback=archive_fp)
    return _write_locked_state(
        wd_path,
        normalized_root,
        state="thawed",
        op_id=op_id,
        dirty=True,
        lock=lock,
        archive_fingerprint=final_fp,
    )


def thaw_locked(
    wd: str | Path,
    root: str,
    *,
    lock: NoDirMaintenanceLock,
) -> NoDirStatePayload:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)
    if lock.root != normalized_root:
        raise ValueError(
            f"maintenance lock root mismatch: expected {normalized_root}, got {lock.root}"
        )
    return _thaw_impl(wd_path, normalized_root, lock)


def thaw(wd: str | Path, root: str) -> NoDirStatePayload:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)

    with maintenance_lock(wd_path, normalized_root, purpose="nodir-thaw") as lock:
        return _thaw_impl(wd_path, normalized_root, lock)


def _freeze_impl(
    wd_path: Path,
    normalized_root: NoDirRoot,
    lock: NoDirMaintenanceLock,
) -> NoDirStatePayload:
    archive_path = wd_path / f"{normalized_root}.nodir"
    dir_path = wd_path / normalized_root
    thaw_tmp = thaw_temp_path(wd_path, normalized_root)
    freeze_tmp = freeze_temp_path(wd_path, normalized_root)
    op_id = str(uuid.uuid4())

    if thaw_tmp.exists() or thaw_tmp.is_symlink():
        _remove_tree_or_file(thaw_tmp)

    if freeze_tmp.exists() or freeze_tmp.is_symlink():
        _remove_tree_or_file(freeze_tmp)

    prior_state = read_state(wd_path, normalized_root, strict=False)
    prior_dirty = True if prior_state is None else bool(prior_state.get("dirty", True))
    prior_fp = None
    if prior_state is not None:
        prior_fp_raw = prior_state.get("archive_fingerprint")
        if isinstance(prior_fp_raw, dict):
            prior_fp = {
                "mtime_ns": int(prior_fp_raw.get("mtime_ns", 0)),
                "size_bytes": int(prior_fp_raw.get("size_bytes", 0)),
            }

    if not dir_path.exists():
        if prior_state is not None and prior_state.get("state") == "freezing" and archive_path.exists():
            _verify_archive(archive_path)
            final_fp = archive_fingerprint_from_path(archive_path)
            return _write_locked_state(
                wd_path,
                normalized_root,
                state="archived",
                op_id=op_id,
                dirty=False,
                lock=lock,
                archive_fingerprint=final_fp,
            )
        raise FileNotFoundError(str(dir_path))
    if not dir_path.is_dir():
        raise nodir_invalid_archive(f"NoDir root is not a directory: {dir_path}")

    start_fp = _best_effort_archive_fingerprint(archive_path, fallback=prior_fp)
    _write_locked_state(
        wd_path,
        normalized_root,
        state="freezing",
        op_id=op_id,
        dirty=prior_dirty,
        lock=lock,
        archive_fingerprint=start_fp,
    )

    _move_parquet_sidecars(wd_path, normalized_root, dir_path)
    _write_archive_from_directory(
        wd_path=wd_path,
        root_path=dir_path,
        tmp_archive=freeze_tmp,
    )
    _verify_archive(freeze_tmp)
    os.replace(freeze_tmp, archive_path)
    shutil.rmtree(dir_path)

    final_fp = archive_fingerprint_from_path(archive_path)
    return _write_locked_state(
        wd_path,
        normalized_root,
        state="archived",
        op_id=op_id,
        dirty=False,
        lock=lock,
        archive_fingerprint=final_fp,
    )


def freeze_locked(
    wd: str | Path,
    root: str,
    *,
    lock: NoDirMaintenanceLock,
) -> NoDirStatePayload:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)
    if lock.root != normalized_root:
        raise ValueError(
            f"maintenance lock root mismatch: expected {normalized_root}, got {lock.root}"
        )
    return _freeze_impl(wd_path, normalized_root, lock)


def freeze(wd: str | Path, root: str) -> NoDirStatePayload:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)

    with maintenance_lock(wd_path, normalized_root, purpose="nodir-freeze") as lock:
        return _freeze_impl(wd_path, normalized_root, lock)
