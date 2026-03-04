"""Directory listing and manifest helpers for the browse microservice."""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import math
import os
import sqlite3
from datetime import datetime
from functools import cmp_to_key
from urllib.parse import urlencode

from os.path import exists as _exists
from os.path import join as _join
from wepppy.runtime_paths.paths import NODIR_ROOTS

__all__ = [
    "MANIFEST_FILENAME",
    "MAX_FILE_LIMIT",
    "create_manifest",
    "remove_manifest",
    "_manifest_path",
    "_normalize_rel_path",
    "_rel_join",
    "_rel_parent",
    "_format_mtime_ns",
    "_format_human_size",
    "get_entries",
    "get_total_items",
    "get_page_entries",
    "html_dir_list",
]

MANIFEST_FILENAME = "manifest.db"
MANIFEST_SCHEMA_VERSION = 1
MAX_FILE_LIMIT = 100

_logger = logging.getLogger(__name__)

_NODIR_SUFFIX = ".nodir"
_NODIR_ROOTS = frozenset(NODIR_ROOTS)


def _allowlisted_nodir_root(name: str) -> str | None:
    _ = name
    return None


def _mixed_nodir_roots(wd: str) -> set[str]:
    _ = wd
    return set()


def _manifest_path(wd: str) -> str:
    return os.path.join(wd, MANIFEST_FILENAME)


def _normalize_rel_path(rel_path: str) -> str:
    if not rel_path or rel_path == ".":
        return "."
    rel_path = rel_path.replace("\\", "/")
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    return rel_path.strip("/") or "."


def _rel_join(parent: str, child: str) -> str:
    parent = _normalize_rel_path(parent)
    child = child.strip("/")
    if not child:
        return parent
    if parent in (".", ""):
        return child
    return f"{parent}/{child}"


def _rel_parent(rel_path: str) -> tuple[str, str]:
    rel_path = _normalize_rel_path(rel_path)
    if rel_path in (".", ""):
        return ".", ""
    head, _, tail = rel_path.rpartition("/")
    if not head:
        head = "."
    return head, tail


def _format_mtime_ns(ns: int) -> str:
    try:
        dt = datetime.fromtimestamp(ns / 1_000_000_000)
    except (OSError, OverflowError, ValueError):
        dt = datetime.fromtimestamp(0)
    return dt.strftime("%Y-%m-%d %H:%M")


def _format_human_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    size_units = ("B", "KB", "MB", "GB", "TB")
    unit_index = min(int(math.log(size_bytes, 1024)), len(size_units) - 1)
    scaled = round(size_bytes / (1024**unit_index), 2)
    return f"{scaled} {size_units[unit_index]}"


def remove_manifest(wd: str) -> None:
    path = _manifest_path(wd)
    try:
        os.remove(path)
    except FileNotFoundError:
        return
    except OSError:
        _logger.warning("Unable to remove manifest file at %s", path, exc_info=True)


