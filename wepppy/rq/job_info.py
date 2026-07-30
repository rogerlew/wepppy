from __future__ import annotations

"""Helpers for introspecting RQ job trees and reporting aggregated status."""

from datetime import datetime, timezone
import hashlib
import math
import re
from typing import Any, Dict, List, MutableMapping, Sequence, Tuple

import redis
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.utils import utcnow

from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)
UNKNOWN_PROGRESS_UPDATED_AT = "1970-01-01T00:00:00Z"


def _resolve_runid(job: Job) -> str | None:
    meta = job.meta if isinstance(job.meta, dict) else {}
    runid = meta.get("runid")
    if runid:
        return str(runid)

    args = list(getattr(job, "args", None) or [])
    if args and isinstance(args[0], str):
        candidate = args[0].strip()
        if candidate:
            return candidate
    return None


def _extract_exc_info(job: Job) -> str | None:
    meta = job.meta if isinstance(job.meta, dict) else {}
    if isinstance(meta.get("error"), dict):
        return None
    exc_info = meta.get("exc_string")
    if isinstance(exc_info, str) and exc_info.strip():
        return exc_info

    fallback = getattr(job, "exc_info", None)
    if isinstance(fallback, str) and fallback.strip():
        return fallback

    return None


def recursive_get_job_details(job: Job, redis_conn: redis.Redis, now: datetime) -> Dict[str, Any]:
    """Recursively fetch job details including any children jobs."""
    elapsed_s = None
    if job.started_at:
        if job.ended_at:
            elapsed_s = (job.ended_at - job.started_at).total_seconds()
        else:
            elapsed_s = (now - job.started_at).total_seconds()

    culvert_batch_uuid = (
        job.meta.get("culvert_batch_uuid") if isinstance(job.meta, dict) else None
    )
    job_info: Dict[str, Any] = {
        "job_id": job.id,
        "runid": _resolve_runid(job),
        "status": job.get_status(),
        "result": job.result,
        "started_at": str(job.started_at) if job.started_at else None,
        "ended_at": str(job.ended_at) if job.ended_at else None,
        "description": job.description,
        "elapsed_s": elapsed_s,
        "exc_info": _extract_exc_info(job),
        "auth_actor": None,
        "culvert_batch_uuid": (
            str(culvert_batch_uuid) if culvert_batch_uuid else None
        ),
        "children": {}
    }
    controlled_error = job.meta.get("error") if isinstance(job.meta, dict) else None
    if isinstance(controlled_error, dict):
        job_info["error"] = controlled_error
        error_id = job.meta.get("error_id")
        if error_id:
            job_info["error_id"] = str(error_id)
    conditioning_diagnostics = (
        job.meta.get("conditioning_diagnostics")
        if isinstance(job.meta, dict)
        else None
    )
    if isinstance(conditioning_diagnostics, dict):
        job_info["_conditioning_diagnostics"] = conditioning_diagnostics
    if job.meta.get("conditioning_diagnostics_required") is True:
        job_info["_conditioning_diagnostics_required"] = True

    for key, child_job_id in job.meta.items():
        if key.startswith('jobs:'):
            job_order = key.split(',')[0].split(':')[1]
            try:
                child_job = Job.fetch(child_job_id, connection=redis_conn)
                child_job_info = recursive_get_job_details(child_job, redis_conn, now) if child_job else None
            except NoSuchJobError:
                child_job_info = None
            job_info.setdefault("children", {}).setdefault(job_order, []).append(child_job_info)

    child_details = [
        detail
        for group in job_info["children"].values()
        for detail in group
        if isinstance(detail, dict)
    ]
    failed_children = [detail for detail in child_details if detail.get("status") == "failed"]
    if failed_children:
        job_info["status"] = "failed"
        controlled_child = next(
            (detail for detail in failed_children if isinstance(detail.get("error"), dict)),
            None,
        )
        if controlled_child is not None:
            job_info["error"] = controlled_child["error"]
            job_info["error_id"] = controlled_child.get("error_id")
            job_info["exc_info"] = None

    return job_info

def get_wepppy_rq_job_info(job_id: str) -> Dict[str, Any]:
    """Return the recursive job tree for a single job id."""
    now = utcnow()
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            return {"job_id": job_id, "status": "not_found"}

        if not job:
            return {"job_id": job_id, "status": "not_found"}

        details = recursive_get_job_details(job, redis_conn, now)
        _strip_private_conditioning_metadata(details)
        _overlay_conditioning_diagnostics_failure(
            details, get_wepppy_rq_job_status(job_id)
        )
        return details


def get_wepppy_rq_jobs_info(job_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch job information for multiple job ids using a single Redis session."""

    if not job_ids:
        return {}

    normalized_ids: list[str] = []
    seen_ids: set[str] = set()
    for raw in job_ids:
        if raw is None:
            continue
        job_id = str(raw).strip()
        if not job_id or job_id in seen_ids:
            continue
        seen_ids.add(job_id)
        normalized_ids.append(job_id)

    if not normalized_ids:
        return {}

    now = utcnow()
    results: Dict[str, Dict[str, Any]] = {}

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        for job_id in normalized_ids:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
            except NoSuchJobError:
                results[job_id] = {"job_id": job_id, "status": "not_found"}
                continue
            except Exception as exc:  # pragma: no cover - defensive guard
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/job_info.py:106", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                results[job_id] = {
                    "job_id": job_id,
                    "status": "error",
                    "exc_info": str(exc),
                }
                continue

            if not job:
                results[job_id] = {"job_id": job_id, "status": "not_found"}
                continue

            try:
                details = recursive_get_job_details(job, redis_conn, now)
                _strip_private_conditioning_metadata(details)
                _overlay_conditioning_diagnostics_failure(
                    details, get_wepppy_rq_job_status(job_id)
                )
                results[job_id] = details
            except Exception as exc:  # pragma: no cover - defensive guard
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/job_info.py:120", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                results[job_id] = {
                    "job_id": job_id,
                    "status": "error",
                    "exc_info": str(exc),
                }

    return results


def _strip_private_conditioning_metadata(job_info: MutableMapping[str, Any]) -> None:
    job_info.pop("_conditioning_diagnostics", None)
    job_info.pop("_conditioning_diagnostics_required", None)
    for group in job_info.get("children", {}).values():
        for child in group:
            if isinstance(child, MutableMapping):
                _strip_private_conditioning_metadata(child)


def _overlay_conditioning_diagnostics_failure(
    job_info: MutableMapping[str, Any],
    status: MutableMapping[str, Any],
) -> None:
    error = status.get("error")
    if not (
        status.get("status") == "failed"
        and isinstance(error, dict)
        and error.get("code") == "wbt_conditioning_diagnostics_invalid"
    ):
        return
    job_info["status"] = "failed"
    job_info["error"] = error
    job_info["error_id"] = status.get("error_id")
    job_info["exc_info"] = None


def _flatten_job_tree(job_info: MutableMapping[str, Any]) -> Tuple[List[Any], List[Any], List[Any]]:
    """Recursively traverse the job tree, collecting statuses, end times, and start times."""
    statuses: List[Any] = [job_info['status']]
    end_times: List[Any] = [job_info['ended_at']]
    start_times: List[Any] = [job_info.get('started_at')]

    # Recursively process children
    for order_key in job_info.get('children', {}):
        for child_job in job_info['children'][order_key]:
            if child_job:  # Child job could be None if not found
                child_statuses, child_end_times, child_start_times = _flatten_job_tree(child_job)
                statuses.extend(child_statuses)
                end_times.extend(child_end_times)
                start_times.extend(child_start_times)

    return statuses, end_times, start_times


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_timestamp_iso(*values: Any) -> str | None:
    latest: datetime | None = None
    for raw in values:
        parsed = _parse_datetime(raw)
        if parsed is None:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    if latest is None:
        return None
    return latest.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_wepppy_rq_job_status(job_id: str) -> Dict[str, Any]:
    """Return an aggregated status summary for a job tree rooted at ``job_id``."""
    now = utcnow()
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            return {"job_id": job_id, "status": "not_found"}

        if not job:
            return {"job_id": job_id, "status": "not_found"}

        all_jobs_tree = recursive_get_job_details(job, redis_conn, now)

        # Walk the job tree to collect all statuses and end times
        statuses, end_times, started_times = _flatten_job_tree(all_jobs_tree)

        # Active descendants keep a job tree non-terminal. Once every job is
        # terminal, any descendant failure determines the aggregate outcome.
        status_priority = ['started', 'queued', 'deferred', 'scheduled', 'failed', 'stopped', 'canceled']
        aggregated_status = 'finished'  # Default to finished
        for status in status_priority:
            if status in statuses:
                aggregated_status = status
                break

        if aggregated_status == 'finished':
            assert all(s == 'finished' for s in statuses), f"Inconsistent statuses for finished aggregation: {statuses}"

        # Find the latest 'ended_at' timestamp, but only if all jobs have completed.
        total_jobs_count = len(statuses)
        valid_end_times = [t for t in end_times if t]
        valid_started_times = [t for t in started_times if t]

        if len(valid_end_times) == total_jobs_count:
            last_ended_at = _latest_timestamp_iso(*valid_end_times)
        else:
            last_ended_at = None

        completed_jobs = sum(
            1
            for status in statuses
            if str(status or "").strip().lower() in {'finished', 'failed', 'stopped', 'canceled'}
        )
        progress_total = max(1, total_jobs_count)
        progress_updated_at = _latest_timestamp_iso(*valid_end_times, *valid_started_times) or UNKNOWN_PROGRESS_UPDATED_AT

        response = {
            "job_id": job.id,
            "runid": _resolve_runid(job),
            "status": aggregated_status,
            "started_at": str(job.started_at) if job.started_at else None,
            "ended_at": last_ended_at,
            "progress": {
                "completed": completed_jobs,
                "total": progress_total,
                "unit": "jobs",
                "percent": round((completed_jobs / progress_total) * 100.0, 2),
                "updated_at": progress_updated_at,
            },
        }
        diagnostics = []
        diagnostics_required = False
        registered_job_ids = set()
        stack = [all_jobs_tree]
        while stack:
            detail = stack.pop()
            detail_job_id = detail.get("job_id")
            if isinstance(detail_job_id, str):
                registered_job_ids.add(detail_job_id)
            diagnostics_required = (
                diagnostics_required
                or detail.get("_conditioning_diagnostics_required") is True
            )
            candidate = detail.get("_conditioning_diagnostics")
            if isinstance(candidate, dict):
                diagnostics.append(
                    (
                        candidate,
                        detail.get("job_id"),
                        detail.get("_conditioning_diagnostics_required") is True,
                    )
                )
            for group in detail.get("children", {}).values():
                stack.extend(child for child in group if isinstance(child, dict))
        if len(diagnostics) == 1:
            candidate, owner_job_id, owner_requires_diagnostics = diagnostics[0]
            expected_keys = {
                "schema_version", "root_job_id", "producer_job_id",
                "operation_id", "method", "elevation_unit", "maximum_raise",
                "maximum_cut", "summary",
            }
            if (
                set(candidate) == expected_keys
                and candidate.get("schema_version") == 1
                and candidate.get("root_job_id") == job.id
                and candidate.get("producer_job_id") in registered_job_ids
                and candidate.get("producer_job_id") == owner_job_id
                and owner_requires_diagnostics
                and isinstance(candidate.get("operation_id"), str)
                and re.fullmatch(r"[0-9a-f]{32}", candidate["operation_id"]) is not None
                and candidate.get("method") in {"fill", "breach", "breach_least_cost", "topaz"}
                and candidate.get("elevation_unit") == "m"
                and all(
                    not isinstance(candidate.get(key), bool)
                    and isinstance(candidate.get(key), (int, float))
                    and math.isfinite(float(candidate[key]))
                    and candidate[key] >= 0
                    for key in ("maximum_raise", "maximum_cut")
                )
                and isinstance(candidate.get("summary"), str)
                and 1 <= len(candidate["summary"]) <= 1000
                and all(char.isprintable() or char == " " for char in candidate["summary"])
            ):
                if aggregated_status == "finished":
                    response["conditioning_diagnostics"] = candidate
            elif diagnostics_required and aggregated_status == "finished":
                error_id = hashlib.sha256(
                    f"{job.id}:wbt_conditioning_diagnostics_invalid".encode()
                ).hexdigest()[:32]
                response["status"] = "failed"
                response["error"] = {
                    "code": "wbt_conditioning_diagnostics_invalid",
                    "message": "Channel delineation stopped because terrain-conditioning diagnostics could not be verified. No successful channel result was published. Build channels again; if the problem continues, contact support with the Error ID.",
                    "details": {"reason": "inconsistent"},
                }
                response["error_id"] = error_id
                __import__("logging").getLogger(__name__).error(
                    "Invalid aggregate WBT diagnostics [error_id=%s job_id=%s reason=inconsistent]",
                    error_id,
                    job.id,
                )
        elif diagnostics_required and aggregated_status == "finished":
            error_id = hashlib.sha256(
                f"{job.id}:wbt_conditioning_diagnostics_invalid".encode()
            ).hexdigest()[:32]
            response["status"] = "failed"
            response["error"] = {
                "code": "wbt_conditioning_diagnostics_invalid",
                "message": "Channel delineation stopped because terrain-conditioning diagnostics could not be verified. No successful channel result was published. Build channels again; if the problem continues, contact support with the Error ID.",
                "details": {
                    "reason": "missing" if not diagnostics else "inconsistent"
                },
            }
            response["error_id"] = error_id
            __import__("logging").getLogger(__name__).error(
                "Invalid aggregate WBT diagnostics [error_id=%s job_id=%s reason=%s]",
                error_id,
                job.id,
                response["error"]["details"]["reason"],
            )
        return response
