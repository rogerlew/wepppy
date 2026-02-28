"""Files JSON API helpers extracted from the browse microservice."""

from __future__ import annotations

import fnmatch
import mimetypes
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cmp_to_key
from http import HTTPStatus
from typing import Awaitable, Callable
from urllib.parse import quote

from starlette.exceptions import HTTPException
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse

from wepppy.microservices.browse.auth import (
    USER_SERVICE_TOKEN_CLASSES,
    BrowseAuthError,
    authorize_run_request,
)
from wepppy.microservices.browse.security import (
    PATH_SECURITY_FORBIDDEN_HIDDEN,
    PATH_SECURITY_FORBIDDEN_RECORDER,
    path_security_detail,
    validate_raw_subpath,
    validate_resolved_path_against_roots,
    validate_resolved_target,
    derive_allowed_symlink_roots,
)
from wepppy.runtime_paths import (
    NoDirError,
    listdir as nodir_listdir,
    parse_external_subpath,
    resolve as nodir_resolve,
    stat as nodir_stat,
)
from wepppy.runtime_paths.paths import NODIR_ROOTS, split_nodir_root

__all__ = [
    "FILES_DEFAULT_LIMIT",
    "FILES_MAX_LIMIT",
    "FilesApiDependencies",
    "accepts_json",
    "build_error_payload",
    "build_files_handlers",
]

FILES_DEFAULT_LIMIT = 1000
FILES_MAX_LIMIT = 10000
_SORT_FIELDS = {"name", "date", "size"}
_SORT_ORDERS = {"asc", "desc"}
_NODIR_SUFFIX = ".nodir"
_NODIR_ROOTS = frozenset(NODIR_ROOTS)


@dataclass(frozen=True)
class FilesApiDependencies:
    get_wd: Callable[[str], str]
    is_restricted_recorder_path: Callable[[str], bool]
    manifest_path: Callable[[str], str]
    normalize_rel_path: Callable[[str], str]
    rel_join: Callable[[str, str], str]
    rel_parent: Callable[[str], tuple[str, str]]
    prefix_path: Callable[[str], str]
    preview_available: Callable[[str], bool]
    validate_filter_pattern: Callable[[str], bool]
    get_page_entries: Callable[..., Awaitable[tuple[list[tuple], int, bool]]]
    get_total_items: Callable[..., Awaitable[int]]


def accepts_json(request: StarletteRequest) -> bool:
    accept = request.headers.get("accept", "")
    if not accept:
        return True
    for part in accept.split(","):
        part = part.strip()
        if not part:
            continue
        media, *params = [segment.strip() for segment in part.split(";")]
        q_value = 1.0
        for param in params:
            if param.lower().startswith("q="):
                try:
                    q_value = float(param.split("=", 1)[1])
                except (TypeError, ValueError):
                    q_value = 0.0
                break
        if q_value <= 0:
            continue
        media = media.lower()
        if media in ("*/*", "application/json", "application/*") or media.endswith("+json"):
            return True
    return False


def build_error_payload(
    message: str,
    code: str | None = None,
    details: str | None = None,
    errors=None,
) -> dict:
    payload = {
        "error": {
            "message": message,
            "code": code,
            "details": details or message,
        }
    }
    if errors:
        payload["errors"] = errors
    return payload


def _raise_files_error(
    status_code: int,
    message: str,
    *,
    code: str | None = None,
    details: str | None = None,
    errors=None,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=build_error_payload(message, code=code, details=details, errors=errors),
    )


def _raise_nodir_error(err: NoDirError) -> None:
    _raise_files_error(
        err.http_status,
        err.message,
        code=err.code,
        details=err.message,
    )


def _is_admin_auth_context(auth_context) -> bool:
    roles = set(getattr(auth_context, "roles", frozenset()))
    return "admin" in roles or "root" in roles


def _allowlisted_nodir_root(name: str) -> str | None:
    _ = name
    return None


def _allowlisted_raw_nodir_relpath(rel_path: str) -> str | None:
    if rel_path in (".", ""):
        return None
    if "/" in rel_path:
        return None
    return _allowlisted_nodir_root(rel_path)


def _is_mixed_nodir_root(wd: str, root: str) -> bool:
    _ = (wd, root)
    return False


def _mixed_nodir_roots(wd: str) -> set[str]:
    _ = wd
    return set()


