import os
import subprocess
import re
import math
import json

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
            abort(404, f"Directory not found: {dir_path}")
            
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
    
    Args:
        directory (str): Directory path to list.
        filter_pattern (str): Sanitized shell glob pattern (e.g., '*.txt').
        page (int): Page number (1-based).
        page_size (int): Number of entries per page.
    
    Returns:
        list: List of tuples (name, is_dir, modified_time, hr_size, is_symlink, sym_target).
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
        return []
    
    entries = []
    dir_indices = []
    index = 0
    for line in result.stdout.splitlines():
        if line == '':
            break
        
        # Split the line into parts, limiting to 7 splits to handle filenames with spaces
        parts = line.split(maxsplit=7)
        if len(parts) < 8:
            continue
        
        # Extract file type flags
        flag = parts[0]
        is_dir = flag.startswith('d')
        is_symlink = flag.startswith('l')
        
        # Extract ISO modification time (YYYY-MM-DD HH:MM)
        modified_time = f"{parts[5]} {parts[6]}"
        
        # Extract filename or symlink information
        file_field = parts[7]
        if is_symlink and " -> " in file_field:
            name, _, sym_target = file_field.partition(" -> ")
            name = name.strip()
            sym_target = '->' + sym_target.strip()
        else:
            name = file_field
            sym_target = ""
        
        # Calculate human-readable size for files (not directories)
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
                size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
                i = int(math.floor(math.log(size_bytes, 1024)))
                p = math.pow(1024, i)
                s = round(size_bytes / p, 2)
                hr_size = f"{s} {size_name[i]}"
        
        # Add entry to the list
        entries.append((name, is_dir, modified_time, hr_size, is_symlink, sym_target))
        index += 1
    
    if dir_indices:
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Call get_total_items for each subdirectory, without filter_pattern
            futures = {executor.submit(get_total_items, dir_path): i for i, dir_path in dir_indices}
            for future in futures:
                index = futures[future]
                total_items = future.result()
                entry = entries[index]
                # Replace the entry with updated total items
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
    s = ['+-' + basename(abspath(_dir)) + '\n']
    
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
        
        if is_dir:
            file_link = '/weppcloud' + _join(request_path, _file)
            item_count = entry[3]
            sym_target = entry[5]
            item_pad = get_pad(8 - len(item_count.split()[0]))
            end_pad = ' ' * 32
            s.append(_padding + f'+-<a href="{file_link}/{diff_arg}">{_file}</a>{ts_pad}{last_modified_time} {item_pad}{item_count}{end_pad}{sym_target}\n')
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
            repr_link = '           '
            if file_lower.endswith('.man') or  file_lower.endswith('.sol'):
                repr_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/repr/')
                repr_link = f'  <a href="{repr_url}">annotated</a>'
            diff_link = '    '
            if diff_wd and not file_lower.endswith(('.tif', '.parquet', '.gz', '.img')):
                diff_path = _join(diff_wd, os.path.relpath(path, wd))
                if _exists(diff_path):
                    diff_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/diff/') + diff_arg
                    diff_link = f'  <a href="{diff_url}">diff</a>'
            s.append(_padding + f'>-<a href="{file_link}">{_file}</a>{ts_pad}{last_modified_time} {item_pad}{file_size}{dl_link}{gl_link}{repr_link}{diff_link}{sym_target}\n')
        
        if i % 2:
            s[-1] = f'<span style="background-color:#f6f6f6;">{s[-1]}</span>'
    
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
        breadcrumbs = [f'<a href="{_url}{diff_arg}">{runid}</a>']

        if rel_path != '.':
            parts = rel_path.split('/')

            _rel_path = ''
            for part in parts[:-1]:
                _rel_path = _join(_rel_path, part)
                _url = f'/weppcloud/runs/{runid}/{config}/browse/{_rel_path}/'
                breadcrumbs.append(f'<a href="{_url}{diff_arg}">{part}</a>')
            breadcrumbs.append(parts[-1])

        breadcrumbs = ' / '.join(breadcrumbs)

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
        tree = f'<pre>{showing_text}{pagination_html}{breadcrumbs}\n\n{listing_html}\n{pagination_html}</pre>'
        
        return Response('''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{runid} browser</title>
<script>
function redirectToDiff() {{
    var runId = document.getElementById('runIdInput').value;
    window.location.href = '?diff=' + encodeURIComponent(runId);
}}
</script>
</head>
<body>
    <input type="text" value="{value}" id="runIdInput" placeholder="runid">
    <button onclick="redirectToDiff()">Compare project</button>
    {tree}
</body>
</html>'''.format(runid=runid, value=diff_runid, tree=tree))
    
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
            c = '<pre style="font-size:xx-small;">\n{}</pre>'.format(contents)
            return Response(c, mimetype='text/html')

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

        if html is not None:
            c = ['<html>',
                 '<head>',
                 '<link rel="stylesheet" '
                 'href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css"'
                 'integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2"'
                 'crossorigin="anonymous">',
                 '<script src="https://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>',
                 '<style>.table-nonfluid {width: auto !important;}</style>'
                 '</head>'
                 '<body>',
                 '<a href="?download">Download File</a><hr>' + html,
                 '</body>',
                 '</html>']

            return Response('\n'.join(c), mimetype='text/html')

        with open(path) as fp:
            try:
                contents = fp.read()
            except UnicodeDecodeError:
                return send_file(path, as_attachment=True, download_name=_split(path)[-1])

        r = Response(response=contents, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r


