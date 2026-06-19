"""Dedicated Starlette service for exact WEPPcloud artifact downloads."""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, BinaryIO

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse
from starlette.routing import Route

from wepppy.microservices.browse.auth import (
    RUN_ALLOWED_TOKEN_CLASSES,
    BrowseAuthError,
    authorize_run_request,
    handle_auth_error,
)
from wepppy.microservices.browse.security import (
    PATH_SECURITY_FORBIDDEN_RECORDER,
    path_security_detail,
    validate_raw_subpath,
    validate_resolved_path_against_roots,
)
from wepppy.weppcloud.utils.helpers import get_wd

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

ARCHIVE_ROUTE_FAMILY = "run_archive"
ARCHIVE_SUBDIR = "archives"
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ResolvedArchive:
    path: Path
    relpath: str
    filename: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ByteRange:
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1


class RangeNotSatisfiable(ValueError):
    """Raised when a Range header cannot be served for a file."""


def _health(_: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


def _request_id(request: Request) -> str:
    return (
        request.headers.get("X-Request-Id")
        or request.headers.get("X-Correlation-Id")
        or uuid.uuid4().hex
    )


def _client_host(request: Request) -> str:
    forwarded_for = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client is not None:
        return request.client.host
    return ""


def _quote_download_filename(filename: str) -> str:
    safe = filename.replace("\\", "_").replace('"', "_")
    return safe or "download.zip"


def _assert_within_root(root: Path, target: Path, *, detail: str = "Invalid path.") -> None:
    try:
        common = os.path.commonpath([str(root), str(target)])
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=detail) from exc
    if common != str(root):
        raise HTTPException(status_code=403, detail=detail)


def _assert_target_allowed(run_root: Path, archive_root: Path, target: Path) -> None:
    violation = validate_resolved_path_against_roots(target, (archive_root,))
    if violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(violation))

    # Keep the broader browse run-root guard in place so restricted recorder and hidden
    # segments keep their canonical behavior if archive layout changes later.
    violation = validate_resolved_path_against_roots(target, (run_root,))
    if violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(violation))


def _resolve_run_root(runid: str) -> Path:
    try:
        run_root = Path(get_wd(runid, prefer_active=False)).resolve()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run '{runid}' not found") from exc
    if not run_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Run '{runid}' not found")
    return run_root


def _resolve_archive(runid: str, archive_subpath: str) -> ResolvedArchive:
    if not archive_subpath or archive_subpath.endswith("/"):
        raise HTTPException(status_code=404)
    if "\\" in archive_subpath:
        raise HTTPException(status_code=403, detail="Invalid path.")
    raw_parts = archive_subpath.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise HTTPException(status_code=403, detail="Invalid path.")
    if not archive_subpath.casefold().endswith(".zip"):
        raise HTTPException(status_code=404)

    run_root = _resolve_run_root(runid)
    archive_root = (run_root / ARCHIVE_SUBDIR).resolve(strict=False)
    target = Path(os.path.abspath(str(archive_root / archive_subpath)))
    _assert_within_root(archive_root, target)
    _assert_target_allowed(run_root, archive_root, target)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404)

    return ResolvedArchive(
        path=target,
        relpath=f"{ARCHIVE_SUBDIR}/{archive_subpath}",
        filename=target.name,
        size_bytes=target.stat().st_size,
    )


