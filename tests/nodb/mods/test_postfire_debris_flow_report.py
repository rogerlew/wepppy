"""Accepted-record report projection against real immutable parquet bundles."""
from copy import deepcopy
from dataclasses import replace
import os
import shutil

import pytest

from wepppy.nodb.mods.postfire_debris_flow import report, production, results, rainfall_io
from wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow import PostfireDebrisFlow

pytestmark = pytest.mark.unit
IDENTITY = 'a' * 32
DNBR = 'b' * 32


@pytest.fixture
def saved(tmp_path):
    from tests.nodb.mods.test_postfire_debris_flow_results import inputs, build
    source = replace(inputs.__wrapped__(tmp_path), assessment_id=DNBR)
    folder = tmp_path / 'postfire_debris_flow' / 'attempts' / IDENTITY
    folder.mkdir(parents=True)
    build(source, folder / 'results')
    accepted = dict(id=IDENTITY, model='M1', snapshot=dict(dnbr=DNBR, frequency='noaa'),
                    completed_at='2026-09-15T00:00:00+00:00', artifacts={
                        str(p.relative_to(tmp_path)): production.signature(tmp_path, p, strong=True)
                        for p in (folder / 'results').iterdir() if p.name in production.FILES})
    controller = PostfireDebrisFlow(str(tmp_path), 'disturbed9002_wbt.cfg')
    # Fixture publication without the production publication/notification side effects.
    with controller.locked():
        controller._state['last_successful_run'] = accepted
    yield tmp_path, controller, accepted
    PostfireDebrisFlow.cleanup_all_instances()


