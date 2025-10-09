
"""
Browse Microservice
===================

This module houses the Starlette microservice that powers the web-based file explorer used in WEPP Cloud.  The service
retains the original browse blueprint behaviour with minimal changes so the underlying view logic remains untouched.

Template Organization
---------------------
All rendering is handled by Jinja templates bundled with the original blueprint under
`wepppy/weppcloud/routes/browse/templates/browse/`:

- `directory.htm` - top-level directory listing view with pagination, diff controls, and the keyboard command bar.
- `not_found.htm` - 404-style response shown when a requested directory segment is missing.
- `_path_input_script.htm` - shared script that wires up the inline path input field for directory and 404 pages.
- `arc_file.htm` - minimal viewer for “.arc” outputs.
- `data_table.htm` - table presentation for CSV/TSV/Parquet/Pickle content rendered via pandas.
- `text_file.htm` - general text viewer (including the command bar) for other readable file types.

Routes
------
- `/runs/{runid}/{config}/browse/`
- `/runs/{runid}/{config}/browse/{subpath:path}`

Key Behaviours
--------------
- **Directory Browsing** - `browse_response` delegates to `html_dir_list` to build directory listings with pagination
  and optional shell-style filtering, then renders `directory.htm`.
- **File Viewing** - Depending on the requested file type, responses are streamed directly, downloaded, or rendered via
  `arc_file.htm`, `data_table.htm`, or `text_file.htm`.
- **Diff Support** - When the `diff` query argument is present the microservice attempts to locate the requested object
  in the comparison run and surfaces diff links in directory listings.
- **Security** - `_browse_tree_helper` prevents directory traversal, validates filter syntax, and ensures the
  requested path stays inside the working directory returned by `get_wd`.
- **Performance** - Directory counts and listings run concurrently via asyncio tasks to keep large listings responsive.

For maintenance purposes, adjust template markup within the dedicated `templates/browse/` files; Python logic in this
module should remain focused on routing, filesystem queries, and response orchestration.
"""

import asyncio
import os
import re
import math
import json
import logging
import html
import traceback
from html import escape as html_escape
import sqlite3

from urllib.parse import urlencode

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from os.path import abspath, basename

import gzip
from functools import lru_cache
from pathlib import Path
from datetime import datetime
from http import HTTPStatus

import pandas as pd
from cmarkgfm import github_flavored_markdown_to_html as markdown_to_html
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request as StarletteRequest
from starlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response as StarletteResponse,
)
from starlette.routing import Route
from wepppy.microservices._download import create_routes as create_download_routes
from wepppy.microservices._gdalinfo import create_routes as create_gdalinfo_routes

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.weppcloud.routes.usersum.usersum import _load_parameter_catalog


class QueryParamsAdapter:
    """Minimal shim to mimic Flask's request.args mapping."""

    def __init__(self, query_params):
        self._query_params = query_params

    def get(self, key, default=None, type=None):
        value = self._query_params.get(key, default)
        if value is default:
            return default
        if type is None:
            return value
        try:
            return type(value)
        except (TypeError, ValueError):
            return default

    def items(self):
        return self._query_params.items()

    def __iter__(self):
        return iter(self._query_params)

    def __contains__(self, item):
        return item in self._query_params

    def __getitem__(self, item):
        return self._query_params[item]


class FlaskRequestAdapter:
    """Wrap Starlette's Request to expose the minimal Flask attributes used here."""

    def __init__(self, request: StarletteRequest):
        self._request = request
        self.args = QueryParamsAdapter(request.query_params)
        self.headers = request.headers
        self.base_url = str(request.base_url)
        self.path = request.url.path

    def __getattr__(self, item):
        return getattr(self._request, item)


BASE_DIR = Path(__file__).resolve().parent
WEPP_CLOUD_DIR = (BASE_DIR.parent / 'weppcloud').resolve()
BROWSE_TEMPLATES_DIR = (WEPP_CLOUD_DIR / 'routes' / 'browse' / 'templates').resolve()
COMMAND_BAR_TEMPLATES_DIR = (WEPP_CLOUD_DIR / 'routes' / 'command_bar' / 'templates').resolve()
SITE_TEMPLATES_DIR = (WEPP_CLOUD_DIR / 'templates').resolve()

templates_env = Environment(
    loader=FileSystemLoader([
        str(BROWSE_TEMPLATES_DIR),
        str(COMMAND_BAR_TEMPLATES_DIR),
        str(SITE_TEMPLATES_DIR),
    ]),
    autoescape=select_autoescape(['html', 'j2', 'xml'])
)


def _normalize_prefix(prefix: str | None) -> str:
    if not prefix:
        return ''
    trimmed = prefix.strip()
    if not trimmed or trimmed == '/':
        return ''
    return '/' + trimmed.strip('/')


SITE_PREFIX = _normalize_prefix(os.getenv('SITE_PREFIX', '/weppcloud'))


def _prefix_path(path: str) -> str:
    if not SITE_PREFIX:
        return path
    return SITE_PREFIX + path if path.startswith('/') else SITE_PREFIX + '/' + path


MANIFEST_FILENAME = 'manifest.db'
MANIFEST_SCHEMA_VERSION = 1


def _manifest_path(wd: str) -> str:
    return os.path.join(wd, MANIFEST_FILENAME)


def _normalize_rel_path(rel_path: str) -> str:
    if not rel_path or rel_path == '.':
        return '.'
    rel_path = rel_path.replace('\\', '/')
    if rel_path.startswith('./'):
        rel_path = rel_path[2:]
    return rel_path.strip('/') or '.'


def _rel_join(parent: str, child: str) -> str:
    parent = _normalize_rel_path(parent)
    child = child.strip('/')
    if not child:
        return parent
    if parent in ('.', ''):
        return child
    return f'{parent}/{child}'


