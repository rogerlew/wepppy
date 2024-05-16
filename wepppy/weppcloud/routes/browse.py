import os

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import pandas as pd

from flask import abort, Blueprint, request, Response, send_file

from utils.helpers import get_wd, htmltree


browse_bp = Blueprint('browse', __name__)


@browse_bp.route('/browse/<config>')
def browse_config(config):

    return browse_response(f'/wepppy/wepppy/wepppy/nodb/configs/{config}.cfg', show_up=False, args=request.args, headers=request.headers)


@browse_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/browse/', defaults={'subpath': ''}, strict_slashes=False)
@browse_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/browse/<path:subpath>', strict_slashes=False)
def wp_browse_tree(runid, config, wepp, subpath):
    return browse_tree(runid, config, subpath)


@browse_bp.route('/runs/<string:runid>/<config>/browse/', defaults={'subpath': ''}, strict_slashes=False)
@browse_bp.route('/runs/<string:runid>/<config>/browse/<path:subpath>', strict_slashes=False)
def browse_tree(runid, config, subpath):
    """
    Recursive list the file structure of the working directory.
    """
    wd = os.path.abspath(get_wd(runid))
    dir_path = os.path.abspath(os.path.join(wd, subpath))

    if not dir_path.startswith(wd):
        abort(403)

    if not _exists(dir_path):
        abort(404)

    show_up = False
    if os.path.isdir(dir_path):
        show_up = dir_path != wd

    return browse_response(dir_path, show_up=show_up, args=request.args, headers=request.headers)


def browse_response(path, args=None, show_up=True, headers=None):
    if not _exists(path):
        return error_factory('path does not exist')

    path_lower = path.lower()

    if os.path.isdir(path):
        up = ''
        if show_up:
            up = '<a href="../">Up</a>\n'

        c = '<pre>\n{}{}</pre>'\
            .format(up, htmltree(path))

        return Response(c, mimetype='text/html')

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

        if path_lower.endswith('.json') or path_lower.endswith('.nodb'):
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


