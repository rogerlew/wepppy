from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Callable, Mapping

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from rq.job import JobStatus

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.mods.geneva import Geneva, GenevaNoDbError, GenevaValidationError
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.geneva_rq import (
    GENEVA_RQ_TIMEOUT,
    run_geneva_build_frequency_panel_rq,
    run_geneva_prepare_hrus_rq,
    run_geneva_run_batch_rq,
)
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.auth_actor import current_auth_actor
from wepppy.observability.correlation import current_correlation_id, normalize_correlation_id
from wepppy.rq.submission_recovery import recover_committed_enqueue, rq_submission_lock
from wepppy.weppcloud.utils.auth_tokens import get_jwt_config
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, _normalize_scopes, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response
from wepppy.rq.job_dependencies import (
    failure_tolerant_depends_on,
    reconcile_deferred_workflow,
    release_deferred_job_if_ready,
)

logger = logging.getLogger(__name__)

router = APIRouter()

CONTRACT_VERSION = "1.0.0-draft"
DEFAULT_DEPLOYMENT_REVISION = "dev"
DEPLOYMENT_REVISION_ENV = "RQ_ENGINE_DEPLOYMENT_REVISION"
GENEVA_READ_ALLOWED_SCOPES = frozenset({"rq:read", "rq:status"})
GENEVA_ENQUEUE_SCOPES = ("rq:enqueue",)
GENEVA_STATE_DOMAIN = "orchestration"
GENEVA_STATE_LOCK_RETRY_ATTEMPTS = 3
GENEVA_STATE_LOCK_RETRY_SECONDS = 0.2


def _deployment_revision() -> str:
    value = str(os.getenv(DEPLOYMENT_REVISION_ENV) or DEFAULT_DEPLOYMENT_REVISION).strip()
    return value or DEFAULT_DEPLOYMENT_REVISION


def _base_payload() -> dict[str, str]:
    return {
        "contract_version": CONTRACT_VERSION,
        "deployment_revision": _deployment_revision(),
    }


def _ensure_geneva_controller(runid: str, config: str) -> Geneva:
    wd = get_wd(runid)
    controller = Geneva.tryGetInstance(wd)
    if controller is None:
        controller = Geneva(wd, f"{config}.cfg")
    return controller


def _invalidate_geneva_preflight_timestamp(runid: str) -> None:
    wd = get_wd(runid)
    RedisPrep.getInstance(wd).remove_timestamp(TaskEnum.run_geneva)


def _extract_scopes(claims: Mapping[str, Any]) -> set[str]:
    return _normalize_scopes(claims.get("scope"), get_jwt_config().scope_separator)


def _require_geneva_read_claims(request: Request, runid: str) -> Mapping[str, Any]:
    claims = require_jwt(request)
    scopes = _extract_scopes(claims)
    if not scopes.intersection(GENEVA_READ_ALLOWED_SCOPES):
        required_text = ", ".join(sorted(GENEVA_READ_ALLOWED_SCOPES))
        raise AuthError(
            f"Token missing required scope(s): {required_text}",
            status_code=403,
            code="forbidden",
        )
    authorize_run_access(claims, runid)
    return claims


def _normalize_prepare_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    schema_version = payload.get("schema_version", 1)
    try:
        normalized_schema_version = int(schema_version)
    except (TypeError, ValueError) as exc:
        raise GenevaValidationError(
            "schema_version must equal 1",
            code="invalid_input",
            details="schema_version must equal 1",
            status_code=400,
        ) from exc
    if normalized_schema_version != 1:
        raise GenevaValidationError(
            "schema_version must equal 1",
            code="invalid_input",
            details="schema_version must equal 1",
            status_code=400,
        )

    force_rebuild = payload.get("force_rebuild", False)
    if not isinstance(force_rebuild, bool):
        raise GenevaValidationError(
            "force_rebuild must be boolean",
            code="invalid_input",
            details="force_rebuild must be boolean",
            status_code=400,
        )

    input_refs = payload.get("input_refs")
    if input_refs is not None and not isinstance(input_refs, Mapping):
        raise GenevaValidationError(
            "input_refs must be an object when provided",
            code="invalid_input",
            details="input_refs must be an object when provided",
            status_code=400,
        )

    normalized_payload: dict[str, Any] = {
        "schema_version": 1,
        "force_rebuild": force_rebuild,
    }
    if input_refs is not None:
        normalized_payload["input_refs"] = dict(input_refs)
    return normalized_payload


