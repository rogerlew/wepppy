
"""
Browse Microservice
===================

This module houses the Starlette microservice that powers the web-based file explorer used in WEPP Cloud.  The service
retains the original browse blueprint behavior with minimal changes so the underlying view logic remains untouched.

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
- `/culverts/{uuid}/browse/`
- `/culverts/{uuid}/browse/{subpath:path}`
- `/batch/{batch_name}/browse/`
- `/batch/{batch_name}/browse/{subpath:path}`

Key Behaviors
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

from urllib.parse import urlencode
from urllib.parse import quote

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
from wepppy.microservices.browse._download import create_routes as create_download_routes
from wepppy.microservices.browse.dtale import (
    DTALE_SUPPORTED_SUFFIXES,
    build_handlers as build_dtale_handlers,
    resolve_dtale_base as _resolve_dtale_base,
)
from wepppy.microservices.browse.files_api import (
    FilesApiDependencies,
    accepts_json as _accepts_json,
    build_error_payload as _build_error_payload,
    build_files_handlers,
)
from wepppy.microservices.browse.listing import (
    MANIFEST_FILENAME,
    MAX_FILE_LIMIT,
    _manifest_path,
    _normalize_rel_path,
    _rel_join,
    _rel_parent,
    create_manifest,
    get_page_entries,
    get_total_items,
    html_dir_list,
    remove_manifest,
)
from wepppy.microservices.browse.security import (
    is_restricted_recorder_path,
    path_security_detail,
    validate_raw_subpath,
    validate_resolved_target,
)
from wepppy.microservices._gdalinfo import create_routes as create_gdalinfo_routes
from wepppy.microservices.dss_preview import build_preview as build_dss_preview

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
WEPPPY_DIR = BASE_DIR.parent.parent
WEPP_CLOUD_DIR = (WEPPPY_DIR / 'weppcloud').resolve()
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


def _resolve_browse_paths(request_path: str, runid: str, config: str) -> tuple[str, str]:
    browse_marker = '/browse'
    if browse_marker in request_path:
        base = request_path.split(browse_marker)[0]
        browse_base = f'{base}/browse/'
        if '/culverts/' in base or '/batch/' in base:
            return browse_base, browse_base
        return browse_base, base
    browse_base = _prefix_path(f'/runs/{runid}/{config}/browse/')
    home_href = _prefix_path(f'/runs/{runid}/{config}')
    return browse_base, home_href

def _resolve_culvert_batch_root(batch_uuid: str) -> Path:
    culverts_root = Path(os.getenv('CULVERTS_ROOT', '/wc1/culverts')).resolve()
    return _resolve_root_child(culverts_root, batch_uuid, "culvert batch")


def _resolve_batch_root(batch_name: str) -> Path:
    batch_root = Path(os.getenv('BATCH_RUNNER_ROOT', '/wc1/batch')).resolve()
    return _resolve_root_child(batch_root, batch_name, "batch")


def _resolve_root_child(root: Path, value: str, label: str) -> Path:
    if not value or value in (".", ".."):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Invalid {label} identifier.",
        )
    value_path = Path(value)
    if len(value_path.parts) != 1 or value_path.name != value:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Invalid {label} identifier.",
        )
    root_path = Path(os.path.abspath(str(root)))
    candidate = Path(os.path.abspath(str(root_path / value)))
    try:
        common = os.path.commonpath([str(root_path), str(candidate)])
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Path traversal detected.",
        ) from exc
    if common != str(root_path):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Path traversal detected.",
        )
    return candidate


def _assert_within_root(root: str | Path, target: str | Path) -> None:
    try:
        common = os.path.commonpath(
            [os.path.abspath(str(root)), os.path.abspath(str(target))]
        )
    except ValueError:
        abort(403)
    if common != os.path.abspath(str(root)):
        abort(403)


def _assert_target_within_allowed_roots(root: str | Path, target: str | Path) -> None:
    violation = validate_resolved_target(root, target)
    if violation is not None:
        abort(403, path_security_detail(violation))


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

# Mirror Flask's versioned static helper for templates that expect it.
_ASSET_VERSION = os.getenv('ASSET_VERSION', '').strip()


def static_url(filename: str) -> str:
    path = url_for('static', filename=filename)
    if _ASSET_VERSION:
        delimiter = '&' if '?' in path else '?'
        return f'{path}{delimiter}v={_ASSET_VERSION}'
    return path


templates_env.globals['static_url'] = static_url
templates_env.globals['asset_version'] = _ASSET_VERSION


def render_template(template_name, **context):
    context.setdefault('site_prefix', SITE_PREFIX)
    template = templates_env.get_template(template_name)
    return template.render(**context)


async def _run_shell_command(command: str, cwd: str) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault('LC_ALL', 'C')
    env.setdefault('LANG', 'C')
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
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

_FILES_PREVIEW_EXTENSIONS = (
    MARKDOWN_EXTENSIONS
    + DTALE_SUPPORTED_SUFFIXES
    + (
        '.arc',
        '.csv',
        '.dss',
        '.dump',
        '.json',
        '.log',
        '.man',
        '.md',
        '.markdown',
        '.mdown',
        '.mkdn',
        '.nodb',
        '.out',
        '.pkl',
        '.pickle',
        '.sol',
        '.tsv',
        '.txt',
        '.xml',
    )
)


def _preview_available(path: str) -> bool:
    lower_path = path.lower()
    return lower_path.endswith(_FILES_PREVIEW_EXTENSIONS)


_logger = logging.getLogger(__name__)


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
    if not pattern:  # Empty pattern is valid
        return True
    if '\x00' in pattern:
        return False
    if '/' in pattern or '\\' in pattern:
        return False
    return True


_SORT_FIELDS = {'name', 'date', 'size'}
_SORT_ORDERS = {'asc', 'desc'}


def _normalize_sort_params(args) -> tuple[str, str]:
    sort_by = (args.get('sort', '') or '').lower()
    if sort_by not in _SORT_FIELDS:
        sort_by = 'name'

    sort_order = (args.get('order', '') or '').lower()
    if sort_order not in _SORT_ORDERS:
        # Defaults: name ascending; date/size default to descending (newest/largest first)
        sort_order = 'desc' if sort_by in ('date', 'size') else 'asc'

    return sort_by, sort_order


def _is_files_request(request: StarletteRequest) -> bool:
    path_parts = [part for part in (request.url.path or '').split('/') if part]
    try:
        runs_index = path_parts.index('runs')
    except ValueError:
        return False
    files_index = runs_index + 3
    if files_index >= len(path_parts):
        return False
    if path_parts[files_index] != 'files':
        return False
    return True


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
    base_browse_url, home_href = _resolve_browse_paths(request.path, runid, config)
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
        if _is_files_request(request):
            response = JSONResponse(
                _build_error_payload(str(detail), details=str(detail)),
                status_code=exc.status_code,
            )
        else:
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

    if _is_files_request(request):
        return JSONResponse(
            _build_error_payload(
                'Internal server error',
                code='internal_error',
                details=stacktrace_display,
            ),
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

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
    _assert_within_root(wd, full_path)
    _assert_target_within_allowed_roots(wd, full_path)

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
        _assert_within_root(wd, dir_path)
        _assert_target_within_allowed_roots(wd, dir_path)
            
        if not os.path.isdir(dir_path):
            return _path_not_found_response(runid, subpath, wd, request, config)
            
        if not _validate_filter_pattern(filter_pattern):
            abort(400, f"Invalid filter pattern: {filter_pattern}")
            
        return await browse_response(dir_path, runid, wd, request, config, filter_pattern=filter_pattern)


async def browse_response(path, runid, wd, request, config, filter_pattern=''):
    args = request.args
    headers = request.headers
    
    diff_runid = args.get('diff', '')
    if '?' in diff_runid:
        diff_runid = diff_runid.split('?')[0]

    sort_by, sort_order = _normalize_sort_params(args)

    diff_wd = None
    base_query: dict[str, str] = {}
    if diff_runid:
        diff_wd = get_wd(diff_runid)
        base_query['diff'] = diff_runid

    include_sort_params = ('sort' in args) or ('order' in args) or sort_by != 'name' or sort_order != 'asc'
    if include_sort_params:
        base_query['sort'] = sort_by
        base_query['order'] = sort_order

    query_suffix = f'?{urlencode(base_query)}' if base_query else ''
    
    if not _exists(path):
        return jsonify({'error': {'message': 'path does not exist'}}), 404
    
    path_lower = path.lower()

    rel_path = os.path.relpath(path, wd)
    breadcrumbs = ''

    base_browse_url, home_href = _resolve_browse_paths(request.path, runid, config)

    if os.path.isdir(path):
        # build breadcrumb links and clickable separators that expose absolute paths
        root_href = f'{base_browse_url}{query_suffix}'
        breadcrumb_items = [(f'<a href="{root_href}"><b>{runid}</b></a>', os.path.abspath(wd))]

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
                    part_href = f'{base_browse_url}{_rel_path}/{query_suffix}'
                    breadcrumb_html = f'<a href="{part_href}"><b>{part}</b></a>'
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
            f'<input type="text" id="pathInput" value="{html_escape(filter_pattern, quote=True)}" '
            'placeholder="../output/p1.*" size="50">'
        )
        breadcrumbs = ''.join(breadcrumb_segments)

        # Get page and filter from query parameters
        page = request.args.get('page', 1, type=int)
        
        # Generate directory listing and get total items
        listing_html, total_items, using_manifest = await html_dir_list(
            path, runid, wd, request.path, diff_wd, base_query,
            page=page, page_size=MAX_FILE_LIMIT, filter_pattern=filter_pattern,
            sort_by=sort_by, sort_order=sort_order,
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
        wants_binary = (
            repr_mode
            or ('raw' in args)
            or ('Raw' in headers)
            or ('download' in args)
            or ('Download' in headers)
        )

        if path_lower.endswith('.dss') and not wants_binary:
            dss_response = await _maybe_render_dss_preview(path, runid, config)
            if dss_response is not None:
                return dss_response

        contents = None
        preview_warning = None

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
            try:
                df = await asyncio.to_thread(pd.read_csv, path, skiprows=skiprows)
            except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
                preview_warning = (
                    f'CSV preview failed: {_format_exception_message(exc)}. '
                    'Showing raw text instead.'
                )
                _logger.warning(
                    'Unable to parse CSV at %s; falling back to text view',
                    path,
                    exc_info=True,
                )
            else:
                html = await _async_df_to_html(df)
            #html = csv_to_html(path)

        if path_lower.endswith('.tsv'):
            skiprows = 0
            try:
                df = await asyncio.to_thread(pd.read_table, path, sep='\t', skiprows=skiprows)
            except Exception as exc:
                preview_warning = (
                    f'TSV preview failed: {_format_exception_message(exc)}. '
                    'Showing raw text instead.'
                )
                _logger.warning(
                    'Unable to parse TSV at %s; falling back to text view',
                    path,
                    exc_info=True,
                )
            else:
                html = await _async_df_to_html(df)

        if html is not None:
            table_markup = Markup(html)
            rel_url = os.path.relpath(path, wd).replace('\\', '/')
            dtale_base = _resolve_dtale_base(request.path, runid, config, _prefix_path)
            dtale_url = f"{dtale_base}{quote(rel_url, safe='/')}"
            return render_template(
                'browse/data_table.htm',
                filename=basename(path),
                runid=runid,
                table_html=table_markup,
                dtale_url=dtale_url,
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
            preview_warning=preview_warning,
        )


async def _maybe_render_dss_preview(path: str, runid: str, config: str):
    download_href = '?download'
    filename = basename(path)
    try:
        preview = await asyncio.to_thread(build_dss_preview, path)
    except ModuleNotFoundError:
        message = (
            "Install pydsstools inside the WEPP environment to enable DSS previews "
            "(pip install pydsstools)."
        )
        return render_template(
            'browse/dss_file.htm',
            runid=runid,
            config=config,
            filename=filename,
            preview=None,
            error_message=message,
            download_href=download_href,
        )
    except FileNotFoundError:
        raise
    except Exception:
        _logger.exception('Unable to summarize DSS file at %s', path)
        message = "Unable to summarize this DSS file. Use Download to inspect it manually."
        return render_template(
            'browse/dss_file.htm',
            runid=runid,
            config=config,
            filename=filename,
            preview=None,
            error_message=message,
            download_href=download_href,
        )

    return render_template(
        'browse/dss_file.htm',
        runid=runid,
        config=config,
        filename=filename,
        preview=preview,
        error_message=None,
        download_href=download_href,
    )


_FILES_API_DEPENDENCIES = FilesApiDependencies(
    get_wd=lambda runid: get_wd(runid),
    is_restricted_recorder_path=is_restricted_recorder_path,
    manifest_path=_manifest_path,
    normalize_rel_path=_normalize_rel_path,
    rel_join=_rel_join,
    rel_parent=_rel_parent,
    prefix_path=_prefix_path,
    preview_available=_preview_available,
    validate_filter_pattern=_validate_filter_pattern,
    get_page_entries=get_page_entries,
    get_total_items=get_total_items,
)
files_root, files_subpath = build_files_handlers(_FILES_API_DEPENDENCIES)


async def _handle_browse_request(
    request: StarletteRequest,
    runid: str,
    config: str,
    subpath: str,
    *,
    wd_override: str | Path | None = None,
):
    subpath_value = subpath or ''
    violation = validate_raw_subpath(subpath_value)
    if violation is not None:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail=path_security_detail(violation),
        )

    wd = os.path.abspath(str(wd_override)) if wd_override is not None else os.path.abspath(get_wd(runid))
    flask_request = FlaskRequestAdapter(request)
    result = await _browse_tree_helper(runid, subpath_value, wd, flask_request, config)
    return ensure_response(result)


async def browse_culvert_root(request: StarletteRequest):
    batch_uuid = request.path_params['uuid']
    batch_root = _resolve_culvert_batch_root(batch_uuid)
    return await _handle_browse_request(
        request,
        runid=batch_uuid,
        config='culvert-batch',
        subpath='',
        wd_override=batch_root,
    )


async def browse_culvert_subpath(request: StarletteRequest):
    batch_uuid = request.path_params['uuid']
    subpath = request.path_params.get('subpath', '')
    batch_root = _resolve_culvert_batch_root(batch_uuid)
    return await _handle_browse_request(
        request,
        runid=batch_uuid,
        config='culvert-batch',
        subpath=subpath,
        wd_override=batch_root,
    )


async def browse_batch_root(request: StarletteRequest):
    batch_name = request.path_params['batch_name']
    batch_root = _resolve_batch_root(batch_name)
    return await _handle_browse_request(
        request,
        runid=batch_name,
        config='batch',
        subpath='',
        wd_override=batch_root,
    )


async def browse_batch_subpath(request: StarletteRequest):
    batch_name = request.path_params['batch_name']
    subpath = request.path_params.get('subpath', '')
    batch_root = _resolve_batch_root(batch_name)
    return await _handle_browse_request(
        request,
        runid=batch_name,
        config='batch',
        subpath=subpath,
        wd_override=batch_root,
    )


dtale_open, dtale_culvert_open, dtale_batch_open = build_dtale_handlers(
    get_wd=lambda runid: get_wd(runid),
    assert_within_root=_assert_within_root,
    resolve_culvert_batch_root=lambda batch_uuid: _resolve_culvert_batch_root(batch_uuid),
    resolve_batch_root=lambda batch_name: _resolve_batch_root(batch_name),
    logger=_logger,
)


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
            '/weppcloud/runs/{runid}/{config}/files/',
            files_root,
            methods=['GET']
        ),
        Route(
            '/weppcloud/runs/{runid}/{config}/files',
            files_root,
            methods=['GET']
        ),
        Route(
            '/weppcloud/runs/{runid}/{config}/files/{subpath:path}',
            files_subpath,
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
        Route(
            '/weppcloud/culverts/{uuid}/browse/',
            browse_culvert_root,
            methods=['GET']
        ),
        Route(
            '/weppcloud/culverts/{uuid}/browse',
            browse_culvert_root,
            methods=['GET']
        ),
        Route(
            '/weppcloud/culverts/{uuid}/browse/{subpath:path}',
            browse_culvert_subpath,
            methods=['GET']
        ),
        Route(
            '/weppcloud/batch/{batch_name}/browse/',
            browse_batch_root,
            methods=['GET']
        ),
        Route(
            '/weppcloud/batch/{batch_name}/browse',
            browse_batch_root,
            methods=['GET']
        ),
        Route(
            '/weppcloud/batch/{batch_name}/browse/{subpath:path}',
            browse_batch_subpath,
            methods=['GET']
        ),
        Route(
            '/weppcloud/runs/{runid}/{config}/dtale/{subpath:path}',
            dtale_open,
            methods=['GET']
        ),
        Route(
            '/weppcloud/culverts/{uuid}/dtale/{subpath:path}',
            dtale_culvert_open,
            methods=['GET']
        ),
        Route(
            '/weppcloud/batch/{batch_name}/dtale/{subpath:path}',
            dtale_batch_open,
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
