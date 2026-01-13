"""Admin dashboard for run sync and provenance registration."""

from __future__ import annotations

from wepppy.rq.migrations_rq import STATUS_CHANNEL_SUFFIX as MIGRATIONS_CHANNEL_SUFFIX
from wepppy.rq.run_sync_rq import DEFAULT_TARGET_ROOT, STATUS_CHANNEL_SUFFIX

from .._common import *  # noqa: F401,F403

run_sync_dashboard_bp = Blueprint('run_sync_dashboard', __name__, template_folder='templates')


@run_sync_dashboard_bp.route('/rq/run-sync', strict_slashes=False)
@login_required
@roles_required('Admin')
def run_sync_dashboard():
    return render_template(
        'rq-run-sync-dashboard.htm',
        default_target_root=DEFAULT_TARGET_ROOT,
        status_channel_suffix=STATUS_CHANNEL_SUFFIX,
        migrations_channel_suffix=MIGRATIONS_CHANNEL_SUFFIX,
    )