def inventory(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_reader_retains_tables_and_two_argument_catalog_compatibility(saved):
    root, _, _ = saved
    assessment = report.open_assessment(root, 'config')
    assert assessment.catalog.design.num_rows == 12
    assert assessment.catalog.inverse.num_rows == 6
    legacy = results.ResultCatalog(assessment.catalog.manifest, assessment.catalog.events)
    assert results.list_events(legacy, duration_minutes=15)['total'] == 3


def test_real_saved_bundle_is_readonly_without_redisprep(saved, monkeypatch):
    root, _, _ = saved
    before = inventory(root)
    monkeypatch.setattr(production, 'get_state', lambda *a, **kw: pytest.fail('must not initialize RedisPrep'))
    assessment = report.open_assessment(root, 'config', IDENTITY)
    payload = report.view(assessment)
    assert payload['summary']['model'] == 'M1'
    assert payload['summary']['assessment_id'] == DNBR
    assert payload['summary']['current'] is None
    assert payload['summary']['coverage'] is None
    assert payload['events']['unfiltered_total'] == 3
    assert len(payload['inverse']) == 3
    assert not (root / 'redisprep.dump').exists()
    assert inventory(root) == before
    assert str(root) not in str(payload)


def test_absence_does_not_initialize_optional_state(tmp_path):
    assert report.view(report.open_assessment(tmp_path, 'config'))['status'] == 'absent'
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(report.ReportError, match='accepted assessment changed'):
        report.open_assessment(tmp_path, 'config', IDENTITY)


@pytest.mark.parametrize('current', [True, False])
def test_existing_currentness_and_newer_model_dont_relabel_saved_model(saved, monkeypatch, current):
    root, controller, _ = saved
    (root / 'redisprep.dump').write_text('existing')
    with controller.locked():
        controller._state['model'] = 'M3'
        controller._state['run_attempt'] = dict(id='c' * 32, model='M3', phase='failed',
                                               snapshot={}, created_at='today', retryable=True)
    def state(wd, config, **kwargs):
        assert kwargs == dict(reconcile=False)
        return dict(results=dict(id=IDENTITY, current=current))
    monkeypatch.setattr(production, 'get_state', state)
    before = inventory(root)
    value = report.view(report.open_assessment(root, 'config'))['summary']
    assert value['model'] == 'M1' and value['current'] is current
    assert value['newer_attempt'] == dict(id='c' * 32, model='M3', phase='failed')
    assert inventory(root) == before


def test_currentness_failure_preserves_values(saved, monkeypatch):
    root, _, _ = saved
    (root / 'redisprep.dump').write_text('existing')
    def broken(*args, **kwargs):
        raise ConnectionError('/private/dependency')
    monkeypatch.setattr(production, 'get_state', broken)
    assert report.open_assessment(root, 'config').current is None


def test_currentness_skips_symlinked_redisprep_without_following_target(saved, monkeypatch):
    root, _, _ = saved
    target = root / 'external-prep.json'
    target.write_bytes(b'{"private": "unchanged"}')
    (root / 'redisprep.dump').symlink_to(target)
    monkeypatch.setattr(production, 'get_state', lambda *a, **kw: pytest.fail('must not follow RedisPrep symlink'))
    before = target.read_bytes()
    assessment = report.open_assessment(root, 'config', IDENTITY)
    assert assessment.current is None
    assert report.view(assessment)['status'] == 'available'
    assert target.read_bytes() == before


@pytest.mark.parametrize('name', ['manifest.json', 'events.parquet', 'design.parquet', 'inverse.parquet'])
def test_corrupt_saved_file_is_explicit(saved, name):
    root, _, _ = saved
    (root / 'postfire_debris_flow' / 'attempts' / IDENTITY / 'results' / name).write_bytes(b'corrupted')
    with pytest.raises(report.ReportError) as exc:
        report.open_assessment(root, 'config', IDENTITY)
    assert exc.value.code == 'results_unavailable'


def test_acceptance_race_and_association_mismatch(saved, monkeypatch):
    root, controller, _ = saved
    actual = results.open_results
    def replace_while_reading(*args, **kwargs):
        catalog = actual(*args, **kwargs)
        with controller.locked():
            controller._state['last_successful_run']['completed_at'] = 'changed'
        return catalog
    monkeypatch.setattr(results, 'open_results', replace_while_reading)
    with pytest.raises(report.ReportError) as exc:
        report.open_assessment(root, 'config')
    assert exc.value.code == 'assessment_replaced'
    monkeypatch.setattr(results, 'open_results', actual)
    with controller.locked():
        controller._state['last_successful_run']['snapshot']['dnbr'] = 'd' * 32
    with pytest.raises(report.ReportError) as exc:
        report.open_assessment(root, 'config')
    assert exc.value.code == 'results_unavailable'


def test_download_verifies_descriptor_and_closes_on_failure(saved, monkeypatch):
    root, _, _ = saved
    assessment = report.open_assessment(root, 'config')
    with report.open_attachment(assessment, 'events.parquet') as stream:
        assert stream.read(4) == b'PAR1'
    opened = []
    original = rainfall_io.open_local
    def capture(*args):
        stream = original(*args)
        opened.append(stream)
        return stream
    monkeypatch.setattr(rainfall_io, 'open_local', capture)
    broken = replace(assessment, accepted=deepcopy(assessment.accepted))
    for signature in broken.accepted['artifacts'].values():
        signature[4] = '0' * 64
    with pytest.raises(report.ReportError):
        report.open_attachment(broken, 'events.parquet')
    assert opened[-1].closed
    with pytest.raises(report.ReportError) as exc:
        report.open_attachment(assessment, '../../secret')
    assert exc.value.status == 404
    assert 'valid_mask.tif' not in report.artifact_names(assessment)
    with pytest.raises(report.ReportError) as exc:
        report.open_attachment(assessment, 'valid_mask.tif')
    assert exc.value.status == 404


def test_download_rejects_symlink_swap_at_open_boundary(saved, monkeypatch):
    root, _, _ = saved
    assessment = report.open_assessment(root, 'config')
    actual = rainfall_io.regular
    def swap(path, limit):
        path = actual(path, limit)
        if path.name == 'events.parquet':
            target = path.with_name('replaced.parquet')
            path.rename(target)
            path.symlink_to(target)
        return path
    monkeypatch.setattr(rainfall_io, 'regular', swap)
    with pytest.raises(OSError):
        report.open_attachment(assessment, 'events.parquet')


def test_byte_identical_archive_restore_preserves_assessment_and_downloads(saved):
    root, _, accepted = saved
    original = report.view(report.open_assessment(root, 'config', IDENTITY))
    archive = root / 'archive-copy'
    archive.mkdir()
    for relative, signature in accepted['artifacts'].items():
        path = root / relative
        copy = archive / path.name
        shutil.copy2(path, copy)
        restored = path.with_suffix(path.suffix + '.restored')
        shutil.copyfile(copy, restored)
        os.utime(restored, ns=(signature[2] + 1000000000, signature[2] + 1000000000))
        restored.replace(path)
        assert path.stat().st_mtime_ns != signature[2]
        assert rainfall_io.digest(path) == signature[4]
    restored_assessment = report.open_assessment(root, 'config', IDENTITY)
    assert report.view(restored_assessment) == original
    assert restored_assessment.accepted == accepted
    for name in report.artifact_names(restored_assessment):
        with report.open_attachment(restored_assessment, name) as stream:
            assert stream.read() == (archive / name).read_bytes()


def test_download_rejects_descriptor_mutation_during_hashing(saved, monkeypatch):
    root, _, _ = saved
    assessment = report.open_assessment(root, 'config')
    original = rainfall_io.open_local
    opened = []
    class MutatingReader:
        def __init__(self, path, stream):
            self.path, self.stream, self.changed = path, stream, False
        def __getattr__(self, name):
            return getattr(self.stream, name)
        def read(self, size):
            value = self.stream.read(size)
            if not self.changed:
                self.changed = True
                metadata = self.path.stat()
                os.utime(self.path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1000000000))
            return value
    def capture(path, limit):
        stream = original(path, limit)
        opened.append(stream)
        return MutatingReader(path, stream)
    monkeypatch.setattr(rainfall_io, 'open_local', capture)
    with pytest.raises(report.ReportError) as exc:
        report.open_attachment(assessment, 'events.parquet')
    assert exc.value.code == 'results_unavailable'
    assert opened[-1].closed


