from __future__ import annotations

import os
import json
import logging
import traceback
from collections import OrderedDict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    Response,
    PlainTextResponse,
)
from starlette.exceptions import HTTPException
from starlette.routing import Route, Mount
from starlette.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader


from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest
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
DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"
MCP_OPENAPI_PATH = DOCS_ROOT / "mcp_openapi.yaml"


def _render_mcp_openapi_yaml() -> str | None:
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
    try:
        detail = str(exc)
    except Exception:
        detail = repr(exc)

    if detail and detail != exc.__class__.__name__:
        return f"{exc.__class__.__name__}: {detail}"
    return exc.__class__.__name__


def _log_exception_details(stacktrace_text: str, runid: str | None) -> None:
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
    return HTMLResponse(
        "<h1>WEPPcloud Query Engine</h1><p>See /query/runs/&lt;runid&gt; for details.</p>"
    )


async def run_info(request: StarletteRequest) -> Response:
    runid_param: str = request.path_params["runid"]
    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        activate_query_engine(run_path, run_interchange=False)
        context = resolve_run_context(str(run_path), auto_activate=False)
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
        },
    )


async def run_schema(request: StarletteRequest) -> Response:
    runid_param: str = request.path_params["runid"]
    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        activate_query_engine(run_path, run_interchange=False)
        context = resolve_run_context(str(run_path), auto_activate=False)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    data = {
        "runid": str(run_path),
        "entries": [asdict(entry) for entry in context.catalog.entries()],
    }
    return JSONResponse(data)


async def make_query_endpoint(request: StarletteRequest) -> Response:
    runid_param: str = request.path_params["runid"]
    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return PlainTextResponse(f"Run '{runid_param}' not found", status_code=404)

    catalog_entries = []
    catalog_ready = True
    sample_dataset = "landuse/landuse.parquet"

    try:
        context = resolve_run_context(str(run_path), auto_activate=False)
        catalog_entries = context.catalog.entries()
        if catalog_entries:
            sample_dataset = catalog_entries[0].path
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
    post_path = str(request.app.url_path_for("run_query_endpoint", runid=slug))
    activate_path = str(request.app.url_path_for("activate_run", runid=slug))

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
            "activate_url": activate_path,
            "query_presets": QUERY_PRESETS,
            "post_url": post_path,
            "post_url_display": post_path,
        },
    )


async def run_query_endpoint(request: StarletteRequest) -> Response:
    runid_param: str = request.path_params["runid"]
    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON payload"}, status_code=400)

    try:
        activate_query_engine(run_path, run_interchange=False)
        context = resolve_run_context(str(run_path), auto_activate=False)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        payload = QueryRequest(**body)
    except Exception as exc:  # pragma: no cover - simple validation error reporting
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
    runid_param: str = request.path_params["runid"]

    try:
        run_path = resolve_run_path(runid_param)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)

    try:
        catalog = activate_query_engine(run_path)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{runid_param}' not found"}, status_code=404)
    except Exception as exc:
        stacktrace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        LOGGER.exception("Activation failed for %s", run_path)
        return JSONResponse({"error": f"Activation failed: {exc}", "stacktrace": stacktrace}, status_code=500)

    return JSONResponse(catalog)


class _HealthLogFilter(logging.Filter):
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
    return PlainTextResponse('OK')


async def mcp_openapi_spec(_: StarletteRequest) -> Response:
    if not MCP_OPENAPI_PATH.is_file():
        LOGGER.warning("MCP OpenAPI spec not found at %s", MCP_OPENAPI_PATH)
        return PlainTextResponse("OpenAPI specification not found", status_code=404)
    rendered = _render_mcp_openapi_yaml()
    if rendered is None:
        return PlainTextResponse("Failed to render OpenAPI specification", status_code=500)
    return Response(rendered, media_type="application/yaml")


def create_app() -> Starlette:
    routes = [
        Route(
            '/health',
            health,
            methods=['GET']
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

    if os.getenv("WEPP_MCP_JWT_SECRET"):
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
    
    return app
