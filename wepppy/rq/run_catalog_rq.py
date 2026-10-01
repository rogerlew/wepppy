"""One coalesced catalog sweep on the existing batch queue."""

import hashlib
import logging
import json
from datetime import datetime, timezone

from redis.exceptions import WatchError
from rq import Queue, Worker, worker_registration
from rq.job import Job
from rq.exceptions import NoSuchJobError
from rq.suspension import WORKERS_SUSPENDED

from wepppy.rq.job_id import new_rq_job_id

__all__ = ["sweep_run_catalog", "enqueue_sweep", "is_catalog_job", "safe_job_details", "maintenance_error", "deployment_identity", "operational_status"]

PREFIX = "run_catalog_sweep_"
DESCRIPTION = "Run catalog maintenance"
MESSAGE = "Run catalog maintenance failed; consult operator diagnostics."


def deployment_identity():
    from wepppy.weppcloud.run_catalog.adapter import database_url
    url = database_url()
    identity = (url.host, url.port or 5432, url.database)
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()


def operational_status(connection):
    identity = deployment_identity()
    workers = Worker.all(connection=connection, queue=Queue("batch", connection=connection))
    incompatible = []
    for worker in workers:
        raw = connection.hget(worker.key, "run_catalog_configuration")
        try:
            configuration = json.loads(raw) if raw else {}
        except (ValueError, TypeError):
            configuration = {}
        if configuration != {"protocol": 1, "database": identity, "write_mode": "catalog"}:
            incompatible.append(worker.name)
    raw = connection.get("run-catalog:health:" + identity)
    try:
        health = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        health = {}
    return {"eligible_consumers": len(workers), "incompatible_consumers": incompatible, "sweep": health}


def is_catalog_job(job_id):
    return str(job_id).startswith(PREFIX)


def maintenance_error():
    return {"error": {"code": "run_catalog_maintenance_failed", "message": MESSAGE},
            "error_id": new_rq_job_id()}


def safe_job_details(job_id, job=None):
    status = job.get_status() if job is not None else "failed"
    status = getattr(status, "value", status)
    result = dict(job_id=job_id, runid=None, status=status, result=None, exc_info=None,
                  description=DESCRIPTION, children={}, auth_actor=None,
                  started_at=str(job.started_at) if job is not None and job.started_at else None,
                  ended_at=str(job.ended_at) if job is not None and job.ended_at else None)
    if status in {"failed", "stopped", "canceled"}:
        result.update(maintenance_error())
    return result


def _has_available_worker(queue, identity):
    worker_keys = list(worker_registration.get_keys(queue=queue))
    if not worker_keys:
        return False
    with queue.connection.pipeline(transaction=True) as pipeline:
        pipeline.exists(WORKERS_SUSPENDED)
        for key in worker_keys:
            pipeline.hmget(key, "state", "queues", "run_catalog_configuration", "death")
            pipeline.ttl(key)
        observed = pipeline.execute()
    if observed[0]:
        return False
    expected = {"protocol": 1, "database": identity, "write_mode": "catalog"}
    for fields, ttl in zip(observed[1::2], observed[2::2]):
        state, queues, configuration, death = fields
        if ttl <= 0 or death is not None or state not in ("idle", b"idle"):
            continue
        try:
            if isinstance(queues, bytes):
                queues = queues.decode("utf-8")
            configuration = json.loads(configuration) if configuration else None
        except (ValueError, TypeError, UnicodeError):
            continue
        if isinstance(queues, str) and queue.name in queues.split(",") and configuration == expected:
            return True
    return False


def enqueue_sweep(queue, *, timeout=3600, result_ttl=86400):
    from wepppy.weppcloud.run_catalog.adapter import Settings
    settings = Settings.from_environ()
    if settings.commit_mode != "postgres" or settings.write_mode != "catalog":
        raise ValueError("Catalog sweep requires catalog write mode")
    identity = deployment_identity()
    if not _has_available_worker(queue, identity):
        return False
    key = "run-catalog:admission:" + identity
    with queue.connection.pipeline() as pipeline:
        try:
            pipeline.watch(key)
            previous = pipeline.get(key)
            if previous:
                previous = previous.decode() if isinstance(previous, bytes) else previous
                pipeline.watch(Job.key_for(previous))
                try:
                    job = Job.fetch(previous, connection=queue.connection)
                    state = job.get_status(refresh=True)
                    state = getattr(state, "value", state)
                except NoSuchJobError:
                    state = None
                if state in {"queued", "started", "deferred", "scheduled"}:
                    return False
            identifier = PREFIX + new_rq_job_id()
            queue.enqueue_call(sweep_run_catalog, job_id=identifier, description=DESCRIPTION,
                               timeout=timeout, result_ttl=result_ttl,
                               meta={"run_catalog_maintenance": True}, pipeline=pipeline)
            pipeline.set(key, identifier)
            pipeline.execute()
            return True
        except WatchError:
            return False


def sweep_run_catalog():
    from wepppy.weppcloud.run_catalog.adapter import initialize, get_engine
    from wepppy.weppcloud.run_catalog.service import sweep
    settings = initialize()
    if settings.commit_mode != "postgres" or settings.write_mode != "catalog":
        raise ValueError("Catalog sweep requires catalog write mode")
    result = sweep(get_engine(refresh=True), apply=True)
    logging.getLogger(__name__).info("run_catalog_sweep outcome=%s", result)
    from rq import get_current_job
    job = get_current_job()
    if job is not None:
        job.connection.set("run-catalog:health:" + deployment_identity(), json.dumps({
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "attempted": result.get("attempted", 0),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "failures": result.get("failures", 0),
            "source_seconds": result.get("source_seconds"),
            "sql_acquire_seconds": result.get("sql_acquire_seconds"),
            "sql_publish_seconds": result.get("sql_publish_seconds"),
            "state": result["state"],
            "queue_delay_seconds": (job.started_at - job.enqueued_at).total_seconds() if job.started_at and job.enqueued_at else None,
        }))
    return None
