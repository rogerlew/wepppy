#!/usr/bin/env python3
"""Stress-test harness for Redis NoDb cache client behavior.

This harness is intentionally scoped to Redis DB 13 (NoDb cache) and uses
synthetic run ids by default so it does not collide with active production runs.
It exercises a mixed set/get/delete/scan workload with thread-level concurrency
and emits a machine-readable JSON report.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import socket
import sys
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse, urlunparse

import redis

# Mirror wepppy.nodb.base NODB cache defaults used by redis_nodb_cache_client.
DEFAULT_POOL_KWARGS = {
    "max_connections": 50,
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
    "socket_keepalive": True,
    "health_check_interval": 30,
    "retry_on_timeout": True,
}

ALLOWED_OPERATIONS = ("get", "set", "mutate", "mutate_seq", "delete", "scan")


@dataclass(frozen=True)
class PayloadFixture:
    """Serializable payload fixture used to generate cache key/value pairs."""

    name: str
    relative_path: str
    payload_text: str

    @property
    def payload_bytes(self) -> int:
        return len(self.payload_text.encode("utf-8"))


@dataclass(frozen=True)
class KeyPayload:
    """Prepared cache-key payload with optional decoded JSON object."""

    key: str
    payload_text: str
    decoded_payload: Optional[Any]


class RunStats:
    """Thread-safe aggregate metrics with bounded latency sampling."""

    def __init__(self, sample_limit: int, seed: int) -> None:
        self._lock = threading.Lock()
        self._rng = random.Random(seed)
        self._sample_limit = max(100, sample_limit)

        self.total_ops = 0
        self.success_ops = 0
        self.failed_ops = 0

        self.latency_seen = 0
        self.latency_samples: List[float] = []

        self.op_counts: Counter[str] = Counter()
        self.op_success_counts: Counter[str] = Counter()
        self.op_failure_counts: Counter[str] = Counter()
        self.op_latency_seen: Dict[str, int] = defaultdict(int)
        self.op_latency_samples: Dict[str, List[float]] = defaultdict(list)

        self.error_types: Counter[str] = Counter()

        self.first_failure_monotonic: Optional[float] = None
        self.first_recovery_monotonic: Optional[float] = None

    def _reservoir_add(self, samples: List[float], seen: int, value: float) -> None:
        if seen <= self._sample_limit:
            samples.append(value)
            return
        idx = self._rng.randrange(seen)
        if idx < self._sample_limit:
            samples[idx] = value

    def record(self, op: str, latency_ms: float, ok: bool, error_type: Optional[str], now_mono: float) -> None:
        with self._lock:
            self.total_ops += 1
            self.op_counts[op] += 1

            self.latency_seen += 1
            self._reservoir_add(self.latency_samples, self.latency_seen, latency_ms)

            self.op_latency_seen[op] += 1
            self._reservoir_add(self.op_latency_samples[op], self.op_latency_seen[op], latency_ms)

            if ok:
                self.success_ops += 1
                self.op_success_counts[op] += 1
                if self.first_failure_monotonic is not None and self.first_recovery_monotonic is None:
                    self.first_recovery_monotonic = now_mono
                return

            self.failed_ops += 1
            self.op_failure_counts[op] += 1
            if error_type:
                self.error_types[error_type] += 1
            if self.first_failure_monotonic is None:
                self.first_failure_monotonic = now_mono


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = int(round((len(sorted_values) - 1) * q))
    idx = max(0, min(len(sorted_values) - 1, idx))
    return sorted_values[idx]


def parse_operation_weights(raw: str) -> Dict[str, int]:
    weights: Dict[str, int] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"Invalid operation weight token: {token}")
        name, value = token.split("=", 1)
        op = name.strip().lower()
        if op not in ALLOWED_OPERATIONS:
            raise ValueError(f"Unsupported operation '{op}'. Allowed: {', '.join(ALLOWED_OPERATIONS)}")
        count = int(value.strip())
        if count < 0:
            raise ValueError(f"Weight for '{op}' must be >= 0")
        weights[op] = count

    for op in ALLOWED_OPERATIONS:
        weights.setdefault(op, 0)

    if sum(weights.values()) <= 0:
        raise ValueError("At least one operation weight must be > 0")

    return weights


def build_operation_table(weights: Dict[str, int]) -> List[str]:
    table: List[str] = []
    for op in ALLOWED_OPERATIONS:
        table.extend([op] * weights[op])
    return table


def as_redis_db_url(raw_url: str, db: int) -> str:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid Redis URL: {raw_url}")
    path = f"/{int(db)}"
    return urlunparse(parsed._replace(path=path))


def connection_pool_kwargs_from_url(redis_url: str) -> Dict[str, Any]:
    parsed = urlparse(redis_url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid Redis URL: {redis_url}")

    db = 0
    if parsed.path and parsed.path != "/":
        try:
            db = int(parsed.path.lstrip("/"))
        except ValueError as exc:
            raise ValueError(f"Redis URL path must contain numeric DB index: {redis_url}") from exc

    kwargs: Dict[str, Any] = {
        "host": parsed.hostname,
        "port": parsed.port or 6379,
        "db": db,
    }
    if parsed.username:
        kwargs["username"] = parsed.username
    if parsed.password:
        kwargs["password"] = parsed.password
    return kwargs


def redact_redis_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.hostname:
        return "<invalid-url>"

    host = parsed.hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"

    if parsed.username or parsed.password:
        netloc = f"<redacted>@{host}"
    else:
        netloc = host

    return urlunparse(parsed._replace(netloc=netloc))


def load_builtin_fixtures(fixture_dir: Path) -> List[PayloadFixture]:
    fixtures: List[PayloadFixture] = []

    for path in sorted(fixture_dir.glob("*.json")):
        blob = json.loads(path.read_text(encoding="utf-8"))

        name = str(blob.get("name") or path.stem)
        relpath = str(blob.get("relative_path") or f"{path.stem}.nodb")

        if "payload_text" in blob:
            payload_text = str(blob["payload_text"])
        elif "payload" in blob:
            payload_text = json.dumps(blob["payload"], separators=(",", ":"), ensure_ascii=True)
        else:
            raise ValueError(f"Fixture {path} requires 'payload' or 'payload_text'")

        fixtures.append(
            PayloadFixture(
                name=name,
                relative_path=relpath,
                payload_text=payload_text,
            )
        )

    if not fixtures:
        raise RuntimeError(f"No built-in fixtures found in {fixture_dir}")

    return fixtures


def load_corpus_fixtures(corpus_dir: Path, limit: int) -> List[PayloadFixture]:
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Payload corpus directory not found: {corpus_dir}")

    fixtures: List[PayloadFixture] = []

    for path in sorted(corpus_dir.rglob("*.nodb")):
        relpath = path.relative_to(corpus_dir).as_posix()
        payload_text = path.read_text(encoding="utf-8")
        fixtures.append(
            PayloadFixture(
                name=path.stem,
                relative_path=relpath,
                payload_text=payload_text,
            )
        )
        if limit > 0 and len(fixtures) >= limit:
            break

    if not fixtures:
        raise RuntimeError(f"No .nodb files found under payload corpus: {corpus_dir}")

    return fixtures


def build_runids(prefix: str, count: int) -> List[str]:
    return [f"{prefix}-{idx:06d}" for idx in range(1, count + 1)]


def _decode_payload_text(payload_text: str) -> Optional[Any]:
    try:
        return json.loads(payload_text)
    except json.JSONDecodeError:
        return None


def _build_mutated_payload(
    key_payload: KeyPayload,
    *,
    worker_id: int,
    mutation_id: int,
    seq_index: int,
    seq_len: int,
) -> str:
    mutation_meta = {
        "worker_id": worker_id,
        "mutation_id": mutation_id,
        "seq_index": seq_index,
        "seq_len": seq_len,
        "mutated_at_epoch_s": round(time.time(), 6),
    }

    decoded = key_payload.decoded_payload
    if isinstance(decoded, dict):
        mutated = dict(decoded)
        state = mutated.get("py/state")
        if isinstance(state, dict):
            state_copy = dict(state)
            state_copy["_stress_mutation"] = mutation_meta
            mutated["py/state"] = state_copy
        else:
            mutated["_stress_mutation"] = mutation_meta
        return json.dumps(mutated, separators=(",", ":"), ensure_ascii=True)

    wrapped = {
        "py/object": "wepppy.nodb.stress.RawPayloadMutation",
        "py/state": {
            "payload_text": key_payload.payload_text,
            "_stress_mutation": mutation_meta,
        },
    }
    return json.dumps(wrapped, separators=(",", ":"), ensure_ascii=True)


def build_keys_and_payloads(run_root: str, runids: Iterable[str], fixtures: Iterable[PayloadFixture]) -> List[KeyPayload]:
    items: List[KeyPayload] = []
    root = run_root.rstrip("/")
    for runid in runids:
        run_prefix = runid[:2]
        for fixture in fixtures:
            rel = fixture.relative_path.lstrip("/")
            key = f"{root}/{run_prefix}/{runid}/{rel}"
            items.append(
                KeyPayload(
                    key=key,
                    payload_text=fixture.payload_text,
                    decoded_payload=_decode_payload_text(fixture.payload_text),
                )
            )
    return items


def scan_patterns(run_root: str, runids: Iterable[str]) -> List[str]:
    root = run_root.rstrip("/")
    patterns: List[str] = []
    for runid in runids:
        run_prefix = runid[:2]
        patterns.append(f"{root}/{run_prefix}/{runid}/*")
    return patterns


def select_mutation_keyspace(
    key_payloads: List[KeyPayload],
    *,
    fraction: float,
    seed: int,
) -> List[KeyPayload]:
    if not key_payloads:
        return []

    target = max(1, int(round(len(key_payloads) * fraction)))
    target = min(target, len(key_payloads))

    indices = list(range(len(key_payloads)))
    rng = random.Random(seed ^ 0xA5A5A5A5)
    rng.shuffle(indices)

    return [key_payloads[i] for i in indices[:target]]


def resolve_redis_url(args: argparse.Namespace) -> str:
    selected = sum(
        int(bool(x))
        for x in (
            args.redis_url,
            args.redis_url_env,
            args.use_wepppy_resolver,
        )
    )
    if selected != 1:
        raise RuntimeError(
            "Choose exactly one Redis URL source: --redis-url, --redis-url-env, or --use-wepppy-resolver"
        )

    if args.redis_url:
        raw_url = args.redis_url
    elif args.redis_url_env:
        env_val = os.getenv(args.redis_url_env)
        if not env_val:
            raise RuntimeError(f"Environment variable {args.redis_url_env} is not set")
        raw_url = env_val
    else:
        from wepppy.config.redis_settings import RedisDB, redis_url

        raw_url = redis_url(RedisDB.NODB_CACHE)

    return as_redis_db_url(raw_url, args.redis_db)


def prime_cache_keys(client: redis.Redis, key_payloads: List[KeyPayload], ttl_seconds: int) -> None:
    for key_payload in key_payloads:
        client.set(key_payload.key, key_payload.payload_text, ex=ttl_seconds)


def worker_loop(
    worker_id: int,
    *,
    pool: redis.ConnectionPool,
    key_payloads: List[KeyPayload],
    mutation_keyspace: List[KeyPayload],
    patterns: List[str],
    operation_table: List[str],
    ttl_seconds: int,
    scan_count: int,
    mutate_seq_burst_length: int,
    deadline: float,
    seed: int,
    stats: RunStats,
) -> None:
    rng = random.Random(seed + worker_id)
    client = redis.Redis(connection_pool=pool)
    mutation_counter = 0

    while time.monotonic() < deadline:
        op = rng.choice(operation_table)
        now = time.monotonic()
        t0 = time.perf_counter()

        try:
            if op == "set":
                key_payload = rng.choice(key_payloads)
                client.set(key_payload.key, key_payload.payload_text, ex=ttl_seconds)
            elif op == "mutate":
                key_payload = rng.choice(mutation_keyspace)
                mutation_counter += 1
                payload = _build_mutated_payload(
                    key_payload,
                    worker_id=worker_id,
                    mutation_id=mutation_counter,
                    seq_index=1,
                    seq_len=1,
                )
                client.set(key_payload.key, payload, ex=ttl_seconds)
            elif op == "mutate_seq":
                key_payload = rng.choice(mutation_keyspace)
                seq_len = max(1, mutate_seq_burst_length)
                for seq_index in range(1, seq_len + 1):
                    mutation_counter += 1
                    payload = _build_mutated_payload(
                        key_payload,
                        worker_id=worker_id,
                        mutation_id=mutation_counter,
                        seq_index=seq_index,
                        seq_len=seq_len,
                    )
                    client.set(key_payload.key, payload, ex=ttl_seconds)
            elif op == "get":
                key_payload = rng.choice(key_payloads)
                client.get(key_payload.key)
            elif op == "delete":
                key_payload = rng.choice(key_payloads)
                client.delete(key_payload.key)
            elif op == "scan":
                pattern = rng.choice(patterns)
                client.scan(match=pattern, count=scan_count)
            else:
                raise RuntimeError(f"Unsupported operation: {op}")
        except (redis.exceptions.RedisError, OSError, ValueError) as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            stats.record(op=op, latency_ms=elapsed_ms, ok=False, error_type=type(exc).__name__, now_mono=now)
            continue

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        stats.record(op=op, latency_ms=elapsed_ms, ok=True, error_type=None, now_mono=now)


def build_summary(
    args: argparse.Namespace,
    *,
    redis_url: str,
    fixture_set: List[PayloadFixture],
    runids: List[str],
    key_payloads: List[KeyPayload],
    mutation_keyspace_size: int,
    started_mono: float,
    finished_mono: float,
    started_wall: datetime,
    finished_wall: datetime,
    stats: RunStats,
) -> Dict[str, Any]:
    elapsed_s = max(0.001, finished_mono - started_mono)
    failure_rate = float(stats.failed_ops) / float(stats.total_ops) if stats.total_ops else 0.0

    overall_latency = {
        "p50": round(percentile(stats.latency_samples, 0.50), 3),
        "p95": round(percentile(stats.latency_samples, 0.95), 3),
        "p99": round(percentile(stats.latency_samples, 0.99), 3),
    }

    by_operation: Dict[str, Dict[str, Any]] = {}
    for op in ALLOWED_OPERATIONS:
        samples = stats.op_latency_samples.get(op, [])
        by_operation[op] = {
            "count": int(stats.op_counts.get(op, 0)),
            "success": int(stats.op_success_counts.get(op, 0)),
            "failure": int(stats.op_failure_counts.get(op, 0)),
            "latency_ms": {
                "p50": round(percentile(samples, 0.50), 3),
                "p95": round(percentile(samples, 0.95), 3),
                "p99": round(percentile(samples, 0.99), 3),
            },
        }

    recovery: Dict[str, Optional[float]] = {
        "first_failure_offset_s": None,
        "first_recovery_after_failure_s": None,
    }
    if stats.first_failure_monotonic is not None:
        recovery["first_failure_offset_s"] = round(stats.first_failure_monotonic - started_mono, 3)
    if stats.first_failure_monotonic is not None and stats.first_recovery_monotonic is not None:
        recovery["first_recovery_after_failure_s"] = round(
            stats.first_recovery_monotonic - stats.first_failure_monotonic,
            3,
        )

    return {
        "harness": "redis_nodb_cache_stress",
        "started_at_utc": started_wall.isoformat(),
        "finished_at_utc": finished_wall.isoformat(),
        "host": socket.gethostname(),
        "target_profile": args.target_profile,
        "redis": {
            "url": redact_redis_url(redis_url),
            "db": args.redis_db,
            "pool_kwargs": {
                "max_connections": args.max_connections,
                "socket_timeout": args.socket_timeout,
                "socket_connect_timeout": args.socket_connect_timeout,
                "socket_keepalive": True,
                "health_check_interval": args.health_check_interval,
                "retry_on_timeout": True,
            },
        },
        "workload": {
            "threads": args.threads,
            "duration_seconds": args.duration_seconds,
            "ttl_seconds": args.ttl_seconds,
            "scan_count": args.scan_count,
            "operation_weights": parse_operation_weights(args.operation_weights),
            "mutate_seq_burst_length": args.mutate_seq_burst_length,
            "mutate_hot_key_fraction": args.mutate_hot_key_fraction,
            "mutation_keyspace_size": mutation_keyspace_size,
            "run_root": args.run_root,
            "runid_prefix": args.runid_prefix,
            "runid_count": args.runid_count,
            "generated_key_count": len(key_payloads),
            "fixtures": [
                {
                    "name": fixture.name,
                    "relative_path": fixture.relative_path,
                    "payload_bytes": fixture.payload_bytes,
                }
                for fixture in fixture_set
            ],
            "runids_sample": runids[: min(10, len(runids))],
        },
        "results": {
            "ops_total": stats.total_ops,
            "ops_success": stats.success_ops,
            "ops_failure": stats.failed_ops,
            "failure_rate": round(failure_rate, 6),
            "throughput_ops_per_sec": round(stats.total_ops / elapsed_s, 3),
            "elapsed_seconds": round(elapsed_s, 3),
            "latency_ms": overall_latency,
            "by_operation": by_operation,
            "error_types": dict(stats.error_types),
            "recovery": recovery,
        },
    }


def write_report(output_dir: Path, summary: Dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"redis_nodb_cache_stress_{timestamp}.json"
    report_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stress harness for Redis NoDb cache client behavior")

    parser.add_argument("--target-profile", choices=("local", "wepp1", "wepp2"), default="local")
    parser.add_argument("--run-root", default="/wc1/runs", help="Run-root path used when generating cache keys")
    parser.add_argument("--runid-prefix", default="stresscache")
    parser.add_argument("--runid-count", type=int, default=250)

    parser.add_argument("--threads", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=180)
    parser.add_argument("--ttl-seconds", type=int, default=72 * 3600)
    parser.add_argument("--scan-count", type=int, default=200)
    parser.add_argument("--operation-weights", default="get=35,set=25,mutate=20,mutate_seq=10,delete=5,scan=5")
    parser.add_argument(
        "--mutate-seq-burst-length",
        type=int,
        default=5,
        help="Number of sequential writes executed by each mutate_seq operation",
    )
    parser.add_argument(
        "--mutate-hot-key-fraction",
        type=float,
        default=0.10,
        help="Fraction of generated keys used as mutation hot-key set (0 < f <= 1)",
    )

    parser.add_argument("--fixture-dir", type=Path, default=Path(__file__).resolve().parent / "fixtures")
    parser.add_argument(
        "--payload-corpus-dir",
        type=Path,
        default=None,
        help="Optional directory with real .nodb files to append to the fixture set",
    )
    parser.add_argument(
        "--payload-corpus-limit",
        type=int,
        default=0,
        help="If >0, stop after loading this many .nodb files from --payload-corpus-dir",
    )

    parser.add_argument("--redis-db", type=int, default=13)
    parser.add_argument("--redis-url", default=None)
    parser.add_argument("--redis-url-env", default=None)
    parser.add_argument("--use-wepppy-resolver", action="store_true")

    parser.add_argument("--max-connections", type=int, default=DEFAULT_POOL_KWARGS["max_connections"])
    parser.add_argument("--socket-timeout", type=float, default=DEFAULT_POOL_KWARGS["socket_timeout"])
    parser.add_argument(
        "--socket-connect-timeout",
        type=float,
        default=DEFAULT_POOL_KWARGS["socket_connect_timeout"],
    )
    parser.add_argument(
        "--health-check-interval",
        type=int,
        default=DEFAULT_POOL_KWARGS["health_check_interval"],
    )

    parser.add_argument("--latency-sample-limit", type=int, default=200_000)
    parser.add_argument("--max-failure-rate", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-prime", action="store_true")

    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "results")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.threads <= 0:
        raise RuntimeError("--threads must be > 0")
    if args.duration_seconds <= 0:
        raise RuntimeError("--duration-seconds must be > 0")
    if args.runid_count <= 0:
        raise RuntimeError("--runid-count must be > 0")
    if args.ttl_seconds <= 0:
        raise RuntimeError("--ttl-seconds must be > 0")
    if args.mutate_seq_burst_length <= 0:
        raise RuntimeError("--mutate-seq-burst-length must be > 0")
    if not (0.0 < args.mutate_hot_key_fraction <= 1.0):
        raise RuntimeError("--mutate-hot-key-fraction must be within (0, 1]")

    fixture_set = load_builtin_fixtures(args.fixture_dir)
    if args.payload_corpus_dir is not None:
        fixture_set.extend(load_corpus_fixtures(args.payload_corpus_dir, args.payload_corpus_limit))

    runids = build_runids(args.runid_prefix, args.runid_count)
    key_payloads = build_keys_and_payloads(args.run_root, runids, fixture_set)
    mutation_keyspace = select_mutation_keyspace(
        key_payloads,
        fraction=args.mutate_hot_key_fraction,
        seed=args.seed,
    )
    patterns = scan_patterns(args.run_root, runids)
    operation_table = build_operation_table(parse_operation_weights(args.operation_weights))

    redis_url = resolve_redis_url(args)

    print("== redis_nodb_cache_stress ==")
    print(f"target_profile={args.target_profile}")
    print(f"redis_url={redact_redis_url(redis_url)}")
    print(f"threads={args.threads} duration_seconds={args.duration_seconds} runid_count={args.runid_count}")
    print(f"fixtures={len(fixture_set)} generated_keys={len(key_payloads)} mutation_keyspace={len(mutation_keyspace)}")

    if args.dry_run:
        print("dry-run enabled; no Redis writes executed")
        for key_payload in key_payloads[:5]:
            print(f"sample_key={key_payload.key} payload_bytes={len(key_payload.payload_text.encode('utf-8'))}")
        return 0

    pool_kwargs = connection_pool_kwargs_from_url(redis_url)
    pool_kwargs.update(
        {
            "decode_responses": True,
            "max_connections": args.max_connections,
            "socket_timeout": args.socket_timeout,
            "socket_connect_timeout": args.socket_connect_timeout,
            "socket_keepalive": True,
            "health_check_interval": args.health_check_interval,
            "retry_on_timeout": True,
        }
    )
    pool = redis.ConnectionPool(**pool_kwargs)

    # Fail fast on bad credentials/network before starting worker threads.
    redis.Redis(connection_pool=pool).ping()

    if not args.skip_prime:
        print("priming synthetic keyspace...")
        prime_cache_keys(redis.Redis(connection_pool=pool), key_payloads, ttl_seconds=args.ttl_seconds)

    stats = RunStats(sample_limit=args.latency_sample_limit, seed=args.seed)

    started_wall = datetime.now(timezone.utc)
    started_mono = time.monotonic()
    deadline = started_mono + args.duration_seconds

    workers: List[threading.Thread] = []
    for worker_id in range(args.threads):
        thread = threading.Thread(
            target=worker_loop,
            kwargs={
                "worker_id": worker_id,
                "pool": pool,
                "key_payloads": key_payloads,
                "mutation_keyspace": mutation_keyspace,
                "patterns": patterns,
                "operation_table": operation_table,
                "ttl_seconds": args.ttl_seconds,
                "scan_count": args.scan_count,
                "mutate_seq_burst_length": args.mutate_seq_burst_length,
                "deadline": deadline,
                "seed": args.seed,
                "stats": stats,
            },
            daemon=True,
        )
        workers.append(thread)
        thread.start()

    for thread in workers:
        thread.join()

    finished_mono = time.monotonic()
    finished_wall = datetime.now(timezone.utc)

    summary = build_summary(
        args,
        redis_url=redis_url,
        fixture_set=fixture_set,
        runids=runids,
        key_payloads=key_payloads,
        mutation_keyspace_size=len(mutation_keyspace),
        started_mono=started_mono,
        finished_mono=finished_mono,
        started_wall=started_wall,
        finished_wall=finished_wall,
        stats=stats,
    )

    report_path = write_report(args.output_dir, summary)

    results = summary["results"]
    print(f"ops_total={results['ops_total']} ops_failure={results['ops_failure']} failure_rate={results['failure_rate']}")
    print(f"throughput_ops_per_sec={results['throughput_ops_per_sec']} p95_ms={results['latency_ms']['p95']}")
    print(f"report={report_path}")

    if results["failure_rate"] > args.max_failure_rate:
        print(
            f"failure_rate {results['failure_rate']} exceeded max {args.max_failure_rate}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
