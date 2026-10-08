"""Fork console routes."""

import json
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


def _read_fork_optional_state(root_fd: int, name: str) -> dict:
    # Hydrating even a detached NoDb can migrate a legacy source on this GET.
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=root_fd)
    except FileNotFoundError:
        return {}
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(f"Fork option metadata must be a regular file: {name}")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
            document = json.load(stream)
    finally:
        os.close(fd)
    if not isinstance(document, dict):
        raise ValueError(f"Invalid fork option metadata: {name}")
    state = document.get("py/state", document)
    if not isinstance(state, dict):
        raise ValueError(f"Invalid fork option metadata state: {name}")
    return state


def _fork_has_omni_children(root_fd: int) -> bool:
    opened: list[int] = []
    try:
        for collection in ("scenarios", "contrasts"):
            parent_fd = root_fd
            for part in ("_pups", "omni", collection):
                try:
                    parent_fd = os.open(
                        part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=parent_fd,
                    )
                except FileNotFoundError:
                    break
                opened.append(parent_fd)
            else:
                with os.scandir(parent_fd) as children:
                    if any(child.is_dir(follow_symlinks=False) for child in children):
                        return True
        return False
    finally:
        for fd in reversed(opened):
            os.close(fd)


def _fork_option_availability(source_wd: str) -> tuple[bool, bool]:
    root_fd = os.open(source_wd, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        disturbed = _read_fork_optional_state(root_fd, "disturbed.nodb")
        omni = _read_fork_optional_state(root_fd, "omni.nodb")
        map_name = disturbed.get("_disturbed_fn")
        if map_name is not None and not isinstance(map_name, str):
            raise ValueError("Invalid disturbed SBS filename in fork source")
        can_undisturbify = bool(map_name) and (
            os.path.isfile(os.path.join(source_wd, "disturbed", map_name))
            or os.path.isfile(os.path.join(source_wd, "disturbed", "sbs_4class.tif"))
        )
        can_skip_omni = False
        for key in ("_scenarios", "_contrast_names", "_contrast_pairs", "_contrasts"):
            values = omni.get(key)
            if values is not None and not isinstance(values, list):
                raise ValueError(f"Invalid Omni fork option metadata: {key}")
            can_skip_omni = can_skip_omni or bool(any(values or []))
        return can_undisturbify, can_skip_omni or _fork_has_omni_children(root_fd)
    finally:
        os.close(root_fd)


def _checked_omni_destination_ready(destination_wd: str) -> bool:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    opened: list[int] = []
    try:
        root_fd = os.open(destination_wd, flags)
        opened.append(root_fd)
        try:
            omni_stat = os.stat("omni.nodb", dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            controller_present = False
        else:
            if not stat.S_ISREG(omni_stat.st_mode):
                return False
            controller_present = True
        for parts in (("omni",), ("_pups", "omni", "scenarios"), ("_pups", "omni", "contrasts")):
            parent_fd = root_fd
            for part in parts:
                try:
                    parent_fd = os.open(part, flags, dir_fd=parent_fd)
                except FileNotFoundError:
                    if controller_present:
                        return False
                    break
                opened.append(parent_fd)
            else:
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
    can_undisturbify, can_skip_omni = _fork_option_availability(
        get_wd(runid, prefer_active=False)
    )
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
    undisturbify = undisturbify and can_undisturbify
    skip_omni_scenarios_contrasts = skip_omni_scenarios_contrasts and can_skip_omni

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
        can_undisturbify=can_undisturbify,
        can_skip_omni=can_skip_omni,
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
