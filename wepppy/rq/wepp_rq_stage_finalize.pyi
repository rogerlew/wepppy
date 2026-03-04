from __future__ import annotations

from typing import Callable

from rq.job import Job
from wepppy.nodb.core import Wepp

send_discord_message: Callable[[str], None] | None


def _bootstrap_autocommit_actor(job: Job | None) -> str: ...


def _bootstrap_autocommit_with_lock(runid: str, wepp: Wepp, stage: str, *, actor: str) -> str | None: ...


def _log_complete_rq(
    runid: str,
    auto_commit_inputs: bool = ...,
    commit_stage: str = ...,
    *,
    send_message: Callable[[str], None] | None = ...,
) -> None: ...

def _log_prep_complete_rq(
    runid: str,
    auto_commit_inputs: bool = ...,
    commit_stage: str = ...,
    *,
    send_message: Callable[[str], None] | None = ...,
) -> None: ...