def create_manifest(wd: str) -> str:
    wd = os.path.abspath(wd)
    if not os.path.isdir(wd):
        raise FileNotFoundError(f"{wd} is not a directory")

    manifest_path = _manifest_path(wd)
    tmp_path = manifest_path + ".tmp"

    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except OSError:
        _logger.warning("Could not remove stale manifest temp file %s", tmp_path, exc_info=True)

    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS entries (
                   dir_path TEXT NOT NULL,
                   name TEXT NOT NULL,
                   is_dir INTEGER NOT NULL,
                   is_symlink INTEGER NOT NULL DEFAULT 0,
                   symlink_is_dir INTEGER NOT NULL DEFAULT 0,
                   size_bytes INTEGER NOT NULL DEFAULT 0,
                   mtime_ns INTEGER NOT NULL DEFAULT 0,
                   child_count INTEGER,
                   symlink_target TEXT NOT NULL DEFAULT '',
                   sort_rank INTEGER NOT NULL DEFAULT 0,
                   PRIMARY KEY (dir_path, name)
               )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_dir_sort "
            "ON entries(dir_path, sort_rank DESC, name COLLATE NOCASE ASC, name COLLATE BINARY ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_name_case "
            "ON entries(dir_path, name COLLATE NOCASE ASC, name COLLATE BINARY ASC)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS meta (
                   key TEXT PRIMARY KEY,
                   value TEXT NOT NULL
               )"""
        )
        conn.execute("DELETE FROM entries")
        conn.execute("DELETE FROM meta")

        stack = [(wd, ".")]

        while stack:
            abs_dir, rel_dir = stack.pop()
            try:
                with os.scandir(abs_dir) as it:
                    dir_entries = [entry for entry in it if entry.name not in (".", "..")]
            except OSError:
                dir_entries = []

            rel_dir_norm = _normalize_rel_path(rel_dir)
            if rel_dir_norm != ".":
                parent_dir, dir_name = _rel_parent(rel_dir_norm)
                conn.execute(
                    "UPDATE entries SET child_count = ? WHERE dir_path = ? AND name = ?",
                    (len(dir_entries), parent_dir, dir_name),
                )
            else:
                conn.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                    ("root_child_count", str(len(dir_entries))),
                )

            batch = []
            for entry in dir_entries:
                name = entry.name
                entry_path = entry.path
                try:
                    stat_result = entry.stat(follow_symlinks=False)
                except OSError:
                    stat_result = None

                size_bytes = stat_result.st_size if stat_result else 0
                if stat_result is not None:
                    mtime_ns = getattr(stat_result, "st_mtime_ns", None)
                    if mtime_ns is None:
                        mtime_ns = int(stat_result.st_mtime * 1_000_000_000)
                else:
                    mtime_ns = 0

                is_dir = 1 if entry.is_dir(follow_symlinks=False) else 0
                is_symlink = 1 if entry.is_symlink() else 0
                symlink_target = ""
                symlink_is_dir = 0
                if is_symlink:
                    try:
                        symlink_target = os.readlink(entry_path)
                    except OSError:
                        symlink_target = ""
                    symlink_is_dir = 1 if os.path.isdir(entry_path) else 0

                sort_rank = 2 if is_dir else 0
                if not is_dir and _allowlisted_nodir_root(name) is not None:
                    # Treat allowlisted NoDir archive containers as directory-like for listing order.
                    sort_rank = 2
                batch.append(
                    (
                        rel_dir_norm,
                        name,
                        is_dir,
                        is_symlink,
                        symlink_is_dir,
                        size_bytes,
                        mtime_ns,
                        None,
                        symlink_target,
                        sort_rank,
                    )
                )

                if is_dir:
                    stack.append((entry_path, _rel_join(rel_dir_norm, name)))

            if batch:
                conn.executemany(
                    """INSERT OR REPLACE INTO entries(
                           dir_path, name, is_dir, is_symlink, symlink_is_dir,
                           size_bytes, mtime_ns, child_count, symlink_target, sort_rank
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    batch,
                )

        generated_at = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("schema_version", str(MANIFEST_SCHEMA_VERSION)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("generated_at", generated_at),
        )
        conn.commit()
    except (sqlite3.Error, OSError, ValueError, TypeError):
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()

    os.replace(tmp_path, manifest_path)
    return manifest_path


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _pattern_sql_prefilter(pattern: str) -> tuple[str | None, list[str]]:
    if not pattern:
        return None, []
    for index, char in enumerate(pattern):
        if char in ("*", "?", "["):
            break
    else:
        return "name = ?", [pattern]

    if index == 0:
        return None, []
    prefix = pattern[:index]
    if not prefix:
        return None, []
    escaped_prefix = _escape_like(prefix)
    return "name LIKE ? ESCAPE '\\'", [f"{escaped_prefix}%"]


def _append_query_params(url: str, params: dict[str, str] | None) -> str:
    if not params:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(params)}"


