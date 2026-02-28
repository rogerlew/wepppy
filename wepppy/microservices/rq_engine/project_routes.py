from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Mapping, Sequence

import requests
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from wepppy.config.secrets import get_secret
from wepppy.nodb.core import Ron
from wepppy.weppcloud.routes.readme_md import ensure_readme_on_create
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.weppcloud.utils.runid import generate_runid

from .auth import AuthError, _check_revocation, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_CREATE_SCOPES = ["rq:enqueue"]


class CapVerificationError(RuntimeError):
    """Raised when CAPTCHA verification fails or cannot be performed."""


def _normalize_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    trimmed = prefix.strip()
    if not trimmed or trimmed == "/":
        return ""
    return "/" + trimmed.strip("/")


def _site_prefix() -> str:
    return _normalize_prefix(os.getenv("SITE_PREFIX", "/weppcloud"))


def _run_url(runid: str, config: str) -> str:
    prefix = _site_prefix()
    path = f"/runs/{runid}/{config}"
    return f"{prefix}{path}" if prefix else path


def _resolve_cap_config(request: Request) -> tuple[str, str, str]:
    base_url = os.getenv("CAP_BASE_URL")
    site_key = os.getenv("CAP_SITE_KEY")
    secret = get_secret("CAP_SECRET")

    if not base_url:
        raise CapVerificationError("CAP_BASE_URL is required for CAPTCHA verification.")
    if not site_key:
        raise CapVerificationError("CAP_SITE_KEY is required for CAPTCHA verification.")
    if not secret:
        raise CapVerificationError("CAP_SECRET is required for CAPTCHA verification.")

    base_url = base_url.rstrip("/")
    if base_url.startswith("/"):
        base_url = f"{request.url.scheme}://{request.url.netloc}{base_url}"

    return base_url, site_key, secret


