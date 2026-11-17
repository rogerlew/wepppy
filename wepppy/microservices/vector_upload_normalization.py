"""Bounded receiving-side vector upload retention and normalization.

This module owns project evidence publication and the trusted HTTP handoff to
shape-converter.  Workflow routes remain responsible for authentication,
workflow-specific validation, mutation locking, and response envelopes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import shutil
import stat
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable, Mapping, Protocol, Sequence

import requests
import redis
from werkzeug.utils import secure_filename

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

_ATTEMPT_LIMIT = 50
_ORIGINAL_BYTES_LIMIT = 1024 * 1024 * 1024
_LIVE_TREE_LIMIT = 1280 * 1024 * 1024
_TOTAL_EVIDENCE_LIMIT = 2560 * 1024 * 1024
_CANDIDATE_LIMIT = 32 * 1024 * 1024
_CONVERTER_RESPONSE_LIMIT = _CANDIDATE_LIMIT + 2 * 1024 * 1024
_RECEIPT_ALLOWANCE = 1024 * 1024
_GLOBAL_LIMIT = 100 * 1024 * 1024 * 1024
_PRINCIPAL_LIMIT = 10 * 1024 * 1024 * 1024
_UNATTRIBUTED_LIMIT = 1024 * 1024 * 1024
_GLOBAL_INFLIGHT_LIMIT = 8
_FREE_SPACE_RESERVE = 10 * 1024 * 1024 * 1024
_LEASE_SECONDS = 600
_CHUNK_BYTES = 1024 * 1024
_RECEIPT_NAME = "normalization.json"
_RECEIPT_SCHEMA = "vector-normalization-v1"
_BINARY_SUFFIXES = {".zip": "shapefile", ".parquet": "geoparquet", ".geoparquet": "geoparquet"}
_GEOJSON_SUFFIXES = {".geojson": "geojson", ".json": "geojson"}
_CONVERTER_CODES = {
    "invalid_archive": (400, "Uploaded vector archive is invalid."),
    "archive_path_traversal": (400, "Uploaded vector archive is invalid."),
    "missing_required_sidecar": (400, "Uploaded Shapefile is incomplete."),
    "invalid_shapefile": (400, "Uploaded Shapefile is invalid."),
    "invalid_vector": (400, "Uploaded vector content is invalid."),
    "unsupported_vector": (400, "Uploaded vector uses an unsupported format feature."),
    "invalid_source_crs": (400, "Uploaded vector CRS is invalid."),
    "unknown_source_crs": (400, "Uploaded vector CRS is missing or unknown."),
    "reprojection_failed": (400, "Uploaded vector cannot be transformed safely."),
    "vector_limit_exceeded": (413, "Uploaded vector exceeds a normalization limit."),
    "archive_quota_exceeded": (413, "Uploaded vector archive exceeds a normalization limit."),
    "vector_crs_invalid": (400, "Uploaded vector CRS cannot be transformed safely."),
    "vector_source_integrity_error": (502, "Vector source integrity verification failed."),
    "request_timeout": (408, "Vector conversion timed out."),
    "service_saturated": (503, "Vector converter is temporarily saturated."),
    "unavailable": (503, "Vector converter is unavailable."),
}
_LOGGER = logging.getLogger(__name__)


class VectorUploadError(ValueError):
    """Stable receiver error; route adapters preserve their response envelope."""

    def __init__(self, code: str, message: str, *, status_code: int, attempt_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.attempt_id = attempt_id


@dataclass(frozen=True, slots=True)
class RetentionActor:
    kind: str
    identifier: str | int | None

    def receipt_value(self) -> dict[str, object]:
        if self.kind == "human" and isinstance(self.identifier, int) and self.identifier > 0:
            return {"kind": "human", "user_id": self.identifier}
        if self.kind in {"service", "mcp"} and isinstance(self.identifier, str):
            subject = self.identifier.strip()[:160]
            if subject:
                return {"kind": self.kind, "subject": subject}
        return {"kind": "unattributed"}

    @property
    def ledger_bucket(self) -> str:
        value = self.receipt_value()
        if value["kind"] == "human":
            return f"human:{value['user_id']}"
        if value["kind"] in {"service", "mcp"}:
            return f"{value['kind']}:{value['subject']}"
        return "unattributed"


class Reservation(Protocol):
    reservation_id: str

    def bind_attempt(self, attempt_dir: Path) -> None: ...

    def commit(self, exact_bytes: int) -> None: ...

    def release_prewrite(self) -> None: ...


class RetentionLedger(Protocol):
    def reserve(self, *, project_key: str, actor: RetentionActor, worst_case_bytes: int, filesystem_root: Path) -> Reservation: ...


class ScopeLease(Protocol):
    def assert_owned(self) -> None: ...

    def release(self) -> None: ...


class ScopeLeaseFactory(Protocol):
    def __call__(self, scope_key: str) -> ScopeLease: ...


_RESERVE_LUA = """
if redis.call('EXISTS', KEYS[4]) ~= 0 then return {-5, 0} end
local total_committed = tonumber(redis.call('HGET', KEYS[1], 'committed') or '0')
local total_reserved = tonumber(redis.call('HGET', KEYS[1], 'reserved') or '0')
local inflight = tonumber(redis.call('HGET', KEYS[1], 'inflight') or '0')
local principal_committed = tonumber(redis.call('HGET', KEYS[2], 'committed') or '0')
local principal_reserved = tonumber(redis.call('HGET', KEYS[2], 'reserved') or '0')
local amount = tonumber(ARGV[2])
if inflight + 1 > tonumber(ARGV[4]) then return {-1, total_reserved} end
if total_committed + total_reserved + amount > tonumber(ARGV[5]) then return {-2, total_reserved} end
if principal_committed + principal_reserved + amount > tonumber(ARGV[6]) then return {-3, total_reserved} end
if redis.call('EXISTS', KEYS[3]) ~= 0 then return {-4, total_reserved} end
redis.call('HINCRBY', KEYS[1], 'reserved', amount)
redis.call('HINCRBY', KEYS[1], 'inflight', 1)
redis.call('HINCRBY', KEYS[2], 'reserved', amount)
redis.call('HSET', KEYS[3], 'owner', ARGV[1], 'amount', amount, 'principal', KEYS[2], 'project', ARGV[3], 'created_unix', ARGV[7], 'state', 'reserved')
return {1, total_reserved + amount}
"""

_COMMIT_LUA = """
if redis.call('HGET', KEYS[3], 'owner') ~= ARGV[1] then return 0 end
if redis.call('HGET', KEYS[3], 'state') == 'committed' then return 2 end
local amount = tonumber(redis.call('HGET', KEYS[3], 'amount') or '-1')
if amount < 0 then return 0 end
local exact = tonumber(ARGV[2])
redis.call('HINCRBY', KEYS[1], 'reserved', -amount)
redis.call('HINCRBY', KEYS[1], 'inflight', -1)
redis.call('HINCRBY', KEYS[1], 'committed', exact)
redis.call('HINCRBY', KEYS[2], 'reserved', -amount)
redis.call('HINCRBY', KEYS[2], 'committed', exact)
redis.call('HSET', KEYS[3], 'state', 'committed', 'exact', exact)
return 1
"""

_RELEASE_LUA = """
if redis.call('HGET', KEYS[3], 'owner') ~= ARGV[1] then return 0 end
local amount = tonumber(redis.call('HGET', KEYS[3], 'amount') or '-1')
if amount < 0 then return 0 end
redis.call('HINCRBY', KEYS[1], 'reserved', -amount)
redis.call('HINCRBY', KEYS[1], 'inflight', -1)
redis.call('HINCRBY', KEYS[2], 'reserved', -amount)
redis.call('DEL', KEYS[3])
return 1
"""

_RECONCILE_LUA = """
local state = redis.call('HGET', KEYS[2], 'state')
if not state then state = 'reserved' end
if state == 'committed' then return 2 end
local amount = tonumber(redis.call('HGET', KEYS[2], 'amount') or '-1')
local principal = redis.call('HGET', KEYS[2], 'principal')
local reserved = tonumber(redis.call('HGET', KEYS[1], 'reserved') or '0')
local inflight = tonumber(redis.call('HGET', KEYS[1], 'inflight') or '0')
if amount < 0 or not principal or reserved < amount or inflight < 1 then return -1 end
local principal_reserved = tonumber(redis.call('HGET', principal, 'reserved') or '0')
if principal_reserved < amount then return -1 end
redis.call('HINCRBY', KEYS[1], 'reserved', -amount)
redis.call('HINCRBY', KEYS[1], 'inflight', -1)
redis.call('HINCRBY', principal, 'reserved', -amount)
if ARGV[1] == 'commit' then
  local exact = tonumber(ARGV[2])
  redis.call('HINCRBY', KEYS[1], 'committed', exact)
  redis.call('HINCRBY', principal, 'committed', exact)
  redis.call('HSET', KEYS[2], 'state', 'committed', 'exact', exact)
