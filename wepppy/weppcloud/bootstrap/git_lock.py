from __future__ import annotations

import json
import os
import socket
import time
import uuid
from dataclasses import dataclass
from typing import Any

import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs


BOOTSTRAP_GIT_LOCK_TTL_SECONDS = int(os.getenv("BOOTSTRAP_GIT_LOCK_TTL_SECONDS", "900"))
BOOTSTRAP_ENABLE_JOB_TTL_SECONDS = int(os.getenv("BOOTSTRAP_ENABLE_JOB_TTL_SECONDS", "900"))


def bootstrap_git_lock_key(runid: str) -> str:
    return f"bootstrap:git-lock:{runid}"


def bootstrap_enable_job_key(runid: str) -> str:
    return f"bootstrap:enable:job:{runid}"


@dataclass(frozen=True)
class BootstrapGitLock:
    runid: str
    token: str
    operation: str
    actor: str
    owner: str
    acquired_at: int
    ttl_seconds: int


_RELEASE_LOCK_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if not current then
    return 0
end
local decoded = cjson.decode(current)
if decoded.token ~= ARGV[1] then
    return 0
end
return redis.call('DEL', KEYS[1])
"""

_DELETE_IF_EQUALS_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if not current then
    return 0
end
if current ~= ARGV[1] then
    return 0
end
return redis.call('DEL', KEYS[1])
"""


def _lock_owner() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _lock_payload(lock: BootstrapGitLock) -> str:
    return json.dumps(
        {
            "token": lock.token,
            "owner": lock.owner,
            "operation": lock.operation,
            "actor": lock.actor,
            "acquired_at": lock.acquired_at,
            "ttl_seconds": lock.ttl_seconds,
        },
        separators=(",", ":"),
    )


def acquire_bootstrap_git_lock(
    redis_conn: redis.Redis[Any],
    *,
    runid: str,
    operation: str,
    actor: str | None = None,
    ttl_seconds: int = BOOTSTRAP_GIT_LOCK_TTL_SECONDS,
    token: str | None = None,
) -> BootstrapGitLock | None:
    normalized_ttl = max(int(ttl_seconds), 1)
    lock = BootstrapGitLock(
        runid=runid,
        token=token or uuid.uuid4().hex,
        operation=str(operation or "unknown"),
        actor=str(actor or "unknown"),
        owner=_lock_owner(),
        acquired_at=int(time.time()),
        ttl_seconds=normalized_ttl,
    )
    inserted = redis_conn.set(
        bootstrap_git_lock_key(runid),
        _lock_payload(lock),
        nx=True,
        ex=normalized_ttl,
    )
    if not inserted:
        return None
    return lock


def release_bootstrap_git_lock(
    redis_conn: redis.Redis[Any],
    *,
    runid: str,
    token: str,
) -> bool:
    result = redis_conn.eval(_RELEASE_LOCK_SCRIPT, 1, bootstrap_git_lock_key(runid), token)
    return bool(result)


def get_bootstrap_enable_job_id(redis_conn: redis.Redis[Any], runid: str) -> str | None:
    raw = redis_conn.get(bootstrap_enable_job_key(runid))
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore") or None
    return str(raw) or None


def set_bootstrap_enable_job_id(
    redis_conn: redis.Redis[Any],
    *,
    runid: str,
    job_id: str,
    ttl_seconds: int = BOOTSTRAP_ENABLE_JOB_TTL_SECONDS,
) -> None:
    redis_conn.setex(bootstrap_enable_job_key(runid), max(int(ttl_seconds), 1), str(job_id))


def clear_bootstrap_enable_job_id(
    redis_conn: redis.Redis[Any],
    *,
    runid: str,
    expected_job_id: str | None = None,
) -> bool:
    key = bootstrap_enable_job_key(runid)
    if expected_job_id is None:
        return bool(redis_conn.delete(key))
    result = redis_conn.eval(_DELETE_IF_EQUALS_SCRIPT, 1, key, str(expected_job_id))
    return bool(result)


def lock_connection() -> redis.Redis[Any]:
    return redis.Redis(**redis_connection_kwargs(RedisDB.LOCK))


__all__ = [
    "BOOTSTRAP_ENABLE_JOB_TTL_SECONDS",
    "BOOTSTRAP_GIT_LOCK_TTL_SECONDS",
    "BootstrapGitLock",
    "acquire_bootstrap_git_lock",
    "bootstrap_enable_job_key",
    "bootstrap_git_lock_key",
    "clear_bootstrap_enable_job_id",
    "get_bootstrap_enable_job_id",
    "lock_connection",
    "release_bootstrap_git_lock",
    "set_bootstrap_enable_job_id",
]
