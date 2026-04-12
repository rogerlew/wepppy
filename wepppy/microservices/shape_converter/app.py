"""Shape-converter Starlette application scaffold."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.datastructures import FormData
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .cleanup import (
    ActiveRequestScratchRegistry,
    RequestScratchLayout,
    cleanup_request_scratch_dir,
    create_request_scratch_dir,
    sweep_stale_request_dirs,
)
from .convert import convert_uploaded_archive
from .errors import ShapeConverterError, error_response
from .inspect import inspect_uploaded_archive

SERVICE_SCOPE = "shape-converter"
DEFAULT_SCRATCH_ROOT = Path("/tmp/shape-converter")
_LOGGER = logging.getLogger("wepppy.microservices.shape_converter.cleanup")
_CONVERT_ALLOWED_FIELDS = frozenset({"archive", "output_format", "target_crs", "response_mode"})
_CONVERT_REQUIRED_FIELDS = frozenset({"archive", "output_format", "target_crs"})
_CONVERT_METADATA_MAX_ENTRIES = int(os.getenv("SHAPE_CONVERTER_METADATA_MAX_ENTRIES", "256"))
_CONVERT_METADATA_TTL_SECONDS = int(os.getenv("SHAPE_CONVERTER_METADATA_TTL_SECONDS", "900"))
_INSPECT_TIMEOUT_SECONDS = max(1, int(os.getenv("SHAPE_CONVERTER_INSPECT_TIMEOUT_SECONDS", "30")))
_CONVERT_TIMEOUT_SECONDS = max(1, int(os.getenv("SHAPE_CONVERTER_CONVERT_TIMEOUT_SECONDS", "120")))
_JANITOR_STALE_SECONDS = max(1, int(os.getenv("SHAPE_CONVERTER_JANITOR_STALE_SECONDS", "900")))
_JANITOR_INTERVAL_SECONDS = max(1, int(os.getenv("SHAPE_CONVERTER_JANITOR_INTERVAL_SECONDS", "60")))


def _resolve_scratch_root() -> Path:
    scratch_override = os.getenv("SHAPE_CONVERTER_SCRATCH_ROOT")
    if scratch_override:
        return Path(scratch_override)
    return DEFAULT_SCRATCH_ROOT


def _is_scratch_root_writable(scratch_root: Path) -> tuple[bool, str | None]:
    try:
        scratch_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"scratch_root_create_failed: {exc}"

    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=scratch_root, delete=True, encoding="utf-8") as handle:
            handle.write("shape-converter readiness check")
            handle.flush()
    except OSError as exc:
        return False, f"scratch_root_not_writable: {exc}"

    return True, None


def _log_structured_event(*, level: int, event: str, **fields: object) -> None:
    payload = {"event": event, **fields}
    _LOGGER.log(level, json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _active_scratch_registry(app: Starlette) -> ActiveRequestScratchRegistry:
    registry = getattr(app.state, "active_request_scratch_registry", None)
    if isinstance(registry, ActiveRequestScratchRegistry):
        return registry

    fallback_registry = ActiveRequestScratchRegistry()
    app.state.active_request_scratch_registry = fallback_registry
    return fallback_registry


def _allocate_request_scratch_layout(
    *,
    request: Request,
    request_id: str,
    request_scope: str,
) -> RequestScratchLayout:
    scratch_root = getattr(request.app.state, "scratch_root", _resolve_scratch_root())
    registry = _active_scratch_registry(request.app)
    return create_request_scratch_dir(
        scratch_root=scratch_root,
        request_id=request_id,
        request_scope=request_scope,
        registry=registry,
        logger=_LOGGER,
    )


def _run_janitor_sweep(app: Starlette, *, trigger: str) -> None:
    scratch_root = getattr(app.state, "scratch_root", _resolve_scratch_root())
    registry = _active_scratch_registry(app)
    result = sweep_stale_request_dirs(
        scratch_root=scratch_root,
        stale_after_seconds=_JANITOR_STALE_SECONDS,
        registry=registry,
        logger=_LOGGER,
    )
    _log_structured_event(
        level=logging.INFO,
        event="request_scratch_janitor_sweep",
        trigger=trigger,
        scanned=result.scanned,
        removed=result.removed,
        skipped_non_owned=result.skipped_non_owned,
        skipped_active=result.skipped_active,
        skipped_fresh=result.skipped_fresh,
        failed=result.failed,
    )


async def _run_janitor_loop(app: Starlette, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        _run_janitor_sweep(app, trigger="periodic")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=_JANITOR_INTERVAL_SECONDS)
        except TimeoutError:
            continue


async def homepage(_: Request) -> JSONResponse:
    return JSONResponse(
        {
            "service": SERVICE_SCOPE,
            "status": "ok",
            "message": "shape-converter service scaffold",
        }
    )


async def health_live(_: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "scope": SERVICE_SCOPE,
            "check": "live",
        }
    )


async def health_ready(request: Request) -> JSONResponse:
    bootstrapped = bool(getattr(request.app.state, "bootstrapped", False))
    scratch_root = getattr(request.app.state, "scratch_root", _resolve_scratch_root())
    writable, failure_reason = _is_scratch_root_writable(scratch_root)

    if not bootstrapped:
        return JSONResponse(
            {
                "status": "not_ready",
                "scope": SERVICE_SCOPE,
                "check": "ready",
                "reason": "service_not_bootstrapped",
            },
            status_code=503,
        )

    if not writable:
        return JSONResponse(
            {
                "status": "not_ready",
                "scope": SERVICE_SCOPE,
                "check": "ready",
                "reason": failure_reason,
                "scratch_root": str(scratch_root),
            },
            status_code=503,
        )

    return JSONResponse(
        {
            "status": "ok",
            "scope": SERVICE_SCOPE,
            "check": "ready",
            "scratch_root": str(scratch_root),
        }
    )


async def inspect_archive(request: Request) -> JSONResponse:
    request_id = uuid.uuid4().hex
    request_scope = "inspect"
    cleanup_reason = "unknown"

    try:
        scratch_layout = _allocate_request_scratch_layout(
            request=request,
            request_id=request_id,
            request_scope=request_scope,
        )
    except OSError as exc:
        return error_response(
            ShapeConverterError(
                code="invalid_shapefile",
                message="Unable to allocate request scratch directory.",
                details=str(exc),
                status_code=500,
            ),
            request_id=request_id,
        )

    try:
        async with asyncio.timeout(_INSPECT_TIMEOUT_SECONDS):
            try:
                form = await request.form()
            except (RuntimeError, ValueError, TypeError) as exc:
                cleanup_reason = "invalid_multipart"
                return error_response(
                    ShapeConverterError(
                        code="invalid_archive",
                        message="Request body must be multipart/form-data.",
                        details=str(exc),
                    ),
                    request_id=request_id,
                )

            if set(form.keys()) != {"archive"}:
                cleanup_reason = "invalid_fields"
                return error_response(
                    ShapeConverterError(
                        code="invalid_archive",
                        message="Request must include exactly one file field named 'archive'.",
                        details=f"Received form fields: {list(form.keys())}.",
                    ),
                    request_id=request_id,
                )

            archive_field = form.get("archive")
            if not isinstance(archive_field, UploadFile):
                cleanup_reason = "archive_not_upload"
                return error_response(
                    ShapeConverterError(
                        code="invalid_archive",
                        message="Field 'archive' must be an uploaded file.",
                        details="Multipart field 'archive' was not a file upload.",
                    ),
                    request_id=request_id,
                )

            try:
                payload = await inspect_uploaded_archive(
                    archive=archive_field,
                    scratch=scratch_layout,
                    request_id=request_id,
                )
            except ShapeConverterError as exc:
                cleanup_reason = f"shape_error:{exc.code}"
                return error_response(exc, request_id=request_id)
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                # Boundary catch: ensure inspect failures still return canonical payloads.
                cleanup_reason = "inspect_unexpected_failure"
                return error_response(
                    ShapeConverterError(
                        code="invalid_shapefile",
                        message="Unexpected inspect processing failure.",
                        details=str(exc),
                        status_code=500,
                    ),
                    request_id=request_id,
                )

        cleanup_reason = "success"
        return JSONResponse(payload)
    except TimeoutError:
        cleanup_reason = "timeout"
        return error_response(
            ShapeConverterError(
                code="request_timeout",
                message="Inspect request exceeded processing timeout.",
                details=f"Inspect processing exceeded {_INSPECT_TIMEOUT_SECONDS} seconds.",
                status_code=408,
            ),
            request_id=request_id,
        )
    except asyncio.CancelledError:
        cleanup_reason = "cancelled"
        raise
    finally:
        cleanup_request_scratch_dir(
            layout=scratch_layout,
            request_id=request_id,
            request_scope=request_scope,
            cleanup_reason=cleanup_reason,
            registry=_active_scratch_registry(request.app),
            logger=_LOGGER,
        )


def _parse_required_string_field(form: FormData, field_name: str) -> str:
    value = form.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ShapeConverterError(
            code="invalid_request",
            message=f"Field '{field_name}' is required.",
            details=f"Multipart field '{field_name}' must be a non-empty string.",
        )
    return value.strip()


def _validate_convert_form(form: FormData) -> tuple[UploadFile, str, str, str]:
    received_fields = set(form.keys())
    unknown_fields = sorted(received_fields - _CONVERT_ALLOWED_FIELDS)
    missing_fields = sorted(_CONVERT_REQUIRED_FIELDS - received_fields)

    if unknown_fields or missing_fields:
        details_parts: list[str] = []
        if missing_fields:
            details_parts.append(f"missing fields={missing_fields}")
        if unknown_fields:
            details_parts.append(f"unknown fields={unknown_fields}")
        raise ShapeConverterError(
            code="invalid_request",
            message="Convert request fields are invalid.",
            details="; ".join(details_parts) or "Invalid multipart fields.",
        )

    archive_field = form.get("archive")
    if not isinstance(archive_field, UploadFile):
        raise ShapeConverterError(
            code="invalid_archive",
            message="Field 'archive' must be an uploaded file.",
            details="Multipart field 'archive' was not a file upload.",
        )

    output_format = _parse_required_string_field(form, "output_format")
    target_crs = _parse_required_string_field(form, "target_crs")

    response_mode_raw = form.get("response_mode")
    if response_mode_raw is None:
        response_mode = "download"
    elif isinstance(response_mode_raw, str) and response_mode_raw.strip():
        response_mode = response_mode_raw.strip()
    else:
        raise ShapeConverterError(
            code="invalid_request",
            message="Field 'response_mode' must be a string when provided.",
            details="Multipart field 'response_mode' was not a non-empty string.",
        )

    return archive_field, output_format, target_crs, response_mode


def _metadata_path_for_request(*, root_path: str, request_id: str) -> str:
    normalized_root = root_path.rstrip("/")
    return f"{normalized_root}/v1/convert/metadata/{request_id}" if normalized_root else f"/v1/convert/metadata/{request_id}"


def _prune_convert_metadata_store(
    store: OrderedDict[str, tuple[float, dict[str, object]]],
    *,
    now_monotonic: float,
) -> None:
    if _CONVERT_METADATA_TTL_SECONDS > 0:
        expired_keys = [
            request_id
            for request_id, (created_at, _payload) in store.items()
            if now_monotonic - created_at > _CONVERT_METADATA_TTL_SECONDS
        ]
        for request_id in expired_keys:
            store.pop(request_id, None)

    while _CONVERT_METADATA_MAX_ENTRIES > 0 and len(store) > _CONVERT_METADATA_MAX_ENTRIES:
        store.popitem(last=False)


async def convert_archive(request: Request) -> Response:
    request_id = uuid.uuid4().hex
    request_scope = "convert"
    cleanup_reason = "unknown"

    try:
        scratch_layout = _allocate_request_scratch_layout(
            request=request,
            request_id=request_id,
            request_scope=request_scope,
        )
    except OSError as exc:
        return error_response(
            ShapeConverterError(
                code="reprojection_failed",
                message="Unable to allocate request scratch directory.",
                details=str(exc),
                status_code=500,
            ),
            request_id=request_id,
        )

    try:
        async with asyncio.timeout(_CONVERT_TIMEOUT_SECONDS):
            try:
                form = await request.form()
            except (RuntimeError, ValueError, TypeError) as exc:
                cleanup_reason = "invalid_multipart"
                return error_response(
                    ShapeConverterError(
                        code="invalid_archive",
                        message="Request body must be multipart/form-data.",
                        details=str(exc),
                    ),
                    request_id=request_id,
                )

            try:
                archive_field, output_format, target_crs, response_mode = _validate_convert_form(form)
            except ShapeConverterError as exc:
                cleanup_reason = f"shape_error:{exc.code}"
                return error_response(exc, request_id=request_id)

            if response_mode == "json_body":
                cleanup_reason = "response_mode_not_supported"
                return error_response(
                    ShapeConverterError(
                        code="response_mode_not_supported",
                        message="response_mode=json_body is not available yet.",
                        details="json_body mode is deferred to WP-06B; use response_mode=download.",
                        status_code=400,
                    ),
                    request_id=request_id,
                )

            if response_mode != "download":
                cleanup_reason = "response_mode_invalid"
                return error_response(
                    ShapeConverterError(
                        code="invalid_request",
                        message="Unsupported response_mode value.",
                        details=f"response_mode={response_mode!r} is invalid; expected 'download' or 'json_body'.",
                    ),
                    request_id=request_id,
                )

            try:
                converted = await convert_uploaded_archive(
                    archive=archive_field,
                    scratch=scratch_layout,
                    request_id=request_id,
                    output_format=output_format,
                    target_crs=target_crs,
                )
            except ShapeConverterError as exc:
                cleanup_reason = f"shape_error:{exc.code}"
                return error_response(exc, request_id=request_id)
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                # Boundary catch: ensure convert failures still return canonical payloads.
                cleanup_reason = "convert_unexpected_failure"
                return error_response(
                    ShapeConverterError(
                        code="reprojection_failed",
                        message="Unexpected convert processing failure.",
                        details=str(exc),
                        status_code=500,
                    ),
                    request_id=request_id,
                )

        root_path = str(request.scope.get("root_path") or "")
        metadata_path = _metadata_path_for_request(root_path=root_path, request_id=request_id)

        convert_metadata = dict(converted.metadata)
        convert_metadata["request_id"] = request_id
        convert_metadata["download_filename"] = converted.filename
        convert_metadata["download_content_type"] = converted.content_type
        convert_metadata["metadata_path"] = metadata_path
        metadata_store: OrderedDict[str, tuple[float, dict[str, object]]] = request.app.state.convert_metadata
        now_monotonic = time.monotonic()
        _prune_convert_metadata_store(metadata_store, now_monotonic=now_monotonic)
        metadata_store[request_id] = (now_monotonic, convert_metadata)
        metadata_store.move_to_end(request_id)
        _prune_convert_metadata_store(metadata_store, now_monotonic=now_monotonic)

        headers = {
            "Content-Disposition": f'attachment; filename="{converted.filename}"',
            "X-Shape-Converter-Request-Id": request_id,
            "X-Shape-Converter-Metadata-Path": metadata_path,
        }
        cleanup_reason = "success"
        return Response(content=converted.content, media_type=converted.content_type, headers=headers)
    except TimeoutError:
        cleanup_reason = "timeout"
        return error_response(
            ShapeConverterError(
                code="request_timeout",
                message="Convert request exceeded processing timeout.",
                details=f"Convert processing exceeded {_CONVERT_TIMEOUT_SECONDS} seconds.",
                status_code=408,
            ),
            request_id=request_id,
        )
    except asyncio.CancelledError:
        cleanup_reason = "cancelled"
        raise
    finally:
        cleanup_request_scratch_dir(
            layout=scratch_layout,
            request_id=request_id,
            request_scope=request_scope,
            cleanup_reason=cleanup_reason,
            registry=_active_scratch_registry(request.app),
            logger=_LOGGER,
        )


async def convert_metadata(request: Request) -> JSONResponse:
    request_id = str(request.path_params.get("request_id") or "").strip()
    metadata_store: OrderedDict[str, tuple[float, dict[str, object]]] = getattr(
        request.app.state,
        "convert_metadata",
        OrderedDict(),
    )
    _prune_convert_metadata_store(metadata_store, now_monotonic=time.monotonic())

    metadata_entry = metadata_store.get(request_id)
    metadata_payload = metadata_entry[1] if metadata_entry is not None else None
    if metadata_payload is None:
        return error_response(
            ShapeConverterError(
                code="metadata_not_found",
                message="Convert metadata request_id was not found.",
                details=f"No convert metadata exists for request_id={request_id!r}.",
                status_code=404,
            ),
            request_id=request_id or None,
        )

    return JSONResponse(metadata_payload)


@asynccontextmanager
async def app_lifespan(app: Starlette):
    app.state.scratch_root = _resolve_scratch_root()
    app.state.active_request_scratch_registry = ActiveRequestScratchRegistry()
    app.state.convert_metadata = OrderedDict()
    app.state.janitor_stop_event = asyncio.Event()
    _run_janitor_sweep(app, trigger="startup")
    app.state.janitor_task = asyncio.create_task(
        _run_janitor_loop(app, app.state.janitor_stop_event),
        name="shape-converter-janitor",
    )
    app.state.bootstrapped = True
    try:
        yield
    finally:
        janitor_stop_event = getattr(app.state, "janitor_stop_event", None)
        if isinstance(janitor_stop_event, asyncio.Event):
            janitor_stop_event.set()

        janitor_task = getattr(app.state, "janitor_task", None)
        if isinstance(janitor_task, asyncio.Task):
            try:
                await janitor_task
            except asyncio.CancelledError:
                pass

        _run_janitor_sweep(app, trigger="shutdown")
        app.state.convert_metadata = {}
        app.state.bootstrapped = False


def create_app() -> Starlette:
    routes = [
        Route("/", homepage),
        Route("/health/live", health_live),
        Route("/health/ready", health_ready),
        Route("/v1/inspect", inspect_archive, methods=["POST"]),
        Route("/v1/convert", convert_archive, methods=["POST"]),
        Route("/v1/convert/metadata/{request_id}", convert_metadata, methods=["GET"]),
    ]

    app = Starlette(debug=False, routes=routes, lifespan=app_lifespan)

    @app.middleware("http")
    async def forwarded_prefix_middleware(request: Request, call_next):
        prefix = request.headers.get("X-Forwarded-Prefix")
        if prefix:
            normalized = prefix.rstrip("/")
            request.scope["root_path"] = normalized if normalized else ""
        return await call_next(request)

    return app


app = create_app()


__all__ = ["app", "create_app"]
