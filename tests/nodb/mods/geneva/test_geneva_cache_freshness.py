"""Actual native producer/cache checks for Geneva's bounded freshness proof."""
import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators.hru_map_geometry_service import GenevaHruMapGeometryService
from wepppy.nodb.mods.geneva.collaborators.hsg_assignment_service import GenevaHsgAssignmentService
from wepppy.nodb.mods.geneva.collaborators import _cache_freshness as freshness
from wepppy.nodb.mods.geneva.errors import GenevaKernelError

pytestmark = pytest.mark.integration


def raster(path, value=7, *, x=500000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, 'w', driver='GTiff', width=2, height=2, count=1,
                       dtype='int16', nodata=0, crs='EPSG:32611',
                       transform=from_origin(x, 5000000, 30, 30)) as dataset:
        dataset.write(np.full((2, 2), value, dtype='int16'), 1)
    return path


@pytest.fixture
def project(tmp_path):
    geneva = SimpleNamespace(wd=str(tmp_path), artifact_io=GenevaArtifactIO())
    raster(geneva.artifact_io.resolve_path(geneva.wd, 'hru_map.tif'))
    geneva.artifact_io.write_json(geneva.wd, 'hru_map_legend.json', {
        'rows': [{'hru_value': 7, 'hru_id': 'seven'}, {'hru_value': 8, 'hru_id': 'eight'}]})
    return geneva


def test_geometry_content_and_legend_changes_with_restored_timestamp(project):
    service = GenevaHruMapGeometryService()
    def query():
        return service.query_feature_collection(project)['feature_collection']
    first = query()
    target = project.artifact_io.resolve_path(project.wd, 'hru_map_features.wgs.geojson')
    version = target.stat().st_ino
    source = project.artifact_io.resolve_path(project.wd, 'hru_map.tif')
    os.utime(source, None)
    assert query() == first
    assert target.stat().st_ino == version
    before = source.stat()
    with rasterio.open(source, 'r+') as dataset:
        dataset.write(np.full((2, 2), 8, dtype='int16'), 1)
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert query()['features'][0]['properties']['hru_id'] == 'eight'
    legend = project.artifact_io.resolve_path(project.wd, 'hru_map_legend.json')
    before = legend.stat()
    legend.write_text(legend.read_text().replace('eight', 'EIGHT'))
    os.utime(legend, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert query()['features'][0]['properties']['hru_id'] == 'EIGHT'


def test_geometry_native_aba_rejected_prior_artifact_preserved(project, monkeypatch):
    service = GenevaHruMapGeometryService()
    service.query_feature_collection(project)
    target = project.artifact_io.resolve_path(project.wd, 'hru_map_features.wgs.geojson')
    original = target.read_bytes()
    source = project.artifact_io.resolve_path(project.wd, 'hru_map.tif')
    import rasterio.features
    original_shapes = rasterio.features.shapes
    def racing_shapes(*args, **kwargs):
        data, info = source.read_bytes(), source.stat()
        with source.open('r+b') as stream:
            stream.seek(-1, 2)
            stream.write(b'X')
        source.write_bytes(data)
        os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns))
        yield from original_shapes(*args, **kwargs)
    monkeypatch.setattr(rasterio.features, 'shapes', racing_shapes)
    with pytest.raises((GenevaKernelError, OSError)):
        service._materialize_feature_collection_from_raster(project, source_path=source)
    assert target.read_bytes() == original
    statuses = [json.loads(path.read_text()) for path in target.parent.glob('cache_attempts/*/status.json')]
    assert any(status['status'] == 'failed' for status in statuses)


def test_alignment_pixels_and_bound_profile_refresh(project):
    source = raster(Path(project.wd) / 'source.tif', 3)
    bound = raster(Path(project.wd) / 'bound.tif', 1)
    service = GenevaHsgAssignmentService()
    def build():
        return Path(service._materialize_auto_burn_severity(
            project, source_path=str(source), bound_tif=str(bound)))
    target = build()
    version = target.stat().st_ino
    assert build().stat().st_ino == version
    before = source.stat()
    with rasterio.open(source, 'r+') as dataset:
        dataset.write(np.full((2, 2), 4, dtype='int16'), 1)
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    build()
    with rasterio.open(target) as dataset:
        assert np.all(dataset.read(1) == 4)
        assert json.loads(dataset.tags()[freshness.TIFF_PROOF])['version'] == 1
    raster(bound, 1, x=500030)
    build()
    with rasterio.open(target) as dataset:
        assert dataset.transform.c == 500030


def test_alignment_old_external_mask_native_compatibility(project):
    source = raster(Path(project.wd) / 'source.tif', 3)
    bound = raster(Path(project.wd) / 'bound.tif', 1)
    service = GenevaHsgAssignmentService()
    def build():
        return Path(service._materialize_auto_burn_severity(
            project, source_path=str(source), bound_tif=str(bound)))
    target = build()
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(target, 'r+') as dataset:
            dataset.write_mask(np.zeros((2, 2), dtype='uint8'))
    assert Path(str(target) + '.msk').exists()
    build()
    with rasterio.open(target) as dataset:
        assert np.all(dataset.dataset_mask() == 255)
        assert freshness.TIFF_PROOF not in dataset.tags()
    assert not Path(str(target) + '.msk').exists()
    build()
    with rasterio.open(target) as dataset:
        assert freshness.TIFF_PROOF in dataset.tags()


