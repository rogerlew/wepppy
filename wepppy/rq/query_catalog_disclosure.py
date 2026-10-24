"""Payload-independent public disclosure for query catalog maintenance jobs.

Keep this module independent of refresh workers and their filesystem imports:
retained job IDs must remain safely pollable after a worker rollback.
"""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from wepppy.rq.job_id import new_rq_job_id

__all__ = ["PREFIX", "DESCRIPTION", "is_query_catalog_job", "maintenance_error", "safe_job_details", "get_query_catalog_job_details"]

PREFIX = "query_catalog_refresh_"
DESCRIPTION = "Query catalog maintenance"
_STATES = {"queued", "started", "finished", "failed", "stopped", "canceled", "deferred", "scheduled"}
_FAILURES = {"failed", "stopped", "canceled"}
_LOG = logging.getLogger(__name__)


def is_query_catalog_job(job_id: str) -> bool:
    """Classify before loading any RQ serialized arguments, metadata or result."""
    return str(job_id).startswith(PREFIX)


def maintenance_error() -> dict[str, Any]:
    return {
        "error": {
            "code": "query_catalog_refresh_failed",
            "message": "Query catalog maintenance failed; consult project diagnostics",
        },
        "error_id": new_rq_job_id(),
    }


def safe_job_details(job_id: str, job: Any = None) -> dict[str, Any]:
    """Return a failure shape without inspecting an untrusted RQ object."""
    return _details(job_id, "failed", None, None)


def _timestamp(raw: Any) -> str | None:
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("ascii")
    return str(datetime.fromisoformat(raw.replace("Z", "+00:00")))


def _details(job_id: str, state: str, started: str | None, ended: str | None) -> dict[str, Any]:
    result = {
        "job_id": job_id, "status": state, "description": DESCRIPTION,
        "started_at": started, "ended_at": ended, "runid": None,
        "result": None, "exc_info": None, "auth_actor": None, "children": {},
    }
    if state in _FAILURES:
        result.update(maintenance_error())
    return result


def get_query_catalog_job_details(job_id: str, connection: Any) -> dict[str, Any]:
    """Read only allowlisted scalar hash fields; never deserialize the job.

    A single HMGET avoids reading data/meta/result even when their serializer or
    worker module is unavailable. Unknown status or malformed dates fail closed.
    """
    if not is_query_catalog_job(job_id):
        raise ValueError("Not a query catalog maintenance job")
    try:
        values = connection.hmget(f"rq:job:{job_id}", "status", "started_at", "ended_at")
        if all(value is None for value in values):
            if not connection.exists(f"rq:job:{job_id}"):
                return {"job_id": job_id, "status": "not_found"}
            return safe_job_details(job_id)
        state, started, ended = values
        if isinstance(state, bytes):
            state = state.decode("ascii")
        if state not in _STATES:
            return safe_job_details(job_id)
        return _details(job_id, state, _timestamp(started), _timestamp(ended))
    except Exception:  # broad-except: deliberate disclosure boundary; corrupt Redis records/client errors must never expose job data.
        _LOG.exception("Query catalog maintenance polling failed job_id=%s", job_id)
        return safe_job_details(job_id)
