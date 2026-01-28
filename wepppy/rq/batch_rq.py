from __future__ import annotations

"""
RQ tasks that orchestrate batch WEPP runs across a watershed collection.

The helpers enqueue per-watershed jobs, monitor their progress, and emit
summary events when an entire batch completes so the UI can react in real time.
"""

import inspect
import json
import logging
import os
import shutil
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, List, Optional

import redis
from rq import Queue, get_current_job
from rq.job import Job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.nodb.base import NoDbAlreadyLockedError, clear_nodb_file_cache
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.omni_rq import run_omni_scenarios_rq
from wepppy.topo.watershed_collection import WatershedFeature
try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except Exception:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200
logger = logging.getLogger(__name__)

def _write_run_metadata(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def _reset_omni_nodb_from_base(base_wd: Path, runid_wd: Path, runid: str) -> None:
    base_omni = base_wd / "omni.nodb"
    if not base_omni.exists():
        logger.info("batch_rq: omni.nodb missing in base_wd=%s; skipping reset", base_wd)
        return

    with base_omni.open("r", encoding="utf-8") as fp:
        state = json.load(fp)

    if "py/state" in state:
        state["py/state"]["wd"] = str(runid_wd)
    else:
        state["wd"] = str(runid_wd)

    runid_wd.mkdir(parents=True, exist_ok=True)
    target = runid_wd / "omni.nodb"
    with target.open("w", encoding="utf-8") as fp:
        json.dump(state, fp)
        fp.flush()
        os.fsync(fp.fileno())

    try:
        clear_nodb_file_cache(runid)
    except Exception as exc:
        logger.warning("batch_rq: failed to clear NoDb cache for %s - %s", runid, exc)

    base_omni_dir = base_wd / "_pups" / "omni"
    if not base_omni_dir.exists():
        logger.info("batch_rq: omni dir missing in base_wd=%s; skipping sync", base_omni_dir)
        return

    target_omni_dir = runid_wd / "_pups" / "omni"
    if target_omni_dir.exists():
        shutil.rmtree(target_omni_dir)
    shutil.copytree(base_omni_dir, target_omni_dir)

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
        if job is not None:
            try:
                batch_runner.set_rq_job_id("run_batch_rq", job.id)
            except Exception as exc:
                logger.warning("batch_rq: failed to persist run_batch_rq job id - %s", exc)
        watershed_collection = batch_runner.get_watershed_collection()
        if not watershed_collection.runid_template:
            raise ValueError('Batch run requires a validated run ID template.')

        if not watershed_collection.runid_template_is_valid:
            raise ValueError('Run ID template validation is not in an OK state.')

        watershed_features = batch_runner.get_watershed_features_lpt()
        if not watershed_features:
            raise ValueError('No watershed features available to enqueue.')
        watershed_jobs: List[Job] = []
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)

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
    """
    job = get_current_job()
    job_id = job.id if job is not None else "N/A"
    _runid = watershed_feature.runid
    runid = f'batch;;{batch_name};;{_runid}'
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{batch_name}:batch'
    start_ts = time.time()
    started_at = datetime.now(timezone.utc)

    try:
        StatusMessenger.publish(status_channel, f'rq:{job_id} STARTED {func_name}({runid})')

        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        locks_cleared = batch_runner.run_batch_project(watershed_feature, job_id=job_id)
        if locks_cleared:
            StatusMessenger.publish(
                status_channel,
                f'rq:{job_id} INFO cleared stale locks {list(locks_cleared)}',
            )

        runid_wd = Path(get_wd(runid))
        prep: Optional[RedisPrep] = None
        try:
            prep = RedisPrep.getInstance(str(runid_wd))
        except FileNotFoundError:
            prep = None

        if batch_runner.is_task_enabled(TaskEnum.run_omni_scenarios) and (
            prep is None or prep[str(TaskEnum.run_omni_scenarios)] is None
        ):
            _reset_omni_nodb_from_base(Path(batch_runner.base_wd), runid_wd, runid)
            run_omni_scenarios_rq(runid)

        elapsed = time.time() - start_ts
        status = True
        StatusMessenger.publish(
            status_channel,
            f'rq:{job_id} COMPLETED {func_name}({runid}) -> ({status}, {elapsed:.3f})',
        )

        StatusMessenger.publish(status_channel, f'rq:{job_id} TRIGGER batch BATCH_WATERSHED_TASK_COMPLETED')
        return status, elapsed

    except Exception as exc:
        elapsed = time.time() - start_ts
        error_payload = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

        try:
            run_wd = Path(get_wd(runid))
            run_wd.mkdir(parents=True, exist_ok=True)
            completed_at = datetime.now(timezone.utc)
            run_metadata = {
                "runid": runid,
                "batch_name": batch_name,
                "status": "failed",
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_seconds": elapsed,
                "error": error_payload,
            }
            _write_run_metadata(run_wd / "run_metadata.json", run_metadata)
        except Exception as meta_exc:
            logger.warning("batch_rq: failed to write run metadata for %s - %s", runid, meta_exc)

        StatusMessenger.publish(status_channel, f'rq:{job_id} EXCEPTION {func_name}({runid})')
        try:
            StatusMessenger.publish(
                status_channel,
                f'rq:{job_id} EXCEPTION_JSON {json.dumps(error_payload)}',
            )
        except Exception as publish_exc:
            logger.warning("batch_rq: failed to publish EXCEPTION_JSON for %s - %s", runid, publish_exc)
        StatusMessenger.publish(status_channel, f'rq:{job_id} TRIGGER batch BATCH_WATERSHED_TASK_COMPLETED')
        return False, elapsed

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
