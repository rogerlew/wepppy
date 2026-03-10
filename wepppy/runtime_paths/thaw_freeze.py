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
from typing import Any, Literal, cast

from .errors import nodir_locked
from .paths import NoDirRoot, NODIR_ROOTS

__all__ = [
    "NoDirMaintenanceLock",
    "NoDirMaintenanceLockScope",
    "maintenance_lock_scope_token",
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
    scope: "NoDirMaintenanceLockScope"
    scope_token: str
    host: str
    pid: int
    owner: str
    token: str
    lock_path: str
    expires_at: int


_DEFAULT_LOCK_TTL_SECONDS = 6 * 3600

NoDirMaintenanceLockScope = Literal[
    "legacy_runid",
    "effective_root_path",
    "effective_root_path_compat",
]

_LOCK_SCOPES: tuple[NoDirMaintenanceLockScope, ...] = (
    "legacy_runid",
    "effective_root_path",
    "effective_root_path_compat",
)


def _normalize_root(root: str) -> NoDirRoot:
    if root not in NODIR_ROOTS:
        raise ValueError(f"unsupported root: {root}")
    return root


def _normalize_scope(scope: str) -> NoDirMaintenanceLockScope:
    if scope not in _LOCK_SCOPES:
        raise ValueError(f"unsupported maintenance lock scope: {scope}")
    return cast(NoDirMaintenanceLockScope, scope)


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


def _effective_root_path_scope_token(wd_path: Path, root: NoDirRoot) -> str:
    root_path = wd_path / root
    try:
        resolved = root_path.resolve(strict=False)
    except (OSError, RuntimeError):
        resolved = Path(os.path.realpath(str(root_path)))
    return os.path.normcase(os.path.normpath(str(resolved)))


def _scope_token_for_scope(
    wd_path: Path,
    root: NoDirRoot,
    scope: NoDirMaintenanceLockScope,
) -> str:
    if scope == "legacy_runid":
        return _runid_from_wd(wd_path)
    return _effective_root_path_scope_token(wd_path, root)


def _lock_key_for_scope(
    scope_token: str,
    root: NoDirRoot,
    *,
    scope: NoDirMaintenanceLockScope,
) -> str:
    if scope == "legacy_runid":
        return f"nodb-lock:{scope_token}:runtime-paths/{root}"
    digest = hashlib.sha1(scope_token.encode("utf-8")).hexdigest()[:12]
    return f"nodb-lock:path-scope:{digest}:runtime-paths/{root}"


def _lock_path(scope_token: str, root: NoDirRoot) -> Path:
    lock_root = Path(
        os.getenv("WEPP_RUNTIME_PATH_LOCK_ROOT", "/tmp/wepppy-runtime-path-locks")
    )
    safe_scope_token = "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in scope_token
    )
    if not safe_scope_token:
        safe_scope_token = "scope"
    digest = hashlib.sha1(scope_token.encode("utf-8")).hexdigest()[:8]
    filename = f"{safe_scope_token[:80]}.{digest}.{root}.lock"
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


def _active_lock_payload(lock_path: Path, now: int) -> dict[str, Any] | None:
    existing = _read_lock_payload(lock_path)
    if existing is None:
        return None
    existing_expiry = existing.get("expires_at")
    if isinstance(existing_expiry, int) and existing_expiry <= now:
        with suppress(FileNotFoundError):
            lock_path.unlink()
        return None
    return existing


def maintenance_lock_scope_token(
    wd: str | Path,
    root: str,
    *,
    scope: NoDirMaintenanceLockScope = "legacy_runid",
) -> str:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)
    normalized_scope = _normalize_scope(scope)
    return _scope_token_for_scope(wd_path, normalized_root, normalized_scope)


def maintenance_lock_key(
    wd: str | Path,
    root: str,
    *,
    scope: NoDirMaintenanceLockScope = "legacy_runid",
    scope_token: str | None = None,
) -> str:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)
    normalized_scope = _normalize_scope(scope)
    resolved_scope_token = (
        scope_token
        if scope_token is not None
        else _scope_token_for_scope(wd_path, normalized_root, normalized_scope)
    )
    return _lock_key_for_scope(
        resolved_scope_token,
        normalized_root,
        scope=normalized_scope,
    )


