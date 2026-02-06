from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import json
import os

TTL_FILENAME = "TTL"
TTL_VERSION = 1
TTL_DAYS = 90

POLICY_ROLLING = "rolling_90d"
POLICY_DISABLED = "disabled"
POLICY_EXCLUDED = "excluded"

DISABLED_REASON_READONLY = "readonly"
DISABLED_REASON_USER = "user"
DISABLED_REASON_BATCH = "batch"

DELETE_STATE_ACTIVE = "active"
DELETE_STATE_QUEUED = "queued"
DELETE_STATE_TRASH = "trash"
DELETE_STATE_PURGED = "purged"

__all__ = [
    "TTL_FILENAME",
    "TTL_VERSION",
    "TTL_DAYS",
    "POLICY_ROLLING",
    "POLICY_DISABLED",
    "POLICY_EXCLUDED",
    "DISABLED_REASON_READONLY",
    "DISABLED_REASON_USER",
    "DISABLED_REASON_BATCH",
    "DELETE_STATE_ACTIVE",
    "DELETE_STATE_QUEUED",
    "DELETE_STATE_TRASH",
    "DELETE_STATE_PURGED",
    "initialize_ttl",
    "touch_ttl",
    "set_user_ttl_disabled",
    "sync_ttl_policy",
    "mark_delete_state",
    "read_ttl_state",
    "touch_ttl_from_access_log",
    "collect_gc_candidates",
    "collect_expired_runs",
]


