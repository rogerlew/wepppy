"""Directory-only lock and thaw/freeze compatibility helpers."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import uuid
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any

from .errors import nodir_locked
from .paths import NoDirRoot, NODIR_ROOTS

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
    lock_path: str
    expires_at: int


_DEFAULT_LOCK_TTL_SECONDS = 6 * 3600


def _normalize_root(root: str) -> NoDirRoot:
    if root not in NODIR_ROOTS:
        raise ValueError(f"unsupported root: {root}")
    return root


def _runid_from_wd(wd_path: Path) -> str:
    parts = wd_path.parts
    if "_pups" in parts:
        pups_idx = parts.index("_pups")
        if pups_idx > 0:
            return parts[pups_idx - 1]
    if "runs" in parts:
        runs_idx = parts.index("runs")
        if runs_idx + 2 < len(parts):
            return parts[runs_idx + 2]
    return wd_path.name


def _lock_path(runid: str, root: NoDirRoot) -> Path:
    lock_root = Path(
        os.getenv("WEPP_RUNTIME_PATH_LOCK_ROOT", "/tmp/wepppy-runtime-path-locks")
    )
    safe_runid = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in runid)
    if not safe_runid:
        safe_runid = "run"
    digest = hashlib.sha1(runid.encode("utf-8")).hexdigest()[:8]
    filename = f"{safe_runid[:80]}.{digest}.{root}.lock"
    return lock_root / filename


def _read_lock_payload(lock_path: Path) -> dict[str, Any] | None:
    try:
        raw = lock_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _raise_locked(root: NoDirRoot, payload: dict[str, Any] | None = None) -> None:
    if payload is None:
        raise nodir_locked(f"{root} maintenance lock is already held")
    owner = payload.get("owner")
    expires_at = payload.get("expires_at")
    owner_str = str(owner) if isinstance(owner, str) and owner else "unknown-owner"
    expiry_str = str(expires_at) if isinstance(expires_at, int) else "unknown-expiry"
    raise nodir_locked(
        f"{root} maintenance lock is already held by {owner_str} (expires_at={expiry_str})"
    )


def maintenance_lock_key(wd: str | Path, root: str) -> str:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)
    runid = _runid_from_wd(wd_path)
    return f"nodb-lock:{runid}:runtime-paths/{normalized_root}"


def acquire_maintenance_lock(
    wd: str | Path,
    root: str,
    *,
    purpose: str = "runtime-path-maintenance",
    ttl_seconds: int | None = None,
) -> NoDirMaintenanceLock:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)
    runid = _runid_from_wd(wd_path)
    key = maintenance_lock_key(wd_path, normalized_root)
    ttl = max(1, int(ttl_seconds)) if ttl_seconds is not None else _DEFAULT_LOCK_TTL_SECONDS
    now = int(time())
    expires_at = now + ttl
    host = socket.gethostname()
    pid = os.getpid()
    token = uuid.uuid4().hex
    owner = f"{host}:{pid}"
    lock_path = _lock_path(runid, normalized_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _read_lock_payload(lock_path)
    if existing is not None:
        existing_expiry = existing.get("expires_at")
        if isinstance(existing_expiry, int) and existing_expiry <= now:
            with suppress(FileNotFoundError):
                lock_path.unlink()
        else:
            _raise_locked(normalized_root, existing)

    payload = {
        "token": token,
        "owner": owner,
        "runid": runid,
        "root": normalized_root,
        "purpose": purpose,
        "acquired_at": now,
        "expires_at": expires_at,
        "ttl_seconds": ttl,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    try:
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _raise_locked(normalized_root, _read_lock_payload(lock_path))
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(serialized)

    return NoDirMaintenanceLock(
        key=key,
        value=purpose,
        root=normalized_root,
        runid=runid,
        host=host,
        pid=pid,
        owner=owner,
        token=token,
        lock_path=str(lock_path),
        expires_at=expires_at,
    )


def release_maintenance_lock(lock: NoDirMaintenanceLock) -> None:
    lock_path = Path(lock.lock_path)
    payload = _read_lock_payload(lock_path)
    if payload is None:
        return
    if payload.get("token") != lock.token:
        return
    with suppress(FileNotFoundError):
        lock_path.unlink()


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
    purpose: str = "runtime-path-maintenance",
    ttl_seconds: int | None = None,
) -> _MaintenanceLockContext:
    return _MaintenanceLockContext(
        wd,
        root,
        purpose=purpose,
        ttl_seconds=ttl_seconds,
    )


def _state_payload(root: NoDirRoot, lock: NoDirMaintenanceLock, state: str) -> dict[str, Any]:
    return {
        "state": state,
        "root": root,
        "dirty": False,
        "archive_fingerprint": None,
        "op_id": lock.token,
    }


def thaw_locked(
    wd: str | Path,
    root: str,
    *,
    lock: NoDirMaintenanceLock,
) -> dict[str, Any]:
    _ = wd
    normalized_root = _normalize_root(root)
    if lock.root != normalized_root:
        raise ValueError(
            f"maintenance lock root mismatch: expected {normalized_root}, got {lock.root}"
        )
    return _state_payload(normalized_root, lock, "directory")


def thaw(wd: str | Path, root: str) -> dict[str, Any]:
    with maintenance_lock(wd, root, purpose="runtime-path-thaw") as lock:
        return thaw_locked(wd, root, lock=lock)


def freeze_locked(
    wd: str | Path,
    root: str,
    *,
    lock: NoDirMaintenanceLock,
) -> dict[str, Any]:
    _ = wd
    normalized_root = _normalize_root(root)
    if lock.root != normalized_root:
        raise ValueError(
            f"maintenance lock root mismatch: expected {normalized_root}, got {lock.root}"
        )
    return _state_payload(normalized_root, lock, "directory")


def freeze(wd: str | Path, root: str) -> dict[str, Any]:
    with maintenance_lock(wd, root, purpose="runtime-path-freeze") as lock:
        return freeze_locked(wd, root, lock=lock)