def _verify_cap_token(request: Request, token: str) -> Mapping[str, Any]:
    if not token:
        raise CapVerificationError("CAP token is required for verification.")

    base_url, site_key, secret = _resolve_cap_config(request)
    verify_url = f"{base_url}/{site_key}/siteverify"

    try:
        response = requests.post(
            verify_url,
            json={"secret": secret, "response": token},
            timeout=6,
        )
    except requests.RequestException as exc:
        raise CapVerificationError(f"CAP siteverify request failed: {exc}") from exc

    if response.status_code != 200:
        raise CapVerificationError(f"CAP siteverify returned status {response.status_code}.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise CapVerificationError("CAP siteverify returned invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise CapVerificationError("CAP siteverify returned unexpected payload.")

    return payload


def _normalize_scopes(raw: Any, separator: str) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {scope for scope in raw.split(separator) if scope}
    if isinstance(raw, Sequence):
        scopes: set[str] = set()
        for item in raw:
            if isinstance(item, str):
                scopes.update(scope for scope in item.split(separator) if scope)
        return scopes
    return set()


def _require_rq_token(token: str, *, required_scopes: Sequence[str]) -> Mapping[str, Any]:
    audience = (os.getenv("RQ_ENGINE_JWT_AUDIENCE") or "rq-engine").strip() or None

    try:
        claims = auth_tokens.decode_token(token, audience=audience)
    except auth_tokens.JWTConfigurationError as exc:
        raise AuthError(f"JWT configuration error: {exc}", status_code=500) from exc
    except auth_tokens.JWTDecodeError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc

    _check_revocation(str(claims.get("jti") or ""))

    scope_separator = auth_tokens.get_jwt_config().scope_separator
    scopes = _normalize_scopes(claims.get("scope"), scope_separator)
    missing = [scope for scope in required_scopes if scope not in scopes]
    if missing:
        raise AuthError(
            f"Token missing required scope(s): {', '.join(missing)}",
            status_code=403,
            code="forbidden",
        )

    return claims


def _create_run_dir(user_email: str | None) -> tuple[str, str]:
    runs_root = "/wc1/runs"
    if not os.path.exists(runs_root):
        os.makedirs(runs_root, exist_ok=True)
    if not os.path.isdir(runs_root):
        raise RuntimeError(f"Runs root is not a directory: {runs_root}")
    if not os.access(runs_root, os.W_OK | os.X_OK):
        raise PermissionError(f"Runs root is not writable: {runs_root}")

    while True:
        runid = generate_runid(user_email or "")
        wd = get_wd(runid)
        if os.path.exists(wd):
            continue
        os.makedirs(wd)
        return runid, wd


def _resolve_user_from_claims(claims: Mapping[str, Any] | None) -> Any | None:
    if not claims:
        return None

    subject = claims.get("sub")
    email = claims.get("email")

    try:
        from wepppy.weppcloud.app import User, app as flask_app
    except ImportError:
        logger.exception("Unable to import weppcloud app for user lookup")
        return None

    with flask_app.app_context():
        user = None
        if subject:
            subject_str = str(subject).strip()
            if subject_str:
                if subject_str.isdigit():
                    user = User.query.get(int(subject_str))
                if user is None:
                    user = User.query.filter_by(fs_uniquifier=subject_str).first()
        if user is None and email:
            user = User.query.filter_by(email=str(email)).first()
        return user


def _register_run_owner(runid: str, config: str, user: Any | None) -> None:
    if user is None:
        return
    try:
        from wepppy.weppcloud.app import user_datastore, app as flask_app
    except ImportError:
        logger.exception("Unable to import weppcloud app for run ownership")
        return

    with flask_app.app_context():
        user_datastore.create_run(runid, config, user)


def _collect_overrides(payload: Mapping[str, Any], query_params: Mapping[str, Any]) -> str:
    data: dict[str, Any] = {}
    for key, value in query_params.items():
        data[key] = value
    for key, value in payload.items():
        data[key] = value

    overrides: list[str] = []
    for key, value in data.items():
        if key in {"cap_token", "rq_token", "config"}:
            continue
        if value is None or value == "":
            continue
        if isinstance(value, (list, tuple)) and value:
            value = value[0]
        if isinstance(value, bool):
            serialized = "true" if value else "false"
        else:
            serialized = str(value)
        overrides.append(f"{key}={serialized}")

    return "&".join(overrides)


@router.post(
    "/create/",
    summary="Create a new run",
    description=(
        "Supports `rq_token`, Bearer auth (`rq:enqueue`), or CAPTCHA verification. "
        "Synchronously creates run directory/config metadata and responds with a redirect to the new run URL."
    ),
    tags=["rq-engine", "project"],
    operation_id=rq_operation_id("create"),
    responses=agent_route_responses(
        success_code=303,
        success_description="Run created and redirect issued to the new run URL.",
        extra={
            400: "Create payload validation failed. Returns the canonical error payload.",
        },
    ),
)
async def create(request: Request) -> Response:
    try:
        payload = await parse_request_payload(request)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine create payload parse failed")
        return error_response_with_traceback("Invalid payload", status_code=400)

    config = str(payload.get("config") or "").strip()
    if not config:
        return error_response("config is required", status_code=400, code="validation_error")

    rq_token = str(payload.get("rq_token") or "").strip()
    cap_token = str(payload.get("cap_token") or "").strip()
    claims: Mapping[str, Any] | None = None

    if rq_token:
        try:
            claims = await asyncio.to_thread(
                _require_rq_token,
                rq_token,
                required_scopes=RQ_CREATE_SCOPES,
            )
        except AuthError as exc:
            return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    elif "authorization" in {key.lower() for key in request.headers.keys()}:
        try:
            claims = await asyncio.to_thread(
                require_jwt,
                request,
                required_scopes=RQ_CREATE_SCOPES,
            )
        except AuthError as exc:
            return error_response(exc.message, status_code=exc.status_code, code=exc.code)
        except Exception:  # broad-except: boundary contract
            logger.exception("rq-engine create auth failed")
            return error_response_with_traceback("Failed to authorize request", status_code=401)
    else:
        if not cap_token:
            return error_response("CAPTCHA token is required.", status_code=403)
        try:
            verification = await asyncio.to_thread(_verify_cap_token, request, cap_token)
        except CapVerificationError as exc:
            logger.error("CAPTCHA verification error for create/%s: %s", config, exc)
            return error_response("CAPTCHA verification failed.", status_code=500)
        if not verification.get("success"):
            logger.warning(
                "CAPTCHA rejected for create/%s (errors=%s)",
                config,
                verification.get("error-codes"),
            )
            return error_response("CAPTCHA verification failed.", status_code=403)

    cfg = f"{config}.cfg"
    overrides = _collect_overrides(payload, request.query_params)
    if overrides:
        cfg = f"{cfg}?{overrides}"

    def _create_run_blocking() -> str | Response:
        user = None
        try:
            user = _resolve_user_from_claims(claims)
        except Exception:  # broad-except: boundary contract
            logger.exception("rq-engine create user lookup failed")

        try:
            runid, wd = _create_run_dir(getattr(user, "email", None) if user else None)
        except PermissionError as exc:
            logger.exception("rq-engine create run directory permission error")
            return error_response(
                "Could not create run directory. NAS may be down.",
                details=str(exc),
            )
        except Exception as exc:  # broad-except: boundary contract
            logger.exception("rq-engine create run directory failed")
            return error_response(
                "Could not create run directory.",
                details=str(exc),
            )

        try:
            Ron(wd, cfg)
        except Exception:  # broad-except: boundary contract
            logger.exception("rq-engine create Ron failed")
            return error_response("Could not create run")

        try:
            from wepppy.weppcloud.utils.run_ttl import initialize_ttl

            initialize_ttl(wd)
        except Exception:  # broad-except: boundary contract
            logger.exception("rq-engine create TTL initialization failed")

        try:
            _register_run_owner(runid, config, user)
        except Exception:  # broad-except: boundary contract
            logger.exception("rq-engine create run owner failed")

        try:
            ensure_readme_on_create(runid, config)
        except Exception:  # broad-except: boundary contract
            logger.exception("rq-engine create README failed")

        return runid

    create_result = await asyncio.to_thread(_create_run_blocking)
    if isinstance(create_result, Response):
        return create_result

    return RedirectResponse(_run_url(create_result, config), status_code=303)


__all__ = ["router"]
