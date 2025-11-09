from __future__ import annotations

"""Helpers for introspecting RQ job trees and reporting aggregated status."""

from datetime import datetime
from typing import Any, Dict, List, MutableMapping, Sequence, Tuple

import redis
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.utils import utcnow

from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)


def recursive_get_job_details(job: Job, redis_conn: redis.Redis, now: datetime) -> Dict[str, Any]:
    """Recursively fetch job details including any children jobs."""
    elapsed_s = None
    if job.started_at:
        if job.ended_at:
            elapsed_s = (job.ended_at - job.started_at).total_seconds()
        else:
            elapsed_s = (now - job.started_at).total_seconds()

    job_info: Dict[str, Any] = {
        "id": job.id,
        "runid": job.meta.get('runid'),
        "status": job.get_status(),
        "result": job.result,
        "started_at": str(job.started_at) if job.started_at else None,
        "ended_at": str(job.ended_at) if job.ended_at else None,
        "description": job.description,
        "elapsed_s": elapsed_s,
        "exc_info": job.meta.get('exc_string'),
        "children": {}
    }

    for key, child_job_id in job.meta.items():
        if key.startswith('jobs:'):
            job_order = key.split(',')[0].split(':')[1]
            try:
                child_job = Job.fetch(child_job_id, connection=redis_conn)
                child_job_info = recursive_get_job_details(child_job, redis_conn, now) if child_job else None
            except NoSuchJobError:
                child_job_info = None
            job_info.setdefault("children", {}).setdefault(job_order, []).append(child_job_info)

    return job_info

def get_wepppy_rq_job_info(job_id: str) -> Dict[str, Any]:
    """Return the recursive job tree for a single job id."""
    now = utcnow()
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            return {"id": job_id, "status": "not_found"}

        if not job:
            return {"id": job_id, "status": "not_found"}

        return recursive_get_job_details(job, redis_conn, now)


def get_wepppy_rq_jobs_info(job_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch job information for multiple job ids using a single Redis session."""

    if not job_ids:
        return {}

    normalized_ids: list[str] = []
    seen_ids: set[str] = set()
    for raw in job_ids:
        if raw is None:
            continue
        job_id = str(raw).strip()
        if not job_id or job_id in seen_ids:
            continue
        seen_ids.add(job_id)
        normalized_ids.append(job_id)

    if not normalized_ids:
        return {}

    now = utcnow()
    results: Dict[str, Dict[str, Any]] = {}

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        for job_id in normalized_ids:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
            except NoSuchJobError:
                results[job_id] = {"id": job_id, "status": "not_found"}
                continue
            except Exception as exc:  # pragma: no cover - defensive guard
                results[job_id] = {
                    "id": job_id,
                    "status": "error",
                    "error": str(exc),
                }
                continue

            if not job:
                results[job_id] = {"id": job_id, "status": "not_found"}
                continue

            try:
                results[job_id] = recursive_get_job_details(job, redis_conn, now)
            except Exception as exc:  # pragma: no cover - defensive guard
                results[job_id] = {
                    "id": job_id,
                    "status": "error",
                    "error": str(exc),
                }

    return results


def _flatten_job_tree(job_info: MutableMapping[str, Any]) -> Tuple[List[Any], List[Any]]:
    """Recursively traverse the job tree, collecting statuses and end times."""
    statuses: List[Any] = [job_info['status']]
    end_times: List[Any] = [job_info['ended_at']]

    # Recursively process children
    for order_key in job_info.get('children', {}):
        for child_job in job_info['children'][order_key]:
            if child_job:  # Child job could be None if not found
                child_statuses, child_end_times = _flatten_job_tree(child_job)
                statuses.extend(child_statuses)
                end_times.extend(child_end_times)

    return statuses, end_times


def get_wepppy_rq_job_status(job_id: str) -> Dict[str, Any]:
    """Return an aggregated status summary for a job tree rooted at ``job_id``."""
    now = utcnow()
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            return {"id": job_id, "status": "not_found"}

        if not job:
            return {"id": job_id, "status": "not_found"}

        all_jobs_tree = recursive_get_job_details(job, redis_conn, now)

        # Walk the job tree to collect all statuses and end times
        statuses, end_times = _flatten_job_tree(all_jobs_tree)

        # Determine the aggregated status based on priority.
        # If any job failed, the whole thing failed. If any is started, it's started.
        status_priority = ['failed', 'stopped', 'canceled', 'started', 'queued', 'deferred', 'scheduled']
        aggregated_status = 'finished'  # Default to finished
        for status in status_priority:
            if status in statuses:
                aggregated_status = status
                break

        if aggregated_status == 'finished':
            assert all(s == 'finished' for s in statuses), f"Inconsistent statuses for finished aggregation: {statuses}"

        # Find the latest 'ended_at' timestamp, but only if all jobs have completed.
        total_jobs_count = len(statuses)
        valid_end_times = [t for t in end_times if t]

        if len(valid_end_times) == total_jobs_count:
            last_ended_at = max(valid_end_times)
        else:
            last_ended_at = None

        return {
            "id": job.id,
            "runid": job.meta.get("runid"),
            "status": aggregated_status,
            "started_at": str(job.started_at) if job.started_at else None,
            "ended_at": last_ended_at,
        }
