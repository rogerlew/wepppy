"""Fork console routes."""

from .._common import *  # noqa: F401,F403


fork_bp = Blueprint('fork', __name__, template_folder='templates')


@fork_bp.route('/runs/<string:runid>/<config>/rq-fork-console', strict_slashes=False)
@fork_bp.route('/runs/<string:runid>/<config>/rq-fork-console/', strict_slashes=False)
def rq_fork_console(runid, config):
    authorize(runid, config)
    undisturbify = ('false', 'true')[bool(request.args.get('undisturbify', False))]
    return render_template('rq-fork-console.j2', runid=runid, config=config, undisturbify=undisturbify)
