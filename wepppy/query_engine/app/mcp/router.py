"""Starlette router for the query-engine MCP API."""

from __future__ import annotations

import json
import logging
import os
import time
from collections import OrderedDict
from pathlib import Path
from collections.abc import Iterable, Mapping, Sequence
from typing import Any
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
    """Raised when a query payload fails validation before execution."""

    def __init__(self, status_code: int, code: str, detail: str, meta: Mapping[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.meta = dict(meta or {})


def _with_trace_id(meta: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Attach a random trace identifier to metadata payloads.

    Args:
        meta: Optional metadata dictionary.

    Returns:
        Dictionary containing the original metadata plus a `trace_id`.
    """
    payload = dict(meta or {})
    payload.setdefault("trace_id", uuid4().hex)
    return payload


def _error_response(status_code: int, code: str, detail: str, error_meta: Mapping[str, Any] | None = None) -> JSONResponse:
    """Return a JSON API error response with a standard envelope.

    Args:
        status_code: HTTP status code to emit.
        code: Short machine-readable error code.
        detail: Human readable error detail.
        error_meta: Optional metadata payload for context.

    Returns:
        JSONResponse following the JSON:API error shape.
    """
    error_entry = {"code": code, "detail": detail}
    if error_meta:
        error_entry["meta"] = dict(error_meta)
    return JSONResponse({"errors": [error_entry], "meta": _with_trace_id({})}, status_code=status_code)


def _normalise_leading_slash(path: str) -> str:
    """Ensure paths include a leading slash.

    Args:
        path: Raw path fragment.

    Returns:
        Path guaranteed to start with `/`.
    """
    if not path.startswith("/"):
        return "/" + path
    return path


def _join_path(root_path: str, suffix: str) -> str:
    """Join a root_path with a suffix while normalising slashes.

    Args:
        root_path: Base prefix (e.g., proxy root path).
        suffix: Path fragment to append.

    Returns:
        Normalised combined path.
    """
    if not root_path:
        return _normalise_leading_slash(suffix)
    base = root_path.rstrip("/")
    return _normalise_leading_slash(f"{base}/{suffix.lstrip('/')}")


def _absolute_url(request: Request, path: str) -> str:
    """Build an absolute URL for the current request host.

    Args:
        request: Current Starlette request.
        path: URL path to append.

    Returns:
        Fully-qualified URL string.
    """
    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}{path}"


def _load_catalog_data(run_path: os.PathLike[str]) -> tuple[list[dict[str, Any]], str | None]:
    """Load catalog JSON for a run path and return entries plus timestamp.

    Args:
        run_path: Filesystem path to the run directory.

    Returns:
        Tuple containing the list of catalog entries and the generated_at timestamp.

    Raises:
        FileNotFoundError: If the catalog file is missing.
    """
    catalog_path = resolve_catalog_path(run_path)
    if not catalog_path.exists():
        raise FileNotFoundError(catalog_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    files = data.get("files")
    entries = files if isinstance(files, list) else []
    generated_at = data.get("generated_at") or data.get("generatedAt")
    return entries, generated_at


def _load_catalog_metadata(run_path: os.PathLike[str]) -> tuple[bool, str | None, int]:
    """Return activation metadata for a run without loading the full catalog.

    Args:
        run_path: Filesystem path to the run directory.

    Returns:
        Tuple of (activated flag, generated_at timestamp, dataset count).
    """
    try:
        entries, generated_at = _load_catalog_data(run_path)
    except FileNotFoundError:
        return False, None, 0
    except Exception:  # pragma: no cover - malformed catalog files
        LOGGER.warning("Failed to parse catalog for %s", run_path, exc_info=True)
        return True, None, 0
    dataset_count = len(entries)
    return True, generated_at, dataset_count


def _load_prompt_template() -> str:
    """Read the LLM prompt template from disk, falling back to a built-in default.

    Returns:
        Template text with placeholder tokens.
    """
    try:
        return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            "Run {{RUN_ID}}\n"
            "Endpoint {{QUERY_ENDPOINT}}\n"
            "Limit {{ROW_LIMIT}}\n"
            "{{SCHEMA_SUMMARY}}\n"
            "{{SAMPLE_PAYLOAD}}\n"
        )


def _build_schema_summary(raw_entries: Iterable[Mapping[str, Any]]) -> str:
    """Build a concise bullet list summarising catalog schema coverage.

    Args:
        raw_entries: Catalog entries loaded from disk.

    Returns:
        Markdown-style bullet list describing available schemas.
    """
    lines: list[str] = []
    for entry in raw_entries:
        path = entry.get("path") if isinstance(entry, Mapping) else None
        if not isinstance(path, str):
            continue
        schema = entry.get("schema") if isinstance(entry, Mapping) else None
        fields = schema.get("fields") if isinstance(schema, Mapping) else None
        if isinstance(fields, Sequence):
            names = [field.get("name") for field in fields if isinstance(field, Mapping) and field.get("name")]
            if names:
                lines.append(f"* {path}: {', '.join(names)}")
                continue
        lines.append(f"* {path}")
    if not lines:
        return "_No catalog schema available._"
    return "\n".join(lines)


def _build_default_payload(raw_entries: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Construct a starter query payload using the first catalog entry.

    Args:
        raw_entries: Catalog entries loaded from disk.

    Returns:
        Mapping representing a query payload example.
    """
    datasets: list[dict[str, Any]] = []
    if raw_entries:
        first = raw_entries[0]
        path = first.get("path") if isinstance(first, Mapping) else None
        if isinstance(path, str):
            dataset_entry: dict[str, Any] = {"path": path}
            schema = first.get("schema") if isinstance(first, Mapping) else None
            fields = schema.get("fields") if isinstance(schema, Mapping) else None
            if isinstance(fields, Sequence):
                names = [field.get("name") for field in fields if isinstance(field, Mapping) and field.get("name")]
                if names:
                    dataset_entry["columns"] = names[: min(len(names), 3)]
            datasets.append(dataset_entry)
    payload = {
        "datasets": datasets or [],
        "limit": DEFAULT_PROMPT_ROW_LIMIT,
        "include_schema": True,
    }
    return payload


def _render_prompt_template(template: str, placeholders: Mapping[str, Any]) -> str:
    """Replace template placeholders with contextual values.

    Args:
        template: Template string containing `{{KEY}}` placeholders.
        placeholders: Mapping of placeholder keys to replacement values.

    Returns:
        Rendered template string.
    """
    rendered = template
    for key, value in placeholders.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def _prepare_query_request(
    payload: Mapping[str, Any],
    *,
    runid: str,
    run_path: os.PathLike[str],
) -> tuple[QueryRequest, Mapping[str, Any], list[dict[str, Any]], str | None]:
    """Validate the inbound payload and build a QueryRequest instance.

    Args:
        payload: Raw JSON payload from the HTTP request.
        runid: Run identifier string.
        run_path: Filesystem path to the run directory.

    Returns:
        Tuple of (QueryRequest, normalized payload, raw catalog entries, generated_at).

    Raises:
        QueryValidationException: If the payload references missing datasets or is malformed.
    """
    try:
        raw_entries, generated_at = _load_catalog_data(run_path)
    except FileNotFoundError as exc:
        raise QueryValidationException(404, "catalog_missing", f"Catalog for run '{runid}' not found") from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning("Failed to parse catalog for %s", runid, exc_info=True)
        raise QueryValidationException(500, "catalog_invalid", f"Catalog for run '{runid}' is invalid") from exc

    catalog_index = OrderedDict()
    for entry in raw_entries:
        if isinstance(entry, Mapping):
            path = entry.get("path")
            if isinstance(path, str):
                catalog_index[path] = entry

    datasets_value = payload.get("datasets")
    if not isinstance(datasets_value, Sequence) or isinstance(datasets_value, (str, bytes)):
        raise QueryValidationException(400, "invalid_request", "'datasets' must be a list")

    sanitized_datasets: list[Any] = []
    missing: list[str] = []

    for index, dataset in enumerate(datasets_value):
        if isinstance(dataset, str):
            path = dataset
            sanitized = {"path": path}
        elif isinstance(dataset, Mapping):
            path = dataset.get("path") or dataset.get("dataset")
            if not path:
                raise QueryValidationException(400, "invalid_request", "Dataset object must define 'path'")
            sanitized = dict(dataset)
            sanitized["path"] = str(path)
        else:
            raise QueryValidationException(400, "invalid_request", "Dataset entries must be strings or objects")

        path_str = str(path)
        if path_str not in catalog_index:
            missing.append(path_str)

        sanitized_datasets.append(sanitized)

    if missing:
        raise QueryValidationException(
            422,
            "dataset_missing",
            "One or more datasets were not found in the catalog",
            {"missing": missing},
        )

    request_kwargs = dict(payload)
    request_kwargs["datasets"] = sanitized_datasets

    try:
        query_request = QueryRequest(**request_kwargs)
    except (TypeError, ValueError) as exc:
        raise QueryValidationException(422, "invalid_payload", str(exc)) from exc

    normalized_datasets: list[dict[str, Any]] = []
    for spec in query_request._dataset_specs:
        dataset_entry = OrderedDict()
        dataset_entry["path"] = spec.path
        dataset_entry["alias"] = spec.alias
        if spec.columns:
            dataset_entry["columns"] = list(spec.columns)
        normalized_datasets.append(dataset_entry)

    normalized_payload: OrderedDict[str, Any] = OrderedDict()
    normalized_payload["datasets"] = normalized_datasets

    if query_request.columns is not None:
        normalized_payload["columns"] = list(query_request.columns)
    if query_request.limit is not None:
        normalized_payload["limit"] = int(query_request.limit)
    normalized_payload["include_schema"] = bool(query_request.include_schema)
    normalized_payload["include_sql"] = bool(query_request.include_sql)
    if query_request.joins:
        normalized_payload["joins"] = query_request.joins
    if query_request.group_by:
        normalized_payload["group_by"] = list(query_request.group_by)
    if query_request.aggregations:
        normalized_payload["aggregations"] = query_request.aggregations
    if query_request.order_by:
        normalized_payload["order_by"] = list(query_request.order_by)
    if query_request.filters:
        normalized_payload["filters"] = query_request.filters
    if query_request.computed_columns:
        normalized_payload["computed_columns"] = query_request.computed_columns
    if query_request.reshape:
        normalized_payload["reshape"] = query_request.reshape

    return query_request, normalized_payload, raw_entries, generated_at


def resolve_catalog_path(run_path: os.PathLike[str]) -> Path:
    """Return the expected catalog.json path beneath a run directory.

    Args:
        run_path: Base run directory path.

    Returns:
        Path object pointing at `_query_engine/catalog.json`.
    """
    return Path(run_path) / "_query_engine" / "catalog.json"


async def ping(request: Request) -> JSONResponse:
    """Return a lightweight MCP service health payload.

    Args:
        request: Current Starlette request.

    Returns:
        JSONResponse with principal and service metadata.
    """
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
    """Parse a positive integer query parameter.

    Args:
        value: Raw string value from query params.
        field: Field name used in error messages.
        default: Default value when `value` is None.
        minimum: Minimum allowed integer (inclusive).
        maximum: Maximum allowed integer (inclusive).

    Returns:
        Parsed integer value.

    Raises:
        ValueError: If the value cannot be parsed or is out of bounds.
    """
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
    """Parse an optional positive integer, returning None when absent.

    Args:
        value: Raw string value.
        field: Field name for error reporting.
        minimum: Minimum allowed value.
        maximum: Maximum allowed value.

    Returns:
        Parsed integer or None.

    Raises:
        ValueError: If the provided value is invalid.
    """
    if value is None:
        return None
    parsed = _parse_positive_int(value, field=field, default=minimum, minimum=minimum, maximum=maximum)
    return parsed


def _get_query_param(params: Mapping[str, Any], *names: str) -> str | None:
    """Return the first present query parameter from the provided list of names.

    Args:
        params: Query parameter mapping.
        *names: Candidate parameter names to inspect.

    Returns:
        The first matching value or None when absent.
    """
    for name in names:
        value = params.get(name)
        if value is not None:
            return value
    return None


def _parse_bool(value: str | None, *, field: str, default: bool) -> bool:
    """Parse a truthy/falsy string into a boolean.

    Args:
        value: Optional query parameter string.
        field: Field name for error reporting.
        default: Boolean default when value is None.

    Returns:
        Parsed boolean value.

    Raises:
        ValueError: If the value cannot be interpreted as boolean.
    """
    if value is None:
        return default
    value_lower = value.strip().lower()
    if value_lower in {"1", "true", "yes", "on"}:
        return True
    if value_lower in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{field} must be a boolean")


def _resolve_run_entry(request: Request, runid: str) -> tuple[Path, dict[str, Any]]:
    """Resolve run metadata and construct the JSON API envelope.

    Args:
        request: Starlette request providing URL context.
        runid: Run identifier string.

    Returns:
        Tuple containing the run Path and the JSON:API resource object.

    Raises:
        FileNotFoundError: If the run cannot be resolved.
    """
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
    """Return True if the authenticated token grants access to the run.

    Args:
        principal: Authenticated MCP principal.
        runid: Run identifier being accessed.

    Returns:
        True when the runid is whitelisted in the token.
    """
    if principal.run_ids is None:
        return False
    return runid in principal.run_ids


def _is_excluded_dataset(path: str) -> bool:
    """Return True when a dataset path should be hidden from clients.

    Args:
        path: Dataset path relative to the catalog root.

    Returns:
        True if the dataset should be filtered from responses.
    """
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
    """Filter catalog entries to remove hidden or excluded datasets.

    Args:
        entries: Iterable of catalog entry dictionaries.

    Returns:
        Filtered list of entry dictionaries.
    """
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
    """Return a filtered copy of a catalog entry, optionally trimming schema fields.

    Args:
        entry: Catalog entry dictionary.
        include_fields: Whether schema field metadata should be included.
        field_limit: Optional limit on the number of schema fields.

    Returns:
        Shallow copy of the entry with schema adjusted as requested.
    """
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
    """Return catalog entries for a run, enforcing scope and filters.

    Args:
        request: Starlette request containing runid path param.

    Returns:
        JSONResponse describing filtered catalog entries.
    """
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
    """Return run metadata including activation status and catalog stats.

    Args:
        request: Starlette request containing the runid path parameter.

    Returns:
        JSONResponse with run status and catalog metadata.
    """
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
    """Validate a query payload without executing it.

    Args:
        request: Starlette request holding the runid and payload.

    Returns:
        JSONResponse summarising the normalized payload and catalog metadata.
    """
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
    """Execute a query payload after validating scope and catalog access.

    Args:
        request: Starlette request with the runid, payload, and query params.

    Returns:
        JSONResponse containing execution metadata and results.
    """
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
        context = resolve_run_context(str(run_path), auto_activate=True, run_interchange=False)
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
    """Trigger catalog activation for a run via the MCP API.

    Args:
        request: Starlette request with the runid path parameter.

    Returns:
        JSONResponse describing activation status.
    """
    runid = request.path_params.get("runid") or ""
    principal = require_scope(request, "runs:activate")

    if not _principal_has_run(principal, runid):
        return _error_response(404, "not_found", f"Run '{runid}' is not accessible")

    try:
        run_path = resolve_run_path(runid)
    except FileNotFoundError:
        return _error_response(404, "not_found", f"Run '{runid}' not found")

    try:
        catalog = activate_query_engine(run_path, force_refresh=True)
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
    """Return the static query preset catalog.

    Args:
        request: Starlette request with runid parameter (used for scope).

    Returns:
        JSONResponse containing preset categories.
    """
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
    """Render the LLM prompt template with run-aware placeholders.

    Args:
        request: Starlette request referencing the runid.

    Returns:
        JSONResponse containing markdown template data.
    """
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
    """Instantiate the Starlette app that powers the MCP API surface.

    Returns:
        Configured Starlette application with MCP routes and middleware.
    """
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
