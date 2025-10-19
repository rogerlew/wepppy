from __future__ import annotations

from typing import Dict

import redis
from rq.job import Job

REDIS_HOST: str
RQ_DB: int

def _cancel_job_recursive(job: Job, redis_conn: redis.Redis) -> None: ...

def cancel_jobs(job_id: str) -> Dict[str, str]: ...
