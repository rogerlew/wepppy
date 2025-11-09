from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from flask import Response
from werkzeug.datastructures import FileStorage

__all__ = ["UploadError", "save_run_file", "upload_success", "upload_failure"]


class UploadError(Exception): ...


def save_run_file(
    *,
    runid: str,
    config: str,
    form_field: str,
    allowed_extensions: Sequence[str],
    dest_subdir: str,
    run_root: str | Path | None = ...,
    filename_transform: Optional[Callable[[str], str]] = ...,
    overwrite: bool = ...,
    post_save: Optional[Callable[[Path], None]] = ...,
    max_bytes: int | None = ...,
) -> Path: ...


def upload_success(
    message: Optional[str] = ...,
    *,
    content: Any = ...,
    status: int = ...,
    **extras: Any,
) -> Response: ...


def upload_failure(error: str, status: int = ..., **extras: Any) -> Response: ...
