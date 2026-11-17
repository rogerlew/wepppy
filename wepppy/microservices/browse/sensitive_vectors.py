"""Classification and authorization for retained vector-upload evidence."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from urllib.parse import unquote

from sqlalchemy.exc import SQLAlchemyError


_SENSITIVE_ROOTS = (
    ("roads", "vector_upload_attempts"),
    ("ag_fields", "vector_upload_attempts"),
    ("_pups", "omni", "contrasts", "vector_upload_attempts"),
    ("resources", "vector_upload_attempts"),
    ("archives", "private"),
)


def _path_parts(raw_path: str) -> tuple[str, ...]:
    value = str(raw_path or "")
    for _ in range(2):
        decoded = unquote(value)
        if decoded == value:
            break
        value = decoded
    value = unicodedata.normalize("NFKC", value).replace("\\", "/")
    return tuple(part.casefold() for part in value.split("/") if part not in ("", "."))


def is_sensitive_vector_path(raw_path: str) -> bool:
    """Return true for a retained-attempt/private-archive root or descendant."""

    parts = _path_parts(raw_path)
    for root in _SENSITIVE_ROOTS:
        width = len(root)
        if any(parts[index : index + width] == root for index in range(len(parts) - width + 1)):
            return True
    return False


def sensitive_child_names(raw_parent: str) -> frozenset[str]:
    """Names that must be hidden when an unauthorized caller lists a parent."""

    parent = _path_parts(raw_parent)
    names = {
        root[-1]
        for root in _SENSITIVE_ROOTS
        if len(parent) == len(root) - 1 and root[:-1] == parent
    }
    return frozenset(names)


def is_retained_original(raw_path: str) -> bool:
    parts = _path_parts(raw_path)
    return is_sensitive_vector_path(raw_path) and bool(parts) and parts[-1].endswith(".upload")


def _positive_user_id(claims: Mapping[str, object] | None) -> int | None:
    if not claims:
        return None
    candidate = claims.get("user_id")
    principal = claims.get("feature_access_principal")
    if candidate is None and isinstance(principal, Mapping) and principal.get("kind") == "human":
        candidate = principal.get("id")
    try:
        value = int(candidate)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def can_access_run_sensitive_vector(auth_context, runid: str) -> bool:
    if bool(getattr(auth_context, "is_root", False)):
        return True
    claims = getattr(auth_context, "claims", None)
    user_id = _positive_user_id(claims)
    if user_id is None:
        return False
    try:
        from wepppy.weppcloud.utils.helpers import get_run_owners_lazy

        owners = get_run_owners_lazy(runid) or ()
    except (ImportError, OSError, RuntimeError, SQLAlchemyError, ValueError):
        return False
    for owner in owners:
        try:
            if int(getattr(owner, "id", 0)) == user_id:
                return True
        except (TypeError, ValueError):
            continue
    return False


def can_access_batch_sensitive_vector(auth_context, batch_name: str) -> bool:
    if bool(getattr(auth_context, "is_root", False)):
        return True
    claims = getattr(auth_context, "claims", None)
    if not isinstance(claims, Mapping):
        return False
    try:
        from wepppy.microservices.rq_engine.auth import AuthError
        from wepppy.microservices.rq_engine.feature_access import require_feature_access

        require_feature_access(
            claims,
            "batch_runner",
            operation="inspect",
            protected_read=True,
        )
    except (AuthError, ImportError, RuntimeError, ValueError):
        return False
    return True


__all__ = [
    "can_access_batch_sensitive_vector",
    "can_access_run_sensitive_vector",
    "is_retained_original",
    "is_sensitive_vector_path",
    "sensitive_child_names",
]
