"""NoDir thaw/freeze state file helpers.

This module owns the per-root maintenance state file:
``WD/.nodir/<root>.json``.
"""

from __future__ import annotations

import json
import os
import socket
import stat as statmod
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping, TypedDict, cast

from .paths import NODIR_ROOTS, NoDirRoot

__all__ = [
    "NoDirStateName",
    "NoDirArchiveFingerprint",
    "NoDirStatePayload",
    "NODIR_STATE_SCHEMA_VERSION",
    "NODIR_TRANSITION_STATES",
    "state_path",
    "thaw_temp_path",
    "freeze_temp_path",
    "archive_fingerprint_from_path",
    "build_state_payload",
    "validate_state_payload",
    "read_state",
    "write_state",
    "is_transitioning_locked",
]


NoDirStateName = Literal["archived", "thawing", "thawed", "freezing"]

NODIR_STATE_SCHEMA_VERSION = 1
NODIR_TRANSITION_STATES: frozenset[NoDirStateName] = frozenset({"thawing", "freezing"})

_REQUIRED_FIELDS = (
    "schema_version",
    "root",
    "state",
    "op_id",
    "host",
    "pid",
    "lock_owner",
    "dir_path",
    "archive_path",
    "dirty",
    "archive_fingerprint",
    "updated_at",
)
_OPTIONAL_FIELDS = ("note",)
_ALLOWED_FIELDS = frozenset((*_REQUIRED_FIELDS, *_OPTIONAL_FIELDS))


class NoDirArchiveFingerprint(TypedDict):
    mtime_ns: int
    size_bytes: int


