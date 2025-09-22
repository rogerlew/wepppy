import os
from rq import Queue, Worker
from rq.job import Job
from rq.utils import get_version, utcnow
from rq.exceptions import NoSuchJobError
import redis
import json
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9


def recursive_get_job_details(job, redis_conn, now):
    """Recursively fetch job details including any children jobs."""
    elapsed_s = None
    if job.started_at:
        if job.ended_at:
            elapsed_s = (job.ended_at - job.started_at).total_seconds()
        else:
            elapsed_s = (now - job.started_at).total_seconds()

    job_info = {
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
            job_info["children"].setdefault(job_order, []).append(child_job_info)

    return job_info

def get_wepppy_rq_job_info(job_id: str) -> dict:
    now = utcnow()
    with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            return {"id": job_id, "status": "not_found"}

        if not job:
            return {"id": job_id, "status": "not_found"}

        return recursive_get_job_details(job, redis_conn, now)


def _flatten_job_tree(job_info: dict) -> tuple[list, list]:
    """
    Recursively traverses the job tree to collect all statuses and end times.
    """
    statuses = [job_info['status']]
    end_times = [job_info['ended_at']]

    # Recursively process children
    for order_key in job_info.get('children', {}):
        for child_job in job_info['children'][order_key]:
            if child_job:  # Child job could be None if not found
                child_statuses, child_end_times = _flatten_job_tree(child_job)
                statuses.extend(child_statuses)
                end_times.extend(child_end_times)

    return statuses, end_times


def get_wepppy_rq_job_status(job_id: str) -> dict:
    now = utcnow()
    with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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
