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
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Tuple, List, Optional

import redis
from rq import Queue, get_current_job
from rq.exceptions import NoSuchJobError
from rq.job import Dependency, Job, JobStatus
from rq.registry import DeferredJobRegistry, ScheduledJobRegistry, StartedJobRegistry
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.submission_recovery import rq_submission_lock

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.nodb.base import (
    NoDbAlreadyLockedError,
    NoDbStaleWriteError,
    NoDbBase,
    clear_locks,
    clear_nodb_file_cache,
)
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.job_dependencies import (
    reconcile_deferred_workflow,
    release_deferred_job_if_ready,
)
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


def _collect_run_task_status(run_wd: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        prep = RedisPrep.getInstance(str(run_wd))
    except FileNotFoundError:
        return {}, []
    except (OSError, TypeError, ValueError, redis.exceptions.RedisError) as exc:
        return {}, [f"task_status_unavailable: {type(exc).__name__}: {exc}"]

    task_status: dict[str, Any] = {}
    warnings: list[str] = []
    for task in BatchRunner.DEFAULT_TASKS:
        try:
            task_status[task.value] = prep[task]
        except (TypeError, ValueError, redis.exceptions.RedisError) as exc:
            task_status[task.value] = None
            task_status[f"{task.value}_error"] = f"{type(exc).__name__}: {exc}"
            warnings.append(f"{task.value}: {type(exc).__name__}: {exc}")
    return task_status, warnings


def _write_watershed_run_metadata(
    *,
    run_wd: Path,
    runid: str,
    batch_name: str,
    status: str,
    started_at: datetime,
    elapsed: float,
    job_id: str,
    error: dict[str, str] | None = None,
) -> None:
    completed_at = datetime.now(timezone.utc)
    task_status, metadata_warnings = _collect_run_task_status(run_wd)
    run_metadata: dict[str, Any] = {
        "runid": runid,
        "batch_name": batch_name,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": elapsed,
        "rq_job_id": job_id,
        "task_status": task_status,
    }
    if metadata_warnings:
        run_metadata["metadata_warnings"] = metadata_warnings
    if error is not None:
        run_metadata["error"] = error
    _write_run_metadata(run_wd / "run_metadata.json", run_metadata)

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
    allowed_funcs = {
        f"{__name__}.delete_batch_rq",
        f"{__name__}.run_batch_rq",
        f"{__name__}.run_batch_watershed_rq",
        f"{__name__}.run_batch_hillslopes_rq",
        f"{__name__}._final_batch_complete_rq",
        "wepppy.rq.omni_rq.run_omni_scenarios_rq",
        "wepppy.rq.omni_rq.run_omni_scenario_rq",
        "wepppy.rq.omni_rq._compile_hillslope_summaries_rq",
        "wepppy.rq.omni_rq._finalize_omni_scenarios_rq",
    }
    if str(job.func_name) not in allowed_funcs or str(job.origin) != "batch":
        return False
    meta = job.meta if isinstance(job.meta, dict) else {}
    raw_runid = meta.get("runid")
    runid = str(raw_runid).strip() if raw_runid is not None else ""
    args = list(job.args or [])
    if not args or not isinstance(args[0], str):
        return False
    arg_matches = args[0] == batch_name or args[0].startswith(
        f"batch;;{batch_name};;"
    )
    meta_matches = not runid or runid == batch_name or runid.startswith(
        f"batch;;{batch_name};;"
    )
    return arg_matches and meta_matches


def _job_plausibly_targets_batch(job: Job, batch_name: str) -> bool:
    meta = job.meta if isinstance(job.meta, dict) else {}
    raw_runid = meta.get("runid")
    runid = str(raw_runid).strip() if raw_runid is not None else ""
    args = list(job.args or [])
    arg_matches = bool(
        args
        and isinstance(args[0], str)
        and (
            args[0] == batch_name
            or args[0].startswith(f"batch;;{batch_name};;")
        )
    )
    meta_matches = runid == batch_name or runid.startswith(
        f"batch;;{batch_name};;"
    )
    return arg_matches or meta_matches


def _active_batch_job_summaries(
    batch_name: str,
    *,
    redis_conn: redis.Redis | None = None,
    exclude_job_ids: set[str] | None = None,
    max_jobs: int = 25,
) -> list[str]:
    """Return active job summaries for a batch (queued/started/scheduled)."""
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


def _format_active_jobs_text(active_jobs: list[str]) -> str:
    active_jobs_text = ", ".join(active_jobs[:5])
    if len(active_jobs) > 5:
        active_jobs_text += f" (+{len(active_jobs) - 5} more)"
    return active_jobs_text


def reconcile_deferred_batch_jobs(
    batch_name: str,
    *,
    redis_conn: redis.Redis,
    exclude_job_ids: set[str] | None = None,
    lease_checkpoint: Callable[[], None] | None = None,
    _watch_attempt: int = 0,
) -> list[str]:
    """Cancel deferred jobs for one batch and return executable conflicts."""
    excluded = set(exclude_job_ids or set())
    queue = Queue("batch", connection=redis_conn)
    started_registry = StartedJobRegistry(queue=queue)
    deferred_registry = DeferredJobRegistry(queue=queue)
    scheduled_registry = ScheduledJobRegistry(queue=queue)
    pipeline = redis_conn.pipeline()
    pipeline.watch(
        queue.key,
        queue.intermediate_queue_key,
        started_registry.key,
        deferred_registry.key,
        scheduled_registry.key,
    )
    registry_members = (
        queue.get_job_ids(),
        redis_conn.lrange(queue.intermediate_queue_key, 0, -1),
        started_registry.get_job_ids(),
        deferred_registry.get_job_ids(),
        scheduled_registry.get_job_ids(),
    )
    persisted_job_ids: set[str] = set()
    receipt_job_id = redis_conn.get(f"rq:batch:receipt:{batch_name}")
    if isinstance(receipt_job_id, bytes):
        receipt_job_id = receipt_job_id.decode("utf-8")
    if receipt_job_id:
        persisted_job_ids.add(str(receipt_job_id))
    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError:
        batch_runner = None
    if batch_runner is not None:
        receipt_map = batch_runner.rq_job_ids
        for task_name in (
            "run_batch_rq",
            "delete_batch_rq",
            "final_batch_complete_rq",
        ):
            persisted_job_id = receipt_map.get(task_name)
            if persisted_job_id:
                persisted_job_ids.add(str(persisted_job_id))
    discovered_job_ids = {
        raw_job_id.decode("utf-8") if isinstance(raw_job_id, bytes) else str(raw_job_id)
        for job_ids in registry_members
        for raw_job_id in job_ids
    } | persisted_job_ids
    if discovered_job_ids:
        pipeline.watch(*(Job.key_for(job_id) for job_id in discovered_job_ids))
    candidates: dict[str, Job] = {}
    for job_ids, persisted in (
        *((job_ids, False) for job_ids in registry_members),
        (persisted_job_ids, True),
    ):
        for raw_job_id in job_ids:
            if lease_checkpoint is not None:
                lease_checkpoint()
            job_id = (
                raw_job_id.decode("utf-8")
                if isinstance(raw_job_id, bytes)
                else str(raw_job_id)
            )
            if not job_id or job_id in excluded or job_id in candidates:
                continue
            try:
                job = Job.fetch(job_id, connection=redis_conn)
            except NoSuchJobError:
                continue
            if _job_targets_batch(job, batch_name):
                candidates[job_id] = job
            elif persisted or _job_plausibly_targets_batch(job, batch_name):
                return [f"{job_id}:mismatch"]

    active: list[str] = []
    for job in candidates.values():
        if lease_checkpoint is not None:
            lease_checkpoint()
        raw_status = job.get_status(refresh=False)
        status = str(getattr(raw_status, "value", raw_status)).lower()
        if status in {"queued", "started", "scheduled"}:
            active.append(f"{job.id}:{status}")
    pipeline.multi()
    pipeline.ping()
    try:
        pipeline.execute()
    except redis.WatchError:
        if _watch_attempt >= 4:
            return ["inventory:changed"]
        return reconcile_deferred_batch_jobs(
            batch_name,
            redis_conn=redis_conn,
            exclude_job_ids=excluded,
            lease_checkpoint=lease_checkpoint,
            _watch_attempt=_watch_attempt + 1,
        )
    finally:
        pipeline.reset()
    if active:
        return active

    for job in candidates.values():
        if lease_checkpoint is not None:
            lease_checkpoint()
        result = reconcile_deferred_workflow(
            str(job.id),
            connection=redis_conn,
            association=lambda candidate: _job_targets_batch(candidate, batch_name),
            root_association=lambda candidate: _job_targets_batch(
                candidate, batch_name
            ),
            lease_checkpoint=lease_checkpoint,
        )
        if result.state in {"active", "mismatch"}:
            return [f"{job.id}:{result.state}"]
    return []


def _release_deferred_finalizer_if_ready(queue: Queue, final_job: Job) -> None:
    """Release a failure-tolerant finalizer if all dependencies are already terminal."""
    release_deferred_job_if_ready(queue, final_job)


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

        active_jobs = _active_batch_job_summaries(batch_name, exclude_job_ids={job_id})
        if active_jobs:
            raise RuntimeError(
                "Batch cannot be deleted while jobs are active. "
                f"Active jobs: {_format_active_jobs_text(active_jobs)}"
            )

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

def run_batch_rq(batch_name: str) -> dict[str, Any]:
    """Enqueue a batch run for each watershed feature and a finalizer task.

    Args:
        batch_name: Identifier of the batch runner workspace.

    Returns:
        Serializable summary containing the finalizer job id and selection counts.

    Raises:
        Exception: Any failure encountered while preparing or enqueuing tasks.
    """
    try:
        job = get_current_job()
        job_id = job.id if job is not None else 'N/A'
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{batch_name}:batch'

        if job is not None:
            # Downstream identity validation must survive unbounded queue delay.
            job.result_ttl = -1
            job.meta['runid'] = batch_name
            job.save()

        StatusMessenger.publish(status_channel, f'rq:{job_id} STARTED {func_name}({batch_name})')

        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        active_jobs = _active_batch_job_summaries(batch_name, exclude_job_ids={job_id})
        if active_jobs:
            raise RuntimeError(
                "Batch cannot be run while jobs are active. "
                f"Active jobs: {_format_active_jobs_text(active_jobs)}"
            )

        if job is not None:
            try:
                batch_runner.set_rq_job_id_fresh("run_batch_rq", job.id)
            except (NoDbAlreadyLockedError, NoDbStaleWriteError, OSError, redis.exceptions.RedisError) as exc:
                logger.warning("batch_rq: failed to persist run_batch_rq job id - %s", exc)
        watershed_collection = batch_runner.get_watershed_collection()
        if not watershed_collection.runid_template:
            raise ValueError('Batch run requires a validated run ID template.')

        if not watershed_collection.runid_template_is_valid:
            raise ValueError('Run ID template validation is not in an OK state.')

        watershed_features = batch_runner.get_watershed_features_lpt()
        if not watershed_features:
            raise ValueError('No watershed features available to enqueue.')
        full_rerun = batch_runner.is_task_enabled(TaskEnum.if_exists_rmtree)
        if full_rerun:
            selected_features = list(watershed_features)
            selection_mode = "full_rerun"
            runstate_summary = {
                "total": len(watershed_features),
                "complete": 0,
                "failed": 0,
                "incomplete": 0,
                "missing": 0,
                "invalid": 0,
                "retry_eligible": len(watershed_features),
                "metadata_stale": 0,
                "metadata_error": 0,
                "prep_error": 0,
                "base_stale": 0,
                "base_sync_error": 0,
                "unclassified": len(watershed_features),
            }
        else:
            run_states = batch_runner.classify_batch_run_states(watershed_features)
            runstate_summary = batch_runner.summarize_batch_run_states(run_states)
            selected_features = [
                wf for wf in watershed_features
                if run_states.get(str(wf.runid), {}).get("retry_eligible")
            ]
            selection_mode = "retry_eligible"

        selection_summary = {
            **runstate_summary,
            "mode": selection_mode,
            "enqueued": len(selected_features),
            "skipped": len(watershed_features) - len(selected_features),
        }
        if job is not None:
            job.meta["batch_run_selection"] = selection_summary
            job.save()
        StatusMessenger.publish(
            status_channel,
            (
                f"rq:{job_id} STATUS run selection total={len(watershed_features)} "
                f"enqueued={selection_summary['enqueued']} "
                f"skipped={selection_summary['skipped']} mode={selection_mode}"
            ),
        )

        cleared_runtime_locks = batch_runner.clear_retry_runtime_locks(selected_features)
        if cleared_runtime_locks:
            if job is not None:
                job.meta["batch_runtime_locks_cleared"] = len(cleared_runtime_locks)
                job.save()
            StatusMessenger.publish(
                status_channel,
                f"rq:{job_id} INFO cleared stale runtime locks count={len(cleared_runtime_locks)}",
            )

        watershed_jobs: List[Job] = []
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)

            for wf in selected_features:
                runid = str(wf.runid)
                child_runid = f'batch;;{batch_name};;{runid}'
                child_job_id = new_rq_job_id()
                hillslope_job_id = new_rq_job_id()
                if job is not None:
                    job.meta[f'jobs:0,runid:{runid}'] = child_job_id
                    job.meta[f'jobs:0,hillslopes,runid:{runid}'] = hillslope_job_id
                    job.save()
                with rq_submission_lock(
                    redis_conn,
                    f"{child_runid}:batch-child",
                    lifecycle_key=child_runid,
                ) as lease:
                    lease.checkpoint()
                    q.enqueue_call(
                        func=run_batch_hillslopes_rq,
                        args=[batch_name, wf, child_job_id],
                        timeout=TIMEOUT,
                        job_id=hillslope_job_id,
                        result_ttl=-1,
                        depends_on=job_id,
                        meta={'runid': child_runid, 'batch_root_job_id': job_id,
                              'jobs:0,func:run_batch_watershed_rq': child_job_id},
                    )
                    child_job = q.enqueue_call(
                        func=run_batch_watershed_rq,
                        args=[batch_name, wf, hillslope_job_id],
                        timeout=TIMEOUT,
                        job_id=child_job_id,
                        meta={'runid': child_runid, 'batch_root_job_id': job_id},
                        depends_on=Dependency(jobs=[hillslope_job_id], allow_failure=True),
                    )
                watershed_jobs.append(child_job)

            # RQ otherwise leaves dependents deferred when any dependency fails.
            final_depends_on = (
                Dependency(
                    jobs=[watershed_job.id for watershed_job in watershed_jobs],
                    allow_failure=True,
                )
                if watershed_jobs
                else None
            )
            final_job = q.enqueue_call(
                func=_final_batch_complete_rq,
                args=[batch_name],
                timeout=TIMEOUT,
                depends_on=final_depends_on,
            )
            final_job.meta['runid'] = batch_name
            final_job.meta['batch_root_job_id'] = job_id
            final_job.save()
            if job is not None:
                job.meta['jobs:1,func:_final_batch_complete_rq'] = final_job.id
                job.save()
            _release_deferred_finalizer_if_ready(q, final_job)
            try:
                batch_runner.set_rq_job_id_fresh("final_batch_complete_rq", final_job.id)
            except (NoDbAlreadyLockedError, NoDbStaleWriteError, OSError, redis.exceptions.RedisError) as exc:
                logger.warning("batch_rq: failed to persist final_batch_complete_rq job id - %s", exc)

        StatusMessenger.publish(status_channel, f'rq:{job_id} COMPLETED {func_name}({batch_name})')
        return {
            "batch_name": batch_name,
            "final_job_id": final_job.id,
            "enqueued": len(watershed_jobs),
            "selection": selection_summary,
        }

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/batch_rq.py:364", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job_id} EXCEPTION {func_name}({batch_name})')
        raise


