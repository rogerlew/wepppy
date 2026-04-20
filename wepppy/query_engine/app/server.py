"""Starlette application exposing the query-engine web console and MCP routes."""

from __future__ import annotations

import asyncio
import os
import json
import logging
import math
import threading
import time
import traceback
from collections import OrderedDict, deque
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    Response,
    PlainTextResponse,
    StreamingResponse,
)
from starlette.exceptions import HTTPException
from starlette.routing import Route, Mount
from starlette.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader

from wepppy.observability.correlation import (
    CORRELATION_ID_HEADER,
    bind_correlation_id,
    install_correlation_log_record_factory,
    reset_correlation_id,
    select_inbound_correlation_id,
)
from wepppy.config.secrets import get_secret

from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest
from wepppy.weppcloud.utils.assets import resolve_asset_version
from .query_presets import QUERY_PRESETS
from .helpers import resolve_run_path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
SHARED_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "weppcloud" / "templates"
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))

loaders = [FileSystemLoader(str(TEMPLATES_DIR))]
if SHARED_TEMPLATES_DIR.exists():
    loaders.append(FileSystemLoader(str(SHARED_TEMPLATES_DIR)))
TEMPLATES.env.loader = ChoiceLoader(loaders)
LOGGER = logging.getLogger(__name__)
install_correlation_log_record_factory()
DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"
MCP_OPENAPI_PATH = DOCS_ROOT / "mcp_openapi.yaml"
ASSET_VERSION = resolve_asset_version()


