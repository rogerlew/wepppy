import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify

from utils.helpers import get_wd, htmltree, error_factory


repr_bp = Blueprint('repr', __name__)


@repr_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/repr/<path:subpath>', strict_slashes=False)
def wp_repr_tree(runid, config, wepp, subpath):
    return repr_tree(runid, config, subpath)


@repr_bp.route('/runs/<string:runid>/<config>/repr/<path:subpath>', strict_slashes=False)
def repr_tree(runid, config, subpath):
    """
    Recursive list the file structure of the working directory.
    """
    wd = os.path.abspath(get_wd(runid))
    dir_path = os.path.abspath(os.path.join(wd, subpath))

    if not dir_path.startswith(wd):
        abort(403)

    if not _exists(dir_path):
        abort(404)

    if os.path.isdir(dir_path):
        abort(404)

    return repr_response(dir_path)


def repr_response(path):
    if not _exists(path):
        return error_factory('path does not exist')

    path_lower = path.lower()
    if path_lower.endswith('.man'):
        from wepppy.wepp.management import read_management
        try:
            man = read_management(path)
            contents = repr(man)

            r = Response(response=contents, status=200, mimetype="text/plain")
            r.headers["Content-Type"] = "text/plain; charset=utf-8"
            return r

        except Exception:
            return exception_factory('Error retrieving management', runid=runid)

    abort(404)