else
  redis.call('DEL', KEYS[2])
end
return 1
"""


@dataclass(slots=True)
class _RedisReservation:
    connection: Any
    totals_key: str
    principal_key: str
    reservation_key: str
    owner_token: str
    reservation_id: str
    filesystem_root: Path
    _finished: bool = False

    def bind_attempt(self, attempt_dir: Path) -> None:
        if self._finished:
            raise RuntimeError("retention reservation is already finalized")
        try:
            relative = attempt_dir.resolve(strict=True).relative_to(self.filesystem_root).as_posix()
            result = self.connection.eval(
                "if redis.call('HGET',KEYS[1],'owner') == ARGV[1] then "
                "redis.call('HSET',KEYS[1],'attempt_relpath',ARGV[2]); return 1 end return 0",
                1, self.reservation_key, self.owner_token, relative,
            )
        except (OSError, ValueError, redis.RedisError) as exc:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence reservation could not be bound safely.",
                status_code=507,
            ) from exc
        if int(result or 0) not in {1, 2}:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence reservation ownership was lost.",
                status_code=507,
            )

    def commit(self, exact_bytes: int) -> None:
        if self._finished:
            raise RuntimeError("retention reservation is already finalized")
        try:
            result = self.connection.eval(
                _COMMIT_LUA, 3, self.totals_key, self.principal_key,
                self.reservation_key, self.owner_token, int(exact_bytes),
            )
        except redis.RedisError as exc:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence accounting could not be committed safely.",
                status_code=507,
            ) from exc
        if int(result or 0) != 1:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence reservation ownership was lost.",
                status_code=507,
            )
        self._finished = True

    def release_prewrite(self) -> None:
        if self._finished:
            return
        try:
            result = self.connection.eval(
                _RELEASE_LUA, 3, self.totals_key, self.principal_key,
                self.reservation_key, self.owner_token,
            )
        except redis.RedisError as exc:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence reservation could not be released safely.",
                status_code=507,
            ) from exc
        if int(result or 0) != 1:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence reservation could not be released safely.",
                status_code=507,
            )
        self._finished = True


class RedisRetentionLedger:
    """Fail-closed shared retained-evidence ledger backed by Redis Lua."""

    def __init__(self, connection: Any | None = None) -> None:
        self._connection = connection

    def _client(self) -> Any:
        if self._connection is not None:
            return self._connection
        return redis.Redis(**redis_connection_kwargs(RedisDB.LOCK, decode_responses=True))

    def reserve(self, *, project_key: str, actor: RetentionActor, worst_case_bytes: int, filesystem_root: Path) -> Reservation:
        filesystem_id = os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "").strip()
        configured_root = os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", "").strip()
        if not filesystem_id or not configured_root:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence retention is not configured.",
                status_code=507,
            )
        try:
            expected_root = Path(configured_root).resolve(strict=True)
            actual_root = filesystem_root.resolve(strict=True)
            actual_root.relative_to(expected_root)
        except (OSError, ValueError) as exc:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence filesystem identity cannot be verified.",
                status_code=507,
            ) from exc
        principal = actor.ledger_bucket
        principal_limit = _UNATTRIBUTED_LIMIT if principal == "unattributed" else _PRINCIPAL_LIMIT
        reservation_id = uuid.uuid4().hex
        owner = uuid.uuid4().hex
        prefix = f"vector-upload-retention:{filesystem_id}"
        totals_key = f"{prefix}:totals"
        principal_key = f"{prefix}:principal:{hashlib.sha256(principal.encode()).hexdigest()}"
        reservation_key = f"{prefix}:reservation:{reservation_id}"
        reconcile_key = f"{prefix}:reconcile"
        try:
            result = self._client().eval(
                _RESERVE_LUA, 4, totals_key, principal_key, reservation_key, reconcile_key,
                owner, int(worst_case_bytes), project_key,
                _GLOBAL_INFLIGHT_LIMIT, _GLOBAL_LIMIT, principal_limit,
                int(time.time()),
            )
            outcome, outstanding = int(result[0]), int(result[1])
            if outcome != 1:
                raise VectorUploadError(
                    "vector_retention_quota_exceeded",
                    "Vector evidence retention quota is exhausted.",
                    status_code=507,
                )
            if shutil.disk_usage(actual_root).free - outstanding < _FREE_SPACE_RESERVE:
                reservation = _RedisReservation(
                    self._client(), totals_key, principal_key, reservation_key,
                    owner, reservation_id, actual_root,
                )
                reservation.release_prewrite()
                raise VectorUploadError(
                    "vector_retention_quota_exceeded",
                    "Vector evidence filesystem reserve is exhausted.",
                    status_code=507,
                )
        except VectorUploadError:
            raise
        except (OSError, TypeError, ValueError, redis.RedisError) as exc:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector evidence retention is unavailable.",
                status_code=507,
            ) from exc
        return _RedisReservation(
            self._client(), totals_key, principal_key, reservation_key,
            owner, reservation_id, actual_root,
        )


def reconcile_retention(
    filesystem_root: Path,
    *,
    apply: bool = False,
    connection: Any | None = None,
    now: int | None = None,
    stale_seconds: int = _LEASE_SECONDS,
    rebuild_ledger: bool = False,
) -> dict[str, object]:
    """Audit/recover reservations and optionally rebuild accounting from receipts."""
    filesystem_id = os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "").strip()
    configured_root = os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", "").strip()
    if not filesystem_id or not configured_root:
        raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence retention is not configured.", status_code=507)
    try:
        root = filesystem_root.resolve(strict=True)
        root.relative_to(Path(configured_root).resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence filesystem identity cannot be verified.", status_code=507) from exc
    client = connection or redis.Redis(**redis_connection_kwargs(RedisDB.LOCK, decode_responses=True))
    prefix = f"vector-upload-retention:{filesystem_id}"
    totals_key = f"{prefix}:totals"
    lock_key = f"{prefix}:reconcile"
    lock_token = uuid.uuid4().hex
    try:
        if not client.set(lock_key, lock_token, nx=True, ex=300):
            raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence reconciliation is already active.", status_code=507)
        keys = list(client.scan_iter(match=f"{prefix}:reservation:*", count=100))
        if len(keys) > 10_000:
            raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence reservation inventory exceeds the recovery bound.", status_code=507)
        actions: list[dict[str, object]] = []
        current = int(time.time()) if now is None else int(now)
        for key in sorted(keys):
            metadata = client.hgetall(key)
            created = int(metadata.get("created_unix") or 0)
            if current - created < stale_seconds:
                continue
            relative = str(metadata.get("attempt_relpath") or "")
            state = str(metadata.get("state") or "reserved")
            if not relative:
                action = {"reservation": key.rsplit(":", 1)[-1], "action": "release_prewrite"}
                actions.append(action)
                if apply and state != "committed":
                    result = int(client.eval(_RECONCILE_LUA, 2, totals_key, key, "release", 0) or 0)
                    if result != 1:
                        raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence ledger drift requires operator repair.", status_code=507)
                elif apply:
                    client.delete(key)
                continue
            attempt = (root / relative).resolve(strict=False)
            try:
                attempt.relative_to(root)
            except ValueError as exc:
                raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence reservation path escapes its filesystem.", status_code=507) from exc
            if not attempt.exists() or attempt.is_symlink() or not attempt.is_dir():
                actions.append({"reservation": key.rsplit(":", 1)[-1], "action": "blocked_missing_attempt"})
                continue
            receipt_path = attempt / _RECEIPT_NAME
            try:
                receipt = _strict_json(receipt_path.read_bytes())
            except (OSError, UnicodeError, ValueError):
                actions.append({"reservation": key.rsplit(":", 1)[-1], "action": "corrupt_attempt"})
                if not apply:
                    continue
                corrupt_bytes = receipt_path.read_bytes() if receipt_path.exists() else b""
                if corrupt_bytes:
                    corrupt_path = attempt / f"normalization.corrupt.{hashlib.sha256(corrupt_bytes).hexdigest()}.json"
                    os.replace(receipt_path, corrupt_path)
                receipt = {
                    "schema": _RECEIPT_SCHEMA,
                    "attempt_id": attempt.name,
                    "status": "corrupt_attempt",
                    "outcome": "quarantined",
                    "enforcement_stage": "reconciliation",
                    "error_code": "invalid_receipt",
                    "updated_utc": _utc_now(),
                    "reservation_id": key.rsplit(":", 1)[-1],
                }
                _atomic_json(receipt_path, receipt)
            status = str(receipt.get("status") or "")
            recovered_status = status
            if status == "accepted":
                project_rel = receipt.get("project_root")
                canonical_rel = receipt.get("canonical_path")
                recovered_status = "incomplete"
                if isinstance(project_rel, str) and isinstance(canonical_rel, str):
                    canonical = (root / project_rel / canonical_rel).resolve(strict=False)
                    try:
                        canonical.relative_to(root)
                        size, digest = _hash_regular(canonical)
                        if size == receipt.get("canonical_size") and digest == receipt.get("canonical_sha256"):
                            recovered_status = "accepted_recovered"
                    except (OSError, ValueError, VectorUploadError):
                        pass
            elif status not in {"rejected", "accepted_recovered", "corrupt_attempt", "incomplete"}:
                recovered_status = "incomplete"
            actions.append({"reservation": key.rsplit(":", 1)[-1], "action": recovered_status})
            if not apply:
                continue
            receipt.update(
                status=recovered_status,
                outcome="retained" if recovered_status == "accepted_recovered" else "quarantined",
                enforcement_stage="reconciliation",
                accounting_status="committed",
                updated_utc=_utc_now(),
            )
            _atomic_json(receipt_path, receipt)
            exact = _regular_tree_size(attempt)
            result = int(client.eval(_RECONCILE_LUA, 2, totals_key, key, "commit", exact) or 0)
            if result not in {1, 2}:
                raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence ledger drift requires operator repair.", status_code=507)
            client.delete(key)
        ledger_audit: dict[str, object] | None = None
        if rebuild_ledger:
            receipt_count = 0
            committed_bytes = 0
            principal_bytes: dict[str, int] = {}
            for walk_root, directories, filenames in os.walk(root, followlinks=False):
                directories[:] = [
                    name for name in directories
                    if not (Path(walk_root) / name).is_symlink()
                ]
                if _RECEIPT_NAME not in filenames:
                    continue
                if receipt_count >= 10_000:
                    raise VectorUploadError(
                        "vector_retention_quota_exceeded",
                        "Vector evidence receipt inventory exceeds the recovery bound.",
                        status_code=507,
                    )
                receipt_path = Path(walk_root) / _RECEIPT_NAME
                try:
                    receipt = _strict_json(receipt_path.read_bytes())
                except (OSError, UnicodeError, ValueError):
                    actions.append({
                        "path": os.fspath(receipt_path.relative_to(root)),
                        "action": "blocked_corrupt_receipt",
                    })
                    continue
                if receipt.get("schema") != _RECEIPT_SCHEMA:
                    continue
                status = str(receipt.get("status") or "")
                if status not in {"accepted", "accepted_recovered", "rejected", "incomplete", "corrupt_attempt"}:
                    actions.append({
                        "path": os.fspath(receipt_path.relative_to(root)),
                        "action": "blocked_nonterminal_receipt",
                    })
                    continue
                attempt_bytes = _regular_tree_size(receipt_path.parent)
                actor = receipt.get("actor")
                bucket = "unattributed"
                if isinstance(actor, dict):
                    kind = actor.get("kind")
                    if kind == "human" and isinstance(actor.get("user_id"), int) and actor["user_id"] > 0:
                        bucket = f"human:{actor['user_id']}"
                    elif kind in {"service", "mcp"} and isinstance(actor.get("subject"), str) and actor["subject"]:
                        bucket = f"{kind}:{actor['subject'][:160]}"
                receipt_count += 1
                committed_bytes += attempt_bytes
                principal_bytes[bucket] = principal_bytes.get(bucket, 0) + attempt_bytes

            current_totals = client.hgetall(totals_key)
            ledger_audit = {
                "receipt_count": receipt_count,
                "computed_committed": committed_bytes,
                "recorded_committed": int(current_totals.get("committed") or 0),
                "principal_count": len(principal_bytes),
            }
            blocked = [item for item in actions if str(item.get("action", "")).startswith("blocked_")]
            if apply:
                remaining_reservations = list(client.scan_iter(match=f"{prefix}:reservation:*", count=100))
                if blocked or remaining_reservations:
                    raise VectorUploadError(
                        "vector_retention_quota_exceeded",
                        "Vector evidence ledger rebuild is blocked by active or unverifiable evidence.",
                        status_code=507,
                    )
                principal_keys = list(client.scan_iter(match=f"{prefix}:principal:*", count=100))
                pipeline = client.pipeline(transaction=True)
                pipeline.delete(totals_key)
                if principal_keys:
                    pipeline.delete(*principal_keys)
                pipeline.hset(totals_key, mapping={
                    "committed": committed_bytes,
                    "reserved": 0,
                    "inflight": 0,
                })
                for bucket, amount in principal_bytes.items():
                    principal_key = f"{prefix}:principal:{hashlib.sha256(bucket.encode()).hexdigest()}"
                    pipeline.hset(principal_key, mapping={"committed": amount, "reserved": 0})
                pipeline.execute()
                ledger_audit["rebuilt"] = True
        return {
            "filesystem_id": filesystem_id,
            "apply": apply,
            "actions": actions,
            "ledger_audit": ledger_audit,
        }
    except VectorUploadError:
        raise
    except (OSError, TypeError, ValueError, redis.RedisError) as exc:
        raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence reconciliation failed closed.", status_code=507) from exc
    finally:
        try:
            client.eval(_LOCK_RELEASE_LUA, 1, lock_key, lock_token)
        except redis.RedisError:
            _LOGGER.warning("Vector retention reconciliation lock release deferred to TTL", exc_info=True)


_LOCK_RELEASE_LUA = "if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0"


@dataclass(slots=True)
class _RedisScopeLease:
    connection: Any
    key: str
    token: str
    _released: bool = False

    def assert_owned(self) -> None:
        try:
            owned = not self._released and self.connection.get(self.key) == self.token
        except redis.RedisError as exc:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector upload retention lock is unavailable.",
                status_code=507,
            ) from exc
        if not owned:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector upload retention lock ownership was lost.",
                status_code=507,
            )

    def release(self) -> None:
        if self._released:
            return
        try:
            self.connection.eval(_LOCK_RELEASE_LUA, 1, self.key, self.token)
        except redis.RedisError as exc:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector upload retention lock could not be released safely.",
                status_code=507,
            ) from exc
        self._released = True


class RedisScopeLeaseFactory:
    def __init__(self, connection: Any | None = None) -> None:
        self._connection = connection

    def __call__(self, scope_key: str) -> ScopeLease:
        if self._connection is None:
            connection = redis.Redis(**redis_connection_kwargs(RedisDB.LOCK, decode_responses=True))
        else:
            connection = self._connection
        key = f"vector-upload-retention:scope:{hashlib.sha256(scope_key.encode()).hexdigest()}"
        token = uuid.uuid4().hex
        deadline = time.monotonic() + 10.0
        try:
            while not connection.set(key, token, nx=True, ex=_LEASE_SECONDS):
                if time.monotonic() >= deadline:
                    raise VectorUploadError(
                        "vector_retention_quota_exceeded",
                        "Another vector evidence operation is active for this project.",
                        status_code=507,
                    )
                time.sleep(0.05)
        except VectorUploadError:
            raise
        except (OSError, TypeError, ValueError, redis.RedisError) as exc:
            raise VectorUploadError(
                "vector_retention_quota_exceeded",
                "Vector upload retention lock is unavailable.",
                status_code=507,
            ) from exc
        return _RedisScopeLease(connection, key, token)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_submitted_name(raw_name: str) -> str:
    safe = secure_filename(unicodedata.normalize("NFKC", raw_name or ""))
    if not safe:
        raise VectorUploadError("invalid_vector", "Uploaded vector filename is invalid.", status_code=400)
    path = Path(safe)
    suffix = path.suffix
    stem_budget = 120 - len(suffix.encode("ascii", "ignore"))
    stem = path.stem.encode("ascii", "ignore")[: max(1, stem_budget)].decode("ascii", "ignore").rstrip("._")
    result = f"{stem}{suffix}" if stem else ""
    if not result or len(result.encode("ascii")) > 120:
        raise VectorUploadError("invalid_vector", "Uploaded vector filename is invalid.", status_code=400)
    return result


def _format_for_name(name: str) -> str:
    suffix = Path(name).suffix.lower()
    detected = {**_GEOJSON_SUFFIXES, **_BINARY_SUFFIXES}.get(suffix)
    if detected is None:
        raise VectorUploadError(
            "unsupported_vector",
            "Upload a GeoJSON, Shapefile ZIP, or GeoParquet file.",
            status_code=400,
        )
    return detected


def _atomic_json(path: Path, payload: Mapping[str, object]) -> None:
    encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temp.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _hash_regular(path: Path) -> tuple[int, str]:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    digest = hashlib.sha256()
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise VectorUploadError("vector_source_integrity_error", "Vector evidence is not a regular file.", status_code=502)
        for chunk in iter(lambda: stream.read(_CHUNK_BYTES), b""):
            digest.update(chunk)
    return info.st_size, digest.hexdigest()


def _tree_stats(evidence_roots: Iterable[Path]) -> tuple[int, int, int]:
    attempts = originals = total = 0
    for root in evidence_roots:
        if not root.exists():
            continue
        if root.is_symlink() or not root.is_dir():
            raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence tree requires operator repair.", status_code=507)
        for attempt in root.iterdir():
            if attempt.is_symlink() or not attempt.is_dir():
                raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence tree requires operator repair.", status_code=507)
            attempts += 1
        for item in root.rglob("*"):
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence tree requires operator repair.", status_code=507)
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
                if item.parent.name == "original" and item.name.endswith(".upload"):
                    originals += info.st_size
    return attempts, originals, total


def _ensure_attempt_root(attempt_root: Path, filesystem_root: Path) -> None:
    try:
        trusted_root = filesystem_root.resolve(strict=True)
        resolved_parent = attempt_root.parent.resolve(strict=True)
        resolved_parent.relative_to(trusted_root)
    except (OSError, ValueError) as exc:
        raise VectorUploadError(
            "vector_retention_quota_exceeded",
            "Vector evidence root cannot be verified.",
            status_code=507,
        ) from exc
    if attempt_root.is_symlink():
        raise VectorUploadError(
            "vector_retention_quota_exceeded",
            "Vector evidence root requires operator repair.",
            status_code=507,
        )
    attempt_root.mkdir(parents=False, exist_ok=True, mode=0o700)
    if not attempt_root.is_dir() or attempt_root.resolve(strict=True).parent != resolved_parent:
        raise VectorUploadError(
            "vector_retention_quota_exceeded",
            "Vector evidence root cannot be verified.",
            status_code=507,
        )
    os.chmod(attempt_root, 0o700)


def _regular_tree_size(root: Path) -> int:
    total = 0
    for item in root.rglob("*"):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence tree requires operator repair.", status_code=507)
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
    return total


def _strict_json(data: bytes) -> dict[str, object]:
    depth = 0
    in_string = False
    escaped = False
    for byte in data:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
            continue
        if byte == 0x22:
            in_string = True
        elif byte in {0x5B, 0x7B}:
            depth += 1
            if depth > 64:
                raise ValueError("JSON nesting limit exceeded")
        elif byte in {0x5D, 0x7D}:
            depth -= 1
            if depth < 0:
                raise ValueError("malformed JSON nesting")

    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate object key")
            result[key] = value
        return result

    def finite_float(raw: str) -> float:
        parsed = float(raw)
        if not math.isfinite(parsed):
            raise ValueError("nonfinite number")
        return parsed

    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("nonfinite number")),
            parse_float=finite_float,
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting limit exceeded") from exc
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def validate_feature_collection_geometries(payload: Mapping[str, object], allowed_types: Sequence[str]) -> dict[str, object]:
    """Validate nonempty workflow geometry without repairing or exploding it."""
    allowed = frozenset(allowed_types)
    features = payload.get("features")
    if payload.get("type") != "FeatureCollection" or not isinstance(features, list) or not features:
        raise VectorUploadError("invalid_vector", "Uploaded vector must be a nonempty FeatureCollection.", status_code=400)

    def coordinates(value: object) -> int:
        count = 0
        stack: list[tuple[object, int]] = [(value, 0)]
        while stack:
            current, depth = stack.pop()
            if depth > 16:
                raise VectorUploadError(
                    "invalid_vector",
                    "Uploaded vector geometry nesting exceeds the receiving limit.",
                    status_code=400,
                )
            if not isinstance(current, list) or not current:
                raise VectorUploadError("invalid_vector", "Uploaded vector contains empty geometry coordinates.", status_code=400)
            if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in current):
                if len(current) < 2 or not all(math.isfinite(float(item)) for item in current):
                    raise VectorUploadError("invalid_vector", "Uploaded vector contains invalid coordinates.", status_code=400)
                count += 1
                continue
            if any(not isinstance(item, list) for item in current):
                raise VectorUploadError("invalid_vector", "Uploaded vector contains malformed coordinates.", status_code=400)
            stack.extend((item, depth + 1) for item in current)
        return count

    geometry_types: set[str] = set()
    vertex_count = 0
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise VectorUploadError("invalid_vector", "Uploaded vector contains an invalid feature.", status_code=400)
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            raise VectorUploadError("invalid_vector", "Uploaded vector contains a null or invalid geometry.", status_code=400)
        geometry_type = geometry.get("type")
        if not isinstance(geometry_type, str) or geometry_type not in allowed:
            raise VectorUploadError(
                "invalid_vector",
                f"Uploaded vector geometry must be one of: {', '.join(sorted(allowed))}.",
                status_code=400,
            )
        geometry_types.add(geometry_type)
        vertex_count += coordinates(geometry.get("coordinates"))
    return {"feature_count": len(features), "geometry_types": sorted(geometry_types), "vertex_count": vertex_count}


def _write_candidate(path: Path, content: bytes, limit: int) -> tuple[int, str]:
    if len(content) > limit:
        raise VectorUploadError("vector_limit_exceeded", "Normalized GeoJSON exceeds the receiving limit.", status_code=413)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return len(content), hashlib.sha256(content).hexdigest()


def _sanitize_parser_provenance(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    result: dict[str, str] = {}
    limits = {
        "binary_name": 80,
        "binary_version": 80,
        "binary_sha256": 64,
        "cargo_lock_sha256": 64,
        "source_revision": 64,
    }
    for key, limit in limits.items():
        item = value.get(key)
        if not isinstance(item, str) or not item or len(item) > limit:
            return None
        result[key] = item
    return result


def _log_quarantine(receipt: Mapping[str, object]) -> None:
    _LOGGER.warning(
        "vector_upload_security_event_v1 %s",
        json.dumps(
            {
                "attempt_id": receipt.get("attempt_id"),
                "project_identity": receipt.get("project_identity"),
                "workflow": receipt.get("workflow"),
                "actor": receipt.get("actor"),
                "source_sha256": receipt.get("source_sha256"),
                "source_size": receipt.get("source_size"),
                "error_code": receipt.get("error_code"),
                "enforcement_stage": receipt.get("enforcement_stage"),
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def _converter_payload(*, source_path: Path, submitted_name: str, source_size: int, source_sha256: str, converter_url: str, timeout_seconds: float) -> tuple[bytes, dict[str, object]]:
    descriptor = os.open(source_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise VectorUploadError("vector_source_integrity_error", "Retained source is not a regular file.", status_code=502)
            response = requests.post(
                converter_url,
                files={"archive": (submitted_name, stream, "application/octet-stream")},
                data={"output_format": "geojson", "target_crs": "wgs84", "response_mode": "json_body"},
                timeout=(5.0, timeout_seconds),
                allow_redirects=False,
                stream=True,
            )
            stream.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(_CHUNK_BYTES), b""):
                digest.update(chunk)
            after = os.fstat(stream.fileno())
    except requests.Timeout as exc:
        raise VectorUploadError("vector_conversion_timeout", "Vector conversion timed out.", status_code=408) from exc
    except requests.ConnectionError as exc:
        raise VectorUploadError("vector_converter_unavailable", "Vector converter is unavailable.", status_code=503) from exc
    except requests.RequestException as exc:
        raise VectorUploadError("vector_converter_unavailable", "Vector converter request failed.", status_code=503) from exc
    if (
        before.st_dev != after.st_dev or before.st_ino != after.st_ino or
        before.st_mtime_ns != after.st_mtime_ns or source_size != after.st_size or
        source_sha256 != digest.hexdigest()
    ):
        raise VectorUploadError("vector_source_integrity_error", "Retained source changed during conversion.", status_code=502)
    try:
        declared_length = int(response.headers.get("Content-Length", "0"))
        if declared_length > _CONVERTER_RESPONSE_LIMIT:
            raise VectorUploadError("vector_limit_exceeded", "Vector converter response exceeds the receiving limit.", status_code=413)
        response_bytes = bytearray()
        for chunk in response.iter_content(chunk_size=_CHUNK_BYTES):
            response_bytes.extend(chunk)
            if len(response_bytes) > _CONVERTER_RESPONSE_LIMIT:
                raise VectorUploadError("vector_limit_exceeded", "Vector converter response exceeds the receiving limit.", status_code=413)
        body = json.loads(bytes(response_bytes))
    except VectorUploadError:
        raise
    except (TypeError, ValueError, UnicodeError) as exc:
        raise VectorUploadError("vector_converter_unavailable", "Vector converter returned an invalid response.", status_code=503) from exc
    finally:
        response.close()
    if response.status_code != 200:
        error = body.get("error") if isinstance(body, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        status, message = _CONVERTER_CODES.get(str(code), (503, "Vector converter rejected the upload."))
        if response.status_code == 408:
            status, code, message = 408, "vector_conversion_timeout", "Vector conversion timed out."
        raise VectorUploadError(str(code or "vector_converter_unavailable"), message, status_code=status)
    if not isinstance(body, dict) or set(body) != {"request_id", "geojson", "metadata"}:
        raise VectorUploadError("vector_converter_unavailable", "Vector converter returned an invalid response.", status_code=503)
    metadata = body["metadata"]
    if not isinstance(metadata, dict):
        raise VectorUploadError("vector_converter_unavailable", "Vector converter metadata is invalid.", status_code=503)
    if metadata.get("source_size") != source_size or metadata.get("source_sha256") != source_sha256:
        raise VectorUploadError("vector_source_integrity_error", "Vector converter source digest did not match the retained upload.", status_code=502)
    try:
        content = json.dumps(body["geojson"], ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VectorUploadError("vector_converter_unavailable", "Vector converter GeoJSON is invalid.", status_code=503) from exc
    if metadata.get("canonical_size") != len(content) or metadata.get("canonical_sha256") != hashlib.sha256(content).hexdigest():
        raise VectorUploadError("vector_source_integrity_error", "Vector converter canonical digest did not match its artifact.", status_code=502)
    provenance = _sanitize_parser_provenance(metadata.get("parser_provenance"))
    if provenance is None:
        raise VectorUploadError(
            "vector_converter_unavailable",
            "Vector converter did not provide bounded parser provenance.",
            status_code=503,
        )
    metadata = dict(metadata)
    metadata["request_id"] = str(body["request_id"])[:128]
    metadata["parser_provenance"] = provenance
    return content, metadata


@dataclass(slots=True)
class PreparedVectorUpload:
    attempt_id: str
    attempt_dir: Path
    candidate_path: Path
    candidate_sha256: str
    candidate_size: int
    receipt: dict[str, object]
    reservation: Reservation
    lease: ScopeLease
    evidence_roots: tuple[Path, ...]
    _finished: bool = False

    @property
    def is_terminal(self) -> bool:
        return self._finished

    def _persist(self) -> None:
        self.lease.assert_owned()
        self.receipt["updated_utc"] = _utc_now()
        _atomic_json(self.attempt_dir / _RECEIPT_NAME, self.receipt)

    def reject(self, code: str, *, stage: str = "workflow_publication") -> None:
        if self._finished:
            return
        self.receipt.update(
            status="rejected", outcome="quarantined", enforcement_stage=stage,
            error_code=code, accounting_status="pending",
        )
        self._persist()
        _log_quarantine(self.receipt)
        self.receipt["accounting_status"] = "committed"
        self._persist()
        exact = _regular_tree_size(self.attempt_dir)
        try:
            self.reservation.commit(exact)
        except VectorUploadError:
            self.receipt["accounting_status"] = "pending"
            self._persist()
            self._finished = True
            try:
                self.lease.release()
            except VectorUploadError:
                _LOGGER.warning("Vector upload scope lease release deferred to TTL", exc_info=True)
            raise
        try:
            self.lease.release()
        except VectorUploadError:
            _LOGGER.warning("Vector upload scope lease release deferred to TTL", exc_info=True)
        self._finished = True

    def _incomplete_after_mutation(self, code: str) -> None:
        self.receipt.update(
            status="incomplete", outcome="quarantined", enforcement_stage="workflow_publication_uncertain",
            error_code=code, accounting_status="pending",
        )
        self._persist()
        self.receipt["accounting_status"] = "committed"
        self._persist()
        exact = _regular_tree_size(self.attempt_dir)
        try:
            self.reservation.commit(exact)
        except VectorUploadError:
            self.receipt["accounting_status"] = "pending"
            self._persist()
            self._finished = True
            try:
                self.lease.release()
            except VectorUploadError:
                _LOGGER.warning("Vector upload scope lease release deferred to TTL", exc_info=True)
            raise
        try:
            self.lease.release()
        except VectorUploadError:
            _LOGGER.warning("Vector upload scope lease release deferred to TTL", exc_info=True)
        self._finished = True

    def publish(
        self,
        *,
        mutation: Callable[[Path], Any],
        canonical_path: Path,
        canonical_relative_path: str | None = None,
    ) -> Any:
        """Run the existing validated workflow mutation, then prove readback."""
        if self._finished:
            raise RuntimeError("vector upload attempt is already terminal")
        self.lease.assert_owned()
        try:
            result = mutation(self.candidate_path)
        except Exception:
            # A workflow callback is required to roll back its own authoritative
            # state. If the candidate nevertheless became canonical, preserve an
            # explicit recovery state instead of falsely recording rejection.
            try:
                canonical_size, canonical_sha256 = _hash_regular(canonical_path)
            except (OSError, ValueError):
                canonical_size, canonical_sha256 = -1, ""
            if canonical_size == self.candidate_size and canonical_sha256 == self.candidate_sha256:
                self._incomplete_after_mutation("workflow_publication_uncertain")
            else:
                self.reject("workflow_publication_failed")
            raise
        try:
            canonical_size, canonical_sha256 = _hash_regular(canonical_path)
            if canonical_size != self.candidate_size or canonical_sha256 != self.candidate_sha256:
                raise VectorUploadError(
                    "vector_source_integrity_error",
                    "Published workflow GeoJSON does not match the validated candidate.",
                    status_code=502,
                    attempt_id=self.attempt_id,
                )
            self.receipt.update(
                status="accepted", outcome="retained", enforcement_stage="accepted_publication",
                canonical_path=canonical_relative_path or canonical_path.name,
                canonical_size=canonical_size,
                canonical_sha256=canonical_sha256,
                accounting_status="pending",
            )
            try:
                self.candidate_path.unlink(missing_ok=True)
            except OSError:
                _LOGGER.warning("Accepted vector candidate cleanup deferred", exc_info=True)
            self.receipt["accounting_status"] = "committed"
            self._persist()
            exact = _regular_tree_size(self.attempt_dir)
            try:
                self.reservation.commit(exact)
            except VectorUploadError:
                # The accepted workflow and receipt are monotonic. A durable
                # reservation record lets the reconciliation command finish
                # accounting without rewriting this attempt as rejected.
                self.receipt["accounting_status"] = "pending"
                try:
                    self._persist()
                finally:
                    self._finished = True
                try:
                    self.lease.release()
                except VectorUploadError:
                    _LOGGER.warning("Vector upload scope lease release deferred to TTL", exc_info=True)
                raise
            self._finished = True
            try:
                self.lease.release()
            except VectorUploadError:
                _LOGGER.warning("Vector upload scope lease release deferred to TTL", exc_info=True)
            return result
        except Exception:
            if not self._finished:
                self._incomplete_after_mutation("workflow_readback_failed")
            raise

    def __enter__(self) -> "PreparedVectorUpload":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if not self._finished:
            self.reject("workflow_publication_incomplete")


def prepare_vector_upload(
    *,
    raw_filename: str,
    stream: BinaryIO,
    endpoint_max_bytes: int,
    attempt_root: Path,
    evidence_roots: Sequence[Path],
    filesystem_root: Path,
    project_key: str,
    workflow: str,
    project_identity: str,
    actor: RetentionActor,
    validator: Callable[[Path, Mapping[str, object]], object],
    converter_url: str | None = None,
    converter_timeout_seconds: float = 100.0,
    ledger: RetentionLedger | None = None,
    scope_lease_factory: ScopeLeaseFactory | None = None,
) -> PreparedVectorUpload:
    """Retain, normalize, validate, and durably prepare one vector upload."""
    safe_name = _safe_submitted_name(raw_filename)
    detected_format = _format_for_name(safe_name)
    candidate_allowance = endpoint_max_bytes if detected_format == "geojson" else min(endpoint_max_bytes, _CANDIDATE_LIMIT)
    worst_case = endpoint_max_bytes + candidate_allowance + _RECEIPT_ALLOWANCE
    ledger = ledger or RedisRetentionLedger()
    reservation = ledger.reserve(
        project_key=project_key, actor=actor, worst_case_bytes=worst_case,
        filesystem_root=filesystem_root,
    )
    lease: ScopeLease | None = None
    attempt_dir: Path | None = None
    source_complete = False
    receipt: dict[str, object] | None = None
    try:
        lease = (scope_lease_factory or RedisScopeLeaseFactory())(project_key)
        attempts, originals, live_bytes = _tree_stats(evidence_roots)
        if attempts >= _ATTEMPT_LIMIT or originals + endpoint_max_bytes > _ORIGINAL_BYTES_LIMIT:
            raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence project quota is exhausted.", status_code=507)
        if live_bytes + worst_case > _LIVE_TREE_LIMIT or live_bytes + worst_case > _TOTAL_EVIDENCE_LIMIT:
            raise VectorUploadError("vector_retention_quota_exceeded", "Vector evidence project quota is exhausted.", status_code=507)
        _ensure_attempt_root(attempt_root, filesystem_root)
        attempt_id = str(uuid.uuid4())
        attempt_dir = attempt_root / attempt_id
        attempt_dir.mkdir(mode=0o700)
        os.chmod(attempt_dir, 0o700)
        bind_attempt = getattr(reservation, "bind_attempt", None)
        if callable(bind_attempt):
            bind_attempt(attempt_dir)
        original_dir = attempt_dir / "original"
        original_dir.mkdir(mode=0o700)
        os.chmod(original_dir, 0o700)
        receipt = {
            "schema": _RECEIPT_SCHEMA, "attempt_id": attempt_id,
            "created_utc": _utc_now(), "updated_utc": _utc_now(),
            "status": "receiving", "outcome": "working",
            "enforcement_stage": "receiving", "workflow": workflow[:64],
            "project_identity": project_identity[:160], "actor": actor.receipt_value(),
            "project_root": filesystem_root.resolve(strict=True).relative_to(
                Path(os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(filesystem_root))).resolve(strict=True)
            ).as_posix(),
            "reservation_id": reservation.reservation_id,
            "submitted_name": safe_name, "detected_format": detected_format,
            "source_complete": False,
        }
        _atomic_json(attempt_dir / _RECEIPT_NAME, receipt)
        partial = original_dir / f".{safe_name}.partial"
        terminal = original_dir / f"{safe_name}.upload"
        descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        digest = hashlib.sha256()
        size = 0
        try:
            seek = getattr(stream, "seek", None)
            if callable(seek):
                seek(0)
            with os.fdopen(descriptor, "wb") as output:
                while True:
                    chunk = stream.read(_CHUNK_BYTES)
                    if not chunk:
                        break
                    if isinstance(chunk, str):
                        chunk = chunk.encode()
                    size += len(chunk)
                    if size > endpoint_max_bytes:
                        raise VectorUploadError("vector_limit_exceeded", "Uploaded vector exceeds the endpoint size limit.", status_code=413, attempt_id=attempt_id)
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        except VectorUploadError:
            partial.unlink(missing_ok=True)
            receipt.update(
                status="rejected", outcome="oversize_not_retained", enforcement_stage="source_limit",
                source_complete=False, measured_lower_bound_size=size,
                error_code="vector_limit_exceeded",
            )
            _atomic_json(attempt_dir / _RECEIPT_NAME, receipt)
            exact = _regular_tree_size(attempt_dir)
            reservation.commit(exact)
            lease.release()
            raise
        os.replace(partial, terminal)
        _fsync_directory(original_dir)
        source_complete = True
        source_size, source_sha256 = _hash_regular(terminal)
        if source_size != size or source_sha256 != digest.hexdigest():
            raise VectorUploadError("vector_source_integrity_error", "Retained upload digest verification failed.", status_code=502, attempt_id=attempt_id)
        receipt.update(
            status="source_stored", outcome="working", enforcement_stage="source_stored",
            source_complete=True, source_path=os.fspath(terminal.relative_to(attempt_dir)),
            source_size=source_size, source_sha256=source_sha256,
        )
        _atomic_json(attempt_dir / _RECEIPT_NAME, receipt)
        if size == 0:
            raise VectorUploadError("invalid_vector", "Uploaded vector is empty.", status_code=400, attempt_id=attempt_id)

        converter_metadata: dict[str, object] = {}
        if detected_format == "geojson":
            content = terminal.read_bytes()
            candidate_limit = endpoint_max_bytes
        else:
            if os.getenv("VECTOR_UPLOAD_BINARY_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
                raise VectorUploadError(
                    "vector_converter_unavailable",
                    "Binary vector uploads are not enabled on this service.",
                    status_code=503,
                    attempt_id=attempt_id,
                )
            url = (converter_url or os.getenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", "")).strip()
            if not url:
                raise VectorUploadError("vector_converter_unavailable", "Vector converter is unavailable.", status_code=503, attempt_id=attempt_id)
            content, converter_metadata = _converter_payload(
                source_path=terminal, submitted_name=safe_name, source_size=source_size,
                source_sha256=source_sha256, converter_url=url,
                timeout_seconds=converter_timeout_seconds,
            )
            # The internal receiving handoff is deliberately explicit so Roads
            # cannot reinterpret longitude/latitude through its project-CRS
            # inference. Direct GeoJSON remains byte-for-byte unchanged.
            try:
                converted_payload = _strict_json(content)
            except (UnicodeError, ValueError) as exc:
                raise VectorUploadError(
                    "vector_converter_unavailable",
                    "Vector converter returned invalid normalized GeoJSON.",
                    status_code=503,
                    attempt_id=attempt_id,
                ) from exc
            converted_payload["crs"] = {
                "type": "name",
                "properties": {"name": "EPSG:4326"},
            }
            content = json.dumps(
                converted_payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
            candidate_limit = min(endpoint_max_bytes, _CANDIDATE_LIMIT)
        candidate_path = attempt_dir / "candidate.geojson"
        candidate_size, candidate_sha256 = _write_candidate(candidate_path, content, candidate_limit)
        receipt.update(
            status="candidate_stored", outcome="working", enforcement_stage="normalized_candidate",
            candidate_path="candidate.geojson", candidate_size=candidate_size,
            candidate_sha256=candidate_sha256,
        )
        if converter_metadata:
            receipt["converter_request_id"] = converter_metadata.get("request_id")
            receipt["converter_canonical_size"] = converter_metadata.get("canonical_size")
            receipt["converter_canonical_sha256"] = converter_metadata.get("canonical_sha256")
            provenance = _sanitize_parser_provenance(converter_metadata.get("parser_provenance"))
            if provenance is not None:
                receipt["parser_provenance"] = provenance
        _atomic_json(attempt_dir / _RECEIPT_NAME, receipt)
        try:
            payload = _strict_json(content)
            validation = validator(candidate_path, payload)
        except VectorUploadError:
            raise
        except (OSError, TypeError, ValueError) as exc:
            raise VectorUploadError("invalid_vector", "Uploaded vector failed workflow validation.", status_code=400, attempt_id=attempt_id) from exc
        receipt.update(
            status="prepared", outcome="working", enforcement_stage="workflow_validated",
            candidate_path="candidate.geojson", candidate_size=candidate_size,
            candidate_sha256=candidate_sha256,
        )
        if isinstance(validation, Mapping):
            receipt["validation"] = {str(key)[:64]: value for key, value in validation.items() if isinstance(value, (str, int, float, bool, type(None), list))}
        _atomic_json(attempt_dir / _RECEIPT_NAME, receipt)
        return PreparedVectorUpload(
            attempt_id, attempt_dir, candidate_path, candidate_sha256,
            candidate_size, receipt, reservation, lease, tuple(evidence_roots),
        )
    except VectorUploadError as exc:
        if exc.attempt_id is None and attempt_dir is not None:
            exc.attempt_id = attempt_dir.name
        if receipt is not None and source_complete and receipt.get("status") not in {"rejected", "accepted"}:
            receipt.update(
                status="rejected", outcome="quarantined", enforcement_stage="normalization",
                error_code=exc.code, updated_utc=_utc_now(),
            )
            try:
                _atomic_json(attempt_dir / _RECEIPT_NAME, receipt)
                _log_quarantine(receipt)
                exact = _regular_tree_size(attempt_dir)
                reservation.commit(exact)
            finally:
                if lease is not None:
                    lease.release()
        elif attempt_dir is None:
            reservation.release_prewrite()
            if lease is not None:
                lease.release()
        elif receipt is not None and receipt.get("status") == "rejected":
            pass
        else:
            # Ambiguous published evidence remains conservatively reserved.
            if lease is not None:
                lease.release()
        raise
    except (OSError, TypeError, ValueError) as exc:
        if attempt_dir is None:
            reservation.release_prewrite()
        if lease is not None:
            lease.release()
        raise VectorUploadError(
            "vector_retention_quota_exceeded",
            "Vector evidence could not be persisted safely.",
            status_code=507,
            attempt_id=attempt_dir.name if attempt_dir else None,
        ) from exc


__all__ = [
    "PreparedVectorUpload",
    "RedisRetentionLedger",
    "RedisScopeLeaseFactory",
    "RetentionActor",
    "VectorUploadError",
    "prepare_vector_upload",
    "reconcile_retention",
    "validate_feature_collection_geometries",
]
