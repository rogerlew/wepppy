from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename


class UploadError(Exception):
    """Raised when an upload validation or post-save check fails."""


def _normalize_extensions(allowed_extensions: Sequence[str]) -> set[str]:
    normalized: set[str] = set()
    for ext in allowed_extensions:
        if not ext:
            continue
        cleaned = str(ext).lower().lstrip(".")
        if cleaned:
            normalized.add(cleaned)
    return normalized


def _prepare_filename(
    upload: UploadFile,
    filename_transform: Optional[Callable[[str], str]],
) -> str:
    raw_name = upload.filename or ""
    if raw_name.strip() == "":
        raise UploadError("no filename specified")

    safe_name = secure_filename(raw_name)
    if not safe_name:
        raise UploadError("Invalid filename")

    transformed = safe_name.lower() if filename_transform is None else filename_transform(safe_name)
    transformed = transformed.strip()
    if not transformed:
        raise UploadError("Invalid filename")
    return transformed


def _enforce_max_bytes(upload: UploadFile, max_bytes: Optional[int]) -> None:
    if max_bytes is None:
        return
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > max_bytes:
        raise UploadError("File exceeds maximum allowed size")


def save_upload_file(
    upload: UploadFile,
    *,
    allowed_extensions: Sequence[str],
    dest_dir: Path,
    filename_transform: Optional[Callable[[str], str]] = None,
    overwrite: bool = False,
    max_bytes: Optional[int] = None,
    post_save: Optional[Callable[[Path], None]] = None,
) -> Path:
    filename = _prepare_filename(upload, filename_transform)
    allowed = _normalize_extensions(allowed_extensions)
    if allowed:
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in allowed:
            allowed_list = ", ".join(sorted(f".{ext}" for ext in allowed))
            raise UploadError(f"Invalid file extension. Allowed: {allowed_list}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    destination = dest_dir / filename

    if destination.exists():
        if not overwrite:
            raise UploadError("File already exists")
        destination.unlink()

    _enforce_max_bytes(upload, max_bytes)

    with open(destination, "wb") as dest:
        shutil.copyfileobj(upload.file, dest)

    try:
        if post_save is not None:
            post_save(destination)
    except UploadError:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/microservices/rq_engine/upload_helpers.py:94", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        destination.unlink(missing_ok=True)
        raise exc

    return destination


def upload_success(
    message: Optional[str] = None,
    *,
    result: Any = None,
    status: int = 200,
    **extras: Any,
) -> JSONResponse:
    payload: dict[str, Any] = {}
    if message is not None:
        payload["message"] = message
    if result is not None:
        payload["result"] = result
    payload.update(extras)
    return JSONResponse(payload, status_code=status)


def upload_failure(error: str, status: int = 400, **extras: Any) -> JSONResponse:
    error_payload: dict[str, Any] = {"message": error}
    if extras:
        error_payload["details"] = extras
    payload: dict[str, Any] = {"error": error_payload}
    return JSONResponse(payload, status_code=status)


__all__ = [
    "UploadError",
    "save_upload_file",
    "upload_failure",
    "upload_success",
]
