"""Fork console routes."""

from wepppy.weppcloud.utils.rq_engine_token import issue_user_rq_engine_token

from .._common import *  # noqa: F401,F403


fork_bp = Blueprint('fork', __name__, template_folder='templates')


def _issue_rq_engine_token() -> str | None:
    return issue_user_rq_engine_token(current_user)


@fork_bp.route('/runs/<string:runid>/<config>/rq-fork-console', strict_slashes=False)
@fork_bp.route('/runs/<string:runid>/<config>/rq-fork-console/', strict_slashes=False)
def rq_fork_console(runid, config):
    authorize(runid, config)
    undisturbify_arg = request.args.get('undisturbify')
    undisturbify = False
    if isinstance(undisturbify_arg, str):
        undisturbify = undisturbify_arg.strip().lower() in ('true', '1', 'yes', 'on')

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
        cap_base_url=cap_base_url,
        cap_asset_base_url=cap_asset_base_url,
        cap_site_key=cap_site_key,
        rq_engine_token=rq_engine_token,
    )
