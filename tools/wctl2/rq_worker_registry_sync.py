from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable, List

import redis
from rq import Worker
from rq import worker_registration

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

_WORKER_KEY_PATTERN = f"{Worker.redis_worker_namespace_prefix}*"
_WORKER_QUEUE_KEY_PATTERN = f"{worker_registration.WORKERS_BY_QUEUE_KEY.split('%s', 1)[0]}*"


@dataclass(frozen=True)
class RegistrySyncResult:
    worker_hashes_seen: int
    workers_registered: int
    queue_sets_cleared: int


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _scan_keys(redis_conn: redis.Redis, pattern: str) -> list[str]:
    keys: list[str] = []
    for raw in redis_conn.scan_iter(match=pattern):
        key = _as_text(raw).strip()
        if key:
            keys.append(key)
    # Keep key order deterministic for tests/logging.
    return sorted(set(keys))


def _worker_hash_keys(redis_conn: redis.Redis) -> list[str]:
    return _scan_keys(redis_conn, _WORKER_KEY_PATTERN)


def _worker_queue_set_keys(redis_conn: redis.Redis) -> list[str]:
    return _scan_keys(redis_conn, _WORKER_QUEUE_KEY_PATTERN)


def _clear_worker_sets(redis_conn: redis.Redis, queue_set_keys: Iterable[str]) -> int:
    queue_keys = [key for key in queue_set_keys if key]
    keys_to_delete = [Worker.redis_workers_keys, *queue_keys]
    redis_conn.delete(*keys_to_delete)
    return len(queue_keys)


def rebuild_worker_registry_sets(redis_conn: redis.Redis) -> RegistrySyncResult:
    worker_keys = _worker_hash_keys(redis_conn)
    queue_set_keys = _worker_queue_set_keys(redis_conn)
    queue_sets_cleared = _clear_worker_sets(redis_conn, queue_set_keys)

    workers_registered = 0
    for worker_key in worker_keys:
        worker = Worker.find_by_key(worker_key, connection=redis_conn)
        if worker is None:
            continue
        worker_registration.register(worker)
        workers_registered += 1

    return RegistrySyncResult(
        worker_hashes_seen=len(worker_keys),
        workers_registered=workers_registered,
        queue_sets_cleared=queue_sets_cleared,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild RQ worker registry set indexes from live worker hashes."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print rebuild counters to stdout.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        result = rebuild_worker_registry_sets(redis_conn)

    if args.verbose:
        print(
            "worker_registry_sync:"
            f" worker_hashes_seen={result.worker_hashes_seen}"
            f" workers_registered={result.workers_registered}"
            f" queue_sets_cleared={result.queue_sets_cleared}"
        )


if __name__ == "__main__":
    main()
