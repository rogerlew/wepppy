from __future__ import annotations

import json
import logging
import math
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlencode
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
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
CATALOG_PAGE_SIZE = 50
CATALOG_MAX_PAGE_SIZE = 200
IGNORED_CATALOG_PREFIXES = (".mypy_cache/", ".mypy_cache", "_query_engine/", "_query_engine")
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


def _parse_non_negative_int(value: str | None, *, field: str, default: int = 0) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an integer")
    if parsed < 0:
        raise ValueError(f"{field} must be >= 0")
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


def _parse_pagination_params(params, *, default_size: int, max_size: int) -> tuple[int, int, int, bool]:
    size_raw = _get_query_param(params, "page[size]", "page_size")
    size_field = "page[size]" if "page[size]" in params else ("page_size" if "page_size" in params else "page[size]")
    size = _parse_positive_int(size_raw, field=size_field, default=default_size, minimum=1, maximum=max_size)

    offset_param = _get_query_param(params, "page[offset]", "page_offset")
    if offset_param is not None:
        offset_field = "page[offset]" if "page[offset]" in params else ("page_offset" if "page_offset" in params else "page[offset]")
        offset = _parse_non_negative_int(offset_param, field=offset_field, default=0)
        number = (offset // size) + 1
        use_offset = True
    else:
        number_raw = _get_query_param(params, "page[number]", "page_number")
        number_field = "page[number]" if "page[number]" in params else ("page_number" if "page_number" in params else "page[number]")
        number = _parse_positive_int(number_raw, field=number_field, default=1, minimum=1)
        offset = (number - 1) * size
        use_offset = False
    return size, number, offset, use_offset


def _resolve_run_entry(request: Request, run_id: str) -> tuple[Path, dict[str, Any]]:
    try:
        run_path = resolve_run_path(run_id)
    except FileNotFoundError:
        raise

    activated, generated_at, dataset_count = _load_catalog_metadata(run_path)
    root_path = request.scope.get("root_path", "")
    self_path = _join_path(root_path, f"runs/{run_id}")
    catalog_path = _join_path(root_path, f"runs/{run_id}/catalog")
    query_execute_path = _join_path(root_path, f"runs/{run_id}/queries/execute")
    query_validate_path = _join_path(root_path, f"runs/{run_id}/queries/validate")
    activate_path = _join_path(root_path, f"runs/{run_id}/activate")

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
        "id": run_id,
        "type": "run",
        "attributes": attributes,
        "links": links,
    }
    return run_path, entry


def _serialise_run(request: Request, run_id: str) -> dict[str, Any] | None:
    try:
        _, entry = _resolve_run_entry(request, run_id)
        return entry
    except FileNotFoundError:
        LOGGER.warning("Run '%s' referenced in token but not found on disk", run_id)
        return None


def _principal_has_run(principal: MCPPrincipal, run_id: str) -> bool:
    if principal.run_ids is None:
        return False
    return run_id in principal.run_ids


def _filter_catalog_entries(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "")
        normalized = path.replace("\\", "/")
        if any(normalized.startswith(prefix) or f"/{prefix}" in normalized for prefix in IGNORED_CATALOG_PREFIXES):
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
                processed_fields.append(field if not isinstance(field, dict) else dict(field))
                if field_limit is not None and len(processed_fields) >= field_limit:
                    break
            schema_clone["fields"] = processed_fields
        clone["schema"] = schema_clone
    elif schema is not None:
        clone["schema"] = schema
    return clone


def _prepare_query_request(payload: Mapping[str, Any], *, run_id: str, run_path: Path) -> tuple[QueryRequest, dict[str, Any], list[dict[str, Any]], str | None]:
    try:
        query_request = QueryRequest(**payload)
    except Exception as exc:  # pragma: no cover - validation error formatting
        raise QueryValidationException(422, "invalid_payload", f"Invalid query payload: {exc}") from exc

    try:
        raw_entries, generated_at = _load_catalog_data(run_path)
    except FileNotFoundError as exc:
        raise QueryValidationException(404, "catalog_missing", f"Catalog for run '{run_id}' not found") from exc
    except Exception as exc:  # pragma: no cover - malformed catalog files
        LOGGER.warning("Failed to parse catalog for %s", run_id, exc_info=True)
        raise QueryValidationException(500, "catalog_invalid", f"Catalog for run '{run_id}' is invalid") from exc

    available_paths = {str(entry.get("path")) for entry in raw_entries if entry.get("path")}
    missing = [spec.path for spec in query_request.dataset_specs if spec.path not in available_paths]
    if missing:
        detail = f"Dataset(s) not found: {', '.join(missing)}"
        raise QueryValidationException(422, "dataset_missing", detail, {"missing_datasets": missing})

    normalized_payload = _normalise_query_payload(query_request)
    return query_request, normalized_payload, raw_entries, generated_at


