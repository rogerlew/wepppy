import os
import subprocess
import re
import math
import json
import logging
import html

from urllib.parse import urlencode

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from os.path import abspath, basename

import gzip
import pandas as pd

from flask import (
    Blueprint,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
)
from markupsafe import Markup

from wepppy.weppcloud.utils.helpers import get_wd, error_factory
from functools import lru_cache

from wepppy.weppcloud.routes.usersum.usersum import _load_parameter_catalog

"""
Browse Blueprint
================

This module hosts the `browse` Flask blueprint that serves the web-based file explorer used in WEPP Cloud.  The
blueprint is exposed via `weppcloud.routes.browse.__init__` and registered against the application elsewhere.

Template Organization
---------------------
All rendering is handled by Jinja templates bundled with the blueprint under
`wepppy/weppcloud/routes/browse/templates/browse/`:

- `directory.j2` - top-level directory listing view with pagination, diff controls, and the keyboard command bar.
- `not_found.j2` - 404-style response shown when a requested directory segment is missing.
- `_path_input_script.j2` - shared script that wires up the inline path input field for directory and 404 pages.
- `arc_file.j2` - minimal viewer for “.arc” outputs.
- `data_table.j2` - table presentation for CSV/TSV/Parquet/Pickle content rendered via pandas.
- `text_file.j2` - general text viewer (including the command bar) for other readable file types.

Routes
------
- `/runs/<string:runid>/<config>/report/<string:wepp>/browse/`
- `/runs/<string:runid>/<config>/report/<string:wepp>/browse/<path:subpath>`
- `/runs/<string:runid>/<config>/browse/`
- `/runs/<string:runid>/<config>/browse/<path:subpath>`

Key Behaviors
-------------
- **Directory Browsing** – `browse_response` delegates to `html_dir_list` to build directory listings with pagination
  and optional shell-style filtering, then renders `directory.j2`.
- **File Viewing** – Depending on the requested file type, responses are streamed directly, downloaded, or rendered via
  `arc_file.j2`, `data_table.j2`, or `text_file.j2`.
- **Diff Support** – When the `diff` query argument is present the blueprint attempts to locate the requested object in
  the comparison run and surfaces diff links in directory listings.
- **Security** – `_browse_tree_helper` prevents directory traversal, validates filter syntax, and ensures the
  requested path stays inside the working directory returned by `get_wd`.
- **Performance** – Directory counts and listings are gathered concurrently using `ThreadPoolExecutor` to keep large
  listings responsive.

For maintenance purposes, adjust template markup within the dedicated `templates/browse/` files; Python logic in this
module should remain focused on routing, filesystem queries, and response orchestration.
"""

MAX_FILE_LIMIT = 100

browse_bp = Blueprint('browse', __name__, template_folder='templates')

_logger = logging.getLogger(__name__)


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
        return None

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
    base_browse_url = f'/weppcloud/runs/{runid}/{config}/browse/'
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
    
    project_href = Markup(f'<a href="/weppcloud/runs/{runid}/{config}">☁️</a> ')

    return (
        render_template(
            'browse/not_found.j2',
            runid=runid,
            config=config,
            diff_runid=diff_runid,
            breadcrumbs_html=Markup(breadcrumbs_html),
            project_href=project_href,
            error_message=Markup(error_message),
        ),
        404,
    )

    
def _browse_tree_helper(runid, subpath, wd, request, config, filter_pattern_default=''):
    """
    Helper function to handle common browse tree logic.
    Returns the response for a file or directory browse request.
    """
    full_path = os.path.abspath(os.path.join(wd, subpath))
    
    if os.path.isfile(full_path):
        # If subpath points to a file, serve it
        return browse_response(full_path, runid, wd, request, config)
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
            
        return browse_response(dir_path, runid, wd, request, config, filter_pattern=filter_pattern)


@browse_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/browse/', defaults={'subpath': ''}, strict_slashes=False)
@browse_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/browse/<path:subpath>', strict_slashes=False)
def wp_browse_tree(runid, config, wepp, subpath):
    wd = os.path.abspath(get_wd(runid))  # Assume get_wd retrieves the working directory
    return _browse_tree_helper(runid, subpath, wd, request, config)

@browse_bp.route('/runs/<string:runid>/<config>/browse/', defaults={'subpath': ''}, strict_slashes=False)
@browse_bp.route('/runs/<string:runid>/<config>/browse/<path:subpath>', strict_slashes=False)
def browse_tree(runid, config, subpath):
    wd = os.path.abspath(get_wd(runid))  # Assume get_wd retrieves the working directory
    return _browse_tree_helper(runid, subpath, wd, request, config)


