"""Session-only FA-01 transport and read models; no feature endpoint admission."""
from datetime import datetime, timedelta
from functools import wraps
from uuid import uuid4

import flask
import flask_security
from flask_security.utils import get_request_attr
from sqlalchemy.exc import SQLAlchemyError

from wepppy.weppcloud.feature_registry import FeatureRegistryValidationError, load_feature_registry
from .feature_access_store import (
    FeatureAccessConflict,
    FeatureAccessStore,
    FeatureAccessUnavailableError,
    FeatureAccessValidationError,
)

__all__ = [
    "INTERNAL_STATEMENT_VERSION", "INTERNAL_STATEMENT", "POWERUSER_STATEMENT_VERSION",
    "POWERUSER_STATEMENT", "access_store", "access_error",
    "access_unavailable", "access_errors", "access_boundary", "json_fields", "utc_timestamp",
    "profile_access", "membership_change", "acknowledge_internal", "approve_poweruser",
]

from .feature_access_identity import INTERNAL_STATEMENT_VERSION
INTERNAL_STATEMENT = (
    "Internal WEPPcloud access may include experimental, preview, restricted, or publication-embargoed "
    "functionality. Access is granted only for the approved feature, purpose, and time period. Outputs "
    "may be incomplete, unstable, or unsuitable for publication or management decisions without "
    "additional review. You are responsible for documenting versions, inputs, assumptions, limitations, "
    "and maturity status. If results appear anomalous or scientifically important, notify the WEPPcloud "
    "project contact before public release when practical. Internal access does not imply authorship "
    "rights, publication approval, or access to unrelated features. Authorship and acknowledgment "
    "should be discussed early when WEPPcloud personnel provide substantial intellectual, scientific, "
    "technical, or interpretive contributions."
)
POWERUSER_STATEMENT_VERSION = "poweruser-2026-10-01"
POWERUSER_DECISION_RULE = "automatic-two-affirmative-answers-v1"
POWERUSER_STATEMENT = (
    "PowerUser workflows may expose advanced WEPPcloud features, larger jobs, or less commonly used "
    "model configurations. The general WEPPcloud user contract continues to apply. WEPPcloud outputs "
    "are model-based estimates, not measurements or guarantees. Results depend on input data, assumptions, "
    "parameterization, model structure, and watershed/domain suitability. You are responsible for "
    "reviewing inputs, configuration, parameterization, assumptions, and outputs; independently validating "
    "results as appropriate for your use case; and documenting versions, inputs, and limitations when results "
    "are shared or published. Preview or experimental functionality may change, produce unexpected results, "
    "or require additional interpretation. Elevated access may be limited, reviewed, or removed to protect "
    "system reliability, storage, compute capacity, or scientific integrity. PowerUser access does not authorize "
    "internal actions or access to private resources unless separately granted; public read-only views follow "
    "the sharing policy."
)


def access_store():
    return FeatureAccessStore(flask.current_app.extensions["sqlalchemy"].engine)


def access_error(code, message, status, *, error_id=None):
    body = {"error": {"code": code, "message": message, "details": message}}
    if error_id:
        body["error_id"] = error_id
    return flask.jsonify(body), status


def access_unavailable():
    error_id = uuid4().hex
    flask.current_app.logger.exception("Feature access unavailable error_id=%s", error_id)
    return access_error("feature_access_unavailable", "Feature access is temporarily unavailable. Please retry.",
                        503, error_id=error_id)


