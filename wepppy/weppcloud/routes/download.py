import os
from io import BytesIO

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import pandas as pd

from flask import abort, Blueprint, request, Response, send_file, jsonify

from wepppy.weppcloud.utils.helpers import get_wd, htmltree


download_bp = Blueprint('download', __name__)

@download_bp.route('/runs/<string:runid>/<config>/aria2c.spec')
def aria2c_spec(runid, config):
    wd = os.path.abspath(get_wd(runid))
    base_url = f"https://wepp.cloud/weppcloud/runs/{runid}/{config}/download"

    file_list = []

    for root, dirs, files in os.walk(wd):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, wd)
            url = f"{base_url}/{relative_path}"
            file_list.append(f"{url}\n out={relative_path}")

    spec_content = "\n".join(file_list)
    return Response(spec_content, mimetype='text/plain')


@download_bp.route('/runs/<string:runid>/<config>/download/', defaults={'subpath': ''}, strict_slashes=False)
@download_bp.route('/runs/<string:runid>/<config>/download/<path:subpath>', strict_slashes=False)
def download_tree(runid, config, subpath):
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
        show_up = dir_path != wd
        return download_response_dir(dir_path, show_up=show_up, args=request.args, headers=request.headers)
    else:
        return download_response_file(dir_path, args=request.args, headers=request.headers)
    

def download_response_file(path, args=None, headers=None):
    filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower()
    as_csv = args.get('as_csv') if args else False

    # if ?as_csv=1 and it's a Parquet file, convert it
    if as_csv and ext == '.parquet':
        # read the parquet into a DataFrame
        df = pd.read_parquet(path)
        # write CSV to an in-memory bytes buffer
        buf = BytesIO()
        df.to_csv(buf, index=False)
        buf.seek(0)

        csv_name = os.path.splitext(filename)[0] + '.csv'
        return send_file(
            buf,
            as_attachment=True,
            download_name=csv_name,
            mimetype='text/csv'
        )

    # fall back to regular file download
    return send_file(
        path,
        as_attachment=True,
        download_name=filename
    )


def download_response_dir(path, show_up=False, args=None, headers=None):
    assert os.path.isdir(path)

    up = ''
    if show_up:
        up = '<a href="../">Up</a>\n'
    c = '<pre>\n{}{}</pre>'.format(up, htmltree(path))

    return Response(c, mimetype='text/html')