def get_entries(directory, filter_pattern, start, end, page_size):
    """
    Retrieve paginated directory entries using ls -l with ISO time style.
    """
 
    # Construct the ls command with --time-style=long-iso
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
    
    # Execute the command
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
        cwd=directory
    )
    
    # Handle command failure
    if result.returncode != 0:
        # This can happen if the directory is empty and the filter matches nothing, which is not an error.
        # Or if ls fails for another reason. Returning [] is safe.
        return []
    
    entries = []
    dir_indices = []
    index = 0
    for line in result.stdout.splitlines():
        if line == '':
            break
        
        parts = line.split(maxsplit=7)
        if len(parts) < 8:
            continue
        
        flag = parts[0]
        is_dir = flag.startswith('d')
        is_symlink = flag.startswith('l')
        
        modified_time = f"{parts[5]} {parts[6]}"
        
        file_field = parts[7]
        if is_symlink and " -> " in file_field:
            name, _, sym_target = file_field.partition(" -> ")
            name = name.strip()
            sym_target = '->' + sym_target.strip()
        else:
            name = file_field
            sym_target = ""
        
        if is_dir:
            hr_size = ""
            dir_indices.append((index, _join(directory, name)))
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
        
        entries.append((name, is_dir, modified_time, hr_size, is_symlink, sym_target))
        index += 1
    
    if dir_indices:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(get_total_items, dir_path): i for i, dir_path in dir_indices}

            pending = set(futures.keys())
            while pending:
                done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)

                if not done:
                    # Directory counts should be quick; repeated warnings imply system load.
                    _logger.warning('browse.get_entries() directory count still pending after 5 seconds; continuing to wait.')
                    continue

                for future in done:
                    index = futures[future]
                    try:
                        total_items = future.result()
                    except Exception:
                        for remaining in pending:
                            remaining.cancel()
                        raise

                    entry = entries[index]
                    entries[index] = (entry[0], entry[1], entry[2], f"{total_items} items", entry[4], entry[5])
                
    return entries


def get_total_items(directory, filter_pattern=''):
    """
    Count total items in the directory, respecting the filter_pattern.
    """

    if filter_pattern == '':
        total_cmd = "ls | wc -l"
    else:
        total_cmd = f"ls {filter_pattern} | wc -l"
    
    total_result = subprocess.run(
        total_cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=directory
    )

    return int(total_result.stdout.strip()) if total_result.returncode == 0 else 0


def get_page_entries(directory, page=1, page_size=MAX_FILE_LIMIT, filter_pattern=''):
    """
    List directory contents with pagination and optional filtering, using concurrent subprocess calls.
    
    Args:
        directory (str): Directory path to list.
        page (int): Page number (1-based).
        page_size (int): Number of entries per page.
        filter_pattern (str): Sanitized shell glob pattern (e.g., '*.txt').
    
    Returns:
        tuple: (list of entries, total item count)
    """
    start = (page - 1) * page_size + 1
    end = page * page_size
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(get_entries, directory, filter_pattern, start, end, page_size): 'entries',
            executor.submit(get_total_items, directory, filter_pattern): 'total_items'
        }

        results = {}
        pending = set(futures.keys())
        while pending:
            done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)

            if not done:
                _logger.warning('browse.get_page_entries() still waiting on subprocesses after 5 seconds; continuing to wait.')
                continue

            for future in done:
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception:
                    for remaining in pending:
                        remaining.cancel()
                    raise

    return results['entries'], results['total_items']


def get_pad(x):
    if x < 1: return ' '
    return x * ' '


def html_dir_list(_dir, runid, wd, request_path, diff_runid, diff_wd, diff_arg, page=1, page_size=MAX_FILE_LIMIT, filter_pattern=''):
    _padding = ' '
    s = []
    
    page_entries, total_items = get_page_entries(_dir, page, page_size, filter_pattern)
    
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
            file_link = '/weppcloud' + _join(request_path, _file)
            item_count = entry[3]
            sym_target = entry[5]
            item_pad = get_pad(8 - len(item_count.split()[0]))
            end_pad = ' ' * 32
            s.append(_padding + f'{_tree_char} <a href="{file_link}/{diff_arg}"><b>{_file}{ts_pad}</b></a>{last_modified_time} {item_pad}{item_count}{end_pad}{sym_target}  \n')
        else:
            file_link = '/weppcloud' + _join(request_path, _file)
            is_symlink = entry[4]
            sym_target = entry[5]
            file_size = entry[3]
            item_pad = get_pad(8 - len(file_size.split()[0]))
            dl_pad = get_pad(6 - len(file_size.split()[1]))
            dl_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/download/')
            dl_link = f'{dl_pad}<a href="{dl_url}">download</a>'
            file_lower = _file.lower()
            gl_link = '          '
            if file_lower.endswith(('.arc', '.tif', '.img', '.nc')):
                gl_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/gdalinfo/')
                gl_link = f'  <a href="{gl_url}">gdalinfo</a>'
            if file_lower.endswith('.parquet'):
                gl_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/download/') + '?as_csv=1'
                gl_link = f'  <a href="{gl_url}">.csv</a>'
            repr_link = '           '
            if file_lower.endswith('.man') or  file_lower.endswith('.sol'):
                repr_url = '/weppcloud' + _join(request_path, _file) + '?repr=1'
                repr_link = f'  <a href="{repr_url}">annotated</a>'
            elif file_lower.endswith('.parquet') or file_lower.endswith('.csv') or file_lower.endswith('.tsv'):
                repr_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/pivottable/')
                repr_link = f'  <a href="{repr_url}">pivot</a>    '

            diff_link = '    '
            if diff_wd and not file_lower.endswith(('.tif', '.parquet', '.gz', '.img')):
                diff_path = _join(diff_wd, os.path.relpath(path, wd))
                if _exists(diff_path):
                    diff_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/diff/') + diff_arg
                    diff_link = f'  <a href="{diff_url}">diff</a>'
            s.append(_padding + f'{_tree_char} <a href="{file_link}">{_file}{ts_pad}</a>{last_modified_time} {item_pad}{file_size}{dl_link}{gl_link}{repr_link}{diff_link}{sym_target}\n')
        
        if i % 2:
            s[-1] = f'<span class="even-row">{s[-1]}</span>'
        else:
            s[-1] = f'<span class="odd-row">{s[-1]}</span>'
    
    return ''.join(s), total_items


