"""Coalesced query-catalog maintenance on the existing default queue.

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
    "suspend_catalog_refresh", "resume_catalog_refresh", "inventory_query_catalog_rq",
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
    return {**configuration(), "enabled": QueryCatalogSettings.from_environ().enabled,
            "inventory_protocol": 1, "admission_protocol": 1, "pilot_protocol": 1, "queue": "default"}


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
    return Queue("default", connection=redis.Redis(**redis_connection_kwargs(RedisDB.RQ)))


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
    pilot_id: str | None = None,
    controller_token: str | None = None,
) -> dict[str, Any]:
    """Admit once per incarnation; leave durable receipts on any contention."""
    from wepppy.query_engine.catalog_refresh import resolve_scope
    from . import _query_catalog_admission as admission, _query_catalog_pilot as pilot

    if pilot_id:
        pilot.authorize_receipt((queue if queue is not None else _default_queue()).connection, pilot_id, str(wd), controller_token)
    settings = QueryCatalogSettings.from_environ()
    resolved = resolve_scope(wd, create=False)
    current = resolved.as_dict()
    if not resolved.managed or not resolved.incarnation:
        raise ValueError("Asynchronous catalog work requires initialized managed scope")
    if scope is not None and any(scope.get(key) != current.get(key) for key in ("scope_id", "incarnation", "namespace")):
        raise ValueError("Catalog scope identity changed before admission")
    if not settings.enabled and not pilot_id:
        return _pending("query_catalog_refresh_disabled")
    queue = queue if queue is not None else _default_queue()
    connection = queue.connection
    scope_id = resolved.scope_id
    try:
        if not pilot_id:
            connection.sadd("query-catalog:dirty:" + _configuration_id(), str(resolved.base))
        if connection.exists(_suspension_key(scope_id)):
            return _pending("query_catalog_refresh_suspended")
        status = consumer_status(queue)
        if status["suspended"]:
            return _pending("query_catalog_workers_suspended")
        if status["incompatible"] or not status["compatible"]:
            if pilot_id:
                pilot.pause_pilot(connection, pilot_id, "configuration_mismatch")
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
                ticket = admission.prepare(pipeline, queue, job_id=identifier, kind="refresh",
                                           configuration=catalog_worker_configuration(), scope=current,
                                           pilot_id=pilot_id, controller_token=controller_token)
                queue.enqueue_call(
                    refresh_query_catalog_rq,
                    kwargs={"wd": str(resolved.base), "scope_id": scope_id,
                            "incarnation": resolved.incarnation,
                            "configuration": catalog_worker_configuration(), "pilot_id": pilot_id},
                    job_id=identifier, description=DESCRIPTION,
                    timeout=timeout, result_ttl=result_ttl,
                    meta={"query_catalog_maintenance": True}, pipeline=pipeline,
                )
                pipeline.hset(Job.key_for(identifier), "query_catalog_scope", scope_id)
                pipeline.set(key, identifier)
                admission.commit(pipeline, ticket)
                pipeline.execute()
                return {"state": "queued", "job_id": identifier}
            except admission.AdmissionDenied as exc:
                return _pending(str(exc))
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
    wd: str, *, scope_id: str, incarnation: str, configuration: dict[str, Any], pilot_id: str | None = None
) -> None:
    """One finite receipt snapshot; scheduler handles late work and retries."""
    from wepppy.query_engine.catalog_refresh import refresh_catalog, resolve_scope

    job = get_current_job()
    if job is None:
        raise RuntimeError("Query catalog maintenance requires an RQ job")
    settings = QueryCatalogSettings.from_environ()
    if (not settings.enabled and not pilot_id) or configuration != catalog_worker_configuration():
        raise RuntimeError("Query catalog worker configuration is incompatible")
    connection = job.connection
    from . import _query_catalog_admission as admission
    registration = connection.hget("rq:worker:" + job.worker_name, WORKER_FIELD) if job.worker_name else None
    if not registration or json.loads(registration) != configuration:
        raise RuntimeError("Executing worker did not advertise catalog compatibility")
    admission.authorize_job(connection, job, kind="refresh", pilot_id=pilot_id, scope_id=scope_id, wd=wd)
    try:
        if connection.exists(_suspension_key(scope_id)):
            return None
        resolved = resolve_scope(wd, create=False)
        if resolved.scope_id != scope_id or resolved.incarnation != incarnation or not resolved.managed:
            raise ValueError("Queued catalog project identity is no longer current")
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
    finally:
        admission.execution_exited(connection, job, pilot_id)


def _enqueue_inventory(queue: Queue, key: str, roots: list[Any], *, new_cycle: bool, lock: Any, pilot_id: str | None = None, controller_token: str | None = None) -> dict[str, Any]:
    from wepppy.rq import _query_catalog_inventory as inventory
    from . import _query_catalog_admission as admission, _query_catalog_pilot as pilot

    status = consumer_status(queue)
    if status["suspended"] or status["incompatible"] or not status["compatible"]:
        if pilot_id:
            pilot.pause_pilot(queue.connection, pilot_id, "configuration_mismatch")
        return {**inventory.state(queue.connection, key), "state": "unavailable"}
    connection = queue.connection
    with connection.pipeline() as pipe:
        try:
            pipe.watch(key + ":discovery", key + ":generation", lock.name)
            if pipe.get(lock.name) != lock.local.token:
                return {"state": "lease_lost"}
            current = inventory.state(pipe, key)
            previous = current.get("job_id")
            if previous:
                pipe.watch(Job.key_for(previous))
                job_state = _text(pipe.hget(Job.key_for(previous), "status"))
                if job_state in ACTIVE_STATES:
                    return current
            if not new_cycle and current.get("completed_at"):
                return current
            if previous and not new_cycle and current.get("failed_job") != previous:
                # Hard worker death/timeout bypasses the worker's error boundary.
                # Give its retained frontier the same bounded retry policy.
                settings = QueryCatalogSettings.from_environ()
                attempts = current.get("attempts", 0) + 1
                current["errors"] = current.get("errors") or ["InventoryJobFailed"]
                current.update(attempts=attempts, failed_job=previous,
                               retry_at=time.time() + min(settings.retry_max_seconds, settings.retry_seconds * 2 ** min(attempts - 1, 16)))
                pipe.multi()
                pipe.set(key + ":discovery", json.dumps(current))
                pipe.execute()
                return current
            if current.get("retry_at", 0) > time.time():
                return current
            identifier = PREFIX + new_rq_job_id()
            cycle = identifier if new_cycle or not current else current["cycle"]
            initialize_cycle = new_cycle or not current
            if initialize_cycle:
                current = {"cycle": cycle, "started_at": time.time(), "visited": 0,
                           "entries": 0, "errors": []}
            current["job_id"] = identifier
            current.pop("retry_at", None)
            ticket = admission.prepare(pipe, queue, job_id=identifier, kind="inventory",
                                       configuration=catalog_worker_configuration(), pilot_id=pilot_id,
                                       controller_token=controller_token)
            seeds = None
            if pilot_id:
                seeds = []
                for scope in ticket['pilot']['manifest']['scopes']:
                    for index, root in enumerate(roots):
                        if Path(scope['path']).is_relative_to(root.path):
                            seeds.append({'root': index, 'relative': str(Path(scope['path']).relative_to(root.path))})
                            break
                    else:
                        raise ValueError('Pilot inventory seed is not configured')
            queue.enqueue_call(
                inventory_query_catalog_rq,
                kwargs={"configuration": catalog_worker_configuration(), "cycle": cycle, "pilot_id": pilot_id},
                job_id=identifier, description=DESCRIPTION, timeout=3600, result_ttl=86400,
                meta={"query_catalog_maintenance": True}, pipeline=pipe,
            )
            if initialize_cycle:
                inventory.initialize(pipe, key, cycle, roots, seeds=seeds)
            pipe.set(key + ":discovery", json.dumps(current))
            pipe.set(key + ":generation", json.dumps([cycle, identifier]))
            admission.commit(pipe, ticket)
            pipe.execute()
            return current
        except admission.AdmissionDenied as exc:
            return {**inventory.state(connection, key), "state": "unavailable", "error_code": str(exc)}
        except WatchError:
            return {"state": "contended"}


def inventory_query_catalog_rq(*, configuration: dict[str, Any], cycle: str, pilot_id: str | None = None) -> None:
    """Read configured roots only; publish fenced Redis discovery checkpoints."""
    from wepppy.query_engine.catalog_refresh import configured_roots
    from wepppy.rq import _query_catalog_inventory as inventory

    job = get_current_job()
    if job is None or configuration != catalog_worker_configuration() or (not QueryCatalogSettings.from_environ().enabled and not pilot_id):
        raise RuntimeError("Inventory worker configuration is incompatible")
    registration = job.connection.hget("rq:worker:" + job.worker_name, WORKER_FIELD) if job.worker_name else None
    if not registration or json.loads(registration) != configuration:
        raise RuntimeError("Executing inventory worker did not advertise compatibility")
    from . import _query_catalog_admission as admission, _query_catalog_pilot as pilot
    manifest = admission.authorize_job(job.connection, job, kind="inventory", pilot_id=pilot_id)
    try:
        key = "query-catalog:inventory:" + _configuration_id() + (":pilot:" + pilot_id if pilot_id else "")
        settings = QueryCatalogSettings.from_environ()
        try:
            inventory.run(job.connection, key, job.id, cycle, configured_roots(), settings.inventory_limit,
                          approved_paths={s["path"] for s in manifest["scopes"]} if manifest else None,
                          validate_scope=(lambda path: pilot._scope(manifest, str(path))) if manifest else None)
        except inventory.InventorySuperseded:
            raise
        except (OSError, ValueError, RuntimeError):
            # Boundary: retain retry metadata only while this attempt still owns state.
            with job.connection.pipeline() as pipe:
                pipe.watch(key + ":discovery")
                current = inventory.state(pipe, key)
                if current.get("job_id") == job.id and current.get("cycle") == cycle:
                    attempts = current.get("attempts", 0) + 1
                    current["attempts"] = attempts
                    current["failed_job"] = job.id
                    current["retry_at"] = time.time() + min(settings.retry_max_seconds, settings.retry_seconds * 2 ** min(attempts - 1, 16))
                    pipe.multi()
                    pipe.set(key + ":discovery", json.dumps(current))
                    try:
                        pipe.execute()
                    except WatchError:
                        LOGGER.info("Inventory retry publication superseded")
            raise
    finally:
        admission.execution_exited(job.connection, job, pilot_id)


def reconcile_query_catalogs(*, queue: Queue | None = None, pilot_id: str | None = None, controller_token: str | None = None) -> dict[str, Any]:
    """Admit streaming discovery and drain bounded durable scope checkpoints."""
    from wepppy.query_engine.catalog_refresh import (
        configured_roots, record_catalog_refresh, resolve_scope, pending_catalog_requests,
        is_catalog_readonly,
    )
    from wepppy.rq import _query_catalog_inventory as inventory

    settings = QueryCatalogSettings.from_environ()
    if not settings.enabled and not pilot_id:
        return {"state": "disabled", "admitted": 0}
    queue = queue if queue is not None else _default_queue()
    connection = queue.connection
    identity = _configuration_id()
    from . import _query_catalog_pilot as pilot
    manifest = pilot.read(connection, pilot_id)["manifest"] if pilot_id else None
    key = "query-catalog:inventory:" + identity + (":pilot:" + pilot_id if pilot_id else "")
    roots = configured_roots()
    available_namespaces: set[str] = set()
    unavailable_aliases: list[dict[str, Any]] = []
    # Metadata probes run outside the scheduler lease. A completed inventory
    # must not conceal a lost mount until the next daily cycle; aliases share
    # availability, so an absent redundant spelling is not a missing namespace.
    for index, root in enumerate(roots):
        if manifest and not any(Path(s["path"]).is_relative_to(root.path) for s in manifest["scopes"]):
            continue
        try:
            path = inventory.validated_path(roots, {"root": index, "relative": "."})
            if path.is_dir() and os.access(path, os.R_OK | os.X_OK):
                available_namespaces.add(root.namespace)
            else:
                unavailable_aliases.append({"root": index, "namespace": root.namespace, "error": "Unavailable"})
        except (OSError, ValueError) as exc:
            unavailable_aliases.append({"root": index, "namespace": root.namespace, "error": type(exc).__name__})
            LOGGER.warning("Catalog inventory root unavailable namespace=%s", root.namespace)
    expected_namespaces = {s["namespace"] for s in manifest["scopes"]} if manifest else {root.namespace for root in roots}
    unavailable_namespaces = sorted(expected_namespaces - available_namespaces)
    lock = connection.lock(key + ":lock", timeout=60, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        return {"state": "already_running", "admitted": 0}
    try:
        raw = connection.get(key)
        cursor = json.loads(raw) if raw else {}
        now = time.time()
        if unavailable_namespaces:
            cursor.pop("completed_at", None)
            cursor.pop("discovery_completed_at", None)
            cursor["rediscovery_required"] = True
        discovery = inventory.state(connection, key)
        new_cycle = (not discovery or bool(cursor.get("rediscovery_required")) or
                     bool(cursor.get("completed_at") and now >= cursor["completed_at"] + settings.cycle_seconds))
        if not unavailable_namespaces and (new_cycle or not discovery.get("completed_at")):
            discovery = _enqueue_inventory(queue, key, roots, new_cycle=new_cycle, lock=lock, pilot_id=pilot_id, controller_token=controller_token)
        scan = dict(cursor)
        if discovery.get("cycle") != cursor.get("cycle"):
            scan = {"cycle": discovery.get("cycle"), "stream_ack": "0-0",
                    "cycle_started_at": discovery.get("started_at", now),
                    "previous_cycle_errors": cursor.get("cycle_errors", [])}
        if unavailable_namespaces:
            scan["rediscovery_required"] = True
        scan["unavailable_namespaces"] = unavailable_namespaces
        scan["unavailable_aliases"] = unavailable_aliases
        ack = scan.get("stream_ack", "0-0")
        records = connection.xrange(key + ":stream", min="(" + ack, count=settings.inventory_limit)
        candidates = [Path(_text(fields.get(b"path", fields.get("path")))) for _, fields in records]
        if records:
            scan["stream_ack"] = _text(records[-1][0])
        scan["cycle_errors"] = discovery.get("errors", [])
        scan["visited"] = discovery.get("visited", 0)
        stream_drained = not connection.xrange(key + ":stream", min="(" + scan.get("stream_ack", "0-0"), count=1)
        if discovery.get("completed_at") and stream_drained and not scan.get("rediscovery_required"):
            scan["discovery_completed_at"] = discovery["completed_at"]
        dirty_key = "query-catalog:dirty:" + identity + (":pilot:" + pilot_id if pilot_id else "")
        dirty_cursor, dirty_paths = (0, []) if pilot_id else connection.sscan(dirty_key, cursor=cursor.get("dirty_cursor", 0), count=settings.admission_limit)
        retry_candidates = [{"path": _text(value), "reconcile": False} for value in dirty_paths]
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
            # Redis verifies the current token; an expired lease is never revived.
            try:
                lock.reacquire()
            except LockNotOwnedError:
                return {"state": "lease_lost", "admitted": admitted}
            item = pending.pop(0)
            path = Path(item["path"])
            try:
                # Stream, dirty-index and retained-cursor paths are locators,
                # never authority. Reject redirection before resolving helpers
                # can initialize even standalone project metadata.
                if manifest:
                    pilot._scope(manifest, item["path"])
                path = inventory.validated_scope_path(roots, item["path"])
                if is_catalog_readonly(path):
                    connection.srem(dirty_key, str(path), item["path"])
                    continue
                existing_scope = resolve_scope(path, create=False)
                if not existing_scope.managed:
                    raise ValueError("Inventory scope is not managed")
                inventory.validated_scope_path(roots, str(path))
                scope = resolve_scope(path, create=not bool(pilot_id))
                if not scope.managed:
                    raise ValueError("Inventory scope is not managed")
                if item["reconcile"]:
                    # Full scan detects the artifact-publication/pre-receipt crash gap.
                    if pilot_id:
                        from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard
                        with catalog_lifecycle_guard(path):
                            pilot.authorize_receipt(connection, pilot_id, str(path), controller_token)
                            record_catalog_refresh(path)
                    else:
                        record_catalog_refresh(path)
                    item["reconcile"] = False
                elif not pending_catalog_requests(path):
                    connection.srem(dirty_key, str(path), item["path"])
                    continue
                result = enqueue_catalog_refresh(path, scope=scope.as_dict(), queue=queue, pilot_id=pilot_id, controller_token=controller_token)
                if result.get("job_id"):
                    admitted += 1
                if item.get("cycle"):
                    pending.append(item)
            except inventory.InventoryScopeMissing:
                connection.srem(dirty_key, str(path), item["path"])
            except (OSError, ValueError, RuntimeError) as exc:
                LOGGER.exception("Catalog reconciliation could not admit scope")
                failures.append({"scope": hashlib.sha256(str(path).encode()).hexdigest(), "error": type(exc).__name__})
                # Retry failed discovery as well as producer-registered dirty scopes.
                if not pilot_id:
                    connection.sadd(dirty_key, str(path))
                if item.get("cycle"):
                    pending.append(item)
        if (scan.get("discovery_completed_at") and not scan.get("rediscovery_required") and
                not scan.get("cycle_errors") and not any(item.get("cycle") for item in pending)):
            scan.setdefault("completed_at", now)
        scan.update(dirty_cursor=dirty_cursor, pending=pending, last_tick_at=now,
                    admitted=admitted, failures=failures, target_cycle_seconds=settings.cycle_seconds)
        with connection.pipeline() as pipeline:
            pipeline.watch(lock.name, key + ":generation")
            latest = inventory.state(pipeline, key)
            if pipeline.get(lock.name) != lock.local.token or latest.get("cycle") != scan.get("cycle"):
                return {"state": "lease_lost", "admitted": admitted}
            pipeline.multi()
            # Batch acknowledgment and durable pending publication are one commit.
            pipeline.set(key, json.dumps(scan))
            if records:
                pipeline.xdel(key + ":stream", *(identifier for identifier, _ in records))
            try:
                pipeline.execute()
            except WatchError:
                return {"state": "lease_lost", "admitted": admitted}
        state = "completed" if scan.get("completed_at") else "pending"
        if failures or scan.get("cycle_errors") or unavailable_namespaces or discovery.get("state") == "unavailable":
            state = "degraded"
        return {"state": state, "admitted": admitted, "visited": scan.get("visited", 0),
                "failures": len(failures) + len(scan.get("cycle_errors", [])) + len(unavailable_namespaces),
                "unavailable_namespaces": unavailable_namespaces,
                "unavailable_aliases": unavailable_aliases,
                "cycle_started_at": scan.get("cycle_started_at"), "completed_at": scan.get("completed_at"),
                "inventory_job_id": discovery.get("job_id")}
    finally:
        try:
            lock.release()
        except LockNotOwnedError:
            LOGGER.warning("Catalog reconciliation lease expired; cursor not owned")
