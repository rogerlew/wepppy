"""RQ task wrappers for PATH cost-effective optimization workflows."""

from __future__ import annotations

import inspect
from typing import Any, Dict

from rq import get_current_job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.mods.path_ce import PathCostEffective
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.weppcloud.utils.helpers import get_wd

TIMEOUT: int = 43_200


def run_path_cost_effective_rq(runid: str) -> Dict[str, Any]:
    """Run the PATH cost-effective optimization workflow for the given project.

    Args:
        runid: Identifier used to locate the working directory.

    Returns:
        Serialized solver payload including cost summaries and artifact paths.
    """
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:path_ce"
    StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

    wd = get_wd(runid)
    prep = RedisPrep.tryGetInstance(wd)
    if prep is not None:
        try:
            prep.set_rq_job_id("run_path_ce", job.id)
            prep.remove_timestamp(TaskEnum.run_path_cost_effective)
        except Exception:
            pass

    controller = PathCostEffective.getInstance(wd)

    try:
        StatusMessenger.publish(status_channel, f"rq:{job.id} STATUS Preparing PATH Cost-Effective inputs")
        result = controller.run()

        if prep is not None:
            try:
                prep.timestamp(TaskEnum.run_path_cost_effective)
            except Exception:
                pass

        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
        StatusMessenger.publish(status_channel, f"rq:{job.id} TRIGGER path_ce PATH_CE_RUN_COMPLETE")
        return result
    except Exception:
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise
