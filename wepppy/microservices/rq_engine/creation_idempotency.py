"""Bounded Redis idempotency records for synchronous project creation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import secrets
from typing import Mapping, Protocol

__all__ = [
    "CREATION_IDEMPOTENCY_TTL_SECONDS",
    "CreationIdempotencyError",
    "CreationReservation",
    "build_creation_fingerprint",
    "complete_creation",
    "release_creation",
    "reserve_creation",
]

CREATION_IDEMPOTENCY_TTL_SECONDS = 86_400
_KEY_RE = re.compile(r"^[A-Za-z0-9._~-]{20,200}$")


class RedisIdempotencyClient(Protocol):
    def set(self, key: str, value: str, *, nx: bool = ..., xx: bool = ..., ex: int = ...) -> object: ...
    def get(self, key: str) -> object: ...
    def delete(self, key: str) -> object: ...


class CreationIdempotencyError(ValueError):
    """Raised when a creation idempotency record is malformed or stale."""


@dataclass(frozen=True, slots=True)
class CreationReservation:
    status: str
    redis_key: str
    fingerprint: str
    reservation_token: str | None = None
    run_id: str | None = None
    location: str | None = None


def build_creation_fingerprint(
    *,
    mode: str,
    preset_id: str,
    normalized_overrides: Mapping[str, object],
    registry_revision: str,
) -> str:
    payload = {
        "mode": mode,
        "preset_id": preset_id,
        "overrides": dict(sorted(normalized_overrides.items())),
        "registry_revision": registry_revision,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _redis_key(idempotency_key: str, actor_scope: str | None) -> str:
    if _KEY_RE.fullmatch(idempotency_key) is None:
        raise CreationIdempotencyError(
            "creation_idempotency_key must be 20-200 URL-safe random characters"
        )
    scope = actor_scope.strip() if actor_scope else f"anonymous:{hashlib.sha256(idempotency_key.encode()).hexdigest()}"
    if not scope:
        raise CreationIdempotencyError("Authenticated idempotency scope cannot be empty")
    digest = hashlib.sha256(f"{scope}\0{idempotency_key}".encode("utf-8")).hexdigest()
    return f"project-create:idempotency:v1:{digest}"


def _decode_record(raw: object) -> dict[str, object]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if not isinstance(raw, str):
        raise CreationIdempotencyError("Creation idempotency record is unavailable")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CreationIdempotencyError("Creation idempotency record is malformed") from exc
    if not isinstance(payload, dict):
        raise CreationIdempotencyError("Creation idempotency record is malformed")
    return payload


def reserve_creation(
    client: RedisIdempotencyClient,
    *,
    idempotency_key: str,
    actor_scope: str | None,
    fingerprint: str,
) -> CreationReservation:
    redis_key = _redis_key(idempotency_key, actor_scope)
    token = secrets.token_urlsafe(24)
    record = json.dumps(
        {"state": "reserved", "fingerprint": fingerprint, "token": token},
        sort_keys=True,
        separators=(",", ":"),
    )
    if client.set(redis_key, record, nx=True, ex=CREATION_IDEMPOTENCY_TTL_SECONDS):
        return CreationReservation("acquired", redis_key, fingerprint, token)
    payload = _decode_record(client.get(redis_key))
    if payload.get("fingerprint") != fingerprint:
        return CreationReservation("conflict", redis_key, fingerprint)
    if payload.get("state") == "completed":
        run_id = payload.get("run_id")
        location = payload.get("location")
        if isinstance(run_id, str) and isinstance(location, str):
            return CreationReservation("replay", redis_key, fingerprint, run_id=run_id, location=location)
        raise CreationIdempotencyError("Completed creation record is malformed")
    return CreationReservation("in_progress", redis_key, fingerprint)


def complete_creation(
    client: RedisIdempotencyClient,
    reservation: CreationReservation,
    *,
    run_id: str,
    location: str,
) -> None:
    payload = _decode_record(client.get(reservation.redis_key))
    if (
        reservation.status != "acquired"
        or payload.get("token") != reservation.reservation_token
        or payload.get("fingerprint") != reservation.fingerprint
    ):
        raise CreationIdempotencyError("Creation reservation ownership was lost")
    record = json.dumps(
        {
            "state": "completed",
            "fingerprint": reservation.fingerprint,
            "run_id": run_id,
            "location": location,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    if not client.set(
        reservation.redis_key,
        record,
        xx=True,
        ex=CREATION_IDEMPOTENCY_TTL_SECONDS,
    ):
        raise CreationIdempotencyError("Creation reservation expired before completion")


def release_creation(client: RedisIdempotencyClient, reservation: CreationReservation) -> None:
    if reservation.status != "acquired":
        return
    payload = _decode_record(client.get(reservation.redis_key))
    if payload.get("token") == reservation.reservation_token:
        client.delete(reservation.redis_key)