class NoDirStatePayload(TypedDict, total=False):
    schema_version: int
    root: NoDirRoot
    state: NoDirStateName
    op_id: str
    host: str
    pid: int
    lock_owner: str
    dir_path: str
    archive_path: str
    dirty: bool
    archive_fingerprint: NoDirArchiveFingerprint
    updated_at: str
    note: str


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_int_not_bool(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _normalize_root(root: str) -> NoDirRoot:
    if root not in NODIR_ROOTS:
        raise ValueError(f"unsupported NoDir root: {root}")
    return cast(NoDirRoot, root)


def _default_archive_fingerprint() -> NoDirArchiveFingerprint:
    return {"mtime_ns": 0, "size_bytes": 0}


def _validate_uuid4(op_id: str) -> str:
    try:
        op_uuid = uuid.UUID(op_id)
    except ValueError as exc:
        raise ValueError("op_id must be a valid UUID4") from exc
    if op_uuid.version != 4:
        raise ValueError("op_id must be a UUID4")
    return op_id


def state_path(wd: str | Path, root: str) -> Path:
    normalized_root = _normalize_root(root)
    wd_path = Path(os.path.abspath(str(wd)))
    return wd_path / ".nodir" / f"{normalized_root}.json"


def thaw_temp_path(wd: str | Path, root: str) -> Path:
    normalized_root = _normalize_root(root)
    wd_path = Path(os.path.abspath(str(wd)))
    return wd_path / f"{normalized_root}.thaw.tmp"


def freeze_temp_path(wd: str | Path, root: str) -> Path:
    normalized_root = _normalize_root(root)
    wd_path = Path(os.path.abspath(str(wd)))
    return wd_path / f"{normalized_root}.nodir.tmp"


def archive_fingerprint_from_path(archive_path: str | Path) -> NoDirArchiveFingerprint:
    path = Path(archive_path)
    st = path.stat()
    if not statmod.S_ISREG(st.st_mode):
        raise ValueError(f"archive path is not a regular file: {path}")
    mtime_ns = getattr(st, "st_mtime_ns", None)
    if mtime_ns is None:
        mtime_ns = int(st.st_mtime * 1_000_000_000)
    return {"mtime_ns": int(mtime_ns), "size_bytes": int(st.st_size)}


def _validate_archive_fingerprint(value: Any) -> NoDirArchiveFingerprint:
    if not isinstance(value, Mapping):
        raise ValueError("archive_fingerprint must be an object")

    raw_mtime = value.get("mtime_ns")
    raw_size = value.get("size_bytes")
    if not _is_int_not_bool(raw_mtime) or int(raw_mtime) < 0:
        raise ValueError("archive_fingerprint.mtime_ns must be an integer >= 0")
    if not _is_int_not_bool(raw_size) or int(raw_size) < 0:
        raise ValueError("archive_fingerprint.size_bytes must be an integer >= 0")

    return {"mtime_ns": int(raw_mtime), "size_bytes": int(raw_size)}


def validate_state_payload(
    payload: Mapping[str, Any],
    *,
    root: str | None = None,
) -> NoDirStatePayload:
    if not isinstance(payload, Mapping):
        raise ValueError("state payload must be an object")

    unexpected = sorted(set(payload.keys()) - _ALLOWED_FIELDS)
    if unexpected:
        raise ValueError(f"unexpected state fields: {', '.join(unexpected)}")

    missing = [name for name in _REQUIRED_FIELDS if name not in payload]
    if missing:
        raise ValueError(f"missing required state fields: {', '.join(missing)}")

    schema_version = payload.get("schema_version")
    if not _is_int_not_bool(schema_version):
        raise ValueError(f"unsupported schema_version: {schema_version}")
    if int(schema_version) != NODIR_STATE_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {schema_version}")

    payload_root = _normalize_root(str(payload.get("root")))
    if root is not None and payload_root != _normalize_root(root):
        raise ValueError(f"state root mismatch: expected {root}, got {payload_root}")

    payload_state = str(payload.get("state"))
    if payload_state not in ("archived", "thawing", "thawed", "freezing"):
        raise ValueError(f"invalid state value: {payload_state}")
    state_value = cast(NoDirStateName, payload_state)

    op_id_raw = payload.get("op_id")
    if not isinstance(op_id_raw, str) or op_id_raw.strip() == "":
        raise ValueError("op_id must be a non-empty string")
    op_id = _validate_uuid4(op_id_raw.strip())

    host = payload.get("host")
    if not isinstance(host, str) or host.strip() == "":
        raise ValueError("host must be a non-empty string")
    host = host.strip()

    pid = payload.get("pid")
    if not _is_int_not_bool(pid) or int(pid) < 1:
        raise ValueError("pid must be an integer >= 1")
    pid_value = int(pid)

    lock_owner = payload.get("lock_owner")
    if not isinstance(lock_owner, str) or lock_owner.strip() == "":
        raise ValueError("lock_owner must be a non-empty string")
    expected_owner = f"{host}:{pid_value}"
    if lock_owner != expected_owner:
        raise ValueError(f"lock_owner must equal host:pid ({expected_owner})")

    dir_path = payload.get("dir_path")
    if dir_path != payload_root:
        raise ValueError(f"dir_path must equal root ({payload_root})")
    if any(segment in str(dir_path) for segment in ("/", "\\", "..")):
        raise ValueError("dir_path must not contain separators or traversal segments")

    archive_path = payload.get("archive_path")
    expected_archive_path = f"{payload_root}.nodir"
    if archive_path != expected_archive_path:
        raise ValueError(f"archive_path must equal {expected_archive_path}")
    if any(segment in str(archive_path) for segment in ("/", "\\", "..")):
        raise ValueError("archive_path must not contain separators or traversal segments")

    dirty = payload.get("dirty")
    if not isinstance(dirty, bool):
        raise ValueError("dirty must be a boolean")

    archive_fingerprint = _validate_archive_fingerprint(payload.get("archive_fingerprint"))

    updated_at = payload.get("updated_at")
    if not isinstance(updated_at, str) or updated_at.strip() == "":
        raise ValueError("updated_at must be a non-empty string")
    updated_at = updated_at.strip()
    try:
        datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("updated_at must be UTC ISO-8601 (YYYY-MM-DDTHH:MM:SSZ)") from exc

    note = payload.get("note")
    if note is not None and not isinstance(note, str):
        raise ValueError("note must be a string when present")

    normalized: NoDirStatePayload = {
        "schema_version": int(schema_version),
        "root": payload_root,
        "state": state_value,
        "op_id": op_id,
        "host": host,
        "pid": pid_value,
        "lock_owner": lock_owner,
        "dir_path": str(dir_path),
        "archive_path": str(archive_path),
        "dirty": bool(dirty),
        "archive_fingerprint": archive_fingerprint,
        "updated_at": updated_at,
    }
    if note is not None:
        normalized["note"] = note
    return normalized


def build_state_payload(
    *,
    root: str,
    state: NoDirStateName,
    op_id: str,
    dirty: bool,
    archive_fingerprint: Mapping[str, Any] | None = None,
    host: str | None = None,
    pid: int | None = None,
    lock_owner: str | None = None,
    updated_at: str | None = None,
    note: str | None = None,
) -> NoDirStatePayload:
    normalized_root = _normalize_root(root)
    host_value = (host or socket.gethostname()).strip()
    if pid is None:
        pid_value = os.getpid()
    else:
        if not _is_int_not_bool(pid) or int(pid) < 1:
            raise ValueError("pid must be an integer >= 1")
        pid_value = int(pid)
    owner_value = lock_owner or f"{host_value}:{pid_value}"
    archive_fp = archive_fingerprint if archive_fingerprint is not None else _default_archive_fingerprint()

    payload: NoDirStatePayload = {
        "schema_version": NODIR_STATE_SCHEMA_VERSION,
        "root": normalized_root,
        "state": state,
        "op_id": str(op_id),
        "host": host_value,
        "pid": pid_value,
        "lock_owner": owner_value,
        "dir_path": normalized_root,
        "archive_path": f"{normalized_root}.nodir",
        "dirty": bool(dirty),
        "archive_fingerprint": _validate_archive_fingerprint(archive_fp),
        "updated_at": updated_at or _now_iso_utc(),
    }
    if note is not None:
        payload["note"] = note

    return validate_state_payload(payload, root=normalized_root)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True)

    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def read_state(wd: str | Path, root: str, *, strict: bool = True) -> NoDirStatePayload | None:
    path = state_path(wd, root)
    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        if strict:
            raise ValueError(f"invalid state file {path}: {exc}") from exc
        return None

    try:
        return validate_state_payload(cast(Mapping[str, Any], raw_payload), root=root)
    except ValueError:
        if strict:
            raise
        return None


def write_state(
    wd: str | Path,
    root: str,
    *,
    state: NoDirStateName,
    op_id: str,
    dirty: bool,
    archive_fingerprint: Mapping[str, Any] | None = None,
    host: str | None = None,
    pid: int | None = None,
    lock_owner: str | None = None,
    note: str | None = None,
) -> NoDirStatePayload:
    payload = build_state_payload(
        root=root,
        state=state,
        op_id=op_id,
        dirty=dirty,
        archive_fingerprint=archive_fingerprint,
        host=host,
        pid=pid,
        lock_owner=lock_owner,
        note=note,
    )
    _atomic_write_json(state_path(wd, root), payload)
    return payload


def is_transitioning_locked(wd: str | Path, root: str) -> bool:
    normalized_root = _normalize_root(root)
    if thaw_temp_path(wd, normalized_root).exists():
        return True
    if freeze_temp_path(wd, normalized_root).exists():
        return True

    state_file = state_path(wd, normalized_root)
    try:
        payload = read_state(wd, normalized_root, strict=True)
    except ValueError:
        return state_file.exists()
    if payload is None:
        return False
    return payload["state"] in NODIR_TRANSITION_STATES