def _format_iso_mtime_ns(mtime_ns: int | None) -> str | None:
    if mtime_ns is None:
        return None
    try:
        dt = datetime.fromtimestamp(mtime_ns / 1_000_000_000, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        dt = datetime.fromtimestamp(0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _display_rel_path(rel_path: str) -> str:
    return "" if rel_path in (".", "") else rel_path


def _normalize_files_rel_path(raw_path: str) -> str:
    if not raw_path:
        return "."
    if "\x00" in raw_path:
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            "Invalid path.",
            code="path_outside_root",
            details="Null byte in path.",
        )
    raw_path = raw_path.replace("\\", "/")
    if raw_path.startswith("/"):
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            "Invalid path.",
            code="path_outside_root",
            details="Absolute paths are not allowed.",
        )
    parts = [part for part in raw_path.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            "Invalid path.",
            code="path_outside_root",
            details="Path traversal segments are not allowed.",
        )
    rel_path = "/".join(parts) or "."
    return rel_path


def _enforce_no_symlink_traversal(
    root: str,
    rel_path: str,
    *,
    meta: bool,
    on_forbidden_target: Callable[[str], None],
) -> None:
    if rel_path in (".", ""):
        return
    parts = [part for part in rel_path.split("/") if part]
    current = os.path.abspath(root)
    allowed_roots = derive_allowed_symlink_roots(root)
    for index, part in enumerate(parts):
        current = os.path.join(current, part)
        if os.path.islink(current):
            resolved = os.path.realpath(current)
            violation = validate_resolved_path_against_roots(resolved, allowed_roots)
            if violation in (PATH_SECURITY_FORBIDDEN_RECORDER, PATH_SECURITY_FORBIDDEN_HIDDEN):
                on_forbidden_target(violation)
            if violation is None:
                continue
            if index < len(parts) - 1:
                _raise_files_error(
                    HTTPStatus.BAD_REQUEST,
                    "Invalid path.",
                    code="path_outside_root",
                    details="Symlink traversal is not allowed.",
                )
            if not meta:
                path_display = _display_rel_path(rel_path) or "."
                _raise_files_error(
                    HTTPStatus.BAD_REQUEST,
                    f"Path '{path_display}' is not a directory",
                    code="not_a_directory",
                    details="Symlink traversal is not allowed.",
                )
            _raise_files_error(
                HTTPStatus.BAD_REQUEST,
                "Invalid path.",
                code="path_outside_root",
                details="Symlink traversal is not allowed.",
            )


def _resolve_files_path(root: str, rel_path: str) -> str:
    root_abs = os.path.abspath(root)
    join_path = rel_path if rel_path != "." else ""
    abs_path = os.path.abspath(os.path.join(root_abs, join_path))
    try:
        common = os.path.commonpath([root_abs, abs_path])
    except ValueError:
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            "Invalid path.",
            code="path_outside_root",
            details="Path traversal detected.",
        )
    if common != root_abs:
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            "Invalid path.",
            code="path_outside_root",
            details="Path traversal detected.",
        )
    return abs_path


