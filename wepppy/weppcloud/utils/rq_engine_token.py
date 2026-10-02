from __future__ import annotations

from typing import Any, Sequence
import uuid

from wepppy.weppcloud.utils import auth_tokens

# Canonical UI profile used by browser-driven rq-engine requests.
RQ_ENGINE_UI_SCOPES: tuple[str, ...] = ("rq:enqueue", "rq:status", "rq:export")


def issue_user_rq_engine_token(
    user: Any,
    *,
    scopes: Sequence[str] = RQ_ENGINE_UI_SCOPES,
) -> str | None:
    """Issue an rq-engine JWT for an authenticated Flask-Login user-like object."""
    if getattr(user, "is_anonymous", False):
        return None

    user_id = getattr(user, "id", None)
    if type(user_id) is not int or user_id <= 0:
        raise RuntimeError("Unable to resolve numeric user ID for rq-engine token")
    # The verified feature-access adapter resolves user-token principals from
    # ``sub``.  Flask-Security's get_id() returns an fs_uniquifier, which is a
    # session identifier rather than the canonical account identity.
    subject = str(user_id)

    roles = [
        str(getattr(role, "name", role)).strip()
        for role in (getattr(user, "roles", None) or [])
        if str(getattr(role, "name", role)).strip()
    ]

    token_payload = auth_tokens.issue_token(
        str(subject),
        scopes=list(scopes),
        audience="rq-engine",
        extra_claims={
            "roles": roles,
            "token_class": "user",
            "user_id": user_id,
            "email": getattr(user, "email", None),
            "jti": uuid.uuid4().hex,
        },
    )
    token = token_payload.get("token")
    if not token:
        raise RuntimeError("Failed to issue rq-engine token")
    return token


__all__ = ["RQ_ENGINE_UI_SCOPES", "issue_user_rq_engine_token"]
