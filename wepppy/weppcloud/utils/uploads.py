from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple, Any, Union

from flask import Response, jsonify, request
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .helpers import get_wd

__all__ = [
    "UploadError",
    "save_run_file",
    "upload_success",
    "upload_failure",
]


class UploadError(Exception):
    """Raised when an upload validation or post-save check fails."""


_BUFFER_SIZE = 64 * 1024


def _normalize_extensions(allowed_extensions: Sequence[str]) -> set[str]:
    normalized: set[str] = set()
    for ext in allowed_extensions:
        if not ext:
            continue
        cleaned = ext.lower().lstrip(".")
        if cleaned:
            normalized.add(cleaned)
    return normalized


def _prepare_filename(
    storage: FileStorage,
    filename_transform: Optional[Callable[[str], str]],
) -> str:
    raw_name = storage.filename or ""
    if raw_name.strip() == "":
        raise UploadError("no filename specified")

    safe_name = secure_filename(raw_name)
    if not safe_name:
        raise UploadError("Invalid filename")

    if filename_transform is None:
        transformed = safe_name.lower()
    else:
        transformed = filename_transform(safe_name)

    transformed = transformed.strip()
    if not transformed:
        raise UploadError("Invalid filename")
    return transformed


def save_run_file(
    *,
    runid: str,
    config: str,
    form_field: str,
    allowed_extensions: Sequence[str],
    dest_subdir: str,
    run_root: Optional[Union[str, Path]] = None,
    filename_transform: Optional[Callable[[str], str]] = None,
    overwrite: bool = False,
    post_save: Optional[Callable[[Path], None]] = None,
    max_bytes: Optional[int] = None,
) -> Path:
    """Validate and persist a run-scoped file upload."""
    if form_field not in request.files:
        raise UploadError("Could not find file")

    storage = request.files[form_field]
    if not isinstance(storage, FileStorage):
        raise UploadError("Invalid upload payload")

    filename = _prepare_filename(storage, filename_transform)
    allowed = _normalize_extensions(allowed_extensions)
    if allowed:
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in allowed:
            allowed_list = ", ".join(sorted(f".{ext}" for ext in allowed))
            raise UploadError(f"Invalid file extension. Allowed: {allowed_list}")

    root_value = Path(run_root) if run_root is not None else Path(get_wd(runid))
    destination_dir = (root_value / dest_subdir) if dest_subdir else root_value
    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / filename

    if destination.exists():
        if not overwrite:
            raise UploadError("File already exists")
        destination.unlink()

    if max_bytes is not None:
        storage.stream.seek(0, 2)
        size = storage.stream.tell()
        storage.stream.seek(0)
        if size > max_bytes:
            raise UploadError("File exceeds maximum allowed size")

    storage.save(str(destination), buffer_size=_BUFFER_SIZE)

    try:
        if post_save is not None:
            post_save(destination)
    except UploadError:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:  # pragma: no cover - defensive
        destination.unlink(missing_ok=True)
        raise exc

    return destination


def upload_success(
    message: Optional[str] = None,
    *,
    content: Any = None,
    status: int = 200,
    **extras: Any,
) -> Response:
    payload: dict[str, Any] = {"Success": True}
    if message is not None:
        payload["Message"] = message
    if content is not None:
        payload["Content"] = content
    payload.update(extras)
    response = jsonify(payload)
    response.status_code = status
    return response


def upload_failure(error: str, status: int = 400, **extras: Any) -> Response:
    payload: dict[str, Any] = {"Success": False, "Error": error}
    payload.update(extras)
    response = jsonify(payload)
    response.status_code = status
    return response