def _format_iso_mtime(stat_result) -> str | None:
    if stat_result is None:
        return None
    mtime_ns = getattr(stat_result, "st_mtime_ns", None)
    if mtime_ns is None:
        mtime_ns = int(stat_result.st_mtime * 1_000_000_000)
    try:
        dt = datetime.fromtimestamp(mtime_ns / 1_000_000_000, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        dt = datetime.fromtimestamp(0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_child_count(value: str) -> int | None:
    if not value:
        return None
    match = re.match(r"^(\d+)", value.strip())
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _safe_symlink_target(
    root: str,
    entry_path: str,
    target: str,
    normalize_rel_path: Callable[[str], str],
) -> str | None:
    if not target:
        return None
    if os.path.isabs(target):
        candidate = target
    else:
        candidate = os.path.abspath(os.path.join(os.path.dirname(entry_path), target))
    root_abs = os.path.abspath(root)
    try:
        common = os.path.commonpath([root_abs, candidate])
    except ValueError:
        return None
    if common != root_abs:
        return None
    rel_target = os.path.relpath(candidate, root_abs).replace("\\", "/")
    return _display_rel_path(normalize_rel_path(rel_target))


def _parse_files_query_params(
    request: StarletteRequest,
    *,
    validate_filter_pattern: Callable[[str], bool],
) -> tuple[int, int, str, str, str, bool]:
    params = request.query_params
    errors = []

    def _add_error(path: str, message: str) -> None:
        errors.append({"code": "invalid_value", "message": message, "path": path})

    limit_raw = params.get("limit")
    if limit_raw is None:
        limit = FILES_DEFAULT_LIMIT
    else:
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            limit = FILES_DEFAULT_LIMIT
            _add_error("limit", "limit must be an integer.")
        else:
            if limit < 1 or limit > FILES_MAX_LIMIT:
                _add_error("limit", f"limit must be between 1 and {FILES_MAX_LIMIT}.")

    offset_raw = params.get("offset")
    if offset_raw is None:
        offset = 0
    else:
        try:
            offset = int(offset_raw)
        except (TypeError, ValueError):
            offset = 0
            _add_error("offset", "offset must be an integer.")
        else:
            if offset < 0:
                _add_error("offset", "offset must be >= 0.")

    pattern = params.get("pattern") or ""
    if pattern and not validate_filter_pattern(pattern):
        _add_error("pattern", "pattern contains unsupported characters.")

    sort_by = (params.get("sort") or "name").lower()
    if sort_by not in _SORT_FIELDS:
        _add_error("sort", "sort must be one of: name, date, size.")

    sort_order = (params.get("order") or "asc").lower()
    if sort_order not in _SORT_ORDERS:
        _add_error("order", "order must be one of: asc, desc.")

    meta_raw = params.get("meta")
    if meta_raw is None:
        meta = False
    else:
        meta_value = meta_raw.strip().lower()
        if meta_value in ("1", "true", "yes", "y", "on"):
            meta = True
        elif meta_value in ("0", "false", "no", "n", "off"):
            meta = False
        else:
            meta = False
            _add_error("meta", "meta must be a boolean.")

    if errors:
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            "Validation failed",
            code="validation_error",
            details=errors[0]["message"],
            errors=errors,
        )

    return limit, offset, pattern, sort_by, sort_order, meta


def _resolve_files_root(runid: str, deps: FilesApiDependencies) -> str:
    try:
        wd = os.path.abspath(deps.get_wd(runid))
    except (TypeError, ValueError, OSError) as exc:
        _raise_files_error(
            HTTPStatus.NOT_FOUND,
            f"Run '{runid}' not found",
            code="run_not_found",
            details=str(exc) or f"No run directory for runid={runid}",
        )
    if not os.path.isdir(wd):
        _raise_files_error(
            HTTPStatus.NOT_FOUND,
            f"Run '{runid}' not found",
            code="run_not_found",
            details=f"No run directory for runid={runid}",
        )
    return wd


def _build_files_entry_payload(
    *,
    name: str,
    rel_dir: str,
    root: str,
    is_dir: bool,
    is_symlink: bool,
    symlink_is_dir: bool,
    hr_value: str,
    runid: str,
    config: str,
    include_meta: bool,
    deps: FilesApiDependencies,
) -> dict:
    rel_path = deps.rel_join(rel_dir, name)
    abs_path = os.path.abspath(os.path.join(root, rel_path))
    try:
        stat_result = os.lstat(abs_path)
    except OSError:
        stat_result = None

    payload = {
        "name": name,
        "path": _display_rel_path(rel_path),
        "type": "file",
    }

    modified_iso = _format_iso_mtime(stat_result)
    if modified_iso:
        payload["modified_iso"] = modified_iso

    if is_symlink:
        payload["type"] = "symlink"
        payload["symlink_is_dir"] = bool(symlink_is_dir)
        try:
            target = os.readlink(abs_path)
        except OSError:
            target = ""
        safe_target = _safe_symlink_target(root, abs_path, target, deps.normalize_rel_path)
        if safe_target is not None:
            payload["symlink_target"] = safe_target
        return payload

    if is_dir:
        payload["type"] = "directory"
        child_count = _parse_child_count(hr_value)
        if child_count is not None:
            payload["child_count"] = child_count
        return payload

    if stat_result is not None:
        payload["size_bytes"] = int(stat_result.st_size)

    payload["download_url"] = deps.prefix_path(
        f"/runs/{runid}/{config}/download/{quote(rel_path, safe='/')}"
    )

    if include_meta:
        content_type, _encoding = mimetypes.guess_type(name)
        payload["content_type"] = content_type or "application/octet-stream"
        payload["preview_available"] = deps.preview_available(name)

    return payload


def _build_nodir_entry_payload(
    *,
    name: str,
    rel_dir: str,
    is_dir: bool,
    size_bytes: int | None,
    mtime_ns: int | None,
    child_count: int | None,
    runid: str,
    config: str,
    include_meta: bool,
    deps: FilesApiDependencies,
) -> dict:
    rel_path = deps.rel_join(rel_dir, name)
    payload = {
        "name": name,
        "path": _display_rel_path(rel_path),
        "type": "directory" if is_dir else "file",
    }

    modified_iso = _format_iso_mtime_ns(mtime_ns)
    if modified_iso:
        payload["modified_iso"] = modified_iso

    if is_dir:
        if child_count is not None:
            payload["child_count"] = child_count
        return payload

    if size_bytes is not None:
        payload["size_bytes"] = int(size_bytes)

    payload["download_url"] = deps.prefix_path(
        f"/runs/{runid}/{config}/download/{quote(rel_path, safe='/')}"
    )

    if include_meta:
        content_type, _encoding = mimetypes.guess_type(name)
        payload["content_type"] = content_type or "application/octet-stream"
        payload["preview_available"] = deps.preview_available(name)

    return payload


def _sort_nodir_entries(entries: list[dict], *, sort_by: str, sort_order: str) -> list[dict]:
    sort_by = sort_by if sort_by in _SORT_FIELDS else "name"
    sort_order = sort_order if sort_order in _SORT_ORDERS else "asc"

    def _compare(left: dict, right: dict) -> int:
        left_rank = 0 if left["is_dir"] else 1
        right_rank = 0 if right["is_dir"] else 1
        if left_rank != right_rank:
            return -1 if left_rank < right_rank else 1

        if sort_by == "date":
            left_primary = int(left.get("mtime_ns") or 0)
            right_primary = int(right.get("mtime_ns") or 0)
        elif sort_by == "size":
            left_primary = int(left.get("size_bytes") or 0)
            right_primary = int(right.get("size_bytes") or 0)
        else:
            left_primary = left["name"].casefold()
            right_primary = right["name"].casefold()

        if left_primary != right_primary:
            if sort_order == "asc":
                return -1 if left_primary < right_primary else 1
            return -1 if left_primary > right_primary else 1

        left_name_casefold = left["name"].casefold()
        right_name_casefold = right["name"].casefold()
        if left_name_casefold != right_name_casefold:
            return -1 if left_name_casefold < right_name_casefold else 1
        if left["name"] != right["name"]:
            return -1 if left["name"] < right["name"] else 1
        return 0

    return sorted(entries, key=cmp_to_key(_compare))


def _nodir_mixed_conflict() -> None:
    _raise_files_error(
        HTTPStatus.CONFLICT,
        "NoDir root is in mixed state (dir + .nodir present).",
        code="NODIR_MIXED_STATE",
        details="NoDir root is in mixed state (dir + .nodir present).",
    )


async def _files_list_response(
    *,
    runid: str,
    config: str,
    wd: str,
    rel_path: str,
    abs_path: str,
    limit: int,
    offset: int,
    pattern: str,
    sort_by: str,
    sort_order: str,
    hide_mixed_nodir: bool,
    deps: FilesApiDependencies,
) -> JSONResponse:
    page = (offset // limit) + 1
    page_offset = offset % limit

    entries, total_items, using_manifest = await deps.get_page_entries(
        wd,
        abs_path,
        page=page,
        page_size=limit,
        filter_pattern=pattern,
        sort_by=sort_by,
        sort_order=sort_order,
        hide_mixed_nodir=hide_mixed_nodir,
    )

    if total_items == 0 or offset >= total_items:
        entries = []
    elif page_offset:
        entries = entries[page_offset:]
        if len(entries) < limit and (offset + len(entries)) < total_items:
            next_entries, _next_total, next_using_manifest = await deps.get_page_entries(
                wd,
                abs_path,
                page=page + 1,
                page_size=limit,
                filter_pattern=pattern,
                sort_by=sort_by,
                sort_order=sort_order,
                hide_mixed_nodir=hide_mixed_nodir,
            )
            using_manifest = using_manifest or next_using_manifest
            needed = limit - len(entries)
            if needed > 0:
                entries.extend(next_entries[:needed])

    hidden_mixed_roots: set[str] = set()
    if hide_mixed_nodir and rel_path in (".", ""):
        hidden_mixed_roots = _mixed_nodir_roots(wd)

    payload_entries = []
    for entry in entries:
        name, is_dir, _mtime_display, hr_value, is_symlink, _sym_target, symlink_is_dir = entry
        nodir_root = _allowlisted_nodir_root(name)
        if (
            hidden_mixed_roots
            and (
                name in hidden_mixed_roots
                or (nodir_root is not None and nodir_root in hidden_mixed_roots)
            )
        ):
            continue
        effective_is_dir = is_dir or (
            nodir_root is not None and not is_symlink and not symlink_is_dir
        )
        payload_entries.append(
            _build_files_entry_payload(
                name=name,
                rel_dir=rel_path,
                root=wd,
                is_dir=effective_is_dir,
                is_symlink=is_symlink,
                symlink_is_dir=symlink_is_dir,
                hr_value=hr_value,
                runid=runid,
                config=config,
                include_meta=False,
                deps=deps,
            )
        )

    response_payload = {
        "runid": runid,
        "config": config,
        "path": _display_rel_path(rel_path),
        "entries": payload_entries,
        "total": total_items,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(payload_entries)) < total_items,
    }
    if using_manifest:
        response_payload["cached"] = True
    return JSONResponse(response_payload)


async def _files_nodir_list_response(
    *,
    runid: str,
    config: str,
    rel_path: str,
    target,
    limit: int,
    offset: int,
    pattern: str,
    sort_by: str,
    sort_order: str,
    deps: FilesApiDependencies,
) -> JSONResponse:
    try:
        target_meta = nodir_stat(target)
    except FileNotFoundError:
        path_display = _display_rel_path(rel_path) or "."
        _raise_files_error(
            HTTPStatus.NOT_FOUND,
            f"Directory '{path_display}' does not exist",
            code="path_not_found",
            details=f"No entry at {path_display}",
        )
    if not target_meta.is_dir:
        path_display = _display_rel_path(rel_path) or "."
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            f"Path '{path_display}' is not a directory",
            code="not_a_directory",
            details="Requested path is not a directory.",
        )

    try:
        entries = nodir_listdir(target)
    except (FileNotFoundError, NotADirectoryError):
        path_display = _display_rel_path(rel_path) or "."
        _raise_files_error(
            HTTPStatus.NOT_FOUND,
            f"Directory '{path_display}' does not exist",
            code="path_not_found",
            details=f"No entry at {path_display}",
        )
    listing_rows: list[dict] = []
    for item in entries:
        if item.name.startswith("."):
            continue
        if pattern and not fnmatch.fnmatchcase(item.name, pattern):
            continue
        listing_rows.append(
            {
                "name": item.name,
                "is_dir": bool(item.is_dir),
                "size_bytes": None if item.is_dir else int(item.size_bytes or 0),
                "mtime_ns": item.mtime_ns,
            }
        )

    sorted_rows = _sort_nodir_entries(
        listing_rows,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total_items = len(sorted_rows)
    if offset >= total_items:
        paged_rows = []
    else:
        paged_rows = sorted_rows[offset : offset + limit]

    payload_entries = []
    for row in paged_rows:
        payload_entries.append(
            _build_nodir_entry_payload(
                name=row["name"],
                rel_dir=rel_path,
                is_dir=bool(row["is_dir"]),
                size_bytes=row["size_bytes"],
                mtime_ns=row["mtime_ns"],
                child_count=None,
                runid=runid,
                config=config,
                include_meta=False,
                deps=deps,
            )
        )

    return JSONResponse(
        {
            "runid": runid,
            "config": config,
            "path": _display_rel_path(rel_path),
            "entries": payload_entries,
            "total": total_items,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(payload_entries)) < total_items,
        }
    )