def acquire_maintenance_lock(
    wd: str | Path,
    root: str,
    *,
    purpose: str = "runtime-path-maintenance",
    ttl_seconds: int | None = None,
    scope: NoDirMaintenanceLockScope = "legacy_runid",
    scope_token: str | None = None,
) -> NoDirMaintenanceLock:
    wd_path = Path(os.path.abspath(str(wd)))
    normalized_root = _normalize_root(root)
    normalized_scope = _normalize_scope(scope)
    runid = _runid_from_wd(wd_path)
    resolved_scope_token = (
        scope_token
        if scope_token is not None
        else _scope_token_for_scope(wd_path, normalized_root, normalized_scope)
    )
    key = maintenance_lock_key(
        wd_path,
        normalized_root,
        scope=normalized_scope,
        scope_token=resolved_scope_token,
    )
    ttl = max(1, int(ttl_seconds)) if ttl_seconds is not None else _DEFAULT_LOCK_TTL_SECONDS
    now = int(time())
    expires_at = now + ttl
    host = socket.gethostname()
    pid = os.getpid()
    token = uuid.uuid4().hex
    owner = f"{host}:{pid}"
    primary_lock_path = _lock_path(resolved_scope_token, normalized_root)
    compatibility_lock_paths = [primary_lock_path]
    if normalized_scope == "effective_root_path_compat":
        legacy_scope_token = _scope_token_for_scope(wd_path, normalized_root, "legacy_runid")
        legacy_lock_path = _lock_path(legacy_scope_token, normalized_root)
        if legacy_lock_path != primary_lock_path:
            compatibility_lock_paths.append(legacy_lock_path)
    primary_lock_path.parent.mkdir(parents=True, exist_ok=True)

    for lock_path in compatibility_lock_paths:
        existing = _active_lock_payload(lock_path, now)
        if existing is not None:
            _raise_locked(normalized_root, existing)

    payload = {
        "token": token,
        "owner": owner,
        "runid": runid,
        "root": normalized_root,
        "scope": normalized_scope,
        "scope_token": resolved_scope_token,
        "purpose": purpose,
        "acquired_at": now,
        "expires_at": expires_at,
        "ttl_seconds": ttl,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    try:
        fd = os.open(primary_lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _raise_locked(normalized_root, _read_lock_payload(primary_lock_path))
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(serialized)

    if normalized_scope == "effective_root_path_compat":
        for lock_path in compatibility_lock_paths[1:]:
            existing = _active_lock_payload(lock_path, now)
            if existing is None:
                continue
            with suppress(FileNotFoundError):
                primary_lock_path.unlink()
            _raise_locked(normalized_root, existing)

    return NoDirMaintenanceLock(
        key=key,
        value=purpose,
        root=normalized_root,
        runid=runid,
        scope=normalized_scope,
        scope_token=resolved_scope_token,
        host=host,
        pid=pid,
        owner=owner,
        token=token,
        lock_path=str(primary_lock_path),
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
        scope: NoDirMaintenanceLockScope,
        scope_token: str | None,
    ) -> None:
        self._wd = wd
        self._root = root
        self._purpose = purpose
        self._ttl_seconds = ttl_seconds
        self._scope = scope
        self._scope_token = scope_token
        self._lock: NoDirMaintenanceLock | None = None

    def __enter__(self) -> NoDirMaintenanceLock:
        self._lock = acquire_maintenance_lock(
            self._wd,
            self._root,
            purpose=self._purpose,
            ttl_seconds=self._ttl_seconds,
            scope=self._scope,
            scope_token=self._scope_token,
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
    scope: NoDirMaintenanceLockScope = "legacy_runid",
    scope_token: str | None = None,
) -> _MaintenanceLockContext:
    return _MaintenanceLockContext(
        wd,
        root,
        purpose=purpose,
        ttl_seconds=ttl_seconds,
        scope=scope,
        scope_token=scope_token,
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
