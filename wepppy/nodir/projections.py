"""NoDir canonical root projection lifecycle utilities."""

from __future__ import annotations

import json
import os
import shutil
import socket
import uuid
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Iterator, Literal

from .errors import NoDirError, nodir_invalid_archive, nodir_locked, nodir_mixed_state
from .fs import _get_zip_index, resolve
from .paths import NODIR_ROOTS, NoDirRoot
from .thaw_freeze import _move_parquet_sidecars, _verify_archive, _write_archive_from_directory

__all__ = [
    "ProjectionMode",
    "ProjectionHandle",
    "acquire_root_projection",
    "release_root_projection",
    "with_root_projection",
    "commit_mutation_projection",
    "abort_mutation_projection",
]

ProjectionMode = Literal["read", "mutate"]
_SCHEMA_VERSION = 1
_MANAGED_BACKEND = "symlink+archive-projection"
_REUSE_LOCK_TTL_SECONDS = 30

# Test harnesses monkeypatch this module attribute directly.
_REDIS_LOCK_CLIENT_UNSET = object()
redis_lock_client = _REDIS_LOCK_CLIENT_UNSET


@dataclass(frozen=True, slots=True)
class ProjectionHandle:
    wd: str
    root: NoDirRoot
    mode: ProjectionMode
    purpose: str
    archive_fingerprint: tuple[int, int]
    mount_path: str
    backend: str
    token: str
    acquired_at: str
    lock_key: str
    lock_value: str
    metadata_path: str
    lower_path: str
    upper_path: str | None = None
    work_path: str | None = None


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _projection_fp(archive_fp: tuple[int, int]) -> str:
    return f"{int(archive_fp[0])}-{int(archive_fp[1])}"


def _projection_lock_key(*, wd_path: Path, root: NoDirRoot, archive_fp: tuple[int, int], mode: ProjectionMode) -> str:
    runid = _runid_from_wd(wd_path)
    return f"nodb-lock:{runid}:nodir-project/{root}/{_projection_fp(archive_fp)}/{mode}"


def _metadata_path(*, wd_path: Path, root: NoDirRoot, archive_fp: tuple[int, int], mode: ProjectionMode) -> Path:
    return wd_path / ".nodir" / "projections" / root / _projection_fp(archive_fp) / f"{mode}.json"


def _lower_data_path(*, wd_path: Path, root: NoDirRoot, archive_fp: tuple[int, int]) -> Path:
    return wd_path / ".nodir" / "lower" / root / _projection_fp(archive_fp) / "data"


def _upper_data_path(*, wd_path: Path, root: NoDirRoot, token: str) -> Path:
    return wd_path / ".nodir" / "upper" / root / token / "data"


def _work_path(*, wd_path: Path, root: NoDirRoot, token: str) -> Path:
    return wd_path / ".nodir" / "work" / root / token


def _mount_path(*, wd_path: Path, root: NoDirRoot) -> Path:
    return wd_path / root


def _redis_value_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _projection_lock_backend() -> tuple[int, object | None]:
    override = globals().get("redis_lock_client", _REDIS_LOCK_CLIENT_UNSET)
    if override is not _REDIS_LOCK_CLIENT_UNSET:
        from wepppy.nodb.base import LOCK_DEFAULT_TTL

        return LOCK_DEFAULT_TTL, override

    # Delay import to avoid query-engine bootstrap cycles during module import.
    from wepppy.nodb.base import LOCK_DEFAULT_TTL, redis_lock_client

    return LOCK_DEFAULT_TTL, redis_lock_client


def _acquire_lock(lock_key: str, *, purpose: str, ttl_seconds: int | None = None) -> str:
    lock_default_ttl, redis_client = _projection_lock_backend()
    if redis_client is None:
        raise nodir_locked("NoDir projection lock backend unavailable")

    ttl = max(1, int(ttl_seconds if ttl_seconds is not None else lock_default_ttl))
    token = uuid.uuid4().hex
    lock_value = json.dumps(
        {
            "token": token,
            "owner": f"{socket.gethostname()}:{os.getpid()}",
            "purpose": purpose,
            "acquired_at": int(time()),
            "ttl": ttl,
        },
        separators=(",", ":"),
    )
    try:
        acquired = redis_client.set(lock_key, lock_value, nx=True, ex=ttl)
    except Exception as exc:
        raise nodir_locked("failed to acquire NoDir projection lock") from exc
    if not acquired:
        raise nodir_locked("NoDir projection lock is currently held")
    return lock_value


