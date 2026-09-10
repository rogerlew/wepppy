"""Custom Redis Queue worker that adds per-run logging and cancellation hooks."""

from __future__ import annotations

import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import signal

import logging

import json
import traceback
from typing import Any, cast
from multiprocessing import Process

import redis
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)
from wepppy.observability.correlation import (
    install_correlation_log_record_factory,
    normalize_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)

import rq
from rq import Worker, Queue
from rq.job import Job
from rq.registry import StartedJobRegistry
from rq.exceptions import NoSuchJobError

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.profile_coverage import load_settings_from_env
from wepppy.profile_coverage.runtime import (
    install_rq_hooks,
    reset_profile_trace_slug,
    set_profile_trace_slug,
)
from wepppy.rq.auth_actor import (
    install_rq_auth_actor_hook,
    reset_auth_actor,
    set_auth_actor,
)
try:
    from coverage import Coverage
    from coverage.exceptions import CoverageException
except ImportError as exc:  # coverage is required for profile tracing
    raise RuntimeError("coverage.py must be installed for profile coverage") from exc

from uuid import uuid4


REDIS_HOST = redis_host()
RQ_DB = int(RedisDB.RQ)

DEFAULT_RESULT_TTL = 604_800  # 1 week

LOGGER = logging.getLogger(__name__)
install_correlation_log_record_factory()
PROFILE_COVERAGE_SETTINGS = load_settings_from_env()
if PROFILE_COVERAGE_SETTINGS.enabled and Coverage is not None:
    PROFILE_COVERAGE_SETTINGS.ensure_data_root(LOGGER)
    install_rq_hooks()

install_rq_auth_actor_hook()


class JobCancelledException(Exception):
    """Custom exception raised when a job is cancelled."""
    pass


def _extract_runid(job: Job) -> str | None:
    """Best-effort runid extraction for jobs with positional or keyword args."""
    if job.args:
        candidate = job.args[0]
        if isinstance(candidate, str) and candidate:
            return candidate

    if isinstance(job.kwargs, dict):
        candidate = job.kwargs.get("runid")
        if isinstance(candidate, str) and candidate:
            return candidate

    if isinstance(job.meta, dict):
        candidate = job.meta.get("runid")
        if isinstance(candidate, str) and candidate:
            return candidate

    return None