def _manifest_get_page_entries(
    root_wd: str,
    directory: str,
    filter_pattern: str,
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
    hide_mixed_nodir: bool = False,
):
    manifest_path = _manifest_path(root_wd)
    if not os.path.exists(manifest_path):
        return None

    try:
        rel_dir = os.path.relpath(directory, root_wd)
    except ValueError:
        return None

    rel_dir = _normalize_rel_path(rel_dir)
    if rel_dir.startswith(".."):
        return None

    mixed_roots = _mixed_nodir_roots(root_wd) if hide_mixed_nodir and rel_dir == "." else set()

    conn = sqlite3.connect(manifest_path)
    conn.row_factory = sqlite3.Row
    try:
        if rel_dir != ".":
            parent_dir, entry_name = _rel_parent(rel_dir)
            parent_row = conn.execute(
                "SELECT is_dir, symlink_is_dir FROM entries WHERE dir_path = ? AND name = ?",
                (parent_dir, entry_name),
            ).fetchone()
            if parent_row is None:
                return None
            if int(parent_row["is_dir"]) != 1:
                return None

        where_clause = "dir_path = ? AND name NOT LIKE '.%'"
        params = [rel_dir]
        if filter_pattern:
            prefilter_clause, prefilter_params = _pattern_sql_prefilter(filter_pattern)
            if prefilter_clause:
                where_clause += f" AND {prefilter_clause}"
                params += prefilter_params

        sort_column = {
            "date": "mtime_ns",
            "size": "size_bytes",
            "name": "name",
        }.get(sort_by, "name")
        direction = "ASC" if sort_order == "asc" else "DESC"
        if sort_column == "name":
            primary_sort = f"{sort_column} COLLATE NOCASE {direction}"
        else:
            primary_sort = f"{sort_column} {direction}"
        order_clause = (
            f"ORDER BY sort_rank DESC, {primary_sort}, "
            "name COLLATE NOCASE ASC, name COLLATE BINARY ASC"
        )

        select_clause = f"""SELECT name, is_dir, is_symlink, symlink_is_dir, size_bytes, mtime_ns,
                                   child_count, symlink_target, sort_rank
                            FROM entries
                            WHERE {where_clause}
                            {order_clause}"""

        if filter_pattern:
            start_index = max(0, (page - 1) * page_size)
            total_items = 0
            rows = []
            for row in conn.execute(select_clause, params):
                name = row["name"]
                if not fnmatch.fnmatchcase(name, filter_pattern):
                    continue
                if total_items >= start_index and len(rows) < page_size:
                    rows.append(row)
                total_items += 1
        else:
            total_items = conn.execute(
                f"SELECT COUNT(*) AS total FROM entries WHERE {where_clause}",
                params,
            ).fetchone()["total"]
            offset = max(0, (page - 1) * page_size)
            rows = conn.execute(
                f"{select_clause} LIMIT ? OFFSET ?",
                params + [page_size, offset],
            ).fetchall()

        entries = []
        for row in rows:
            name = row["name"]
            nodir_root = _allowlisted_nodir_root(name)
            if mixed_roots and (
                name in mixed_roots
                or (nodir_root is not None and nodir_root in mixed_roots)
            ):
                continue

            is_dir = bool(row["is_dir"]) or (
                nodir_root is not None and not bool(row["is_symlink"]) and not bool(row["symlink_is_dir"])
            )
            is_symlink = bool(row["is_symlink"])
            symlink_is_dir = bool(row["symlink_is_dir"])

            mtime_display = _format_mtime_ns(int(row["mtime_ns"]))
            if is_dir:
                if nodir_root is not None and not bool(row["is_dir"]):
                    hr_value = "0 items"
                else:
                    child_dir = _rel_join(rel_dir, name)
                    child_count = conn.execute(
                        "SELECT COUNT(*) AS total FROM entries WHERE dir_path = ? AND name NOT LIKE '.%'",
                        (child_dir,),
                    ).fetchone()["total"]
                    hr_value = f"{child_count} items"
            else:
                hr_value = _format_human_size(int(row["size_bytes"]))

            sym_target = ""
            if is_symlink:
                target = row["symlink_target"] or ""
                if symlink_is_dir and target and not target.endswith("/"):
                    target = f"{target}/"
                sym_target = f"->{target}" if target else "->"

            entries.append(
                (name, is_dir, mtime_display, hr_value, is_symlink, sym_target, symlink_is_dir)
            )
    finally:
        conn.close()

    return entries, total_items


def _should_hide_entry(name: str) -> bool:
    return name.startswith(".") and name not in (".", "..")


