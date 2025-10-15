from __future__ import annotations

import json
import logging
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..helpers import resolve_run_path
from ..query_presets import QUERY_PRESETS
from .auth import (
    MCPAuthMiddleware,
    MCPPrincipal,
    get_auth_config,
    get_principal,
    require_scope,
)
from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest

LOGGER = logging.getLogger(__name__)
SERVICE_NAME = "weppcloud-query-engine"
SERVICE_VERSION = os.getenv("WEPP_MCP_SERVICE_VERSION") or os.getenv("WEPP_RELEASE") or "unknown"
IGNORED_CATALOG_PREFIXES = (".mypy_cache/", ".mypy_cache", "_query_engine/", "_query_engine")
EXCLUDED_DATASET_PATTERNS = (
    ("ash/", "H", ".parquet"),
)
PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompt_templates" / "llm_query_prompt.md"
DEFAULT_PROMPT_ROW_LIMIT = 25


class QueryValidationException(Exception):
    def __init__(self, status_code: int, code: str, detail: str, meta: Mapping[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.meta = dict(meta or {})


def _with_trace_id(meta: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(meta or {})
    payload.setdefault("trace_id", uuid4().hex)
    return payload


def _error_response(status_code: int, code: str, detail: str, error_meta: Mapping[str, Any] | None = None) -> JSONResponse:
    error_entry = {"code": code, "detail": detail}
    if error_meta:
        error_entry["meta"] = dict(error_meta)
    return JSONResponse({"errors": [error_entry], "meta": _with_trace_id({})}, status_code=status_code)


def _normalise_leading_slash(path: str) -> str:
    if not path.startswith("/"):
        return "/" + path
    return path


def _join_path(root_path: str, suffix: str) -> str:
    if not root_path:
        return _normalise_leading_slash(suffix)
    base = root_path.rstrip("/")
    return _normalise_leading_slash(f"{base}/{suffix.lstrip('/')}")


def _absolute_url(request: Request, path: str) -> str:
    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}{path}"


def _load_catalog_data(run_path: os.PathLike[str]) -> tuple[list[dict[str, Any]], str | None]:
    catalog_path = resolve_catalog_path(run_path)
    if not catalog_path.exists():
        raise FileNotFoundError(catalog_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    files = data.get("files")
    entries = files if isinstance(files, list) else []
    generated_at = data.get("generated_at") or data.get("generatedAt")
    return entries, generated_at


def _load_catalog_metadata(run_path: os.PathLike[str]) -> tuple[bool, str | None, int]:
    try:
        entries, generated_at = _load_catalog_data(run_path)
    except FileNotFoundError:
        return False, None, 0
    except Exception:  # pragma: no cover - malformed catalog files
        LOGGER.warning("Failed to parse catalog for %s", run_path, exc_info=True)
        return True, None, 0
    dataset_count = len(entries)
    return True, generated_at, dataset_count


def resolve_catalog_path(run_path: os.PathLike[str]) -> Path:
    return Path(run_path) / "_query_engine" / "catalog.json"


async def ping(request: Request) -> JSONResponse:
    principal = get_principal(request)
    data: dict[str, Any] = {
        "type": "mcp_ping",
        "attributes": {
            "service": SERVICE_NAME,
            "status": "ok",
            "principal": principal.subject,
        },
    }
    if SERVICE_VERSION:
        data["attributes"]["version"] = SERVICE_VERSION

    meta = _with_trace_id({
        "timestamp": int(time.time()),
    })

    return JSONResponse({"data": data, "meta": meta})


def _parse_positive_int(value: str | None, *, field: str, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an integer")
    if parsed < minimum:
        raise ValueError(f"{field} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{field} must be <= {maximum}")
    return parsed


def _parse_optional_positive_int(value: str | None, *, field: str, minimum: int = 1, maximum: int | None = None) -> int | None:
    if value is None:
        return None
    parsed = _parse_positive_int(value, field=field, default=minimum, minimum=minimum, maximum=maximum)
    return parsed


def _get_query_param(params: Mapping[str, Any], *names: str) -> str | None:
    for name in names:
        value = params.get(name)
        if value is not None:
            return value
    return None


def _parse_bool(value: str | None, *, field: str, default: bool) -> bool:
    if value is None:
        return default
    value_lower = value.strip().lower()
    if value_lower in {"1", "true", "yes", "on"}:
        return True
    if value_lower in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{field} must be a boolean")


def _resolve_run_entry(request: Request, runid: str) -> tuple[Path, dict[str, Any]]:
    try:
        run_path = resolve_run_path(runid)
    except FileNotFoundError:
        raise

    activated, generated_at, dataset_count = _load_catalog_metadata(run_path)
    root_path = request.scope.get("root_path", "")
    self_path = _join_path(root_path, f"runs/{runid}")
    catalog_path = _join_path(root_path, f"runs/{runid}/catalog")
    query_execute_path = _join_path(root_path, f"runs/{runid}/queries/execute")
    query_validate_path = _join_path(root_path, f"runs/{runid}/queries/validate")
    activate_path = _join_path(root_path, f"runs/{runid}/activate")

    attributes = {
        "path": str(run_path),
        "activated": activated,
        "last_catalog_refresh": generated_at,
        "dataset_count": dataset_count,
    }

    links = {
        "self": _absolute_url(request, self_path),
        "catalog": _absolute_url(request, catalog_path),
        "query": _absolute_url(request, query_execute_path),
        "query_execute": _absolute_url(request, query_execute_path),
        "query_validate": _absolute_url(request, query_validate_path),
        "activate": _absolute_url(request, activate_path),
    }

    entry = {
        "id": runid,
        "type": "run",
        "attributes": attributes,
        "links": links,
    }
    return run_path, entry


def _principal_has_run(principal: MCPPrincipal, runid: str) -> bool:
    if principal.run_ids is None:
        return False
    return runid in principal.run_ids


def _is_excluded_dataset(path: str) -> bool:
    normalized = path.replace("\\", "/")
    normalized_lower = normalized.lower()

    def _has_ash_segment(value: str) -> bool:
        if value.startswith("ash/"):
            return True
        parts = value.split("/")
        return "ash" in parts[:-1]

    if _has_ash_segment(normalized_lower):
        return True
    if normalized_lower.startswith("ash") and (normalized_lower.endswith(".nodb") or normalized_lower.endswith(".json")):
        return True
    # Legacy pattern matching for simple prefix/suffix pairs.
    for prefix, startswith, suffix in EXCLUDED_DATASET_PATTERNS:
        if normalized.startswith(prefix) and normalized[len(prefix):].startswith(startswith) and normalized.endswith(suffix):
            return True
    return False


def _filter_catalog_entries(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "")
        normalized = path.replace("\\", "/")
        if any(normalized.startswith(prefix) or f"/{prefix}" in normalized for prefix in IGNORED_CATALOG_PREFIXES):
            continue
        if _is_excluded_dataset(normalized):
            continue
        filtered.append(entry)
    return filtered


def _clone_entry(entry: dict[str, Any], *, include_fields: bool, field_limit: int | None) -> dict[str, Any]:
    clone = dict(entry)
    if not include_fields:
        clone.pop("schema", None)
        return clone

    schema = clone.get("schema")
    if isinstance(schema, dict):
        schema_clone = dict(schema)
        fields = schema.get("fields")
        if isinstance(fields, list):
            processed_fields = []
            for field in fields:
                if isinstance(field, dict):
                    processed_fields.append(dict(field))
                else:
                    processed_fields.append(field)
                if field_limit is not None and len(processed_fields) >= field_limit:
                    break
            schema_clone["fields"] = processed_fields
        clone["schema"] = schema_clone
    elif schema is not None:
        clone["schema"] = schema
    return clone


async def get_catalog(request: Request) -> JSONResponse:
    runid = request.path_params.get("runid") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, runid):
        return _error_response(404, "not_found", f"Run '{runid}' is not accessible")

    try:
        run_path = resolve_run_path(runid)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")

    try:
        raw_entries, generated_at = _load_catalog_data(run_path)
    except FileNotFoundError:
        return _error_response(404, "catalog_missing", f"Catalog for run '{runid}' not found")
    except Exception as exc:  # pragma: no cover - malformed catalog files
        LOGGER.warning("Failed to parse catalog for %s", runid, exc_info=True)
        return _error_response(500, "catalog_invalid", f"Catalog for run '{runid}' is invalid")

    try:
        include_fields = _parse_bool(
            _get_query_param(request.query_params, "include_fields", "include-fields"),
            field="include_fields",
            default=True,
        )
        fields_limit = _parse_optional_positive_int(
            _get_query_param(request.query_params, "limit[fields]", "limit_fields"),
            field="limit[fields]",
            minimum=1,
            maximum=1000,
        )
    except ValueError as exc:
        return _error_response(400, "invalid_request", str(exc))

    filtered_entries = _filter_catalog_entries(raw_entries)
    filtered_total = len(filtered_entries)

    data = [
        _clone_entry(entry, include_fields=include_fields, field_limit=fields_limit if include_fields else None)
        for entry in filtered_entries
    ]

    total_items = len(data)
    total_pages = 1 if total_items else 0
    page_number = 1 if total_items else 0

    meta = {
        "catalog": {
            "generated_at": generated_at,
            "total": len(raw_entries),
            "filtered": filtered_total,
            "returned": len(data),
        },
        "limits": {
            "fields": fields_limit,
            "include_fields": include_fields,
        },
        "page": {
            "size": total_items,
            "number": page_number,
            "offset": 0,
            "total_pages": total_pages,
            "total_items": total_items,
        },
    }
    meta = _with_trace_id(meta)
    links = {
        "self": str(request.url),
    }
    return JSONResponse({"data": data, "meta": meta, "links": links})


async def get_run(request: Request) -> JSONResponse:
    runid = request.path_params.get("runid") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, runid):
        return _error_response(404, "not_found", f"Run '{runid}' is not accessible")

    try:
        run_path, entry = _resolve_run_entry(request, runid)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")

    activated, generated_at, dataset_count = _load_catalog_metadata(run_path)
    meta: dict[str, Any] = {
        "catalog": {
            "activated": activated,
            "dataset_count": dataset_count,
            "generated_at": generated_at,
        }
    }
    meta = _with_trace_id(meta)
    return JSONResponse({"data": entry, "meta": meta})


async def validate_query(request: Request) -> JSONResponse:
    runid = request.path_params.get("runid") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, runid):
        return _error_response(404, "not_found", f"Run '{runid}' is not accessible")

    if not (principal.has_scope("queries:validate") or principal.has_scope("queries:execute")):
        return _error_response(403, "forbidden", "Token lacks query validation scope")

    try:
        run_path = resolve_run_path(runid)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return _error_response(400, "invalid_request", "Request body must be valid JSON")

    if not isinstance(payload, Mapping):
        return _error_response(400, "invalid_request", "Request body must be a JSON object")

    try:
        query_request, normalized_payload, raw_entries, generated_at = _prepare_query_request(
            payload,
            runid=runid,
            run_path=run_path,
        )
    except QueryValidationException as exc:
        return _error_response(exc.status_code, exc.code, exc.detail, exc.meta)

    data = {
        "type": "query_validation",
        "attributes": {
            "normalized_payload": normalized_payload,
            "warnings": [],
            "missing_datasets": [],
        },
    }
    meta = {
        "catalog": {
            "generated_at": generated_at,
            "dataset_count": len(raw_entries),
        }
    }
    meta = _with_trace_id(meta)
    return JSONResponse({"data": data, "meta": meta})


async def execute_query(request: Request) -> JSONResponse:
    runid = request.path_params.get("runid") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, runid):
        return _error_response(404, "not_found", f"Run '{runid}' is not accessible")

    if not principal.has_scope("queries:execute"):
        return _error_response(403, "forbidden", "Token lacks query execution scope")

    try:
        dry_run = _parse_bool(request.query_params.get("dry_run"), field="dry_run", default=False)
    except ValueError as exc:
        return _error_response(400, "invalid_request", str(exc))

    try:
        run_path = resolve_run_path(runid)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return _error_response(400, "invalid_request", "Request body must be valid JSON")

    if not isinstance(payload, Mapping):
        return _error_response(400, "invalid_request", "Request body must be a JSON object")

    try:
        query_request, normalized_payload, raw_entries, generated_at = _prepare_query_request(
            payload,
            runid=runid,
            run_path=run_path,
        )
    except QueryValidationException as exc:
        return _error_response(exc.status_code, exc.code, exc.detail, exc.meta)

    execution_meta: dict[str, Any] = {"dry_run": dry_run}

    if dry_run:
        execution_meta["row_count"] = 0
        data = {
            "type": "query_execute",
            "attributes": {
                "normalized_payload": normalized_payload,
                "warnings": [],
                "dry_run": True,
            },
        }
        meta = {
            "catalog": {
                "generated_at": generated_at,
                "dataset_count": len(raw_entries),
            },
            "execution": execution_meta,
        }
        meta = _with_trace_id(meta)
        return JSONResponse({"data": data, "meta": meta})

    try:
        context = resolve_run_context(str(run_path), auto_activate=False)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning("Failed to resolve run context for %s", runid, exc_info=True)
        return _error_response(500, "context_unavailable", f"Unable to resolve run context: {exc}")

    started = time.perf_counter()

    try:
        result = run_query(context, query_request)
    except FileNotFoundError as exc:
        return _error_response(404, "dataset_missing", str(exc))
    except ValueError as exc:
        return _error_response(422, "invalid_payload", str(exc))
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.exception("Query execution failed for %s", runid)
        return _error_response(500, "execution_failed", f"Query execution failed: {exc}")
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)

    execution_meta.update({
        "duration_ms": duration_ms,
        "row_count": result.row_count,
    })

    result_payload: dict[str, Any] = {
        "records": result.records,
        "row_count": result.row_count,
    }
    if result.schema is not None:
        result_payload["schema"] = result.schema
    if result.formatted is not None:
        result_payload["formatted"] = result.formatted
    if result.sql is not None:
        result_payload["sql"] = result.sql

    data = {
        "type": "query_execute",
        "attributes": {
            "normalized_payload": normalized_payload,
            "warnings": [],
            "dry_run": False,
            "result": result_payload,
        },
    }
    meta = {
        "catalog": {
            "generated_at": generated_at,
            "dataset_count": len(raw_entries),
        },
        "execution": execution_meta,
    }
    meta = _with_trace_id(meta)
    return JSONResponse({"data": data, "meta": meta})


