from __future__ import annotations

import logging
from typing import Any, Callable, Tuple

from wepppy.topo.watershed_collection import WatershedFeature

_hostname: str
REDIS_HOST: str
RQ_DB: int
TIMEOUT: int
logger: logging.Logger
send_discord_message: Callable[[str], None] | None

def reconcile_deferred_batch_jobs(
    batch_name: str,
    *,
    redis_conn: Any,
    exclude_job_ids: set[str] | None = ...,
    lease_checkpoint: Callable[[], None] | None = ...,
    _watch_attempt: int = ...,
) -> list[str]: ...

def run_batch_rq(batch_name: str) -> dict[str, Any]: ...

def delete_batch_rq(batch_name: str) -> dict[str, Any]: ...

def run_batch_watershed_rq(
    batch_name: str,
    watershed_feature: WatershedFeature,
) -> Tuple[bool, float]: ...

def _final_batch_complete_rq(batch_name: str) -> None: ...