def _parse_range_header(range_header: str | None, size_bytes: int) -> ByteRange | None:
    if not range_header:
        return None

    value = range_header.strip()
    if not value.lower().startswith("bytes="):
        raise RangeNotSatisfiable("unsupported_range_unit")

    spec = value[6:].strip()
    if "," in spec:
        raise RangeNotSatisfiable("multipart_ranges_unsupported")
    if "-" not in spec:
        raise RangeNotSatisfiable("malformed_range")

    start_text, end_text = (part.strip() for part in spec.split("-", 1))
    if size_bytes <= 0:
        raise RangeNotSatisfiable("empty_file")

    if not start_text:
        try:
            suffix_length = int(end_text)
        except ValueError as exc:
            raise RangeNotSatisfiable("malformed_suffix_range") from exc
        if suffix_length <= 0:
            raise RangeNotSatisfiable("invalid_suffix_range")
        start = max(size_bytes - suffix_length, 0)
        end = size_bytes - 1
        return ByteRange(start=start, end=end)

    try:
        start = int(start_text)
    except ValueError as exc:
        raise RangeNotSatisfiable("malformed_range_start") from exc
    if start < 0 or start >= size_bytes:
        raise RangeNotSatisfiable("range_start_outside_file")

    if end_text:
        try:
            end = int(end_text)
        except ValueError as exc:
            raise RangeNotSatisfiable("malformed_range_end") from exc
        if end < start:
            raise RangeNotSatisfiable("range_end_before_start")
        end = min(end, size_bytes - 1)
    else:
        end = size_bytes - 1

    return ByteRange(start=start, end=end)


def _archive_response_headers(
    archive: ResolvedArchive,
    *,
    content_length: int,
    byte_range: ByteRange | None,
    request_id: str,
) -> dict[str, str]:
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'attachment; filename="{_quote_download_filename(archive.filename)}"',
        "Content-Length": str(content_length),
        "X-Request-Id": request_id,
    }
    if byte_range is not None:
        headers["Content-Range"] = (
            f"bytes {byte_range.start}-{byte_range.end}/{archive.size_bytes}"
        )
    return headers


def _open_binary(path: Path) -> BinaryIO:
    return path.open("rb")


