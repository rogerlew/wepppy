from __future__ import annotations

from typing import Callable, Tuple

from rq.job import Job
from wepppy.topo.watershed_collection import WatershedFeature

_hostname: str
REDIS_HOST: str
RQ_DB: int
TIMEOUT: int
send_discord_message: Callable[[str], None] | None

def run_batch_rq(batch_name: str) -> Job: ...

def run_batch_watershed_rq(
    batch_name: str,
    watershed_feature: WatershedFeature,
) -> Tuple[bool, float]: ...

def _final_batch_complete_rq(batch_name: str) -> None: ...
