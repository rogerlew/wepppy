from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from rq.job import Job
from starlette.datastructures import UploadFile

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices.culvert_payload_validator import (
    ValidationIssue,
    format_validation_errors,
    validate_payload_root,
)
from wepppy.microservices.shape_converter.archive_validation import (
    ArchiveLimits,
    read_upload_bytes_with_limit,
    validate_and_extract_zip_archive,
)
from wepppy.microservices.shape_converter.errors import ShapeConverterError
from wepppy.rq.culvert_rq import TIMEOUT as CULVERT_BATCH_TIMEOUT
from wepppy.rq.culvert_rq import (
    run_culvert_batch_finalize_rq,
    run_culvert_batch_rq,
    run_culvert_run_rq,
)
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.rq.job_dependencies import reconcile_deferred_workflow
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.submission_recovery import (
    RqEnqueueVerificationError,
    RqSubmissionConflict,
    rq_submission_lock,
)
from wepppy.weppcloud.utils import auth_tokens

from .auth import AuthError, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, validation_error_response

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_PAYLOAD_BYTES = 2 * 1024 * 1024 * 1024
CULVERT_BROWSE_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
CULVERT_ARCHIVE_LIMITS = ArchiveLimits(
    max_compressed_bytes=MAX_PAYLOAD_BYTES,
    max_uncompressed_bytes=6 * 1024 * 1024 * 1024,
    max_member_count=1200,
)

CULVERT_JOB_KEYS = (
    "run_culvert_batch_rq",
    "run_culvert_run_rq",
    "run_culvert_batch_finalize_rq",
)
CULVERT_ROOT_FUNCTION_BY_JOB_KEY = {
    "run_culvert_batch_rq": run_culvert_batch_rq,
    "run_culvert_run_rq": run_culvert_run_rq,
    "run_culvert_batch_finalize_rq": run_culvert_batch_finalize_rq,
}


def _culvert_job_belongs_to_batch(job: Job, batch_uuid: str) -> bool:
    allowed_funcs = {
        f"{func.__module__}.{func.__qualname__}"
        for func in (
            run_culvert_batch_rq,
            run_culvert_run_rq,
            run_culvert_batch_finalize_rq,
        )
    }
    allowed_funcs.add("wepppy.rq.culvert_rq._final_culvert_batch_complete_rq")
    if str(job.func_name) not in allowed_funcs or str(job.origin) != "batch":
        return False
    metadata = job.meta if isinstance(job.meta, dict) else {}
    args = tuple(job.args or ())
    canonical_arg_index = (
        1
        if str(job.func_name)
        == f"{run_culvert_run_rq.__module__}.{run_culvert_run_rq.__qualname__}"
        else 0
    )
    if len(args) <= canonical_arg_index or str(args[canonical_arg_index]) != batch_uuid:
        return False
    metadata_batch = str(metadata.get("culvert_batch_uuid") or "")
    return not metadata_batch or metadata_batch == batch_uuid


def _culvert_runner(batch_uuid: str) -> CulvertsRunner:
    batch_root = _resolve_culverts_root() / batch_uuid
    runner = CulvertsRunner.getInstance(str(batch_root), allow_nonexistent=True)
    if runner is None:
        runner = CulvertsRunner(str(batch_root), "culvert.cfg")
    return runner


def _canonical_batch_uuid(batch_uuid: str) -> str:
    """Return the canonical UUID spelling accepted as one batch-root child."""
    try:
        canonical = str(uuid.UUID(batch_uuid))
    except (AttributeError, ValueError) as exc:
        raise ValueError("Invalid culvert batch UUID.") from exc
    if canonical != batch_uuid:
        raise ValueError("Invalid culvert batch UUID.")
    return canonical


