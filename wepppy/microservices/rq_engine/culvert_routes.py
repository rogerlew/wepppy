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
from wepppy.microservices.culvert_payload_validator import (
    ValidationIssue,
    format_validation_errors,
    validate_payload_root,
    validate_zip_members,
)
from wepppy.rq.culvert_rq import TIMEOUT as CULVERT_BATCH_TIMEOUT
from wepppy.rq.culvert_rq import run_culvert_batch_rq

from .responses import error_response, validation_error_response

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_PAYLOAD_BYTES = 2 * 1024 * 1024 * 1024


@router.post("/culverts-wepp-batch/")
async def culverts_wepp_batch(request: Request) -> JSONResponse:
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
        status_url = f"/rq-engine/api/jobstatus/{job_id}"
        return JSONResponse(
            {
                "job_id": job_id,
                "culvert_batch_uuid": culvert_batch_uuid,
                "status_url": status_url,
            }
        )
    except Exception:
        shutil.rmtree(batch_root, ignore_errors=True)
        logger.exception("rq-engine culvert batch ingestion failed")
        return error_response("Failed to ingest culvert batch payload")


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