def _load_prompt_template() -> str:
    try:
        return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "# Prompt template not found\n\nGenerate a prompt manually with the supplied catalog information."


def _build_schema_summary(entries: Iterable[Mapping[str, Any]], *, max_datasets: int = 8, max_fields: int = 6) -> str:
    lines: list[str] = []
    entries_list = list(entries)
    for entry in entries_list[:max_datasets]:
        path = str(entry.get("path") or "(unknown dataset)")
        lines.append(f"- {path}")
        schema = entry.get("schema")
        if isinstance(schema, Mapping):
            fields = schema.get("fields")
            if isinstance(fields, list) and fields:
                visible = fields[:max_fields]
                for field in visible:
                    if isinstance(field, Mapping):
                        name = field.get("name", "(field)")
                        field_type = field.get("type", "")
                        lines.append(f"  - {name} ({field_type})")
                if len(fields) > max_fields:
                    lines.append(f"  - … {len(fields) - max_fields} more fields")
    if len(entries_list) > max_datasets:
        lines.append(f"- … {len(entries_list) - max_datasets} more datasets")
    if not lines:
        lines.append("- No catalog metadata available.")
    return "\n".join(lines)


def _build_default_payload(entries: Iterable[Mapping[str, Any]], *, row_limit: int = DEFAULT_PROMPT_ROW_LIMIT) -> OrderedDict[str, Any]:
    entries_list = list(entries)
    sample_dataset = entries_list[0].get("path") if entries_list and entries_list[0].get("path") else None
    dataset_value = [sample_dataset] if sample_dataset else []
    payload = OrderedDict([
        ("datasets", dataset_value),
        ("limit", row_limit),
        ("include_schema", True),
    ])
    return payload


