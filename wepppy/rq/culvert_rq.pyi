from __future__ import annotations

from typing import Any

from rq.job import Job

TIMEOUT: int

class CulvertBatchError(Exception):
    total: int
    succeeded: int
    failed: int
    def __init__(
        self,
        message: str,
        *,
        total: int = 0,
        succeeded: int = 0,
        failed: int = 0,
    ) -> None: ...

class WatershedAreaBelowMinimumError(Exception): ...

def run_culvert_batch_rq(culvert_batch_uuid: str) -> Job: ...

def run_culvert_run_rq(runid: str, culvert_batch_uuid: str, run_id: str) -> str: ...

def run_culvert_batch_finalize_rq(culvert_batch_uuid: str) -> dict[str, Any]: ...

def _final_culvert_batch_complete_rq(culvert_batch_uuid: str) -> dict[str, Any]: ...

__all__: list[str] = [
    "TIMEOUT",
    "run_culvert_batch_rq",
    "run_culvert_run_rq",
    "run_culvert_batch_finalize_rq",
    "CulvertBatchError",
]