def _scan_directory_snapshot(
    directory: str,
    filter_pattern: str,
    sort_by: str,
    sort_order: str,
    root_wd: str | None = None,
    hide_mixed_nodir: bool = False,
) -> tuple[list[dict], int]:
    entries = []
    directory_abs = os.path.abspath(directory)
    mixed_roots: set[str] = set()
    if hide_mixed_nodir and root_wd is not None and directory_abs == os.path.abspath(root_wd):
        mixed_roots = _mixed_nodir_roots(root_wd)
    try:
        with os.scandir(directory) as it:
            for entry in it:
                name = entry.name
                if name in (".", ".."):
                    continue
                nodir_root = _allowlisted_nodir_root(name)
                if mixed_roots and (
                    name in mixed_roots
                    or (nodir_root is not None and nodir_root in mixed_roots)
                ):
                    continue
                if _should_hide_entry(name):
                    continue
                if filter_pattern and not fnmatch.fnmatchcase(name, filter_pattern):
                    continue

                try:
                    stat_result = entry.stat(follow_symlinks=False)
                except OSError:
                    stat_result = None

                size_bytes = stat_result.st_size if stat_result else 0
                if stat_result is not None:
                    mtime_ns = getattr(stat_result, "st_mtime_ns", None)
                    if mtime_ns is None:
                        mtime_ns = int(stat_result.st_mtime * 1_000_000_000)
                else:
                    mtime_ns = 0

                is_dir = entry.is_dir(follow_symlinks=False)
                is_symlink = entry.is_symlink()
                symlink_is_dir = False
                symlink_target = ""
                if is_symlink:
                    try:
                        symlink_target = os.readlink(entry.path)
                    except OSError:
                        symlink_target = ""
                    try:
                        symlink_is_dir = os.path.isdir(entry.path)
                    except OSError:
                        symlink_is_dir = False

                is_nodir_dir_like = (
                    nodir_root is not None and not is_dir and not is_symlink and not symlink_is_dir
                )
                effective_is_dir = is_dir or is_nodir_dir_like

                entries.append(
                    {
                        "name": name,
                        "name_casefold": name.casefold(),
                        "is_dir": effective_is_dir,
                        "is_symlink": is_symlink,
                        "symlink_is_dir": symlink_is_dir,
                        "symlink_target": symlink_target,
                        "size_bytes": int(size_bytes),
                        "mtime_ns": int(mtime_ns),
                        "sort_rank": 2 if effective_is_dir else 0,
                    }
                )
    except OSError:
        return [], 0

    sort_fields = {"name", "date", "size"}
    sort_orders = {"asc", "desc"}
    sort_by = sort_by if sort_by in sort_fields else "name"
    sort_order = sort_order if sort_order in sort_orders else "asc"

    def _compare_entries(left: dict, right: dict) -> int:
        if left["sort_rank"] != right["sort_rank"]:
            return -1 if left["sort_rank"] > right["sort_rank"] else 1

        if sort_by == "date":
            left_primary = left["mtime_ns"]
            right_primary = right["mtime_ns"]
        elif sort_by == "size":
            left_primary = left["size_bytes"]
            right_primary = right["size_bytes"]
        else:
            left_primary = left["name_casefold"]
            right_primary = right["name_casefold"]

        if left_primary != right_primary:
            if sort_order == "asc":
                return -1 if left_primary < right_primary else 1
            return -1 if left_primary > right_primary else 1

        if left["name_casefold"] != right["name_casefold"]:
            return -1 if left["name_casefold"] < right["name_casefold"] else 1
        if left["name"] != right["name"]:
            return -1 if left["name"] < right["name"] else 1
        return 0

    entries.sort(key=cmp_to_key(_compare_entries))
    return entries, len(entries)


