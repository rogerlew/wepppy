from __future__ import annotations

import logging
from typing import Any

from rq import Queue, Worker
from rq.job import Job
from rq.registry import StartedJobRegistry

from wepppy.profile_coverage import ProfileCoverageSettings

REDIS_HOST: str
RQ_DB: int
DEFAULT_RESULT_TTL: int
LOGGER: logging.Logger
PROFILE_COVERAGE_SETTINGS: ProfileCoverageSettings

class JobCancelledException(Exception): ...

class WepppyRqWorker(Worker):
    def perform_job(self, job: Job, queue: Queue) -> bool: ...
    def handle_job_failure(
        self,
        job: Job,
        queue: Queue,
        started_job_registry: StartedJobRegistry | None = ...,
        exc_string: str = ...,
    ) -> None: ...
    def handle_job_success(self, job: Job, queue: Queue, started_job_registry: StartedJobRegistry) -> None: ...
    def handle_cancel_signal(self, signum: int, frame: object | None) -> None: ...
    def handle_exception(self, job: Job, *exc_info: Any) -> None: ...

def start_worker() -> None: ...
