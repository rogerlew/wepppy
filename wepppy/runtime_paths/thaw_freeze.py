"""Redis-backed directory-only lock and thaw/freeze compatibility helpers."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import socket
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import time
from typing import Any, Literal, cast

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

from .errors import nodir_locked
from .paths import NoDirRoot, NODIR_ROOTS

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover - redis is optional in type-only contexts
    redis = None  # type: ignore

__all__ = [
    "NoDirMaintenanceLock",
    "NoDirMaintenanceLockScope",
    "maintenance_lock_scope_token",
    "maintenance_lock_key",
    "runtime_lock_statuses",
    "clear_runtime_locks",
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
    # Kept for compatibility with existing call sites; this now stores the
    # primary Redis lock key instead of a filesystem path.
    lock_path: str
    expires_at: int
    lock_keys: tuple[str, ...]
    payload: str


_DEFAULT_LOCK_TTL_SECONDS = 6 * 3600
_RUNTIME_LOCK_SCAN_PATTERN = "nodb-lock:*:runtime-paths/*"
_RUNTIME_LOCK_RUNTIME_PATHS_MARKER = ":runtime-paths/"
_COMPARE_AND_DELETE_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if current == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
""".strip()

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


def _serialize_lock_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _parse_lock_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"token": raw}
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def _runtime_lock_redis_client():
    if redis is None:
        raise RuntimeError("redis package is unavailable for runtime lock operations")
    try:
        kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
        client = redis.Redis(**kwargs)
        ping_fn = getattr(client, "ping", None)
        if callable(ping_fn):
            ping_fn()
        return client
    except (redis.exceptions.RedisError, OSError, TypeError, ValueError) as exc:
        raise RuntimeError("runtime lock Redis client is unavailable") from exc


def _delete_if_raw_matches(client, lock_key: str, expected_raw: str | None) -> bool:
    if not expected_raw:
        return False
    eval_fn = getattr(client, "eval", None)
    if callable(eval_fn):
        try:
            deleted = eval_fn(_COMPARE_AND_DELETE_SCRIPT, 1, lock_key, expected_raw)
            return bool(deleted)
        except redis.exceptions.RedisError as exc:
            raise RuntimeError("runtime lock Redis operation failed") from exc
    try:
        current = client.get(lock_key)
        if current != expected_raw:
            return False
        deleted = client.delete(lock_key)
        if deleted:
            return True
        return client.get(lock_key) is None
    except redis.exceptions.RedisError as exc:
        raise RuntimeError("runtime lock Redis operation failed") from exc


def _read_active_lock_payload(client, lock_key: str, now: int) -> dict[str, Any] | None:
    try:
        raw = client.get(lock_key)
    except redis.exceptions.RedisError as exc:
        raise RuntimeError("runtime lock Redis operation failed") from exc

    if not raw:
        return None

    payload = _parse_lock_payload(raw)
    existing_expiry = payload.get("expires_at")
    if isinstance(existing_expiry, int) and existing_expiry <= now:
        _delete_if_raw_matches(client, lock_key, raw)
        return None
    return payload


def _contended_lock_keys_for_scope(
    wd_path: Path,
    root: NoDirRoot,
    scope: NoDirMaintenanceLockScope,
    scope_token: str,
) -> tuple[str, ...]:
    primary_key = maintenance_lock_key(
        wd_path,
        root,
        scope=scope,
        scope_token=scope_token,
    )

    keys: list[str] = [primary_key]
    if scope == "effective_root_path_compat":
        legacy_scope_token = _scope_token_for_scope(wd_path, root, "legacy_runid")
        legacy_key = maintenance_lock_key(
            wd_path,
            root,
            scope="legacy_runid",
            scope_token=legacy_scope_token,
        )
        if legacy_key != primary_key:
            keys.append(legacy_key)

    return tuple(keys)


def _write_lock_keys_for_scope(
    wd_path: Path,
    root: NoDirRoot,
    scope: NoDirMaintenanceLockScope,
    scope_token: str,
) -> tuple[str, ...]:
    return (
        maintenance_lock_key(
            wd_path,
            root,
            scope=scope,
            scope_token=scope_token,
        ),
    )


def _raise_locked(root: NoDirRoot, payload: dict[str, Any] | None = None) -> None:
    if payload is None:
        raise nodir_locked(
            f"{root} maintenance lock is already held. "
            "If stale, run ':clear directory_locks' or wait for lock expiry."
        )

    owner = payload.get("owner")
    expires_at = payload.get("expires_at")
    owner_str = str(owner) if isinstance(owner, str) and owner else "unknown-owner"
    expiry_str = str(expires_at) if isinstance(expires_at, int) else "unknown-expiry"
    raise nodir_locked(
        f"{root} maintenance lock is already held by {owner_str} "
        f"(expires_at={expiry_str}). "
        "If stale, run ':clear directory_locks' or wait for lock expiry."
    )


def _release_lock_key(client, lock_key: str, token: str) -> bool:
    try:
        raw = client.get(lock_key)
    except redis.exceptions.RedisError as exc:
        raise RuntimeError("runtime lock Redis operation failed") from exc

    if not raw:
        return False

    payload = _parse_lock_payload(raw)
    if payload.get("token") != token:
        return False

    return _delete_if_raw_matches(client, lock_key, raw)


