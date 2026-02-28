import os
import difflib

from .._common import *  # noqa: F401,F403

from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.runtime_paths.fs import stat as nodir_stat
from wepppy.runtime_paths.paths import parse_external_subpath
from wepppy.weppcloud.utils.helpers import get_wd, error_factory, url_for_run

from .._run_context import load_run_context


diff_bp = Blueprint('diff', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/diff/static')


def _nodir_error_response(err: NoDirError):
    return error_factory(
        err.message,
        status_code=err.http_status,
        code=err.code,
        details=err.message,
    )


def _resolve_diff_target_path(wd_root: str, logical_rel_path: str, *, nodir_view: str) -> str | None:
    try:
        nodir_target = nodir_resolve(wd_root, logical_rel_path, view=nodir_view)
    except NoDirError:
        raise

    if nodir_target is None:
        dir_path = os.path.abspath(os.path.join(wd_root, logical_rel_path))
        if not dir_path.startswith(wd_root + os.sep) and dir_path != wd_root:
            abort(403)

        if not os.path.exists(dir_path):
            return None
        if os.path.isdir(dir_path):
            abort(404)

        return os.path.relpath(dir_path, wd_root).replace(os.sep, "/")

    try:
        nodir_entry = nodir_stat(nodir_target)
    except FileNotFoundError:
        return None
    except NotADirectoryError:
        return None

    if nodir_entry.is_dir:
        abort(404)

    if logical_rel_path in (".", ""):
        abort(404)

    return logical_rel_path.replace(os.sep, "/")


@diff_bp.route('/runs/<string:runid>/<config>/diff/<path:subpath>', strict_slashes=False)
@authorize_and_handle_with_exception_factory
def diff_comparer(runid, config, subpath):
    ctx = load_run_context(runid, config)
    wd_root = os.path.abspath(str(ctx.active_root))

    diff_runid = request.args.get('diff', None)
    if diff_runid is None:
        abort(403)

    try:
        logical_subpath, _parsed_view = parse_external_subpath(subpath, allow_admin_alias=False)
        nodir_view = "effective"
    except ValueError:
        abort(403)

    try:
        safe_subpath = _resolve_diff_target_path(
            wd_root,
            logical_subpath,
            nodir_view=nodir_view,
        )
    except NoDirError as err:
        return _nodir_error_response(err)

    if safe_subpath is None:
        missing_left = os.path.abspath(os.path.join(wd_root, logical_subpath))
        return error_factory(f'path: `{missing_left}` does not exist')

    diff_root = os.path.abspath(get_wd(diff_runid))
    try:
        diff_subpath = _resolve_diff_target_path(
            diff_root,
            safe_subpath,
            nodir_view=nodir_view,
        )
    except NoDirError as err:
        return _nodir_error_response(err)

    if diff_subpath is None:
        missing_right = os.path.abspath(os.path.join(diff_root, safe_subpath))
        return error_factory(f'path: `{missing_right}` does not exist')

    left_download_url = url_for_run(
                    'download.download_with_subpath',
                    runid=runid,
                    config=config,
                    subpath=safe_subpath
                )
    right_download_url = url_for_run(
                    'download.download_with_subpath',
                    runid=diff_runid,
                    config=config,
                    subpath=safe_subpath
                )

    # render template with client side diff. client will fetch the files from diff
    return render_template('comparer.htm',
                            runid=runid,  # left
                            config=config,
                            diff_runid=diff_runid,  # right
                            subpath=safe_subpath,
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