async def activate_run_endpoint(request: Request) -> JSONResponse:
    runid = request.path_params.get("runid") or ""
    principal = require_scope(request, "runs:activate")

    if not _principal_has_run(principal, runid):
        return _error_response(404, "not_found", f"Run '{runid}' is not accessible")

    try:
        run_path = resolve_run_path(runid)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")

    try:
        catalog = activate_query_engine(run_path)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.exception("Activation failed for %s", runid)
        return _error_response(500, "activation_failed", f"Activation failed: {exc}")

    generated_at = catalog.get("generated_at") if isinstance(catalog, Mapping) else None
    dataset_count = len(catalog.get("files", [])) if isinstance(catalog, Mapping) else 0

    data = {
        "type": "activation_job",
        "attributes": {
            "runid": runid,
            "status": "completed",
            "generated_at": generated_at,
            "dataset_count": dataset_count,
        },
    }
    meta = _with_trace_id({
        "catalog": {
            "generated_at": generated_at,
            "dataset_count": dataset_count,
        }
    })
    return JSONResponse({"data": data, "meta": meta})


async def get_presets(request: Request) -> JSONResponse:
    runid = request.path_params.get("runid") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, runid):
        return _error_response(404, "not_found", f"Run '{runid}' is not accessible")

    categories = [
        {
            "category": category,
            "presets": presets,
        }
        for category, presets in QUERY_PRESETS.items()
    ]
    preset_count = sum(len(presets) for presets in QUERY_PRESETS.values())

    data = {
        "type": "preset_collection",
        "attributes": {
            "categories": categories,
        },
    }
    meta = _with_trace_id(
        {
            "categories": len(categories),
            "presets": preset_count,
        }
    )
    return JSONResponse({"data": data, "meta": meta})


