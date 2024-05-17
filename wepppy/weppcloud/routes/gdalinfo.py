import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify

from utils.helpers import get_wd, htmltree, error_factory


gdalinfo_bp = Blueprint('gdalinfo', __name__)


@gdalinfo_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/gdalinfo/<path:subpath>', strict_slashes=False)
def wp_gdalinfo_tree(runid, config, wepp, subpath):
    return gdalinfo_tree(runid, config, subpath)


@gdalinfo_bp.route('/runs/<string:runid>/<config>/gdalinfo/<path:subpath>', strict_slashes=False)
def gdalinfo_tree(runid, config, subpath):
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

    return gdalinfo_response(dir_path)


def gdalinfo_response(path):
    if not _exists(path):
        return error_factory('path does not exist')

    contents = check_output('gdalinfo -json ' + path, shell=True)
    jsobj = json.loads(contents)
    return jsonify(jsobj)