def _validate_batch_stage(job: Job, batch_name: str, leaf: str, stage: str) -> str:
    """Validate task identity before any run-tree access, including error writes."""
    for value in (batch_name, leaf):
        if (not isinstance(value, str) or not value or value in {".", ".."}
                or any(token in value for token in ("/", "\\", "\x00", ";;"))):
            raise ValueError("Invalid batch stage identity")
    runid = f"batch;;{batch_name};;{leaf}"
    if job is None or job.origin != "batch" or job.meta.get("runid") != runid:
        raise ValueError("Batch stage job identity mismatch")
    if (len(job.args) != 3 or job.args[0] != batch_name
            or getattr(job.args[1], "runid", None) != leaf):
        raise ValueError("Batch stage arguments mismatch")
    if job.func_name != f"wepppy.rq.batch_rq.run_batch_{stage}_rq":
        raise ValueError("Batch stage function mismatch")
    root = Job.fetch(job.meta["batch_root_job_id"], connection=job.connection)
    key = f"jobs:0,runid:{leaf}" if stage == "watershed" else f"jobs:0,hillslopes,runid:{leaf}"
    if (root.origin != "batch" or root.func_name != "wepppy.rq.batch_rq.run_batch_rq"
            or tuple(root.args) != (batch_name,) or root.meta.get(key) != job.id
            or root.get_status(refresh=True) != JobStatus.FINISHED):
        raise ValueError("Batch stage root lineage mismatch")
    return runid


