"""Fork console routes."""

import os
import stat

import redis

from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.weppcloud.utils.rq_engine_token import issue_user_rq_engine_token

from .._common import *  # noqa: F401,F403


fork_bp = Blueprint('fork', __name__, template_folder='templates')

_FORK_DESTINATION_REQUIRED_FILES = (
    'ron.nodb',
    'wepp.nodb',
    'landuse.nodb',
    'soils.nodb',
)


def _issue_rq_engine_token() -> str | None:
    return issue_user_rq_engine_token(current_user)


def _fetch_fork_job(job_id: str):
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        return Job.fetch(job_id, connection=redis_conn)


def _checked_omni_destination_ready(destination_wd: str) -> bool:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    opened: list[int] = []
    try:
        root_fd = os.open(destination_wd, flags)
        opened.append(root_fd)
        omni_stat = os.stat("omni.nodb", dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISREG(omni_stat.st_mode):
            return False
        for parts in (("omni",), ("_pups", "omni", "scenarios"), ("_pups", "omni", "contrasts")):
            parent_fd = root_fd
            for part in parts:
                parent_fd = os.open(part, flags, dir_fd=parent_fd)
                opened.append(parent_fd)
            if os.listdir(parent_fd):
                return False
        return True
    except OSError:
        return False
    finally:
        for fd in reversed(opened):
            os.close(fd)


@fork_bp.route('/runs/<string:runid>/<config>/rq-fork-console', strict_slashes=False)
@fork_bp.route('/runs/<string:runid>/<config>/rq-fork-console/', strict_slashes=False)
def rq_fork_console(runid, config):
    authorize(runid, config)
    undisturbify_arg = request.args.get('undisturbify')
    skip_wepp_runs_output_arg = request.args.get('skip_wepp_runs_output')
    skip_omni_scenarios_contrasts_arg = request.args.get('skip_omni_scenarios_contrasts')
    undisturbify = False
    skip_wepp_runs_output = False
    skip_omni_scenarios_contrasts = False
    if isinstance(undisturbify_arg, str):
        undisturbify = undisturbify_arg.strip().lower() in ('true', '1', 'yes', 'on')
    if isinstance(skip_wepp_runs_output_arg, str):
        skip_wepp_runs_output = skip_wepp_runs_output_arg.strip().lower() in ('true', '1', 'yes', 'on')
    if isinstance(skip_omni_scenarios_contrasts_arg, str):
        skip_omni_scenarios_contrasts = skip_omni_scenarios_contrasts_arg.strip().lower() in ('true', '1', 'yes', 'on')

    cap_base_url = (current_app.config.get('CAP_BASE_URL') or os.getenv('CAP_BASE_URL', '/cap')).rstrip('/')
    cap_asset_base_url = (
        current_app.config.get('CAP_ASSET_BASE_URL')
        or os.getenv('CAP_ASSET_BASE_URL', f'{cap_base_url}/assets')
    ).rstrip('/')
    cap_site_key = current_app.config.get('CAP_SITE_KEY') or os.getenv('CAP_SITE_KEY', '')
    rq_engine_token = None
    if current_user.is_authenticated:
        try:
            rq_engine_token = _issue_rq_engine_token()
        except Exception:
            current_app.logger.exception("Failed to issue rq-engine token for fork console")

    return render_template(
        'rq-fork-console.htm',
        runid=runid,
        config=config,
        undisturbify=undisturbify,
        skip_wepp_runs_output=skip_wepp_runs_output,
        skip_omni_scenarios_contrasts=skip_omni_scenarios_contrasts,
        cap_base_url=cap_base_url,
        cap_asset_base_url=cap_asset_base_url,
        cap_site_key=cap_site_key,
        rq_engine_token=rq_engine_token,
    )


@fork_bp.get(
    '/runs/<string:runid>/<config>/rq-fork-console/readiness/'
    '<string:job_id>/<string:destination_runid>'
)
def fork_destination_readiness(runid, config, job_id, destination_runid):
    """Report whether WEPPcloud can resolve the fork's core destination state."""
    authorize(runid, config)
    try:
        job = _fetch_fork_job(job_id)
    except NoSuchJobError:
        abort(404)

    expected_func = 'wepppy.rq.project_rq.fork_rq'
    args = tuple(job.args or ())
    if (
        job.func_name != expected_func
        or len(args) < 2
        or args[:2] != (runid, destination_runid)
    ):
        abort(404)
    if job.get_status(refresh=True) != 'finished':
        return jsonify({'ready': False})

    authorize(destination_runid, config)
    try:
        destination_wd = get_wd(destination_runid, prefer_active=False)
    except ValueError:
        abort(400)

    missing = [
        name
        for name in _FORK_DESTINATION_REQUIRED_FILES
        if not _exists(_join(destination_wd, name))
    ]
    ready = _exists(destination_wd) and not missing
    if ready and len(args) == 5 and args[4] is True:
        ready = _checked_omni_destination_ready(destination_wd)
    return jsonify(
        {'ready': ready}
    )
