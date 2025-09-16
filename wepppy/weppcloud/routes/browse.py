import os
import subprocess
import re
import math
import json

import urllib
from urllib.parse import urlencode

from concurrent.futures import ThreadPoolExecutor

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from os.path import abspath, basename

import pandas as pd
import gzip

from flask import abort, Blueprint, request, Response, send_file, jsonify, redirect

from utils.helpers import get_wd, error_factory

"""
Browse Blueprint
================

This Flask Blueprint provides a web-based file explorer for project directories, allowing users to browse, filter, 
view, download, and compare files and directories associated with project runs.

Routes
------
- `/runs/<string:runid>/<config>/report/<string:wepp>/browse/`  
- `/runs/<string:runid>/<config>/report/<string:wepp>/browse/<path:subpath>`  
- `/runs/<string:runid>/<config>/browse/`  
- `/runs/<string:runid>/<config>/browse/<path:subpath>`  

Functionality
-------------
- **Directory Browsing**: Navigate project directories with pagination and wildcard filtering.
- **File Interaction**: View text-based file contents in the browser or download files via query parameters or headers.
- **File Type Support**: Render JSON, XML, CSV, Parquet, and Pickle files appropriately, with HTML tables for tabular data.
- **Directory Comparison**: Compare the current directory with another project run's directory using the `diff` parameter.
- **Security**: Prevent directory traversal and validate filter patterns to avoid shell injection.

Logical Flow
------------
1. **Route Handling**:
   - Routes `wp_browse_tree` and `browse_tree` capture URL parameters (`runid`, `config`, optional `wepp`, and `subpath`).
   - They determine the project's working directory (`wd`) using `get_wd(runid)` and delegate to `_browse_tree_helper`.

2. **Path and Filter Processing**:
   - `_browse_tree_helper` constructs the full path from `wd` and `subpath`.
   - If the path is a file, it calls `browse_response` directly.
   - If it’s a directory, it extracts any wildcard filter from the subpath (e.g., `*.txt`) or uses a default filter, then 
     passes control to `browse_response`.

3. **Security Validation**:
   - `_browse_tree_helper` ensures the path stays within `wd` to prevent directory traversal (aborts with 403 if not).
   - Validates the filter pattern with `_validate_filter_pattern` (aborts with 400 if invalid).

4. **Response Generation**:
   - For files, `browse_response`:
     - Checks for `raw` or `download` parameters/headers to serve raw content or trigger downloads.
     - Handles special file types (e.g., JSON, CSV) with appropriate rendering.
     - Falls back to plain text or binary download for unreadable files.
   - For directories, `browse_response`:
     - Calls `html_dir_list` to generate an HTML listing with pagination, file details, and action links.
     - Incorporates pagination controls and a diff comparison form.

5. **Directory Listing**:
   - `get_page_entries` uses `get_entries` and `get_total_items` concurrently via `ThreadPoolExecutor`:
     - `get_entries` runs `ls -l` with ISO time style to fetch paginated entries, parsing output into file details.
     - `get_total_items` counts total items with `ls | wc -l`.
   - Returns entries and total count for the current page.

6. **HTML Rendering**:
   - `html_dir_list` constructs an HTML string with directory contents, including navigation links, file sizes, 
     modification times, and action links (download, diff, etc.), respecting pagination and filters.

7. **Final Response**:
   - `browse_response` wraps the directory listing in a full HTML page with a diff comparison form and pagination, 
     or serves file content with the correct MIME type.

Key Functions
-------------
- **_validate_filter_pattern(pattern)**:
  Validates wildcard patterns (e.g., `*.txt`) using a regex, allowing safe characters and rejecting shell metacharacters.

- **_browse_tree_helper(runid, subpath, wd, request, filter_pattern_default='')**:
  Processes the request by parsing the path, enforcing security, and delegating to `browse_response`.

- **get_entries(directory, filter_pattern, start, end, page_size)**:
  Executes `ls -l` with pagination and filtering, parsing output into a list of entry tuples (name, is_dir, etc.).

- **get_total_items(directory)**:
  Counts total directory items using `ls | wc -l`.

- **get_page_entries(directory, page=1, page_size=MAX_FILE_LIMIT, filter_pattern='')**:
  Concurrently retrieves paginated entries and total count using `ThreadPoolExecutor`.

- **html_dir_list(_dir, runid, wd, request_path, diff_runid, diff_wd, diff_arg, page=1, page_size=MAX_FILE_LIMIT, filter_pattern='')**:
  Generates an HTML directory listing with file details, action links, and diff support.

- **browse_response(path, runid, wd, request, filter_pattern='')**:
  Handles file serving (raw, download, or rendered) or directory listing generation, including pagination and UI elements.

Notes
-----
- Uses `MAX_FILE_LIMIT = 100` as the default page size for pagination.
- Employs subprocess calls for efficiency, with concurrent execution for listing and counting.
- Assumes `get_wd(runid)` (from `utils.helpers`) returns the project’s working directory.
"""

MAX_FILE_LIMIT = 100

browse_bp = Blueprint('browse', __name__)



