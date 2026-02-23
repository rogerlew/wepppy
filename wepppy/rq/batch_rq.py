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
from typing import Any, Tuple, List, Optional

import redis
from rq import Queue, get_current_job
from rq.job import Job
from rq.registry import DeferredJobRegistry, ScheduledJobRegistry, StartedJobRegistry
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.nodb.base import (
    NoDbAlreadyLockedError,
    NoDbBase,
    clear_locks,
    clear_nodb_file_cache,
)
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.omni_rq import run_omni_scenarios_rq
from wepppy.topo.watershed_collection import WatershedFeature
try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except ImportError:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200
logger = logging.getLogger(__name__)


_TERMINAL_JOB_STATUSES = {
    "finished",
    "failed",
    "stopped",
    "canceled",
    "not_found",
}


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


def _collect_batch_runids(batch_wd: Path, batch_name: str) -> list[str]:
    runids = [f'batch;;{batch_name};;_base']
    runs_dir = batch_wd / 'runs'
    if runs_dir.exists():
        for child in runs_dir.iterdir():
            if child.is_dir():
                runids.append(f'batch;;{batch_name};;{child.name}')
    return runids


def _cleanup_batch_run_cache_and_locks(runid: str) -> None:
    try:
        clear_nodb_file_cache(runid)
    except FileNotFoundError:
        # The run directory may not exist for every possible leaf run ID.
        pass
    except Exception as exc:
        logger.warning("batch_rq: failed to clear NoDb cache for %s - %s", runid, exc)

    try:
        clear_locks(runid)
    except Exception as exc:
        logger.warning("batch_rq: failed to clear locks for %s - %s", runid, exc)


def _job_targets_batch(job: Job, batch_name: str) -> bool:
    meta = job.meta if isinstance(job.meta, dict) else {}
    raw_runid = meta.get("runid")
    runid = str(raw_runid).strip() if raw_runid is not None else ""
    if runid == batch_name:
        return True
    if runid.startswith(f"batch;;{batch_name};;"):
        return True

    args = list(job.args or [])
    if args:
        first_arg = args[0]
        if isinstance(first_arg, str) and first_arg == batch_name:
            return True

    return False


def _active_batch_job_summaries(
    batch_name: str,
    *,
    redis_conn: redis.Redis | None = None,
    exclude_job_ids: set[str] | None = None,
    max_jobs: int = 25,
) -> list[str]:
    """Return active job summaries for a batch (queued/started/deferred/scheduled)."""
    if max_jobs <= 0:
        return []

    excluded = set(exclude_job_ids or set())

    def _collect(connection: redis.Redis) -> list[str]:
        queue = Queue("batch", connection=connection)
        registries = [
            ("queued", queue.get_job_ids()),
            ("started", StartedJobRegistry(queue=queue).get_job_ids()),
            ("deferred", DeferredJobRegistry(queue=queue).get_job_ids()),
            ("scheduled", ScheduledJobRegistry(queue=queue).get_job_ids()),
        ]

        seen: set[str] = set()
        summaries: list[str] = []
        for registry_label, job_ids in registries:
            for raw_job_id in job_ids:
                job_id = str(raw_job_id)
                if not job_id or job_id in seen or job_id in excluded:
                    continue
                seen.add(job_id)

                try:
                    job = Job.fetch(job_id, connection=connection)
                except Exception:
                    # Boundary catch: preserve contract behavior while logging unexpected failures.
                    __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/batch_rq.py:184", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                    continue
                if job is None:
                    continue
                if not _job_targets_batch(job, batch_name):
                    continue

                status = str(job.get_status(refresh=False) or registry_label).lower()
                if status in _TERMINAL_JOB_STATUSES:
                    continue

                func_name = str(getattr(job, "func_name", "") or "")
                if func_name:
                    func_name = func_name.rsplit(".", 1)[-1]
                else:
                    func_name = str(getattr(job, "description", "job") or "job")

                summaries.append(f"{job.id}:{status}:{func_name}")
                if len(summaries) >= max_jobs:
                    return summaries

        return summaries

    if redis_conn is not None:
        return _collect(redis_conn)

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as connection:
        return _collect(connection)


