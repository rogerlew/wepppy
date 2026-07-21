"""RQ task wrapper for the PATH cost-effective pipeline (v2).

Omni provisioning was removed per D3/ADR-0023: the user runs Omni
scenarios and contrasts before PATH-CE; this task validates preconditions
and fails with actionable messages when artifacts are missing. Stage
transitions stream on the ``{runid}:path_ce`` channel via the controller's
status callback.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Dict

import redis
from rq import get_current_job

from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.nodb.mods.path_ce import PathCostEffective
from wepppy.nodb.mods.path_ce.preconditions import PathCEPreconditionError
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.rq.exception_logging import with_exception_logging

TIMEOUT: int = 43_200

logger = logging.getLogger(__name__)


@with_exception_logging
def run_path_cost_effective_rq(runid: str) -> Dict[str, Any]:
    """Run the PATH cost-effective pipeline for the given project.

    Stages: validate preconditions → data prep → solve → threshold sweep →
    render the HTML report → persist artifacts under ``<wd>/path/``.
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
        except (redis.exceptions.RedisError, OSError, ValueError, TypeError) as exc:
            logger.warning(
                "path_ce: failed to persist prep job metadata (runid=%s job_id=%s): %s",
                runid,
                job.id,
                exc,
            )

    # Root/precondition rejection must precede cache invalidation and
    # mutable hydration (NoDb mutation-cache-guard ordering).
    try:
        for root in ("climate", "watershed", "landuse", "soils"):
            nodir_resolve(wd, root, view="effective")
    except Exception:
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise

    clear_nodb_file_cache(runid, pup_relpath="path_ce.nodb")
    controller = PathCostEffective.getInstance(wd)

    def _emit(message: str) -> None:
        StatusMessenger.publish(status_channel, f"rq:{job.id} STATUS {message}")

    try:
        result = controller.run(status_callback=_emit)

        if prep is not None:
            try:
                prep.timestamp(TaskEnum.run_path_cost_effective)
            except (redis.exceptions.RedisError, OSError, ValueError, TypeError) as exc:
                logger.warning(
                    "path_ce: failed to record prep timestamp (runid=%s job_id=%s task=%s): %s",
                    runid,
                    job.id,
                    TaskEnum.run_path_cost_effective,
                    exc,
                )

        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
        StatusMessenger.publish(status_channel, f"rq:{job.id} TRIGGER path_ce PATH_CE_RUN_COMPLETE")
        return result
    except PathCEPreconditionError as exc:
        # controller.run() already set status=failed with the report message
        for error in exc.report.errors:
            StatusMessenger.publish(status_channel, f"rq:{job.id} STATUS PRECONDITION {error}")
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise
    except Exception as exc:
        try:
            controller.set_status("failed", message=str(exc))
        except Exception as status_exc:  # pragma: no cover - best-effort cleanup only
            logger.warning(
                "path_ce: failed to update controller status after exception (runid=%s job_id=%s): %s",
                runid,
                job.id,
                status_exc,
                exc_info=True,
            )
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise
