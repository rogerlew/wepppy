"""RQ task wrappers for Geneva task endpoints."""

from __future__ import annotations

from typing import Any, Mapping

from rq import get_current_job

from wepppy.nodb.mods.geneva import Geneva
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.utils.helpers import get_wd

GENEVA_RQ_TIMEOUT: int = 43_200


def _ensure_geneva_controller(wd: str, cfg_fn: str) -> Geneva:
    controller = Geneva.tryGetInstance(wd)
    if controller is None:
        controller = Geneva(wd, cfg_fn)
    return controller


def _current_job_id() -> str:
    job = get_current_job()
    if job is None or getattr(job, "id", None) in (None, ""):
        return "unknown-job-id"
    return str(job.id)


@with_exception_logging
def run_geneva_prepare_hrus_rq(
    runid: str,
    config: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wd = get_wd(runid)
    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")

    request_payload = dict(payload or {})
    force_rebuild = bool(request_payload.get("force_rebuild", False))
    input_refs_raw = request_payload.get("input_refs")
    input_refs = dict(input_refs_raw) if isinstance(input_refs_raw, dict) else None

    job_id = _current_job_id()
    geneva.mark_job_started(job_id, status_message="Preparing Geneva HRUs...")
    try:
        return geneva.prepare_hrus(
            force_rebuild=force_rebuild,
            input_refs=input_refs,
        )
    finally:
        geneva.mark_job_finished(job_id)


@with_exception_logging
def run_geneva_build_frequency_panel_rq(
    runid: str,
    config: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wd = get_wd(runid)
    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")

    request_payload = geneva.frequency_panel_service.normalize_request(payload or {})

    job_id = _current_job_id()
    geneva.mark_job_started(job_id, status_message="Building Geneva frequency panel...")
    try:
        return geneva.build_frequency_panel(
            durations_minutes=request_payload.get("durations_minutes"),
            ari_years=request_payload.get("ari_years"),
            rebuild=bool(request_payload.get("rebuild", False)),
            sources=request_payload.get("sources"),
        )
    finally:
        geneva.mark_job_finished(job_id)


@with_exception_logging
def run_geneva_run_batch_rq(
    runid: str,
    config: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wd = get_wd(runid)
    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")

    request_payload = dict(payload or {})

    job_id = _current_job_id()
    geneva.mark_job_started(job_id, status_message="Running Geneva storm batch...")
    try:
        return geneva.run_batch(request_payload)
    finally:
        geneva.mark_job_finished(job_id)


__all__ = [
    "GENEVA_RQ_TIMEOUT",
    "run_geneva_prepare_hrus_rq",
    "run_geneva_build_frequency_panel_rq",
    "run_geneva_run_batch_rq",
]