def delete_batch_rq(batch_name: str) -> dict[str, Any]:
    """Delete an entire batch workspace (base + generated runs)."""
    job = get_current_job()
    job_id = job.id if job is not None else 'N/A'
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{batch_name}:batch'

    try:
        StatusMessenger.publish(status_channel, f'rq:{job_id} STARTED {func_name}({batch_name})')
        if job is not None:
            job.meta['runid'] = batch_name
            job.save()

        try:
            batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        except FileNotFoundError:
            StatusMessenger.publish(
                status_channel,
                f'rq:{job_id} COMPLETED {func_name}({batch_name}) already-missing',
            )
            StatusMessenger.publish(status_channel, f'rq:{job_id} TRIGGER batch BATCH_DELETE_COMPLETED')
            return {'batch_name': batch_name, 'deleted': False, 'already_missing': True}

        batch_wd = Path(batch_runner.wd).resolve()
        runids = _collect_batch_runids(batch_wd, batch_name)

        for runid in runids:
            _cleanup_batch_run_cache_and_locks(runid)

        wd_targets: list[str] = [str(batch_wd)]
        base_wd = batch_wd / '_base'
        if base_wd.exists():
            wd_targets.append(str(base_wd))
        runs_dir = batch_wd / 'runs'
        if runs_dir.exists():
            wd_targets.extend(str(path) for path in runs_dir.iterdir() if path.is_dir())

        try:
            BatchRunner.cleanup_run_instances(str(batch_wd))
        except Exception as exc:
            logger.warning("batch_rq: failed to cleanup BatchRunner instance for %s - %s", batch_wd, exc)

        for wd in wd_targets:
            try:
                NoDbBase.cleanup_run_instances(wd)
            except Exception as exc:
                logger.warning("batch_rq: failed to cleanup NoDb instances for %s - %s", wd, exc)

        active_jobs = _active_batch_job_summaries(batch_name, exclude_job_ids={job_id})
        if active_jobs:
            active_jobs_text = ", ".join(active_jobs[:5])
            if len(active_jobs) > 5:
                active_jobs_text += f" (+{len(active_jobs) - 5} more)"
            raise RuntimeError(
                "Batch cannot be deleted while jobs are active. "
                f"Active jobs: {active_jobs_text}"
            )

        if batch_wd.exists():
            shutil.rmtree(batch_wd)

        StatusMessenger.publish(status_channel, f'rq:{job_id} COMPLETED {func_name}({batch_name})')
        StatusMessenger.publish(status_channel, f'rq:{job_id} TRIGGER batch BATCH_DELETE_COMPLETED')
        return {'batch_name': batch_name, 'deleted': True}

    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/batch_rq.py:280", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job_id} EXCEPTION {func_name}({batch_name})')
        StatusMessenger.publish(status_channel, f'rq:{job_id} STATUS delete batch failed ({exc})')
        StatusMessenger.publish(status_channel, f'rq:{job_id} TRIGGER batch BATCH_DELETE_FAILED')
        raise

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
            try:
                batch_runner.set_rq_job_id("final_batch_complete_rq", final_job.id)
            except Exception as exc:
                logger.warning("batch_rq: failed to persist final_batch_complete_rq job id - %s", exc)
            if job is not None:
                job.meta['jobs:1,func:_final_batch_complete_rq'] = final_job.id
                job.save()

        StatusMessenger.publish(status_channel, f'rq:{job_id} COMPLETED {func_name}({batch_name})')
        return final_job

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/batch_rq.py:364", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
            omni_final_job = run_omni_scenarios_rq(runid)
            if job is not None and omni_final_job is not None:
                job.meta['omni_final_job_id'] = omni_final_job.id
                job.save()
            if omni_final_job is not None:
                final_job_id = batch_runner.rq_job_ids.get("final_batch_complete_rq")
                if not final_job_id:
                    logger.warning(
                        "batch_rq: missing final_batch_complete_rq id for %s; Omni job %s not linked",
                        batch_name,
                        omni_final_job.id,
                    )
                else:
                    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
                    with redis.Redis(**conn_kwargs) as redis_conn:
                        try:
                            final_job = Job.fetch(final_job_id, connection=redis_conn)
                        except Exception as exc:
                            logger.warning(
                                "batch_rq: failed to fetch final_batch_complete_rq %s for %s - %s",
                                final_job_id,
                                batch_name,
                                exc,
                            )
                        else:
                            dependency_ids = list(final_job._dependency_ids or [])
                            if omni_final_job.id not in dependency_ids:
                                dependency_ids.append(omni_final_job.id)
                                final_job._dependency_ids = dependency_ids
                                final_job.save()
                                final_job.register_dependency()

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
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/batch_rq.py:504", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({batch_name})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch BATCH_RUN_COMPLETED')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch END_BROADCAST')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni END_BROADCAST')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/batch_rq.py:512", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({batch_name})')
        raise
