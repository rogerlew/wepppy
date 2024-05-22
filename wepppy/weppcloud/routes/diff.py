import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import difflib


from flask import abort, Blueprint, request, Response, jsonify

from utils.helpers import get_wd, htmltree, error_factory


diff_bp = Blueprint('diff', __name__)


@diff_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/diff/<path:subpath>', strict_slashes=False)
def wp_diff_tree(runid, config, wepp, subpath):
    return diff_tree(runid, config, subpath)


@diff_bp.route('/runs/<string:runid>/<config>/diff/<path:subpath>', strict_slashes=False)
def diff_tree(runid, config, subpath):
    wd = os.path.abspath(get_wd(runid))
    dir_path = os.path.abspath(os.path.join(wd, subpath))

    diff_runid = request.args.get('diff', None)
    if diff_runid is None:
        abort(403)

    if not dir_path.startswith(wd):
        abort(403)

    if not _exists(dir_path):
        return error_factory(f'path: `{dir_path}` does not exist')

    if os.path.isdir(dir_path):
        abort(404)

    diff_wd = os.path.abspath(get_wd(diff_runid))
    diff_path = os.path.abspath(os.path.join(diff_wd, subpath))

    if not _exists(diff_path):
        return error_factory(f'path: `{diff_path}` does not exist')

    return diff_response(dir_path, diff_path, runid, diff_runid)


def diff_response(path, diff_path, runid, diff_runid):
    with open(path, 'r') as f:
        left = f.readlines()
    with open(diff_path, 'r') as f:
        right = f.readlines()

    diff = difflib.HtmlDiff()
    html_diff = diff.make_file(left, right, runid, diff_runid)
    html_diff = html_diff.replace('Courier; border:medium;', 'monospace;')
    return Response(html_diff)

