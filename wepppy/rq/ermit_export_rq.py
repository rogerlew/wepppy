"""RQ worker entrypoint for ERMiT/Disturbed WEPP batch export generation."""

from __future__ import annotations

import logging
from pathlib import Path

from rq import get_current_job

from wepppy.export import create_ermit_input
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


@with_exception_logging
def run_ermit_export_rq(
    runid: str,
    config: str,
    wd_override: str | None = None,
) -> dict[str, object]:
    """Generate the ERMiT/Disturbed WEPP batch-input archive for a run."""

    job_id = _current_job_id()
    status_channel = f"{runid}:ermit_export"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED run_ermit_export_rq({runid})")

    try:
        wd = _resolve_workdir(runid, wd_override=wd_override)
        wd_path = Path(wd).resolve()
        artifact_path = Path(create_ermit_input(wd)).resolve()
        artifact_relpath = artifact_path.relative_to(wd_path).as_posix()
        result: dict[str, object] = {
            "artifact_relpath": artifact_relpath,
            "filename": artifact_path.name,
            "config": config,
        }
        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED run_ermit_export_rq({runid})")
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} TRIGGER ermit_export ERMIT_EXPORT_TASK_COMPLETED",
        )
        return result
    except Exception:
        # Boundary catch: keep RQ exception logging/status updates while preserving the original failure.
        logger.exception("ERMiT export worker failed", extra={"runid": runid, "job_id": job_id})
        StatusMessenger.publish(status_channel, f"rq:{job_id} EXCEPTION run_ermit_export_rq({runid})")
        raise


__all__ = ["run_ermit_export_rq"]