def _rel_parent(rel_path: str) -> tuple[str, str]:
    rel_path = _normalize_rel_path(rel_path)
    if rel_path in ('.', ''):
        return '.', ''
    head, _, tail = rel_path.rpartition('/')
    if not head:
        head = '.'
    return head, tail


def _format_mtime_ns(ns: int) -> str:
    try:
        dt = datetime.fromtimestamp(ns / 1_000_000_000)
    except (OSError, OverflowError, ValueError):
        dt = datetime.fromtimestamp(0)
    return dt.strftime('%Y-%m-%d %H:%M')


def _format_human_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return '0 B'
    size_units = ('B', 'KB', 'MB', 'GB', 'TB')
    unit_index = min(int(math.log(size_bytes, 1024)), len(size_units) - 1)
    scaled = round(size_bytes / (1024 ** unit_index), 2)
    return f'{scaled} {size_units[unit_index]}'


# NOTE: Simplified url_for shim mimics Flask asset lookup.
# Extend this mapping or integrate with Starlette routing before using additional blueprint templates.
def url_for(endpoint: str, **values) -> str:
    if endpoint == 'command_bar.static':
        filename = values.get('filename', '')
        return _prefix_path(f'/command_bar/static/{filename}')
    if endpoint == 'static':
        filename = values.get('filename', '')
        return _prefix_path(f'/static/{filename}')
    suffix = endpoint.replace('.', '/')
    return _prefix_path(f'/{suffix}')


templates_env.globals['url_for'] = url_for
templates_env.globals['site_prefix'] = SITE_PREFIX


def render_template(template_name, **context):
    context.setdefault('site_prefix', SITE_PREFIX)
    template = templates_env.get_template(template_name)
    return template.render(**context)


async def _run_shell_command(command: str, cwd: str) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await process.communicate()
    stdout_text = stdout.decode('utf-8', errors='replace')
    stderr_text = stderr.decode('utf-8', errors='replace')
    if process.returncode != 0 and stderr_text:
        _logger.debug('Command failed (%s): %s', cwd, stderr_text.strip())
    return process.returncode, stdout_text, stderr_text


def _read_gzip_text(path: str) -> str:
    with gzip.open(path, 'rt') as fp:
        return fp.read()


def _read_text_file(path: str) -> str:
    with open(path) as fp:
        return fp.read()


async def _async_read_gzip(path: str) -> str:
    return await asyncio.to_thread(_read_gzip_text, path)


async def _async_read_text(path: str) -> str:
    return await asyncio.to_thread(_read_text_file, path)


async def _async_df_to_html(df: pd.DataFrame) -> str:
    return await asyncio.to_thread(
        df.to_html,
        classes=['sortable table table-nonfluid'],
        border=0,
        justify='left'
    )


def jsonify(payload):
    return JSONResponse(payload)


def abort(status_code, detail=None):
    raise HTTPException(status_code=status_code, detail=detail)


def redirect(location, code=302):
    return RedirectResponse(location, status_code=code)


class Response(StarletteResponse):
    def __init__(self, response=None, status=200, mimetype=None):
        super().__init__(content=response if response is not None else b'', status_code=status, media_type=mimetype)


def send_file(path, as_attachment=False, download_name=None):
    if as_attachment:
        filename = download_name or os.path.basename(path)
        return FileResponse(path, filename=filename)

    response = FileResponse(path)
    if download_name:
        response.headers['Content-Disposition'] = f'inline; filename="{download_name}"'
    return response


def ensure_response(value):
    if isinstance(value, StarletteResponse):
        return value

    if isinstance(value, tuple) and len(value) == 2:
        body, status_code = value
        if isinstance(body, StarletteResponse):
            body.status_code = status_code
            return body
        return HTMLResponse(body, status_code=status_code)

    if isinstance(value, (str, Markup)):
        return HTMLResponse(str(value))

    if value is None:
        return StarletteResponse(status_code=204)

    return value

MAX_FILE_LIMIT = 100
MARKDOWN_EXTENSIONS = ('.md', '.markdown', '.mdown', '.mkdn')


_logger = logging.getLogger(__name__)


def remove_manifest(wd: str) -> None:
    path = _manifest_path(wd)
    try:
        os.remove(path)
    except FileNotFoundError:
        return
    except OSError:
        _logger.warning('Unable to remove manifest file at %s', path, exc_info=True)


