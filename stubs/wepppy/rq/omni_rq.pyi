from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

import redis
from rq.job import Job

from wepppy.nodb.mods.omni import Omni

REDIS_HOST: str
RQ_DB: int
TIMEOUT: int
send_discord_message: Callable[[str], None] | None

class OmniLockTimeout(Exception): ...

def _scenario_payload_for_job(scenario_def: Dict[str, Any]) -> Dict[str, Any]: ...

def _update_dependency_state(
    omni: Omni,
    scenario_name: str,
    dependency_entry: Dict[str, Any],
    run_state_entry: Dict[str, Any],
) -> None: ...

def run_omni_scenario_rq(
    runid: str,
    scenario: Dict[str, Any],
    *,
    dependency_target: Optional[str] = ...,
    dependency_path: Optional[str] = ...,
    signature: Optional[str] = ...,
    run_state_reason: str = ...,
) -> Tuple[bool, float]: ...

def run_omni_scenarios_rq(runid: str) -> Optional[Job]: ...

def _compile_hillslope_summaries_rq(runid: str) -> None: ...

def _finalize_omni_scenarios_rq(runid: str) -> None: ...
