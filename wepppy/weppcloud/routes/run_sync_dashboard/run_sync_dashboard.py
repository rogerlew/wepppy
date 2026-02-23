"""Admin dashboard for run sync and provenance registration."""

from __future__ import annotations

import uuid

from wepppy.rq.migrations_rq import STATUS_CHANNEL_SUFFIX as MIGRATIONS_CHANNEL_SUFFIX
from wepppy.rq.run_sync_rq import DEFAULT_TARGET_ROOT, STATUS_CHANNEL_SUFFIX
from wepppy.weppcloud.utils import auth_tokens

from .._common import *  # noqa: F401,F403

run_sync_dashboard_bp = Blueprint('run_sync_dashboard', __name__, template_folder='templates')

def _issue_rq_engine_token() -> str:
    subject = None
    if hasattr(current_user, "get_id"):
        subject = current_user.get_id()
    if not subject:
        subject = getattr(current_user, "id", None)
    if not subject:
        subject = getattr(current_user, "email", None)
    if not subject:
        raise RuntimeError("Unable to resolve user subject for rq-engine token")

    roles = [
        str(getattr(role, "name", role)).strip()
        for role in (getattr(current_user, "roles", None) or [])
        if str(getattr(role, "name", role)).strip()
    ]

    token_payload = auth_tokens.issue_token(
        str(subject),
        scopes=["rq:enqueue"],
        audience="rq-engine",
        extra_claims={
            "roles": roles,
            "token_class": "user",
            "email": getattr(current_user, "email", None),
            "jti": uuid.uuid4().hex,
        },
    )
    token = token_payload.get("token")
    if not token:
        raise RuntimeError("Failed to issue rq-engine token")
    return token


@run_sync_dashboard_bp.route('/rq/run-sync', strict_slashes=False)
@login_required
@roles_required('Admin')
def run_sync_dashboard():
    try:
        rq_engine_token = _issue_rq_engine_token()
        return render_template(
            'rq-run-sync-dashboard.htm',
            default_target_root=DEFAULT_TARGET_ROOT,
            status_channel_suffix=STATUS_CHANNEL_SUFFIX,
            migrations_channel_suffix=MIGRATIONS_CHANNEL_SUFFIX,
            rq_engine_token=rq_engine_token,
        )
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("Failed to issue rq-engine token for run sync dashboard")
        return exception_factory(f"JWT configuration error: {exc}")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_sync_dashboard/run_sync_dashboard.py:65", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory()
