"""Resolve the job displayed by the run page's Climate panel."""

from collections.abc import Mapping
from datetime import datetime, timezone
import logging

import redis
from rq.exceptions import DeserializationError, NoSuchJobError
from rq.job import Job, JobStatus

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs


def resolve_climate_attempt(runid: str, tracked: Mapping[str, str]) -> tuple[str | None, bool]:
    """Return the selected job ID and whether the job details are unavailable."""
    keys = ('build_climate_rq', 'upload_cli_rq')
    candidates = [(key, tracked[key]) for key in keys if tracked.get(key)]
    if not candidates:
        return None, False

    job_ids = [job_id for _, job_id in candidates]
    if len(set(job_ids)) != len(job_ids):
        return None, True

    try:
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ, decode_responses=False)) as connection:
            with connection.pipeline(transaction=False) as pipe:
                for job_id in job_ids:
                    pipe.hgetall(Job.key_for(job_id))
                records = pipe.execute()
        timestamps = []
        for (key, job_id), record in zip(candidates, records, strict=True):
            if not record:
                return None, True
            if len(candidates) == 2 and not record.get(b'created_at'):
                # RQ fills absent stored timestamps with the current time.
                return None, True
            job = Job(job_id, connection=connection)
            job.restore(record)
            if job.get_status(refresh=False) == JobStatus.CREATED or job.func_name != f'wepppy.rq.project_rq.{key}':
                return None, True
            if not isinstance(job.args, (tuple, list)) or not job.args or str(job.args[0]) != runid:
                return None, True
            if not isinstance(job.meta, dict) or 'unserialized' in job.meta or job.meta.get('runid') not in (None, '', runid):
                return None, True
            if len(candidates) == 1:
                return job_id, False
            created = job.created_at
            if not isinstance(created, datetime):
                return None, True
            timestamps.append(created if created.tzinfo else created.replace(tzinfo=timezone.utc))
    except redis.RedisError:
        logging.getLogger(__name__).warning('Could not read Climate job records for %s', runid, exc_info=True)
        return None, True
    except (DeserializationError, NoSuchJobError, KeyError, TypeError, ValueError):
        return None, True

    if timestamps[0] == timestamps[1]:
        return None, True
    latest_job_id = job_ids[1] if timestamps[1] > timestamps[0] else job_ids[0]
    return latest_job_id, False
