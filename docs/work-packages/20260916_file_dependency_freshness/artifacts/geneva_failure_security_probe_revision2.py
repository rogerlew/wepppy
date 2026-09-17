"""Additional disposable error/absence controls for real Geneva services."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

from wepppy.all_your_base.geo import raster_stacker
from wepppy.nodb.mods.geneva.collaborators import _cache_freshness as freshness
from wepppy.nodb.mods.geneva.collaborators.hru_map_geometry_service import GenevaHruMapGeometryService

_spec = importlib.util.spec_from_file_location(
    'geneva_security_fixtures', Path(__file__).with_name('geneva_implementation_security_probe_revision2.py'))
fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixtures)


def record(name, **data):
    Path(__file__).with_name(f'geneva_failure_security_{name}_revision2.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(data))


def test_orphan_mask_native_and_candidate_publication(tmp_path):
    geneva, root, source, bound = fixtures.fixture(tmp_path)
    direct = tmp_path / 'direct.tif'
    target = root / 'inputs/burn_severity_4class.tif'
    for path in (direct, target):
        fixtures.raster(path, 1)
        fixtures.mask(path)
        path.unlink()
    raster_stacker(source, bound, direct, resample='near')
    fixtures.align(geneva, source, bound)
    statuses = [json.loads(path.read_text()) for path in (root / 'cache_attempts').glob('*/status.json')]
    record('orphan_mask', old_native=fixtures.state(direct), current=fixtures.state(target), statuses=statuses)
    assert fixtures.state(target) == fixtures.state(direct)
    assert statuses[-1]['compatibility_native_overwrite'] is True


def test_postcommit_status_path_failure_does_not_reverse_success(tmp_path, monkeypatch):
    geneva, root, source, bound = fixtures.fixture(tmp_path)
    target = root / 'inputs/burn_severity_4class.tif'
    outside = tmp_path / 'outside.json'
    outside.write_text('private unrelated record')
    replace = os.replace

    def replace_then_change_status(source_path, destination, *args, **kwargs):
        result = replace(source_path, destination, *args, **kwargs)
        if Path(destination) == target:
            status = Path(source_path).parent / 'status.json'
            status.unlink()
            status.symlink_to(outside)
        return result

    monkeypatch.setattr(freshness.os, 'replace', replace_then_change_status)
    error = None
    try:
        fixtures.align(geneva, source, bound)
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc), 'code': getattr(exc, 'code', None)}
    record('postcommit_status_escape', error=error, output=fixtures.state(target), outside=outside.read_text())
    assert error is None
    assert outside.read_text() == 'private unrelated record'


def test_denied_existing_native_cache_read_keeps_prior_bytes(tmp_path):
    assert os.geteuid() != 0
    geneva, root, source, bound = fixtures.fixture(tmp_path)
    target = Path(fixtures.align(geneva, source, bound))
    prior = target.read_bytes()
    target.chmod(0)
    error = None
    try:
        fixtures.align(geneva, source, bound)
    except Exception as exc:
        error = type(exc).__name__
    finally:
        target.chmod(0o600)
    record('denied_native_read', error=error, prior_preserved=target.read_bytes() == prior)
    assert error is not None and target.read_bytes() == prior


def test_readonly_json_target_keeps_original_inode_authorization(tmp_path):
    assert os.geteuid() != 0
    geneva, root, source, bound = fixtures.fixture(tmp_path)
    fixtures.raster(root / 'hru_map.tif', 1)
    (root / 'hru_map_legend.json').write_text(json.dumps({'rows': [{'hru_value': 1, 'hru_id': 'one'}]}))
    target = root / 'hru_map_features.wgs.geojson'
    target.write_text('{"type":"FeatureCollection","features":[]}')
    prior = target.read_bytes()
    target.chmod(0o444)
    error = None
    try:
        GenevaHruMapGeometryService().query_feature_collection(geneva)
    except Exception as exc:
        error = type(exc).__name__
    record('readonly_json', error=error, prior_preserved=target.read_bytes() == prior)
    assert error == 'PermissionError' and target.read_bytes() == prior


def test_cached_json_target_disappears_after_read_returns_changed_source(tmp_path, monkeypatch):
    from wepppy.nodb.mods.geneva.collaborators import hru_map_geometry_service as geometry
    geneva, root, source, bound = fixtures.fixture(tmp_path)
    fixtures.raster(root / 'hru_map.tif', 1)
    (root / 'hru_map_legend.json').write_text(json.dumps({'rows': [{'hru_value': 1, 'hru_id': 'one'}]}))
    service = GenevaHruMapGeometryService()
    service.query_feature_collection(geneva)
    lexical = root / 'hru_map_features.wgs.geojson'
    target = root / 'outputs/selected.geojson'
    target.parent.mkdir()
    lexical.rename(target)
    lexical.symlink_to(target)
    acquire = geometry.geometry_inputs
    calls = 0

    def acquire_then_remove(*args, **kwargs):
        nonlocal calls
        result = acquire(*args, **kwargs)
        calls += 1
        if calls == 2:
            target.unlink()
        return result

    monkeypatch.setattr(geometry, 'geometry_inputs', acquire_then_remove)
    error = None
    try:
        service.query_feature_collection(geneva)
    except Exception as exc:
        error = {'type': type(exc).__name__, 'code': getattr(exc, 'code', None)}
    record('cached_target_disappeared', error=error, input_checks=calls)
    assert error is not None and error['code'] == 'changed_source'