def _render_prompt_template(template: str, placeholders: Mapping[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _normalise_query_payload(query: QueryRequest) -> dict[str, Any]:
    datasets = []
    for spec in query.dataset_specs:
        entry = {"path": spec.path, "alias": spec.alias}
        if spec.columns:
            entry["columns"] = spec.columns
        datasets.append(entry)

    normalized: dict[str, Any] = {
        "datasets": datasets,
        "limit": query.limit,
        "include_schema": query.include_schema,
        "include_sql": query.include_sql,
    }
    if query.columns is not None:
        normalized["columns"] = query.columns
    if query.group_by:
        normalized["group_by"] = query.group_by
    if query.order_by:
        normalized["order_by"] = query.order_by
    if query.filters:
        normalized["filters"] = query.filters
    if query.joins:
        normalized["joins"] = query.joins
    if query.aggregations:
        normalized["aggregations"] = query.aggregations
    if query.computed_columns:
        normalized["computed_columns"] = query.computed_columns
    if query.reshape is not None:
        normalized["reshape"] = query.reshape

    return normalized


def _build_pagination_links(request: Request, page_number: int, total_pages: int, *, page_size: int, use_offset: bool) -> dict[str, str]:
    links: dict[str, str] = {}
    base_url = str(request.base_url).rstrip("/")
    path = request.url.path
    query_items = list(request.query_params.multi_items())
    removal_keys = {"page[number]", "page[offset]", "page_number", "page_offset"}
    number_key = "page[number]" if "page[number]" in request.query_params else (
        "page_number" if "page_number" in request.query_params else "page[number]"
    )
    offset_key = "page[offset]" if "page[offset]" in request.query_params else (
        "page_offset" if "page_offset" in request.query_params else "page[offset]"
    )

    def build_url(target_page: int) -> str:
        items = [(k, v) for k, v in query_items if k not in removal_keys]
        if use_offset:
            items.append((offset_key, str((target_page - 1) * page_size)))
        else:
            items.append((number_key, str(target_page)))
        query = urlencode(items, doseq=True)
        return f"{base_url}{path}?{query}" if query else f"{base_url}{path}"

    links["self"] = build_url(page_number)
    if total_pages:
        if page_number > 1:
            links["prev"] = build_url(page_number - 1)
        if page_number < total_pages:
            links["next"] = build_url(page_number + 1)
    return links


async def list_runs(request: Request) -> JSONResponse:
    principal = require_scope(request, "runs:read")
    run_ids: Iterable[str] | None = principal.run_ids

    if run_ids is None:
        return _error_response(403, "forbidden", "Token is not scoped to any runs")

    try:
        page_size, page_number, offset, use_offset = _parse_pagination_params(
            request.query_params,
            default_size=DEFAULT_PAGE_SIZE,
            max_size=MAX_PAGE_SIZE,
        )
    except ValueError as exc:
        return _error_response(400, "invalid_request", str(exc))

    sorted_runs = sorted(run_ids)
    total_items = len(sorted_runs)
    total_pages = math.ceil(total_items / page_size) if total_items else 0

    start_index = offset
    end_index = offset + page_size
    page_slice = sorted_runs[start_index:end_index]

    data: list[dict[str, Any]] = []
    for run_id in page_slice:
        entry = _serialise_run(request, run_id)
        if entry:
            data.append(entry)

    meta = {
        "total_items": total_items,
        "page": {
            "size": page_size,
            "number": page_number,
            "offset": offset,
            "total_pages": total_pages,
        },
    }
    meta = _with_trace_id(meta)
    links = _build_pagination_links(request, page_number, total_pages, page_size=page_size, use_offset=use_offset)

    return JSONResponse({"data": data, "meta": meta, "links": links})


async def get_run(request: Request) -> JSONResponse:
    run_id = request.path_params.get("run_id") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, run_id):
        return _error_response(404, "not_found", f"Run '{run_id}' is not accessible")

    try:
        run_path, entry = _resolve_run_entry(request, run_id)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{run_id}' not found")

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


def _filter_catalog_entries(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "")
        normalized = path.replace("\\", "/")
        if any(normalized.startswith(prefix) or f"/{prefix}" in normalized for prefix in IGNORED_CATALOG_PREFIXES):
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
    run_id = request.path_params.get("run_id") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, run_id):
        return _error_response(404, "not_found", f"Run '{run_id}' is not accessible")

    try:
        run_path = resolve_run_path(run_id)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{run_id}' not found")

    try:
        raw_entries, generated_at = _load_catalog_data(run_path)
    except FileNotFoundError:
        return _error_response(404, "catalog_missing", f"Catalog for run '{run_id}' not found")
    except Exception as exc:  # pragma: no cover - malformed catalog files
        LOGGER.warning("Failed to parse catalog for %s", run_id, exc_info=True)
        return _error_response(500, "catalog_invalid", f"Catalog for run '{run_id}' is invalid")

    try:
        include_fields = _parse_bool(
            _get_query_param(request.query_params, "include_fields", "include-fields"),
            field="include_fields",
            default=True,
        )
        datasets_limit = _parse_optional_positive_int(
            _get_query_param(request.query_params, "limit[datasets]", "limit_datasets"),
            field="limit[datasets]",
            minimum=1,
            maximum=CATALOG_MAX_PAGE_SIZE,
        )
        fields_limit = _parse_optional_positive_int(
            _get_query_param(request.query_params, "limit[fields]", "limit_fields"),
            field="limit[fields]",
            minimum=1,
            maximum=1000,
        )
        page_size, page_number, offset, use_offset = _parse_pagination_params(
            request.query_params,
            default_size=CATALOG_PAGE_SIZE,
            max_size=CATALOG_MAX_PAGE_SIZE,
        )
    except ValueError as exc:
        return _error_response(400, "invalid_request", str(exc))

    filtered_entries = _filter_catalog_entries(raw_entries)
    filtered_total = len(filtered_entries)

    if datasets_limit is not None:
        filtered_entries = filtered_entries[:datasets_limit]

    total_items = len(filtered_entries)
    total_pages = math.ceil(total_items / page_size) if total_items else 0
    start_index = offset
    end_index = offset + page_size
    if start_index >= total_items:
        page_slice: list[dict[str, Any]] = []
    else:
        page_slice = filtered_entries[start_index:end_index]

    data = [
        _clone_entry(entry, include_fields=include_fields, field_limit=fields_limit if include_fields else None)
        for entry in page_slice
    ]

    meta = {
        "catalog": {
            "generated_at": generated_at,
            "total": len(raw_entries),
            "filtered": filtered_total,
            "returned": len(data),
        },
        "limits": {
            "datasets": datasets_limit,
            "fields": fields_limit,
            "include_fields": include_fields,
        },
        "page": {
            "size": page_size,
            "number": page_number,
            "offset": offset,
            "total_pages": total_pages,
            "total_items": total_items,
        },
    }
    meta = _with_trace_id(meta)
    links = _build_pagination_links(
        request,
        page_number,
        total_pages,
        page_size=page_size,
        use_offset=use_offset,
    )
    return JSONResponse({"data": data, "meta": meta, "links": links})


