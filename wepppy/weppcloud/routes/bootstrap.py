"""Bootstrap routes for git-backed input workflows."""

from __future__ import annotations

from ._common import *  # noqa: F401,F403

from wepppy.weppcloud.bootstrap.api_shared import (
    BootstrapOperationError,
    bootstrap_checkout_operation,
    bootstrap_commits_operation,
    bootstrap_current_ref_operation,
    enable_bootstrap_operation,
    ensure_bootstrap_eligibility,
    ensure_bootstrap_opt_in,
    mint_bootstrap_token_operation,
    verify_forward_auth_context,
)

bootstrap_bp = Blueprint("bootstrap", __name__)


def _get_external_host() -> str | None:
    host = current_app.config.get("OAUTH_REDIRECT_HOST") or current_app.config.get("EXTERNAL_HOST")
    if host:
        return str(host)
    forwarded_host = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
    if forwarded_host:
        return forwarded_host.split(":")[0] or None
    return (request.host or "").split(":")[0] or None


def _reject(message: str, status_code: int = 401):
    response = make_response(message, status_code)
    if status_code == 401:
        response.headers["WWW-Authenticate"] = 'Basic realm="Bootstrap"'
    return response


def _bootstrap_actor_for_current_user() -> str:
    user_id = getattr(current_user, "id", "unknown")
    email = str(getattr(current_user, "email", "") or "").strip().lower() or "unknown"
    return f"user:{user_id}:{email}"


@bootstrap_bp.route("/api/bootstrap/verify-token", methods=["GET", "POST"])
def verify_token():
    # CSRF exemption is applied in app bootstrap wiring because this endpoint
    # is consumed by Caddy forward_auth/git clients, not browser form posts.
    forwarded_path = request.headers.get("X-Forwarded-Uri") or request.headers.get("X-Original-Uri")

    try:
        context = verify_forward_auth_context(
            auth_header=request.headers.get("Authorization"),
            forwarded_path=forwarded_path,
            external_host=_get_external_host(),
        )
        ensure_bootstrap_eligibility(
            context.runid,
            require_owner=True,
            enforce_not_disabled=True,
            email=context.email,
            require_user_access=True,
        )
        ensure_bootstrap_opt_in(context.runid)
    except BootstrapOperationError as exc:
        # Keep Caddy forward_auth contract stable: all denials return 401.
        return _reject(exc.message, status_code=401)
    except Exception:
        current_app.logger.exception("bootstrap verify-token failed")
        return _reject("bootstrap verification failed")

    response = make_response("", 200)
    response.headers["X-Auth-User"] = context.email
    return response


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/enable", methods=["POST"])
@login_required
def enable_bootstrap(runid: str, config: str):
    authorize(runid, config)
    try:
        result = enable_bootstrap_operation(
            runid,
            actor=_bootstrap_actor_for_current_user(),
            email=str(getattr(current_user, "email", "") or "").strip(),
            require_user_access=True,
        )
        response = success_factory(result.payload)
        response.status_code = result.status_code
        return response
    except BootstrapOperationError as exc:
        return error_factory(exc.message, status_code=exc.status_code)
    except Exception:
        current_app.logger.exception("bootstrap enable failed for %s", runid)
        return error_factory("Error Handling Request", status_code=500)


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/mint-token", methods=["POST"])
@login_required
def mint_bootstrap_token(runid: str, config: str):
    authorize(runid, config)
    try:
        result = mint_bootstrap_token_operation(
            runid,
            user_email=str(getattr(current_user, "email", "") or "").strip(),
            user_id=str(getattr(current_user, "id", "") or "").strip(),
            require_user_access=True,
        )
        return success_factory(result.payload)
    except BootstrapOperationError as exc:
        return error_factory(exc.message, status_code=exc.status_code)
    except Exception:
        current_app.logger.exception("bootstrap mint-token failed for %s", runid)
        return error_factory("Error Handling Request", status_code=500)


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/commits", methods=["GET"])
@login_required
def bootstrap_commits(runid: str, config: str):
    authorize(runid, config)
    try:
        result = bootstrap_commits_operation(runid)
        return success_factory(result.payload)
    except BootstrapOperationError as exc:
        return error_factory(exc.message, status_code=exc.status_code)
    except Exception:
        current_app.logger.exception("bootstrap commits failed for %s", runid)
        return error_factory("Error Handling Request", status_code=500)


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/checkout", methods=["POST"])
@login_required
def bootstrap_checkout(runid: str, config: str):
    authorize(runid, config)
    payload = request.json or {}
    try:
        result = bootstrap_checkout_operation(
            runid,
            sha=payload.get("sha"),
            actor=_bootstrap_actor_for_current_user(),
        )
        return success_factory(result.payload)
    except BootstrapOperationError as exc:
        return error_factory(exc.message, status_code=exc.status_code)
    except Exception:
        current_app.logger.exception("bootstrap checkout failed for %s", runid)
        return error_factory("Error Handling Request", status_code=500)


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/current-ref", methods=["GET"])
@login_required
def bootstrap_current_ref(runid: str, config: str):
    authorize(runid, config)
    try:
        result = bootstrap_current_ref_operation(runid)
        return success_factory(result.payload)
    except BootstrapOperationError as exc:
        return error_factory(exc.message, status_code=exc.status_code)
    except Exception:
        current_app.logger.exception("bootstrap current-ref failed for %s", runid)
        return error_factory("Error Handling Request", status_code=500)


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/disable", methods=["POST"])
@roles_accepted("Admin", "Root")
def bootstrap_disable(runid: str, config: str):
    authorize(runid, config)
    payload = request.json or {}
    disabled = payload.get("disabled", True)
    try:
        from wepppy.weppcloud.app import Run, db

        run = Run.query.filter(Run.runid == runid).first()
        if run is None:
            return error_factory("run not found", status_code=404)
        run.bootstrap_disabled = bool(disabled)
        db.session.commit()
        return success_factory({"bootstrap_disabled": run.bootstrap_disabled})
    except Exception:
        current_app.logger.exception("bootstrap disable failed for %s", runid)
        return error_factory("Error Handling Request", status_code=500)


def register_csrf_exemptions(csrf) -> None:
    csrf.exempt(verify_token)


__all__ = ["bootstrap_bp", "register_csrf_exemptions"]