def access_errors(view):
    """Sanitize dependency failures, including authentication database reads."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except FeatureAccessConflict as exc:
            return access_error("membership_conflict", str(exc), 409)
        except FeatureAccessValidationError as exc:
            return access_error("validation_error", str(exc), 400)
        except PermissionError:
            return access_error("forbidden", "Root access is required.", 403)
        except (SQLAlchemyError, FeatureRegistryValidationError, FeatureAccessUnavailableError):
            return access_unavailable()
    return wrapped


def access_boundary(*, root=False):
    """Browser session boundary; CSRF remains owned by the global middleware."""
    def decorate(view):
        @wraps(view)
        @access_errors
        def wrapped(*args, **kwargs):
            # A stale session marker can fall through to Flask-Security's
            # token loader. Require the resolved identity's actual provenance.
            if (not flask_security.current_user.is_authenticated or not flask_security.current_user.is_active
                    or get_request_attr("fs_authn_via") != "session"
                    or flask.session.get("_user_id") != flask_security.current_user.get_id()):
                return access_error("unauthorized", "Sign in to continue.", 401)
            if root and not flask_security.current_user.has_role("Root"):
                return access_error("forbidden", "Root access is required.", 403)
            return view(*args, **kwargs)
        return wrapped
    return decorate


def json_fields(required, optional=()):
    if flask.request.mimetype != "application/json":
        raise FeatureAccessValidationError("Send an application/json object.")
    payload = flask.request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise FeatureAccessValidationError("A JSON object is required.")
    if set(payload) - set(required) - set(optional) or set(required) - set(payload):
        raise FeatureAccessValidationError("Unexpected or missing fields.")
    return payload


def utc_timestamp(value):
    if value is None:
        return None
    if not isinstance(value, str) or "T" not in value:
        raise FeatureAccessValidationError("Dates must be UTC timestamps, for example 2027-01-01T00:00:00Z.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeatureAccessValidationError("Invalid UTC timestamp.") from exc
    if result.utcoffset() != timedelta(0):
        raise FeatureAccessValidationError("Dates must include the UTC offset Z or +00:00.")
    return result


def profile_access():
    """Keep ordinary Profile usable, with an explicit unavailable subsection on DB failure."""
    result = {
        "version": INTERNAL_STATEMENT_VERSION,
        "statement": INTERNAL_STATEMENT,
        "poweruser_version": POWERUSER_STATEMENT_VERSION,
        "poweruser_statement": POWERUSER_STATEMENT,
    }
    try:
        result.update(access_store().account_status(
            flask_security.current_user.id,
            INTERNAL_STATEMENT_VERSION,
            poweruser_statement_version=POWERUSER_STATEMENT_VERSION,
        ))
    except SQLAlchemyError:
        error_id = uuid4().hex
        flask.current_app.logger.exception("Profile feature access unavailable error_id=%s", error_id)
        result["error_id"] = error_id
    return result


def membership_change():
    payload = json_fields({"operation", "user_id", "group_key", "reason"}, {"review_at", "expires_at"})
    if not isinstance(payload["operation"], str) or payload["operation"] not in {"add", "remove"}:
        raise FeatureAccessValidationError("Operation must be add or remove.")
    if not isinstance(payload["group_key"], str):
        raise FeatureAccessValidationError("Select a registered group.")
    if payload["operation"] == "remove" and {"review_at", "expires_at"} & payload.keys():
        raise FeatureAccessValidationError("Remove does not accept date fields.")
    result = access_store().change_membership_status(
        actor_id=flask_security.current_user.id, user_id=payload["user_id"], group_key=payload["group_key"],
        operation=payload["operation"], reason=payload["reason"], features=load_feature_registry(),
        review_at=utc_timestamp(payload.get("review_at")), expires_at=utc_timestamp(payload.get("expires_at")),
    )
    # Do not perform fallible DB work after commit and report an error for a saved decision.
    return flask.jsonify(message="Membership saved." if result["changed"] else "Membership already matches this decision.",
                   result={"user_id": payload["user_id"], "group_key": payload["group_key"],
                           **result})


def acknowledge_internal():
    payload = json_fields({"accepts_training", "statement_version"})
    if payload["accepts_training"] is not True:
        raise FeatureAccessValidationError("Read and accept the internal access statement.")
    if payload["statement_version"] != INTERNAL_STATEMENT_VERSION:
        return access_error("statement_version_conflict", "The statement has changed. Reload Profile and read it again.", 409)
    changed = access_store().acknowledge_internal(flask_security.current_user.id, INTERNAL_STATEMENT_VERSION)
    return flask.jsonify(message="Internal access statement accepted.", result={
        "statement_kind": "internal", "statement_version": INTERNAL_STATEMENT_VERSION, "changed": changed,
    })


def approve_poweruser():
    payload = json_fields({"needs_poweruser", "accepts_training", "statement_version"})
    if payload["needs_poweruser"] is not True or payload["accepts_training"] is not True:
        raise FeatureAccessValidationError("Answer yes to both PowerUser onboarding questions.")
    if not isinstance(payload["statement_version"], str):
        raise FeatureAccessValidationError("Statement version must be a string.")
    if payload["statement_version"] != POWERUSER_STATEMENT_VERSION:
        return access_error(
            "statement_version_conflict",
            "The statement has changed. Reload Profile and read it again.",
            409,
        )
    result = access_store().approve_poweruser(
        flask_security.current_user.id,
        POWERUSER_STATEMENT_VERSION,
        POWERUSER_DECISION_RULE,
    )
    message = "PowerUser access granted." if result["role_changed"] else "PowerUser access is already approved."
    return flask.jsonify(message=message, result={
        "status": result["status"],
        "role_changed": result["role_changed"],
        "statement_version": result["statement_version"],
    })
