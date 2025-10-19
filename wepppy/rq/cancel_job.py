from __future__ import annotations

"""Utilities for canceling RQ jobs (and their dependency tree) from workers or CLIs."""

import json
from typing import Dict

import redis
from dotenv import load_dotenv
from rq.command import send_stop_job_command
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

load_dotenv()

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)


def _cancel_job_recursive(job: Job, redis_conn: redis.Redis) -> None:
    """Cancel a job and its children, stopping running jobs when necessary."""

    try:
        if job.get_status() == "started":
            send_stop_job_command(redis_conn, job.id)
        else:
            job.cancel()
    except (NoSuchJobError, InvalidJobOperation):
        return

    for key, child_job_id in job.meta.items():
        if not key.startswith("jobs:"):
            continue
        try:
            child_job = Job.fetch(child_job_id, connection=redis_conn)
        except NoSuchJobError:
            continue
        _cancel_job_recursive(child_job, redis_conn)


def cancel_jobs(job_id: str) -> Dict[str, str]:
    """Cancel a job tree rooted at ``job_id``.

    Args:
        job_id: Identifier of the job to cancel.

    Returns:
        Status dictionary reporting success or any lookup error.
    """

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            return {"error": "Job not found"}

        _cancel_job_recursive(job, redis_conn)
        return {"status": "ok"}
    
    
if __name__ == "__main__":
    import sys
    from pprint import pprint

    if not sys.argv[-1].endswith('.py'):
        job_id = str(sys.argv[-1])
        job_info = cancel_jobs(job_id)
        print(json.dumps(job_info, indent=2))
