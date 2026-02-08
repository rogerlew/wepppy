from __future__ import annotations

from rq.job import Job

REDIS_HOST: str
RQ_DB: int
TIMEOUT: int

def run_swat_rq(runid: str) -> Job: ...

def run_swat_noprep_rq(runid: str) -> Job: ...

def _build_swat_inputs_rq(runid: str) -> None: ...

def _run_swat_rq(runid: str) -> None: ...
