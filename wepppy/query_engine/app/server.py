from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import logging

from starlette.applications import Starlette
from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, JSONResponse, Response, PlainTextResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates


from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


async def homepage(request: StarletteRequest) -> Response:
    return HTMLResponse(
        "<h1>WEPPcloud Query Engine</h1><p>See /query/runs/&lt;runid&gt; for details.</p>"
    )


async def run_info(request: StarletteRequest) -> Response:
    runid_param: str = request.path_params["runid"]
    run_path = Path("/" + runid_param).resolve()
    try:
        activate_query_engine(run_path, run_interchange=False)
        context = resolve_run_context(str(run_path), auto_activate=False)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{run_path}' not found"}, status_code=404)

    catalog_entries = context.catalog.entries()
    runid_str = str(run_path)
    return TEMPLATES.TemplateResponse(
        "run_info.html",
        {
            "request": request,
            "runid": runid_str,
            "runid_slug": runid_str.lstrip("/"),
            "entry_count": len(catalog_entries),
            "catalog_entries": catalog_entries,
        },
    )


async def run_schema(request: StarletteRequest) -> Response:
    runid_param: str = request.path_params["runid"]
    run_path = Path("/" + runid_param).resolve()
    try:
        activate_query_engine(run_path, run_interchange=False)
        context = resolve_run_context(str(run_path), auto_activate=False)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{run_path}' not found"}, status_code=404)

    data = {
        "runid": str(run_path),
        "entries": [entry.__dict__ for entry in context.catalog.entries()],
    }
    return JSONResponse(data)


async def run_query_endpoint(request: StarletteRequest) -> Response:
    runid_param: str = request.path_params["runid"]
    run_path = Path("/" + runid_param).resolve()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON payload"}, status_code=400)

    try:
        activate_query_engine(run_path, run_interchange=False)
        context = resolve_run_context(str(run_path), auto_activate=False)
    except FileNotFoundError:
        return JSONResponse({"error": f"Run '{run_path}' not found"}, status_code=404)

    try:
        payload = QueryRequest(**body)
    except Exception as exc:  # pragma: no cover - simple validation error reporting
        return JSONResponse({"error": f"Invalid query payload: {exc}"}, status_code=422)

    result = run_query(context, payload)
    return JSONResponse({
        "records": result.records,
        "schema": result.schema,
        "row_count": result.row_count,
    })

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


def create_app() -> Starlette:
    routes = [
        Route(
            '/health',
            health,
            methods=['GET']
        ),
        Route("/", homepage),
        Route("/query/runs/{runid:path}", run_info, methods=["GET"]),
        Route("/query/runs/{runid:path}/schema", run_schema, methods=["GET"]),
        Route("/query/runs/{runid:path}/query", run_query_endpoint, methods=["POST"]),
    ]

    app = Starlette(debug=False, routes=routes)
    return app