def _batch_handoff_path(run_wd: Path, hillslope_job_id: str) -> Path:
    if (not isinstance(hillslope_job_id, str) or not hillslope_job_id
            or hillslope_job_id in {".", ".."}
            or any(token in hillslope_job_id for token in ("/", "\\", "\x00"))):
        raise ValueError("Invalid hillslope job ID")
    path = run_wd / "batch_handoff" / f"{hillslope_job_id}.json"
    if path.resolve() != run_wd.resolve() / "batch_handoff" / path.name:
        raise ValueError("Batch handoff path escapes its leaf")
    return path


def _verify_batch_handoff(
    job: Job, upstream: Job, runid: str, run_wd: Path,
) -> None:
    """Require successful RQ completion and exact durable attempt evidence."""
    if upstream.get_status(refresh=True) != JobStatus.FINISHED:
        raise RuntimeError(f"Hillslope prerequisite {upstream.id} did not finish successfully")
    path = _batch_handoff_path(run_wd, upstream.id)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1, "status": "success", "runid": runid,
        "hillslope_job_id": upstream.id, "watershed_job_id": job.id,
    }
    if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("Batch handoff receipt mismatch")
    if upstream.meta.get("batch_handoff") != receipt:
        raise ValueError("Batch handoff RQ receipt mismatch")


