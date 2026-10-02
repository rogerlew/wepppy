"""FA-01 decisions for trusted principal/resource adapters, not raw JWT claims.

Callers must verify identity, token scope/resource and existing authorization
before constructing these inputs. This module neither validates tokens nor
widens endpoint-supported token classes. Wiring follows in milestone three.
"""

from dataclasses import dataclass
import logging

from sqlalchemy.exc import SQLAlchemyError

from wepppy.weppcloud.feature_registry.schema import FeatureSpec, ROLE_AUDIENCES, REQUIRED_ACCESS_FEATURES
from .feature_access_store import FeatureAccessValidationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerifiedPrincipal:
    kind: str = "anonymous"
    user_id: int | None = None
    roles: frozenset[str] = frozenset()
    # Only an operator-registered integration adapter may supply this set.
    integration_features: frozenset[str] = frozenset()


@dataclass(frozen=True)
class FeatureResourceContext:
    existing_access_allowed: bool = False
    readonly: bool = False
    backend: str = "any"
    enabled_features: frozenset[str] = frozenset()
    # Private grouped resources require live workflow membership for reads.
    requires_read_entitlement: bool = False
    internal_statement_version: str | None = None
    # Removal of retained legacy state need not satisfy enable/run capability.
    check_capabilities: bool = True


@dataclass(frozen=True)
class FeatureAccessDecision:
    allowed: bool
    reason: str
    basis: str | None = None


def _valid_access_configuration(feature):
    if feature.access_mode is None and feature.access_group is None:
        return feature.id not in REQUIRED_ACCESS_FEATURES
    return (
        feature.access_mode in {"group_only", "role_or_group"}
        and isinstance(feature.access_group, str) and bool(feature.access_group.strip())
    )


def _entitlement(principal, feature, operation, context, store):
    if not _valid_access_configuration(feature):
        return FeatureAccessDecision(False, "feature_access_configuration_error")
    if principal.kind == "integration":
        if feature.id == "culvert_runner" and feature.id in principal.integration_features:
            return FeatureAccessDecision(True, "allowed", "integration")
        return FeatureAccessDecision(False, "integration_not_authorized")
    if principal.kind != "human" or type(principal.user_id) is not int or principal.user_id <= 0:
        return FeatureAccessDecision(False, "human_identity_required")
    if feature.access_mode != "group_only" and principal.roles & ROLE_AUDIENCES[feature.min_role]:
        return FeatureAccessDecision(True, "allowed", "legacy_role")
    if not feature.access_group:
        return FeatureAccessDecision(False, "feature_entitlement_required")
    try:
        member, acknowledged = store.membership(
            principal.user_id, feature.access_group,
            statement_version=context.internal_statement_version,
        )
    except FeatureAccessValidationError:
        return FeatureAccessDecision(False, "feature_access_configuration_error")
    except SQLAlchemyError:
        # Decision boundary: preserve operator evidence; never fall back to a role.
        logger.exception("Feature membership lookup unavailable for %s", feature.id)
        return FeatureAccessDecision(False, "feature_access_unavailable")
    if not member:
        return FeatureAccessDecision(False, "feature_membership_required")
    if operation == "act" and not acknowledged:
        return FeatureAccessDecision(False, "internal_acknowledgment_required")
    return FeatureAccessDecision(True, "allowed", "group")


def evaluate_feature_access(principal: VerifiedPrincipal, feature: FeatureSpec,
                            operation: str, context: FeatureResourceContext,
                            store):
    """Conjoin feature admission with the endpoint's existing resource decision."""
    if operation not in {"inspect", "act"}:
        return FeatureAccessDecision(False, "invalid_operation")
    if not context.existing_access_allowed:
        return FeatureAccessDecision(False, "existing_access_denied")
    if not _valid_access_configuration(feature):
        return FeatureAccessDecision(False, "feature_access_configuration_error")
    if operation == "inspect" and not context.requires_read_entitlement:
        return FeatureAccessDecision(True, "allowed", "existing_read")
    if operation == "act":
        if context.readonly:
            return FeatureAccessDecision(False, "readonly")
        if context.check_capabilities and feature.requires_backend != "any" and feature.requires_backend != context.backend:
            return FeatureAccessDecision(False, "backend_required")
        if context.check_capabilities and not set(feature.requires_features).issubset(context.enabled_features):
            return FeatureAccessDecision(False, "prerequisite_required")
    # Omitted group metadata preserves ordinary role/anonymous behavior.
    if feature.access_mode is None and feature.min_role == "user":
        decision = FeatureAccessDecision(True, "allowed", "legacy_role")
    else:
        decision = _entitlement(principal, feature, operation, context, store)
    return decision