on_load_script = """<script>
document.addEventListener('DOMContentLoaded', () => {
    const pathInput = document.getElementById('pathInput');
    const rows = document.querySelectorAll('span.odd-row, span.even-row');
    const prompt = document.getElementById('filter-prompt');

    /**
     * Handles navigation when the Enter key is pressed in the path input.
     */
    function handleNavigation(event) {
        if (event.key !== 'Enter') return;
        event.preventDefault();

        const path = pathInput.value.trim();
        if (!path) return;

        const currentUrl = new URL(window.location.href);
        const searchParams = currentUrl.search;

        let newUrl;

        if (path.startsWith('/')) {
            // absolute from your browse root
            const baseUrl = `/weppcloud/runs/${runid}/${config}/browse`;
            newUrl = baseUrl + path; // e.g., "/.../browse/output"
        } else {
            // ensure the base ends with "/" so it's treated as a directory
            const baseHref =
                currentUrl.origin +
                currentUrl.pathname +
                (currentUrl.pathname.endsWith('/') ? '' : '/');

            const resolvedUrl = new URL(path, baseHref);
            newUrl = resolvedUrl.pathname;
        }

        window.location.href = newUrl + searchParams;
    }
    
    // Attach event listeners
    pathInput.addEventListener('keydown', handleNavigation);

    const el = document.getElementById('pathInput');
    if (!el) return;

    // in case something made it inert
    el.disabled = false;
    el.readOnly = false;

    // delay one frame so the URL bar/layout settles and other scripts attach
    requestAnimationFrame(() => {
        el.focus({ preventScroll: true });
        // put caret at end
        const pos = el.value.length;
        try { el.setSelectionRange(pos, pos); } catch (_) {}
    });
});
</script>
"""

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
    
    project_href = f'<a href="/weppcloud/runs/{runid}/{config}">☁️</a> '
    tree = f'<pre>{project_href}{breadcrumbs_html}{error_message}</pre>'

    # Construct the full HTML page, reusing the template from the main browse response
    html_content = f'''\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="/static/favicon/open_folder.svg?v=20250908"/>
<title>{runid} - Not Found</title>
<script>
// This script is needed for the diff and path input functionality
function redirectToDiff() {{
    var runId = document.getElementById('runIdInput').value;
    window.location.href = '?diff=' + encodeURIComponent(runId);
}}
const runid = "{runid}";
const config = "{config}";
</script>
<style>
  input[type='text'] {{ font-family: monospace; }}
  a {{ text-decoration: none; }}
</style>
</head>
<body>
    <input type="text" value="{diff_runid}" id="runIdInput" placeholder="runid">
    <button onclick="redirectToDiff()">Compare project</button>
    {tree}
    {on_load_script}
</body>
</html>'''

    return Response(html_content, status=404)

    
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
            for future in futures:
                index = futures[future]
                total_items = future.result()
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
        # Submit both subprocess tasks concurrently
        future_entries = executor.submit(get_entries, directory, filter_pattern, start, end, page_size)

        future_total = executor.submit(get_total_items, directory, filter_pattern)
        
        # Retrieve results (blocks until both are complete)
        entries = future_entries.result()
        total_items = future_total.result()
    
    return entries, total_items


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
                repr_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/repr/')
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
        project_href = f'<a href="/weppcloud/runs/{runid}/{config}">☁️</a> '
        tree = f'<pre id="file-tree">{showing_text}{pagination_html}\n{project_href}{breadcrumbs}\n{listing_html}\n{pagination_html}</pre>'

        return Response(f'''\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="/static/favicon/open_folder.svg?v=20250908"/>
<title>{runid}</title>
<script>
function redirectToDiff() {{
    var runId = document.getElementById('runIdInput').value;
    window.location.href = '?diff=' + encodeURIComponent(runId);
}}
const runid = "{runid}";
const config = "{config}";
</script>
<style>
  input[type='text'] {{ font-family: monospace; }}
  a {{ text-decoration: none; }}
  span.even-row {{ background-color: #f6f6f6;  display: block; }}
  span.odd-row {{ background-color: #ffffff;  display: block; }}
  span.even-row:hover, 
  span.odd-row:hover {{
    background-color: #d0ebff;
    cursor: pointer;
  }}
</style>
</head>
<body>
    <input type="text" value="{diff_runid}" id="runIdInput" placeholder="runid">
    <button onclick="redirectToDiff()">Compare project</button>
    {tree}
    {on_load_script}
</body>
</html>''')

    else:
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
            _content = f'''\
<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="/static/favicon/page.svg?v=20250908"/>
<title>{basename(path)} - {runid}</title>
</head><body>
<pre style="font-size:xx-small;">\n{contents}</pre>
</body></html>'''
            return Response(_content, mimetype='text/html')

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
            _content = f'''\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="/static/favicon/page.svg?v=20250908"/>
<title>{basename(path)} - {runid}</title>
<link rel="stylesheet"
href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css"
integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2"
crossorigin="anonymous">
<script src="/weppcloud/static/js/sorttable.js"></script>
<style>.table-nonfluid {{width: auto !important;}}</style>
</head>
<body>
<a href="?download">Download File</a><hr>{html}
</body>
</html>'''

            return Response(_content, mimetype='text/html')

        with open(path) as fp:
            try:
                contents = fp.read()
            except UnicodeDecodeError:
                return send_file(path, as_attachment=True, download_name=_split(path)[-1])

        _content = f'''\
<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="/static/favicon/page.svg?v=20250908"/>
<title>{basename(path)} - {runid}</title>
</head><body>
<pre>\n{contents}</pre>
</body></html>'''
        return Response(_content, mimetype='text/html')
        