class WepppyRqWorker(Worker):
    """RQ worker that attaches run-scoped logs and supports SIGUSR1 cancellations."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the signal handler for SIGUSR1
        signal.signal(signal.SIGUSR1, self.handle_cancel_signal)

    def _start_job_coverage(self, job: Job):
        if not PROFILE_COVERAGE_SETTINGS.enabled:
            return None
        slug = None
        if isinstance(job.meta, dict):
            slug = job.meta.get("profile_trace_slug")
        if not slug:
            LOGGER.info(
                "Profile coverage: job %s has no profile_trace_slug meta; skipping coverage.",
                job.id,
            )
            return None
        token = uuid4().hex
        ctx_token = set_profile_trace_slug(slug)
        kwargs = PROFILE_COVERAGE_SETTINGS.coverage_kwargs(slug, token)
        LOGGER.info(
            "Profile coverage: starting for job %s slug=%s data_file=%s context=%s",
            job.id,
            slug,
            kwargs.get("data_file"),
            kwargs.get("context"),
        )
        try:
            cov = Coverage(**cast(dict[str, Any], kwargs))
            try:
                cov.load()
            except CoverageException:
                pass
            cov.start()
        except Exception as exc:  # pragma: no cover - defensive logging
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/rq_worker.py:110", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            reset_profile_trace_slug(ctx_token)
            LOGGER.warning(
                "Failed to start profile coverage for job %s (slug=%s): %s",
                job.id,
                slug,
                exc,
            )
            return None
        return cov, ctx_token, slug

    def _stop_job_coverage(self, state) -> None:
        coverage_state, ctx_token, slug = state
        try:
            coverage_state.stop()
            coverage_state.save()
        except CoverageException as exc:  # pragma: no cover - logging only
            LOGGER.warning("Profile coverage save failed for slug %s: %s", slug, exc)
        except Exception as exc:  # pragma: no cover - defensive logging
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/rq_worker.py:128", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            LOGGER.exception("Unexpected error while saving coverage for slug %s: %s", slug, exc)
        finally:
            reset_profile_trace_slug(ctx_token)
        
    def perform_job(self, job: 'Job', queue: 'Queue') -> bool:
        """Override perform_job to capture PID/runid metadata and log to rq.log."""
        self.default_result_ttl = DEFAULT_RESULT_TTL
        runid = _extract_runid(job)
        if not isinstance(job.meta, dict):
            job.meta = {}
        job.meta['pid'] = os.getpid()
        if runid is not None:
            job.meta['runid'] = runid
        job.save()

        auth_token = None
        correlation_token = None
        if isinstance(job.meta, dict):
            auth_actor = job.meta.get("auth_actor")
            if isinstance(auth_actor, dict) and auth_actor:
                auth_token = set_auth_actor(auth_actor)
            raw_correlation_id = job.meta.get("correlation_id")
            if isinstance(raw_correlation_id, str):
                correlation_id = normalize_correlation_id(raw_correlation_id)
                if correlation_id:
                    correlation_token = set_correlation_id(correlation_id)

        wd = None
        if runid is not None:
            try:
                wd = get_wd(runid)
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/rq_worker.py:151", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                wd = None

        file_handler = None
        if wd and os.path.isdir(wd):
            try:
                file_handler = logging.FileHandler(_join(wd, 'rq.log'))
                self.log.addHandler(file_handler)
            except OSError:
                file_handler = None

        coverage_state = self._start_job_coverage(job)
        try:
            print(f"Starting job {job.id}")
            return super().perform_job(job, queue)
        finally:
            if coverage_state:
                self._stop_job_coverage(coverage_state)
            if auth_token is not None:
                reset_auth_actor(auth_token)
            if correlation_token is not None:
                reset_correlation_id(correlation_token)
            if file_handler:
                self.log.removeHandler(file_handler)
                
    def handle_job_failure(
        self,
        job: Job,
        queue: Queue,
        started_job_registry: StartedJobRegistry | None = None,
        exc_string: str = '',
    ) -> None:
        """Publish job failure events while preserving the superclass behavior."""
        controlled_error = (
            job.meta.get("error")
            if isinstance(job.meta, dict)
            else None
        )
        if isinstance(controlled_error, dict):
            sanitized = str(controlled_error.get("message") or "Controlled job failure")
            super().handle_job_failure(
                job,
                queue,
                started_job_registry,
                exc_string=sanitized,
            )
            job.meta["exc_string"] = sanitized
            job.save_meta()
        else:
            super().handle_job_failure(
                job,
                queue,
                started_job_registry,
                exc_string=exc_string,
            )
        if isinstance(job.meta, dict) and isinstance(job.meta.get("fork_failure"), dict):
            # RQ's per-job failure callback is skipped when the work horse dies
            # (for example OOM/SIGKILL). Reconcile from the surviving supervisor.
            # Duplicate task-callback reports are suppressed by the receipt Lua.
            from wepppy.rq.fork_failure import report_fork_failure

            try:
                if job.get_status(refresh=True) == "failed":
                    report_fork_failure(job, job.connection, None, None, None)
            except redis.RedisError:
                LOGGER.exception("Could not inspect failed fork prerequisite job_id=%s", job.id)
        if isinstance(job.meta, dict):
            try:
                from wepppy.rq.project_rq import (
                    _WBT_ADMISSION_RECEIPT_KEY,
                    _release_subcatchment_tail,
                )

                if isinstance(job.meta.get(_WBT_ADMISSION_RECEIPT_KEY), str):
                    runid = _extract_runid(job)
                    if runid is not None:
                        _release_subcatchment_tail(
                            job.connection,
                            runid,
                            job.id,
                        )
            except redis.RedisError:
                LOGGER.exception(
                    "Could not release failed WBT subcatchment mutation tail "
                    "(job_id=%s)",
                    job.id,
                )
        StatusMessenger.publish('f{runid}:rq', json.dumps({'job': job.id, 'status': 'failed'}))
        print(f"Job {job.id} Failed")

    def handle_job_success(self, job: Job, queue: Queue, started_job_registry: StartedJobRegistry) -> None:
        """Publish job success events while preserving the superclass behavior."""
        super().handle_job_success(job, queue, started_job_registry)
        StatusMessenger.publish('f{runid}:rq', json.dumps({'job': job.id, 'status': 'success'}))
        print(f"Finished job {job.id}")

    def handle_cancel_signal(self, signum: int, frame: object | None) -> None:
        """Handle SIGUSR1 by raising an exception to stop the job."""
        raise JobCancelledException("Job was cancelled")
        
    def handle_exception(self, job: Job, *exc_info) -> None:
        """Publish exception details before delegating back to the superclass."""
        controlled_error = (
            job.meta.get("error")
            if isinstance(job.meta, dict)
            else None
        )
        if isinstance(controlled_error, dict):
            message = str(controlled_error.get("message") or "Controlled job failure")
            error_id = str(job.meta.get("error_id") or "")
            edge_ids = (
                controlled_error.get("details", {}).get("edge_hillslope_ids", [])
                if isinstance(controlled_error.get("details"), dict)
                else []
            )
            runid = _extract_runid(job)
            self.log.error(
                "Controlled RQ failure "
                "[error_id=%s job_id=%s runid=%s edge_hillslope_ids=%s]: %s",
                error_id,
                job.id,
                runid,
                edge_ids,
                message,
                extra={
                    "error_id": error_id,
                    "job_id": job.id,
                    "runid": runid,
                    "edge_hillslope_ids": edge_ids,
                },
            )
            job.meta["exc_string"] = message
            job.save_meta()
        else:
            super().handle_exception(job, *exc_info)
            exc_string = ''.join(traceback.format_exception(*exc_info))
            job.meta['exc_string'] = exc_string
            job.save()
        StatusMessenger.publish('f{runid}:rq', json.dumps({'job': job.id, 'status': 'exception'}))
        print(f"Job {job.id} Raised Exception")


    def fork_work_horse(self, job: Job, queue: Queue) -> None:
        from wepppy.rq.directory_locks import prepare_containment
        from wepppy.runtime_paths.thaw_freeze import maintenance_lock_execution

        self._directory_lock_cancel_requested = False
        self._directory_lock_containment_error = None
        self._directory_lock_protected_children = {}
        try:
            scheduler_process = getattr(getattr(self, "scheduler", None), "_process", None)
            scheduler_pid = (
                scheduler_process.pid
                if scheduler_process is not None and scheduler_process.is_alive()
                else None
            )
            self._directory_lock_protected_children = prepare_containment(scheduler_pid)
        except (OSError, RuntimeError) as exc:
            # Cleanup boundary: cancellation still stops RQ, but uncertain
            # process ownership must never authorize directory-lock release.
            self._directory_lock_containment_error = str(exc)
            LOGGER.exception("Directory lock containment unavailable job_id=%s", job.id)
        with maintenance_lock_execution(job.id) as execution_id:
            self._directory_lock_execution_id = execution_id
            job.meta["directory_lock_execution_id"] = execution_id
            job.meta["directory_lock_cleanup"] = {"execution_id": execution_id, "state": "not_requested"}
            job.save_meta()
            super().fork_work_horse(job, queue)

    def kill_horse(self, sig: signal.Signals = signal.SIGKILL) -> None:
        if self._stopped_job_id is not None:
            self._directory_lock_cancel_requested = True
        super().kill_horse(sig)

    def monitor_work_horse(self, job: Job, queue: Queue) -> None:
        try:
            super().monitor_work_horse(job, queue)
        finally:
            try:
                self._cleanup_canceled_directory_locks(job)
            finally:
                self._retire_if_writers_remain(job)
                for fd in self._directory_lock_protected_children.values():
                    os.close(fd)
                self._directory_lock_protected_children = {}

    def _cleanup_canceled_directory_locks(self, job: Job) -> None:
        if getattr(self, "_directory_lock_cancel_requested", False):
            from wepppy.rq.directory_locks import cleanup_stopped_execution, record_cleanup

            try:
                cleanup_stopped_execution(self, job)
            except (OSError, RuntimeError, ValueError, redis.RedisError) as exc:
                # Post-stop cleanup boundary: retain exclusion on uncertain
                # termination/Redis state and preserve RQ's terminal handling.
                LOGGER.exception("Directory lock cleanup failed job_id=%s", job.id)
                record_cleanup(job, self._directory_lock_execution_id,
                               "pending", reason=str(exc))

    def _retire_if_writers_remain(self, job: Job) -> None:
        from wepppy.rq.directory_locks import has_remaining_writers

        try:
            if not self._directory_lock_containment_error and not has_remaining_writers(
                self._directory_lock_protected_children
            ):
                return
        except (OSError, RuntimeError):
            LOGGER.exception("Could not inspect residual writers job_id=%s", job.id)
        # Subreaper adoption survives job failure. Never attribute a crashed
        # execution's surviving descendants to the next job. The worker pool
        # replaces this supervisor; failed-job locks retain existing recovery.
        self._stop_requested = True
        LOGGER.error("Retiring worker with uncertain/residual writers job_id=%s", job.id)

def start_worker() -> None:
    """Start a worker that listens on the high/default/low queues."""
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    redis_conn = redis.Redis(**conn_kwargs)
    qs = [
        Queue('high', connection=redis_conn),
        Queue('default', connection=redis_conn),
        Queue('low', connection=redis_conn),
    ]
    w = WepppyRqWorker(qs, connection=redis_conn)
    w.work()


if __name__ == '__main__':
    num_workers = 5
    workers = []

    for _ in range(num_workers):
        p = Process(target=start_worker)
        p.start()
        workers.append(p)

    for p in workers:
        p.join()