async def _files_nodir_meta_response(
    *,
    runid: str,
    config: str,
    rel_path: str,
    target,
    deps: FilesApiDependencies,
) -> JSONResponse:
    try:
        entry = nodir_stat(target)
    except FileNotFoundError:
        path_display = _display_rel_path(rel_path) or "."
        _raise_files_error(
            HTTPStatus.NOT_FOUND,
            f"Path '{path_display}' does not exist",
            code="path_not_found",
            details=f"No entry at {path_display}",
        )

    rel_dir = deps.rel_parent(rel_path)[0] if rel_path not in (".", "") else "."
    child_count: int | None = None
    if entry.is_dir:
        try:
            child_count = len(
                [
                    item
                    for item in nodir_listdir(target)
                    if not item.name.startswith(".")
                ]
            )
        except (FileNotFoundError, NotADirectoryError):
            path_display = _display_rel_path(rel_path) or "."
            _raise_files_error(
                HTTPStatus.NOT_FOUND,
                f"Path '{path_display}' does not exist",
                code="path_not_found",
                details=f"No entry at {path_display}",
            )

    payload = _build_nodir_entry_payload(
        name=entry.name,
        rel_dir=rel_dir,
        is_dir=bool(entry.is_dir),
        size_bytes=entry.size_bytes,
        mtime_ns=entry.mtime_ns,
        child_count=child_count,
        runid=runid,
        config=config,
        include_meta=True,
        deps=deps,
    )
    return JSONResponse({"runid": runid, "config": config, **payload})


