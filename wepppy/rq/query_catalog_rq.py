"""Coalesced query-catalog maintenance on the existing batch queue.

Filesystem receipts are authoritative pending intent. Redis reservations and the
resumable inventory cursor are recoverable accelerators, never acknowledgment.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import os
from pathlib import Path
import time
from typing import Any

import redis
from redis.exceptions import WatchError, LockNotOwnedError
from rq import Queue, get_current_job, worker_registration
from rq.job import Job
from rq.suspension import WORKERS_SUSPENDED

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.job_id import new_rq_job_id

__all__ = [
    "enqueue_catalog_refresh", "refresh_query_catalog_rq", "reconcile_query_catalogs",
    "catalog_worker_configuration", "consumer_status", "QueryCatalogSettings",
    "suspend_catalog_refresh", "resume_catalog_refresh",
]

LOGGER = logging.getLogger(__name__)
PREFIX = "query_catalog_refresh_"
DESCRIPTION = "Query catalog maintenance"
ACTIVE_STATES = frozenset({"queued", "started", "deferred", "scheduled"})
WORKER_FIELD = "query_catalog_configuration"


def _positive_env(name: str, default: int) -> int:
    value = int(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class QueryCatalogSettings:
    enabled: bool
    inventory_limit: int
    admission_limit: int
    retry_seconds: int
    retry_max_seconds: int
    cycle_seconds: int

    @classmethod
    def from_environ(cls) -> "QueryCatalogSettings":
        from wepppy.query_engine.catalog_refresh import catalog_refresh_enabled
        return cls(
            catalog_refresh_enabled(),
            _positive_env("QUERY_CATALOG_INVENTORY_LIMIT", 100),
            _positive_env("QUERY_CATALOG_ADMISSION_LIMIT", 25),
            _positive_env("QUERY_CATALOG_RETRY_SECONDS", 30),
            _positive_env("QUERY_CATALOG_RETRY_MAX_SECONDS", 3600),
            _positive_env("QUERY_CATALOG_CYCLE_SECONDS", 86400),
        )


def catalog_worker_configuration() -> dict[str, Any]:
    from wepppy.query_engine.catalog_refresh import catalog_worker_configuration as configuration
    return {**configuration(), "enabled": QueryCatalogSettings.from_environ().enabled}


def _configuration_id() -> str:
    value = json.dumps(catalog_worker_configuration(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()


def _text(value: Any) -> str | None:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value) if value is not None else None


def _admission_key(scope_id: str, incarnation: str) -> str:
    return "query-catalog:admission:" + scope_id + ":" + incarnation


def _retry_key(scope_id: str) -> str:
    return "query-catalog:retry:" + scope_id


def _suspension_key(scope_id: str) -> str:
    return "query-catalog:suspended:" + scope_id


def _default_queue() -> Queue:
    return Queue("batch", connection=redis.Redis(**redis_connection_kwargs(RedisDB.RQ)))


def consumer_status(queue: Queue) -> dict[str, Any]:
    """Every live consumer must agree, not just one idle local worker."""
    expected = catalog_worker_configuration()
    incompatible: list[str] = []
    compatible = 0
    for key in worker_registration.get_keys(queue=queue):
        fields = queue.connection.hmget(key, "queues", WORKER_FIELD, "death")
        queues, configuration, death = fields
        if death is not None or queue.connection.ttl(key) <= 0:
            continue
        if queue.name not in (_text(queues) or "").split(","):
            continue
        try:
            observed = json.loads(configuration) if configuration else None
        except (ValueError, TypeError):
            observed = None
        if observed != expected:
            incompatible.append(_text(key) or "unknown")
        else:
            compatible += 1
    suspended = bool(queue.connection.exists(WORKERS_SUSPENDED))
    return {"compatible": compatible, "incompatible": incompatible, "suspended": suspended}


def _pending(code: str, job_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"state": "pending", "error_code": code}
    if job_id is not None:
        result["job_id"] = job_id
    return result


def enqueue_catalog_refresh(
    wd: str | Path,
    *,
    scope: dict[str, Any] | None = None,
    queue: Queue | None = None,
    timeout: int = 3600,
    result_ttl: int = 86400,
) -> dict[str, Any]:
    """Admit once per incarnation; leave durable receipts on any contention."""
    from wepppy.query_engine.catalog_refresh import resolve_scope

    settings = QueryCatalogSettings.from_environ()
    resolved = resolve_scope(wd, create=False)
    current = resolved.as_dict()
    if not resolved.managed or not resolved.incarnation:
        raise ValueError("Asynchronous catalog work requires initialized managed scope")
    if scope is not None and any(scope.get(key) != current.get(key) for key in ("scope_id", "incarnation", "namespace")):
        raise ValueError("Catalog scope identity changed before admission")
    if not settings.enabled:
        return _pending("query_catalog_refresh_disabled")
    queue = queue if queue is not None else _default_queue()
    connection = queue.connection
    scope_id = resolved.scope_id
    try:
        connection.sadd("query-catalog:dirty:" + _configuration_id(), str(resolved.base))
        if connection.exists(_suspension_key(scope_id)):
            return _pending("query_catalog_refresh_suspended")
        status = consumer_status(queue)
        if status["suspended"]:
            return _pending("query_catalog_workers_suspended")
        if status["incompatible"] or not status["compatible"]:
            return _pending("query_catalog_workers_unavailable")
        retry_at = connection.hget(_retry_key(scope_id), "next_attempt_at")
        if retry_at and float(retry_at) > time.time():
            return _pending("query_catalog_retry_pending")
        key = _admission_key(scope_id, resolved.incarnation)
        with connection.pipeline() as pipeline:
            try:
                pipeline.watch(key, _suspension_key(scope_id))
                if pipeline.exists(_suspension_key(scope_id)):
                    return _pending("query_catalog_refresh_suspended")
                previous = _text(pipeline.get(key))
                if previous:
                    job_key = Job.key_for(previous)
                    pipeline.watch(job_key)
                    # Reading raw hash fields avoids importing/deserializing an
                    # old or damaged task payload during admission.
                    state, identity = pipeline.hmget(job_key, "status", "query_catalog_scope")
                    if _text(state) in ACTIVE_STATES:
                        if _text(identity) != scope_id:
                            return _pending("query_catalog_admission_invalid", previous)
                        return {"state": "running" if _text(state) == "started" else "queued", "job_id": previous}
                identifier = PREFIX + new_rq_job_id()
                queue.enqueue_call(
                    refresh_query_catalog_rq,
                    kwargs={"wd": str(resolved.base), "scope_id": scope_id,
                            "incarnation": resolved.incarnation,
                            "configuration": catalog_worker_configuration()},
                    job_id=identifier, description=DESCRIPTION,
                    timeout=timeout, result_ttl=result_ttl,
                    meta={"query_catalog_maintenance": True}, pipeline=pipeline,
                )
                pipeline.hset(Job.key_for(identifier), "query_catalog_scope", scope_id)
                pipeline.set(key, identifier)
                pipeline.execute()
                return {"state": "queued", "job_id": identifier}
            except WatchError:
                return _pending("query_catalog_admission_contended")
    except redis.RedisError:
        LOGGER.exception("Query catalog dispatch unavailable scope=%s", scope_id)
        return _pending("query_catalog_dispatch_unavailable")


def suspend_catalog_refresh(connection: Any, scope_id: str) -> None:
    """Explicit operator suspension survives ordinary terminal-job retry."""
    connection.set(_suspension_key(scope_id), "1")


def resume_catalog_refresh(connection: Any, scope_id: str) -> None:
    connection.delete(_suspension_key(scope_id))


def refresh_query_catalog_rq(
    wd: str, *, scope_id: str, incarnation: str, configuration: dict[str, Any]
) -> None:
    """One finite receipt snapshot; scheduler handles late work and retries."""
    from wepppy.query_engine.catalog_refresh import refresh_catalog, resolve_scope

    job = get_current_job()
    if job is None:
        raise RuntimeError("Query catalog maintenance requires an RQ job")
    settings = QueryCatalogSettings.from_environ()
    if not settings.enabled or configuration != catalog_worker_configuration():
        raise RuntimeError("Query catalog worker configuration is incompatible")
    connection = job.connection
    if connection.exists(_suspension_key(scope_id)):
        return None
    resolved = resolve_scope(wd, create=False)
    if resolved.scope_id != scope_id or resolved.incarnation != incarnation or not resolved.managed:
        raise ValueError("Queued catalog project identity is no longer current")
    # Recheck executing worker's raw registration before filesystem work.
    registration = connection.hget("rq:worker:" + job.worker_name, WORKER_FIELD) if job.worker_name else None
    if not registration or json.loads(registration) != configuration:
        raise RuntimeError("Executing worker did not advertise catalog compatibility")
    try:
        refresh_catalog(wd, expected_incarnation=incarnation, strict=True)
    except (OSError, ValueError, RuntimeError):
        # Worker boundary: retain core failure evidence/receipts and retry budget.
        attempts = connection.hincrby(_retry_key(scope_id), "attempts", 1)
        delay = min(settings.retry_max_seconds, settings.retry_seconds * 2 ** min(attempts - 1, 16))
        connection.hset(_retry_key(scope_id), mapping={"next_attempt_at": time.time() + delay})
        raise
    else:
        connection.delete(_retry_key(scope_id))
    # Keep the admission pointer while RQ still marks this job started.
    # A later tick replaces only terminal/missing jobs, including late receipts.
    return None


def _inventory_step(roots: list[Any], cursor: dict[str, Any], limit: int) -> tuple[list[Path], dict[str, Any]]:
    """Bound directory visits; never follow symlinks or enter scientific trees."""
    stack = list(cursor.get("stack", []))
    if not cursor.get("initialized"):
        stack = [{"root": index, "relative": "."} for index in reversed(range(len(roots)))]
    found: list[Path] = []
    errors: list[dict[str, str]] = []
    visited = 0
    while stack and visited < limit:
        item = stack.pop()
        visited += 1
        root_index = item["root"]
        root = Path(roots[root_index].path)
        path = root / item["relative"]
        try:
            if path.is_symlink() or not path.is_dir():
                continue
            path.resolve().relative_to(root.resolve())
            project = (path / "ron.nodb").is_file() or (path / "wepp.nodb").is_file() or (path / "_query_engine/catalog.json").is_file()
            if project:
                found.append(path)
                children = [path / name for name in ("_pups", "rhessys/scenarios", "runs", "_base")
                            if (path / name).is_dir()]
            else:
                children = sorted((entry for entry in path.iterdir() if entry.is_dir() and not entry.is_symlink()), reverse=True)
            for child in children:
                stack.append({"root": root_index, "relative": str(child.relative_to(root))})
        except (OSError, ValueError) as exc:
            errors.append({"root": str(root_index), "relative": item["relative"], "error": type(exc).__name__})
    return found, {"initialized": True, "stack": stack, "errors": errors, "visited": visited}


def reconcile_query_catalogs(*, queue: Queue | None = None) -> dict[str, Any]:
    """Scheduler-side bounded rediscovery plus recurring source reconciliation."""
    from wepppy.query_engine.catalog_refresh import (
        configured_roots, record_catalog_refresh, resolve_scope, pending_catalog_requests,
        is_catalog_readonly,
    )

    settings = QueryCatalogSettings.from_environ()
    if not settings.enabled:
        return {"state": "disabled", "admitted": 0}
    queue = queue if queue is not None else _default_queue()
    connection = queue.connection
    identity = _configuration_id()
    key = "query-catalog:inventory:" + identity
    lock = connection.lock(key + ":lock", timeout=60, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        return {"state": "already_running", "admitted": 0}
    try:
        raw = connection.get(key)
        cursor = json.loads(raw) if raw else {}
        now = time.time()
        roots = configured_roots()
        available_namespaces: set[str] = set()
        expected_namespaces = {root.namespace for root in roots}
        for root in roots:
            try:
                if Path(root.path).is_dir() and os.access(root.path, os.R_OK | os.X_OK):
                    available_namespaces.add(root.namespace)
            except OSError:
                LOGGER.warning("Catalog inventory root unavailable namespace=%s", root.namespace)
        unavailable_namespaces = sorted(expected_namespaces - available_namespaces)
        if unavailable_namespaces and cursor.get("completed_at"):
            # A missing namespace is not a completed empty inventory. Retry on
            # ordinary ticks, without waiting the full source-cycle interval.
            cursor.pop("completed_at", None)
            cursor.pop("discovery_completed_at", None)
            cursor["initialized"] = False
        dirty_key = "query-catalog:dirty:" + identity
        dirty_cursor, dirty_paths = connection.sscan(
            dirty_key, cursor=cursor.get("dirty_cursor", 0), count=settings.admission_limit
        )
        retry_candidates = [{"path": _text(value), "reconcile": False} for value in dirty_paths]
        if cursor.get("completed_at") and now < cursor["completed_at"] + settings.cycle_seconds:
            candidates = []
            scan = dict(cursor)
        elif cursor.get("discovery_completed_at") and not cursor.get("completed_at"):
            candidates = []
            scan = dict(cursor)
        else:
            new_cycle = not cursor.get("initialized")
            candidates, scan = _inventory_step(roots, cursor, settings.inventory_limit)
            scan["cycle_started_at"] = now if new_cycle else cursor["cycle_started_at"]
            scan["previous_cycle_errors"] = cursor.get("cycle_errors", []) if new_cycle else cursor.get("previous_cycle_errors", [])
            scan["cycle_errors"] = ([] if new_cycle else list(cursor.get("cycle_errors", []))) + scan.pop("errors", [])
            if not scan["stack"]:
                scan["discovery_completed_at"] = now
        pending = list(cursor.get("pending", []))
        pending.extend({"path": str(path), "reconcile": True, "cycle": True} for path in candidates)
        pending.extend(retry_candidates)
        # One pending scope, retaining full reconciliation when either source needs it.
        by_path = {}
        for item in pending:
            existing = by_path.setdefault(item["path"], dict(item))
            existing["reconcile"] = existing["reconcile"] or item["reconcile"]
            existing["cycle"] = existing.get("cycle", False) or item.get("cycle", False)
        pending = list(by_path.values())
        admitted = 0
        failures: list[dict[str, str]] = []
        for _ in range(min(settings.admission_limit, len(pending))):
            item = pending.pop(0)
            path = Path(item["path"])
            try:
                if not path.is_dir() or is_catalog_readonly(path):
                    connection.srem(dirty_key, str(path))
                    continue
                scope = resolve_scope(path, create=True)
                if not scope.managed:
                    raise ValueError("Inventory scope is not managed")
                if item["reconcile"]:
                    # Full scan detects the artifact-publication/pre-receipt crash gap.
                    record_catalog_refresh(path)
                    item["reconcile"] = False
                elif not pending_catalog_requests(path):
                    connection.srem(dirty_key, str(path))
                    continue
                result = enqueue_catalog_refresh(path, scope=scope.as_dict(), queue=queue)
                if result.get("job_id"):
                    admitted += 1
                if item.get("cycle"):
                    pending.append(item)
            except (OSError, ValueError, RuntimeError) as exc:
                LOGGER.exception("Catalog reconciliation could not admit scope")
                failures.append({"scope": hashlib.sha256(str(path).encode()).hexdigest(), "error": type(exc).__name__})
                # Retry failed discovery as well as producer-registered dirty scopes.
                connection.sadd(dirty_key, str(path))
                if item.get("cycle"):
                    pending.append(item)
        if scan.get("discovery_completed_at") and not unavailable_namespaces and not any(item.get("cycle") for item in pending):
            scan.setdefault("completed_at", now)
            scan["initialized"] = False
        if unavailable_namespaces:
            scan.pop("discovery_completed_at", None)
            if not scan.get("stack"):
                scan["initialized"] = False
        scan["unavailable_namespaces"] = unavailable_namespaces
        scan["dirty_cursor"] = dirty_cursor
        scan["pending"] = pending
        scan["last_tick_at"] = now
        scan["admitted"] = admitted
        scan["failures"] = failures
        scan["target_cycle_seconds"] = settings.cycle_seconds
        # Fence cursor publication against an expired scheduler lease. Duplicate
        # admissions are coalesced, but an old cursor must not skip newer work.
        with connection.pipeline() as pipeline:
            pipeline.watch(lock.name)
            if pipeline.get(lock.name) != lock.local.token:
                return {"state": "lease_lost", "admitted": admitted}
            pipeline.multi()
            pipeline.set(key, json.dumps(scan))
            try:
                pipeline.execute()
            except WatchError:
                return {"state": "lease_lost", "admitted": admitted}
        state = "pending" if pending or scan.get("stack") else "completed"
        if failures or scan.get("cycle_errors") or unavailable_namespaces:
            state = "degraded"
        return {"state": state, "admitted": admitted,
                "visited": scan.get("visited", 0), "failures": len(failures) + len(scan.get("cycle_errors", [])) + len(unavailable_namespaces),
                "unavailable_namespaces": unavailable_namespaces,
                "cycle_started_at": scan.get("cycle_started_at"), "completed_at": scan.get("completed_at")}
    finally:
        try:
            lock.release()
        except LockNotOwnedError:
            LOGGER.warning("Catalog reconciliation lease expired; cursor not owned")
