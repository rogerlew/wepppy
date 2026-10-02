"""Trusted FA-01 identity adapters after transport credential verification.

These functions do not verify JWTs, resource claims, revocation or scopes.
Callers must perform those checks before passing claims here. Mutable account
state is read from the account database, never from informational JWT groups.
"""
import json
from pathlib import Path

import sqlalchemy as sa

from .feature_access import VerifiedPrincipal
from .feature_access_schema import users, roles, roles_users
from .feature_access_store import FeatureAccessStore

INTERNAL_STATEMENT_VERSION = "internal-2026-10-01"
PRINCIPAL_CLAIM = "feature_access_principal"


class FeatureIdentityConfigurationError(RuntimeError):
    """The operator-owned integration registration is unavailable or invalid."""


def account_engine():
    from wepppy.weppcloud.run_catalog.adapter import get_engine
    try:
        return get_engine()
    except (RuntimeError, ValueError) as exc:
        raise FeatureIdentityConfigurationError("Account database configuration unavailable") from exc


def account_principal(user_id, *, engine=None):
    """Resolve a canonical account and its current operational roles."""
    if type(user_id) is not int or user_id <= 0:
        return VerifiedPrincipal()
    with (engine if engine is not None else account_engine()).connect() as connection:
        active = connection.scalar(sa.select(users.c.active).where(users.c.id == user_id))
        if not active:
            return VerifiedPrincipal()
        names = connection.scalars(sa.select(roles.c.name).join(
            roles_users, roles_users.c.role_id == roles.c.id
        ).where(roles_users.c.user_id == user_id)).all()
    return VerifiedPrincipal("human", user_id, frozenset(names))


def principal_claim(principal):
    """Serialize verified origin only; this claim is not an entitlement."""
    identity = principal.user_id if principal.kind == "human" else None
    if principal.kind == "integration" and principal.integration_features == frozenset({"culvert_runner"}):
        identity = "culvert-web-app"
    return {"version": 1, "kind": principal.kind, "id": identity}


def _values(value):
    if isinstance(value, str):
        return value.split()
    return value if isinstance(value, (list, tuple)) else []


def _canonical_id(value):
    if type(value) is int:
        return value if value > 0 else None
    if isinstance(value, str) and value.isascii() and value.isdecimal() and not value.startswith("0"):
        return int(value)
    return None


def integration_registration():
    path = Path(__file__).with_name("feature_access_integrations.json")
    try:
        with path.open(encoding="utf-8") as stream:
            registration = json.load(stream)["culvert-web-app"]
        if (not isinstance(registration["subjects"], list)
                or not all(isinstance(subject, str) and subject for subject in registration["subjects"])
                or registration["audience"] != "rq-engine"
                or registration["service_group"] != "culverts"
                or registration["token_classes"] != ["service"]):
            raise ValueError("Invalid Culvert integration registration")
        return registration
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise FeatureIdentityConfigurationError("Integration registration unavailable") from exc


def _registered_integration(claims):
    registration = integration_registration()
    return (
        claims.get("sub") in registration["subjects"]
        and registration["audience"] in _values(claims.get("aud"))
        and registration["service_group"] in _values(claims.get("service_groups"))
        and claims.get("token_class") in registration["token_classes"]
    )


def principal_from_verified_claims(claims, *, engine=None, legacy_session_identity=None,
                                   mcp_identity=None):
    """Resolve only inventoried issuer contracts; never treat a SID as a user ID.

    Legacy callbacks must validate a live SID/identity binding. They are supplied
    by the owning transport rather than creating a second session decoder here.
    """
    token_class = claims.get("token_class")
    if token_class == "user":
        return account_principal(_canonical_id(claims.get("sub")), engine=engine)
    origin = claims.get(PRINCIPAL_CLAIM)
    if isinstance(origin, dict):
        if origin.get("version") != 1 or token_class not in {"session", "service", "mcp"}:
            return VerifiedPrincipal()
        if origin.get("kind") == "human":
            return account_principal(_canonical_id(origin.get("id")), engine=engine)
        if origin.get("kind") == "integration" and origin.get("id") == "culvert-web-app":
            # Derivatives carry the signed issuer binding; operation/resource
            # scopes are still enforced by the transport before this adapter.
            integration_registration()
            return VerifiedPrincipal("integration", integration_features=frozenset({"culvert_runner"}))
        return VerifiedPrincipal()
    if token_class == "service":
        subject = claims.get("sub")
        if isinstance(subject, str) and subject.startswith("admin-run-token:") and "admin-run-token" in _values(claims.get("service_groups")):
            return account_principal(_canonical_id(subject.removeprefix("admin-run-token:")), engine=engine)
    if token_class == "service" and _registered_integration(claims):
        return VerifiedPrincipal("integration", integration_features=frozenset({"culvert_runner"}))
    if token_class == "session" and legacy_session_identity is not None:
        return account_principal(legacy_session_identity(claims), engine=engine)
    if token_class == "mcp" and mcp_identity is not None:
        return account_principal(mcp_identity(claims.get("sub")), engine=engine)
    return VerifiedPrincipal()


def feature_store():
    return FeatureAccessStore(account_engine())
