"""Direct filesystem tests for catalog publication, durable intent and barriers."""
from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.query_engine import activate_query_engine, update_catalog_entry
from wepppy.query_engine import catalog_refresh as refresh

pytestmark = pytest.mark.integration


def _parquet(path: Path, values=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(values or {'topaz_id': [11], 'value': [1.0]}), path)


@pytest.fixture
def managed(tmp_path, monkeypatch):
    root = tmp_path / 'runs'
    wd = root / 'ab' / 'ab-run'
    wd.mkdir(parents=True)
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([{
        'path': str(root), 'namespace': 'test:runs',
        'coordination': str(tmp_path / 'locks'), 'layout': 'sharded'}]))
    monkeypatch.setenv('QUERY_CATALOG_REFRESH_ENABLED', 'true')
    return wd


def test_receipt_snapshot_does_not_ack_late_arrival(managed, monkeypatch):
    from wepppy.query_engine import activate as module
    _parquet(managed / 'soils/soils.parquet')
    first = refresh.record_catalog_refresh(managed, 'soils/soils.parquet')
    original = module._build_catalog
    late = []
    def collect(base):
        entries = original(base)
        late.append(refresh.record_catalog_refresh(base, 'soils/soils.parquet'))
        return entries
    monkeypatch.setattr(module, '_build_catalog', collect)
    result = refresh.refresh_catalog(managed)
    assert result['state'] == 'pending'
    pending = refresh.pending_catalog_requests(managed)
    assert [r['request_id'] for r in pending] == [late[0]['request_id']]
    assert first['request_id'] in result['acknowledged']
    assert all('_query_engine/refresh' not in e['path'] for e in json.loads(
        (managed / '_query_engine/catalog.json').read_text())['files'])
    monkeypatch.setattr(module, '_build_catalog', original)
    assert refresh.refresh_catalog(managed)['state'] == 'current'


def test_existing_schema_and_redirected_source_barrier(tmp_path):
    source = tmp_path / 'external/soil.parquet'
    _parquet(source)
    activate_query_engine(tmp_path, run_interchange=False)
    catalog_path = tmp_path / '_query_engine/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    entry = next(e for e in catalog['files'] if e['path'] == 'external/soil.parquet')
    entry['path'] = 'soils/soils.parquet'
    entry['fs_path'] = 'external/soil.parquet'
    refresh.publish_catalog(tmp_path, catalog)
    _parquet(source, {'wepp_id': [1], 'new_measure': [12.0]})
    result = refresh.ensure_catalog_fresh(tmp_path, ['soils/soils.parquet'])
    refreshed = next(e for e in result['files'] if e['path'] == 'soils/soils.parquet')
    assert refreshed['fs_path'] == 'external/soil.parquet'
    assert {f['name'] for f in refreshed['schema']['fields']} == {'wepp_id', 'new_measure'}


def test_deleted_subtree_entries_removed_and_unrelated_preserved(tmp_path):
    _parquet(tmp_path / 'soils/a.parquet')
    _parquet(tmp_path / 'landuse/b.parquet')
    activate_query_engine(tmp_path, run_interchange=False)
    (tmp_path / 'soils/a.parquet').unlink()
    update_catalog_entry(tmp_path, 'soils')
    paths = {e['path'] for e in json.loads((tmp_path / '_query_engine/catalog.json').read_text())['files']}
    assert 'soils/a.parquet' not in paths
    assert 'landuse/b.parquet' in paths


def test_old_scope_cannot_publish_after_replacement(managed):
    _parquet(managed / 'soils/a.parquet')
    snapshot = refresh.catalog_snapshot(managed)
    refresh.invalidate_catalog_incarnation(managed)
    with pytest.raises(refresh.CatalogRefreshConflict):
        refresh.publish_catalog(managed, {'files': [], 'root': str(managed), 'version': 1}, snapshot=snapshot)
    assert not (managed / '_query_engine/catalog.json').exists()