def create_manifest(wd: str) -> str:
    wd = os.path.abspath(wd)
    if not os.path.isdir(wd):
        raise FileNotFoundError(f'{wd} is not a directory')

    manifest_path = _manifest_path(wd)
    tmp_path = manifest_path + '.tmp'

    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except OSError:
        _logger.warning('Could not remove stale manifest temp file %s', tmp_path, exc_info=True)

    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA temp_store=MEMORY;')
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS entries (
                   dir_path TEXT NOT NULL,
                   name TEXT NOT NULL,
                   is_dir INTEGER NOT NULL,
                   is_symlink INTEGER NOT NULL,
                   symlink_is_dir INTEGER NOT NULL,
                   size_bytes INTEGER NOT NULL,
                   mtime_ns INTEGER NOT NULL,
                   child_count INTEGER,
                   symlink_target TEXT,
                   sort_rank INTEGER NOT NULL,
                   PRIMARY KEY (dir_path, name)
               )'''
        )
        conn.execute(
            'CREATE INDEX IF NOT EXISTS entries_dir_sort ON entries(dir_path, sort_rank DESC, name)'
        )
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS meta (
                   key TEXT PRIMARY KEY,
                   value TEXT
               )'''
        )

        stack = [(wd, '.')]

        while stack:
            abs_dir, rel_dir = stack.pop()
            try:
                with os.scandir(abs_dir) as it:
                    dir_entries = [entry for entry in it if entry.name not in ('.', '..')]
            except OSError:
                dir_entries = []

            rel_dir_norm = _normalize_rel_path(rel_dir)
            if rel_dir_norm != '.':
                parent_dir, dir_name = _rel_parent(rel_dir_norm)
                conn.execute(
                    'UPDATE entries SET child_count = ? WHERE dir_path = ? AND name = ?',
                    (len(dir_entries), parent_dir, dir_name),
                )
            else:
                conn.execute(
                    'INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)',
                    ('root_child_count', str(len(dir_entries))),
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
                    mtime_ns = getattr(stat_result, 'st_mtime_ns', None)
                    if mtime_ns is None:
                        mtime_ns = int(stat_result.st_mtime * 1_000_000_000)
                else:
                    mtime_ns = 0

                is_dir = 1 if entry.is_dir(follow_symlinks=False) else 0
                is_symlink = 1 if entry.is_symlink() else 0
                symlink_target = ''
                symlink_is_dir = 0
                if is_symlink:
                    try:
                        symlink_target = os.readlink(entry_path)
                    except OSError:
                        symlink_target = ''
                    symlink_is_dir = 1 if os.path.isdir(entry_path) else 0

                sort_rank = 2 if is_dir else 0
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
                    '''INSERT OR REPLACE INTO entries(
                           dir_path, name, is_dir, is_symlink, symlink_is_dir,
                           size_bytes, mtime_ns, child_count, symlink_target, sort_rank
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    batch,
                )

        generated_at = datetime.utcnow().isoformat()
        conn.execute(
            'INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)',
            ('schema_version', str(MANIFEST_SCHEMA_VERSION)),
        )
        conn.execute(
            'INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)',
            ('generated_at', generated_at),
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

    os.replace(tmp_path, manifest_path)
    return manifest_path


def _manifest_get_page_entries(root_wd: str, directory: str, filter_pattern: str, page: int, page_size: int):
    manifest_path = _manifest_path(root_wd)
    if not os.path.exists(manifest_path):
        return None

    try:
        rel_dir = os.path.relpath(directory, root_wd)
    except ValueError:
        return None

    rel_dir = _normalize_rel_path(rel_dir)
    if rel_dir.startswith('..'):
        return None

    conn = sqlite3.connect(manifest_path)
    conn.row_factory = sqlite3.Row
    try:
        if rel_dir != '.':
            parent_dir, entry_name = _rel_parent(rel_dir)
            parent_row = conn.execute(
                'SELECT is_dir, symlink_is_dir FROM entries WHERE dir_path = ? AND name = ?',
                (parent_dir, entry_name),
            ).fetchone()
            if parent_row is None:
                return None
            if int(parent_row['is_dir']) != 1:
                return None

        where_clause = 'dir_path = ?'
        params = [rel_dir]
        if filter_pattern:
            where_clause += ' AND name GLOB ?'
            params.append(filter_pattern)

        total_items = conn.execute(
            f'SELECT COUNT(*) AS total FROM entries WHERE {where_clause}',
            params,
        ).fetchone()['total']

        offset = max(0, (page - 1) * page_size)
        rows = conn.execute(
            f'''SELECT name, is_dir, is_symlink, symlink_is_dir, size_bytes, mtime_ns,
                       child_count, symlink_target, sort_rank
                FROM entries
                WHERE {where_clause}
                ORDER BY sort_rank DESC, name
                LIMIT ? OFFSET ?''',
            params + [page_size, offset],
        ).fetchall()
    finally:
        conn.close()

    entries = []
    for row in rows:
        name = row['name']
        is_dir = bool(row['is_dir'])
        is_symlink = bool(row['is_symlink'])
        symlink_is_dir = bool(row['symlink_is_dir'])

        mtime_display = _format_mtime_ns(int(row['mtime_ns']))
        if is_dir:
            child_count = row['child_count'] if row['child_count'] is not None else 0
            hr_value = f'{child_count} items'
        else:
            hr_value = _format_human_size(int(row['size_bytes']))

        sym_target = ''
        if is_symlink:
            target = row['symlink_target'] or ''
            if symlink_is_dir and target and not target.endswith('/'):
                target = f'{target}/'
            sym_target = f'->{target}' if target else '->'

        entries.append(
            (name, is_dir, mtime_display, hr_value, is_symlink, sym_target, symlink_is_dir)
        )

    return entries, total_items


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


@lru_cache(maxsize=1)
def _usersum_parameter_names():
    try:
        by_name, _ = _load_parameter_catalog()
    except Exception:
        _logger.exception('Unable to load usersum parameter catalog')
        return tuple()
    return tuple(sorted(by_name.keys(), key=len, reverse=True))


@lru_cache(maxsize=1)
def _usersum_pattern():
    names = _usersum_parameter_names()
    if not names:
        return None
    return re.compile(r'\b(' + '|'.join(re.escape(name) for name in names) + r')\b')


def _wrap_usersum_spans(text):
    if text is None:
        return Markup('')

    pattern = _usersum_pattern()
    escaped = html.escape(text)
    if not pattern:
        return Markup(escaped)

    def replacer(match):
        name = match.group(0)
        return f'<span data-usersum="{name}">{name}</span>'

    highlighted = pattern.sub(replacer, escaped)
    return Markup(highlighted)


def _generate_repr_content(path):
    path_lower = path.lower()
    try:
        if path_lower.endswith('.man'):
            from wepppy.wepp.management import read_management
            management_obj = read_management(path)
            return repr(management_obj)
        if path_lower.endswith('.sol'):
            from wepppy.wepp.soils.utils import WeppSoilUtil
            soil = WeppSoilUtil(path)
            return repr(soil)
    except Exception:
        _logger.exception('Failed to generate repr content for %s', path)
        raise

    return None


def _validate_filter_pattern(pattern):
    """
    Validate filter_pattern to ensure it’s a safe wildcard pattern.
    Returns True if valid, False otherwise.
    """
    # Allowed: alphanumeric, *, ?, [], -, ., _
    # Disallowed: shell metacharacters like &, |, ;, <, >, $, `, ", ', etc.
    if not pattern:  # Empty pattern is valid
        return True
    safe_pattern = r'^[a-zA-Z0-9_*?[\]\-\.]+$'
    return bool(re.match(safe_pattern, pattern))


def _ensure_markup(value):
    if isinstance(value, Markup):
        return value
    return Markup(value)


def _render_browse_error_page(*,
                              runid: str,
                              config: str,
                              diff_runid: str,
                              breadcrumbs_html: str | Markup,
                              project_href: str | Markup,
                              error_message: str | Markup,
                              page_title: str) -> str:
    return render_template(
        'browse/not_found.htm',
        runid=runid,
        config=config,
        diff_runid=diff_runid,
        breadcrumbs_html=_ensure_markup(breadcrumbs_html),
        project_href=_ensure_markup(project_href),
        error_message=_ensure_markup(error_message),
        page_title=page_title,
    )


def _path_not_found_response(runid, subpath, wd, request, config):
    """
    Generates an HTML response for a path that was not found,
    mimicking the style of the standard directory browser.
    """
    args = request.args
    
    # Preserve the diff parameter if it exists
    diff_runid = args.get('diff', '')
    if '?' in diff_runid:
        diff_runid = diff_runid.split('?')[0]
    diff_arg = f'?diff={diff_runid}' if diff_runid else ''

    # Build breadcrumbs up to the point of failure
    base_browse_url = _prefix_path(f'/runs/{runid}/{config}/browse/')
    breadcrumbs = [f'<a href="{base_browse_url}{diff_arg}"><b>{runid}</b></a>']
    
    # Clean the subpath for display and split into components
    # This handles cases where a search pattern like "wepp/runs/p100.*" was used
    path_to_check = subpath.split('*')[0].strip('/')
    parts = [p for p in path_to_check.split('/') if p]

    # Create links for the parts of the path that do exist
    current_rel_path = ''
    for part in parts:
        # Check if the next segment of the path exists
        next_path_segment = os.path.join(wd, current_rel_path, part)
        if os.path.isdir(next_path_segment):
            current_rel_path = os.path.join(current_rel_path, part)
            part_url = f'{base_browse_url}{current_rel_path}/{diff_arg}'
            breadcrumbs.append(f'<a href="{part_url}"><b>{part}</b></a>')
        else:
            # This part and the rest of the path do not exist
            breadcrumbs.append(f'<b>{part}</b>')
            # Once we find a non-existent part, we stop creating links
            # and just show the rest of the requested path as bold text.
            remaining_index = parts.index(part) + 1
            if remaining_index < len(parts):
                breadcrumbs.extend([f'<b>{p}</b>' for p in parts[remaining_index:]])
            break

    breadcrumbs.append('<input type="text" id="pathInput" placeholder="../output/p1.*" size="50">')
    breadcrumbs_html = ' ❯ '.join(breadcrumbs)
    
    # Create the main content tree with the error message
    error_message = f"""
<div style="padding: 1em 0 0 2em;">
    <h3 style="color: #d9534f;">404 - Directory Not Found</h3>
    <p>The path '<b style="font-family: monospace;">{subpath}</b>' could not be found on the server.</p>
</div>"""
    
    home_href = _prefix_path(f'/runs/{runid}/{config}')
    project_href = Markup(f'<a href="{home_href}">☁️</a> ')

    page_html = _render_browse_error_page(
        runid=runid,
        config=config,
        diff_runid=diff_runid,
        breadcrumbs_html=breadcrumbs_html,
        project_href=project_href,
        error_message=error_message,
        page_title='Not Found',
    )

    return page_html, 404


async def browse_http_exception_handler(request: StarletteRequest, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, (dict, list)):
        response = JSONResponse(detail, status_code=exc.status_code)
    else:
        if detail is None:
            try:
                detail = HTTPStatus(exc.status_code).phrase
            except ValueError:
                detail = 'Error'
        response = PlainTextResponse(str(detail), status_code=exc.status_code)

    if exc.headers:
        response.headers.update(exc.headers)

    return response


def _format_exception_message(exc: BaseException) -> str:
    try:
        detail = str(exc)
    except Exception:
        detail = repr(exc)

    if detail and detail != exc.__class__.__name__:
        return f'{exc.__class__.__name__}: {detail}'
    return exc.__class__.__name__


def _log_exception_details(stacktrace_text: str, runid: str | None) -> None:
    timestamp = datetime.now()

    if runid:
        try:
            wd = os.path.abspath(get_wd(runid))
        except Exception:
            wd = None

        if wd and _exists(wd):
            try:
                with open(_join(wd, 'exceptions.log'), 'a', encoding='utf-8') as fp:
                    fp.write(f'[{timestamp}]\n')
                    fp.write(stacktrace_text)
                    fp.write('\n\n')
            except OSError:
                _logger.warning('Unable to append to run exception log for %s', runid, exc_info=True)

    try:
        with open('/var/log/exceptions.log', 'a', encoding='utf-8') as fp:
            fp.write(f'[{timestamp}] ')
            if runid:
                fp.write(f'{runid}\n')
            fp.write(stacktrace_text)
            fp.write('\n\n')
    except OSError:
        _logger.debug('Unable to append to /var/log/exceptions.log', exc_info=True)


async def browse_exception_handler(request: StarletteRequest, exc: Exception):
    stacktrace_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    stacktrace_text = ''.join(stacktrace_lines)
    stacktrace_display = stacktrace_text.strip('\n')

    runid = request.path_params.get('runid')
    config = request.path_params.get('config')
    diff_runid = request.query_params.get('diff', '')
    subpath = request.path_params.get('subpath') or ''

    _logger.exception('Unhandled exception for %s', request.url)
    _log_exception_details(stacktrace_text, runid)

    message = _format_exception_message(exc)
    escaped_message = html_escape(message)
    escaped_stacktrace = html_escape(stacktrace_display)

    breadcrumbs = []
    if runid and config:
        base_browse_url = _prefix_path(f'/runs/{runid}/{config}/browse/')
        diff_arg = f'?diff={diff_runid}' if diff_runid else ''
        breadcrumbs.append(f'<a href="{base_browse_url}{diff_arg}"><b>{html_escape(runid)}</b></a>')

        if subpath:
            for part in [p for p in subpath.split('/') if p]:
                breadcrumbs.append(f'<b>{html_escape(part)}</b>')
    else:
        breadcrumbs.append('<b>Browse</b>')

    breadcrumbs.append('<b>Error</b>')
    breadcrumbs.append('<input type="text" id="pathInput" placeholder="../output/p1.*" size="50">')
    breadcrumbs_html = ' ❯ '.join(breadcrumbs)

    if runid and config:
        home_href = _prefix_path(f'/runs/{runid}/{config}')
        project_href = Markup(f'<a href="{home_href}">☁️</a> ')
    else:
        project_href = Markup('')

    error_message = f"""
<div style="padding: 1em 0 0 2em;">
    <h3 style="color: #d9534f;">500 - Internal Server Error</h3>
    <p>{escaped_message}</p>
    <details open>
        <summary>Stack Trace</summary>
        <pre style="white-space: pre-wrap; font-family: monospace;">{escaped_stacktrace}</pre>
    </details>
</div>"""

    run_display = runid if runid else 'Browse'
    config_display = config if config else ''

    page_html = _render_browse_error_page(
        runid=run_display,
        config=config_display,
        diff_runid=diff_runid,
        breadcrumbs_html=breadcrumbs_html,
        project_href=project_href,
        error_message=error_message,
        page_title='Server Error',
    )

    return HTMLResponse(page_html, status_code=500)


async def _browse_tree_helper(runid, subpath, wd, request, config, filter_pattern_default=''):
    """
    Helper function to handle common browse tree logic.
    Returns the response for a file or directory browse request.
    """
    full_path = os.path.abspath(os.path.join(wd, subpath))
    
    if os.path.isfile(full_path):
        # If subpath points to a file, serve it
        return await browse_response(full_path, runid, wd, request, config)
    else:
        # Parse subpath for directory and filter
        if subpath.endswith('/'):
            filter_pattern = filter_pattern_default
            dir_path = subpath
        else:
            components = subpath.split('/')
            if '*' in components[-1]:
                filter_pattern = components[-1]
                dir_components = components[:-1]
            else:
                filter_pattern = filter_pattern_default
                dir_components = components

            dir_path = '/'.join(dir_components) if dir_components else '.'
            
        dir_path = os.path.abspath(os.path.join(wd, dir_path))
        
        # Security and existence checks
        if not dir_path.startswith(wd):
            abort(403)  # Prevent directory traversal
            
        if not os.path.isdir(dir_path):
            return _path_not_found_response(runid, subpath, wd, request, config)
            
        if not _validate_filter_pattern(filter_pattern):
            abort(400, f"Invalid filter pattern: {filter_pattern}")
            
        return await browse_response(dir_path, runid, wd, request, config, filter_pattern=filter_pattern)


async def get_entries(directory, filter_pattern, start, end, page_size):
    """Retrieve paginated directory entries using ls -l with ISO time style."""

    if filter_pattern:
        cmd = (
            f"ls -l --time-style=long-iso --group-directories-first {filter_pattern} "
            f"| sed '/^total /d' | sed -n '{start},{end}p'"
        )
    else:
        cmd = (
            f"ls -l --time-style=long-iso --group-directories-first "
            f"| sed '/^total /d' | sed -n '{start},{end}p'"
        )

    returncode, stdout, _ = await _run_shell_command(cmd, directory)
    if returncode != 0:
        return []

    entries = []
    dir_indices = []
    index = 0
    for line in stdout.splitlines():
        if line == '':
            break

        parts = line.split(maxsplit=7)
        if len(parts) < 8:
            continue

        flag = parts[0]
        is_dir = flag.startswith('d')
        is_symlink = flag.startswith('l')
        symlink_is_dir = False

        modified_time = f"{parts[5]} {parts[6]}"

        file_field = parts[7]
        if is_symlink and " -> " in file_field:
            name, _, sym_target = file_field.partition(" -> ")
            name = name.strip()
            sym_target = '->' + sym_target.strip()
        else:
            name = file_field
            sym_target = ""

        entry_path = _join(directory, name)
        if is_symlink:
            try:
                symlink_is_dir = os.path.isdir(entry_path)
            except OSError:
                symlink_is_dir = False
            if symlink_is_dir and sym_target.startswith('->') and not sym_target.endswith('/'):
                sym_target = sym_target + '/'

        if is_dir:
            hr_size = ""
            dir_indices.append((index, entry_path))
        else:
            try:
                size_bytes = int(parts[4])
            except ValueError:
                size_bytes = 0
            if size_bytes == 0:
                hr_size = "0 B"
            else:
                size_name = ("B", "KB", "MB", "GB", "TB")
                i = int(math.floor(math.log(size_bytes, 1024))) if size_bytes > 0 else 0
                p = math.pow(1024, i)
                s = round(size_bytes / p, 2)
                hr_size = f"{s} {size_name[i]}"

        entries.append((name, is_dir, modified_time, hr_size, is_symlink, sym_target, symlink_is_dir))
        index += 1

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
                'browse.get_entries() directory count took %.1f seconds; consider investigating system load.',
                elapsed,
            )

        for (entry_index, _), total_items in zip(dir_indices, totals):
            if isinstance(total_items, Exception):
                raise total_items
            entry = entries[entry_index]
            entries[entry_index] = (
                entry[0],
                entry[1],
                entry[2],
                f"{total_items} items",
                entry[4],
                entry[5],
                entry[6],
            )

    return entries


async def get_total_items(directory, filter_pattern=''):
    """Count total items in the directory, respecting the filter_pattern."""

    total_cmd = "ls | wc -l" if filter_pattern == '' else f"ls {filter_pattern} | wc -l"
    returncode, stdout, _ = await _run_shell_command(total_cmd, directory)
    if returncode != 0:
        return 0
    try:
        return int(stdout.strip())
    except (TypeError, ValueError):
        return 0


async def get_page_entries(wd, directory, page=1, page_size=MAX_FILE_LIMIT, filter_pattern=''):
    """List directory contents with pagination and optional filtering."""

    manifest_result = await asyncio.to_thread(
        _manifest_get_page_entries,
        wd,
        directory,
        filter_pattern,
        page,
        page_size,
    )
    if manifest_result is not None:
        entries, total_items = manifest_result
        return entries, total_items, True

    start = (page - 1) * page_size + 1
    end = page * page_size

    entries_task = asyncio.create_task(
        get_entries(directory, filter_pattern, start, end, page_size)
    )
    total_task = asyncio.create_task(
        get_total_items(directory, filter_pattern)
    )

    loop = asyncio.get_running_loop()
    start_time = loop.time()
    entries, total_items = await asyncio.gather(entries_task, total_task)
    elapsed = loop.time() - start_time
    if elapsed > 5:
        _logger.warning(
            'browse.get_page_entries() completed after %.1f seconds; large directories may impact responsiveness.',
            elapsed,
        )
    return entries, total_items, False


def get_pad(x):
    if x < 1: return ' '
    return x * ' '


async def html_dir_list(_dir, runid, wd, request_path, diff_runid, diff_wd, diff_arg, page=1, page_size=MAX_FILE_LIMIT, filter_pattern=''):
    _padding = ' '
    s = []
    
    page_entries, total_items, using_manifest = await get_page_entries(wd, _dir, page, page_size, filter_pattern)
    
    # Adjust column width based on current page entries
    n = max(36, max(len(entry[0]) for entry in page_entries) + 2) if page_entries else 36
    
    # strip wildcard from request path if it has a wild card as last item
    if filter_pattern:
        request_path = request_path.rsplit('/', 1)[0]
    
    # Generate HTML for the current page
    for i, entry in enumerate(page_entries):
        _file = entry[0]
        is_dir = entry[1]
        path = _join(_dir, _file)
        ts_pad = get_pad(n - len(_file))
        last_modified_time = entry[2]
        _tree_char = '├└'[i == len(page_entries) - 1]
        
        if is_dir:
            file_link = _join(request_path, _file)
            item_count = entry[3]
            sym_target = entry[5]
            item_pad = get_pad(8 - len(item_count.split()[0]))
            end_pad = ' ' * 32
            s.append(_padding + f'{_tree_char} <a href="{file_link}/{diff_arg}"><b>{_file}{ts_pad}</b></a>{last_modified_time} {item_pad}{item_count}{end_pad}{sym_target}  \n')
        else:
            file_link = _join(request_path, _file)
            is_symlink = entry[4]
            sym_target = entry[5]
            file_size = entry[3]
            item_pad = get_pad(8 - len(file_size.split()[0]))
            size_tokens = file_size.split()
            unit = size_tokens[1] if len(size_tokens) > 1 else ''
            dl_pad = get_pad(6 - len(unit))
            dl_link = '          '
            symlink_is_dir = entry[6] if len(entry) > 6 else False
            if not symlink_is_dir:
                dl_url = _join(request_path, _file).replace('/browse/', '/download/')
                dl_link = f'{dl_pad}<a href="{dl_url}">download</a>'
            file_lower = _file.lower()
            gl_link = '      '
            if file_lower.endswith(('.arc', '.tif', '.img', '.nc')):
                gl_url = _join(request_path, _file).replace('/browse/', '/gdalinfo/')
                gl_link = f'  <a href="{gl_url}">gdalinfo</a>'
            if file_lower.endswith('.parquet'):
                gl_url = _join(request_path, _file).replace('/browse/', '/download/') + '?as_csv=1'
                gl_link = f'  <a href="{gl_url}">.csv</a>'
            repr_link = '           '
            if file_lower.endswith('.man') or  file_lower.endswith('.sol'):
                repr_url = _join(request_path, _file) + '?repr=1'
                repr_link = f'  <a href="{repr_url}">annotated</a>'
            elif file_lower.endswith('.parquet') or file_lower.endswith('.csv') or file_lower.endswith('.tsv'):
                repr_url = _join(request_path, _file).replace('/browse/', '/pivottable/')
                repr_link = f'  <a href="{repr_url}">pivot</a>    '

            diff_link = '    '
            if diff_wd and not file_lower.endswith(('.tif', '.parquet', '.gz', '.img')):
                diff_path = _join(diff_wd, os.path.relpath(path, wd))
                if _exists(diff_path):
                    diff_url = _join(request_path, _file).replace('/browse/', '/diff/') + diff_arg
                    diff_link = f'  <a href="{diff_url}">diff</a>'
            s.append(_padding + f'{_tree_char} <a href="{file_link}">{_file}{ts_pad}</a>{last_modified_time} {item_pad}{file_size}{dl_link}{gl_link}{repr_link}{diff_link}{sym_target}\n')
        
        if i % 2:
            s[-1] = f'<span class="even-row">{s[-1]}</span>'
        else:
            s[-1] = f'<span class="odd-row">{s[-1]}</span>'
    
    return ''.join(s), total_items, using_manifest


async def browse_response(path, runid, wd, request, config, filter_pattern=''):
    args = request.args
    headers = request.headers
    
    diff_runid = args.get('diff', '')
    if '?' in diff_runid:
        diff_runid = diff_runid.split('?')[0]

    diff_wd = None
    diff_arg = ''
    if diff_runid:
        diff_wd = get_wd(diff_runid)
        diff_arg = f'?diff={diff_runid}'
    
    if not _exists(path):
        return jsonify({'Success': False, 'Error': 'path does not exist'})
    
    path_lower = path.lower()

    rel_path = os.path.relpath(path, wd)
    breadcrumbs = ''

    if os.path.isdir(path):
        # build breadcrumb links and clickable separators that expose absolute paths
        root_url = _prefix_path(f'/runs/{runid}/{config}/browse/')
        breadcrumb_items = [(f'<a href="{root_url}{diff_arg}"><b>{runid}</b></a>', os.path.abspath(wd))]

        if rel_path != '.':
            parts = rel_path.split('/')

            _rel_path = ''
            for idx, part in enumerate(parts):
                _rel_path = _join(_rel_path, part)
                abs_part_path = os.path.abspath(os.path.join(wd, _rel_path))
                is_last = idx == len(parts) - 1
                if is_last:
                    breadcrumb_html = f'<b>{part}</b>'
                else:
                    part_url = _prefix_path(f'/runs/{runid}/{config}/browse/{_rel_path}/')
                    breadcrumb_html = f'<a href="{part_url}{diff_arg}"><b>{part}</b></a>'
                breadcrumb_items.append((breadcrumb_html, abs_part_path))

        breadcrumb_segments: list[str] = []
        previous_abs_path = None
        for idx, (crumb_html, abs_path_str) in enumerate(breadcrumb_items):
            if idx and previous_abs_path is not None:
                escaped_abs_path = html_escape(previous_abs_path, quote=True)
                breadcrumb_segments.append(
                    f' <span class="breadcrumb-separator" data-copy-path="{escaped_abs_path}" title="Copy absolute path" role="button" tabindex="0">❯</span> '
                )
            breadcrumb_segments.append(crumb_html)
            previous_abs_path = abs_path_str

        current_abs_path = previous_abs_path or os.path.abspath(path)
        breadcrumb_segments.append(
            f' <span class="breadcrumb-separator" data-copy-path="{html_escape(current_abs_path, quote=True)}" title="Copy absolute path" role="button" tabindex="0">❯</span> '
        )

        breadcrumb_segments.append(
            f'<input type="text" id="pathInput" value="{filter_pattern}" placeholder="../output/p1.*" size="50">'
        )
        breadcrumbs = ''.join(breadcrumb_segments)

        # Get page and filter from query parameters
        page = request.args.get('page', 1, type=int)
        
        # Generate directory listing and get total items
        listing_html, total_items, using_manifest = await html_dir_list(
            path, runid, wd, request.path, diff_runid, diff_wd, diff_arg,
            page=page, page_size=MAX_FILE_LIMIT, filter_pattern=filter_pattern
        )
        
        # Calculate total pages and validate page number
        total_pages = math.ceil(total_items / MAX_FILE_LIMIT) if total_items > 0 else 1
        if page > total_pages:
            query = {k: v for k, v in request.args.items() if k != 'page'}
            query['page'] = total_pages
            return redirect(request.path + '?' + urlencode(query))
        elif page < 1:
            query = {k: v for k, v in request.args.items() if k != 'page'}
            query['page'] = 1
            return redirect(request.path + '?' + urlencode(query))
        
        # Determine pagination links
        if total_pages <= 10:
            pages_to_show = list(range(1, total_pages + 1))
        else:
            pages = [1]
            for i in range(11, total_pages + 1, 10):  # Every 10th page
                if i <= total_pages:
                    pages.append(i)
            window = 3  # Show 3 pages before and after current
            for i in range(max(1, page - window), min(total_pages + 1, page + window + 1)):
                if i not in pages:
                    pages.append(i)
            if total_pages not in pages:
                pages.append(total_pages)
            pages_to_show = sorted(pages)
        
        # Insert ellipses for gaps
        display_pages = []
        for i in range(len(pages_to_show) - 1):
            display_pages.append(pages_to_show[i])
        display_pages.append(pages_to_show[-1])
        
        # Generate pagination HTML
        base_query = {k: v for k, v in request.args.items() if k != 'page'}
        pagination_html = '<div>'
        for item in display_pages:
            starting_item = 1 + (item - 1) * MAX_FILE_LIMIT
            if item == page:
                pagination_html += f'<b>[{starting_item}]</b> '
            else:
                query = {**base_query, 'page': item}
                href = "?" + urlencode(query)
                pagination_html += f'<a href="{href}">[{starting_item}]</a> '
        pagination_html += '</div>'
        
        # Calculate showing range
        start = (page - 1) * MAX_FILE_LIMIT
        showing_start = start + 1 if total_items > 0 else 0
        showing_end = min(start + MAX_FILE_LIMIT, total_items)
        manifest_note = ' (manifest cached)' if using_manifest else ''
        if total_items > 0:
            showing_text = f'<p>Showing items {showing_start} to {showing_end} of {total_items}{manifest_note}</p>'
        else:
            showing_text = f'<p>No items to display{manifest_note}</p>'
        
        # Combine UI elements
        home_href = _prefix_path(f'/runs/{runid}/{config}')
        project_href = Markup(f'<a href="{home_href}">☁️</a> ')
        breadcrumbs_markup = Markup(breadcrumbs)
        listing_markup = Markup(listing_html)
        pagination_markup = Markup(pagination_html)
        showing_markup = Markup(showing_text)

        return render_template(
            'browse/directory.htm',
            runid=runid,
            config=config,
            diff_runid=diff_runid,
            project_href=project_href,
            breadcrumbs_html=breadcrumbs_markup,
            listing_html=listing_markup,
            pagination_html=pagination_markup,
            showing_text=showing_markup,
            using_manifest=using_manifest,
        )

    else:
        repr_mode = args.get('repr') is not None
        contents = None

        if repr_mode:
            contents = _generate_repr_content(path)
            if contents is None:
                abort(404)

        if contents is None:
            if path_lower.endswith('.gz'):
                contents = await _async_read_gzip(path)
                path_lower = path_lower[:-3]
            else:
                try:
                    contents = await _async_read_text(path)
                except UnicodeDecodeError:
                    contents = None

        if 'raw' in args or 'Raw' in headers:
            if contents is not None:
                r = Response(response=contents, status=200, mimetype="text/plain")
                r.headers["Content-Type"] = "text/plain; charset=utf-8"
                return r

        if 'download' in args or 'Download' in headers:
            return send_file(path, as_attachment=True, download_name=_split(path)[-1])

        if path_lower.endswith('.json') or path_lower.endswith('.nodb') or path_lower.endswith('.dump'):
            assert contents is not None
            jsobj = json.loads(contents)
            return jsonify(jsobj)

        if path_lower.endswith('.xml'):
            assert contents is not None
            r = Response(response=contents, status=200, mimetype="text/xml")
            r.headers["Content-Type"] = "text/xml; charset=utf-8"
            return r

        if path_lower.endswith('.arc'):
            assert contents is not None
            return render_template(
                'browse/arc_file.htm',
                filename=basename(path),
                runid=runid,
                contents=contents,
            )

        markdown_markup = None
        if path_lower.endswith(MARKDOWN_EXTENSIONS):
            if contents is None:
                try:
                    contents = await _async_read_text(path)
                except UnicodeDecodeError:
                    contents = None
            if contents is not None:
                try:
                    rendered_markdown = markdown_to_html(contents)
                except Exception:
                    _logger.exception('Failed to render Markdown file at %s', path)
                else:
                    markdown_markup = Markup(rendered_markdown)
            if markdown_markup is not None:
                return render_template(
                    'browse/markdown_file.htm',
                    runid=runid,
                    path=path,
                    filename=basename(path),
                    markdown_html=markdown_markup,
                )

        html = None
        if path_lower.endswith('.pkl'):
            df = await asyncio.to_thread(pd.read_pickle, path)
            html = await _async_df_to_html(df)

        if path_lower.endswith('.parquet'):
            df = await asyncio.to_thread(pd.read_parquet, path)
            html = await _async_df_to_html(df)

        if path_lower.endswith('.csv'):
            skiprows = 0
            if 'totalwatsed2' in path_lower:
                skiprows = 1
            df = await asyncio.to_thread(pd.read_csv, path, skiprows=skiprows)
            html = await _async_df_to_html(df)
            #html = csv_to_html(path)

        if path_lower.endswith('.tsv'):
            skiprows = 0
            try:
                df = await asyncio.to_thread(pd.read_table, path, sep='\t', skiprows=skiprows)
            except Exception:
                _logger.warning('Unable to parse TSV at %s; falling back to plain text view', path, exc_info=True)
            else:
                html = await _async_df_to_html(df)

        if html is not None:
            table_markup = Markup(html)
            return render_template(
                'browse/data_table.htm',
                filename=basename(path),
                runid=runid,
                table_html=table_markup,
            )

        if contents is None:
            try:
                contents = await _async_read_text(path)
            except UnicodeDecodeError:
                return send_file(path, as_attachment=True, download_name=_split(path)[-1])

        contents_html = _wrap_usersum_spans(contents)

        return render_template(
            'browse/text_file.htm',
            runid=runid,
            path=path,
            filename=basename(path),
            contents=contents,
            contents_html=contents_html,
        )


async def _handle_browse_request(request: StarletteRequest, runid: str, config: str, subpath: str):
    wd = os.path.abspath(get_wd(runid))
    flask_request = FlaskRequestAdapter(request)
    result = await _browse_tree_helper(runid, subpath or '', wd, flask_request, config)
    return ensure_response(result)


async def browse_root(request: StarletteRequest):
    runid = request.path_params['runid']
    config = request.path_params['config']
    return await _handle_browse_request(request, runid, config, '')


async def browse_subpath(request: StarletteRequest):
    runid = request.path_params['runid']
    config = request.path_params['config']
    subpath = request.path_params.get('subpath', '')
    return await _handle_browse_request(request, runid, config, subpath)


def health(_: StarletteRequest):
    return PlainTextResponse('OK')


def create_app():
    routes = [
        Route(
            '/health',
            health,
            methods=['GET']
        ),
        Route(
            '/weppcloud/runs/{runid}/{config}/browse/',
            browse_root,
            methods=['GET']
        ),
        Route(
            '/weppcloud/runs/{runid}/{config}/browse',
            browse_root,
            methods=['GET']
        ),
        Route(
            '/weppcloud/runs/{runid}/{config}/browse/{subpath:path}',
            browse_subpath,
            methods=['GET']
        ),
    ]

    routes.extend(create_download_routes(_prefix_path))
    routes.extend(create_gdalinfo_routes(_prefix_path))

    exception_handlers = {
        HTTPException: browse_http_exception_handler,
        Exception: browse_exception_handler,
    }

    return Starlette(routes=routes, exception_handlers=exception_handlers)


app = create_app()

__all__ = ['create_app', 'app', 'create_manifest', 'remove_manifest', 'MANIFEST_FILENAME']


if __name__ == '__main__':
    import uvicorn

    port = int(os.getenv('PORT', '9009'))
    uvicorn.run(app, host=os.getenv('HOST', '0.0.0.0'), port=port)
