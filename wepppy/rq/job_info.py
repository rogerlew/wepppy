import os
from rq import Queue, Worker
from rq.job import Job
from rq.utils import get_version
import redis
import json

from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9


def get_job_details(job, redis_conn, now):
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
            child_job = Job.fetch(child_job_id, connection=redis_conn)
            child_job_info =None
            if child_job:
                child_job_info = get_job_details(child_job, redis_conn, now)
            job_info["children"].setdefault(job_order, []).append(child_job_info)

    return job_info


def get_run_wepp_rq_job_info(job_id: str) -> dict:
    now = datetime.now(timezone.utc)
    with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
        job = Job.fetch(job_id, connection=redis_conn)

        if not job:
            return {"error": "Job not found"}

        return get_job_details(job, redis_conn, now)

if __name__ == "__main__":
    import sys
    from pprint import pprint

    if not sys.argv[-1].endswith('.py'):
        job_id = str(sys.argv[-1])
        job_info = get_run_wepp_rq_job_info(job_id)
        print(json.dumps(job_info, indent=2))