async def _stream_file_range(
    path: Path,
    byte_range: ByteRange,
    metrics: dict[str, int | str],
) -> AsyncIterator[bytes]:
    remaining = byte_range.length
    sent = 0
    outcome = "success"
    fp: BinaryIO | None = None
    try:
        fp = await asyncio.to_thread(_open_binary, path)
        await asyncio.to_thread(fp.seek, byte_range.start)
        while remaining > 0:
            chunk = await asyncio.to_thread(fp.read, min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            sent += len(chunk)
            remaining -= len(chunk)
            metrics["bytes_sent"] = sent
            yield chunk
    except (BrokenPipeError, ConnectionResetError):
        outcome = "client_aborted"
        metrics["outcome"] = outcome
        raise
    except OSError:
        outcome = "server_error"
        metrics["outcome"] = outcome
        raise
    finally:
        if fp is not None:
            await asyncio.to_thread(fp.close)
        metrics["bytes_sent"] = sent
        metrics.setdefault("outcome", outcome)


def _log_download(
    request: Request,
    *,
    request_id: str,
    archive: ResolvedArchive | None,
    status_code: int,
    bytes_sent: int,
    duration_ms: float,
    outcome: str,
    byte_range: ByteRange | None = None,
    error_reason: str = "",
) -> None:
    runid = request.path_params.get("runid", "")
    config = request.path_params.get("config", "")
    LOGGER.info(
        "download.complete route_family=%s request_id=%s runid=%s config=%s "
        "path_category=%s basename=%s file_size=%s method=%s status=%s "
        "range_start=%s range_end=%s bytes_sent=%s duration_ms=%.2f "
        "outcome=%s error_reason=%s client_ip=%s user_agent=%s",
        ARCHIVE_ROUTE_FAMILY,
        request_id,
        runid,
        config,
        ARCHIVE_SUBDIR,
        archive.filename if archive is not None else "",
        archive.size_bytes if archive is not None else "",
        request.method,
        status_code,
        byte_range.start if byte_range is not None else "",
        byte_range.end if byte_range is not None else "",
        bytes_sent,
        duration_ms,
        outcome,
        error_reason,
        _client_host(request),
        request.headers.get("User-Agent", ""),
    )


async def archive_download(request: Request) -> Response:
    started = time.monotonic()
    request_id = _request_id(request)
    runid = request.path_params["runid"]
    config = request.path_params["config"]
    archive_subpath = request.path_params.get("subpath", "")
    full_subpath = f"{ARCHIVE_SUBDIR}/{archive_subpath}" if archive_subpath else ARCHIVE_SUBDIR
    archive: ResolvedArchive | None = None

    try:
        auth_context = authorize_run_request(
            request,
            runid=runid,
            config=config,
            subpath=full_subpath,
            allow_public_without_token=True,
            require_authenticated=False,
            allowed_token_classes=RUN_ALLOWED_TOKEN_CLASSES,
        )
    except BrowseAuthError as exc:
        status_code = exc.status_code
        try:
            response = handle_auth_error(
                request,
                runid=runid,
                error=exc,
                redirect_on_401=True,
                redirect_html_only=True,
            )
            status_code = response.status_code
            return response
        finally:
            _log_download(
                request,
                request_id=request_id,
                archive=None,
                status_code=status_code,
                bytes_sent=0,
                duration_ms=(time.monotonic() - started) * 1000,
                outcome="auth_error",
                error_reason=exc.code,
            )

    violation = validate_raw_subpath(full_subpath)
    if violation is not None:
        if auth_context.is_root and violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            violation = None
    if violation is not None:
        status_code = 403
        _log_download(
            request,
            request_id=request_id,
            archive=None,
            status_code=status_code,
            bytes_sent=0,
            duration_ms=(time.monotonic() - started) * 1000,
            outcome="forbidden",
            error_reason=violation,
        )
        raise HTTPException(status_code=status_code, detail=path_security_detail(violation))

    try:
        archive = await asyncio.to_thread(_resolve_archive, runid, archive_subpath)
        byte_range = _parse_range_header(request.headers.get("Range"), archive.size_bytes)
    except RangeNotSatisfiable as exc:
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes */{archive.size_bytes if archive is not None else 0}",
            "X-Request-Id": request_id,
        }
        _log_download(
            request,
            request_id=request_id,
            archive=archive,
            status_code=416,
            bytes_sent=0,
            duration_ms=(time.monotonic() - started) * 1000,
            outcome="range_not_satisfiable",
            error_reason=str(exc),
        )
        return Response(status_code=416, headers=headers)
    except HTTPException as exc:
        _log_download(
            request,
            request_id=request_id,
            archive=archive,
            status_code=exc.status_code,
            bytes_sent=0,
            duration_ms=(time.monotonic() - started) * 1000,
            outcome="not_found" if exc.status_code == 404 else "forbidden",
            error_reason=str(exc.detail or ""),
        )
        raise

    status_code = 206 if byte_range is not None else 200
    if byte_range is None:
        byte_range = ByteRange(start=0, end=max(archive.size_bytes - 1, -1))
    content_length = byte_range.length if archive.size_bytes > 0 else 0
    response_headers = _archive_response_headers(
        archive,
        content_length=content_length,
        byte_range=byte_range if status_code == 206 else None,
        request_id=request_id,
    )

    if request.method == "HEAD":
        _log_download(
            request,
            request_id=request_id,
            archive=archive,
            status_code=status_code,
            bytes_sent=0,
            duration_ms=(time.monotonic() - started) * 1000,
            outcome="success",
            byte_range=byte_range if status_code == 206 else None,
        )
        return Response(
            status_code=status_code,
            headers=response_headers,
            media_type="application/zip",
        )

    metrics: dict[str, int | str] = {"bytes_sent": 0, "outcome": "success"}
    body = _stream_file_range(archive.path, byte_range, metrics)

    async def _finalizing_body():
        try:
            async for chunk in body:
                yield chunk
        finally:
            _log_download(
                request,
                request_id=request_id,
                archive=archive,
                status_code=status_code,
                bytes_sent=int(metrics.get("bytes_sent", 0)),
                duration_ms=(time.monotonic() - started) * 1000,
                outcome=str(metrics.get("outcome", "success")),
                byte_range=byte_range if status_code == 206 else None,
            )

    return StreamingResponse(
        _finalizing_body(),
        status_code=status_code,
        media_type="application/zip",
        headers=response_headers,
    )


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/health", _health, methods=["GET"]),
            Route(
                "/weppcloud/runs/{runid}/{config}/download/archives/{subpath:path}",
                archive_download,
                methods=["GET", "HEAD"],
            ),
        ]
    )


app = create_app()
