from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, MutableMapping, Sequence, Tuple

import redis
from rq.job import Job

REDIS_HOST: str
RQ_DB: int

def recursive_get_job_details(job: Job, redis_conn: redis.Redis, now: datetime) -> Dict[str, Any]: ...

def get_wepppy_rq_job_info(job_id: str) -> Dict[str, Any]: ...

def get_wepppy_rq_jobs_info(job_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]: ...

def _flatten_job_tree(job_info: MutableMapping[str, Any]) -> Tuple[list[Any], list[Any]]: ...

def get_wepppy_rq_job_status(job_id: str) -> Dict[str, Any]: ...