@pytest.mark.parametrize('terrain_reason', ['watershed_area_mismatch', 'terrain_potentially_truncated'])
def test_validated_partial_m3_keeps_known_terrain_reason(saved, terrain_reason):
    """Controlled persisted M3 fixture exercises validation, not native derivation."""
    import json
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    import rasterio
    from wepppy.nodb.mods.postfire_debris_flow.predictor_v2 import M3_ARTIFACTS

    root, controller, _ = saved
    folder = root / 'postfire_debris_flow' / 'attempts' / IDENTITY / 'results'
    manifest = json.loads((folder / 'manifest.json').read_text())
    predictors = manifest['predictor_snapshot']
    coverage = dict(total_cells=10, valid_cells=10, excluded_cells=0, valid_fraction=1.,
                    policy='common_valid_v1', mask='valid_mask.tif', primary_valid_cells=10, fallback_valid_cells=0)
    predictors.update(schema_version=2, model='M3', support_policy='common_valid_v1',
                      availability='partial', coverage=coverage, soil_policy='recorded_depth_v1')
    predictors['tool']['version'] = 'controlled-fixture'
    predictors['prepared_sha256'] = {'terrain/manifest.json': 'd' * 64, 'soil/manifest.json': 'e' * 64}
    predictors['artifacts_sha256'] = {name: 'f' * 64 for name in M3_ARTIFACTS}
    mask = np.full((10, 10), 255, dtype='uint8')
    mask[0, :] = 1
    with rasterio.open(folder / 'valid_mask.tif', 'w', driver='GTiff', height=10, width=10,
                       count=1, dtype='uint8', nodata=255, crs=predictors['grid']['crs'],
                       transform=rasterio.Affine(*predictors['grid']['transform'])) as dataset:
        dataset.write(mask, 1)
    mask_hash = rainfall_io.digest(folder / 'valid_mask.tif')
    predictors['artifacts_sha256']['valid_mask.tif'] = mask_hash
    for key, unit in (('T', 'dimensionless'), ('F', 'fraction'), ('S', 'thickness_cm_div_254')):
        predictors['predictors'][key]['units'] = unit
        predictors['predictors'][key].pop('lower', None)
        predictors['predictors'][key].pop('upper', None)
    predictors['predictors']['T'].update(value=None, status='unavailable', reason=terrain_reason,
        support=dict(total_cells=10, valid_cells=0, coverage_fraction=0.),
        wbt_summary=dict(schema_version=1, status='complete', tool='D8UpstreamRelief',
                         tool_sha256=predictors['tool']['sha256'], tool_version='controlled-fixture',
                         grid=predictors['grid'], area_m2=9000., relief_m=30., full_upstream_cells=10,
                         outlet=[0, 0], terrain_valid=False, reason=terrain_reason))
    manifest.update(model='M3', coverage=coverage, artifacts_sha256={'valid_mask.tif': mask_hash})
    manifest['identity']['assessment_id'] = IDENTITY
    for name, schema in results.SCHEMAS.items():
        path = folder / f'{name}.parquet'
        rows = pq.read_table(path).to_pylist()
        for row in rows:
            if name == 'inverse' or row['rainfall_mm'] is not None:
                row.update(status='unavailable', reason='missing_predictors', probability=None)
            if name == 'inverse':
                row.update(rainfall_mm=None, intensity_mm_per_hour=None)
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
        manifest['tables'][name]['sha256'] = rainfall_io.digest(path)
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    with controller.locked():
        accepted = controller._state['last_successful_run']
        accepted.update(model='M3', snapshot=dict(dnbr=None, frequency='noaa'))
        accepted['artifacts'] = {str(path.relative_to(root)): production.signature(root, path, strong=True)
                                 for path in folder.iterdir() if path.name != 'incomplete.json'}
    payload = report.view(report.open_assessment(root, 'config', IDENTITY))
    assert payload['summary']['model'] == 'M3'
    assert payload['summary']['coverage']['valid_fraction'] == 1.
    assert next(p for p in payload['summary']['predictors'] if p['name'] == 'T')['reason'] == terrain_reason
    assert all(row['reason'] == 'missing_predictors' for row in payload['events']['rows'])
