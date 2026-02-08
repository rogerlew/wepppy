"""Shared Bootstrap route helpers used by Flask and rq-engine."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlsplit

import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Wepp
from wepppy.weppcloud.bootstrap.enable_jobs import BootstrapLockBusyError, enqueue_bootstrap_enable
from wepppy.weppcloud.bootstrap.git_lock import (
    acquire_bootstrap_git_lock,
    release_bootstrap_git_lock,
)
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.helpers import get_wd

_GIT_PATH_RE = re.compile(
    r"^/(?:git/)?(?P<prefix>[A-Za-z0-9]{2})/(?P<runid>[A-Za-z0-9][A-Za-z0-9._-]*)/\.git(?:/.*)?$"
)


@dataclass(frozen=True)
class BootstrapOperationResult:
    payload: dict[str, Any]
    status_code: int = 200


@dataclass(frozen=True)
class BootstrapForwardAuthContext:
    runid: str
    email: str


class BootstrapOperationError(ValueError):
    """Raised for expected bootstrap contract errors."""

    def __init__(self, message: str, *, status_code: int = 400, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def decode_basic_auth(auth_header: str | None) -> tuple[str, str] | None:
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


def parse_forwarded_git_path(forwarded_path: str) -> tuple[str, str]:
    decoded_path = unquote(urlsplit(forwarded_path).path or "")
    if not decoded_path:
        raise BootstrapOperationError("invalid git path", status_code=401)
    if "\\" in decoded_path:
        raise BootstrapOperationError("invalid git path", status_code=401)
    parts = [part for part in decoded_path.split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise BootstrapOperationError("invalid git path", status_code=401)

    match = _GIT_PATH_RE.fullmatch(decoded_path)
    if not match:
        raise BootstrapOperationError("invalid git path", status_code=401)
    return match.group("prefix"), match.group("runid")


def verify_forward_auth_context(
    *,
    auth_header: str | None,
    forwarded_path: str | None,
    external_host: str | None,
) -> BootstrapForwardAuthContext:
    auth = decode_basic_auth(auth_header)
    if not auth:
        raise BootstrapOperationError("missing authorization", status_code=401)
    _ignored_user_id, token = auth

    if not forwarded_path:
        raise BootstrapOperationError("missing forwarded path", status_code=401)

    prefix, runid = parse_forwarded_git_path(forwarded_path)
    if len(runid) < 2 or prefix != runid[:2]:
        raise BootstrapOperationError("run prefix mismatch", status_code=401)

    if not external_host:
        raise BootstrapOperationError("missing external host", status_code=401)

    try:
        claims = auth_tokens.decode_token(token, audience=external_host)
    except Exception as exc:
        raise BootstrapOperationError(f"invalid token: {exc}", status_code=401) from exc

    if claims.get("runid") != runid:
        raise BootstrapOperationError("runid mismatch", status_code=401)

    email = claims.get("sub")
    if not isinstance(email, str) or not email:
        raise BootstrapOperationError("missing subject", status_code=401)

    return BootstrapForwardAuthContext(runid=runid, email=email)


def _resolve_run_record(runid: str) -> Any | None:
    from wepppy.weppcloud.app import Run, app as flask_app

    with flask_app.app_context():
        return Run.query.filter(Run.runid == runid).first()


def _resolve_user_by_email(email: str) -> Any | None:
    from sqlalchemy import func
    from wepppy.weppcloud.app import User, app as flask_app

    with flask_app.app_context():
        return User.query.filter(func.lower(User.email) == email.lower()).first()


def user_has_run_access(user: Any, run: Any) -> bool:
    if user is None or run is None:
        return False
    try:
        for role_name in ("Admin", "Root"):
            if user.has_role(role_name):
                return True
    except Exception:
        pass

    if getattr(run, "owner_id", None) and str(run.owner_id) == str(getattr(user, "id", "")):
        return True

    try:
        return user in run.users
    except Exception:
        return False


def ensure_bootstrap_eligibility(
    runid: str,
    *,
    require_owner: bool,
    enforce_not_disabled: bool = True,
    email: str | None = None,
    require_user_access: bool = False,
) -> tuple[Any, Any | None]:
    run = _resolve_run_record(runid)
    if run is None:
        raise BootstrapOperationError("run not found", status_code=400)

    if enforce_not_disabled and bool(getattr(run, "bootstrap_disabled", False)):
        raise BootstrapOperationError("bootstrap disabled", status_code=400)

    if require_owner and not getattr(run, "owner_id", None):
        raise BootstrapOperationError("anonymous runs cannot enable bootstrap", status_code=400)

    if email is None:
        return run, None

    user = _resolve_user_by_email(email)
    if user is None:
        raise BootstrapOperationError("user not found", status_code=400)

    if require_user_access and not user_has_run_access(user, run):
        raise BootstrapOperationError("user does not have access to run", status_code=400)

    return run, user


def bootstrap_wd(runid: str) -> str:
    return get_wd(runid, prefer_active=False)


def ensure_bootstrap_opt_in(runid: str) -> Wepp:
    wd = bootstrap_wd(runid)
    wepp = Wepp.getInstance(wd)
    if not wepp.bootstrap_enabled:
        raise BootstrapOperationError("bootstrap not enabled", status_code=400)
    return wepp


def bootstrap_status_url(job_id: str) -> str:
    return f"/rq-engine/api/jobstatus/{job_id}"


def enable_bootstrap_operation(
    runid: str,
    *,
    actor: str,
    email: str | None = None,
    require_user_access: bool = False,
) -> BootstrapOperationResult:
    ensure_bootstrap_eligibility(
        runid,
        require_owner=True,
        enforce_not_disabled=True,
        email=email,
        require_user_access=require_user_access,
    )
    try:
        payload, status_code = enqueue_bootstrap_enable(runid, actor=actor)
    except BootstrapLockBusyError as exc:
        raise BootstrapOperationError(str(exc), status_code=409, code="conflict") from exc
    job_id = str(payload.get("job_id") or "").strip()
    if job_id:
        payload["status_url"] = bootstrap_status_url(job_id)
    return BootstrapOperationResult(payload=payload, status_code=status_code)


def mint_bootstrap_token_operation(
    runid: str,
    *,
    user_email: str,
    user_id: str,
    require_user_access: bool = False,
) -> BootstrapOperationResult:
    if not user_email or not user_id:
        raise BootstrapOperationError(
            "User identity claims are required to mint bootstrap tokens",
            status_code=403,
            code="forbidden",
        )

    ensure_bootstrap_eligibility(
        runid,
        require_owner=True,
        enforce_not_disabled=True,
        email=user_email if require_user_access else None,
        require_user_access=require_user_access,
    )
    wepp = ensure_bootstrap_opt_in(runid)
    return BootstrapOperationResult(payload={"clone_url": wepp.mint_bootstrap_jwt(user_email, user_id)})


def bootstrap_commits_operation(runid: str) -> BootstrapOperationResult:
    ensure_bootstrap_eligibility(
        runid,
        require_owner=False,
        enforce_not_disabled=False,
    )
    wepp = ensure_bootstrap_opt_in(runid)
    return BootstrapOperationResult(payload={"commits": wepp.get_bootstrap_commits()})


def bootstrap_current_ref_operation(runid: str) -> BootstrapOperationResult:
    ensure_bootstrap_eligibility(
        runid,
        require_owner=False,
        enforce_not_disabled=False,
    )
    wepp = ensure_bootstrap_opt_in(runid)
    return BootstrapOperationResult(payload={"ref": wepp.get_bootstrap_current_ref()})


def bootstrap_checkout_operation(
    runid: str,
    *,
    sha: str,
    actor: str,
) -> BootstrapOperationResult:
    sha_text = str(sha or "").strip()
    if not sha_text:
        raise BootstrapOperationError("sha required", status_code=400)

    ensure_bootstrap_eligibility(
        runid,
        require_owner=False,
        enforce_not_disabled=False,
    )
    wepp = ensure_bootstrap_opt_in(runid)

    lock_conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
    with redis.Redis(**lock_conn_kwargs) as lock_conn:
        lock = acquire_bootstrap_git_lock(
            lock_conn,
            runid=runid,
            operation="checkout",
            actor=actor,
        )
        if lock is None:
            raise BootstrapOperationError("bootstrap lock busy", status_code=409, code="conflict")
        try:
            if not wepp.checkout_bootstrap_commit(sha_text):
                raise BootstrapOperationError("checkout failed", status_code=400)
        finally:
            release_bootstrap_git_lock(lock_conn, runid=runid, token=lock.token)

    return BootstrapOperationResult(payload={"checked_out": sha_text})


__all__ = [
    "BootstrapForwardAuthContext",
    "BootstrapOperationError",
    "BootstrapOperationResult",
    "bootstrap_checkout_operation",
    "bootstrap_commits_operation",
    "bootstrap_current_ref_operation",
    "bootstrap_status_url",
    "bootstrap_wd",
    "decode_basic_auth",
    "enable_bootstrap_operation",
    "ensure_bootstrap_eligibility",
    "ensure_bootstrap_opt_in",
    "mint_bootstrap_token_operation",
    "parse_forwarded_git_path",
    "user_has_run_access",
    "verify_forward_auth_context",
]
