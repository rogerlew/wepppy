"""FA-01 retained artifact and response boundaries, including renamed sources."""
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
from starlette.exceptions import HTTPException

from wepppy.weppcloud.utils.feature_access_data import protected_source, protected_bundle
from wepppy.microservices.rq_engine.feature_results import project_job_results
from wepppy.query_engine.app.feature_access import require_datasets, visible_entries, require_root
from wepppy.query_engine.catalog import CatalogEntry

pytestmark = pytest.mark.microservice


def test_alias_and_renamed_export_keep_contrast_classification(tmp_path):
    protected = tmp_path / '_pups/omni/contrasts/1/wepp/output/result.parquet'
    protected.parent.mkdir(parents=True)
    protected.write_bytes(b'protected')
    alias = tmp_path / 'innocent.parquet'
    alias.symlink_to(protected)
    assert protected_source(alias)
    artifact = tmp_path / 'export/features/artifacts/test/hillslopes.parquet'
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b'renamed')
    (artifact.parent / 'manifest.json').write_text(json.dumps({'layers': [{'context': 'contrast'}]}))
    assert protected_source(artifact)
    assert protected_source(artifact.parent / 'manifest.json')
    assert not protected_source(tmp_path / 'wepp/output/ordinary.parquet')


@pytest.mark.parametrize('member,body', [
    ('omni/contrasts.out.parquet', b'protected'),
    ('manifest.json', json.dumps({'request': {'resolved': {'contrast_ids': ['1']}}}).encode()),
])
def test_zip_classification_uses_members_and_existing_manifest(tmp_path, member, body):
    bundle = tmp_path / 'renamed.zip'
    with zipfile.ZipFile(bundle, 'w') as archive:
        archive.writestr(member, body)
    assert protected_bundle(bundle)


def test_query_checks_effective_catalog_source_before_execution(tmp_path):
    request = SimpleNamespace(state=SimpleNamespace(), path_params={'runid': 'run'}, headers={}, cookies={})
    entry = CatalogEntry('safe.parquet', '.parquet', 10, '',
                         fs_path=str(tmp_path / 'omni/contrasts.out.parquet'))
    with pytest.raises(HTTPException) as denied:
        require_datasets(request, tmp_path, ['safe.parquet'], entries=[entry])
    assert denied.value.status_code == 403
    assert visible_entries(request, tmp_path, [entry]) == []
    ordinary = CatalogEntry('wepp/output/hillslopes.parquet', '.parquet', 10, '')
    require_datasets(request, tmp_path, [ordinary.path], entries=[ordinary])
    assert visible_entries(request, tmp_path, [ordinary]) == [ordinary]


def test_recursive_job_projection_retains_ordinary_results_and_queue_state():
    protected = {'job_id': 'child', 'status': 'finished', 'description': 'run_path_cost_effective_rq(run)',
                 'result': {'total_cost': 9000}, 'exc_info': 'selected hillside 10',
                 'error': {'details': 'cost 9000'}, 'queue': {'rank': 1}, 'children': {}}
    root = {'job_id': 'root', 'status': 'finished', 'result': {'ordinary': 2},
            'exc_info': 'propagated protected child error', 'metadata': {'cost': 9000},
            'children': {'0': [protected]}}
    result = project_job_results(root, None)
    assert result['result'] == {'ordinary': 2}
    assert 'exc_info' not in result and 'metadata' not in result
    child = result['children']['0'][0]
    assert child['result'] is None and child['exc_info'] is None
    assert 'error' not in child
    assert child['queue'] == {'rank': 1} and child['status'] == 'finished'
    assert root['children']['0'][0]['result'] == {'total_cost': 9000}


def test_mixed_job_result_projects_only_explicit_nonprotected_fields():
    result = project_job_results({'job_id': 'job', 'result': {'job_id': 'next', 'contrasts': [123],
                                                         'unknown_solver_value': 123}}, None)
    assert result['result'] == {'job_id': 'next'}


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


def test_raw_query_catalog_and_embedded_catalog_keep_embargo(tmp_path):
    catalog = tmp_path / '_query_engine/catalog.json'
    catalog.parent.mkdir()
    payload = {'root': str(tmp_path), 'files': [{'path': 'omni/contrasts.out.parquet'}]}
    catalog.write_text(json.dumps(payload))
    assert protected_source(catalog)
    archive_path = tmp_path / 'catalog-only.zip'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('_query_engine/catalog.json', json.dumps(payload))
    assert protected_bundle(archive_path)
    catalog.write_text(json.dumps({'files': [{'path': 'wepp/output/hillslopes.parquet'}]}))
    assert not protected_source(catalog)


def test_job_projection_preserves_missing_children():
    node = {'job_id': 'parent', 'status': 'finished', 'children': {'0': [None]}}
    assert project_job_results(node, None) == node


@pytest.mark.parametrize('method', ['GET', 'POST'])
def test_flask_legacy_pup_alias_requires_contrast_admission(tmp_path, monkeypatch, method):
    from flask import Flask
    from werkzeug.exceptions import HTTPException as FlaskHTTPException
    from wepppy.weppcloud.utils import helpers, feature_access_flask
    from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal, FeatureResourceContext
    monkeypatch.setattr(helpers, '_authorize_existing', lambda *args: None)
    monkeypatch.setattr(helpers, 'get_wd', lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(feature_access_flask, 'current_principal', lambda: VerifiedPrincipal())
    monkeypatch.setattr(feature_access_flask, 'resource_context', lambda *args, **kwargs: FeatureResourceContext(
        existing_access_allowed=True, backend='wbt', enabled_features=frozenset({'omni'})))
    app = Flask(__name__)
    with app.test_request_context('/runs/parent/cfg/?pup=omni/contrasts/1', method=method):
        with pytest.raises(FlaskHTTPException) as denied:
            helpers.authorize('parent', 'cfg')
        assert denied.value.get_response().status_code == 403
    with app.test_request_context('/runs/parent/cfg/?pup=omni/scenarios/ordinary', method=method):
        helpers.authorize('parent', 'cfg')


def test_export_legacy_pup_alias_checks_read_entitlement(tmp_path, monkeypatch):
    from wepppy.microservices.rq_engine import export_routes
    from wepppy.microservices.rq_engine.auth import AuthError
    protected = tmp_path / '_pups/omni/contrasts/1'
    ordinary = tmp_path / '_pups/omni/scenarios/ordinary'
    protected.mkdir(parents=True)
    ordinary.mkdir(parents=True)
    monkeypatch.setattr(export_routes, 'get_wd', lambda *args, **kwargs: str(tmp_path))
    with pytest.raises(AuthError) as denied:
        export_routes._resolve_export_wd('parent', SimpleNamespace(query_params={'pup': 'omni/contrasts/1'}))
    assert denied.value.status_code == 403
    assert export_routes._resolve_export_wd('parent', SimpleNamespace(query_params={'pup': 'omni/scenarios/ordinary'})) == str(ordinary)


def test_public_inspection_does_not_resolve_account(monkeypatch):
    from wepppy.microservices.rq_engine import feature_access

    def unavailable(claims):
        raise AssertionError('Public inspection must not resolve account identity')

    monkeypatch.setattr(feature_access, 'verified_principal', unavailable)
    feature_access.require_feature_access({'token_class': 'user', 'sub': '1'}, 'openet_ts', operation='inspect')


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
