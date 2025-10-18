"""OAuth login and linking routes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
import secrets
from typing import Any, Dict, Optional, Tuple

import re

from flask import flash, session
from flask_security import current_user
from flask_security.utils import login_user, hash_password
from flask_wtf.csrf import validate_csrf
from typing import TYPE_CHECKING
from wtforms.validators import ValidationError

from .._common import (
    Blueprint,
    abort,
    current_app,
    redirect,
    request,
    url_for,
)
from wepppy.weppcloud.utils.oauth import (
    build_pkce_pair,
    ensure_oauth_client,
    normalize_token_scopes,
    provider_enabled,
    utc_now,
)

if TYPE_CHECKING:
    from wepppy.weppcloud.app import OAuthAccount, User


logger = logging.getLogger("weppcloud.security.oauth")

security_oauth_bp = Blueprint("security_oauth", __name__)

_SESSION_PKCE_KEY = "oauth_pkce_verifier"
_SESSION_NEXT_KEY = "oauth_next"
_ORCID_ID_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9Xx]$")


def _get_provider_settings(provider: str) -> Optional[Dict[str, Any]]:
    providers = current_app.config.get("OAUTH_PROVIDERS", {}) or {}
    return providers.get(provider)


def _get_user_datastore():
    from wepppy.weppcloud.app import user_datastore

    return user_datastore


def _get_oauth_account_model():
    from wepppy.weppcloud.app import OAuthAccount

    return OAuthAccount


def _store_session_value(bucket_key: str, provider: str, value: Optional[str]):
    bucket: Dict[str, str] = dict(session.get(bucket_key) or {})

    if value is None:
        bucket.pop(provider, None)
    else:
        bucket[provider] = value

    if bucket:
        session[bucket_key] = bucket
    else:
        session.pop(bucket_key, None)

    session.modified = True


def _pop_session_value(bucket_key: str, provider: str) -> Optional[str]:
    bucket = dict(session.get(bucket_key) or {})
    value = bucket.pop(provider, None)

    if bucket:
        session[bucket_key] = bucket
    else:
        session.pop(bucket_key, None)

    session.modified = True
    return value


def _build_redirect_uri(provider: str, provider_settings: Dict) -> str:
    redirect_uri = provider_settings.get("redirect_uri")
    if redirect_uri:
        return redirect_uri

    scheme = current_app.config.get("OAUTH_REDIRECT_SCHEME", "https")
    host = current_app.config.get("OAUTH_REDIRECT_HOST")
    path = url_for("security_oauth.callback", provider=provider, _external=False)

    if host:
        return f"{scheme}://{host}{path}"

    return url_for(
        "security_oauth.callback",
        provider=provider,
        _external=True,
        _scheme=scheme,
    )


def _extract_name_from_profile(profile: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    given_name = profile.get("given_name")
    family_name = profile.get("family_name")
    display_name = profile.get("name") or profile.get("display_name")

    # ORCID nests names under 'name' with sub-keys like 'given-names'
    if isinstance(profile.get("name"), dict):
        name_block = profile["name"]
        given_name = given_name or name_block.get("given-names", {}).get("value")
        family_name = family_name or name_block.get("family-name", {}).get("value")
        display_name = (
            display_name
            or name_block.get("credit-name", {}).get("value")
            or name_block.get("name", {}).get("value")
        )

    if given_name or family_name:
        return given_name, family_name

    if not display_name:
        return None, None

    parts = display_name.strip().split(None, 1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def _normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    return email.strip().lower()


def _fetch_primary_verified_email(client, provider_settings: Dict, profile: Dict) -> Tuple[Optional[str], bool]:
    email = profile.get("email")
    verified = profile.get("email_verified") or profile.get("verified") or False

    if email and verified:
        return _normalize_email(email), True

    provider = provider_settings.get("name", "").lower()
    emails_endpoint = provider_settings.get("emails_url")

    logger.debug(
        "OAuth email extraction seed provider=%s email=%s verified=%s",
        provider,
        email,
        verified,
    )

    if provider == "orcid":
        emails_section = profile.get("emails")
        if isinstance(emails_section, dict):
            records = emails_section.get("email")
            if isinstance(records, list):
                for record in records:
                    if record.get("primary") and record.get("verified"):
                        return _normalize_email(record.get("email")), True
                for record in records:
                    if record.get("verified"):
                        return _normalize_email(record.get("email")), True
                for record in records:
                    if record.get("email"):
                        return _normalize_email(record.get("email")), bool(record.get("verified"))

        logger.debug(
            "OAuth email extraction orcid fallback profile keys=%s",
            list(profile.keys()) if isinstance(profile, dict) else type(profile),
        )

    if provider == "github" or emails_endpoint:
        endpoint = emails_endpoint or "user/emails"
        try:
            response = client.get(endpoint)
        except Exception as exc:  # pragma: no cover - network failure paths
            logger.warning("OAuth email fetch failed for provider=%s: %s", provider, exc)
            return _normalize_email(email), bool(email and verified)

        if not response.ok:
            logger.warning(
                "OAuth email fetch returned %s for provider=%s",
                response.status_code,
                provider,
            )
            return _normalize_email(email), bool(email and verified)

        try:
            payload = response.json()
        except ValueError:
            logger.warning("OAuth email response not JSON for provider=%s", provider)
            return _normalize_email(email), bool(email and verified)

        for record in payload:
            if record.get("primary") and record.get("verified"):
                return _normalize_email(record.get("email")), True

        for record in payload:
            if record.get("verified"):
                return _normalize_email(record.get("email")), True

    normalized = _normalize_email(email)
    return normalized, bool(normalized and verified)


def _extract_provider_uid(profile: Dict[str, Any], token: Optional[Dict[str, Any]] = None) -> Optional[str]:
    for key in ("sub", "id", "user_id", "uid"):
        value = profile.get(key)
        if value:
            return str(value)
    if token:
        for key in ("orcid", "id", "sub"):
            if token.get(key):
                return str(token[key])
    if "orcid" in profile:
        return str(profile["orcid"])
    identifier = profile.get("orcid-identifier")
    if isinstance(identifier, dict):
        path = identifier.get("path")
        if path:
            return str(path)
    return None


def _token_expiry_from_token(token: Dict[str, Any]) -> Optional[datetime]:
    expires_at = token.get("expires_at")
    if expires_at:
        try:
            return datetime.fromtimestamp(int(expires_at), tz=timezone.utc)
        except Exception:
            logger.debug("Unable to parse expires_at %r", expires_at)

    expires_in = token.get("expires_in")
    if expires_in:
        try:
            return utc_now() + timedelta(seconds=int(expires_in))
        except Exception:
            logger.debug("Unable to parse expires_in %r", expires_in)

    return None


def _link_identity(
    provider: str,
    provider_uid: str,
    email: str,
    profile: Dict[str, Any],
    token: Dict[str, Any],
) -> "User":
    """Link an OAuth identity to a user record (creating one if needed).

    Raises:
        ValueError: if the identity is already linked to a different user.
    """
    datastore = _get_user_datastore()

    account = datastore.find_oauth_account(provider, provider_uid)
    user = account.user if account else None

    if not user and email:
        user = datastore.find_user(email=email)

    if user and not user.active:
        abort(403, description="Account is inactive; contact support.")

    if not user:
        first_name, last_name = _extract_name_from_profile(profile)
        confirmed_at = utc_now()
        temp_password = hash_password(secrets.token_urlsafe(32))
        user = datastore.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            confirmed_at=confirmed_at.replace(tzinfo=None),
            active=True,
            password=temp_password,
        )
        datastore.commit()

    provider_config = _get_provider_settings(provider)
    scopes = normalize_token_scopes(token, provider_config)

    datastore.link_oauth_account(
        user,
        provider=provider,
        provider_uid=provider_uid,
        email=email,
        access_token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_type=token.get("token_type"),
        token_expiry=_token_expiry_from_token(token),
        scopes=scopes,
    )

    return user


def _resolve_next(provider: str) -> Optional[str]:
    next_hint = _pop_session_value(_SESSION_NEXT_KEY, provider)
    if next_hint:
        return next_hint
    return request.args.get("next")


@security_oauth_bp.route("/oauth/<provider>/login", methods=["GET"], strict_slashes=False)
def oauth_login(provider: str):
    provider_settings = _get_provider_settings(provider)
    if not provider_enabled(provider_settings):
        abort(404)

    if current_user.is_authenticated:
        return redirect(url_for(current_app.config.get("SECURITY_POST_LOGIN_VIEW", "security_ui.welcome")))

    client = ensure_oauth_client(provider, provider_settings)
    if client is None:
        abort(404)

    code_verifier, code_challenge = build_pkce_pair()
    _store_session_value(_SESSION_PKCE_KEY, provider, code_verifier)

    next_param = request.args.get("next")
    if next_param:
        _store_session_value(_SESSION_NEXT_KEY, provider, next_param)

    redirect_uri = _build_redirect_uri(provider, provider_settings)

    try:
        return client.authorize_redirect(
            redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
    except Exception as exc:  # pragma: no cover - network errors
        logger.error("Failed to initiate OAuth flow for provider=%s: %s", provider, exc)
        flash("Unable to start OAuth login. Please try again later.", "error")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))


@security_oauth_bp.route("/oauth/<provider>/callback", methods=["GET"], strict_slashes=False)
def callback(provider: str):
    provider_settings = _get_provider_settings(provider)
    if not provider_enabled(provider_settings):
        abort(404)

    client = ensure_oauth_client(provider, provider_settings)
    if client is None:
        abort(404)

    code_verifier = _pop_session_value(_SESSION_PKCE_KEY, provider)
    if not code_verifier:
        flash("OAuth session expired. Please try again.", "warning")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    try:
        token = client.authorize_access_token(code_verifier=code_verifier)
    except Exception as exc:
        logger.warning("OAuth callback token exchange failed for provider=%s: %s", provider, exc)
        flash("Login failed while contacting the identity provider.", "error")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    try:
        userinfo_endpoint = provider_settings.get("userinfo_url") or "user"
        headers = {}
        if provider.lower() == "orcid":
            headers["Accept"] = "application/json"
        response = client.get(userinfo_endpoint, headers=headers)
    except Exception as exc:
        logger.warning("OAuth userinfo request failed for provider=%s: %s", provider, exc)
        flash("Login failed while retrieving profile information.", "error")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    if not response.ok:
        logger.warning(
            "OAuth userinfo returned %s for provider=%s",
            response.status_code,
            provider,
        )
        flash("Unable to retrieve your profile from the identity provider.", "error")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    try:
        profile = response.json()
    except ValueError:
        logger.warning("OAuth userinfo response was not JSON for provider=%s", provider)
        flash("Unexpected response from the identity provider.", "error")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    provider_uid = _extract_provider_uid(profile, token)
    if not provider_uid:
        flash("The identity provider did not return a stable identifier.", "error")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    provider_lower = provider.lower()
    email, verified = _fetch_primary_verified_email(client, provider_settings, profile)
    if provider_lower == "orcid":
        normalized_uid = provider_uid
        if isinstance(normalized_uid, str) and normalized_uid.startswith("https://orcid.org/"):
            normalized_uid = normalized_uid.split("/", 3)[-1]
        normalized_uid = (normalized_uid or "").strip()
        if not _ORCID_ID_PATTERN.match(normalized_uid):
            normalized_uid = normalized_uid.replace("/", "-")
        if not normalized_uid:
            normalized_uid = secrets.token_hex(8)
        synthetic_email = _normalize_email(f"{normalized_uid}@orcid.null")
        if not email:
            email = synthetic_email
        verified = True
    email = _normalize_email(email)

    if not email:
        flash(
            "We could not determine your verified email address from the identity provider.",
            "error",
        )
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    if not verified and provider_lower != "orcid":
        flash("Please verify your email address with the identity provider before continuing.", "error")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    try:
        user = _link_identity(provider, provider_uid, email, profile, token)
    except ValueError:
        flash("This identity is already linked to a different WEPPcloud account.", "error")
        return redirect(url_for(current_app.config.get("SECURITY_LOGIN_ERROR_VIEW", "security_ui.login")))

    login_user(user, remember=True)

    next_url = _resolve_next(provider)
    if next_url:
        return redirect(next_url)

    post_login_view = current_app.config.get("SECURITY_POST_LOGIN_VIEW", "security_ui.welcome")
    return redirect(url_for(post_login_view))


@security_oauth_bp.route("/<provider>-auth-callback", methods=["GET"], strict_slashes=False)
def callback_alias(provider: str):
    provider_normalized = provider.strip().lower()
    return callback(provider_normalized)


@security_oauth_bp.route("/oauth/<provider>/disconnect", methods=["POST"], strict_slashes=False)
def disconnect(provider: str):
    if not current_user.is_authenticated:
        abort(403)

    token = request.form.get("csrf_token", "")
    try:
        validate_csrf(token)
    except ValidationError as exc:
        logger.warning(
            "OAuth disconnect CSRF validation failed for user_id=%s provider=%s: %s",
            getattr(current_user, "id", None),
            provider,
            exc,
        )
        flash("Your session expired. Please refresh the page and try again.", "warning")
        return redirect(url_for("user.profile"))

    OAuthAccount = _get_oauth_account_model()
    datastore = _get_user_datastore()

    account = OAuthAccount.query.filter_by(
        provider=provider,
        user_id=current_user.id,
    ).first()

    if not account:
        abort(404)

    if not current_user.password and current_user.oauth_accounts.count() <= 1:
        flash("Cannot remove the only linked sign-in method.", "warning")
        return redirect(url_for("user.profile"))

    datastore.unlink_oauth_account(current_user, provider)
    flash(f"{provider.title()} account disconnected.", "success")
    return redirect(url_for("user.profile"))


__all__ = ["security_oauth_bp"]