def _release_lock(lock_key: str, lock_value: str) -> None:
    _, redis_client = _projection_lock_backend()
    if redis_client is None:
        return

    release_lua = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then "
        "return redis.call('del', KEYS[1]) "
        "else return 0 end"
    )
    try:
        if hasattr(redis_client, "eval"):
            redis_client.eval(release_lua, 1, lock_key, lock_value)
            return
    except Exception:
        pass

    try:
        current = redis_client.get(lock_key)
    except Exception:
        return
    if _redis_value_text(current) != lock_value:
        return
    try:
        redis_client.delete(lock_key)
    except Exception:
        pass


def _acquire_reuse_lock(lock_key: str, *, purpose: str) -> tuple[str, str]:
    reuse_key = f"{lock_key}/reuse"
    reuse_value = _acquire_lock(
        reuse_key,
        purpose=f"{purpose}/reuse",
        ttl_seconds=_REUSE_LOCK_TTL_SECONDS,
    )
    return reuse_key, reuse_value


def _load_metadata(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _write_metadata(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _remove_tree(path: Path) -> None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        return
    except NotADirectoryError:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _is_within_root(candidate: Path, root: Path) -> bool:
    resolved_candidate = candidate.resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True


def _safe_metadata_path(wd_path: Path, raw_path: object) -> Path | None:
    if not isinstance(raw_path, str) or raw_path.strip() == "":
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = wd_path / candidate
    if not _is_within_root(candidate, wd_path):
        return None
    return candidate


def _is_managed_projection_target(*, wd_path: Path, root: NoDirRoot, target: Path) -> bool:
    resolved_target = target.resolve(strict=False)
    managed_roots = (
        wd_path / ".nodir" / "lower" / root,
        wd_path / ".nodir" / "upper" / root,
    )
    for managed_root in managed_roots:
        try:
            resolved_target.relative_to(managed_root.resolve(strict=False))
            return True
        except ValueError:
            continue
    return False


def _is_managed_mount(mount_path: Path, expected_target: Path) -> bool:
    try:
        if not mount_path.is_symlink():
            return False
        resolved = mount_path.resolve(strict=False)
    except OSError:
        return False
    return resolved == expected_target.resolve(strict=False)


def _ensure_mount_points_to(*, wd_path: Path, root: NoDirRoot, mount_path: Path, target_path: Path) -> None:
    if mount_path.exists() or mount_path.is_symlink():
        if _is_managed_mount(mount_path, target_path):
            return
        if mount_path.is_symlink() and _is_managed_projection_target(
            wd_path=wd_path,
            root=root,
            target=mount_path.resolve(strict=False),
        ):
            raise nodir_locked(f"{root} projection is currently active in another mode")
        raise nodir_mixed_state(f"{mount_path.name} is in mixed unmanaged state (dir + .nodir present)")

    mount_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mount_path.symlink_to(target_path, target_is_directory=True)
    except OSError as exc:
        raise nodir_invalid_archive(f"failed to create projection mountpoint for {mount_path.name}") from exc


def _teardown_mount(*, mount_path: Path, expected_target: Path) -> None:
    if _is_managed_mount(mount_path, expected_target):
        mount_path.unlink(missing_ok=True)


def _extract_archive_to_path(*, target_archive, data_path: Path) -> None:
    if data_path.exists():
        return

    archive_path, index = _get_zip_index(target_archive)
    stage_path = data_path.parent / f".tmp.{data_path.name}.{uuid.uuid4().hex}"
    stage_path.mkdir(parents=True, exist_ok=False)

    try:
        for dir_name in sorted(index.dirs):
            (stage_path / dir_name).mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as zf:
            for file_name, _info in sorted(index.files.items()):
                out_path = stage_path / file_name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(file_name, "r") as src, out_path.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        os.replace(stage_path, data_path)
    except Exception:
        _remove_tree(stage_path)
        raise


def _build_metadata(
    *,
    wd_path: Path,
    root: NoDirRoot,
    mode: ProjectionMode,
    purpose: str,
    archive_fp: tuple[int, int],
    lock_key: str,
    lock_value: str,
    token: str,
    lower_path: Path,
    mount_path: Path,
    upper_path: Path | None = None,
    work_path: Path | None = None,
) -> dict:
    return {
        "schema_version": _SCHEMA_VERSION,
        "root": root,
        "mode": mode,
        "purpose": purpose,
        "runid": _runid_from_wd(wd_path),
        "archive_fingerprint": {
            "mtime_ns": int(archive_fp[0]),
            "size_bytes": int(archive_fp[1]),
        },
        "mount_path": str(mount_path),
        "backend": _MANAGED_BACKEND,
        "lock_key": lock_key,
        "lock_value": lock_value,
        "refcount": 1,
        "sessions": [token],
        "mutation_state": "active" if mode == "mutate" else "n/a",
        "token": token,
        "acquired_at": _now_iso_utc(),
        "updated_at": _now_iso_utc(),
        "lower_path": str(lower_path),
        "upper_path": str(upper_path) if upper_path is not None else None,
        "work_path": str(work_path) if work_path is not None else None,
    }


def _metadata_to_handle(metadata_path: Path, payload: dict, *, token: str, purpose: str) -> ProjectionHandle:
    archive_fp = payload.get("archive_fingerprint")
    if not isinstance(archive_fp, dict):
        raise nodir_invalid_archive("projection metadata missing archive fingerprint")
    mode = str(payload.get("mode"))
    if mode not in {"read", "mutate"}:
        raise nodir_invalid_archive("projection metadata has invalid mode")
    root = _normalize_root(str(payload.get("root")))
    return ProjectionHandle(
        wd=str(Path(str(payload.get("mount_path"))).parent),
        root=root,
        mode=mode,
        purpose=purpose,
        archive_fingerprint=(int(archive_fp["mtime_ns"]), int(archive_fp["size_bytes"])),
        mount_path=str(payload.get("mount_path")),
        backend=str(payload.get("backend", _MANAGED_BACKEND)),
        token=token,
        acquired_at=_now_iso_utc(),
        lock_key=str(payload.get("lock_key")),
        lock_value=str(payload.get("lock_value")),
        metadata_path=str(metadata_path),
        lower_path=str(payload.get("lower_path")),
        upper_path=str(payload.get("upper_path")) if payload.get("upper_path") else None,
        work_path=str(payload.get("work_path")) if payload.get("work_path") else None,
    )


def _assert_active_ownership(metadata: dict, handle: ProjectionHandle) -> None:
    sessions = metadata.get("sessions")
    if not isinstance(sessions, list) or handle.token not in sessions:
        raise nodir_locked("projection session is not active")

    lock_key = str(metadata.get("lock_key", ""))
    lock_value = str(metadata.get("lock_value", ""))
    if lock_key != handle.lock_key or lock_value != handle.lock_value:
        raise nodir_locked("projection lock ownership lost")

    _, redis_client = _projection_lock_backend()
    if redis_client is None:
        raise nodir_locked("NoDir projection lock backend unavailable")

    try:
        current = _redis_value_text(redis_client.get(lock_key))
    except Exception as exc:
        raise nodir_locked("failed to verify NoDir projection lock ownership") from exc
    if current != lock_value:
        raise nodir_locked("projection lock ownership lost")


def _sweep_stale_projection_metadata(*, wd_path: Path, root: NoDirRoot) -> None:
    projections_root = wd_path / ".nodir" / "projections" / root
    if not projections_root.exists():
        return

    # Fail closed when we cannot verify lock ownership.
    _, redis_client = _projection_lock_backend()
    if redis_client is None:
        return

    for metadata_file in projections_root.glob("*/*.json"):
        payload = _load_metadata(metadata_file)
        if payload is None:
            metadata_file.unlink(missing_ok=True)
            continue

        lock_key = str(payload.get("lock_key", ""))
        lock_value = str(payload.get("lock_value", ""))
        if not lock_key or not lock_value:
            continue

        try:
            lock_live = _redis_value_text(redis_client.get(lock_key)) == lock_value
        except Exception:
            continue

        if lock_live:
            continue

        mount_path = _safe_metadata_path(wd_path, payload.get("mount_path"))
        lower_path = _safe_metadata_path(wd_path, payload.get("lower_path"))
        upper_path = _safe_metadata_path(wd_path, payload.get("upper_path"))
        work_path = _safe_metadata_path(wd_path, payload.get("work_path"))

        if lower_path is None:
            continue
        if mount_path is None and payload.get("mount_path"):
            continue
        if upper_path is None and payload.get("upper_path"):
            continue
        if work_path is None and payload.get("work_path"):
            continue

        if mount_path is not None:
            target = upper_path if upper_path is not None else lower_path
            _teardown_mount(mount_path=mount_path, expected_target=target)
        if upper_path is not None:
            _remove_tree(upper_path.parent)
        if work_path is not None:
            _remove_tree(work_path)
        _remove_tree(lower_path.parent)
        metadata_file.unlink(missing_ok=True)


def acquire_root_projection(
    wd: str | Path,
    root: str,
    *,
    mode: ProjectionMode,
    purpose: str,
) -> ProjectionHandle:
    normalized_root = _normalize_root(root)
    wd_path = Path(os.path.abspath(str(wd)))
    if mode not in {"read", "mutate"}:
        raise ValueError("mode must be one of: read, mutate")

    target = resolve(str(wd_path), normalized_root, view="archive")
    if target is None or target.archive_fp is None:
        raise nodir_invalid_archive(f"{normalized_root}.nodir archive is required for projection")

    _sweep_stale_projection_metadata(wd_path=wd_path, root=normalized_root)

    lock_key = _projection_lock_key(
        wd_path=wd_path,
        root=normalized_root,
        archive_fp=target.archive_fp,
        mode=mode,
    )
    metadata_path = _metadata_path(
        wd_path=wd_path,
        root=normalized_root,
        archive_fp=target.archive_fp,
        mode=mode,
    )
    mount_path = _mount_path(wd_path=wd_path, root=normalized_root)
    lower_path = _lower_data_path(wd_path=wd_path, root=normalized_root, archive_fp=target.archive_fp)

    try:
        lock_value = _acquire_lock(lock_key, purpose=purpose)
        lock_acquired = True
    except NoDirError:
        lock_value = ""
        lock_acquired = False

    if not lock_acquired:
        metadata = _load_metadata(metadata_path)
        if metadata is None:
            raise nodir_locked("NoDir projection lock is currently held")

        existing_lock_value = str(metadata.get("lock_value", ""))
        _, redis_client = _projection_lock_backend()
        if redis_client is not None:
            try:
                current = _redis_value_text(redis_client.get(lock_key))
            except Exception:
                current = None
            if current != existing_lock_value:
                raise nodir_locked("NoDir projection lock is currently held")

        reuse_lock_key, reuse_lock_value = _acquire_reuse_lock(lock_key, purpose=purpose)
        try:
            metadata = _load_metadata(metadata_path)
            if metadata is None:
                raise nodir_locked("NoDir projection metadata is stale")

            existing_lock_value = str(metadata.get("lock_value", ""))
            _, redis_client = _projection_lock_backend()
            if redis_client is not None:
                try:
                    current = _redis_value_text(redis_client.get(lock_key))
                except Exception:
                    current = None
                if current != existing_lock_value:
                    raise nodir_locked("NoDir projection lock is currently held")

            current_refcount = int(metadata.get("refcount", 0))
            if current_refcount < 1:
                raise nodir_locked("NoDir projection metadata is stale")

            session_token = uuid.uuid4().hex
            sessions = metadata.get("sessions")
            if not isinstance(sessions, list):
                sessions = []
            sessions.append(session_token)
            metadata["sessions"] = sessions
            metadata["refcount"] = current_refcount + 1
            metadata["updated_at"] = _now_iso_utc()
            _write_metadata(metadata_path, metadata)
            return _metadata_to_handle(metadata_path, metadata, token=session_token, purpose=purpose)
        finally:
            _release_lock(reuse_lock_key, reuse_lock_value)

    try:
        _extract_archive_to_path(target_archive=target, data_path=lower_path)
        session_token = uuid.uuid4().hex
        upper_path: Path | None = None
        work_path: Path | None = None
        mount_target = lower_path

        if mode == "mutate":
            upper_path = _upper_data_path(wd_path=wd_path, root=normalized_root, token=session_token)
            work_path = _work_path(wd_path=wd_path, root=normalized_root, token=session_token)
            _remove_tree(upper_path.parent)
            shutil.copytree(lower_path, upper_path)
            work_path.mkdir(parents=True, exist_ok=True)
            mount_target = upper_path

        _ensure_mount_points_to(
            wd_path=wd_path,
            root=normalized_root,
            mount_path=mount_path,
            target_path=mount_target,
        )

        metadata = _build_metadata(
            wd_path=wd_path,
            root=normalized_root,
            mode=mode,
            purpose=purpose,
            archive_fp=target.archive_fp,
            lock_key=lock_key,
            lock_value=lock_value,
            token=session_token,
            lower_path=lower_path,
            mount_path=mount_path,
            upper_path=upper_path,
            work_path=work_path,
        )
        _write_metadata(metadata_path, metadata)
        return _metadata_to_handle(metadata_path, metadata, token=session_token, purpose=purpose)
    except Exception:
        _release_lock(lock_key, lock_value)
        raise


def _load_handle_metadata(handle: ProjectionHandle) -> tuple[Path, dict]:
    metadata_path = Path(handle.metadata_path)
    metadata = _load_metadata(metadata_path)
    if metadata is None:
        raise nodir_invalid_archive("projection metadata is missing or invalid")
    return metadata_path, metadata


def _iter_staged_sidecars(commit_wd: Path, root: NoDirRoot) -> list[Path]:
    sidecars: list[Path] = []
    for candidate in sorted(commit_wd.glob(f"{root}*.parquet")):
        name = candidate.name
        if name == f"{root}.parquet" or name.startswith(f"{root}."):
            sidecars.append(candidate)
    return sidecars


def commit_mutation_projection(handle: ProjectionHandle) -> None:
    if handle.mode != "mutate":
        raise ValueError("commit_mutation_projection requires mode='mutate'")

    metadata_path, metadata = _load_handle_metadata(handle)
    lock_key = str(metadata.get("lock_key", handle.lock_key))
    reuse_lock_key, reuse_lock_value = _acquire_reuse_lock(lock_key, purpose="nodir-projection-commit")
    try:
        metadata_path, metadata = _load_handle_metadata(handle)
        mutation_state = str(metadata.get("mutation_state", ""))
        if mutation_state in {"committed", "aborted"}:
            return
        if mutation_state != "active":
            raise nodir_invalid_archive("mutation projection metadata is invalid")

        _assert_active_ownership(metadata, handle)

        mount_path = Path(handle.mount_path)
        upper_path_raw = metadata.get("upper_path")
        if not isinstance(upper_path_raw, str) or upper_path_raw.strip() == "":
            raise nodir_invalid_archive("mutation projection upper layer is missing")
        upper_path = Path(upper_path_raw)
        if not upper_path.exists() or not upper_path.is_dir():
            raise nodir_invalid_archive("mutation projection upper layer is missing")

        wd_path = Path(os.path.abspath(handle.wd))
        commit_wd = wd_path / ".nodir" / "work" / handle.root / handle.token / "commit"
        _remove_tree(commit_wd)
        commit_root = commit_wd / handle.root
        commit_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(upper_path, commit_root)

        archive_path = wd_path / f"{handle.root}.nodir"
        tmp_archive = commit_wd / f"{handle.root}.nodir.tmp.{uuid.uuid4().hex}.proj"
        _move_parquet_sidecars(commit_wd, handle.root, commit_root)
        _write_archive_from_directory(wd_path=commit_wd, root_path=commit_root, tmp_archive=tmp_archive)
        _verify_archive(tmp_archive)
        os.replace(tmp_archive, archive_path)

        for staged_sidecar in _iter_staged_sidecars(commit_wd, handle.root):
            final_sidecar = wd_path / staged_sidecar.name
            os.replace(staged_sidecar, final_sidecar)

        metadata["mutation_state"] = "committed"
        metadata["updated_at"] = _now_iso_utc()
        _write_metadata(metadata_path, metadata)

        _teardown_mount(mount_path=mount_path, expected_target=upper_path)
    finally:
        _release_lock(reuse_lock_key, reuse_lock_value)


def abort_mutation_projection(handle: ProjectionHandle) -> None:
    if handle.mode != "mutate":
        raise ValueError("abort_mutation_projection requires mode='mutate'")

    metadata_path, metadata = _load_handle_metadata(handle)
    lock_key = str(metadata.get("lock_key", handle.lock_key))
    reuse_lock_key, reuse_lock_value = _acquire_reuse_lock(lock_key, purpose="nodir-projection-abort")
    try:
        metadata_path, metadata = _load_handle_metadata(handle)
        mutation_state = str(metadata.get("mutation_state", ""))
        if mutation_state in {"aborted", "committed"}:
            return

        _assert_active_ownership(metadata, handle)

        mount_path = Path(handle.mount_path)
        upper_path_raw = metadata.get("upper_path")
        work_path_raw = metadata.get("work_path")
        upper_path = Path(str(upper_path_raw)) if upper_path_raw else None
        if upper_path is not None:
            _teardown_mount(mount_path=mount_path, expected_target=upper_path)
            _remove_tree(upper_path.parent)
        if work_path_raw:
            _remove_tree(Path(str(work_path_raw)))

        metadata["mutation_state"] = "aborted"
        metadata["updated_at"] = _now_iso_utc()
        _write_metadata(metadata_path, metadata)
    finally:
        _release_lock(reuse_lock_key, reuse_lock_value)


def release_root_projection(handle: ProjectionHandle) -> None:
    metadata_path = Path(handle.metadata_path)
    metadata = _load_metadata(metadata_path)
    if metadata is None:
        return

    lock_key = str(metadata.get("lock_key", handle.lock_key))
    try:
        reuse_lock_key, reuse_lock_value = _acquire_reuse_lock(lock_key, purpose="nodir-projection-release")
    except NoDirError:
        # Fail closed on concurrent acquire/release windows.
        return

    try:
        metadata = _load_metadata(metadata_path)
        if metadata is None:
            return

        mode = str(metadata.get("mode"))
        if mode not in {"read", "mutate"}:
            metadata_path.unlink(missing_ok=True)
            return

        sessions = metadata.get("sessions")
        if not isinstance(sessions, list):
            sessions = []
        if handle.token not in sessions:
            return

        sessions = [token for token in sessions if token != handle.token]
        metadata["sessions"] = sessions
        metadata["refcount"] = max(0, int(metadata.get("refcount", 0)) - 1)
        metadata["updated_at"] = _now_iso_utc()

        if int(metadata["refcount"]) > 0:
            _write_metadata(metadata_path, metadata)
            return

        mount_path = Path(str(metadata.get("mount_path", handle.mount_path)))
        lower_path = Path(str(metadata.get("lower_path", handle.lower_path)))
        upper_path_raw = metadata.get("upper_path")
        work_path_raw = metadata.get("work_path")

        if mode == "mutate":
            state = str(metadata.get("mutation_state", "active"))
            if state == "active":
                metadata["mutation_state"] = "aborted"
                metadata["updated_at"] = _now_iso_utc()
            if upper_path_raw:
                upper_path = Path(str(upper_path_raw))
                _teardown_mount(mount_path=mount_path, expected_target=upper_path)
                _remove_tree(upper_path.parent)
            if work_path_raw:
                _remove_tree(Path(str(work_path_raw)))
        else:
            _teardown_mount(mount_path=mount_path, expected_target=lower_path)

        _remove_tree(lower_path.parent)
        projection_lock_key = str(metadata.get("lock_key", handle.lock_key))
        projection_lock_value = str(metadata.get("lock_value", handle.lock_value))
        metadata_path.unlink(missing_ok=True)
        _release_lock(projection_lock_key, projection_lock_value)
    finally:
        _release_lock(reuse_lock_key, reuse_lock_value)


@contextmanager
def with_root_projection(
    wd: str | Path,
    root: str,
    *,
    mode: ProjectionMode,
    purpose: str,
) -> Iterator[ProjectionHandle]:
    handle = acquire_root_projection(wd, root, mode=mode, purpose=purpose)
    try:
        yield handle
    finally:
        release_root_projection(handle)