def _normalize_workflow_request(geneva: Geneva, payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        schema_version = int(payload.get("schema_version", 1))
    except (TypeError, ValueError) as exc:
        raise GenevaValidationError(
            "schema_version must equal 1",
            code="invalid_input",
            details="schema_version must equal 1",
            status_code=400,
        ) from exc
    if schema_version != 1:
        raise GenevaValidationError(
            "schema_version must equal 1",
            code="invalid_input",
            details="schema_version must equal 1",
            status_code=400,
        )

    prepare_raw = payload.get("prepare", {})
    panel_raw = payload.get("panel", {})
    has_run_batch_payload = "run_batch" in payload
    run_batch_raw = payload.get("run_batch", {})

    if not isinstance(prepare_raw, Mapping):
        raise GenevaValidationError(
            "prepare must be an object when provided",
            code="invalid_input",
            details="prepare must be an object when provided",
            status_code=400,
        )
    if not isinstance(panel_raw, Mapping):
        raise GenevaValidationError(
            "panel must be an object when provided",
            code="invalid_input",
            details="panel must be an object when provided",
            status_code=400,
        )

    if has_run_batch_payload and not isinstance(run_batch_raw, Mapping):
        raise GenevaValidationError(
            "run_batch must be an object",
            code="invalid_input",
            details="run_batch must be an object",
            status_code=400,
        )

    # Backward-compatible fallback: treat top-level run-batch envelope as run_batch.
    if not has_run_batch_payload:
        run_payload_keys = ("batch_id", "event_filter", "hyetograph", "runoff_model")
        if any(key in payload for key in run_payload_keys):
            run_batch_raw = {key: payload[key] for key in run_payload_keys if key in payload}

    normalized_prepare = _normalize_prepare_request(dict(prepare_raw))
    normalized_prepare["force_rebuild"] = True

    panel_payload = dict(panel_raw)
    panel_payload["schema_version"] = 1
    panel_payload["rebuild"] = True
    normalized_panel = geneva.frequency_panel_service.normalize_request(panel_payload)
    normalized_panel["rebuild"] = True

    normalized_run_batch = dict(run_batch_raw)
    normalized_run_batch.setdefault("schema_version", 1)
    geneva.batch_run_service.validate_request(geneva, normalized_run_batch)

    return {
        "schema_version": 1,
        "prepare": normalized_prepare,
        "panel": normalized_panel,
        "run_batch": normalized_run_batch,
    }


def _prepare_geneva_job(
    *,
    redis_conn: redis.Redis,
    geneva: Geneva,
    runid: str,
    config: str,
    job_id: str,
    status_message: str,
    lease_checkpoint: Callable[[], None] | None = None,
) -> None:
    active_job_id = geneva.state_payload().get("active_job_id")
    if active_job_id:
        result = reconcile_deferred_workflow(
            str(active_job_id),
            connection=redis_conn,
            association=lambda candidate: (
                tuple(candidate.args or ())[:2] == (runid, config)
                and str(candidate.origin) == "default"
                and str(candidate.func_name) in {
                    f"{func.__module__}.{func.__qualname__}"
                    for func in (
                        run_geneva_prepare_hrus_rq,
                        run_geneva_build_frequency_panel_rq,
                        run_geneva_run_batch_rq,
                    )
                }
            ),
            lease_checkpoint=lease_checkpoint,
        )
        if result.state in {"active", "mismatch"}:
            raise GenevaNoDbError(
                "A Geneva job is already active.",
                code="geneva_job_active",
                status_code=409,
            )
    geneva.mark_job_queued(job_id, status_message=status_message)


def _enqueue_geneva_job(
    *,
    runid: str,
    config: str,
    payload: Mapping[str, Any],
    func: Any,
    geneva: Geneva,
    queued_status_message: str,
) -> dict[str, str]:
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn, rq_submission_lock(
        redis_conn, f"{runid}:geneva", lifecycle_key=runid
    ) as lease:
        queue = Queue(connection=redis_conn)
        job_id = new_rq_job_id()
        _prepare_geneva_job(
            redis_conn=redis_conn,
            geneva=geneva,
            runid=runid,
            config=config,
            job_id=job_id,
            status_message=queued_status_message,
            lease_checkpoint=lease.checkpoint,
        )
        lease.checkpoint()
        job = queue.enqueue_call(
            func=func,
            args=(runid, config, dict(payload)),
            timeout=GENEVA_RQ_TIMEOUT,
            job_id=job_id,
        )

    job_id = str(job.id)
    return {
        "job_id": job_id,
        "status_url": f"/rq-engine/api/jobstatus/{job_id}",
        "message": "Job enqueued.",
    }


def _enqueue_geneva_workflow_jobs(
    *,
    runid: str,
    config: str,
    payload: Mapping[str, Any],
    geneva: Geneva,
) -> dict[str, Any]:
    prepare_payload = dict(payload.get("prepare", {}))
    panel_payload = dict(payload.get("panel", {}))
    run_batch_payload = dict(payload.get("run_batch", {}))

    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn, rq_submission_lock(
        redis_conn, f"{runid}:geneva", lifecycle_key=runid
    ) as lease:
        queue = Queue(connection=redis_conn)
        prepare_job_id = new_rq_job_id()
        queued_message = (
            "Geneva workflow queued. Preparing HRUs, building frequency panel, "
            "then running Geneva batch."
        )
        _prepare_geneva_job(
            redis_conn=redis_conn,
            geneva=geneva,
            runid=runid,
            config=config,
            job_id=prepare_job_id,
            status_message=queued_message,
            lease_checkpoint=lease.checkpoint,
        )
        lease.checkpoint()
        job_meta: dict[str, Any] = {"runid": runid}
        auth_actor = current_auth_actor()
        if auth_actor is not None:
            job_meta["auth_actor"] = auth_actor
        correlation_id = normalize_correlation_id(current_correlation_id())
        if correlation_id is not None:
            job_meta["correlation_id"] = correlation_id
        prepare_job = queue.create_job(
            func=run_geneva_prepare_hrus_rq,
            args=(runid, config, prepare_payload),
            timeout=GENEVA_RQ_TIMEOUT,
            job_id=prepare_job_id,
            meta=job_meta,
        )
        panel_job = queue.create_job(
            func=run_geneva_build_frequency_panel_rq,
            args=(runid, config, panel_payload),
            timeout=GENEVA_RQ_TIMEOUT,
            depends_on=failure_tolerant_depends_on(prepare_job),
            job_id=new_rq_job_id(),
            status=JobStatus.DEFERRED,
            meta=job_meta,
        )
        run_batch_job = queue.create_job(
            func=run_geneva_run_batch_rq,
            args=(runid, config, run_batch_payload),
            timeout=GENEVA_RQ_TIMEOUT,
            depends_on=failure_tolerant_depends_on(panel_job),
            job_id=new_rq_job_id(),
            status=JobStatus.DEFERRED,
            meta=job_meta,
        )
        pipeline = redis_conn.pipeline()
        queue._enqueue_job(prepare_job, pipeline=pipeline)
        panel_job.save(pipeline=pipeline)
        panel_job.register_dependency(pipeline=pipeline)
        run_batch_job.save(pipeline=pipeline)
        run_batch_job.register_dependency(pipeline=pipeline)
        try:
            pipeline.execute()
        except redis.RedisError:
            recovered = (
                recover_committed_enqueue(redis_conn, prepare_job.id, func=run_geneva_prepare_hrus_rq, runid=runid, origin=str(queue.name), args=(runid, config, prepare_payload)),
                recover_committed_enqueue(redis_conn, panel_job.id, func=run_geneva_build_frequency_panel_rq, runid=runid, origin=str(queue.name), args=(runid, config, panel_payload)),
                recover_committed_enqueue(redis_conn, run_batch_job.id, func=run_geneva_run_batch_rq, runid=runid, origin=str(queue.name), args=(runid, config, run_batch_payload)),
            )
            if not all(recovered):
                raise
            prepare_job, panel_job, run_batch_job = recovered

    prepare_job_id = str(prepare_job.id)
    panel_job_id = str(panel_job.id)
    run_batch_job_id = str(run_batch_job.id)
    return {
        "job_id": prepare_job_id,
        "job_ids": {
            "prepare_hrus": prepare_job_id,
            "build_frequency_panel": panel_job_id,
            "run_batch": run_batch_job_id,
        },
        "status_url": f"/rq-engine/api/jobstatus/{prepare_job_id}",
        "message": "Workflow enqueued.",
    }


def _run_state_vector(*, run_state_revision: str) -> dict[str, str | None]:
    return {
        "orchestration_revision": run_state_revision,
        "metadata_revision": None,
        "outputs_revision": None,
    }


def _state_signature(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "state_version": payload.get("state_version"),
        "enabled": payload.get("enabled"),
        "config_snapshot": payload.get("config_snapshot"),
        "status": payload.get("status"),
        "status_message": payload.get("status_message"),
        "progress": payload.get("progress"),
        "active_job_id": payload.get("active_job_id"),
        "last_job_id": payload.get("last_job_id"),
        "last_prepare_summary": payload.get("last_prepare_summary"),
        "last_run_summary": payload.get("last_run_summary"),
        "warnings": payload.get("warnings"),
        "errors": payload.get("errors"),
        "artifacts": payload.get("artifacts"),
    }


def _build_state_response(runid: str, config: str, geneva: Geneva) -> JSONResponse:
    state_payload = geneva.state_payload()
    signature = _state_signature(state_payload)
    digest = hashlib.sha256(
        json.dumps(signature, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    run_state_revision = f"runstate:{runid}:{digest}"

    response_payload = _base_payload()
    response_payload.update(
        {
            "run_state_domain": GENEVA_STATE_DOMAIN,
            "run_state_revision": run_state_revision,
            "run_state_vector": _run_state_vector(run_state_revision=run_state_revision),
            "etag": f'W/"geneva:{runid}:{digest}"',
            "runid": runid,
            "config": config,
        }
    )
    response_payload.update(state_payload)
    return JSONResponse(response_payload)


def _geneva_error_response(exc: GenevaNoDbError) -> JSONResponse:
    details = exc.details if exc.details is not None else exc.message
    return error_response(
        exc.message,
        status_code=exc.status_code,
        code=exc.code,
        details=details,
    )


def _internal_error_response(message: str, *, details: str) -> JSONResponse:
    return error_response(
        message,
        status_code=500,
        code="internal_error",
        details=details,
    )


@router.post(
    "/runs/{runid}/{config}/geneva/prepare-hrus",
    summary="Prepare Geneva HRUs",
    description=(
        "Requires JWT Bearer `rq:enqueue` plus run access. "
        "Validates and enqueues Geneva HRU preparation."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("geneva_prepare_hrus"),
    responses=agent_route_responses(
        success_code=202,
        success_description="Accepted and `job_id` returned.",
        extra={
            400: "Validation failed. Returns the canonical error payload.",
        },
    ),
)
async def prepare_hrus(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=GENEVA_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary auth contract
        logger.exception("rq-engine Geneva prepare auth failed", extra={"runid": runid, "config": config})
        return error_response(
            "Failed to authorize request",
            status_code=401,
            code="unauthorized",
            details="Failed to authorize request",
        )

    try:
        payload = await parse_request_payload(request, boolean_fields=("force_rebuild",))
        normalized_payload = _normalize_prepare_request(payload)
        geneva = _ensure_geneva_controller(runid, config)
        geneva.assert_task_guardrails()
        _invalidate_geneva_preflight_timestamp(runid)
        submission = _enqueue_geneva_job(
            runid=runid,
            config=config,
            payload=normalized_payload,
            func=run_geneva_prepare_hrus_rq,
            geneva=geneva,
            queued_status_message="Geneva HRU preparation queued.",
        )
        return JSONResponse(submission, status_code=202)
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    except Exception:  # broad-except: boundary contract with sanitized response
        logger.exception("rq-engine Geneva prepare enqueue failed", extra={"runid": runid, "config": config})
        return _internal_error_response(
            "Error preparing Geneva HRUs",
            details="Unexpected server error while preparing Geneva HRUs.",
        )


@router.post(
    "/runs/{runid}/{config}/geneva/build-frequency-panel",
    summary="Build Geneva frequency panel",
    description=(
        "Requires JWT Bearer `rq:enqueue` plus run access. "
        "Validates and enqueues Geneva frequency-panel building."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("geneva_build_frequency_panel"),
    responses=agent_route_responses(
        success_code=202,
        success_description="Accepted and `job_id` returned.",
        extra={
            400: "Validation failed. Returns the canonical error payload.",
        },
    ),
)
async def build_frequency_panel(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=GENEVA_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary auth contract
        logger.exception("rq-engine Geneva frequency-panel auth failed", extra={"runid": runid, "config": config})
        return error_response(
            "Failed to authorize request",
            status_code=401,
            code="unauthorized",
            details="Failed to authorize request",
        )

    try:
        payload = await parse_request_payload(request, boolean_fields=("rebuild",))
        geneva = _ensure_geneva_controller(runid, config)
        normalized_payload = geneva.frequency_panel_service.normalize_request(payload)
        geneva.assert_task_guardrails()
        _invalidate_geneva_preflight_timestamp(runid)
        submission = _enqueue_geneva_job(
            runid=runid,
            config=config,
            payload=normalized_payload,
            func=run_geneva_build_frequency_panel_rq,
            geneva=geneva,
            queued_status_message="Geneva frequency panel build queued.",
        )
        return JSONResponse(submission, status_code=202)
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    except Exception:  # broad-except: boundary contract with sanitized response
        logger.exception(
            "rq-engine Geneva frequency-panel enqueue failed",
            extra={"runid": runid, "config": config},
        )
        return _internal_error_response(
            "Error building Geneva frequency panel",
            details="Unexpected server error while building the Geneva frequency panel.",
        )


@router.post(
    "/runs/{runid}/{config}/geneva/run-batch",
    summary="Run Geneva batch",
    description=(
        "Requires JWT Bearer `rq:enqueue` plus run access. "
        "Validates and enqueues the Geneva batch run."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("geneva_run_batch"),
    responses=agent_route_responses(
        success_code=202,
        success_description="Accepted and `job_id` returned.",
        extra={
            400: "Validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_batch(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=GENEVA_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary auth contract
        logger.exception("rq-engine Geneva run-batch auth failed", extra={"runid": runid, "config": config})
        return error_response(
            "Failed to authorize request",
            status_code=401,
            code="unauthorized",
            details="Failed to authorize request",
        )

    try:
        payload = await parse_request_payload(request)
        geneva = _ensure_geneva_controller(runid, config)
        geneva.batch_run_service.validate_request(geneva, payload)
        geneva.assert_task_guardrails()
        submission = _enqueue_geneva_job(
            runid=runid,
            config=config,
            payload=payload,
            func=run_geneva_run_batch_rq,
            geneva=geneva,
            queued_status_message="Geneva batch run queued.",
        )
        return JSONResponse(submission, status_code=202)
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    except Exception:  # broad-except: boundary contract with sanitized response
        logger.exception("rq-engine Geneva run-batch enqueue failed", extra={"runid": runid, "config": config})
        return _internal_error_response(
            "Error running Geneva batch",
            details="Unexpected server error while running the Geneva batch.",
        )


@router.post(
    "/runs/{runid}/{config}/geneva/run-workflow",
    summary="Run Geneva workflow (prepare -> panel -> batch)",
    description=(
        "Requires JWT Bearer `rq:enqueue` plus run access. "
        "Validates and enqueues the chained Geneva workflow."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("geneva_run_workflow"),
    responses=agent_route_responses(
        success_code=202,
        success_description="Accepted and chained `job_id` / `job_ids` returned.",
        extra={
            400: "Validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_workflow(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=GENEVA_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary auth contract
        logger.exception("rq-engine Geneva run-workflow auth failed", extra={"runid": runid, "config": config})
        return error_response(
            "Failed to authorize request",
            status_code=401,
            code="unauthorized",
            details="Failed to authorize request",
        )

    try:
        payload = await parse_request_payload(request)
        geneva = _ensure_geneva_controller(runid, config)
        normalized_payload = _normalize_workflow_request(geneva, payload)
        geneva.assert_task_guardrails()
        _invalidate_geneva_preflight_timestamp(runid)
        submission = _enqueue_geneva_workflow_jobs(
            runid=runid,
            config=config,
            payload=normalized_payload,
            geneva=geneva,
        )
        return JSONResponse(submission, status_code=202)
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    except Exception:  # broad-except: boundary contract with sanitized response
        logger.exception("rq-engine Geneva run-workflow enqueue failed", extra={"runid": runid, "config": config})
        return _internal_error_response(
            "Error running Geneva workflow",
            details="Unexpected server error while running the Geneva workflow.",
        )


@router.get(
    "/runs/{runid}/{config}/geneva/state",
    summary="Read Geneva controller state",
    description=(
        "Requires JWT Bearer auth plus run access. Supports `rq:read` or "
        "`rq:status` and returns read-only Geneva state."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("geneva_state"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Read-only Geneva state returned.",
        extra={
            404: "State unavailable. Returns the canonical error payload.",
        },
    ),
)
async def get_geneva_state(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _require_geneva_read_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary auth contract
        logger.exception("rq-engine Geneva state auth failed", extra={"runid": runid, "config": config})
        return error_response(
            "Failed to authorize request",
            status_code=401,
            code="unauthorized",
            details="Failed to authorize request",
        )

    try:
        geneva = _ensure_geneva_controller(runid, config)
        return _build_state_response(runid, config, geneva)
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    except Exception:  # broad-except: boundary contract with sanitized response
        logger.exception("rq-engine Geneva state failed", extra={"runid": runid, "config": config})
        return _internal_error_response(
            "Error reading Geneva state",
            details="Unexpected server error while reading Geneva controller state.",
        )


__all__ = ["router"]