async def get_prompt_template(request: Request) -> JSONResponse:
    runid = request.path_params.get("runid") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, runid):
        return _error_response(404, "not_found", f"Run '{runid}' is not accessible")

    try:
        run_path = resolve_run_path(runid)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")

    try:
        raw_entries, generated_at = _load_catalog_data(run_path)
    except FileNotFoundError:
        raw_entries, generated_at = [], None
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning("Failed to parse catalog for %s", runid, exc_info=True)
        raw_entries, generated_at = [], None

    schema_summary = _build_schema_summary(raw_entries)
    default_payload = _build_default_payload(raw_entries)
    sample_payload_json = json.dumps(default_payload, indent=2)

    root_path = request.scope.get("root_path", "")
    query_endpoint_path = _join_path(root_path, f"runs/{runid}/query")
    query_endpoint = _absolute_url(request, query_endpoint_path)

    template = _load_prompt_template()
    placeholders = {
        "RUN_ID": str(run_path),
        "QUERY_ENDPOINT": query_endpoint,
        "ROW_LIMIT": str(default_payload.get("limit", DEFAULT_PROMPT_ROW_LIMIT)),
        "SAMPLE_PAYLOAD": sample_payload_json,
        "USER_REQUEST": "_Describe your data question here._",
        "SCHEMA_SUMMARY": schema_summary,
    }
    rendered_markdown = _render_prompt_template(template, placeholders)

    data = {
        "type": "prompt_template",
        "attributes": {
            "markdown": rendered_markdown,
            "placeholders": placeholders,
            "default_payload": default_payload,
            "schema_summary": schema_summary,
        },
    }
    meta = _with_trace_id(
        {
            "catalog": {
                "generated_at": generated_at,
                "dataset_count": len(raw_entries),
            }
        }
    )
    return JSONResponse({"data": data, "meta": meta})


def create_mcp_app() -> Starlette:
    routes = [
        Route("/ping", ping, methods=["GET"], name="mcp_ping"),
        Route("/runs/{runid:str}", get_run, methods=["GET"], name="mcp_get_run"),
        Route("/runs/{runid:str}/catalog", get_catalog, methods=["GET"], name="mcp_get_catalog"),
        Route("/runs/{runid:str}/activate", activate_run_endpoint, methods=["POST"], name="mcp_activate_run"),
        Route("/runs/{runid:str}/presets", get_presets, methods=["GET"], name="mcp_get_presets"),
        Route("/runs/{runid:str}/prompt-template", get_prompt_template, methods=["GET"], name="mcp_get_prompt_template"),
        Route("/runs/{runid:str}/queries/validate", validate_query, methods=["POST"], name="mcp_validate_query"),
        Route("/runs/{runid:str}/queries/execute", execute_query, methods=["POST"], name="mcp_execute_query"),
    ]

    app = Starlette(debug=False, routes=routes)
    config = get_auth_config()
    app.add_middleware(MCPAuthMiddleware, config=config, path_prefix="")
    return app
