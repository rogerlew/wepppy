from __future__ import annotations

import inspect
import logging
from typing import Callable

import redis
from rq import get_current_job
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron, Wepp
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.weppcloud.bootstrap.git_lock import (
    acquire_bootstrap_git_lock,
    release_bootstrap_git_lock,
)
from wepppy.weppcloud.utils.helpers import get_wd

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except (ModuleNotFoundError, ImportError):
    send_discord_message = None

_LOGGER = logging.getLogger(__name__)


def _bootstrap_autocommit_actor(job: Job | None) -> str:
    job_id = str(getattr(job, "id", "") or "").strip()
    if job_id:
        return f"rq:{job_id}:wepp:auto_commit"
    return "rq:unknown:wepp:auto_commit"


def _bootstrap_autocommit_with_lock(runid: str, wepp: Wepp, stage: str, *, actor: str) -> str | None:
    conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
    with redis.Redis(**conn_kwargs) as redis_conn:
        lock = acquire_bootstrap_git_lock(
            redis_conn,
            runid=runid,
            operation="auto_commit",
            actor=actor,
        )
        if lock is None:
            wepp.logger.warning("Skipped bootstrap auto-commit for %s: bootstrap lock busy", stage)
            return None
        try:
            return wepp.bootstrap_commit_inputs(stage)
        finally:
            release_bootstrap_git_lock(redis_conn, runid=runid, token=lock.token)


def _log_complete_rq(
    runid: str,
    auto_commit_inputs: bool = False,
    commit_stage: str = "WEPP pipeline",
    *,
    send_message: Callable[[str], None] | None = send_discord_message,
) -> None:
    """Record final completion metadata and emit notifications for the run."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.run_wepp_watershed)
        except FileNotFoundError:
            _LOGGER.info(
                "Skipping run_wepp_watershed prep timestamp for %s: RedisPrep is unavailable",
                runid,
            )

        if auto_commit_inputs:
            wepp = Wepp.getInstance(wd)
            _bootstrap_autocommit_with_lock(
                runid,
                wepp,
                commit_stage,
                actor=_bootstrap_autocommit_actor(job),
            )

        ron = Ron.getInstance(wd)
        name = ron.name
        scenario = ron.scenario
        config = ron.config_stem

        link = runid
        if name or scenario:
            if name and scenario:
                link = f'{name} - {scenario} _{runid}_'
            elif name:
                link = f'{name} _{runid}_'
            else:
                link = f'{scenario} _{runid}_'

        if send_message is not None:
            send_message(f':fireworks: [{link}](https://wepp.cloud/weppcloud/runs/{runid}/{config}/)')

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   wepp WEPP_RUN_TASK_COMPLETED')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_finalize.py:107", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
