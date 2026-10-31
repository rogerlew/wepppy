"""Shared non-ZIP upload boundary helpers."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import IO, Callable, Optional, Sequence

from werkzeug.utils import secure_filename

UPLOAD_STREAM_CHUNK_BYTES = 64 * 1024


class UploadBoundaryError(ValueError):
    """Raised when upload boundary validation fails."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def normalize_extensions(allowed_extensions: Sequence[str]) -> set[str]:
    normalized: set[str] = set()
    for ext in allowed_extensions:
        if not ext:
            continue
        cleaned = str(ext).lower().lstrip(".")
        if cleaned:
            normalized.add(cleaned)
    return normalized


def prepare_filename(
    raw_name: str | None,
    *,
    filename_transform: Optional[Callable[[str], str]] = None,
    lowercase_by_default: bool = True,
) -> str:
    value = "" if raw_name is None else str(raw_name)
    if value.strip() == "":
        raise UploadBoundaryError("no filename specified")

    safe_name = secure_filename(value)
    if not safe_name:
        raise UploadBoundaryError("Invalid filename")

    if filename_transform is None:
        transformed = safe_name.lower() if lowercase_by_default else safe_name
    else:
        transformed = filename_transform(safe_name)

    transformed = transformed.strip()
    if not transformed:
        raise UploadBoundaryError("Invalid filename")

    return transformed


def enforce_extension(filename: str, allowed_extensions: Sequence[str] | set[str]) -> None:
    allowed = normalize_extensions(tuple(allowed_extensions))
    if not allowed:
        return

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in allowed:
        allowed_list = ", ".join(sorted(f".{token}" for token in allowed))
        raise UploadBoundaryError(f"Invalid file extension. Allowed: {allowed_list}")


def _rewind_stream(stream: IO[bytes]) -> None:
    seek = getattr(stream, "seek", None)
    if callable(seek):
        seek(0)


def write_stream_to_destination(
    stream: IO[bytes],
    destination: Path,
    *,
    overwrite: bool = False,
    max_bytes: int | None = None,
    chunk_bytes: int = UPLOAD_STREAM_CHUNK_BYTES,
    size_error_message: str = "File exceeds maximum allowed size",
) -> int:
    if destination.exists() and not overwrite:
        raise UploadBoundaryError("File already exists")
    _rewind_stream(stream)
    # Transport validation owns temporary storage. Do not unlink an accepted
    # source (or create its parent) until the entire incoming stream is valid.
    with tempfile.TemporaryFile() as buffered:
        bytes_written = 0
        while True:
            chunk = stream.read(chunk_bytes)
            if not chunk:
                break
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            bytes_written += len(chunk)
            if max_bytes is not None and bytes_written > max_bytes:
                raise UploadBoundaryError(size_error_message, status_code=413)
            buffered.write(chunk)
        buffered.seek(0)
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.upload")
        try:
            # Normal open preserves the existing umask-based creation policy.
            with staged.open("xb") as handle:
                while chunk := buffered.read(chunk_bytes):
                    handle.write(chunk)
            if overwrite:
                os.replace(staged, destination)
            else:
                try:
                    os.link(staged, destination)
                except FileExistsError as exc:
                    raise UploadBoundaryError("File already exists") from exc
        finally:
            staged.unlink(missing_ok=True)
    return bytes_written


def save_upload_from_stream(
    *,
    raw_filename: str | None,
    stream: IO[bytes] | None,
    dest_dir: Path,
    allowed_extensions: Sequence[str],
    filename_transform: Optional[Callable[[str], str]] = None,
    lowercase_by_default: bool = True,
    overwrite: bool = False,
    max_bytes: int | None = None,
    post_save: Optional[Callable[[Path], None]] = None,
    size_error_message: str = "File exceeds maximum allowed size",
    chunk_bytes: int = UPLOAD_STREAM_CHUNK_BYTES,
) -> Path:
    """Validate transport and optional staged content before promoting a source.

    The legacy ``post_save`` callback receives a temporary sibling path, not the
    accepted destination. It must finish validation before returning and must not
    retain that temporary pathname in metadata. Only successful validation permits
    destination replacement; the return value is the accepted final path.
    """
    if stream is None:
        raise UploadBoundaryError("Uploaded file stream is unavailable.")

    filename = prepare_filename(
        raw_filename,
        filename_transform=filename_transform,
        lowercase_by_default=lowercase_by_default,
    )
    enforce_extension(filename, allowed_extensions)

    destination = dest_dir / filename
    if destination.exists() and not overwrite:
        raise UploadBoundaryError("File already exists")
    if post_save is not None:
        # A sibling preserves relative VRT dependencies without replacing the
        # accepted source. All transport staging is removed on every exit.
        created_parents = []
        parent = dest_dir
        while not parent.exists():
            created_parents.append(parent)
            parent = parent.parent
        staged = dest_dir / f".{uuid.uuid4().hex}.{filename}"
        try:
            write_stream_to_destination(stream, staged, max_bytes=max_bytes,
                                        chunk_bytes=chunk_bytes, size_error_message=size_error_message)
            post_save(staged)
            with staged.open("rb") as validated:
                write_stream_to_destination(validated, destination, overwrite=overwrite,
                                            chunk_bytes=chunk_bytes)
        finally:
            staged.unlink(missing_ok=True)
            for parent in created_parents:
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
    else:
        write_stream_to_destination(stream, destination, overwrite=overwrite,
                                    max_bytes=max_bytes, chunk_bytes=chunk_bytes,
                                    size_error_message=size_error_message)
    return destination


__all__ = [
    "UPLOAD_STREAM_CHUNK_BYTES",
    "UploadBoundaryError",
    "enforce_extension",
    "normalize_extensions",
    "prepare_filename",
    "save_upload_from_stream",
    "write_stream_to_destination",
]