def test_pending_old_incarnations_retained_as_history(managed):
    child = managed / '_pups/omni/scenarios/burned'
    child.mkdir(parents=True)
    parent_req = refresh.record_catalog_refresh(managed)
    child_req = refresh.record_catalog_refresh(child)
    refresh.invalidate_catalog_incarnation(managed)
    assert refresh.pending_catalog_requests(managed) == []
    assert refresh.pending_catalog_requests(child) == []
    retained = list(managed.rglob('retired-*/*.json'))
    assert {json.loads(p.read_text())['request_id'] for p in retained} == {
        parent_req['request_id'], child_req['request_id']}


def test_readonly_barrier_does_not_create_refresh_metadata(tmp_path):
    _parquet(tmp_path / 'soils/a.parquet')
    # Deliberately build a legacy catalog without modern coordination records.
    from wepppy.query_engine.activate import _build_catalog
    (tmp_path / '_query_engine').mkdir()
    (tmp_path / '_query_engine/catalog.json').write_text(json.dumps({
        'root': str(tmp_path), 'version': 1, 'files': _build_catalog(tmp_path)}))
    (tmp_path / 'READONLY').touch()
    refresh.ensure_catalog_fresh(tmp_path, ['soils/a.parquet'])
    assert not (tmp_path / refresh.REFRESH_PATH).exists()
    _parquet(tmp_path / 'soils/a.parquet', {'changed': [1]})
    with pytest.raises(PermissionError):
        refresh.ensure_catalog_fresh(tmp_path, ['soils/a.parquet'])
    assert not (tmp_path / refresh.REFRESH_PATH).exists()


def test_strict_failure_keeps_receipt_and_legacy_sync_behavior(managed):
    bad = managed / 'soils/bad.parquet'
    bad.parent.mkdir()
    bad.write_bytes(b'not parquet')
    activate_query_engine(managed, run_interchange=False)
    before = (managed / '_query_engine/catalog.json').read_bytes()
    receipt = refresh.record_catalog_refresh(managed, 'soils/bad.parquet')
    with pytest.raises(pa.ArrowInvalid):
        refresh.refresh_catalog(managed)
    assert (managed / '_query_engine/catalog.json').read_bytes() == before
    assert refresh.pending_catalog_requests(managed)[0]['request_id'] == receipt['request_id']
    assert refresh.catalog_refresh_status(managed)['state'] == 'failed'


def test_concurrent_publication_cannot_overwrite_newer_catalog(managed):
    _parquet(managed / 'soils/a.parquet')
    activate_query_engine(managed, run_interchange=False)
    old = refresh.catalog_snapshot(managed)
    _parquet(managed / 'soils/b.parquet')
    update_catalog_entry(managed, 'soils/b.parquet')
    with pytest.raises(refresh.CatalogRefreshConflict):
        refresh.publish_catalog(managed, {'files': [], 'root': str(managed)}, snapshot=old)
    assert any(e['path'] == 'soils/b.parquet' for e in json.loads(
        (managed / '_query_engine/catalog.json').read_text())['files'])


def test_metadata_symlink_and_path_escape_rejected(managed, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (managed / '_query_engine').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        refresh.record_catalog_refresh(managed, 'soils/a.parquet')
    assert list(outside.iterdir()) == []


def _take_guard(wd, ready, done):
    with refresh.catalog_lifecycle_guard(wd):
        ready.set()
        done.wait(10)


def test_guard_is_shared_by_processes_and_nested_scopes(managed):
    child = managed / '_pups/omni/scenarios/test'
    child.mkdir(parents=True)
    context = multiprocessing.get_context('fork')
    ready, done = context.Event(), context.Event()
    process = context.Process(target=_take_guard, args=(managed, ready, done))
    process.start()
    assert ready.wait(5)
    child_ready, child_done = context.Event(), context.Event()
    contender = context.Process(target=_take_guard, args=(child, child_ready, child_done))
    contender.start()
    try:
        assert not child_ready.wait(.2)
        done.set()
        assert child_ready.wait(5)
    finally:
        done.set(); child_done.set()
        process.join(5); contender.join(5)
    assert process.exitcode == contender.exitcode == 0


def test_batch_owner_and_nested_scope_identity(tmp_path, monkeypatch):
    root = tmp_path / 'batch'
    child = root / 'batch-a/runs/run-a'
    child.mkdir(parents=True)
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([{
        'path': str(root), 'namespace': 'test:batch',
        'coordination': str(tmp_path / 'locks'), 'layout': 'batch'}]))
    top = refresh.resolve_scope(root / 'batch-a')
    nested = refresh.resolve_scope(child)
    assert top.owner == nested.owner
    assert top.scope_id != nested.scope_id