def run_batch_hillslopes_rq(
    batch_name: str,
    watershed_feature: WatershedFeature,
    watershed_job_id: str,
) -> dict[str, Any]:
    """Complete preparation/hillslopes and publish the attempt-bound handoff."""
    job = get_current_job()
    runid = _validate_batch_stage(job, batch_name, watershed_feature.runid, "hillslopes")
    downstream = Job.fetch(watershed_job_id, connection=job.connection)
    _validate_batch_stage(downstream, batch_name, watershed_feature.runid, "watershed")
    if (downstream.meta.get("batch_root_job_id") != job.meta.get("batch_root_job_id")
            or downstream.args[2] != job.id or job.args[2] != downstream.id):
        raise ValueError("Batch stage downstream lineage mismatch")
    status_channel = f"{batch_name}:batch"
    StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED run_batch_hillslopes_rq({runid})")
    try:
        runner = BatchRunner.getInstanceFromBatchName(batch_name)
        run_wd = Path(get_wd(runid))
        if run_wd.resolve() != Path(runner.batch_runs_dir).resolve() / watershed_feature.runid:
            raise ValueError("Batch leaf path escapes its workspace")
        locks_cleared = runner.run_batch_hillslopes(watershed_feature, job_id=job.id)
        receipt = {
            "schema_version": 1, "status": "success", "runid": runid,
            "hillslope_job_id": job.id, "watershed_job_id": watershed_job_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "hostname": socket.gethostname(), "pid": os.getpid(),
        }
        path = _batch_handoff_path(run_wd, job.id)
        path.parent.mkdir(exist_ok=True)
        # Same-directory atomic publication preserves the preceding receipt on failure.
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                json.dump(receipt, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        job.meta["batch_handoff"] = receipt
        job.meta["locks_cleared"] = list(locks_cleared)
        job.save_meta()
        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED run_batch_hillslopes_rq({runid})")
        return receipt
    except Exception:
        # RQ task boundary: retain traceback and failed job status for the observer.
        logger.exception("Batch hillslope stage failed for %s (job %s)", runid, job.id)
        raise


def run_batch_watershed_rq(
    batch_name: str,
    watershed_feature: WatershedFeature,
    hillslope_job_id: str,
) -> Tuple[bool, float]:
    """Complete watershed work or observe an unsuccessful hillslope prerequisite.

    Args:
        batch_name: Identifier of the batch runner workspace.
        watershed_feature: Feature metadata describing the watershed run.
        hillslope_job_id: Exact upstream job whose durable handoff is required.

    Returns:
        Success flag and whole-leaf elapsed seconds, including the stage handoff.
    """
    job = get_current_job()
    job_id = job.id if job is not None else "N/A"
    _runid = watershed_feature.runid
    runid = f'batch;;{batch_name};;{_runid}'
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{batch_name}:batch'
    start_ts = time.time()
    started_at = datetime.now(timezone.utc)

    # Identity failures must not enter the run-metadata failure writer below.
    _validate_batch_stage(job, batch_name, _runid, "watershed")
    upstream = Job.fetch(hillslope_job_id, connection=job.connection)
    _validate_batch_stage(upstream, batch_name, _runid, "hillslopes")
    if (upstream.meta.get("batch_root_job_id") != job.meta.get("batch_root_job_id")
            or upstream.args[2] != job.id or job.args[2] != upstream.id):
        raise ValueError("Batch stage upstream lineage mismatch")
    stage_started_at = started_at
    upstream_started_at = getattr(upstream, "started_at", None)
    if upstream_started_at is not None:
        started_at = upstream_started_at.replace(tzinfo=timezone.utc)
        start_ts = started_at.timestamp()
    batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    runid_wd = Path(get_wd(runid))
    if runid_wd.resolve() != Path(batch_runner.batch_runs_dir).resolve() / _runid:
        raise ValueError("Batch leaf path escapes its workspace")

    try:
        StatusMessenger.publish(status_channel, f'rq:{job_id} STARTED {func_name}({runid})')

        _verify_batch_handoff(job, upstream, runid, runid_wd)
        job.meta["watershed_stage_started"] = {
            "hostname": socket.gethostname(), "pid": os.getpid(),
            "started_at": stage_started_at.isoformat(),
        }
        job.save_meta()
        batch_runner.run_batch_watershed(watershed_feature, job_id=job_id)

        prep: Optional[RedisPrep] = None
        try:
            prep = RedisPrep.getInstance(str(runid_wd))
        except FileNotFoundError:
            prep = None

        if batch_runner.is_task_enabled(TaskEnum.run_omni_scenarios) and (
            prep is None or prep[str(TaskEnum.run_omni_scenarios)] is None
        ):
            root_job = Job.fetch(job.meta["batch_root_job_id"], connection=job.connection)
            final_job_id = root_job.meta["jobs:1,func:_final_batch_complete_rq"]
            # Publish intent before dispatch, under a short metadata-only lock.
            # Omni can execute synchronously; never hold this lock during science.
            with job.connection.lock(
                f"batch-finalizer-link:{final_job_id}", timeout=30, blocking_timeout=30,
            ):
                root_job.refresh()
                pending = list(root_job.meta.get("batch_pending_omni_links", []))
                pending.append(job.id)
                root_job.meta["batch_pending_omni_links"] = pending
                root_job.save_meta()
            _reset_omni_nodb_from_base(Path(batch_runner.base_wd), runid_wd, runid)
            omni_final_job = run_omni_scenarios_rq(runid)
            if omni_final_job is not None:
                job.meta['omni_final_job_id'] = omni_final_job.id
                job.save_meta()
            with job.connection.lock(
                f"batch-finalizer-link:{final_job_id}", timeout=30, blocking_timeout=30,
            ):
                if omni_final_job is not None:
                    final_job = Job.fetch(final_job_id, connection=job.connection)
                    dependency_ids = list(final_job._dependency_ids or [])
                    if omni_final_job.id not in dependency_ids:
                        dependency_ids.append(omni_final_job.id)
                        final_job._dependency_ids = dependency_ids
                        final_job.save()
                        final_job.register_dependency()
                # Refresh after dispatch: other leaves may have added intent.
                # Failure retains intent, preventing false final completion.
                root_job.refresh()
                pending = list(root_job.meta.get("batch_pending_omni_links", []))
                pending.remove(job.id)
                root_job.meta["batch_pending_omni_links"] = pending
                root_job.save_meta()

        elapsed = time.time() - start_ts
        status = True
        try:
            runid_wd.mkdir(parents=True, exist_ok=True)
            _write_watershed_run_metadata(
                run_wd=runid_wd,
                runid=runid,
                batch_name=batch_name,
                status="success",
                started_at=started_at,
                elapsed=elapsed,
                job_id=job_id,
            )
        except (OSError, TypeError, ValueError) as meta_exc:
            logger.warning("batch_rq: failed to write success metadata for %s - %s", runid, meta_exc)
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
            run_wd = runid_wd
            run_wd.mkdir(parents=True, exist_ok=True)
            _write_watershed_run_metadata(
                run_wd=run_wd,
                runid=runid,
                batch_name=batch_name,
                status="failed",
                started_at=started_at,
                elapsed=elapsed,
                job_id=job_id,
                error=error_payload,
            )
        except (OSError, TypeError, ValueError) as meta_exc:
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

        root_job_id = job.meta.get("batch_root_job_id")
        if root_job_id:
            root_job = Job.fetch(root_job_id, connection=job.connection)
            if root_job.meta.get("batch_pending_omni_links"):
                raise RuntimeError("Batch Omni dependency linkage is incomplete; retry after job inspection")

        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        run_states = batch_runner.classify_batch_run_states()
        runstate_summary = batch_runner.summarize_batch_run_states(run_states)
        StatusMessenger.publish(
            status_channel,
            (
                f"rq:{job.id} STATUS run summary total={runstate_summary['total']} "
                f"complete={runstate_summary['complete']} "
                f"failed={runstate_summary['failed']} "
                f"incomplete={runstate_summary['incomplete']} "
                f"missing={runstate_summary['missing']} "
                f"invalid={runstate_summary['invalid']} "
                f"retry_eligible={runstate_summary['retry_eligible']}"
            ),
        )
        has_incomplete_leaves = any(
            runstate_summary[key] > 0
            for key in ("failed", "incomplete", "missing", "invalid", "retry_eligible")
        )

        if send_discord_message is not None:
            try:
                send_discord_message(f':herb: Batch {batch_name} completed on {_hostname}')
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/batch_rq.py:504", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({batch_name})')
        if has_incomplete_leaves:
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch BATCH_RUN_COMPLETED_WITH_FAILURES')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch BATCH_RUN_COMPLETED')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch END_BROADCAST')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni END_BROADCAST')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/batch_rq.py:512", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({batch_name})')
        raise
