"""Bounded account/resource stubs for route-domain tests of the real evaluator.

The caller still stubs its pre-existing verified JWT/resource boundary. Account
2 is explicitly granted/acknowledged; other accounts have no memberships.
PostgreSQL and real-token acceptance must not use this fixture.
"""
from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal, FeatureResourceContext


def stub_feature_accounts(monkeypatch, *, members=frozenset({2})):
    from wepppy.microservices.rq_engine import feature_access as adapter
    from wepppy.weppcloud.utils import feature_access_runtime as runtime

    def principal(claims):
        raw_id = claims.get("sub")
        if not isinstance(raw_id, str) or not raw_id.isdecimal():
            return VerifiedPrincipal()
        return VerifiedPrincipal("human", int(raw_id), frozenset(claims.get("roles", [])))

    class Store:
        def membership(self, user_id, group_key, **kwargs):
            return user_id in members, user_id in members

    monkeypatch.setattr(adapter, "verified_principal", principal)
    monkeypatch.setattr(adapter, "resource_context", lambda *args, **kwargs: FeatureResourceContext(
        existing_access_allowed=True, backend="wbt", enabled_features=frozenset({"omni"}),
        requires_read_entitlement=kwargs.get("protected_read", False),
        consumes_contrasts=kwargs.get("consumes_contrasts", False),
        internal_statement_version="internal-2026-10-01"))
    monkeypatch.setattr(runtime, "feature_store", Store)
