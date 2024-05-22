import os
import time
from os import listdir, sep
from os.path import abspath, basename, isdir, isfile

import math
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import pandas as pd

from flask import abort, Blueprint, request, Response, send_file, jsonify, redirect

from utils.helpers import get_wd


browse_bp = Blueprint('browse', __name__)


@browse_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/browse/', defaults={'subpath': ''}, strict_slashes=False)
@browse_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/browse/<path:subpath>', strict_slashes=False)
def wp_browse_tree(runid, config, wepp, subpath):
    wd = os.path.abspath(get_wd(runid))
    dir_path = os.path.abspath(os.path.join(wd, subpath))

    if not dir_path.startswith(wd):
        abort(403)

    if not _exists(dir_path):
        abort(404)

    if os.path.isdir(dir_path):
        if not request.path.endswith('/'):
            return redirect( '/weppcloud' + request.path + '/', code=302)

    return browse_response(dir_path, runid, wd, request)


@browse_bp.route('/runs/<string:runid>/<config>/browse/', defaults={'subpath': ''}, strict_slashes=False)
@browse_bp.route('/runs/<string:runid>/<config>/browse/<path:subpath>', strict_slashes=False)
def browse_tree(runid, config, subpath):
    wd = os.path.abspath(get_wd(runid))
    dir_path = os.path.abspath(os.path.join(wd, subpath))

    if not dir_path.startswith(wd):
        abort(403)

    if not _exists(dir_path):
        abort(404)

    if os.path.isdir(dir_path):
        if not request.path.endswith('/'):
            return redirect( '/weppcloud' + request.path + '/', code=302)

    return browse_response(dir_path, runid, wd, request)


def get_human_readable_size(path):
    size_bytes = os.path.getsize(path)

    if size_bytes == 0:
        return "0 B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return f"{s} {size_name[i]}"


def sorted_paths(paths, _dir):
    dirs = [x for x in paths if isdir(_join(_dir, x))]
    files = [x for x in paths if isfile(_join(_dir, x))]
    return sorted(dirs) + sorted(files)


def get_pad(x):
    if x < 1: return ' '
    return x * ' '

def html_dir_list(_dir, runid, wd, request_path, diff_runid, diff_wd, diff_arg):
    _padding = ' '

    s = ['+-' + basename(abspath(_dir)) + '\n']
    files = listdir(_dir)

    _diff_dir = None
    if diff_runid is not None:
        _diff_dir = _dir.replace(runid, diff_runid)
        if not _exists(_diff_dir):
            _diff_dir = None

    n = max(36, max(len(x) for x in files))

    for i, _file in enumerate(sorted_paths(files, _dir)):
        path = _dir + sep + _file

        ts_pad = get_pad(n - len(_file))
        timestamp = os.path.getmtime(path)
        last_modified_time = time.ctime(timestamp)[4:]

        if isdir(path):
            item_count = f'{len(listdir(path))} items'
            item_pad = get_pad(8 - len(item_count.split()[0]))
            end_pad = ' ' * 32
            s.append(_padding + f'+-<a href="{_file}/{diff_arg}">{_file}</a> {ts_pad}{last_modified_time} {item_pad}{item_count}{end_pad}\n')
        else:
            if os.path.islink(path):
                target = ' -> {}'.format('/'.join(os.readlink(path).split('/')[-2:]))
            else:
                target = ''

            file_size = get_human_readable_size(path)
            item_pad = get_pad(8 - len(file_size.split()[0]))

            dl_pad = get_pad(6 - len(file_size.split()[1]))
            dl_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/download/')
            dl_link = f'{dl_pad}<a href="{dl_url}">download</a>'

            file_lower = _file.lower()
            gl_link = '          '
            if file_lower.endswith('.arc') or file_lower.endswith('.tif') or file_lower.endswith('.img') or file_lower.endswith('.nc'):
                gl_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/gdalinfo/')
                gl_link = f'  <a href="{gl_url}">gdalinfo</a>'

            repr_link = '           '
            if file_lower.endswith('.man'):
                repr_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/repr/')
                repr_link = f'  <a href="{repr_url}">annotated</a>'

            diff_link = '    '
            if _diff_dir:
                if not (file_lower.endswith('.tif') or
                        file_lower.endswith('.parquet') or
                        file_lower.endswith('.gz') or
                        file_lower.endswith('.img')):
                    if _exists(_join(_diff_dir, _file)):
                        diff_url = '/weppcloud' + _join(request_path, _file).replace('/browse/', '/diff/') + diff_arg
                        diff_link = f'  <a href="{diff_url}">diff</a>'

            s.append(_padding + f'>-<a href="{_file}">{_file}</a>{target} {ts_pad}{last_modified_time} {item_pad}{file_size}{dl_link}{gl_link}{repr_link}{diff_link}\n')

        if i % 2:
            s[-1] = f'<span style="background-color:#f6f6f6;">{s[-1]}</span>'

    return ''.join(s)


def browse_response(path, runid, wd, request):
    args = request.args
    headers = request.headers

    diff_runid = args.get('diff', '')
    diff_wd = None
    diff_arg = ''
    if diff_runid:
        diff_wd = get_wd(diff_runid)
        diff_arg = f'?diff={diff_runid}'

    if not _exists(path):
        return error_factory('path does not exist')

    path_lower = path.lower()

    if os.path.isdir(path):
        up = ''
        if path != wd:
            up = f'<a href="../{diff_arg}">Up</a>\n'

        tree = '<pre>\n{}{}</pre>'\
               .format(up, html_dir_list(path, runid, wd, request.path, diff_runid, diff_wd, diff_arg))

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
            return send_file(path, as_attachment=True, attachment_filename=_split(path)[-1])

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
            df = pd.read_csv(path)
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
                return send_file(path, as_attachment=True, attachment_filename=_split(path)[-1])

        r = Response(response=contents, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r