@pytest.mark.parametrize('component', ['_query_engine', '_query_engine/refresh',
                                      '_query_engine/refresh/requests', '_query_engine/refresh/attempts'])
def test_lifecycle_rejects_symlink_metadata_before_any_write(tmp_path, component):
    wd = tmp_path / 'project'
    wd.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    link = wd / component
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        refresh.invalidate_catalog_incarnation(wd)
    assert list(outside.iterdir()) == []


def test_targeted_and_subtree_refresh_exclude_metadata_aliases(tmp_path):
    _parquet(tmp_path / 'soils/a.parquet')
    activate_query_engine(tmp_path, run_interchange=False)
    (tmp_path / 'alias.json').symlink_to(tmp_path / '_query_engine/refresh/incarnation.json')
    (tmp_path / 'aliases').symlink_to(tmp_path / '_query_engine/refresh', target_is_directory=True)
    with pytest.raises(ValueError, match='metadata'):
        update_catalog_entry(tmp_path, 'alias.json')
    with pytest.raises(ValueError, match='metadata'):
        refresh.record_catalog_refresh(tmp_path, 'aliases')
    from wepppy.query_engine.activate import _build_catalog_subset
    entries = _build_catalog_subset(tmp_path, tmp_path)
    assert not any(e['path'] == 'alias.json' or e['path'].startswith('aliases/') for e in entries)


def test_readonly_transition_during_scan_retains_tree(managed, monkeypatch):
    from wepppy.query_engine import activate as module
    _parquet(managed / 'soils/a.parquet')
    refresh.record_catalog_refresh(managed)
    original = module._build_catalog
    captured = {}
    def collect(base):
        entries = original(base)
        (base / 'READONLY').touch()
        captured.update({str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()})
        return entries
    monkeypatch.setattr(module, '_build_catalog', collect)
    with pytest.raises(PermissionError):
        refresh.refresh_catalog(managed)
    assert {str(p.relative_to(managed)): p.read_bytes() for p in managed.rglob('*') if p.is_file()} == captured


def test_strict_scan_detects_omitted_required_asset(managed, monkeypatch):
    from wepppy.query_engine import activate as module
    _parquet(managed / 'soils/a.parquet')
    refresh.record_catalog_refresh(managed)
    original = module._build_catalog
    monkeypatch.setattr(module, '_build_catalog', lambda base: [e for e in original(base) if e['path'] != 'soils/a.parquet'])
    with pytest.raises(ValueError, match='skipped'):
        refresh.refresh_catalog(managed)
    assert refresh.pending_catalog_requests(managed)


def test_child_artifact_supersedes_inherited_parent(tmp_path):
    parent = tmp_path / 'run'
    child = parent / '_pups/omni/scenarios/a'
    child.mkdir(parents=True)
    _parquet(parent / 'soils/a.parquet')
    activate_query_engine(child, run_interchange=False)
    catalog_path = child / '_query_engine/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    from wepppy.query_engine.activate import _build_entry
    entry = _build_entry(parent, parent / 'soils/a.parquet')
    entry['fs_path'] = str(parent / 'soils/a.parquet')
    catalog['files'].append(entry)
    catalog_path.write_text(json.dumps(catalog))
    _parquet(child / 'soils/a.parquet', {'child': [1]})
    refresh.record_catalog_refresh(child, 'soils/a.parquet')
    refresh.refresh_catalog(child)
    result = json.loads(catalog_path.read_text())
    selected = next(e for e in result['files'] if e['path'] == 'soils/a.parquet')
    assert selected['schema']['fields'][0]['name'] == 'child'
    assert selected['fs_path'] == 'soils/a.parquet'