async def _files_meta_response(
    *,
    runid: str,
    config: str,
    wd: str,
    rel_path: str,
    abs_path: str,
    using_manifest: bool,
    deps: FilesApiDependencies,
) -> JSONResponse:
    name = "" if rel_path in (".", "") else os.path.basename(abs_path.rstrip(os.sep))
    is_symlink = os.path.islink(abs_path)
    symlink_is_dir = False
    if is_symlink:
        try:
            symlink_is_dir = os.path.isdir(abs_path)
        except OSError:
            symlink_is_dir = False
    is_dir = False if is_symlink else os.path.isdir(abs_path)

    hr_value = ""
    if is_dir:
        child_count = await deps.get_total_items(abs_path)
        hr_value = f"{child_count} items"

    entry_payload = _build_files_entry_payload(
        name=name,
        rel_dir=deps.rel_parent(rel_path)[0] if rel_path not in (".", "") else ".",
        root=wd,
        is_dir=is_dir,
        is_symlink=is_symlink,
        symlink_is_dir=symlink_is_dir,
        hr_value=hr_value,
        runid=runid,
        config=config,
        include_meta=True,
        deps=deps,
    )

    response_payload = {
        "runid": runid,
        "config": config,
        **entry_payload,
    }

    return JSONResponse(response_payload)


