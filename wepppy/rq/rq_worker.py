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
from multiprocessing import Process

import redis
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
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
PROFILE_COVERAGE_SETTINGS = load_settings_from_env()
if PROFILE_COVERAGE_SETTINGS.enabled and Coverage is not None:
    PROFILE_COVERAGE_SETTINGS.ensure_data_root(LOGGER)
    install_rq_hooks()


class JobCancelledException(Exception):
    """Custom exception raised when a job is cancelled."""
    pass


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
            cov = Coverage(**kwargs)
            try:
                cov.load()
            except CoverageException:
                pass
            cov.start()
        except Exception as exc:  # pragma: no cover - defensive logging
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
            LOGGER.exception("Unexpected error while saving coverage for slug %s: %s", slug, exc)
        finally:
            reset_profile_trace_slug(ctx_token)
        
    def perform_job(self, job: 'Job', queue: 'Queue') -> bool:
        """Override perform_job to capture PID/runid metadata and log to rq.log."""
        self.default_result_ttl = DEFAULT_RESULT_TTL
        runid = job.args[0]
        job.meta['pid'] = os.getpid()
        job.meta['runid'] = runid
        job.save()

        wd = None
        if runid is not None:
            try:
                wd = get_wd(runid)
            except Exception:
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
        super().handle_job_failure(job, queue, started_job_registry)
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
        super().handle_exception(job, *exc_info)
        StatusMessenger.publish('f{runid}:rq', json.dumps({'job': job.id, 'status': 'exception'}))
        print(f"Job {job.id} Raised Exception")
        exc_string = ''.join(traceback.format_exception(*exc_info))
        job.meta['exc_string'] = exc_string
        job.save()


def start_worker() -> None:
    """Start a worker that listens on the high/default/low queues."""
    from redis import Connection as RedisConnection
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    redis_conn = redis.Redis(**conn_kwargs)
    with RedisConnection(redis_conn):
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
