"""Shared feature admission after existing transport/resource authorization."""
from dataclasses import replace
import logging

from sqlalchemy.exc import SQLAlchemyError

from wepppy.weppcloud.feature_registry import FeatureRegistryValidationError
from wepppy.weppcloud.feature_registry.runtime import feature_registry_by_id
from .feature_access import FeatureAccessDecision, FeatureResourceContext, evaluate_feature_access
from .feature_access_identity import INTERNAL_STATEMENT_VERSION, FeatureIdentityConfigurationError, feature_store

logger = logging.getLogger(__name__)


def resource_context(wd=None, *, protected_read=False, consumes_contrasts=False, check_capabilities=True):
    context = FeatureResourceContext(
        existing_access_allowed=True, requires_read_entitlement=protected_read,
        consumes_contrasts=consumes_contrasts,
        internal_statement_version=INTERNAL_STATEMENT_VERSION,
        check_capabilities=check_capabilities,
    )
    if wd is None:
        return context
    from wepppy.nodb.core import Ron, Watershed
    ron = Ron.getInstance(wd)
    watershed = Watershed.tryGetInstance(wd)
    backend = "any"
    if watershed is not None:
        backend = watershed.delineation_backend.name.lower()
    return replace(context, readonly=bool(ron.readonly), backend=backend,
                   enabled_features=frozenset(ron.mods or ()))


def decide(principal, feature_id, operation, context, *, store=None):
    try:
        features = feature_registry_by_id()
        feature = features[feature_id]
        # Public non-embargoed inspection does not require a database engine.
        return evaluate_feature_access(
            principal, feature, operation, context,
            store if store is not None else _LazyStore(),
            contrast_feature=features["omni_contrasts"],
        )
    except (FeatureRegistryValidationError, FeatureIdentityConfigurationError):
        logger.exception("Feature registry unavailable during admission")
        return FeatureAccessDecision(False, "feature_access_configuration_error")
    except SQLAlchemyError:
        logger.exception("Feature account database unavailable during admission")
        return FeatureAccessDecision(False, "feature_access_unavailable")


class _LazyStore:
    def membership(self, *args, **kwargs):
        return feature_store().membership(*args, **kwargs)


def decision_status(decision):
    return 503 if decision.reason in {"feature_access_unavailable", "feature_access_configuration_error"} else 403


def workflow_features(runid):
    """Restricted workflow aliases; enabled mods alone never restrict a run."""
    parts = str(runid).split(";;")
    features = []
    if len(parts) >= 3 and parts[0] == "batch":
        features.append("batch_runner")
    if len(parts) >= 3 and parts[0] == "culvert":
        features.append("culvert_runner")
    if len(parts) >= 3 and parts[-2] == "omni-contrast":
        features.append("omni_contrasts")
    return tuple(features)
