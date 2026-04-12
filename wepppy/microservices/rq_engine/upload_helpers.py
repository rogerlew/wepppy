from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from wepppy.microservices.upload_boundary import UploadBoundaryError, save_upload_from_stream

from .responses import error_response


class UploadError(UploadBoundaryError):
    """Raised when an upload validation or post-save check fails."""


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
    try:
        return save_upload_from_stream(
            raw_filename=getattr(upload, "filename", None),
            stream=getattr(upload, "file", None),
            dest_dir=dest_dir,
            allowed_extensions=allowed_extensions,
            filename_transform=filename_transform,
            overwrite=overwrite,
            max_bytes=max_bytes,
            post_save=post_save,
        )
    except UploadBoundaryError as exc:
        raise UploadError(str(exc), status_code=exc.status_code) from exc


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
    details: Any
    if "details" in extras:
        details = extras.pop("details")
    elif extras:
        details = extras
    else:
        details = error
    code = extras.pop("code", None)
    errors = extras.pop("errors", None)
    if extras:
        if isinstance(details, dict):
            details = {**details, **extras}
        else:
            details = {"details": details, **extras}
    return error_response(
        error,
        status_code=status,
        code=code,
        details=details,
        errors=errors,
    )


__all__ = [
    "UploadError",
    "save_upload_file",
    "upload_failure",
    "upload_success",
]