def _culvert_run_dir(batch_root: Path, point_id: str) -> Path:
    if (
        not point_id
        or point_id in {".", ".."}
        or Path(point_id).name != point_id
        or "/" in point_id
        or "\\" in point_id
    ):
        raise ValueError("Invalid Point_ID")
    if batch_root.is_symlink():
        raise ValueError("Invalid batch directory")
    canonical_batch_root = batch_root.resolve()
    if canonical_batch_root.parent != _resolve_culverts_root():
        raise ValueError("Invalid batch directory")
    runs_entry = canonical_batch_root / "runs"
    if runs_entry.is_symlink():
        raise ValueError("Invalid runs directory")
    runs_root = runs_entry.resolve()
    if runs_root != runs_entry:
        raise ValueError("Invalid runs directory")
    run_dir = runs_root / point_id
    if run_dir.parent != runs_root or (run_dir.exists() and run_dir.is_symlink()):
        raise ValueError("Invalid Point_ID")
    return run_dir


def _enqueue_culvert_job(
    batch_uuid: str,
    *,
    job_key: str,
    func: Any,
    args: list[str],
    meta: dict[str, str],
    before_enqueue: Callable[[], None] | None = None,
) -> str:
    batch_uuid = _canonical_batch_uuid(batch_uuid)
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        with rq_submission_lock(redis_conn, f"culvert:{batch_uuid}", lifecycle_key=batch_uuid, lifecycle_type="culvert") as lease:
            # Read the persisted receipt map only after admission is serialized.
            runner = _culvert_runner(batch_uuid)
            roots_by_job_id: dict[str, set[str]] = {}
            for prior_key, prior_job_id in runner.rq_job_ids.items():
                root_func = CULVERT_ROOT_FUNCTION_BY_JOB_KEY.get(prior_key)
                if not prior_job_id:
                    continue
                if root_func is None:
                    raise RqSubmissionConflict(
                        "Culvert receipt operation could not be verified "
                        f"(key={prior_key})."
                    )
                roots_by_job_id.setdefault(str(prior_job_id), set()).add(
                    f"{root_func.__module__}.{root_func.__qualname__}"
                )
            for prior_job_id, allowed_root_funcs in roots_by_job_id.items():
                result = reconcile_deferred_workflow(
                    str(prior_job_id),
                    connection=redis_conn,
                    association=lambda candidate: _culvert_job_belongs_to_batch(
                        candidate, batch_uuid
                    ),
                    root_association=lambda candidate, allowed=allowed_root_funcs: (
                        _culvert_job_belongs_to_batch(candidate, batch_uuid)
                        and str(candidate.func_name) in allowed
                    ),
                    lease_checkpoint=lease.checkpoint,
                )
                if result.state in {"active", "mismatch"}:
                    raise RqSubmissionConflict("A culvert batch job is already active.")
                lease.checkpoint()
            if before_enqueue is not None:
                lease.checkpoint()
                before_enqueue()
                lease.checkpoint()
            job_id = new_rq_job_id()
            runner.set_rq_job_id(job_key, job_id)
            lease.checkpoint()
            queue = Queue("batch", connection=redis_conn)
            job = queue.enqueue_call(
                func=func,
                args=args,
                timeout=CULVERT_BATCH_TIMEOUT,
                job_id=job_id,
                meta=meta,
            )
            return str(job.id)


def _mint_culvert_browse_token(batch_uuid: str, *, subject: str) -> dict[str, Any]:
    """Mint a batch-scoped browse token for /weppcloud/culverts/{uuid}/browse/*."""
    # Keep the minted token audience in lock-step with what downstream services validate.
    audience = (os.getenv("RQ_ENGINE_JWT_AUDIENCE") or "rq-engine").strip() or "rq-engine"
    return auth_tokens.issue_token(
        subject or "culvert-batch",
        audience=audience,
        runs=[batch_uuid],
        expires_in=CULVERT_BROWSE_TOKEN_TTL_SECONDS,
        extra_claims={
            "token_class": "service",
            "service_groups": ["culverts"],
            "jti": uuid.uuid4().hex,
        },
    )


