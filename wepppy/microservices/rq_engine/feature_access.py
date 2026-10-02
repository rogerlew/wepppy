"""FA-01 request adapter; existing JWT/scope/run checks remain mandatory."""
import logging

from sqlalchemy.exc import SQLAlchemyError

from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal
from wepppy.weppcloud.utils.feature_access_identity import FeatureIdentityConfigurationError, principal_from_verified_claims
from wepppy.weppcloud.utils.feature_access_runtime import decide, decision_status, resource_context
from .auth import AuthError

logger = logging.getLogger(__name__)


def _legacy_session_identity(claims):
    from .auth import require_session_marker
    from .session_routes import _session_payload, _identity_from_session_payload
    sid = claims.get("session_id") or claims.get("sub")
    runid = claims.get("runid")
    if not isinstance(sid, str) or not isinstance(runid, str):
        return None
    try:
        require_session_marker(claims, runid)
        return _identity_from_session_payload(_session_payload(sid))[0]
    except AuthError:
        return None


def verified_principal(claims):
    if claims is None:
        return VerifiedPrincipal()
    from .session_routes import _resolve_user_id_from_fs_uniquifier
    try:
        return principal_from_verified_claims(
            claims, legacy_session_identity=_legacy_session_identity,
            mcp_identity=_resolve_user_id_from_fs_uniquifier,
        )
    except (SQLAlchemyError, FeatureIdentityConfigurationError) as exc:
        logger.exception("Feature identity database unavailable")
        raise AuthError("Feature access is temporarily unavailable.", status_code=503,
                        code="feature_access_unavailable") from exc


def require_feature_access(claims, feature_id, *, runid=None, operation="act",
                           protected_read=False):
    from wepppy.weppcloud.utils.helpers import get_wd
    context = resource_context(get_wd(runid) if runid is not None else None,
                               protected_read=protected_read)
    public_inspection = operation == "inspect" and not protected_read
    principal = VerifiedPrincipal() if public_inspection else verified_principal(claims)
    decision = decide(principal, feature_id, operation, context)
    if not decision.allowed:
        raise AuthError("Feature access denied: " + decision.reason.replace("_", " ") + ".",
                        status_code=decision_status(decision), code=decision.reason)
    return principal


def require_workflow_access(claims, runid, *, operation):
    from wepppy.weppcloud.utils.feature_access_runtime import workflow_features
    from wepppy.nodb.base import NoDbBase
    from wepppy.weppcloud.utils.helpers import get_wd
    for feature_id in workflow_features(runid):
        if operation == "inspect" and feature_id == "batch_runner" and NoDbBase.ispublic(get_wd(runid)):
            continue
        require_feature_access(claims, feature_id, runid=runid, operation=operation,
                               protected_read=True)
