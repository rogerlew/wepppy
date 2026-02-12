from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from starlette.datastructures import UploadFile

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.microservices.culvert_payload_validator import (
    ValidationIssue,
    format_validation_errors,
    validate_payload_root,
    validate_zip_members,
)
from wepppy.rq.culvert_rq import TIMEOUT as CULVERT_BATCH_TIMEOUT
from wepppy.rq.culvert_rq import (
    run_culvert_batch_finalize_rq,
    run_culvert_batch_rq,
    run_culvert_run_rq,
)
from wepppy.weppcloud.utils import auth_tokens

from .auth import AuthError, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, error_response_with_traceback, validation_error_response

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_PAYLOAD_BYTES = 2 * 1024 * 1024 * 1024
CULVERT_BROWSE_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
CULVERT_BATCH_RQ_JOB_KEY = "run_culvert_batch_rq"


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
        return error_response_with_traceback("Failed to authorize request", status_code=401)

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

        payload_sha256, payload_bytes = await _save_upload_file(upload, payload_zip_path)

        zip_member_errors = _validate_zip_archive(payload_zip_path)
        size_errors = _validate_payload_size(
            zip_sha256, total_bytes, payload_sha256, payload_bytes
        )
        if zip_member_errors or size_errors:
            shutil.rmtree(batch_root, ignore_errors=True)
            errors = format_validation_errors(zip_member_errors + size_errors)
            return validation_error_response(errors)

        _extract_zip(payload_zip_path, batch_root)

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
        try:
            runner = CulvertsRunner.getInstance(str(batch_root), allow_nonexistent=True)
            if runner is None:
                runner = CulvertsRunner(str(batch_root), "culvert.cfg")
            runner.set_rq_job_id(CULVERT_BATCH_RQ_JOB_KEY, job_id)
        except Exception:
            logger.warning(
                "rq-engine culvert batch: failed to persist parent job id for %s",
                culvert_batch_uuid,
                exc_info=True,
            )
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
    except Exception:
        shutil.rmtree(batch_root, ignore_errors=True)
        logger.exception("rq-engine culvert batch ingestion failed")
        return error_response_with_traceback("Failed to ingest culvert batch payload")


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
        return error_response_with_traceback("Failed to authorize request", status_code=401)

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

    # Clean up existing run directory for a fresh retry
    run_dir = batch_root / "runs" / point_id
    if run_dir.is_dir():
        shutil.rmtree(run_dir, ignore_errors=True)
        logger.info(f"Removed existing run directory for retry: {run_dir}")

    job_id = _enqueue_culvert_run_job(batch_uuid, point_id)
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
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    culverts_root = _resolve_culverts_root()
    batch_root = culverts_root / batch_uuid
    if not batch_root.is_dir():
        return error_response(
            f"Batch not found: {batch_uuid}",
            status_code=404,
        )

    job_id = _enqueue_culvert_finalize_job(batch_uuid)
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


def _enqueue_culvert_run_job(culvert_batch_uuid: str, point_id: str) -> str:
    """Enqueue a single culvert run job."""
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    runid = f"culvert;;{culvert_batch_uuid};;{point_id}"
    with redis.Redis(**conn_kwargs) as redis_conn:
        q = Queue("batch", connection=redis_conn)
        job = q.enqueue_call(
            func=run_culvert_run_rq,
            args=[runid, culvert_batch_uuid, point_id],
            timeout=CULVERT_BATCH_TIMEOUT,
        )
        job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        job.meta["point_id"] = point_id
        job.meta["runid"] = runid
        job.save()
    return job.id


def _enqueue_culvert_finalize_job(culvert_batch_uuid: str) -> str:
    """Enqueue culvert batch finalizer to refresh summary artifacts."""
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        q = Queue("batch", connection=redis_conn)
        job = q.enqueue_call(
            func=run_culvert_batch_finalize_rq,
            args=[culvert_batch_uuid],
            timeout=CULVERT_BATCH_TIMEOUT,
        )
        job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        job.save()
    return job.id


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


async def _save_upload_file(upload: UploadFile, dest: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    total_bytes = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as handle:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            hasher.update(chunk)
            total_bytes += len(chunk)
    await upload.close()
    return hasher.hexdigest(), total_bytes


def _validate_zip_archive(zip_path: Path) -> list[ValidationIssue]:
    if not zipfile.is_zipfile(zip_path):
        return [
            ValidationIssue(
                code="invalid_zip",
                message="Uploaded file is not a zip archive.",
                path="payload.zip",
            )
        ]
    with zipfile.ZipFile(zip_path) as archive:
        members = [member.filename for member in archive.infolist()]
    return validate_zip_members(members)


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


def _extract_zip(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        dest_root = dest.resolve()
        for member in archive.infolist():
            target = (dest_root / member.filename).resolve()
            try:
                target.relative_to(dest_root)
            except ValueError as exc:
                raise ValueError("Zip member is outside extraction root.") from exc
        archive.extractall(dest)


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
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        q = Queue("batch", connection=redis_conn)
        job = q.enqueue_call(
            func=run_culvert_batch_rq,
            args=[culvert_batch_uuid],
            timeout=CULVERT_BATCH_TIMEOUT,
        )
        job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        job.save()
    return job.id


__all__ = ["router"]