def _legacy_runid_from_lock_key(lock_key: str) -> str | None:
    marker_idx = lock_key.find(_RUNTIME_LOCK_RUNTIME_PATHS_MARKER)
    if marker_idx <= 0:
        return None

    prefix = "nodb-lock:"
    if not lock_key.startswith(prefix):
        return None

    middle = lock_key[len(prefix):marker_idx]
    # Path-scope keys look like `path-scope:<digest>`; they do not embed runid.
    if ":" in middle:
        return None
    return middle or None


def _payload_matches_runid(payload: dict[str, Any], lock_key: str, runid: str) -> bool:
    payload_runid = payload.get("runid")
    if isinstance(payload_runid, str) and payload_runid:
        return payload_runid == runid

    legacy_runid = _legacy_runid_from_lock_key(lock_key)
    return legacy_runid == runid


def _iter_runtime_lock_keys(client) -> list[str]:
    scan_iter_fn = getattr(client, "scan_iter", None)
    if callable(scan_iter_fn):
        try:
            return sorted(str(key) for key in scan_iter_fn(match=_RUNTIME_LOCK_SCAN_PATTERN))
        except redis.exceptions.RedisError as exc:
            raise RuntimeError("runtime lock Redis operation failed") from exc

    keys_fn = getattr(client, "keys", None)
    if callable(keys_fn):
        try:
            return sorted(str(key) for key in keys_fn(_RUNTIME_LOCK_SCAN_PATTERN))
        except redis.exceptions.RedisError as exc:
            raise RuntimeError("runtime lock Redis operation failed") from exc

    store = getattr(client, "store", None)
    if isinstance(store, dict):
        return sorted(
            str(key)
            for key in store.keys()
            if fnmatch.fnmatch(str(key), _RUNTIME_LOCK_SCAN_PATTERN)
        )

    return []


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


def runtime_lock_statuses(runid: str) -> list[dict[str, Any]]:
    """Return active runtime lock payloads for ``runid`` from Redis."""

    client = _runtime_lock_redis_client()
    now = int(time())
    statuses: list[dict[str, Any]] = []
    lock_keys = _iter_runtime_lock_keys(client)

    for lock_key in lock_keys:
        payload = _read_active_lock_payload(client, lock_key, now)
        if payload is None:
            continue
        if not _payload_matches_runid(payload, lock_key, runid):
            continue

        status_payload = {
            "key": lock_key,
            "owner": payload.get("owner"),
            "expires_at": payload.get("expires_at"),
            "acquired_at": payload.get("acquired_at"),
            "purpose": payload.get("purpose"),
            "root": payload.get("root"),
            "scope": payload.get("scope"),
            "scope_token": payload.get("scope_token"),
            "runid": payload.get("runid") or _legacy_runid_from_lock_key(lock_key),
            "token": payload.get("token"),
            "ttl_seconds": payload.get("ttl_seconds"),
        }
        statuses.append(status_payload)

    return statuses


def clear_runtime_locks(runid: str) -> list[dict[str, Any]]:
    """Clear active runtime locks for ``runid`` and return cleared payloads."""

    client = _runtime_lock_redis_client()
    statuses = runtime_lock_statuses(runid)

    cleared: list[dict[str, Any]] = []
    for status in statuses:
        key = status.get("key")
        if not isinstance(key, str) or not key:
            continue
        token = status.get("token")
        if isinstance(token, str) and token:
            if _release_lock_key(client, key, token):
                cleared.append(status)
            continue

        try:
            deleted = client.delete(key)
            if deleted:
                cleared.append(status)
                continue
            if not client.get(key):
                cleared.append(status)
        except redis.exceptions.RedisError as exc:
            raise RuntimeError("runtime lock Redis operation failed") from exc

    return cleared


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
    contended_lock_keys = _contended_lock_keys_for_scope(
        wd_path,
        normalized_root,
        normalized_scope,
        resolved_scope_token,
    )
    write_lock_keys = _write_lock_keys_for_scope(
        wd_path,
        normalized_root,
        normalized_scope,
        resolved_scope_token,
    )

    ttl = max(1, int(ttl_seconds)) if ttl_seconds is not None else _DEFAULT_LOCK_TTL_SECONDS
    now = int(time())
    expires_at = now + ttl
    host = socket.gethostname()
    pid = os.getpid()
    token = uuid.uuid4().hex
    owner = f"{host}:{pid}"

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
    serialized = _serialize_lock_payload(payload)

    client = _runtime_lock_redis_client()

    for lock_key in contended_lock_keys:
        existing = _read_active_lock_payload(client, lock_key, now)
        if existing is not None:
            _raise_locked(normalized_root, existing)

    acquired_keys: list[str] = []
    try:
        for lock_key in write_lock_keys:
            created = client.set(lock_key, serialized, nx=True, ex=ttl)
            if not created:
                existing = _read_active_lock_payload(client, lock_key, int(time()))
                for acquired_key in acquired_keys:
                    _release_lock_key(client, acquired_key, token)
                _raise_locked(normalized_root, existing)
            acquired_keys.append(lock_key)
    except redis.exceptions.RedisError as exc:
        for acquired_key in acquired_keys:
            _release_lock_key(client, acquired_key, token)
        raise RuntimeError("runtime lock Redis operation failed") from exc

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
        lock_path=key,
        expires_at=expires_at,
        lock_keys=tuple(acquired_keys),
        payload=serialized,
    )


def release_maintenance_lock(lock: NoDirMaintenanceLock) -> None:
    client = _runtime_lock_redis_client()
    lock_keys = lock.lock_keys or (lock.lock_path,)
    for lock_key in lock_keys:
        _release_lock_key(client, lock_key, lock.token)


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
