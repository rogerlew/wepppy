from __future__ import annotations

import inspect

from rq import get_current_job

from wepppy.nodb.status_messenger import StatusMessenger

TIMEOUT: int = 43_200


def run_culvert_batch_rq(culvert_batch_uuid: str) -> None:
    """Placeholder entrypoint for culvert batch processing."""
    job = get_current_job()
    job_id = job.id if job is not None else "N/A"
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{culvert_batch_uuid}:culvert_batch"

    if job is not None:
        job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        job.save()

    StatusMessenger.publish(
        status_channel, f"rq:{job_id} STARTED {func_name}({culvert_batch_uuid})"
    )

    try:
        StatusMessenger.publish(
            status_channel, f"rq:{job_id} COMPLETED {func_name}({culvert_batch_uuid})"
        )
    except Exception:
        StatusMessenger.publish(
            status_channel, f"rq:{job_id} EXCEPTION {func_name}({culvert_batch_uuid})"
        )
        raise


__all__ = ["TIMEOUT", "run_culvert_batch_rq"]
