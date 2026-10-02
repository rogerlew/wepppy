"""FA-02 sharing retains actual private workflow boundaries."""
from types import SimpleNamespace

import pytest
from starlette.exceptions import HTTPException

from wepppy.query_engine.app.feature_access import require_datasets, visible_entries, require_root
from wepppy.query_engine.catalog import CatalogEntry

pytestmark = pytest.mark.microservice


@pytest.mark.parametrize('env', ['BATCH_RUNNER_ROOT', 'CULVERTS_ROOT'])
def test_query_private_workflow_roots_and_aliases_require_membership(tmp_path, monkeypatch, env):
    root = tmp_path / 'workflow'
    source = root / 'private' / 'runs' / 'child'
    source.mkdir(parents=True)
    monkeypatch.setenv(env, str(root))
    from wepppy.microservices.browse import auth
    monkeypatch.setattr(auth, '_run_is_public', lambda runid: False)
    request = SimpleNamespace(state=SimpleNamespace(), path_params={'runid': str(source)}, headers={}, cookies={})
    alias = tmp_path / 'ordinary'
    alias.symlink_to(source, target_is_directory=True)
    for path in (source, alias):
        with pytest.raises(HTTPException) as denied:
            require_root(request, path)
        assert denied.value.status_code == 401
    entry = CatalogEntry('safe.parquet', '.parquet', 10, '', fs_path=str(source / 'output.parquet'))
    assert visible_entries(request, tmp_path, [entry]) == []
    with pytest.raises(HTTPException):
        require_datasets(request, tmp_path, ['safe.parquet'], entries=[entry])


def test_query_public_batch_and_ordinary_anonymous_roots_remain_available(tmp_path, monkeypatch):
    root = tmp_path / 'batch'
    monkeypatch.setenv('BATCH_RUNNER_ROOT', str(root))
    from wepppy.microservices.browse import auth
    monkeypatch.setattr(auth, '_run_is_public', lambda runid: runid == 'batch;;public;;_base')
    request = SimpleNamespace(state=SimpleNamespace(), path_params={}, headers={}, cookies={})
    require_root(request, root / 'public' / 'runs' / 'child')
    require_root(request, tmp_path / 'ordinary')


def test_missing_integration_registration_returns_explicit_unavailable(tmp_path, monkeypatch):
    from wepppy.weppcloud.utils import feature_access_identity
    from wepppy.microservices.rq_engine.feature_access import verified_principal
    from wepppy.microservices.rq_engine.auth import AuthError
    monkeypatch.setattr(feature_access_identity, '__file__', str(tmp_path / 'identity.py'))
    with pytest.raises(AuthError) as unavailable:
        verified_principal({'token_class': 'service', 'sub': 'culvert-batch-submit-90d',
                            'aud': 'rq-engine', 'service_groups': ['culverts']})
    assert unavailable.value.status_code == 503
    assert unavailable.value.code == 'feature_access_unavailable'


def test_query_retained_contrasts_and_path_sources_are_public(tmp_path):
    request = SimpleNamespace(state=SimpleNamespace(), path_params={}, headers={}, cookies={})
    for relative in ('omni/contrasts.out.parquet', '_pups/omni/contrasts/1/output.parquet',
                     'path_ce/results.parquet'):
        entry = CatalogEntry('shared.parquet', '.parquet', 10, '', fs_path=str(tmp_path / relative))
        require_datasets(request, tmp_path, [entry.path], entries=[entry])
        assert visible_entries(request, tmp_path, [entry]) == [entry]


@pytest.mark.parametrize('method', ['GET', 'POST'])
def test_contrast_ancestry_does_not_restrict_ordinary_project_operations(tmp_path, monkeypatch, method):
    from flask import Flask
    from wepppy.weppcloud.utils import helpers
    monkeypatch.setattr(helpers, '_authorize_existing', lambda *args: None)
    monkeypatch.setattr(helpers, 'get_wd', lambda *args, **kwargs: str(tmp_path))
    app = Flask(__name__)
    with app.test_request_context('/runs/parent/cfg/?pup=omni/contrasts/1', method=method):
        helpers.authorize('parent', 'cfg')
        helpers.authorize('parent;;omni-contrast;;1', 'cfg')


def test_export_contrast_pup_is_shareable_and_traversal_still_rejected(tmp_path, monkeypatch):
    from wepppy.microservices.rq_engine import export_routes
    child = tmp_path / '_pups/omni/contrasts/1'
    child.mkdir(parents=True)
    monkeypatch.setattr(export_routes, 'get_wd', lambda *args, **kwargs: str(tmp_path))
    assert export_routes._resolve_export_wd('parent', SimpleNamespace(query_params={'pup': 'omni/contrasts/1'})) == str(child)
    with pytest.raises(FileNotFoundError):
        export_routes._resolve_export_wd('parent', SimpleNamespace(query_params={'pup': '../../'}))


@pytest.mark.parametrize('feature', ['openet_ts', 'omni_contrasts', 'path_ce'])
def test_public_inspection_does_not_resolve_account(monkeypatch, feature):
    from wepppy.microservices.rq_engine import feature_access

    def unavailable(claims):
        raise AssertionError('Public inspection must not resolve account identity')

    monkeypatch.setattr(feature_access, 'verified_principal', unavailable)
    feature_access.require_feature_access(None, feature, operation='inspect')


def test_cancellation_classifies_execution_instead_of_ancestry():
    from wepppy.microservices.rq_engine.feature_results import restricted_job_feature
    assert restricted_job_feature({'runid': 'parent;;omni-contrast;;1', 'description': 'run_wepp_rq(...)'}) is None
    assert restricted_job_feature({'description': 'run_omni_contrasts_rq(...)'}) == 'omni_contrasts'
    assert restricted_job_feature({'description': 'run_path_cost_effective_rq(...)'}) == 'path_ce'