def test_receipt_repairs_schema_even_when_size_and_timestamp_match(managed):
    import os
    asset = managed / 'soils/a.parquet'
    _parquet(asset, {'before': [1]})
    activate_query_engine(managed, run_interchange=False)
    original = asset.stat()
    _parquet(asset, {'afterx': [1]})
    assert asset.stat().st_size == original.st_size
    os.utime(asset, ns=(original.st_atime_ns, original.st_mtime_ns))
    refresh.record_catalog_refresh(managed, 'soils/a.parquet')
    refresh.refresh_catalog(managed)
    catalog = json.loads((managed / '_query_engine/catalog.json').read_text())
    entry = next(e for e in catalog['files'] if e['path'] == 'soils/a.parquet')
    assert entry['schema']['fields'][0]['name'] == 'afterx'
    assert not refresh.pending_catalog_requests(managed)


def test_schema_change_after_collection_is_not_acknowledged(managed, monkeypatch):
    import os
    asset = managed / 'soils/a.parquet'
    _parquet(asset, {'before': [1]})
    activate_query_engine(managed, run_interchange=False)
    original_stat = asset.stat()
    old_catalog = (managed / '_query_engine/catalog.json').read_bytes()
    refresh.record_catalog_refresh(managed, 'soils/a.parquet')
    original = refresh._updated_catalog
    def collect(*args, **kwargs):
        candidate = original(*args, **kwargs)
        _parquet(asset, {'afterx': [1]})
        assert asset.stat().st_size == original_stat.st_size
        os.utime(asset, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        return candidate
    monkeypatch.setattr(refresh, '_updated_catalog', collect)
    with pytest.raises(refresh.CatalogRefreshConflict, match='schema changed'):
        refresh.refresh_catalog(managed)
    assert (managed / '_query_engine/catalog.json').read_bytes() == old_catalog
    assert refresh.pending_catalog_requests(managed)


def test_request_admission_keeps_receipt_incarnation_across_lifecycle(managed, monkeypatch):
    from wepppy.rq import query_catalog_rq
    original = refresh.record_catalog_refresh
    captured = {}
    def record(*args, **kwargs):
        receipt = original(*args, **kwargs)
        captured['original'] = receipt['incarnation']
        captured['replacement'] = refresh.invalidate_catalog_incarnation(managed)
        return receipt
    def enqueue(wd, *, scope):
        captured['admitted'] = scope['incarnation']
        return {'state': 'pending'}
    monkeypatch.setattr(refresh, 'record_catalog_refresh', record)
    monkeypatch.setattr(query_catalog_rq, 'enqueue_catalog_refresh', enqueue)
    refresh.request_catalog_refresh(managed, 'soils/a.parquet')
    assert captured['admitted'] == captured['original'] != captured['replacement']


def test_barrier_reloads_catalog_when_receipt_is_acknowledged_during_discovery(managed, monkeypatch):
    import threading
    _parquet(managed / 'soils/a.parquet', {'before': [1]})
    activate_query_engine(managed, run_interchange=False)
    _parquet(managed / 'soils/a.parquet', {'afterx': [1]})
    refresh.record_catalog_refresh(managed, 'soils/a.parquet')
    discovered = threading.Event()
    acknowledged = threading.Event()
    original = refresh._read_json
    result = {}
    def read(path):
        if threading.current_thread().name == 'catalog-reader' and path.parent.name == 'requests':
            discovered.set()
            assert acknowledged.wait(10)
        return original(path)
    def reader():
        try:
            result['catalog'] = refresh.ensure_catalog_fresh(managed)
        except BaseException as error:
            result['error'] = error
    monkeypatch.setattr(refresh, '_read_json', read)
    thread = threading.Thread(target=reader, name='catalog-reader')
    thread.start()
    try:
        assert discovered.wait(5)
        refresh.refresh_catalog(managed)
    finally:
        acknowledged.set()
        thread.join(10)
    assert 'error' not in result
    entry = next(e for e in result['catalog']['files'] if e['path'] == 'soils/a.parquet')
    assert entry['schema']['fields'][0]['name'] == 'afterx'


def test_full_refresh_accepts_native_parquet_type_spellings(managed):
    from datetime import date
    _parquet(managed / 'dates.parquet', {'day': [date(2026, 10, 23)]})
    refresh.record_catalog_refresh(managed)
    assert refresh.refresh_catalog(managed)['state'] == 'current'


def test_queued_child_cannot_publish_after_owner_freeze(managed):
    child = managed / '_pups/omni/scenarios/child'
    _parquet(child / 'soils/a.parquet')
    receipt = refresh.record_catalog_refresh(child, 'soils/a.parquet')
    (managed / 'READONLY').touch()
    before = {str(p.relative_to(managed)): p.read_bytes() for p in managed.rglob('*') if p.is_file()}
    with pytest.raises(PermissionError):
        refresh.refresh_catalog(child, expected_incarnation=receipt['incarnation'])
    with pytest.raises(PermissionError):
        refresh.record_catalog_refresh(child, 'soils/a.parquet')
    assert {str(p.relative_to(managed)): p.read_bytes() for p in managed.rglob('*') if p.is_file()} == before


@pytest.mark.parametrize('malformed', ['{malformed catalog', '{"root": "/old", "version": 1, "files": null}', '{"root": "/old", "version": 1, "files": [{}]}', '{}'])
@pytest.mark.parametrize('barrier', [False, True])
def test_malformed_catalog_is_rebuilt_from_readable_artifacts(managed, barrier, malformed):
    _parquet(managed / 'soils/a.parquet', {'observed': [1]})
    catalog_path = managed / '_query_engine/catalog.json'
    catalog_path.parent.mkdir()
    catalog_path.write_text(malformed)
    refresh.record_catalog_refresh(managed, 'soils/a.parquet')
    if barrier:
        refresh.ensure_catalog_fresh(managed, ['soils/a.parquet'])
    else:
        refresh.refresh_catalog(managed)
    catalog = json.loads(catalog_path.read_text())
    entry = next(e for e in catalog['files'] if e['path'] == 'soils/a.parquet')
    assert entry['schema']['fields'][0]['name'] == 'observed'
    assert not refresh.pending_catalog_requests(managed)
    assert refresh.catalog_refresh_status(managed)['state'] == 'current'
    import base64
    evidence = next((managed / '_query_engine/refresh/attempts').glob('malformed-*.json'))
    assert base64.b64decode(json.loads(evidence.read_text())['catalog_bytes_base64']) == malformed.encode()


def test_atomic_json_preserves_existing_mode_and_owner(tmp_path):
    import os
    import stat
    directory = tmp_path / 'shared'
    directory.mkdir()
    directory.chmod(0o2770)
    path = directory / 'catalog.json'
    path.write_text('{}')
    path.chmod(0o640)
    before = path.stat()
    old_umask = os.umask(0o022)
    try:
        refresh.atomic_json(path, {'published': True})
    finally:
        os.umask(old_umask)
    after = path.stat()
    assert stat.S_IMODE(after.st_mode) == 0o640
    assert (after.st_uid, after.st_gid) == (before.st_uid, before.st_gid)
    assert after.st_gid == directory.stat().st_gid
    assert json.loads(path.read_text()) == {'published': True}


def test_atomic_json_refuses_failed_permission_preservation(tmp_path, monkeypatch):
    import os
    path = tmp_path / 'catalog.json'
    path.write_text('{"original": true}')
    path.chmod(0o640)
    before = path.read_bytes()
    def denied(fd, mode):
        raise PermissionError('mode preservation denied')
    monkeypatch.setattr(os, 'fchmod', denied)
    with pytest.raises(PermissionError, match='preservation denied'):
        refresh.atomic_json(path, {'published': True})
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_json_preserves_actual_linux_access_acl(tmp_path):
    import os
    import struct
    path = tmp_path / 'catalog.json'
    path.write_text('{}')
    acl = struct.pack('<I', 2) + b''.join(
        struct.pack('<HHI', tag, perm, ident)
        for tag, perm, ident in [(1, 6, 0xffffffff), (2, 0, 65534),
                                (4, 4, 0xffffffff), (16, 4, 0xffffffff), (32, 4, 0xffffffff)])
    os.setxattr(path, 'system.posix_acl_access', acl)
    os.setxattr(path, 'user.catalog_provenance', b'private metadata')
    before = {name: os.getxattr(path, name) for name in os.listxattr(path)}
    refresh.atomic_json(path, {'published': True})
    assert {name: os.getxattr(path, name) for name in os.listxattr(path)} == before


def test_atomic_json_xattr_failure_retains_original(tmp_path, monkeypatch):
    import os
    path = tmp_path / 'catalog.json'
    path.write_text('{"original": true}')
    os.setxattr(path, 'user.catalog_provenance', b'private metadata')
    before = path.read_bytes()
    def denied(*args, **kwargs):
        raise PermissionError('xattr preservation denied')
    monkeypatch.setattr(os, 'setxattr', denied)
    with pytest.raises(PermissionError, match='xattr preservation denied'):
        refresh.atomic_json(path, {'published': True})
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('creation_umask', [0o002, 0o022])
@pytest.mark.parametrize('default_acl', [False, True])
def test_atomic_json_new_file_matches_legacy_creation(tmp_path, creation_umask, default_acl):
    import os
    import stat
    import struct
    directory = tmp_path / 'shared'
    directory.mkdir()
    directory.chmod(0o2770)
    if default_acl:
        acl = struct.pack('<I', 2) + b''.join(
            struct.pack('<HHI', tag, perm, ident)
            for tag, perm, ident in [(1, 6, 0xffffffff), (2, 0, 65534),
                                    (4, 4, 0xffffffff), (16, 4, 0xffffffff), (32, 4, 0xffffffff)])
        os.setxattr(directory, 'system.posix_acl_default', acl)
    reference, actual = directory / 'reference.json', directory / 'actual.json'
    old_umask = os.umask(creation_umask)
    try:
        reference.write_text('{}')
        refresh.atomic_json(actual, {})
    finally:
        os.umask(old_umask)
    expected, observed = reference.stat(), actual.stat()
    assert (stat.S_IMODE(observed.st_mode), observed.st_uid, observed.st_gid) == (
        stat.S_IMODE(expected.st_mode), expected.st_uid, expected.st_gid)
    assert observed.st_gid == directory.stat().st_gid
    assert {n: os.getxattr(actual, n) for n in os.listxattr(actual)} == {
        n: os.getxattr(reference, n) for n in os.listxattr(reference)}


def test_malformed_catalog_history_preserves_protected_metadata(managed):
    import os
    import stat
    import struct
    _parquet(managed / 'soils/a.parquet')
    path = managed / '_query_engine/catalog.json'
    path.parent.mkdir()
    path.write_text('{malformed')
    acl = struct.pack('<I', 2) + b''.join(
        struct.pack('<HHI', tag, perm, ident)
        for tag, perm, ident in [(1, 6, 0xffffffff), (2, 0, 65534),
                                (4, 4, 0xffffffff), (16, 4, 0xffffffff), (32, 0, 0xffffffff)])
    os.setxattr(path, 'system.posix_acl_access', acl)
    before = path.stat()
    attributes = {n: os.getxattr(path, n) for n in os.listxattr(path)}
    refresh.record_catalog_refresh(managed)
    refresh.refresh_catalog(managed)
    history = next((managed / '_query_engine/refresh/attempts').glob('malformed-*.json'))
    for published in (path, history):
        observed = published.stat()
        assert (stat.S_IMODE(observed.st_mode), observed.st_uid, observed.st_gid) == (
            0o640, before.st_uid, before.st_gid)
        assert {n: os.getxattr(published, n) for n in os.listxattr(published)} == attributes
