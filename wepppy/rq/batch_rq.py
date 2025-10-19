from __future__ import annotations

"""
RQ tasks that orchestrate batch WEPP runs across a watershed collection.

The helpers enqueue per-watershed jobs, monitor their progress, and emit
summary events when an entire batch completes so the UI can react in real time.
"""

import inspect
import socket
import time
from typing import Tuple, List

import redis
from rq import Queue, get_current_job
from rq.job import Job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.topo.watershed_collection import WatershedFeature
try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except Exception:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200

def run_batch_rq(batch_name: str) -> Job:
    """Enqueue a batch run for each watershed feature and a finalizer task.

    Args:
        batch_name: Identifier of the batch runner workspace.

    Returns:
        The final RQ job that marks the batch as complete.

    Raises:
        Exception: Any failure encountered while preparing or enqueuing tasks.
    """
    try:
        job = get_current_job()
        job_id = job.id if job is not None else 'N/A'
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{batch_name}:batch'

        if job is not None:
            job.meta['runid'] = batch_name
            job.save()

        StatusMessenger.publish(status_channel, f'rq:{job_id} STARTED {func_name}({batch_name})')

        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        watershed_collection = batch_runner.get_watershed_collection()
        if not watershed_collection.runid_template:
            raise ValueError('Batch run requires a validated run ID template.')

        if not watershed_collection.runid_template_is_valid:
            raise ValueError('Run ID template validation is not in an OK state.')

        watershed_features = list(watershed_collection)
        if not watershed_features:
            raise ValueError('No watershed features available to enqueue.')
        watershed_jobs: List[Job] = []
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)

            for wf in watershed_features:
                runid = wf.runid
                child_job = q.enqueue_call(
                    func=run_batch_watershed_rq,
                    args=[batch_name, wf],
                    timeout=TIMEOUT,
                )
                child_job.meta['runid'] = runid
                child_job.save()
                if job is not None:
                    job.meta[f'jobs:0,runid:{runid}'] = child_job.id
                    job.save()
                watershed_jobs.append(child_job)

            final_job = q.enqueue_call(
                func=_final_batch_complete_rq,
                args=[batch_name],
                timeout=TIMEOUT,
                depends_on=watershed_jobs if watershed_jobs else None,
            )
            final_job.meta['runid'] = batch_name
            final_job.save()
            if job is not None:
                job.meta['jobs:1,func:_final_batch_complete_rq'] = final_job.id
                job.save()

        StatusMessenger.publish(status_channel, f'rq:{job_id} COMPLETED {func_name}({batch_name})')
        return final_job

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job_id} EXCEPTION {func_name}({batch_name})')
        raise


def run_batch_watershed_rq(
    batch_name: str,
    watershed_feature: WatershedFeature,
) -> Tuple[bool, float]:
    """Execute the batch workflow for a single watershed feature.

    Args:
        batch_name: Identifier of the batch runner workspace.
        watershed_feature: Feature metadata describing the watershed run.

    Returns:
        Tuple containing the success flag and the runtime in seconds.

    Raises:
        Exception: Propagates errors surfaced by the batch runner.
    """
    try:
        job = get_current_job()
        _runid = watershed_feature.runid
        runid = f'batch;;{batch_name};;{_runid}'
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{batch_name}:batch'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        start_ts = time.time()

        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        locks_cleared = batch_runner.run_batch_project(watershed_feature, job_id=job.id)
        if locks_cleared:
            StatusMessenger.publish(
                status_channel,
                f'rq:{job.id} INFO cleared stale locks {list(locks_cleared)}',
            )

        elapsed = time.time() - start_ts
        status = True
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} COMPLETED {func_name}({runid}) -> ({status}, {elapsed:.3f})',
        )

        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch BATCH_WATERSHED_TASK_COMPLETED')
        return status, elapsed

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def _final_batch_complete_rq(batch_name: str) -> None:
    """Emit completion notifications once all batch jobs finish."""
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{batch_name}:batch'

    try:
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({batch_name})')

        BatchRunner.getInstanceFromBatchName(batch_name)

        if send_discord_message is not None:
            try:
                send_discord_message(f':herb: Batch {batch_name} completed on {_hostname}')
            except Exception:
                pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({batch_name})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch BATCH_RUN_COMPLETED')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch END_BROADCAST')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni END_BROADCAST')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({batch_name})')
        raise