def _read_positive_int_env(name: str, default: int, minimum: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        LOGGER.warning("Invalid integer for %s=%r; using default=%d", name, raw, default)
        return default


_BANDWIDTH_DEFAULT_BYTES = 256 * 1024
_BANDWIDTH_MAX_BYTES = 4 * 1024 * 1024
_BANDWIDTH_CHUNK_BYTES = 64 * 1024
_BANDWIDTH_PATTERN = b"weppcloud-diagnostics-bandwidth-probe-"
_BANDWIDTH_MAX_CONCURRENT = _read_positive_int_env("QUERY_ENGINE_BANDWIDTH_MAX_CONCURRENT", 4, 1)
_BANDWIDTH_SEMAPHORE_WAIT_SECONDS = _read_positive_int_env(
    "QUERY_ENGINE_BANDWIDTH_SEMAPHORE_WAIT_SECONDS",
    5,
    1,
)
_BANDWIDTH_REQUEST_TIMEOUT_SECONDS = _read_positive_int_env(
    "QUERY_ENGINE_BANDWIDTH_REQUEST_TIMEOUT_SECONDS",
    15,
    1,
)
_BANDWIDTH_RATE_LIMIT_MAX_REQUESTS = _read_positive_int_env(
    "QUERY_ENGINE_BANDWIDTH_RATE_LIMIT_MAX_REQUESTS",
    12,
    1,
)
_BANDWIDTH_RATE_LIMIT_WINDOW_SECONDS = _read_positive_int_env(
    "QUERY_ENGINE_BANDWIDTH_RATE_LIMIT_WINDOW_SECONDS",
    30,
    1,
)
_BANDWIDTH_RATE_LIMIT_MAX_BUCKETS = _read_positive_int_env(
    "QUERY_ENGINE_BANDWIDTH_RATE_LIMIT_MAX_BUCKETS",
    2048,
    128,
)
_BANDWIDTH_SEMAPHORE = asyncio.Semaphore(_BANDWIDTH_MAX_CONCURRENT)
_BANDWIDTH_RATE_LIMIT_LOCK = threading.Lock()
_BANDWIDTH_RATE_LIMIT_BUCKETS: OrderedDict[str, deque[float]] = OrderedDict()


def _set_no_store_header(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    return response


def _bandwidth_json(payload: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return _set_no_store_header(JSONResponse(payload, status_code=status_code))


def _bandwidth_error(status_code: int, message: str, code: str, *, retry_after: int | None = None) -> JSONResponse:
    response = _bandwidth_json(
        {"error": {"message": message, "code": code}, "status_code": status_code},
        status_code=status_code,
    )
    if retry_after is not None:
        response.headers["Retry-After"] = str(max(1, retry_after))
    return response


def _bandwidth_probe_bytes(value: str | None) -> tuple[int | None, JSONResponse | None]:
    if value is None or not value.strip():
        return _BANDWIDTH_DEFAULT_BYTES, None
    token = value.strip()
    try:
        parsed = int(token)
    except ValueError:
        return None, _bandwidth_error(
            400,
            "Query parameter 'bytes' must be an integer.",
            "invalid_probe_size",
        )

    if parsed <= 0:
        return None, _bandwidth_error(
            400,
            "Query parameter 'bytes' must be greater than zero.",
            "invalid_probe_size",
        )
    if parsed > _BANDWIDTH_MAX_BYTES:
        return None, _bandwidth_error(
            413,
            f"Requested size exceeds maximum {_BANDWIDTH_MAX_BYTES} bytes.",
            "probe_too_large",
        )

    return parsed, None


def _normalized_origin(origin: str) -> tuple[str, str, int] | None:
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.hostname:
        return None
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    if parsed.port is not None:
        port = parsed.port
    elif scheme == "https":
        port = 443
    elif scheme == "http":
        port = 80
    else:
        return None
    return scheme, host, port


def _request_allowed_origins(request: StarletteRequest) -> set[tuple[str, str, int]]:
    origins: set[tuple[str, str, int]] = set()
    if request.url.hostname:
        port = request.url.port
        if port is None:
            if request.url.scheme == "https":
                port = 443
            elif request.url.scheme == "http":
                port = 80
        if port is not None:
            origins.add((request.url.scheme.lower(), request.url.hostname.lower(), port))

    host = (request.headers.get("host") or "").strip()
    if host:
        scheme = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").split(",")[0].strip()
        candidate = _normalized_origin(f"{scheme}://{host}")
        if candidate is not None:
            origins.add(candidate)

    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if forwarded_host:
        forwarded_scheme = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").split(",")[0].strip()
        candidate = _normalized_origin(f"{forwarded_scheme}://{forwarded_host}")
        if candidate is not None:
            origins.add(candidate)

    return origins


def _is_same_origin_request(request: StarletteRequest) -> bool:
    origin = (request.headers.get("origin") or "").strip()
    if not origin:
        return True
    normalized_origin = _normalized_origin(origin)
    if normalized_origin is None:
        return False
    return normalized_origin in _request_allowed_origins(request)


def _trusted_client_host(request: StarletteRequest) -> str:
    # Trust the right-most X-Forwarded-For hop as the proxy-inserted client address.
    forwarded_for = str(request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded_for:
        tokens = [token.strip() for token in forwarded_for.split(",") if token.strip()]
        if tokens:
            return tokens[-1]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _bandwidth_rate_limit_key(request: StarletteRequest) -> str:
    return f"{_trusted_client_host(request)}:{request.url.path}"


def _bandwidth_rate_limit_allow(key: str) -> tuple[bool, int]:
    now = time.monotonic()
    with _BANDWIDTH_RATE_LIMIT_LOCK:
        while len(_BANDWIDTH_RATE_LIMIT_BUCKETS) > _BANDWIDTH_RATE_LIMIT_MAX_BUCKETS:
            _BANDWIDTH_RATE_LIMIT_BUCKETS.popitem(last=False)

        window = _BANDWIDTH_RATE_LIMIT_WINDOW_SECONDS
        cutoff = now - window
        bucket = _BANDWIDTH_RATE_LIMIT_BUCKETS.get(key)
        if bucket is None:
            bucket = deque()
            _BANDWIDTH_RATE_LIMIT_BUCKETS[key] = bucket
        else:
            _BANDWIDTH_RATE_LIMIT_BUCKETS.move_to_end(key)

        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= _BANDWIDTH_RATE_LIMIT_MAX_REQUESTS:
            retry_after = int(math.ceil((bucket[0] + window) - now))
            return False, max(1, retry_after)

        bucket.append(now)
        return True, 0


async def diagnostics_bandwidth_download(request: StarletteRequest) -> Response:
    if not _is_same_origin_request(request):
        return _bandwidth_error(
            403,
            "Cross-origin request blocked.",
            "cross_origin_blocked",
        )

    bytes_requested, parse_error = _bandwidth_probe_bytes(request.query_params.get("bytes"))
    if parse_error is not None:
        return parse_error
    assert bytes_requested is not None

    allowed, retry_after = _bandwidth_rate_limit_allow(_bandwidth_rate_limit_key(request))
    if not allowed:
        return _bandwidth_error(
            429,
            "Bandwidth diagnostics rate limit exceeded.",
            "rate_limited",
            retry_after=retry_after,
        )

    try:
        await asyncio.wait_for(_BANDWIDTH_SEMAPHORE.acquire(), timeout=_BANDWIDTH_SEMAPHORE_WAIT_SECONDS)
    except TimeoutError:
        return _bandwidth_error(
            503,
            "Bandwidth diagnostics service is busy. Retry shortly.",
            "busy",
        )

    async def _stream() -> Any:
        remaining = bytes_requested
        while remaining > 0:
            chunk_size = min(_BANDWIDTH_CHUNK_BYTES, remaining)
            repeats, remainder = divmod(chunk_size, len(_BANDWIDTH_PATTERN))
            chunk = (_BANDWIDTH_PATTERN * repeats) + _BANDWIDTH_PATTERN[:remainder]
            remaining -= chunk_size
            yield chunk
            await asyncio.sleep(0)

    try:
        response = _set_no_store_header(
            StreamingResponse(_stream(), media_type="application/octet-stream")
        )
        response.headers["Content-Length"] = str(bytes_requested)
        return response
    finally:
        _BANDWIDTH_SEMAPHORE.release()


async def diagnostics_bandwidth_upload(request: StarletteRequest) -> Response:
    if not _is_same_origin_request(request):
        return _bandwidth_error(
            403,
            "Cross-origin request blocked.",
            "cross_origin_blocked",
        )

    allowed, retry_after = _bandwidth_rate_limit_allow(_bandwidth_rate_limit_key(request))
    if not allowed:
        return _bandwidth_error(
            429,
            "Bandwidth diagnostics rate limit exceeded.",
            "rate_limited",
            retry_after=retry_after,
        )

    try:
        await asyncio.wait_for(_BANDWIDTH_SEMAPHORE.acquire(), timeout=_BANDWIDTH_SEMAPHORE_WAIT_SECONDS)
    except TimeoutError:
        return _bandwidth_error(
            503,
            "Bandwidth diagnostics service is busy. Retry shortly.",
            "busy",
        )

    started = time.monotonic()
    bytes_received = 0
    try:
        try:
            async with asyncio.timeout(_BANDWIDTH_REQUEST_TIMEOUT_SECONDS):
                async for chunk in request.stream():
                    if not chunk:
                        continue
                    bytes_received += len(chunk)
                    if bytes_received > _BANDWIDTH_MAX_BYTES:
                        return _bandwidth_error(
                            413,
                            f"Upload exceeds maximum {_BANDWIDTH_MAX_BYTES} bytes.",
                            "upload_too_large",
                        )
        except TimeoutError:
            return _bandwidth_error(
                408,
                "Upload timed out while reading request payload.",
                "upload_timeout",
            )
    finally:
        _BANDWIDTH_SEMAPHORE.release()

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return _bandwidth_json(
        {
            "ok": True,
            "bytes_received": bytes_received,
            "elapsed_ms": elapsed_ms,
            "max_bytes": _BANDWIDTH_MAX_BYTES,
        }
    )


def _render_mcp_openapi_yaml() -> str | None:
    """Render the MCP OpenAPI spec with runtime host overrides.

    Returns:
        Serialized YAML string or None when rendering fails.
    """
    try:
        raw_spec = MCP_OPENAPI_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        LOGGER.warning("Failed to read MCP OpenAPI spec at %s: %s", MCP_OPENAPI_PATH, exc)
        return None

    try:
        spec_data: dict[str, Any] = yaml.safe_load(raw_spec)
    except yaml.YAMLError as exc:
        LOGGER.warning("Failed to parse MCP OpenAPI spec: %s", exc)
        return None

    host = os.getenv("EXTERNAL_HOST")
    description = os.getenv("EXTERNAL_HOST_DESCRIPTION")

    if host:
        contact = spec_data.get("info", {}).get("contact")
        if isinstance(contact, dict):
            contact.setdefault("name", "WEPPcloud Dev")
            contact["url"] = f"https://{host}/weppcloud/"

        for server in spec_data.get("servers", []) or []:
            if isinstance(server, dict):
                server["url"] = f"https://{host}/query-engine/mcp"
                if description:
                    server["description"] = description
                elif not server.get("description"):
                    server["description"] = f"{host} deployment"
    elif description:
        for server in spec_data.get("servers", []) or []:
            if isinstance(server, dict) and not server.get("description"):
                server["description"] = description

    return yaml.safe_dump(spec_data, sort_keys=False)


async def query_engine_http_exception_handler(request: StarletteRequest, exc: HTTPException) -> JSONResponse:
    """Return structured JSON for HTTPException instances raised by Starlette.

    Args:
        request: Current Starlette request.
        exc: Raised HTTPException.

    Returns:
        JSONResponse with error metadata and optional stacktrace.
    """
    payload: dict[str, Any] = {
        "error": exc.detail if exc.detail else exc.__class__.__name__,
        "status_code": exc.status_code,
    }

    if exc.status_code >= 500:
        stacktrace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        payload["stacktrace"] = stacktrace
        LOGGER.exception("HTTPException %s for %s: %s", exc.status_code, request.url, exc.detail)
    else:
        LOGGER.warning("HTTPException %s for %s: %s", exc.status_code, request.url, exc.detail)

    return JSONResponse(payload, status_code=exc.status_code)


async def query_engine_exception_handler(request: StarletteRequest, exc: Exception) -> JSONResponse:
    """Catch-all handler that logs and serialises uncaught exceptions.

    Args:
        request: Current Starlette request.
        exc: Exception raised during processing.

    Returns:
        JSONResponse with stacktrace details.
    """
    stacktrace_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    stacktrace_text = "".join(stacktrace_lines)
    stacktrace_clean = stacktrace_text.strip("\n")
    message = _format_exception_message(exc)
    runid = request.path_params.get("runid")

    LOGGER.exception("Unhandled exception for %s", request.url)
    _log_exception_details(stacktrace_text, runid)

    payload = {
        "error": message,
        "stacktrace": stacktrace_text,
        "stacktrace_lines": stacktrace_clean.splitlines(),
        "exc_info": stacktrace_text,
        "status_code": 500,
    }
    return JSONResponse(payload, status_code=500)


def _format_exception_message(exc: BaseException) -> str:
    """Compose a concise exception message for JSON responses.

    Args:
        exc: Exception instance to summarise.

    Returns:
        Human-readable message combining exception type and detail.
    """
    try:
        detail = str(exc)
    except Exception:
        detail = repr(exc)

    if detail and detail != exc.__class__.__name__:
        return f"{exc.__class__.__name__}: {detail}"
    return exc.__class__.__name__


def _log_exception_details(stacktrace_text: str, runid: str | None) -> None:
    """Append stacktrace details to `<run>/exceptions.log` when possible.

    Args:
        stacktrace_text: Stacktrace text to append.
        runid: Run identifier used to resolve the filesystem path.
    """
    if not runid:
        return

    try:
        run_path = resolve_run_path(runid)
    except Exception:
        return

    log_path = run_path / "exceptions.log"
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().isoformat()}]\n")
            handle.write(stacktrace_text)
            handle.write("\n\n")
    except OSError:
        LOGGER.warning("Unable to append to query engine exception log for %s", runid, exc_info=True)


async def homepage(request: StarletteRequest) -> Response:
    """Serve a minimal landing page for manual testing.

    Args:
        request: Incoming Starlette request (unused).

    Returns:
        HTMLResponse with static instructions.
    """
    return HTMLResponse(
        "<h1>WEPPcloud Query Engine</h1><p>See /query/runs/&lt;runid&gt; for details.</p>"
    )


async def run_info(request: StarletteRequest) -> Response:
    """Render a run summary page including catalog entry listings.

    Args:
        request: Current Starlette request with `runid` path parameter.

    Returns:
        TemplateResponse or JSON error when the run is missing.
    """
    runid_param: str = request.path_params["runid"]
    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        context = resolve_run_context(str(run_path), auto_activate=True, run_interchange=False)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    catalog_entries = context.catalog.entries()
    runid_str = str(run_path)
    slug = runid_param.strip("/") or runid_param
    schema_path = str(request.app.url_path_for("run_schema", runid=slug))
    query_path = str(request.app.url_path_for("run_query_endpoint", runid=slug))
    return TEMPLATES.TemplateResponse(
        "run_info.html",
        {
            "request": request,
            "runid": runid_str,
            "runid_slug": runid_str.lstrip("/"),
            "schema_path": schema_path,
            "query_path": query_path,
            "entry_count": len(catalog_entries),
            "catalog_entries": catalog_entries,
            "asset_version": ASSET_VERSION,
        },
    )


async def run_schema(request: StarletteRequest) -> Response:
    """Return the activated catalog entries for a run as JSON.

    Args:
        request: Starlette request referencing the runid path parameter.

    Returns:
        JSONResponse containing catalog entries or an error payload.
    """
    runid_param: str = request.path_params["runid"]
    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        context = resolve_run_context(str(run_path), auto_activate=True, run_interchange=False)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    data = {
        "runid": str(run_path),
        "entries": [asdict(entry) for entry in context.catalog.entries()],
    }
    return JSONResponse(data)


async def make_query_endpoint(request: StarletteRequest) -> Response:
    """Render the query console HTML page for a given run.

    Args:
        request: Starlette request containing the runid path parameter.

    Returns:
        TemplateResponse for the query console UI, or fallback text response.

    Note:
        Scenario queries should use the POST endpoint with a ``scenario``
        body parameter, NOT URL path manipulation.
    """
    runid_param: str = request.path_params["runid"]

    # Reject garbage paths that embed scenario/subpaths in the URL
    # Check for /_pups/ or /_outputs/ anywhere in path, or at end of path
    if (
        "/_pups/" in runid_param
        or "/_outputs/" in runid_param
        or runid_param.endswith("/_pups")
        or runid_param.endswith("/_outputs")
    ):
        return PlainTextResponse(
            "Invalid URL: scenario paths should not be in the URL. "
            "Use the 'scenario' body parameter in POST requests instead.",
            status_code=400,
        )

    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return PlainTextResponse(f"Run '{runid_param}' not found", status_code=404)

    catalog_entries = []
    catalog_ready = True
    sample_dataset = "landuse/landuse.parquet"

    try:
        context = resolve_run_context(str(run_path), auto_activate=True, run_interchange=False)
        catalog_entries = context.catalog.entries()
        if catalog_entries:
            # Use first parquet file, skip JSON/other metadata files
            for entry in catalog_entries:
                if entry.path.endswith('.parquet'):
                    sample_dataset = entry.path
                    break
    except FileNotFoundError:
        catalog_ready = False
    except Exception:  # pragma: no cover - defensive logging
        catalog_ready = False
        LOGGER.debug("Failed to load catalog for %s", run_path, exc_info=True)

    default_payload = OrderedDict([
        ("datasets", [sample_dataset]),
        ("limit", 25),
        ("include_schema", True),
    ])
    slug = runid_param.strip('/') or runid_param
    slug_parts = [part for part in slug.split('/') if part]
    run_name = slug_parts[0] if slug_parts else runid_param
    config_name = slug_parts[1] if len(slug_parts) > 1 else 'cfg'
    run_link = f"/weppcloud/runs/{run_name}/{config_name}"
    current_path = request.url.path.rstrip("/") or request.url.path or "/"
    if current_path.endswith("/query"):
        base_root = current_path[: -len("/query")] or "/"
        post_display = f"{base_root.rstrip('/') or ''}/query" if base_root != "/" else "/query"
    else:
        base_root = current_path.rsplit("/", 1)[0] or "/"
        post_display = current_path or "/"

    base_root_clean = base_root.rstrip("/")
    if base_root_clean and not base_root_clean.startswith("/"):
        base_root_clean = "/" + base_root_clean
    activate_display = f"{base_root_clean}/activate" if base_root_clean else "/activate"

    # Construct full POST URL including any proxy prefix (e.g., /query-engine)
    forwarded_prefix = request.headers.get("X-Forwarded-Prefix", "").rstrip("/")
    full_post_url = f"{forwarded_prefix}{current_path}" if forwarded_prefix else current_path

    return TEMPLATES.TemplateResponse(
        "query_console.html",
        {
            "request": request,
            "run_name": run_name,
            "config_name": config_name,
            "run_slug": slug,
            "run_link": run_link,
            "catalog_entries": catalog_entries[:20],
            "catalog_ready": catalog_ready,
            "default_payload": default_payload,
            "activate_url": "../activate",
            "activate_url_display": activate_display,
            "query_presets": QUERY_PRESETS,
            "post_url": full_post_url,
            "post_url_display": post_display,
            "asset_version": ASSET_VERSION,
        },
    )


async def run_query_endpoint(request: StarletteRequest) -> Response:
    """Execute a query payload posted from the web console.

    Args:
        request: Starlette request containing the runid and JSON body.

    Returns:
        JSONResponse containing query results or error details.

    Note:
        Scenario queries should use the ``scenario`` body parameter, NOT
        URL path manipulation. If you need scenario data, post::

            {"scenario": "mulch_30_sbs_map", "dataset_specs": [...]}

        Do NOT append ``_pups/omni/scenarios/...`` to the URL - this will
        result in a 400 error.
    """
    runid_param: str = request.path_params["runid"]

    # Reject garbage paths that embed scenario/subpaths in the URL
    # Users must use the body "scenario" parameter instead
    # Check for /_pups/ or /_outputs/ anywhere in path, or at end of path
    if (
        "/_pups/" in runid_param
        or "/_outputs/" in runid_param
        or runid_param.endswith("/_pups")
        or runid_param.endswith("/_outputs")
    ):
        return JSONResponse(
            {
                "error": (
                    "Invalid URL: scenario paths should not be in the URL. "
                    "Use the 'scenario' body parameter instead. "
                    "Example: POST {\"scenario\": \"mulch_30_sbs_map\", \"dataset_specs\": [...]}"
                ),
                "hint": "Remove '_pups/omni/scenarios/...' from URL and add 'scenario' to request body",
            },
            status_code=400,
        )

    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON payload"}, status_code=400)

    # Extract optional scenario from request body
    scenario = body.pop("scenario", None)

    try:
        context = resolve_run_context(str(run_path), scenario=scenario, auto_activate=True, run_interchange=False)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        payload = QueryRequest(**body)
    except (TypeError, ValueError) as exc:  # pragma: no cover - simple validation error reporting
        stacktrace_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        LOGGER.debug("Invalid query payload for %s: %s", run_path, exc, exc_info=True)
        return JSONResponse(
            {
                "error": f"Invalid query payload: {exc}",
                "stacktrace": stacktrace_text,
                "exc_info": stacktrace_text,
                "status_code": 422,
            },
            status_code=422,
        )

    missing = [spec.path for spec in payload.dataset_specs if not context.catalog.has(spec.path)]
    if missing:
        message = f"Dataset(s) not found: {', '.join(missing)}"
        stacktrace_text = "".join(traceback.format_stack())
        LOGGER.warning("Query referenced missing datasets for %s: %s", run_path, missing)
        return JSONResponse(
            {
                "error": message,
                "stacktrace": stacktrace_text,
                "exc_info": stacktrace_text,
                "status_code": 404,
            },
            status_code=404,
        )

    try:
        result = run_query(context, payload)
    except FileNotFoundError as exc:
        stacktrace_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        LOGGER.warning("Query dataset missing for %s", run_path, exc_info=True)
        return JSONResponse(
            {"error": str(exc), "stacktrace": stacktrace_text, "exc_info": stacktrace_text, "status_code": 404},
            status_code=404,
        )
    except ValueError as exc:
        stacktrace_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        LOGGER.debug("Query validation error for %s: %s", run_path, exc, exc_info=True)
        return JSONResponse(
            {
                "error": str(exc),
                "stacktrace": stacktrace_text,
                "exc_info": stacktrace_text,
                "status_code": 422,
            },
            status_code=422,
        )
    except Exception as exc:  # pragma: no cover - defensive error reporting
        stacktrace_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        LOGGER.exception("Query execution failed for %s", run_path)
        _log_exception_details(stacktrace_text, runid_param)
        return JSONResponse(
            {
                "error": f"Query execution failed: {exc}",
                "stacktrace": stacktrace_text,
                "stacktrace_lines": stacktrace_text.strip("\n").splitlines(),
                "exc_info": stacktrace_text,
                "status_code": 500,
            },
            status_code=500,
        )

    response_payload = {
        "records": result.records,
        "schema": result.schema,
        "row_count": result.row_count,
    }
    if result.formatted is not None:
        response_payload["formatted"] = result.formatted
    if result.sql is not None:
        response_payload["sql"] = result.sql

    return JSONResponse(response_payload)


async def activate_run(request: StarletteRequest) -> Response:
    """Trigger activation via the HTTP console endpoints.

    Args:
        request: Starlette request containing the runid path parameter.

    Returns:
        JSONResponse describing activation status.
    """
    runid_param: str = request.path_params["runid"]

    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        catalog = activate_query_engine(run_path, force_refresh=True)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)
    except Exception as exc:
        stacktrace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        LOGGER.exception("Activation failed for %s", run_path)
        return JSONResponse({"error": f"Activation failed: {exc}", "stacktrace": stacktrace}, status_code=500)

    return JSONResponse(catalog)


class _HealthLogFilter(logging.Filter):
    """Suppress /health log entries from access logs."""

    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        return '/health' not in message


_health_log_filter = _HealthLogFilter()
for _log_name in ('uvicorn.access', 'gunicorn.access'):
    logging.getLogger(_log_name).addFilter(_health_log_filter)

def health(_: StarletteRequest):
    """Return a plain-text OK response for container health checks.

    Args:
        _: Unused Starlette request.

    Returns:
        PlainTextResponse containing 'OK'.
    """
    return PlainTextResponse('OK')


async def mcp_openapi_spec(_: StarletteRequest) -> Response:
    """Serve the MCP OpenAPI specification if available.

    Args:
        _: Unused Starlette request.

    Returns:
        Response containing YAML or a PlainTextResponse error.
    """
    if not MCP_OPENAPI_PATH.is_file():
        LOGGER.warning("MCP OpenAPI spec not found at %s", MCP_OPENAPI_PATH)
        return PlainTextResponse("OpenAPI specification not found", status_code=404)
    rendered = _render_mcp_openapi_yaml()
    if rendered is None:
        return PlainTextResponse("Failed to render OpenAPI specification", status_code=500)
    return Response(rendered, media_type="application/yaml")


def create_app() -> Starlette:
    """Create the full Starlette application (HTML + MCP mount if configured).

    Returns:
        Configured Starlette application instance.
    """
    routes = [
        Route(
            '/health',
            health,
            methods=['GET']
        ),
        Route(
            "/diagnostics/bandwidth/download",
            diagnostics_bandwidth_download,
            methods=["GET"],
            name="diagnostics_bandwidth_download",
        ),
        Route(
            "/diagnostics/bandwidth/upload",
            diagnostics_bandwidth_upload,
            methods=["POST"],
            name="diagnostics_bandwidth_upload",
        ),
        Route("/", homepage, name="homepage"),
        Route("/runs/{runid:path}/activate", activate_run, methods=["GET", "POST"], name="activate_run"),
        Route("/runs/{runid:path}/activate/", activate_run, methods=["GET", "POST"], name="activate_run_slash"),
        Route("/runs/{runid:path}/schema", run_schema, methods=["GET"], name="run_schema"),
        Route("/runs/{runid:path}/schema/", run_schema, methods=["GET"], name="run_schema_slash"),
        Route("/runs/{runid:path}/query", make_query_endpoint, methods=["GET"], name="run_query_console"),
        Route("/runs/{runid:path}/query", run_query_endpoint, methods=["POST"], name="run_query_endpoint"),
        Route("/runs/{runid:path}/query/", make_query_endpoint, methods=["GET"], name="run_query_console_slash"),
        Route("/runs/{runid:path}/query/", run_query_endpoint, methods=["POST"], name="run_query_endpoint_slash"),
        Route("/runs/{runid:path}", run_info, methods=["GET"], name="run_info"),
        Route("/runs/{runid:path}/", run_info, methods=["GET"], name="run_info_slash"),
        Route("/docs/mcp_openapi.yaml", mcp_openapi_spec, methods=["GET"], name="mcp_openapi_spec"),
    ]

    exception_handlers = {
        HTTPException: query_engine_http_exception_handler,
        Exception: query_engine_exception_handler,
    }

    if get_secret("WEPP_MCP_JWT_SECRET"):
        try:
            from .mcp import create_mcp_app

            mcp_app = create_mcp_app()
        except RuntimeError as exc:
            LOGGER.warning("Failed to initialise MCP API: %s", exc, exc_info=True)
        else:
            routes.append(Mount("/mcp", app=mcp_app))
            LOGGER.info("MCP API mounted at /mcp")
    else:
        LOGGER.info("WEPP_MCP_JWT_SECRET not configured; MCP API disabled")

    app = Starlette(debug=False, routes=routes, exception_handlers=exception_handlers)

    # Add CORS middleware to allow cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
        allow_headers=["*"],  # Allow all headers
    )

    @app.middleware("http")
    async def correlation_id_middleware(request: StarletteRequest, call_next):
        inbound_id = select_inbound_correlation_id(request.headers.get(CORRELATION_ID_HEADER))
        correlation_id, token = bind_correlation_id(inbound_id)
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            reset_correlation_id(token)

    return app
