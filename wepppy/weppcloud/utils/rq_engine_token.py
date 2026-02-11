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

    subject = None
    if hasattr(user, "get_id"):
        subject = user.get_id()
    if not subject:
        subject = getattr(user, "id", None)
    if not subject:
        subject = getattr(user, "email", None)
    if not subject:
        raise RuntimeError("Unable to resolve user subject for rq-engine token")

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
            "email": getattr(user, "email", None),
            "jti": uuid.uuid4().hex,
        },
    )
    token = token_payload.get("token")
    if not token:
        raise RuntimeError("Failed to issue rq-engine token")
    return token


__all__ = ["RQ_ENGINE_UI_SCOPES", "issue_user_rq_engine_token"]
