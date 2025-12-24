"""Fork console routes."""

from .._common import *  # noqa: F401,F403


fork_bp = Blueprint('fork', __name__, template_folder='templates')


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

    return render_template(
        'rq-fork-console.htm',
        runid=runid,
        config=config,
        undisturbify=undisturbify,
        cap_base_url=cap_base_url,
        cap_asset_base_url=cap_asset_base_url,
        cap_site_key=cap_site_key,
    )
