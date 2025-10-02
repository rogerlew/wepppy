import inspect
import os
import socket
import time
from copy import deepcopy
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import redis
from rq import Queue, get_current_job

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

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

TIMEOUT = 43_200

def run_batch_rq(batch_name: str):
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

        template_state = batch_runner.runid_template_state or {}
        template = template_state.get('template')
        summary = template_state.get('summary') or {}

        if not template:
            raise ValueError('Batch run requires a validated run ID template.')

        if template_state.get('status') != 'ok' or not summary.get('is_valid', False):
            raise ValueError('Run ID template validation is not in an OK state.')

        resource_checksum = template_state.get('resource_checksum')
        if resource_checksum and resource_checksum != watershed_collection.checksum:
            raise ValueError('Watershed GeoJSON has changed since template validation; re-validate before running.')

        watershed_collection.runid_template = template
        watershed_features = list(watershed_collection)
        if not watershed_features:
            raise ValueError('No watershed features available to enqueue.')

        watershed_jobs = []
        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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
):
    try:
        from wepppy.nodb.ron import Ron
        from wepppy.nodb.watershed import Watershed
        from wepppy.nodb.landuse import Landuse
        from wepppy.nodb.soils import Soils
        from wepppy.nodb.mods.rap.rap_ts import RAP_TS
        from wepppy.nodb.wepp import Wepp

        job = get_current_job()
        _runid = watershed_feature.runid
        runid = f'batch;;{batch_name};;{_runid}'
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{batch_name}:batch'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        start_ts = time.time()

        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        locks_cleared = batch_runner.run_batch_project(watershed_feature)
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

def _final_batch_complete_rq(batch_name: str):
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
