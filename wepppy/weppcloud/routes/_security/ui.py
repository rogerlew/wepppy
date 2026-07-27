"""Custom authentication blueprint wrapping Flask-Security views."""

import os

from .._common import (
    Blueprint,
    abort,
    current_app,
    current_user,
    login_required,
    render_template,
)
from flask import request, session
from flask_login.utils import decode_cookie
from flask_security import url_for_security


security_bp = Blueprint("security_ui", __name__)


@security_bp.before_app_request
def refresh_presented_remember_cookie():
    """Refresh only a valid remember credential already carried by the browser."""
    if (
        request.method == "POST"
        and request.endpoint in {"security.login", "security_ui.login"}
        and "remember" not in request.form
    ):
        # A valid remember cookie authenticates before Flask-Security constructs
        # the login form. Clear it here so an explicit opt-out remains effective.
        session["_remember"] = "clear"
        return

    if not current_user.is_authenticated:
        return

    cookie_name = current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    token = request.cookies.get(cookie_name)
    if not token:
        return

    token_identity = decode_cookie(token)
    if token_identity and token_identity == current_user.get_id():
        session["_remember"] = "set"


@security_bp.after_app_request
def clear_logged_out_session(response):
    """Expire server-side session state after Flask-Security handles logout."""
    if request.endpoint == "security.logout":
        session.clear()
        session["_remember"] = "clear"
        response.delete_cookie(
            current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token"),
            path=current_app.config.get("REMEMBER_COOKIE_PATH", "/"),
            domain=current_app.config.get("REMEMBER_COOKIE_DOMAIN"),
            secure=current_app.config.get("REMEMBER_COOKIE_SECURE", False),
            httponly=current_app.config.get("REMEMBER_COOKIE_HTTPONLY", True),
            samesite=current_app.config.get("REMEMBER_COOKIE_SAMESITE"),
        )
    return response


@security_bp.route("/login", methods=["GET", "POST"], strict_slashes=False)
def login():
    view = current_app.view_functions.get("security.login")
    if not view:
        current_app.logger.error("Flask-Security login view missing; unable to serve login page")
        abort(404)
    return current_app.ensure_sync(view)()

@security_bp.route("/welcome", methods=["GET"], strict_slashes=False)
@login_required
def welcome():
    return render_template("security/welcome.html", user=current_user)


@security_bp.route("/goodbye", methods=["GET"], strict_slashes=False)
def goodbye():
    return render_template("security/goodbye.html")


@security_bp.app_context_processor
def inject_auth_context():
    cap_base_url = (
        current_app.config.get("CAP_BASE_URL")
        or os.getenv("CAP_BASE_URL", "/cap")
    ).rstrip("/")
    cap_asset_base_url = (
        current_app.config.get("CAP_ASSET_BASE_URL")
        or os.getenv("CAP_ASSET_BASE_URL", f"{cap_base_url}/assets")
    ).rstrip("/")
    cap_site_key = (
        current_app.config.get("CAP_SITE_KEY")
        or os.getenv("CAP_SITE_KEY", "")
    ).strip("/")

    return {
        "auth_login_url": url_for_security("login"),
        "auth_logout_url": url_for_security("logout"),
        "cap_base_url": cap_base_url,
        "cap_asset_base_url": cap_asset_base_url,
        "cap_site_key": cap_site_key,
    }


__all__ = ["security_bp"]
