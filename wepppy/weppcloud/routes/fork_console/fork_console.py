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

    return render_template('rq-fork-console.htm', runid=runid, config=config, undisturbify=undisturbify)
