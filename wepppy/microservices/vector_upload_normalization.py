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
    "invalid_vector": (400, "Uploaded vector content is invalid."),
    "unsupported_vector": (400, "Uploaded vector uses an unsupported format feature."),
    "vector_limit_exceeded": (413, "Uploaded vector exceeds a normalization limit."),
    "vector_crs_invalid": (400, "Uploaded vector CRS cannot be transformed safely."),
    "vector_source_integrity_error": (502, "Vector source integrity verification failed."),
    "request_timeout": (408, "Vector conversion timed out."),
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
redis.call('HSET', KEYS[3], 'owner', ARGV[1], 'amount', amount, 'principal', KEYS[2], 'project', ARGV[3])
redis.call('EXPIRE', KEYS[3], tonumber(ARGV[7]))
return {1, total_reserved + amount}
"""

_COMMIT_LUA = """
if redis.call('HGET', KEYS[3], 'owner') ~= ARGV[1] then return 0 end
local amount = tonumber(redis.call('HGET', KEYS[3], 'amount') or '-1')
if amount < 0 then return 0 end
local exact = tonumber(ARGV[2])
redis.call('HINCRBY', KEYS[1], 'reserved', -amount)
redis.call('HINCRBY', KEYS[1], 'inflight', -1)
redis.call('HINCRBY', KEYS[1], 'committed', exact)
redis.call('HINCRBY', KEYS[2], 'reserved', -amount)
redis.call('HINCRBY', KEYS[2], 'committed', exact)
redis.call('DEL', KEYS[3])
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


@dataclass(slots=True)
class _RedisReservation:
    connection: Any
    totals_key: str
    principal_key: str
    reservation_key: str
    owner_token: str
    reservation_id: str
    _finished: bool = False

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
        try:
            result = self._client().eval(
                _RESERVE_LUA, 3, totals_key, principal_key, reservation_key,
                owner, int(worst_case_bytes), project_key,
                _GLOBAL_INFLIGHT_LIMIT, _GLOBAL_LIMIT, principal_limit,
                _LEASE_SECONDS,
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
                    owner, reservation_id,
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
            owner, reservation_id,
        )


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

    value = json.loads(
        data.decode("utf-8"), object_pairs_hook=pairs,
        parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("nonfinite number")),
        parse_float=finite_float,
    )
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
        if not isinstance(value, list) or not value:
            raise VectorUploadError("invalid_vector", "Uploaded vector contains empty geometry coordinates.", status_code=400)
        if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
            if len(value) < 2 or not all(math.isfinite(float(item)) for item in value):
                raise VectorUploadError("invalid_vector", "Uploaded vector contains invalid coordinates.", status_code=400)
            return 1
        if any(not isinstance(item, list) for item in value):
            raise VectorUploadError("invalid_vector", "Uploaded vector contains malformed coordinates.", status_code=400)
        return sum(coordinates(item) for item in value)

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
        body = response.json()
    except (ValueError, UnicodeError) as exc:
        raise VectorUploadError("vector_converter_unavailable", "Vector converter returned an invalid response.", status_code=503) from exc
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

    def _persist(self) -> None:
        self.lease.assert_owned()
        self.receipt["updated_utc"] = _utc_now()
        _atomic_json(self.attempt_dir / _RECEIPT_NAME, self.receipt)

    def reject(self, code: str, *, stage: str = "workflow_publication") -> None:
        if self._finished:
            return
        self.receipt.update(status="rejected", outcome="quarantined", enforcement_stage=stage, error_code=code)
        self._persist()
        _log_quarantine(self.receipt)
        exact = _regular_tree_size(self.attempt_dir)
        self.reservation.commit(exact)
        self.lease.release()
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
        published = False
        try:
            result = mutation(self.candidate_path)
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
            )
            self.candidate_path.unlink(missing_ok=True)
            self._persist()
            exact = _regular_tree_size(self.attempt_dir)
            self.reservation.commit(exact)
            self.lease.release()
            self._finished = True
            published = True
            return result
        finally:
            # This is a cleanup boundary, not exception translation: preserve the
            # workflow exception while making every failed publication terminal.
            if not published and not self._finished:
                self.reject("workflow_publication_failed")

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
    worst_case = endpoint_max_bytes + _CANDIDATE_LIMIT + _RECEIPT_ALLOWANCE
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
        original_dir = attempt_dir / "original"
        original_dir.mkdir(mode=0o700)
        os.chmod(original_dir, 0o700)
        receipt = {
            "schema": _RECEIPT_SCHEMA, "attempt_id": attempt_id,
            "created_utc": _utc_now(), "updated_utc": _utc_now(),
            "status": "receiving", "outcome": "working",
            "enforcement_stage": "receiving", "workflow": workflow[:64],
            "project_identity": project_identity[:160], "actor": actor.receipt_value(),
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
            converted_payload = _strict_json(content)
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
        if converter_metadata:
            receipt["converter_request_id"] = converter_metadata.get("request_id")
            receipt["converter_canonical_size"] = converter_metadata.get("canonical_size")
            receipt["converter_canonical_sha256"] = converter_metadata.get("canonical_sha256")
            provenance = _sanitize_parser_provenance(converter_metadata.get("parser_provenance"))
            if provenance is not None:
                receipt["parser_provenance"] = provenance
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
    "validate_feature_collection_geometries",
]
