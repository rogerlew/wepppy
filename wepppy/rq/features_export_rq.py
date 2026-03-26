"""RQ worker entrypoints for features export orchestration."""

from __future__ import annotations

import logging

from rq import get_current_job

from wepppy.nodb.mods.features_export.service import execute_features_export
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.utils.helpers import get_wd

logger = logging.getLogger(__name__)


def _resolve_workdir(runid: str, *, wd_override: str | None) -> str:
    if isinstance(wd_override, str) and wd_override.strip():
        return wd_override
    return get_wd(runid)


def _current_job_id() -> str:
    job = get_current_job()
    value = getattr(job, "id", None) if job is not None else None
    if isinstance(value, str) and value:
        return value
    return "unknown"


def _run_features_export_worker(
    runid: str,
    config: str,
    payload: dict[str, object],
    *,
    task_name: str,
    force_cache_hit: bool,
    wd_override: str | None,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object.")

    job_id = _current_job_id()
    status_channel = f"{runid}:features_export"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {task_name}({runid})")

    wd = _resolve_workdir(runid, wd_override=wd_override)
    prep = RedisPrep.tryGetInstance(wd)
    if prep is not None:
        try:
            prep.remove_timestamp(TaskEnum.run_features_export)
        except Exception as exc:  # boundary: prep metadata persistence should not mask worker execution
            logger.warning("features export: failed to clear timestamp (%s): %s", runid, exc)

    try:
        result = execute_features_export(
            wd,
            runid=runid,
            config=config,
            payload=payload,
            job_id=job_id,
            force_cache_hit=force_cache_hit,
        )
        if prep is not None:
            try:
                prep.timestamp(TaskEnum.run_features_export)
            except Exception as exc:  # boundary: prep metadata persistence should not mask worker completion
                logger.warning("features export: failed to set timestamp (%s): %s", runid, exc)

        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED {task_name}({runid})")
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} TRIGGER features_export FEATURES_EXPORT_TASK_COMPLETED",
        )
        return result
    except Exception:
        # Boundary catch: preserve queue contract while surfacing the original exception.
        logger.exception("features export worker failed", extra={"runid": runid, "job_id": job_id})
        StatusMessenger.publish(status_channel, f"rq:{job_id} EXCEPTION {task_name}({runid})")
        raise


@with_exception_logging
def run_features_export_rq(
    runid: str,
    config: str,
    payload: dict[str, object],
    wd_override: str | None = None,
) -> dict[str, object]:
    """Execute a full features export job."""

    return _run_features_export_worker(
        runid,
        config,
        payload,
        task_name="run_features_export_rq",
        force_cache_hit=False,
        wd_override=wd_override,
    )


@with_exception_logging
def run_features_export_cache_hit_rq(
    runid: str,
    config: str,
    payload: dict[str, object],
    wd_override: str | None = None,
) -> dict[str, object]:
    """Finalize a cached features export artifact into a new job-scoped manifest."""

    return _run_features_export_worker(
        runid,
        config,
        payload,
        task_name="run_features_export_cache_hit_rq",
        force_cache_hit=True,
        wd_override=wd_override,
    )


__all__ = [
    "run_features_export_cache_hit_rq",
    "run_features_export_rq",
]
