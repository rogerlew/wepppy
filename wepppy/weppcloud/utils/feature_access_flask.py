"""Flask feature decisions, separate from ordinary project authorization."""
import flask
import flask_security
from sqlalchemy.exc import SQLAlchemyError

from .feature_access import VerifiedPrincipal
from .feature_access_identity import account_principal
from .feature_access_runtime import decide, decision_status, resource_context


def current_principal():
    user = flask_security.current_user
    if not user or not user.is_authenticated or not user.is_active:
        return VerifiedPrincipal()
    return account_principal(user.id, engine=flask.current_app.extensions["sqlalchemy"].engine)


def feature_decision(feature_id, *, wd=None, operation="act", protected_read=False,
                     consumes_contrasts=False, check_capabilities=True):
    from .feature_access import FeatureAccessDecision
    from .feature_access_store import FeatureAccessStore
    context = resource_context(wd, protected_read=protected_read, consumes_contrasts=consumes_contrasts,
                               check_capabilities=check_capabilities)
    # Anonymous/public inspection has no account dependency.
    if operation == "inspect" and not protected_read and not consumes_contrasts and feature_id != "omni_contrasts":
        return decide(VerifiedPrincipal(), feature_id, operation, context)
    try:
        return decide(current_principal(), feature_id, operation, context,
                      store=_FlaskStore())
    except SQLAlchemyError:
        flask.current_app.logger.exception("Feature identity lookup unavailable")
        return FeatureAccessDecision(False, "feature_access_unavailable")


class _FlaskStore:
    def membership(self, *args, **kwargs):
        from .feature_access_store import FeatureAccessStore
        return FeatureAccessStore(flask.current_app.extensions["sqlalchemy"].engine).membership(*args, **kwargs)


def require_feature(feature_id, **kwargs):
    decision = feature_decision(feature_id, **kwargs)
    if not decision.allowed:
        response = flask.jsonify({"error": {"code": decision.reason,
                                            "message": decision.reason}})
        response.status_code = decision_status(decision)
        flask.abort(response)
    return decision
