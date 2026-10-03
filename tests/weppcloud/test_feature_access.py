"""Real account transactions in isolated PostgreSQL schemas; no shared user writes."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
import importlib
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError

from wepppy.weppcloud.configuration import _build_postgres_uri
from wepppy.weppcloud.feature_registry.runtime import load_feature_registry
from wepppy.weppcloud.feature_registry.schema import validate_feature_registry_payload, FeatureRegistryValidationError
from wepppy.weppcloud.utils.feature_access import (
    VerifiedPrincipal, FeatureResourceContext, evaluate_feature_access,
)
from wepppy.weppcloud.utils.feature_access_store import (
    FeatureAccessStore, FeatureAccessConflict, FeatureAccessValidationError, utc_now,
)
from wepppy.weppcloud.utils.feature_access_schema import (
    metadata, users, roles, roles_users, groups, memberships, events, acceptances,
)

pytestmark = pytest.mark.integration
MIGRATION = importlib.import_module('wepppy.weppcloud.migrations.versions.e7a1c9d204bf_add_feature_access')
POSTGRES_URI = _build_postgres_uri()  # Capture before the autouse secret-isolation fixture.
FEATURES = load_feature_registry()
BY_ID = {f.id: f for f in FEATURES}


@pytest.fixture
def database():
    uri = POSTGRES_URI
    schema = 'feature_access_test_' + uuid4().hex
    admin = sa.create_engine(uri, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    engine = sa.create_engine(uri, hide_parameters=True, connect_args={'options': '-csearch_path=' + schema})
    try:
        # Existing account substrate, with real IDs/role associations preserved.
        metadata.create_all(engine, tables=[users, roles, roles_users])
        with engine.begin() as connection:
            connection.execute(users.insert(), [{'id': n, 'active': True} for n in [1, 2, 3]])
            connection.execute(roles.insert(), [{'id': 1, 'name': 'Root'}, {'id': 2, 'name': 'PowerUser'}])
            connection.execute(roles_users.insert(), [{'user_id': 1, 'role_id': 1}, {'user_id': 2, 'role_id': 2}])
            with Operations.context(MigrationContext.configure(connection)):
                MIGRATION.upgrade()
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))
        admin.dispose()


@pytest.fixture
def store(database):
    return FeatureAccessStore(database)


def change(store, operation='add', **kwargs):
    args = dict(actor_id=1, user_id=2, group_key='openet_ts', operation=operation,
                reason='approved bounded testing', features=FEATURES)
    args.update(kwargs)
    return store.change_membership(**args)


def count(engine, table):
    with engine.connect() as connection:
        return connection.scalar(sa.select(sa.func.count()).select_from(table))


def test_openet_signed_token_live_membership_admission(database, store, monkeypatch, tmp_path):
    """Real JWT and SQL admission; only scientific state and job execution are bounded."""
    from contextlib import nullcontext
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    import wepppy.microservices.rq_engine as rq_engine
    from wepppy.microservices.rq_engine import auth, feature_access, openet_ts_routes as route
    from wepppy.weppcloud.utils import auth_tokens, feature_access_identity as identity
    from wepppy.weppcloud.utils.feature_access_identity import INTERNAL_STATEMENT_VERSION
    from wepppy.weppcloud.utils import helpers

    monkeypatch.setenv('WEPP_AUTH_JWT_SECRET', 'isolated-feature-route-test')
    auth_tokens.get_jwt_config.cache_clear()
    monkeypatch.setattr(identity, 'account_engine', lambda: database)
    monkeypatch.setattr(auth, '_check_revocation', lambda jti: None)
    monkeypatch.setattr(
        auth,
        '_AUTH_REDIS_CLIENT',
        lambda **_kwargs: SimpleNamespace(hget=lambda *_args: None, close=lambda: None),
    )
    monkeypatch.setattr(auth.Ron, 'ispublic', staticmethod(lambda wd: True))
    monkeypatch.setattr(auth, 'get_run_owners_lazy', lambda runid: [])
    for module in (auth, route, helpers):
        monkeypatch.setattr(module, 'get_wd', lambda runid, **kwargs: str(tmp_path))
    monkeypatch.setattr(feature_access, 'resource_context', lambda *args, **kwargs: FeatureResourceContext(
        existing_access_allowed=True, backend='wbt', internal_statement_version=INTERNAL_STATEMENT_VERSION))
    mutations = []
    prep = SimpleNamespace(remove_timestamp=lambda task: mutations.append('timestamp'))
    monkeypatch.setattr(route.RedisPrep, 'getInstance', lambda wd: prep)
    monkeypatch.setattr(route.redis, 'Redis', lambda **kwargs: nullcontext(object()))
    monkeypatch.setattr(route, 'Queue', lambda **kwargs: object())

    def enqueue(*args, **kwargs):
        mutations.append('enqueue')
        return SimpleNamespace(id='admitted-job')

    monkeypatch.setattr(route, 'enqueue_tracked_rq_job', enqueue)

    def token(user_id, scopes=('rq:enqueue',)):
        return auth_tokens.issue_token(str(user_id), scopes=list(scopes), audience='rq-engine',
                                       extra_claims={'token_class': 'user'})['token']

    old_token = token(2)
    with TestClient(rq_engine.app) as client:
        def submit(credential):
            return client.post('/api/runs/public-run/cfg/acquire-openet-ts', json={},
                               headers={'Authorization': 'Bearer ' + credential})

        assert submit(token(1)).status_code == 403  # Root is not an OpenET grant.
        assert submit(old_token).status_code == 403
        change(store)
        assert submit(old_token).json()['error']['code'] == 'internal_acknowledgment_required'
        assert mutations == []
        store.acknowledge_internal(2, INTERNAL_STATEMENT_VERSION)
        assert submit(token(2, scopes=('rq:status',))).status_code == 403
        assert mutations == []
        accepted = submit(old_token)
        assert accepted.status_code == 200 and accepted.json()['job_id'] == 'admitted-job'
        assert mutations == ['timestamp', 'enqueue']
        change(store, operation='remove')
        removed = submit(old_token)
        assert removed.status_code == 403, removed.text
        assert mutations == ['timestamp', 'enqueue']


@pytest.mark.parametrize('claims', [
    {'token_class': 'user', 'sub': '2'},
    {'token_class': 'service', 'sub': 'admin-run-token:2', 'service_groups': ['admin-run-token']},
    {'token_class': 'session', 'sub': 'sid', 'feature_access_principal': {'version': 1, 'kind': 'human', 'id': 2}},
])
def test_verified_origin_uses_live_group_and_account(database, store, claims):
    from wepppy.weppcloud.utils.feature_access_identity import principal_from_verified_claims
    from wepppy.weppcloud.utils.feature_access_runtime import decide, resource_context
    context = resource_context(protected_read=True)
    principal = principal_from_verified_claims(claims, engine=database)
    assert principal.user_id == 2
    assert not decide(principal, 'batch_runner', 'inspect', context, store=store).allowed
    change(store, group_key='batch_runner')
    assert decide(principal, 'batch_runner', 'inspect', context, store=store).allowed
    change(store, operation='remove', group_key='batch_runner')
    assert not decide(principal_from_verified_claims(claims, engine=database),
                      'batch_runner', 'inspect', context, store=store).allowed
    with database.begin() as connection:
        connection.execute(users.update().where(users.c.id == 2).values(active=False))
    assert principal_from_verified_claims(claims, engine=database).kind == 'anonymous'


@pytest.mark.parametrize('claims', [
    {'token_class': 'session', 'sub': '2', 'user_id': 2},
    {'token_class': 'service', 'sub': '2', 'roles': ['Root']},
    {'token_class': 'service', 'sub': 'admin-run-token:2'},
    {'token_class': 'mcp', 'sub': '2'},
    {'token_class': 'session', 'feature_access_principal': {'version': 2, 'kind': 'human', 'id': 2}},
    {'token_class': 'service', 'sub': 'culvert-batch-submit-90d', 'aud': 'other', 'service_groups': ['culverts']},
])
def test_unknown_credential_provenance_never_infers_human(database, claims):
    from wepppy.weppcloud.utils.feature_access_identity import principal_from_verified_claims
    assert principal_from_verified_claims(claims, engine=database).kind == 'anonymous'


def test_registered_integration_and_derivative_origin():
    from wepppy.weppcloud.utils.feature_access_identity import principal_claim, principal_from_verified_claims
    claims = {'token_class': 'service', 'sub': 'culvert-batch-submit-90d',
              'aud': 'rq-engine', 'service_groups': ['culverts']}
    principal = principal_from_verified_claims(claims)
    assert principal.integration_features == frozenset({'culvert_runner'})
    derivative = {'token_class': 'session', 'sub': 'sid', 'feature_access_principal': principal_claim(principal)}
    assert principal_from_verified_claims(derivative) == principal
    claims['sub'] = 'unregistered-service'
    assert principal_from_verified_claims(claims).kind == 'anonymous'


def test_migration_head_schema_seed_and_legacy_preservation(database, store):
    scripts = ScriptDirectory(str(Path(__file__).parents[2] / 'wepppy/weppcloud/migrations'))
    assert scripts.get_heads() == [MIGRATION.revision]
    assert MIGRATION.down_revision == 'd30c91a7b802'
    store.seed_groups(FEATURES)
    store.seed_groups(FEATURES)
    assert count(database, groups) == 6
    assert count(database, memberships) == count(database, events) == count(database, acceptances) == 0
    assert count(database, roles_users) == 2
    with database.connect() as connection:
        assert connection.execute(sa.select(users.c.id).order_by(users.c.id)).scalars().all() == [1, 2, 3]
        differences = __import__('alembic.autogenerate', fromlist=['compare_metadata']).compare_metadata(
            MigrationContext.configure(connection), metadata,
        )
        assert not differences
    with pytest.raises(RuntimeError, match='retained'):
        MIGRATION.downgrade()


def test_empty_accounts_upgrade(database):
    # Recreate only the new tables around an empty pre-existing account schema.
    with database.begin() as connection:
        for table in (acceptances, events, memberships, groups):
            table.drop(connection)
        connection.execute(roles_users.delete())
        connection.execute(users.delete())
        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()
    assert count(database, users) == 0
    assert count(database, groups) == 6
    assert count(database, memberships) == 0


def test_membership_atomicity_history_and_acknowledgment(database, store):
    assert change(store)
    assert not change(store)
    assert store.membership(2, 'openet_ts', statement_version='v1') == (True, False)
    assert store.acknowledge_internal(2, 'v1')
    assert not store.acknowledge_internal(2, 'v1')
    assert store.membership(2, 'openet_ts', statement_version='v1') == (True, True)
    assert store.membership(2, 'openet_ts', statement_version='v2') == (True, False)
    assert change(store, 'remove')
    assert not change(store, 'remove')
    assert count(database, events) == 2
    with database.begin() as connection:
        connection.execute(users.delete().where(users.c.id == 2))
        connection.execute(groups.delete().where(groups.c.key == 'openet_ts'))
        history = connection.execute(sa.select(events).order_by(events.c.id)).mappings().all()
        assert [row.action for row in history] == ['add', 'remove']
        assert all(row.user_id == 2 and row.actor_id == 1 and row.feature_scope == [{'feature_id': 'openet_ts', 'access_mode': 'group_only'}] for row in history)
    assert count(database, acceptances) == 1


def test_poweruser_approval_is_atomic_idempotent_and_preserves_roles(database, store):
    result = store.approve_poweruser(3, 'poweruser-test-v1', 'automatic-test-rule')
    assert result == {
        'status': 'granted',
        'role_changed': True,
        'acceptance_changed': True,
        'statement_version': 'poweruser-test-v1',
    }
    repeated = store.approve_poweruser(3, 'poweruser-test-v1', 'automatic-test-rule')
    assert repeated == {
        'status': 'granted',
        'role_changed': False,
        'acceptance_changed': False,
        'statement_version': 'poweruser-test-v1',
    }
    with database.connect() as connection:
        assert connection.execute(sa.select(roles.c.name).select_from(
            roles.join(roles_users, roles.c.id == roles_users.c.role_id)
        ).where(roles_users.c.user_id == 3)).scalars().all() == ['PowerUser']
        record = connection.execute(sa.select(acceptances).where(
            acceptances.c.user_id == 3,
            acceptances.c.statement_kind == 'poweruser',
        )).mappings().one()
    assert record.statement_version == 'poweruser-test-v1'
    assert record.decision_rule == 'automatic-test-rule'
    assert record.approved_at is not None


def test_poweruser_acceptance_failure_rolls_back_role(database, store):
    with database.begin() as connection:
        connection.execute(sa.text(
            "ALTER TABLE onboarding_acceptance ADD CONSTRAINT reject_poweruser_test "
            "CHECK (statement_kind != 'poweruser')"
        ))
    with pytest.raises(IntegrityError):
        store.approve_poweruser(3, 'poweruser-test-v1', 'automatic-test-rule')
    with database.connect() as connection:
        assert connection.execute(sa.select(roles_users.c.user_id).select_from(
            roles_users.join(roles, roles.c.id == roles_users.c.role_id)
        ).where(roles_users.c.user_id == 3, roles.c.name == 'PowerUser')).first() is None
        assert connection.scalar(sa.select(sa.func.count()).select_from(acceptances)) == 0


def test_fresh_poweruser_token_cannot_read_private_batch(database, store, monkeypatch):
    from wepppy.weppcloud.utils import auth_tokens
    from wepppy.weppcloud.utils.feature_access_identity import principal_from_verified_claims
    from wepppy.weppcloud.utils.feature_access_runtime import decide, resource_context

    monkeypatch.setenv('WEPP_AUTH_JWT_SECRET', 'isolated-poweruser-onboarding-test')
    monkeypatch.setenv('WEPP_AUTH_JWT_ALGORITHMS', 'HS256')
    auth_tokens.get_jwt_config.cache_clear()
    store.approve_poweruser(3, 'poweruser-test-v1', 'automatic-test-rule')
    issued = auth_tokens.issue_token(
        '3',
        scopes=['runs:read', 'rq:enqueue'],
        audience=['rq-engine', 'query-engine'],
        extra_claims={
            'token_class': 'user',
            'roles': ['PowerUser'],
            'groups': [],
        },
    )
    claims = auth_tokens.decode_token(issued['token'], audience='rq-engine')
    principal = principal_from_verified_claims(claims, engine=database)

    decision = decide(
        principal,
        'batch_runner',
        'inspect',
        resource_context(protected_read=True),
        store=store,
    )
    assert principal.roles == frozenset({'PowerUser'})
    assert not decision.allowed
    assert decision.reason == 'feature_membership_required'


def test_event_failure_rolls_back_grant(database, store):
    with database.begin() as connection:
        connection.execute(sa.text("ALTER TABLE feature_access_event ADD CONSTRAINT injected_failure CHECK (reason != 'fail')"))
    with pytest.raises(IntegrityError):
        change(store, reason='fail')
    assert count(database, memberships) == count(database, events) == 0
    assert change(store)
    with pytest.raises(IntegrityError):
        change(store, 'remove', reason='fail')
    assert count(database, memberships) == count(database, events) == 1


def test_concurrent_duplicate_add_remove(database, store):
    for operation in ('add', 'remove'):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: change(store, operation), range(4)))
        assert sorted(results) == [False, False, False, True]
    assert count(database, memberships) == 0
    assert count(database, events) == 2


def test_expiration_review_conflict_and_regrant(database, store):
    now = utc_now()
    review = now - timedelta(days=1)
    assert change(store, review_at=review)
    assert store.membership(2, 'openet_ts') == (True, False)
    with pytest.raises(FeatureAccessConflict):
        change(store, review_at=now)
    assert change(store, 'remove')
    expiry = now + timedelta(days=1)
    assert change(store, expires_at=expiry)
    assert store.membership(2, 'openet_ts', now=expiry) == (False, False)
    with database.begin() as connection:
        connection.execute(memberships.update().values(expires_at=now - timedelta(seconds=1)))
    assert change(store)
    assert count(database, memberships) == 1
    assert count(database, events) == 4


@pytest.mark.parametrize('kwargs', [dict(reason=' '), dict(user_id=999), dict(user_id=True),
    dict(group_key='invented'), dict(expires_at=utc_now()-timedelta(days=1)),
    dict(review_at=utc_now().replace(tzinfo=None)), dict(operation='remove', review_at=utc_now())])
def test_invalid_membership_no_writes(database, store, kwargs):
    with pytest.raises(FeatureAccessValidationError):
        change(store, **kwargs)
    assert count(database, memberships) == count(database, events) == 0


def test_nonroot_cannot_manage(database, store):
    with pytest.raises(PermissionError):
        change(store, actor_id=2)
    assert count(database, events) == 0


def decision(store, feature='openet_ts', operation='act', principal=None, **ctx):
    context = dict(existing_access_allowed=True, backend='wbt', enabled_features=frozenset({'omni'}),
                   internal_statement_version='v1')
    context.update(ctx)
    return evaluate_feature_access(principal or VerifiedPrincipal('human', 2), BY_ID[feature], operation,
                                   FeatureResourceContext(**context), store)


def test_group_only_no_root_bypass_and_current_membership(store):
    for feature in ('openet_ts', 'batch_runner', 'culvert_runner'):
        assert not decision(store, feature, principal=VerifiedPrincipal('human', 1, frozenset({'Root'}))).allowed
    assert change(store)
    assert decision(store).reason == 'internal_acknowledgment_required'
    store.acknowledge_internal(2, 'v1')
    old_principal = VerifiedPrincipal('human', 2, frozenset({'PowerUser'}))
    assert decision(store, principal=old_principal).allowed
    assert change(store, 'remove')
    assert not decision(store, principal=old_principal).allowed


@pytest.mark.parametrize('ctx,reason', [(dict(existing_access_allowed=False), 'existing_access_denied'),
    (dict(readonly=True), 'readonly')])
def test_membership_never_overrides_existing_boundary(store, ctx, reason):
    change(store)
    store.acknowledge_internal(2, 'v1')
    assert decision(store, **ctx).reason == reason


def test_path_dependency_backend_and_prerequisites(store):
    change(store, group_key='path_ce')
    store.acknowledge_internal(2, 'v1')
    assert decision(store, 'path_ce', backend='topaz').reason == 'backend_required'
    assert decision(store, 'path_ce').allowed
    assert not decision(store, 'omni_contrasts').allowed
    change(store, group_key='omni_contrasts')
    assert decision(store, 'path_ce').allowed
    assert decision(store, 'omni_contrasts', enabled_features=frozenset()).reason == 'prerequisite_required'
    assert decision(store, 'omni_contrasts').allowed


def test_inspection_ordinary_and_legacy_noninterference(store):
    anonymous = VerifiedPrincipal()
    # A store that cannot possibly be queried proves public reads do not need it.
    assert decision(None, principal=anonymous, operation='inspect').allowed
    assert decision(None, 'rap_ts', principal=anonymous).allowed
    assert not decision(store, principal=anonymous).allowed
    assert decision(None, 'omni_contrasts', 'inspect', principal=anonymous).allowed
    assert not decision(store, 'batch_runner', 'inspect', principal=anonymous, requires_read_entitlement=True).allowed
    for role in ('Dev', 'Root'):
        assert decision(store, 'ag_fields', principal=VerifiedPrincipal('human', 1, frozenset({role}))).allowed
    assert not decision(store, 'ag_fields', principal=VerifiedPrincipal('human', 1, frozenset({'Admin'}))).allowed


def test_integration_is_explicit_and_resource_checks_still_apply(store):
    integration = VerifiedPrincipal('integration', integration_features=frozenset({'culvert_runner'}))
    assert decision(store, 'culvert_runner', principal=integration).allowed
    assert not decision(store, 'culvert_runner', principal=integration, existing_access_allowed=False).allowed
    assert not decision(store, principal=integration).allowed
    assert not decision(store, 'culvert_runner', principal=VerifiedPrincipal('integration')).allowed


def test_missing_group_and_database_failure_fail_explicitly(database, store):
    with database.begin() as connection:
        connection.execute(groups.delete().where(groups.c.key == 'openet_ts'))
    assert decision(store).reason == 'feature_access_configuration_error'
    with database.begin() as connection:
        memberships.drop(connection)
        groups.drop(connection)
    assert decision(store).reason == 'feature_access_unavailable'
    assert decision(store, operation='inspect').allowed


def test_registry_fields_and_validation():
    import yaml
    root = Path(__file__).parents[2] / 'wepppy/weppcloud/feature_registry'
    payload = yaml.safe_load((root / 'feature_registry.yaml').read_text())
    for key in ('openet_ts', 'batch_runner', 'culvert_runner'):
        assert BY_ID[key].access_mode == 'group_only'
    for key in ('omni_contrasts', 'path_ce', 'ag_fields'):
        assert BY_ID[key].access_mode == 'role_or_group'
    for values in ({'access_group': ' '}, {'access_mode': 'invalid'}, {'access_mode': 'group_only'}, {'access_group': 'x'}):
        bad = dict(payload, features=[dict(payload['features'][0], **values)])
        with pytest.raises(FeatureRegistryValidationError):
            validate_feature_registry_payload(bad, registry_dir=root)


def test_path_results_are_shared_without_action_entitlement(store):
    assert decision(None, 'path_ce', 'inspect', principal=VerifiedPrincipal()).allowed
    assert not decision(store, 'path_ce').allowed


def test_path_execution_does_not_query_contrast_membership(store, monkeypatch):
    change(store, group_key='path_ce')
    store.acknowledge_internal(2, 'v1')
    original = store.membership

    def only_path(user_id, group_key, **kwargs):
        assert group_key == 'path_ce'
        return original(user_id, group_key, **kwargs)

    monkeypatch.setattr(store, 'membership', only_path)
    assert decision(store, 'path_ce').allowed


def test_grant_expiry_revalidated_after_row_lock(database, store, monkeypatch):
    from threading import Event
    from wepppy.weppcloud.utils import feature_access_store as module
    initial = utc_now()
    current = [initial]
    monkeypatch.setattr(module, 'utc_now', lambda: current[0])
    waiting = Event()

    def observe_lock(connection, cursor, statement, parameters, context, executemany):
        if 'FOR UPDATE' in statement:
            waiting.set()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with database.begin() as connection:
            connection.execute(sa.select(users.c.id).where(users.c.id == 2).with_for_update())
            sa.event.listen(database, 'before_cursor_execute', observe_lock)
            try:
                pending = executor.submit(change, store, expires_at=initial + timedelta(seconds=1))
                assert waiting.wait(5)
                current[0] = initial + timedelta(seconds=2)
            finally:
                sa.event.remove(database, 'before_cursor_execute', observe_lock)
        with pytest.raises(FeatureAccessValidationError, match='future'):
            pending.result(timeout=5)
    assert count(database, memberships) == count(database, events) == 0


@pytest.mark.parametrize('feature_id', ['openet_ts', 'batch_runner', 'culvert_runner',
                                      'omni_contrasts', 'path_ce', 'ag_fields'])
@pytest.mark.parametrize('explicit_null', [False, True])
def test_governed_features_cannot_omit_access_metadata(feature_id, explicit_null):
    import yaml
    root = Path(__file__).parents[2] / 'wepppy/weppcloud/feature_registry'
    payload = yaml.safe_load((root / 'feature_registry.yaml').read_text())
    item = next(entry for entry in payload['features'] if entry['id'] == feature_id)
    for key in ('access_group', 'access_mode'):
        if explicit_null:
            item[key] = None
        else:
            del item[key]
    with pytest.raises(FeatureRegistryValidationError):
        validate_feature_registry_payload(payload, registry_dir=root)
    malformed = replace(BY_ID[feature_id], access_group=None, access_mode=None)
    for role in ('Dev', 'Root'):
        result = evaluate_feature_access(
            VerifiedPrincipal('human', 1, frozenset({role})), malformed, 'act',
            FeatureResourceContext(existing_access_allowed=True, backend='wbt',
                                   enabled_features=frozenset({'omni'})), None,
        )
        assert result.reason == 'feature_access_configuration_error'


def test_shared_contrast_results_preserve_existing_resource_denial():
    assert not decision(None, 'omni_contrasts', 'inspect', principal=VerifiedPrincipal(),
                        existing_access_allowed=False).allowed