def browse_response(path, runid, wd, request, config, filter_pattern=''):
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
        return error_factory('path does not exist')
    
    path_lower = path.lower()

    rel_path = os.path.relpath(path, wd)
    breadcrumbs = ''

    if os.path.isdir(path):
        # build bread crumb links
        _url = f'/weppcloud/runs/{runid}/{config}/browse/'
        breadcrumbs = [f'<a href="{_url}{diff_arg}"><b>{runid}</b></a>']

        if rel_path != '.':
            parts = rel_path.split('/')

            _rel_path = ''
            for part in parts[:-1]:
                _rel_path = _join(_rel_path, part)
                _url = f'/weppcloud/runs/{runid}/{config}/browse/{_rel_path}/'
                breadcrumbs.append(f'<a href="{_url}{diff_arg}"><b>{part}</b></a>')
            breadcrumbs.append(f'<b>{parts[-1]}</b>')

        breadcrumbs.append(f'<input type="text" id="pathInput" value="{filter_pattern}" placeholder="../output/p1.*" size="50">')
        breadcrumbs = ' ❯ '.join(breadcrumbs)

        # Get page and filter from query parameters
        page = request.args.get('page', 1, type=int)
        
        # Generate directory listing and get total items
        listing_html, total_items = html_dir_list(
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
        showing_text = (f'<p>Showing items {showing_start} to {showing_end} of {total_items}</p>'
                        if total_items > 0 else '<p>No items to display</p>')
        
        # Combine UI elements
        project_href = Markup(f'<a href="/weppcloud/runs/{runid}/{config}">☁️</a> ')
        breadcrumbs_markup = Markup(breadcrumbs)
        listing_markup = Markup(listing_html)
        pagination_markup = Markup(pagination_html)
        showing_markup = Markup(showing_text)

        return render_template(
            'browse/directory.j2',
            runid=runid,
            config=config,
            diff_runid=diff_runid,
            project_href=project_href,
            breadcrumbs_html=breadcrumbs_markup,
            listing_html=listing_markup,
            pagination_html=pagination_markup,
            showing_text=showing_markup,
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
                with gzip.open(path, 'rt') as fp:
                    contents = fp.read()
                path_lower = path_lower[:-3]
            else:
                with open(path) as fp:
                    try:
                        contents = fp.read()
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
                'browse/arc_file.j2',
                filename=basename(path),
                runid=runid,
                contents=contents,
            )

        html = None
        if path_lower.endswith('.pkl'):
            df = pd.read_pickle(path)
            html = df.to_html(classes=['sortable table table-nonfluid'], border=0, justify='left')

        if path_lower.endswith('.parquet'):
            df = pd.read_parquet(path)
            html = df.to_html(classes=['sortable table table-nonfluid'], border=0, justify='left')

        if path_lower.endswith('.csv'):
            skiprows = 0
            if 'totalwatsed2' in path_lower:
                skiprows = 1
            df = pd.read_csv(path, skiprows=skiprows)
            html = df.to_html(classes=['sortable table table-nonfluid'], border=0, justify='left')
            #html = csv_to_html(path)

        if path_lower.endswith('.tsv'):
            skiprows = 0
            df = pd.read_table(path, sep='\t', skiprows=skiprows)
            html = df.to_html(classes=['sortable table table-nonfluid'], border=0, justify='left')

        if html is not None:
            table_markup = Markup(html)
            return render_template(
                'browse/data_table.j2',
                filename=basename(path),
                runid=runid,
                table_html=table_markup,
            )

        if contents is None:
            with open(path) as fp:
                try:
                    contents = fp.read()
                except UnicodeDecodeError:
                    return send_file(path, as_attachment=True, download_name=_split(path)[-1])

        contents_html = _wrap_usersum_spans(contents)

        return render_template(
            'browse/text_file.j2',
            runid=runid,
            path=path,
            filename=basename(path),
            contents=contents,
            contents_html=contents_html,
        )
