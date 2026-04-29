"""RQ task wrappers for Geneva task endpoints."""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping

from rq import get_current_job

from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.mods.geneva import Geneva
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.utils.helpers import get_wd

GENEVA_RQ_TIMEOUT: int = 43_200
GENEVA_STATE_LOCK_RETRY_ATTEMPTS: int = 5
GENEVA_STATE_LOCK_RETRY_SECONDS: float = 1.0

LOGGER = logging.getLogger(__name__)


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


def _best_effort_state_update(
    geneva: Geneva,
    *,
    action_name: str,
    callback: Any,
) -> None:
    for attempt in range(1, GENEVA_STATE_LOCK_RETRY_ATTEMPTS + 1):
        try:
            callback()
            return
        except NoDbAlreadyLockedError as exc:
            if attempt >= GENEVA_STATE_LOCK_RETRY_ATTEMPTS:
                LOGGER.warning(
                    "Geneva state update skipped after lock retries: %s (%s)",
                    action_name,
                    exc,
                )
                return
            LOGGER.info(
                "Geneva state lock busy for %s; retrying (%d/%d)",
                action_name,
                attempt,
                GENEVA_STATE_LOCK_RETRY_ATTEMPTS,
            )
            time.sleep(GENEVA_STATE_LOCK_RETRY_SECONDS)


def _backfill_legacy_init_sbs_timestamp(prep: RedisPrep) -> None:
    """Ensure legacy runs with SBS enabled have an init_sbs_map timestamp.

    Older runs may have attrs:has_sbs=true but no timestamps:init_sbs_map.
    Geneva preflight freshness requires that timestamp when SBS is present.
    """
    if not prep.has_sbs:
        return
    if prep[TaskEnum.init_sbs_map] is not None:
        return

    fallback_ts = prep[TaskEnum.landuse_map]
    if fallback_ts is None:
        fallback_ts = prep[TaskEnum.build_landuse]

    if fallback_ts is None:
        prep.timestamp(TaskEnum.init_sbs_map)
        return

    prep[TaskEnum.init_sbs_map.value] = int(fallback_ts)


@with_exception_logging
def run_geneva_prepare_hrus_rq(
    runid: str,
    config: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wd = get_wd(runid)
    clear_nodb_file_cache(runid, pup_relpath="geneva.nodb")
    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")

    request_payload = dict(payload or {})
    force_rebuild = bool(request_payload.get("force_rebuild", False))
    input_refs_raw = request_payload.get("input_refs")
    input_refs = dict(input_refs_raw) if isinstance(input_refs_raw, dict) else None

    job_id = _current_job_id()
    _best_effort_state_update(
        geneva,
        action_name="mark_job_started:prepare_hrus",
        callback=lambda: geneva.mark_job_started(job_id, status_message="Preparing Geneva HRUs..."),
    )
    try:
        return geneva.prepare_hrus(
            force_rebuild=force_rebuild,
            input_refs=input_refs,
        )
    finally:
        _best_effort_state_update(
            geneva,
            action_name="mark_job_finished:prepare_hrus",
            callback=lambda: geneva.mark_job_finished(job_id),
        )


@with_exception_logging
def run_geneva_build_frequency_panel_rq(
    runid: str,
    config: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wd = get_wd(runid)
    clear_nodb_file_cache(runid, pup_relpath="geneva.nodb")
    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")

    request_payload = geneva.frequency_panel_service.normalize_request(payload or {})

    job_id = _current_job_id()
    _best_effort_state_update(
        geneva,
        action_name="mark_job_started:build_frequency_panel",
        callback=lambda: geneva.mark_job_started(
            job_id,
            status_message="Building Geneva frequency panel...",
        ),
    )
    try:
        return geneva.build_frequency_panel(
            durations_minutes=request_payload.get("durations_minutes"),
            ari_years=request_payload.get("ari_years"),
            rebuild=bool(request_payload.get("rebuild", False)),
            sources=request_payload.get("sources"),
            distribution_type=str(request_payload.get("distribution_type") or "neh4_type_b"),
        )
    finally:
        _best_effort_state_update(
            geneva,
            action_name="mark_job_finished:build_frequency_panel",
            callback=lambda: geneva.mark_job_finished(job_id),
        )


@with_exception_logging
def run_geneva_run_batch_rq(
    runid: str,
    config: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wd = get_wd(runid)
    clear_nodb_file_cache(runid, pup_relpath="geneva.nodb")
    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")

    request_payload = dict(payload or {})

    job_id = _current_job_id()
    _best_effort_state_update(
        geneva,
        action_name="mark_job_started:run_batch",
        callback=lambda: geneva.mark_job_started(job_id, status_message="Running Geneva storm batch..."),
    )
    try:
        result = geneva.run_batch(request_payload)
        prep = RedisPrep.getInstance(wd)
        _backfill_legacy_init_sbs_timestamp(prep)
        prep.timestamp(TaskEnum.run_geneva)
        return result
    finally:
        _best_effort_state_update(
            geneva,
            action_name="mark_job_finished:run_batch",
            callback=lambda: geneva.mark_job_finished(job_id),
        )


__all__ = [
    "GENEVA_RQ_TIMEOUT",
    "run_geneva_prepare_hrus_rq",
    "run_geneva_build_frequency_panel_rq",
    "run_geneva_run_batch_rq",
]
