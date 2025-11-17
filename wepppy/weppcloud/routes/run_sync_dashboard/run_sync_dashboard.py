"""Admin dashboard for run sync and provenance registration."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List

import redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.registry import DeferredJobRegistry, FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.run_sync_rq import DEFAULT_TARGET_ROOT, STATUS_CHANNEL_SUFFIX, run_sync_rq

from .._common import *  # noqa: F401,F403
from .._common import parse_request_payload

RUN_SYNC_TIMEOUT = 86_400  # 24 hours

run_sync_dashboard_bp = Blueprint('run_sync_dashboard', __name__, template_folder='templates')


@contextmanager
def _redis_conn():
    conn = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _as_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _job_is_run_sync(job: Job) -> bool:
    name = getattr(job, "func_name", "") or ""
    return name.endswith("run_sync_rq") or "run_sync_rq" in name


def _serialize_job(job: Job, status_label: str) -> Dict[str, Any]:
    meta = job.meta or {}
    args = list(job.args or [])
    runid = meta.get("runid") or (args[0] if len(args) > 0 else None)
    config = meta.get("config") or (args[1] if len(args) > 1 else None)
    source_host = meta.get("source_host") or (args[2] if len(args) > 2 else None)
    return {
        "id": job.id,
        "status": status_label,
        "job_status": job.get_status(refresh=False),
        "runid": runid,
        "config": config,
        "source_host": source_host,
        "enqueued_at": _as_iso(getattr(job, "enqueued_at", None)),
        "started_at": _as_iso(getattr(job, "started_at", None)),
        "ended_at": _as_iso(getattr(job, "ended_at", None)),
    }


def _resolve_job(redis_conn: redis.Redis, job_id: str, status_label: str) -> Dict[str, Any] | None:
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return {"id": job_id, "status": "missing"}

    if not _job_is_run_sync(job):
        return None

    return _serialize_job(job, status_label)


def _collect_run_sync_jobs(redis_conn: redis.Redis) -> List[Dict[str, Any]]:
    queue = Queue(connection=redis_conn)
    registries = [
        ("queued", queue.get_job_ids()),
        ("started", StartedJobRegistry(queue=queue).get_job_ids()),
        ("failed", FailedJobRegistry(queue=queue).get_job_ids()),
        ("finished", FinishedJobRegistry(queue=queue).get_job_ids()),
        ("deferred", DeferredJobRegistry(queue=queue).get_job_ids()),
    ]

    jobs: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for status_label, job_ids in registries:
        for job_id in job_ids[:50]:
            if job_id in seen:
                continue
            seen.add(job_id)
            job_payload = _resolve_job(redis_conn, job_id, status_label)
            if job_payload is None:
                continue
            jobs.append(job_payload)
    return jobs


def _serialize_migration(record: RunMigration) -> Dict[str, Any]:
    return {
        "id": record.id,
        "runid": record.runid,
        "config": record.config,
        "local_path": record.local_path,
        "source_host": record.source_host,
        "original_url": record.original_url,
        "pulled_at": _as_iso(record.pulled_at),
        "owner_email": record.owner_email,
        "version_at_pull": record.version_at_pull,
        "last_status": record.last_status,
        "archive_before": record.archive_before,
        "archive_after": record.archive_after,
        "is_fixture": record.is_fixture,
        "created_at": _as_iso(record.created_at),
        "updated_at": _as_iso(record.updated_at),
    }


@run_sync_dashboard_bp.route('/rq/run-sync', strict_slashes=False)
@login_required
@roles_required('Admin')
def run_sync_dashboard():
    return render_template(
        'rq-run-sync-dashboard.htm',
        default_target_root=DEFAULT_TARGET_ROOT,
        status_channel_suffix=STATUS_CHANNEL_SUFFIX,
    )


@run_sync_dashboard_bp.route('/rq/api/run-sync', methods=['POST'])
@login_required
@roles_required('Admin')
def api_run_sync():
    try:
        payload = parse_request_payload(request, boolean_fields={'allow_push', 'overwrite'})
    except Exception:
        return exception_factory('Invalid payload')

    runid = payload.get('runid')
    config = payload.get('config')
    if not runid or not config:
        return error_factory('runid and config are required')

    source_host = payload.get('source_host') or 'wepp.cloud'
    target_root = payload.get('target_root') or DEFAULT_TARGET_ROOT
    owner_email = payload.get('owner_email') or None
    auth_token = payload.get('auth_token') or None
    allow_push = bool(payload.get('allow_push', False))
    overwrite = bool(payload.get('overwrite', False))
    expected_size_raw = payload.get('expected_size')
    expected_sha256 = payload.get('expected_sha256') or None

    expected_size = None
    if expected_size_raw not in (None, ''):
        try:
            expected_size = int(expected_size_raw)
        except (TypeError, ValueError):
            return error_factory('expected_size must be an integer when provided')

    normalized_host = source_host
    if '://' in normalized_host:
        normalized_host = normalized_host.split('://', 1)[1]
    normalized_host = normalized_host.strip('/')
    if normalized_host in {'wc.bearhive.duckdns.org', 'forest.local'} and not allow_push:
        return error_factory('allow_push must be true when syncing from wc.bearhive.duckdns.org or forest.local')
    if allow_push and normalized_host in {'wc.bearhive.duckdns.org', 'forest.local'} and not auth_token:
        return error_factory('auth_token is required when allow_push is enabled for this host')

    try:
        with _redis_conn() as redis_conn:
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(
                run_sync_rq,
                (
                    runid,
                    config,
                    source_host,
                    owner_email,
                    target_root,
                    auth_token,
                    allow_push,
                    overwrite,
                    expected_size,
                    expected_sha256,
                ),
                timeout=RUN_SYNC_TIMEOUT,
            )
    except Exception:
        return exception_factory('Failed to enqueue run sync job', runid=runid)

    StatusMessenger.publish(
        f"{runid}:{STATUS_CHANNEL_SUFFIX}",
        f"rq:{job.id} ENQUEUED run_sync_rq({runid}, {config})",
    )

    return jsonify({'Success': True, 'job_id': job.id})


@run_sync_dashboard_bp.route('/rq/api/run-sync/status', methods=['GET'])
@login_required
@roles_required('Admin')
def run_sync_status():
    try:
        with _redis_conn() as redis_conn:
            jobs = _collect_run_sync_jobs(redis_conn)

        # Import inside the handler to avoid circular imports during app bootstrap.
        from wepppy.weppcloud.app import RunMigration

        records = RunMigration.query.order_by(RunMigration.updated_at.desc()).limit(50).all()
        migrations = [_serialize_migration(record) for record in records]
        return jsonify({'jobs': jobs, 'migrations': migrations})
    except Exception:
        return exception_factory('Failed to load run sync status')
