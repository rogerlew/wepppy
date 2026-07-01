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
from flask_security import url_for_security


security_bp = Blueprint("security_ui", __name__)


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