@router.post(
    "/culverts-wepp-batch/",
    summary="Submit a culvert batch payload",
    description=(
        "Requires JWT Bearer scope `culvert:batch:submit`. Validates and stages uploaded payload.zip, "
        "then asynchronously enqueues culvert batch processing and returns `job_id`."
    ),
    tags=["rq-engine", "culverts"],
    operation_id=rq_operation_id("culverts_wepp_batch"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Payload accepted, batch created, and job enqueued.",
        extra={
            400: "Payload validation failed or upload constraints were not met. Returns the canonical error payload.",
        },
    ),
)
async def culverts_wepp_batch(request: Request) -> JSONResponse:
    try:
        submitter_claims = require_jwt(request, required_scopes=["culvert:batch:submit"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine culvert batch auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    culverts_root = _resolve_culverts_root()
    culvert_batch_uuid, batch_root = _reserve_batch_root(culverts_root)
    payload_zip_path = batch_root / "payload.zip"

    try:
        form = await request.form()
        upload = _extract_upload(form)
        if upload is None:
            shutil.rmtree(batch_root, ignore_errors=True)
            issues = [
                ValidationIssue(
                    code="missing_file",
                    message="payload.zip is required.",
                    path="payload.zip",
                )
            ]
            return validation_error_response(format_validation_errors(issues))

        zip_sha256 = _string_or_none(form.get("zip_sha256"))
        total_bytes = _string_or_none(form.get("total_bytes"))
        total_bytes_value = None
        if total_bytes is not None:
            try:
                total_bytes_value = int(total_bytes)
            except ValueError:
                total_bytes_value = None
            else:
                if total_bytes_value > MAX_PAYLOAD_BYTES:
                    shutil.rmtree(batch_root, ignore_errors=True)
                    issues = [
                        ValidationIssue(
                            code="payload_too_large",
                            message="payload.zip exceeds size limit.",
                            path="payload.zip",
                            detail={
                                "max_bytes": MAX_PAYLOAD_BYTES,
                                "found": total_bytes_value,
                            },
                        )
                    ]
                    return validation_error_response(format_validation_errors(issues))

        archive_name = _resolve_archive_name(upload)
        try:
            archive_bytes = await read_upload_bytes_with_limit(
                upload=upload,
                max_bytes=MAX_PAYLOAD_BYTES,
            )
        except ShapeConverterError as exc:
            shutil.rmtree(batch_root, ignore_errors=True)
            return _archive_error_response(exc)

        payload_zip_path.write_bytes(archive_bytes)
        payload_sha256 = hashlib.sha256(archive_bytes).hexdigest()
        payload_bytes = len(archive_bytes)

        size_errors = _validate_payload_size(
            zip_sha256, total_bytes, payload_sha256, payload_bytes
        )
        if size_errors:
            shutil.rmtree(batch_root, ignore_errors=True)
            return validation_error_response(format_validation_errors(size_errors))

        try:
            validate_and_extract_zip_archive(
                archive_name=archive_name,
                archive_bytes=archive_bytes,
                extraction_root=batch_root,
                limits=CULVERT_ARCHIVE_LIMITS,
                member_policy=_allow_culvert_member,
                sanitize_metadata_sidecars=False,
            )
        except ShapeConverterError as exc:
            shutil.rmtree(batch_root, ignore_errors=True)
            return _archive_error_response(exc)

        payload_issues = validate_payload_root(batch_root)
        if payload_issues:
            shutil.rmtree(batch_root, ignore_errors=True)
            return validation_error_response(format_validation_errors(payload_issues))

        topo_dir = batch_root / "topo"
        topo_dir.mkdir(parents=True, exist_ok=True)

        _write_batch_metadata(
            batch_root,
            culvert_batch_uuid,
            zip_sha256,
            total_bytes_value,
        )

        job_id = _enqueue_culvert_batch_job(culvert_batch_uuid)
        status_url = f"/rq-engine/api/jobstatus/{job_id}"
        browse_token_payload = _mint_culvert_browse_token(
            culvert_batch_uuid,
            subject=str(submitter_claims.get("sub") or "culvert-batch"),
        )
        browse_claims = browse_token_payload.get("claims", {}) or {}
        return JSONResponse(
            {
                "job_id": job_id,
                "culvert_batch_uuid": culvert_batch_uuid,
                "status_url": status_url,
                "browse_token": browse_token_payload.get("token"),
                "browse_token_expires_at": browse_claims.get("exp"),
            }
        )
    except RqSubmissionConflict as exc:
        shutil.rmtree(batch_root, ignore_errors=True)
        return error_response(str(exc), status_code=409, code="conflict")
    except RqEnqueueVerificationError as exc:
        # The exact preallocated receipt may have committed. Preserve its staged
        # inputs so either the worker or a subsequent reconciliation can proceed.
        logger.warning(
            "Culvert batch enqueue outcome could not be verified batch_uuid=%s",
            culvert_batch_uuid,
            exc_info=True,
        )
        return error_response(str(exc), status_code=503, code="enqueue_unverified")
    except Exception:
        shutil.rmtree(batch_root, ignore_errors=True)
        logger.exception("rq-engine culvert batch ingestion failed")
        return error_response("Failed to ingest culvert batch payload", status_code=500)


@router.post(
    "/culverts-wepp-batch/{batch_uuid}/retry/{point_id}",
    summary="Retry one culvert point in a batch",
    description=(
        "Requires JWT Bearer scope `culvert:batch:retry`. Validates existing batch state, "
        "then asynchronously enqueues a retry job for a single `point_id`."
    ),
    tags=["rq-engine", "culverts"],
    operation_id=rq_operation_id("culverts_retry_run"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Retry job enqueued and `job_id` returned.",
        extra={
            400: "Batch metadata is invalid or required files are missing. Returns the canonical error payload.",
            404: "Batch or point ID was not found. Returns the canonical error payload.",
        },
    ),
)
async def culverts_retry_run(
    batch_uuid: str, point_id: str, request: Request
) -> JSONResponse:
    """Retry a single culvert run within an existing batch."""
    try:
        submitter_claims = require_jwt(request, required_scopes=["culvert:batch:retry"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine culvert retry auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        batch_uuid = _canonical_batch_uuid(batch_uuid)
    except ValueError as exc:
        return error_response(str(exc), status_code=404)
    culverts_root = _resolve_culverts_root()
    batch_root = culverts_root / batch_uuid

    if not batch_root.is_dir():
        return error_response(
            f"Batch not found: {batch_uuid}",
            status_code=404,
        )

    # Validate the point_id exists in the batch
    watersheds_path = batch_root / "culverts" / "watersheds.geojson"
    if not watersheds_path.is_file():
        return error_response(
            "Batch is missing watersheds.geojson",
            status_code=400,
        )

    try:
        with watersheds_path.open("r", encoding="utf-8") as f:
            watersheds = json.load(f)
        valid_point_ids = {
            str(feat.get("properties", {}).get("Point_ID"))
            for feat in watersheds.get("features", [])
        }
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning(f"Failed to parse watersheds.geojson: {exc}")
        return error_response(
            "Failed to parse watersheds.geojson",
            status_code=400,
        )

    if point_id not in valid_point_ids:
        return error_response(
            f"Point_ID {point_id} not found in batch {batch_uuid}",
            status_code=404,
        )

    try:
        run_dir = _culvert_run_dir(batch_root, point_id)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="validation_error")

    def _clear_prior_run() -> None:
        if run_dir.is_dir():
            tombstone = run_dir.with_name(
                f".{run_dir.name}.retry-{uuid.uuid4().hex}"
            )
            os.replace(run_dir, tombstone)
            shutil.rmtree(tombstone, ignore_errors=True)
            logger.info("Removed existing run directory for retry: %s", run_dir)

    try:
        job_id = _enqueue_culvert_run_job(
            batch_uuid,
            point_id,
            before_enqueue=_clear_prior_run,
        )
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    status_url = f"/rq-engine/api/jobstatus/{job_id}"
    browse_token_payload = _mint_culvert_browse_token(
        batch_uuid,
        subject=str(submitter_claims.get("sub") or "culvert-batch"),
    )
    browse_claims = browse_token_payload.get("claims", {}) or {}
    return JSONResponse(
        {
            "job_id": job_id,
            "culvert_batch_uuid": batch_uuid,
            "point_id": point_id,
            "status_url": status_url,
            "browse_token": browse_token_payload.get("token"),
            "browse_token_expires_at": browse_claims.get("exp"),
        }
    )


@router.post(
    "/culverts-wepp-batch/{batch_uuid}/finalize",
    summary="Finalize a culvert batch",
    description=(
        "Requires JWT Bearer scope `culvert:batch:retry`. Asynchronously enqueues the "
        "batch finalizer to rebuild `runs_manifest.md`, summary totals, and archive artifacts."
    ),
    tags=["rq-engine", "culverts"],
    operation_id=rq_operation_id("culverts_finalize_batch"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Finalizer job enqueued and `job_id` returned.",
        extra={
            404: "Batch root was not found. Returns the canonical error payload.",
        },
    ),
)
async def culverts_finalize_batch(batch_uuid: str, request: Request) -> JSONResponse:
    """Enqueue finalizer for an existing culvert batch."""
    try:
        submitter_claims = require_jwt(request, required_scopes=["culvert:batch:retry"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine culvert finalize auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        batch_uuid = _canonical_batch_uuid(batch_uuid)
    except ValueError as exc:
        return error_response(str(exc), status_code=404)
    culverts_root = _resolve_culverts_root()
    batch_root = culverts_root / batch_uuid
    if not batch_root.is_dir():
        return error_response(
            f"Batch not found: {batch_uuid}",
            status_code=404,
        )

    try:
        job_id = _enqueue_culvert_finalize_job(batch_uuid)
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    status_url = f"/rq-engine/api/jobstatus/{job_id}"
    browse_token_payload = _mint_culvert_browse_token(
        batch_uuid,
        subject=str(submitter_claims.get("sub") or "culvert-batch"),
    )
    browse_claims = browse_token_payload.get("claims", {}) or {}
    return JSONResponse(
        {
            "job_id": job_id,
            "culvert_batch_uuid": batch_uuid,
            "status_url": status_url,
            "browse_token": browse_token_payload.get("token"),
            "browse_token_expires_at": browse_claims.get("exp"),
        }
    )


def _enqueue_culvert_run_job(
    culvert_batch_uuid: str,
    point_id: str,
    *,
    before_enqueue: Callable[[], None] | None = None,
) -> str:
    """Enqueue a single culvert run job."""
    runid = f"culvert;;{culvert_batch_uuid};;{point_id}"
    return _enqueue_culvert_job(
        culvert_batch_uuid,
        job_key="run_culvert_run_rq",
        func=run_culvert_run_rq,
        args=[runid, culvert_batch_uuid, point_id],
        meta={
            "culvert_batch_uuid": culvert_batch_uuid,
            "point_id": point_id,
            "runid": runid,
        },
        before_enqueue=before_enqueue,
    )


def _enqueue_culvert_finalize_job(culvert_batch_uuid: str) -> str:
    """Enqueue culvert batch finalizer to refresh summary artifacts."""
    return _enqueue_culvert_job(
        culvert_batch_uuid,
        job_key="run_culvert_batch_finalize_rq",
        func=run_culvert_batch_finalize_rq,
        args=[culvert_batch_uuid],
        meta={"culvert_batch_uuid": culvert_batch_uuid},
    )


def _resolve_culverts_root() -> Path:
    return Path(os.getenv("CULVERTS_ROOT", "/wc1/culverts")).resolve()


def _reserve_batch_root(culverts_root: Path) -> tuple[str, Path]:
    culverts_root.mkdir(parents=True, exist_ok=True)
    while True:
        culvert_batch_uuid = str(uuid.uuid4())
        batch_root = culverts_root / culvert_batch_uuid
        try:
            batch_root.mkdir()
            return culvert_batch_uuid, batch_root
        except FileExistsError:
            continue


def _extract_upload(form: Any) -> Optional[UploadFile]:
    for key in ("payload.zip", "payload", "file"):
        upload = form.get(key)
        if isinstance(upload, UploadFile):
            return upload
    for value in getattr(form, "values", lambda: [])():
        if isinstance(value, UploadFile):
            return value
    return None


def _string_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_archive_name(upload: UploadFile) -> str:
    filename = _string_or_none(getattr(upload, "filename", None))
    if filename is None:
        return "payload.zip"
    return filename


def _allow_culvert_member(_member: Any, _normalized_path: Any) -> None:
    # Archive safety checks run in the shared validator; payload semantics remain in
    # culvert_payload_validator.validate_payload_root().
    return


def _archive_error_response(exc: ShapeConverterError) -> JSONResponse:
    if exc.status_code == 413:
        return error_response(
            exc.message,
            status_code=exc.status_code,
            code=exc.code,
            details=exc.details,
        )

    issue_detail = {"details": exc.details} if exc.details else None
    issue = ValidationIssue(
        code=exc.code,
        message=exc.message,
        path="payload.zip",
        detail=issue_detail,
    )
    return validation_error_response(format_validation_errors([issue]))


def _validate_payload_size(
    zip_sha256: Optional[str],
    total_bytes: Optional[str],
    payload_sha256: str,
    payload_bytes: int,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if zip_sha256 and zip_sha256.lower() != payload_sha256.lower():
        issues.append(
            ValidationIssue(
                code="zip_sha256_mismatch",
                message="zip_sha256 does not match uploaded payload.",
                path="zip_sha256",
            )
        )

    if total_bytes is not None:
        try:
            expected = int(total_bytes)
        except ValueError:
            issues.append(
                ValidationIssue(
                    code="invalid_total_bytes",
                    message="total_bytes must be an integer.",
                    path="total_bytes",
                )
            )
        else:
            if expected > MAX_PAYLOAD_BYTES:
                issues.append(
                    ValidationIssue(
                        code="payload_too_large",
                        message="payload.zip exceeds size limit.",
                        path="payload.zip",
                        detail={"max_bytes": MAX_PAYLOAD_BYTES, "found": expected},
                    )
                )
            if expected != payload_bytes:
                issues.append(
                    ValidationIssue(
                        code="total_bytes_mismatch",
                        message="total_bytes does not match uploaded payload.",
                        path="total_bytes",
                    )
                )

    if payload_bytes > MAX_PAYLOAD_BYTES:
        issues.append(
            ValidationIssue(
                code="payload_too_large",
                message="payload.zip exceeds size limit.",
                path="payload.zip",
                detail={"max_bytes": MAX_PAYLOAD_BYTES, "found": payload_bytes},
            )
        )

    return issues


def _write_batch_metadata(
    batch_root: Path,
    culvert_batch_uuid: str,
    zip_sha256: Optional[str],
    total_bytes: Optional[int],
) -> None:
    payload: dict[str, Any] = {
        "culvert_batch_uuid": culvert_batch_uuid,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if zip_sha256:
        payload["zip_sha256"] = zip_sha256
    if total_bytes is not None:
        payload["total_bytes"] = total_bytes

    metadata_path = batch_root / "batch_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def _enqueue_culvert_batch_job(culvert_batch_uuid: str) -> str:
    return _enqueue_culvert_job(
        culvert_batch_uuid,
        job_key="run_culvert_batch_rq",
        func=run_culvert_batch_rq,
        args=[culvert_batch_uuid],
        meta={"culvert_batch_uuid": culvert_batch_uuid},
    )


__all__ = ["router"]
