import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import difflib

from .._common import *  # noqa: F401,F403

from wepppy.weppcloud.utils.helpers import get_wd, error_factory, url_for_run

from .._run_context import load_run_context


diff_bp = Blueprint('diff', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/diff/static')

@diff_bp.route('/runs/<string:runid>/<config>/diff/<path:subpath>', strict_slashes=False)
def diff_comparer(runid, config, subpath):
    ctx = load_run_context(runid, config)
    wd = os.path.abspath(str(ctx.active_root))
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

    diff_wd = get_wd(diff_runid)
    diff_path = os.path.join(diff_wd, subpath)

    if not _exists(diff_path):
        return error_factory(f'path: `{diff_path}` does not exist')

    left_download_url = url_for_run(
                    'download.download_with_subpath',
                    runid=runid,
                    config=config,
                    subpath=subpath
                )
    right_download_url = url_for_run(
                    'download.download_with_subpath',
                    runid=diff_runid,
                    config=config,
                    subpath=subpath
                )

    # render template with client side diff. client will fetch the files from diff
    return render_template('comparer.htm',
                            runid=runid,  # left
                            config=config,
                            diff_runid=diff_runid,  # right
                            subpath=subpath,
                            left_download_url=left_download_url,
                            right_download_url=right_download_url
                           )

# this goes away this was old approach that was slow
def diff_response(path, diff_path, runid, diff_runid):
    with open(path, 'r') as f:
        left = f.readlines()
    with open(diff_path, 'r') as f:
        right = f.readlines()

    diff = difflib.HtmlDiff()
    html_diff = diff.make_file(left, right, runid, diff_runid)
    html_diff = html_diff.replace('Courier; border:medium;', 'monospace;')
    return Response(html_diff)