async def _format_page_entries(entries: list[dict], directory: str) -> list[tuple]:
    if not entries:
        return []

    formatted = []
    dir_indices = []
    for index, entry in enumerate(entries):
        name = entry["name"]
        is_dir = entry["is_dir"]
        is_symlink = entry["is_symlink"]
        symlink_is_dir = entry["symlink_is_dir"]

        sym_target = ""
        if is_symlink:
            target = entry.get("symlink_target") or ""
            if symlink_is_dir and target and not target.endswith("/"):
                target = f"{target}/"
            sym_target = f"->{target}" if target else "->"

        if is_dir:
            hr_value = ""
            dir_indices.append((index, _join(directory, name)))
        else:
            hr_value = _format_human_size(entry["size_bytes"])

        formatted.append(
            (
                name,
                is_dir,
                _format_mtime_ns(entry["mtime_ns"]),
                hr_value,
                is_symlink,
                sym_target,
                symlink_is_dir,
            )
        )

    if dir_indices:
        loop = asyncio.get_running_loop()
        start_time = loop.time()
        totals = await asyncio.gather(
            *[get_total_items(dir_path) for _, dir_path in dir_indices],
            return_exceptions=True,
        )
        elapsed = loop.time() - start_time
        if elapsed > 5:
            _logger.warning(
                "browse.get_entries() directory count took %.1f seconds; consider investigating system load.",
                elapsed,
            )

        for (entry_index, _), total_items in zip(dir_indices, totals):
            if isinstance(total_items, Exception):
                raise total_items
            entry = formatted[entry_index]
            formatted[entry_index] = (
                entry[0],
                entry[1],
                entry[2],
                f"{total_items} items",
                entry[4],
                entry[5],
                entry[6],
            )

    return formatted


def _count_directory_items(
    directory: str,
    filter_pattern: str,
    root_wd: str | None = None,
    hide_mixed_nodir: bool = False,
) -> int:
    total = 0
    directory_abs = os.path.abspath(directory)
    mixed_roots: set[str] = set()
    if hide_mixed_nodir and root_wd is not None and directory_abs == os.path.abspath(root_wd):
        mixed_roots = _mixed_nodir_roots(root_wd)
    try:
        with os.scandir(directory) as it:
            for entry in it:
                name = entry.name
                if name in (".", ".."):
                    continue
                nodir_root = _allowlisted_nodir_root(name)
                if mixed_roots and (
                    name in mixed_roots
                    or (nodir_root is not None and nodir_root in mixed_roots)
                ):
                    continue
                if _should_hide_entry(name):
                    continue
                if filter_pattern and not fnmatch.fnmatchcase(name, filter_pattern):
                    continue
                total += 1
    except OSError:
        return 0
    return total


async def get_entries(
    directory,
    filter_pattern,
    start,
    end,
    page_size,
    sort_by: str = "name",
    sort_order: str = "asc",
    root_wd: str | None = None,
    hide_mixed_nodir: bool = False,
):
    """Retrieve paginated directory entries using deterministic ordering."""

    entries, _total_items = await asyncio.to_thread(
        _scan_directory_snapshot,
        directory,
        filter_pattern,
        sort_by,
        sort_order,
        root_wd,
        hide_mixed_nodir,
    )
    start_index = max(0, start - 1)
    end_index = min(len(entries), end)
    return await _format_page_entries(entries[start_index:end_index], directory)


async def get_total_items(
    directory,
    filter_pattern: str = "",
    *,
    root_wd: str | None = None,
    hide_mixed_nodir: bool = False,
):
    """Count total items in the directory, respecting the filter_pattern."""

    return await asyncio.to_thread(
        _count_directory_items,
        directory,
        filter_pattern,
        root_wd,
        hide_mixed_nodir,
    )


async def get_page_entries(
    wd,
    directory,
    page=1,
    page_size=MAX_FILE_LIMIT,
    filter_pattern="",
    sort_by: str = "name",
    sort_order: str = "asc",
    hide_mixed_nodir: bool = False,
):
    """List directory contents with pagination and optional filtering."""
    skip_manifest = False
    if hide_mixed_nodir:
        skip_manifest = bool(_mixed_nodir_roots(str(wd)))

    if not skip_manifest:
        manifest_result = await asyncio.to_thread(
            _manifest_get_page_entries,
            wd,
            directory,
            filter_pattern,
            page,
            page_size,
            sort_by,
            sort_order,
            hide_mixed_nodir,
        )
        if manifest_result is not None:
            entries, total_items = manifest_result
            return entries, total_items, True

    start_index = max(0, (page - 1) * page_size)
    end_index = start_index + page_size

    loop = asyncio.get_running_loop()
    start_time = loop.time()
    entries, total_items = await asyncio.to_thread(
        _scan_directory_snapshot,
        directory,
        filter_pattern,
        sort_by,
        sort_order,
        wd,
        hide_mixed_nodir,
    )
    page_entries = await _format_page_entries(entries[start_index:end_index], directory)
    elapsed = loop.time() - start_time
    if elapsed > 5:
        _logger.warning(
            "browse.get_page_entries() completed after %.1f seconds; large directories may impact responsiveness.",
            elapsed,
        )
    return page_entries, total_items, False