async def validate_query(request: Request) -> JSONResponse:
    run_id = request.path_params.get("run_id") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, run_id):
        return _error_response(404, "not_found", f"Run '{run_id}' is not accessible")

    if not (principal.has_scope("queries:validate") or principal.has_scope("queries:execute")):
        return _error_response(403, "forbidden", "Token lacks query validation scope")

    try:
        run_path = resolve_run_path(run_id)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{run_id}' not found")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return _error_response(400, "invalid_request", "Request body must be valid JSON")

    if not isinstance(payload, Mapping):
        return _error_response(400, "invalid_request", "Request body must be a JSON object")

    try:
        query_request, normalized_payload, raw_entries, generated_at = _prepare_query_request(
            payload,
            run_id=run_id,
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
    run_id = request.path_params.get("run_id") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, run_id):
        return _error_response(404, "not_found", f"Run '{run_id}' is not accessible")

    if not principal.has_scope("queries:execute"):
        return _error_response(403, "forbidden", "Token lacks query execution scope")

    try:
        dry_run = _parse_bool(request.query_params.get("dry_run"), field="dry_run", default=False)
    except ValueError as exc:
        return _error_response(400, "invalid_request", str(exc))

    try:
        run_path = resolve_run_path(run_id)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{run_id}' not found")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return _error_response(400, "invalid_request", "Request body must be valid JSON")

    if not isinstance(payload, Mapping):
        return _error_response(400, "invalid_request", "Request body must be a JSON object")

    try:
        query_request, normalized_payload, raw_entries, generated_at = _prepare_query_request(
            payload,
            run_id=run_id,
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
        return _error_response(404, "not_found", f"Run '{run_id}' not found")
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning("Failed to resolve run context for %s", run_id, exc_info=True)
        return _error_response(500, "context_unavailable", f"Unable to resolve run context: {exc}")

    started = time.perf_counter()

    try:
        result = run_query(context, query_request)
    except FileNotFoundError as exc:
        return _error_response(404, "dataset_missing", str(exc))
    except ValueError as exc:
        return _error_response(422, "invalid_payload", str(exc))
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.exception("Query execution failed for %s", run_id)
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
    run_id = request.path_params.get("run_id") or ""
    principal = require_scope(request, "runs:activate")

    if not _principal_has_run(principal, run_id):
        return _error_response(404, "not_found", f"Run '{run_id}' is not accessible")

    try:
        run_path = resolve_run_path(run_id)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{run_id}' not found")

    try:
        catalog = activate_query_engine(run_path)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{run_id}' not found")
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.exception("Activation failed for %s", run_id)
        return _error_response(500, "activation_failed", f"Activation failed: {exc}")

    generated_at = catalog.get("generated_at") if isinstance(catalog, Mapping) else None
    dataset_count = len(catalog.get("files", [])) if isinstance(catalog, Mapping) else 0

    data = {
        "type": "activation_job",
        "attributes": {
            "run_id": run_id,
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
    run_id = request.path_params.get("run_id") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, run_id):
        return _error_response(404, "not_found", f"Run '{run_id}' is not accessible")

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
    run_id = request.path_params.get("run_id") or ""
    principal = require_scope(request, "runs:read")

    if not _principal_has_run(principal, run_id):
        return _error_response(404, "not_found", f"Run '{run_id}' is not accessible")

    try:
        run_path = resolve_run_path(run_id)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{run_id}' not found")

    try:
        raw_entries, generated_at = _load_catalog_data(run_path)
    except FileNotFoundError:
        raw_entries, generated_at = [], None
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning("Failed to parse catalog for %s", run_id, exc_info=True)
        raw_entries, generated_at = [], None

    schema_summary = _build_schema_summary(raw_entries)
    default_payload = _build_default_payload(raw_entries)
    sample_payload_json = json.dumps(default_payload, indent=2)

    root_path = request.scope.get("root_path", "")
    query_endpoint_path = _join_path(root_path, f"runs/{run_id}/query")
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
        Route("/runs", list_runs, methods=["GET"], name="mcp_list_runs"),
        Route("/runs/{run_id:str}", get_run, methods=["GET"], name="mcp_get_run"),
        Route("/runs/{run_id:str}/catalog", get_catalog, methods=["GET"], name="mcp_get_catalog"),
        Route("/runs/{run_id:str}/activate", activate_run_endpoint, methods=["POST"], name="mcp_activate_run"),
        Route("/runs/{run_id:str}/presets", get_presets, methods=["GET"], name="mcp_get_presets"),
        Route("/runs/{run_id:str}/prompt-template", get_prompt_template, methods=["GET"], name="mcp_get_prompt_template"),
        Route("/runs/{run_id:str}/queries/validate", validate_query, methods=["POST"], name="mcp_validate_query"),
        Route("/runs/{run_id:str}/queries/execute", execute_query, methods=["POST"], name="mcp_execute_query"),
    ]

    app = Starlette(debug=False, routes=routes)
    config = get_auth_config()
    app.add_middleware(MCPAuthMiddleware, config=config, path_prefix="")
    return app