def ttl_path(wd: str) -> Path:
    return Path(wd) / TTL_FILENAME


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            raw = str(value).strip()
        except Exception:
            return None
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_datetime(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _compute_expiration(base_time: datetime, ttl_days: int = TTL_DAYS) -> datetime:
    return base_time + timedelta(days=ttl_days)


def _is_readonly(wd: str) -> bool:
    return os.path.exists(os.path.join(wd, "READONLY"))


def _is_batch_wd(wd: str) -> bool:
    try:
        from wepppy.weppcloud.utils.helpers import get_batch_root_dir
    except Exception:
        return False

    try:
        root = Path(get_batch_root_dir()).resolve()
        target = Path(wd).resolve()
        target.relative_to(root)
        return True
    except Exception:
        return False


def _load_payload(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _write_payload(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    tmp_path.replace(path)


def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("version", TTL_VERSION)
    normalized.setdefault("ttl_days", TTL_DAYS)
    normalized.setdefault("policy", POLICY_ROLLING)
    normalized.setdefault("user_disabled", False)
    normalized.setdefault("disabled_by_user_id", None)
    normalized.setdefault("disabled_reason", None)
    normalized.setdefault("delete_state", DELETE_STATE_ACTIVE)
    normalized.setdefault("db_cleared", False)
    return normalized


def _apply_policy(
    payload: Dict[str, Any],
    *,
    wd: str,
    now: datetime,
    touched_by: Optional[str] = None,
) -> Dict[str, Any]:
    normalized = _normalize_payload(payload)
    readonly = _is_readonly(wd)
    is_batch = _is_batch_wd(wd)
    user_disabled = bool(normalized.get("user_disabled"))

    if is_batch:
        policy = POLICY_EXCLUDED
        disabled_reason = DISABLED_REASON_BATCH
        user_disabled = False
        normalized["user_disabled"] = False
        normalized["disabled_by_user_id"] = None
    elif user_disabled:
        policy = POLICY_DISABLED
        disabled_reason = DISABLED_REASON_USER
    elif readonly:
        policy = POLICY_DISABLED
        disabled_reason = DISABLED_REASON_READONLY
    else:
        policy = POLICY_ROLLING
        disabled_reason = None

    normalized["policy"] = policy
    normalized["disabled_reason"] = disabled_reason

    if not user_disabled:
        normalized["disabled_by_user_id"] = None

    if normalized.get("created_at") is None:
        normalized["created_at"] = _format_datetime(now)

    if policy == POLICY_ROLLING:
        last_accessed = _coerce_datetime(normalized.get("last_accessed_at"))
        if last_accessed is None:
            last_accessed = now
            normalized["last_accessed_at"] = _format_datetime(last_accessed)
        normalized["expires_at"] = _format_datetime(
            _compute_expiration(last_accessed, int(normalized.get("ttl_days", TTL_DAYS)))
        )

    normalized["updated_at"] = _format_datetime(now)
    if touched_by:
        normalized["last_touched_by"] = touched_by

    return normalized


def initialize_ttl(
    wd: str,
    *,
    now: Optional[datetime] = None,
    touched_by: str = "create",
) -> Optional[Dict[str, Any]]:
    """Create or reset the TTL metadata for a run."""
    wd_path = Path(wd)
    if not wd_path.is_dir():
        return None

    now = now or _utc_now()
    base = {
        "version": TTL_VERSION,
        "ttl_days": TTL_DAYS,
        "policy": POLICY_ROLLING,
        "user_disabled": False,
        "disabled_by_user_id": None,
        "disabled_reason": None,
        "created_at": _format_datetime(now),
        "last_accessed_at": _format_datetime(now),
        "expires_at": _format_datetime(_compute_expiration(now, TTL_DAYS)),
        "delete_state": DELETE_STATE_ACTIVE,
        "db_cleared": False,
        "updated_at": _format_datetime(now),
        "last_touched_by": touched_by,
    }
    payload = _apply_policy(base, wd=wd, now=now, touched_by=touched_by)
    _write_payload(ttl_path(wd), payload)
    return payload


def sync_ttl_policy(
    wd: str,
    *,
    now: Optional[datetime] = None,
    touched_by: str = "policy",
) -> Optional[Dict[str, Any]]:
    """Ensure the TTL policy matches current run flags (readonly/batch/user)."""
    wd_path = Path(wd)
    if not wd_path.is_dir():
        return None

    now = now or _utc_now()
    path = ttl_path(wd)
    payload = _load_payload(path) or {}
    payload = _apply_policy(payload, wd=wd, now=now, touched_by=touched_by)
    _write_payload(path, payload)
    return payload


def touch_ttl(
    wd: str,
    *,
    accessed_at: datetime,
    touched_by: str = "access_log",
) -> Optional[Dict[str, Any]]:
    """Update the TTL timestamps based on a run access event."""
    wd_path = Path(wd)
    if not wd_path.is_dir():
        return None

    accessed = _coerce_datetime(accessed_at) or _utc_now()
    path = ttl_path(wd)
    payload = _load_payload(path) or {}
    payload = _apply_policy(payload, wd=wd, now=accessed, touched_by=touched_by)

    if payload.get("policy") != POLICY_ROLLING:
        _write_payload(path, payload)
        return payload

    last_accessed = _coerce_datetime(payload.get("last_accessed_at"))
    if last_accessed is None or accessed > last_accessed:
        payload["last_accessed_at"] = _format_datetime(accessed)
        payload["expires_at"] = _format_datetime(
            _compute_expiration(accessed, int(payload.get("ttl_days", TTL_DAYS)))
        )
        payload["updated_at"] = _format_datetime(accessed)
        payload["last_touched_by"] = touched_by
        _write_payload(path, payload)
    else:
        _write_payload(path, payload)

    return payload


def set_user_ttl_disabled(
    wd: str,
    disabled: bool,
    user_id: Optional[str],
    *,
    now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Persist the user-level TTL disable override."""
    wd_path = Path(wd)
    if not wd_path.is_dir():
        return None

    now = now or _utc_now()
    path = ttl_path(wd)
    payload = _load_payload(path) or {}
    payload["user_disabled"] = bool(disabled)
    payload["disabled_by_user_id"] = str(user_id) if disabled and user_id is not None else None
    if not disabled:
        payload["last_accessed_at"] = _format_datetime(now)
        payload["expires_at"] = _format_datetime(_compute_expiration(now, TTL_DAYS))

    payload = _apply_policy(payload, wd=wd, now=now, touched_by="user_toggle")
    _write_payload(path, payload)
    return payload


def mark_delete_state(
    wd: str,
    state: str,
    *,
    db_cleared: Optional[bool] = None,
    touched_by: str = "delete",
) -> Optional[Dict[str, Any]]:
    """Record deletion lifecycle state in the TTL metadata."""
    wd_path = Path(wd)
    if not wd_path.is_dir():
        return None

    now = _utc_now()
    path = ttl_path(wd)
    payload = _load_payload(path) or {}
    payload = _apply_policy(payload, wd=wd, now=now, touched_by=touched_by)
    payload["delete_state"] = str(state)
    if db_cleared is not None:
        payload["db_cleared"] = bool(db_cleared)
    payload["updated_at"] = _format_datetime(now)
    payload["last_touched_by"] = touched_by
    _write_payload(path, payload)
    return payload


def read_ttl_state(wd: str) -> Optional[Dict[str, Any]]:
    """Return the TTL metadata without mutating it."""
    path = ttl_path(wd)
    payload = _load_payload(path)
    if payload is None:
        return None
    return _normalize_payload(payload)


def touch_ttl_from_access_log(runid: str, last_accessed: datetime) -> Optional[Dict[str, Any]]:
    from wepppy.weppcloud.utils.helpers import get_wd

    try:
        wd = get_wd(runid, prefer_active=False)
    except Exception:
        return None

    return touch_ttl(wd, accessed_at=last_accessed, touched_by="access_log")


def _iter_run_dirs(root: Path) -> Iterable[tuple[str, Path]]:
    if not root.is_dir():
        return []
    entries: list[tuple[str, Path]] = []
    for prefix in root.iterdir():
        if not prefix.is_dir():
            continue
        for run_dir in prefix.iterdir():
            if not run_dir.is_dir():
                continue
            runid = run_dir.name
            if not runid or runid.startswith("."):
                continue
            entries.append((runid, run_dir))
    return entries


def collect_expired_runs(
    root: str = "/wc1/runs",
    *,
    now: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> list[Dict[str, Any]]:
    """Return run metadata records for TTL-expired runs."""
    root_path = Path(root)
    now = now or _utc_now()

    expired: list[Dict[str, Any]] = []
    for runid, run_dir in _iter_run_dirs(root_path):
        payload = _load_payload(ttl_path(str(run_dir)))
        if not payload:
            continue

        if os.path.exists(run_dir / "READONLY"):
            continue
        if payload.get("user_disabled"):
            continue

        policy = payload.get("policy")
        if policy != POLICY_ROLLING:
            continue

        expires_at = _coerce_datetime(payload.get("expires_at"))
        if expires_at is None or expires_at > now:
            continue

        delete_state = payload.get("delete_state")
        if delete_state == DELETE_STATE_PURGED:
            continue

        expired.append({
            "runid": runid,
            "wd": str(run_dir),
            "expires_at": _format_datetime(expires_at),
            "ttl": _normalize_payload(payload),
        })

        if limit is not None and len(expired) >= limit:
            break

    return expired


def collect_gc_candidates(
    root: str = "/wc1/runs",
    *,
    now: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> list[Dict[str, Any]]:
    """Return run metadata records eligible for GC deletion."""
    root_path = Path(root)
    now = now or _utc_now()

    candidates: list[Dict[str, Any]] = []
    for runid, run_dir in _iter_run_dirs(root_path):
        payload = _load_payload(ttl_path(str(run_dir)))
        if not payload:
            continue

        delete_state = payload.get("delete_state")
        if delete_state in {DELETE_STATE_QUEUED, DELETE_STATE_TRASH}:
            candidates.append({
                "runid": runid,
                "wd": str(run_dir),
                "reason": "queued",
                "ttl": _normalize_payload(payload),
            })
            if limit is not None and len(candidates) >= limit:
                break
            continue

        if os.path.exists(run_dir / "READONLY"):
            continue
        if payload.get("user_disabled"):
            continue

        policy = payload.get("policy")
        if policy != POLICY_ROLLING:
            continue

        expires_at = _coerce_datetime(payload.get("expires_at"))
        if expires_at is None or expires_at > now:
            continue

        if delete_state == DELETE_STATE_PURGED:
            continue

        candidates.append({
            "runid": runid,
            "wd": str(run_dir),
            "reason": "expired",
            "expires_at": _format_datetime(expires_at),
            "ttl": _normalize_payload(payload),
        })

        if limit is not None and len(candidates) >= limit:
            break

    return candidates