def get_pad(x):
    if x < 1:
        return " "
    return x * " "


async def html_dir_list(
    _dir,
    runid,
    wd,
    request_path,
    diff_wd,
    base_query,
    page=1,
    page_size=MAX_FILE_LIMIT,
    filter_pattern="",
    sort_by: str = "name",
    sort_order: str = "asc",
    hide_mixed_nodir: bool = False,
    page_entries_override: list[tuple] | None = None,
    total_items_override: int | None = None,
    using_manifest_override: bool | None = None,
):
    _padding = " "
    s = []

    base_query = base_query or {}
    if page_entries_override is not None:
        page_entries = page_entries_override
        total_items = total_items_override if total_items_override is not None else len(page_entries_override)
        using_manifest = bool(using_manifest_override)
    else:
        page_entries, total_items, using_manifest = await get_page_entries(
            wd,
            _dir,
            page,
            page_size,
            filter_pattern,
            sort_by,
            sort_order,
            hide_mixed_nodir=hide_mixed_nodir,
        )

    original_request_path = request_path
    if filter_pattern:
        request_path = request_path.rsplit("/", 1)[0]

    query_suffix = f"?{urlencode(base_query)}" if base_query else ""
    parquet_filter_query = {}
    pqf_value = base_query.get("pqf")
    if pqf_value:
        parquet_filter_query["pqf"] = pqf_value

    def _default_order_for_field(field: str) -> str:
        if field == "name":
            return "asc"
        return "desc"

    def _build_sort_link(field: str, label: str, width: int) -> str:
        is_active = sort_by == field
        direction_symbol = "↑" if sort_order == "asc" else "↓"
        indicator = f" [{direction_symbol}]" if is_active else ""
        display = f"{label}{indicator}"
        pad = get_pad(max(1, width - len(display)))
        next_order = "desc" if is_active and sort_order == "asc" else "asc"
        if not is_active:
            next_order = _default_order_for_field(field)
        query_params = {
            **{k: v for k, v in base_query.items() if k not in ("sort", "order")},
            "sort": field,
            "order": next_order,
        }
        href = original_request_path
        if query_params:
            href = f"{href}?{urlencode(query_params)}"
        return f'<a href="{href}" class="browse-sort-link">{display}{pad}</a>'

    name_col_width = max(36, max(len(entry[0]) for entry in page_entries) + 2) if page_entries else 36
    date_col_width = max(len(_format_mtime_ns(0)), 16)
    size_col_width = 12

    header_line = (
        f'<span class="browse-header">{_padding}  '
        f"{_build_sort_link('name', 'Name', name_col_width)}"
        f"{_build_sort_link('date', 'Modified', date_col_width)}"
        f"{_build_sort_link('size', 'Size', size_col_width)}"
        "Actions</span>\n"
    )
    s.append(header_line)

    for i, entry in enumerate(page_entries):
        _file = entry[0]
        is_dir = entry[1]
        path = _join(_dir, _file)
        ts_pad = get_pad(name_col_width - len(_file))
        last_modified_time = entry[2]
        _tree_char = "├└"[i == len(page_entries) - 1]
        row_html = ""

        if is_dir:
            file_link = _join(request_path, _file)
            item_count = entry[3]
            sym_target = entry[5]
            item_pad = get_pad(8 - len(item_count.split()[0]))
            end_pad = " " * 32
            dir_href = f"{file_link}/"
            if query_suffix:
                dir_href = f"{dir_href}{query_suffix}"
            row_html = (
                _padding
                + f'{_tree_char} <a href="{dir_href}"><b>{_file}{ts_pad}</b></a>{last_modified_time} {item_pad}{item_count}{end_pad}{sym_target}  \n'
            )
        else:
            file_link = _join(request_path, _file)
            sym_target = entry[5]
            file_size = entry[3]
            item_pad = get_pad(8 - len(file_size.split()[0]))
            size_tokens = file_size.split()
            unit = size_tokens[1] if len(size_tokens) > 1 else ""
            dl_pad = get_pad(6 - len(unit))
            dl_link = "          "
            dl_url = None
            symlink_is_dir = entry[6] if len(entry) > 6 else False
            if not symlink_is_dir:
                dl_url = _join(request_path, _file).replace("/browse/", "/download/")
                dl_link = f'{dl_pad}<a href="{dl_url}">download</a>'
            file_lower = _file.lower()
            is_parquet_file = file_lower.endswith((".parquet", ".pq"))
            parquet_link_attrs = ''
            if is_parquet_file:
                file_link = _append_query_params(file_link, parquet_filter_query)
                parquet_link_attrs = ' data-parquet-link="1"'
                if dl_url is not None:
                    dl_url = _append_query_params(dl_url, parquet_filter_query)
                    dl_link = f'{dl_pad}<a href="{dl_url}"{parquet_link_attrs}>download</a>'
            gl_link = "      "
            if file_lower.endswith((".arc", ".tif", ".img", ".nc")):
                gl_url = _join(request_path, _file).replace("/browse/", "/gdalinfo/")
                gl_link = f'  <a href="{gl_url}">gdalinfo</a>'
            if is_parquet_file:
                gl_url = _join(request_path, _file).replace("/browse/", "/download/")
                csv_query = {"as_csv": "1"}
                if pqf_value:
                    csv_query["pqf"] = pqf_value
                gl_url = _append_query_params(gl_url, csv_query)
                gl_link = f'  <a href="{gl_url}"{parquet_link_attrs}>.csv</a>'
            repr_link = "           "
            dtale_link = "          "
            schema_link = "          "
            if file_lower.endswith(".man") or file_lower.endswith(".sol"):
                repr_url = _join(request_path, _file) + "?repr=1"
                repr_link = f'  <a href="{repr_url}">annotated</a>'
            if (
                file_lower.endswith(".parquet")
                or file_lower.endswith(".pq")
                or file_lower.endswith(".feather")
                or file_lower.endswith(".arrow")
                or file_lower.endswith(".csv")
                or file_lower.endswith(".csv.gz")
                or file_lower.endswith(".tsv")
                or file_lower.endswith(".tsv.gz")
                or file_lower.endswith(".pkl")
                or file_lower.endswith(".pickle")
            ):
                dtale_url = _join(request_path, _file).replace("/browse/", "/dtale/")
                if is_parquet_file:
                    dtale_url = _append_query_params(dtale_url, parquet_filter_query)
                    dtale_link = f'  <a href="{dtale_url}"{parquet_link_attrs}>d-tale</a>'
                else:
                    dtale_link = f'  <a href="{dtale_url}">d-tale</a>'
            if is_parquet_file:
                schema_url = _join(request_path, _file).replace("/browse/", "/schema/")
                panel_id = f"parquet-schema-panel-{i}"
                schema_link = (
                    f'  <a href="{schema_url}"'
                    f' data-parquet-schema-link="1" data-schema-url="{schema_url}"'
                    f' data-schema-target="{panel_id}" aria-expanded="false">schema</a>'
                )

            diff_link = "    "
            if diff_wd and not file_lower.endswith((".tif", ".parquet", ".gz", ".img")):
                diff_path = _join(diff_wd, os.path.relpath(path, wd))
                if _exists(diff_path):
                    diff_url = _join(request_path, _file).replace("/browse/", "/diff/")
                    if query_suffix:
                        diff_url = f"{diff_url}{query_suffix}"
                    diff_link = f'  <a href="{diff_url}">diff</a>'
            row_html = (
                _padding
                + f'{_tree_char} <a href="{file_link}"{parquet_link_attrs}>{_file}{ts_pad}</a>{last_modified_time} {item_pad}{file_size}{dl_link}{gl_link}{repr_link}{dtale_link}{schema_link}{diff_link}{sym_target}\n'
            )

        if i % 2:
            row_html = f'<span class="even-row">{row_html}</span>'
        else:
            row_html = f'<span class="odd-row">{row_html}</span>'
        s.append(row_html)

    return "".join(s), total_items, using_manifest