@pytest.mark.parametrize('mutation', ['alias', 'mask'])
def test_publication_rechecks_destination_after_input_validation(project, mutation):
    root = Path(project.wd) / 'geneva'
    original = raster(root / 'original.tif', 1)
    alternate = raster(root / 'alternate.tif', 2)
    link = root / 'result.tif'
    link.symlink_to(original.name)
    prior = original.read_bytes()
    with pytest.raises(GenevaKernelError) as failure:
        with freshness._Attempt(project, 'result.tif', 'aligned_burn') as attempt:
            candidate = raster(attempt.candidate('candidate.tif'), 3)
            def mutate():
                if mutation == 'alias':
                    link.unlink()
                    link.symlink_to(alternate.name)
                else:
                    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
                        with rasterio.open(original, 'r+') as dataset:
                            dataset.write_mask(np.zeros((2, 2), dtype='uint8'))
            attempt.publish(candidate, clean_tiff=True, validate=mutate)
    assert failure.value.code == 'changed_source'
    assert original.read_bytes() == prior


def test_alignment_preserves_native_readonly_inode_replacement(project):
    source = raster(Path(project.wd) / 'source.tif', 3)
    bound = raster(Path(project.wd) / 'bound.tif', 1)
    service = GenevaHsgAssignmentService()
    def build():
        return Path(service._materialize_auto_burn_severity(
            project, source_path=str(source), bound_tif=str(bound)))
    target = build()
    target.chmod(0o444)
    raster(source, 4)
    build()
    with rasterio.open(target) as dataset:
        assert np.all(dataset.read(1) == 4)
    assert target.stat().st_mode & 0o777 == 0o444


def test_geometry_changed_input_native_error_is_conflict(project, monkeypatch):
    service = GenevaHruMapGeometryService()
    service.query_feature_collection(project)
    target = project.artifact_io.resolve_path(project.wd, 'hru_map_features.wgs.geojson')
    previous = target.read_bytes()
    source = project.artifact_io.resolve_path(project.wd, 'hru_map.tif')
    load_legend = service._load_hru_row_by_value
    def change_before_native(owner):
        rows = load_legend(owner)
        raster(source, 99)
        return rows
    monkeypatch.setattr(service, '_load_hru_row_by_value', change_before_native)
    with pytest.raises(GenevaKernelError) as failure:
        service._materialize_feature_collection_from_raster(project, source_path=source)
    assert failure.value.code == 'changed_source'
    assert target.read_bytes() == previous


def test_alignment_changed_source_native_error_is_conflict(project, monkeypatch):
    from wepppy.nodb.mods.geneva.collaborators import hsg_assignment_service as module
    source = raster(Path(project.wd) / 'source.tif', 3)
    bound = raster(Path(project.wd) / 'bound.tif', 1)
    service = GenevaHsgAssignmentService()
    def build():
        return Path(service._materialize_auto_burn_severity(
            project, source_path=str(source), bound_tif=str(bound)))
    target = build()
    previous = target.read_bytes()
    raster(source, 4)
    stacker = module.raster_stacker
    def change_then_native(*args, **kwargs):
        source.write_bytes(b'corrupt')
        return stacker(*args, **kwargs)
    monkeypatch.setattr(module, 'raster_stacker', change_then_native)
    with pytest.raises(GenevaKernelError) as failure:
        build()
    assert failure.value.code == 'changed_source'
    assert target.read_bytes() == previous


def test_missing_main_with_orphan_mask_is_not_clean(project):
    target = Path(project.wd) / 'geneva' / 'absent.tif'
    raster(Path(str(target) + '.msk'), 0)
    assert freshness.clean_tiff_proof(target) == (False, None, None)


def test_status_containment_error_after_commit_is_diagnostic(project, caplog):
    outside = Path(project.wd) / 'outside.json'
    outside.write_text('unchanged')
    with freshness._Attempt(project, 'result.json', 'hru_geometry') as attempt:
        candidate = attempt.candidate('candidate.json')
        candidate.write_text('{}')
        attempt.publish(candidate)
        status = attempt.root / 'status.json'
        status.unlink()
        status.symlink_to(outside)
    assert attempt.target.read_text() == '{}'
    assert outside.read_text() == 'unchanged'
    assert 'Unable to record Geneva derivation status' in caplog.text


def test_canonical_archive_preserves_geneva_failed_and_accepted_work(project):
    import shutil
    import zipfile
    from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq
    from wepppy.nodb.project_config_update import project_config_lifecycle_guard

    service = GenevaHruMapGeometryService()
    expected_payload = service.query_feature_collection(project)
    with pytest.raises(RuntimeError, match='injected failure'):
        with freshness._Attempt(project, 'hru_map_features.wgs.geojson', 'hru_geometry') as attempt:
            attempt.candidate('candidate.geojson').write_text('partial native work')
            raise RuntimeError('injected failure')
    run = Path(project.wd)
    expected = {str(path.relative_to(run)): path.read_bytes()
                for path in (run / 'geneva').rglob('*') if path.is_file()}
    runtime = ArchiveRuntime(
        get_current_job=lambda: SimpleNamespace(id='geneva-archive-test'),
        get_wd=lambda runid: str(run), get_prep_from_runid=lambda runid: None,
        lock_statuses=lambda runid: {}, clear_nodb_file_cache=lambda runid: [],
        publish_status=lambda channel, message: None, disk_usage=shutil.disk_usage,
        zip_file_cls=zipfile.ZipFile, project_config_lifecycle_guard=project_config_lifecycle_guard,
        project_config_authority_wd=lambda runid: str(run))
    archive_rq('geneva-fixture', 'Geneva native derivations', runtime=runtime)
    archive = next((run / 'archives').glob('*.zip'))
    with zipfile.ZipFile(archive) as members:
        assert expected.keys() <= set(members.namelist())
        assert all(members.read(name) == content for name, content in expected.items())
    shutil.rmtree(run / 'geneva')
    restore_archive_rq('geneva-fixture', archive.name, runtime=runtime)
    assert all((run / name).read_bytes() == content for name, content in expected.items())
    assert service.query_feature_collection(project) == expected_payload
