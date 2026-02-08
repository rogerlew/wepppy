"""Bootstrap routes for git-backed input workflows."""

from __future__ import annotations

import base64
import re
from typing import Any, Tuple
from urllib.parse import unquote, urlsplit

from ._common import *  # noqa: F401,F403

from wepppy.nodb.core import Wepp
from wepppy.weppcloud.utils import auth_tokens

bootstrap_bp = Blueprint("bootstrap", __name__)


_GIT_PATH_RE = re.compile(
    r"^/git/(?P<prefix>[A-Za-z0-9]{2})/(?P<runid>[A-Za-z0-9][A-Za-z0-9._-]*)/\.git(?:/.*)?$"
)


def _get_external_host() -> str | None:
    host = current_app.config.get("OAUTH_REDIRECT_HOST") or current_app.config.get("EXTERNAL_HOST")
    if host:
        return str(host)
    forwarded_host = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
    if forwarded_host:
        return forwarded_host.split(":")[0] or None
    return (request.host or "").split(":")[0] or None


def _decode_basic_auth(auth_header: str | None) -> Tuple[str, str] | None:
    if not auth_header:
        return None
    if not auth_header.lower().startswith("basic "):
        return None
    encoded = auth_header.split(None, 1)[1].strip()
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return None
    if ":" not in decoded:
        return None
    user_id, token = decoded.split(":", 1)
    return user_id, token


def _resolve_run_record(runid: str):
    from wepppy.weppcloud.app import Run

    return Run.query.filter(Run.runid == runid).first()


def _resolve_user_by_email(email: str):
    from sqlalchemy import func
    from wepppy.weppcloud.app import User

    return User.query.filter(func.lower(User.email) == email.lower()).first()


def _user_has_run_access(user: Any, run: Any) -> bool:
    if user is None or run is None:
        return False
    try:
        for role_name in ("Admin", "Root"):
            if user.has_role(role_name):
                return True
    except Exception:
        pass

    if run.owner_id and str(run.owner_id) == str(user.id):
        return True

    try:
        return user in run.users
    except Exception:
        return False


def _reject(message: str, status_code: int = 401):
    response = make_response(message, status_code)
    if status_code == 401:
        response.headers["WWW-Authenticate"] = 'Basic realm="Bootstrap"'
    return response


def _parse_forwarded_git_path(forwarded_path: str) -> Tuple[str, str]:
    decoded_path = unquote(urlsplit(forwarded_path).path or "")
    if not decoded_path:
        raise ValueError("invalid git path")
    if "\\" in decoded_path:
        raise ValueError("invalid git path")
    parts = [part for part in decoded_path.split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise ValueError("invalid git path")

    match = _GIT_PATH_RE.fullmatch(decoded_path)
    if not match:
        raise ValueError("invalid git path")
    return match.group("prefix"), match.group("runid")


def _validate_bootstrap_eligibility(runid: str, email: str) -> Tuple[Any, Any]:
    run = _resolve_run_record(runid)
    if run is None:
        raise ValueError("run not found")
    if getattr(run, "bootstrap_disabled", False):
        raise ValueError("bootstrap disabled")
    if not run.owner_id:
        raise ValueError("anonymous runs cannot enable bootstrap")

    user = _resolve_user_by_email(email)
    if user is None:
        raise ValueError("user not found")
    if not _user_has_run_access(user, run):
        raise ValueError("user does not have access to run")

    return run, user


def _ensure_bootstrap_opt_in(runid: str) -> None:
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    if not wepp.bootstrap_enabled:
        raise ValueError("bootstrap not enabled")


@bootstrap_bp.route("/api/bootstrap/verify-token", methods=["GET", "POST"])
def verify_token():
    auth = _decode_basic_auth(request.headers.get("Authorization"))
    if not auth:
        return _reject("missing authorization")
    _user_id, token = auth

    forwarded_path = request.headers.get("X-Forwarded-Uri") or request.headers.get("X-Original-Uri")
    if not forwarded_path:
        return _reject("missing forwarded path")
    try:
        prefix, runid = _parse_forwarded_git_path(forwarded_path)
    except ValueError as exc:
        return _reject(str(exc))
    if len(runid) < 2 or prefix != runid[:2]:
        return _reject("run prefix mismatch")

    external_host = _get_external_host()
    if not external_host:
        return _reject("missing external host")

    try:
        claims = auth_tokens.decode_token(token, audience=external_host)
    except Exception as exc:
        return _reject(f"invalid token: {exc}")

    token_runid = claims.get("runid")
    if token_runid != runid:
        return _reject("runid mismatch")

    email = claims.get("sub")
    if not isinstance(email, str) or not email:
        return _reject("missing subject")

    try:
        _validate_bootstrap_eligibility(runid, email)
        _ensure_bootstrap_opt_in(runid)
    except ValueError as exc:
        return _reject(str(exc))
    except Exception as exc:
        current_app.logger.exception("bootstrap verify-token failed")
        return _reject(str(exc))

    response = make_response("", 200)
    response.headers["X-Auth-User"] = email
    return response


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/enable", methods=["POST"])
@login_required
def enable_bootstrap(runid: str, config: str):
    authorize(runid, config)
    try:
        _validate_bootstrap_eligibility(runid, current_user.email)
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        if not wepp.bootstrap_enabled:
            wepp.init_bootstrap()
        return success_factory({"enabled": True})
    except Exception as exc:
        return error_factory(str(exc))


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/mint-token", methods=["POST"])
@login_required
def mint_bootstrap_token(runid: str, config: str):
    authorize(runid, config)
    try:
        _validate_bootstrap_eligibility(runid, current_user.email)
        _ensure_bootstrap_opt_in(runid)
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        clone_url = wepp.mint_bootstrap_jwt(current_user.email, str(current_user.id))
        return success_factory({"clone_url": clone_url})
    except Exception as exc:
        return error_factory(str(exc))


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/commits", methods=["GET"])
@login_required
def bootstrap_commits(runid: str, config: str):
    authorize(runid, config)
    try:
        _ensure_bootstrap_opt_in(runid)
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        return success_factory({"commits": wepp.get_bootstrap_commits()})
    except Exception as exc:
        return error_factory(str(exc))


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/checkout", methods=["POST"])
@login_required
def bootstrap_checkout(runid: str, config: str):
    authorize(runid, config)
    sha = (request.json or {}).get("sha")
    if not sha:
        return error_factory("sha required")
    try:
        _ensure_bootstrap_opt_in(runid)
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        if not wepp.checkout_bootstrap_commit(str(sha)):
            return error_factory("checkout failed")
        return success_factory({"checked_out": str(sha)})
    except Exception as exc:
        return error_factory(str(exc))


@bootstrap_bp.route("/runs/<string:runid>/<config>/bootstrap/current-ref", methods=["GET"])
@login_required
def bootstrap_current_ref(runid: str, config: str):
    authorize(runid, config)
    try:
        _ensure_bootstrap_opt_in(runid)
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        return success_factory({"ref": wepp.get_bootstrap_current_ref()})
    except Exception as exc:
        return error_factory(str(exc))


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
            return error_factory("run not found")
        run.bootstrap_disabled = bool(disabled)
        db.session.commit()
        return success_factory({"bootstrap_disabled": run.bootstrap_disabled})
    except Exception as exc:
        return error_factory(str(exc))


__all__ = ["bootstrap_bp"]
