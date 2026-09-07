from typing import Any
from rq.job import Job

def report_fork_failure(job: Job, connection: Any, exc_type: Any, exc_value: Any, traceback: Any) -> None: ...