async def _handle_files_request(
    request: StarletteRequest,
    runid: str,
    config: str,
    subpath: str,
    *,
    deps: FilesApiDependencies,
):
    if not accepts_json(request):
        _raise_files_error(
            HTTPStatus.NOT_ACCEPTABLE,
            "Only application/json is supported.",
            code="not_acceptable",
            details="Accept header must allow application/json.",
        )

    try:
        auth_context = authorize_run_request(
            request,
            runid=runid,
            config=config,
            subpath=subpath or "",
            allow_public_without_token=False,
            require_authenticated=True,
            allowed_token_classes=USER_SERVICE_TOKEN_CLASSES,
        )
    except BrowseAuthError as exc:
        if exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            _raise_files_error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Internal server error.",
                code="internal_error",
                details=exc.message,
            )
        message = "Authentication required." if exc.status_code == HTTPStatus.UNAUTHORIZED else "Access denied."
        code = "unauthorized" if exc.status_code == HTTPStatus.UNAUTHORIZED else "forbidden"
        _raise_files_error(
            exc.status_code,
            message,
            code=code,
            details=exc.message,
        )

    allow_recorder = auth_context.is_root
    is_admin = _is_admin_auth_context(auth_context)
    limit, offset, pattern, sort_by, sort_order, meta = _parse_files_query_params(
        request, validate_filter_pattern=deps.validate_filter_pattern
    )

    wd = _resolve_files_root(runid, deps)
    rel_path = _normalize_files_rel_path(subpath or "")

    def _raise_forbidden_path(violation_code: str) -> None:
        _raise_files_error(
            HTTPStatus.FORBIDDEN,
            "Access denied.",
            code="forbidden_path",
            details=path_security_detail(violation_code),
        )

    def _raise_outside_or_invalid_path() -> None:
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            "Invalid path.",
            code="path_outside_root",
            details="Symlink traversal is not allowed.",
        )

    raw_violation = validate_raw_subpath(rel_path)
    if raw_violation is not None:
        if allow_recorder and raw_violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            raw_violation = None
    if raw_violation is not None:
        _raise_forbidden_path(raw_violation)

    parse_rel_path = rel_path
    if _allowlisted_raw_nodir_relpath(rel_path) is not None:
        parse_rel_path = f"{rel_path}/"
    elif (subpath or "").endswith("/") and rel_path not in (".", ""):
        parse_rel_path = f"{rel_path}/"

    try:
        logical_rel_path, nodir_view = parse_external_subpath(
            parse_rel_path, allow_admin_alias=False
        )
    except ValueError as exc:
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            "Invalid path.",
            code="path_outside_root",
            details=str(exc),
        )

    nodir_root, _inner_path = split_nodir_root(logical_rel_path)
    if nodir_root is not None and nodir_view == "archive" and _is_mixed_nodir_root(wd, nodir_root):
        _nodir_mixed_conflict()

    nodir_target = None
    try:
        nodir_target = nodir_resolve(wd, logical_rel_path, view=nodir_view)
    except NoDirError as err:
        _raise_nodir_error(err)

    if nodir_target is not None:
        if meta:
            return await _files_nodir_meta_response(
                runid=runid,
                config=config,
                rel_path=rel_path,
                target=nodir_target,
                deps=deps,
            )
        return await _files_nodir_list_response(
            runid=runid,
            config=config,
            rel_path=rel_path,
            target=nodir_target,
            limit=limit,
            offset=offset,
            pattern=pattern,
            sort_by=sort_by,
            sort_order=sort_order,
            deps=deps,
        )

    if nodir_root is not None and nodir_view == "archive":
        path_display = _display_rel_path(rel_path) or "."
        label = "Path" if meta else "Directory"
        _raise_files_error(
            HTTPStatus.NOT_FOUND,
            f"{label} '{path_display}' does not exist",
            code="path_not_found",
            details=f"No entry at {path_display}",
        )

    abs_path = _resolve_files_path(wd, rel_path)
    _enforce_no_symlink_traversal(
        wd,
        rel_path,
        meta=meta,
        on_forbidden_target=_raise_forbidden_path,
    )

    if not os.path.lexists(abs_path):
        path_display = _display_rel_path(rel_path) or "."
        label = "Path" if meta else "Directory"
        _raise_files_error(
            HTTPStatus.NOT_FOUND,
            f"{label} '{path_display}' does not exist",
            code="path_not_found",
            details=f"No entry at {path_display}",
        )

    resolved_violation = validate_resolved_target(wd, abs_path)
    if resolved_violation in (PATH_SECURITY_FORBIDDEN_RECORDER, PATH_SECURITY_FORBIDDEN_HIDDEN):
        if allow_recorder and resolved_violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            resolved_violation = None
    if resolved_violation in (PATH_SECURITY_FORBIDDEN_RECORDER, PATH_SECURITY_FORBIDDEN_HIDDEN):
        _raise_forbidden_path(resolved_violation)
    if resolved_violation is not None:
        _raise_outside_or_invalid_path()

    using_manifest = os.path.exists(deps.manifest_path(wd))

    if meta:
        return await _files_meta_response(
            runid=runid,
            config=config,
            wd=wd,
            rel_path=rel_path,
            abs_path=abs_path,
            using_manifest=using_manifest,
            deps=deps,
        )

    if not os.path.isdir(abs_path):
        path_display = _display_rel_path(rel_path) or "."
        _raise_files_error(
            HTTPStatus.BAD_REQUEST,
            f"Path '{path_display}' is not a directory",
            code="not_a_directory",
            details="Requested path is not a directory.",
        )

    return await _files_list_response(
        runid=runid,
        config=config,
        wd=wd,
        rel_path=rel_path,
        abs_path=abs_path,
        limit=limit,
        offset=offset,
        pattern=pattern,
        sort_by=sort_by,
        sort_order=sort_order,
        hide_mixed_nodir=not is_admin,
        deps=deps,
    )


def build_files_handlers(deps: FilesApiDependencies):
    async def files_root(request: StarletteRequest):
        runid = request.path_params["runid"]
        config = request.path_params["config"]
        return await _handle_files_request(request, runid, config, "", deps=deps)

    async def files_subpath(request: StarletteRequest):
        runid = request.path_params["runid"]
        config = request.path_params["config"]
        subpath = request.path_params.get("subpath", "")
        return await _handle_files_request(request, runid, config, subpath, deps=deps)

    return files_root, files_subpath
