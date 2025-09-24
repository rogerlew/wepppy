import os
import rq
from rq import Queue, Worker
from rq.job import Job
from rq.utils import get_version
import redis
import json

from dotenv import load_dotenv
from datetime import datetime

from rq.command import send_stop_job_command
from rq.exceptions import NoSuchJobError, InvalidJobOperation

load_dotenv()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9


def cancel_job(job, redis_conn):
    """Recursively cancel jobs including any children jobs. Now handles stopping running jobs."""

    try:
        if job.get_status() == 'started':
            send_stop_job_command(redis_conn, job.id)  # Stop running job
        else:
            job.cancel()  # Cancel non-started job
    except (NoSuchJobError, InvalidJobOperation):
        pass  # Job doesn't exist, isn't stoppable, or already handled

    # Recurse into children
    for key, child_job_id in job.meta.items():
        if key.startswith('jobs:'):
            child_job = Job.fetch(child_job_id, connection=redis_conn)
            if child_job:
                cancel_job(child_job, redis_conn)


def cancel_jobs(job_id: str) -> dict:
    with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            return {"error": "Job not found"}

        cancel_job(job, redis_conn)
        return {"status": "ok"}
    
    
if __name__ == "__main__":
    import sys
    from pprint import pprint

    if not sys.argv[-1].endswith('.py'):
        job_id = str(sys.argv[-1])
        job_info = cancel_jobs(job_id)
        print(json.dumps(job_info, indent=2))