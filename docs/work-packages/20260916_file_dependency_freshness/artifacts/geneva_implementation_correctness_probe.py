"""Independent disposable native Geneva cache/admission controls.

Real GDAL/rasterio, ArtifactIO, service generation and publication execute. Only
the NoDb owner is a wd/ArtifactIO namespace; mutation hooks model visible input
changes around real native operations. No named runs or HTTP/RQ calls.
"""
import errno
import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from osgeo import gdal, osr
import pytest
import rasterio

from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators import _cache_freshness as freshness
from wepppy.nodb.mods.geneva.collaborators import hsg_assignment_service as alignment
from wepppy.nodb.mods.geneva.collaborators.hru_map_geometry_service import GenevaHruMapGeometryService
from wepppy.nodb.mods.geneva.errors import GenevaNoDbError


def raster(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    ds = gdal.GetDriverByName('GTiff').Create(str(path), 2, 2, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(32611)
    ds.SetProjection(crs.ExportToWkt())
    ds.GetRasterBand(1).Fill(value)
    ds.GetRasterBand(1).SetNoDataValue(0)
    ds = None


def replace_bytes(path, data):
    temporary = path.with_name(path.name + '.replacement')
    temporary.write_bytes(data)
    os.replace(temporary, path)


def owner(tmp_path):
    return SimpleNamespace(wd=str(tmp_path), artifact_io=GenevaArtifactIO())


def geometry_fixture(tmp_path, *, two_rows=True):
    geneva = owner(tmp_path)
    source = geneva.artifact_io.resolve_path(geneva.wd, 'hru_map.tif')
    raster(source, 1)
    rows = [{'hru_value': n, 'hru_id': f'hru_{n}', 'landuse_class': 10 * n}
            for n in ((1, 2) if two_rows else (1,))]
    geneva.artifact_io.write_json(geneva.wd, 'hru_map_legend.json', {'rows': rows})
    service = GenevaHruMapGeometryService()
    service.query_feature_collection(geneva)
    target = geneva.artifact_io.resolve_path(geneva.wd, 'hru_map_features.wgs.geojson')
    return geneva, service, source, target


def alignment_fixture(tmp_path):
    geneva = owner(tmp_path)
    source, bound = tmp_path / 'disturbed/source.tif', tmp_path / 'watershed/bound.tif'
    raster(source, 1)
    raster(bound, 1)
    service = alignment.GenevaHsgAssignmentService()
    target = Path(service._materialize_auto_burn_severity(geneva, source_path=str(source), bound_tif=str(bound)))
    return geneva, service, source, bound, target


def record(name, payload):
    print('GENEVA_CORRECTNESS', name, json.dumps(payload, sort_keys=True))
    Path(__file__).with_name(f'geneva_implementation_correctness_{name}.json').write_text(
        json.dumps(payload, indent=2) + '\n')


def test_geometry_changed_pixels_and_legend_with_restored_mtime(tmp_path):
    geneva, service, source, target = geometry_fixture(tmp_path)
    old_version = source.stat()
    raster(source, 2)
    os.utime(source, ns=(old_version.st_atime_ns, old_version.st_mtime_ns))
    first = service.query_feature_collection(geneva)
    row = first['feature_collection']['features'][0]['properties']
    assert row['hru_id'] == 'hru_2'
    legend = geneva.artifact_io.resolve_path(geneva.wd, 'hru_map_legend.json')
    old_version = legend.stat()
    payload = json.loads(legend.read_text())
    payload['rows'][1]['hru_id'] = 'new_2'
    legend.write_text(json.dumps(payload))
    os.utime(legend, ns=(old_version.st_atime_ns, old_version.st_mtime_ns))
    second = service.query_feature_collection(geneva)
    assert second['feature_collection']['features'][0]['properties']['hru_id'] == 'new_2'
    before = target.stat()
    os.utime(source, None)
    service.query_feature_collection(geneva)
    assert target.stat().st_ino == before.st_ino
    record('geometry_content', {'changed_pixels_hru': row['hru_id'], 'changed_legend_hru': 'new_2',
                                'same_bytes_touch_reused': True})


def test_geometry_native_aba_rejected_preserving_prior(tmp_path, monkeypatch):
    geneva, service, source, target = geometry_fixture(tmp_path)
    prior = target.read_bytes()
    original = source.read_bytes()
    alternate = tmp_path / 'alternative.tif'
    raster(alternate, 2)
    actual_open = rasterio.open
    actual_shapes = rasterio.features.shapes
    triggered = False

    def mutate_before_open(path, *args, **kwargs):
        nonlocal triggered
        if Path(path) == source and not triggered:
            triggered = True
            replace_bytes(source, alternate.read_bytes())
        return actual_open(path, *args, **kwargs)

    def restore_after_native_shapes(*args, **kwargs):
        try:
            yield from actual_shapes(*args, **kwargs)
        finally:
            replace_bytes(source, original)

    monkeypatch.setattr(rasterio, 'open', mutate_before_open)
    monkeypatch.setattr(rasterio.features, 'shapes', restore_after_native_shapes)
    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_feature_collection_from_raster(geneva, source_path=source)
    assert caught.value.code == 'changed_source' and caught.value.status_code == 409
    assert target.read_bytes() == prior and source.read_bytes() == original
    record('geometry_aba', {'error_code': caught.value.code, 'prior_preserved': True, 'source_restored': True})


def test_geometry_changed_source_native_error_is_changed_source(tmp_path, monkeypatch):
    geneva, service, source, target = geometry_fixture(tmp_path, two_rows=False)
    prior = target.read_bytes()
    alternate = tmp_path / 'alternative.tif'
    raster(alternate, 2)
    actual_open = rasterio.open
    triggered = False

    def mutate_before_open(path, *args, **kwargs):
        nonlocal triggered
        if Path(path) == source and not triggered:
            triggered = True
            replace_bytes(source, alternate.read_bytes())
        return actual_open(path, *args, **kwargs)

    monkeypatch.setattr(rasterio, 'open', mutate_before_open)
    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_feature_collection_from_raster(geneva, source_path=source)
    record('geometry_error', {'error_code': caught.value.code, 'status': caught.value.status_code,
                              'prior_preserved': target.read_bytes() == prior})
    assert target.read_bytes() == prior
    assert caught.value.code == 'changed_source' and caught.value.status_code == 409


def test_alignment_content_and_profile_identity(tmp_path, monkeypatch):
    geneva, service, source, bound, target = alignment_fixture(tmp_path)
    native = alignment.raster_stacker
    calls = []

    def counted(*args, **kwargs):
        calls.append(True)
        return native(*args, **kwargs)

    monkeypatch.setattr(alignment, 'raster_stacker', counted)
    old = source.stat()
    raster(source, 3)
    os.utime(source, ns=(old.st_atime_ns, old.st_mtime_ns))
    service._materialize_auto_burn_severity(geneva, source_path=str(source), bound_tif=str(bound))
    with rasterio.open(target) as ds:
        assert ds.read(1).tolist() == [[3, 3], [3, 3]]
    assert len(calls) == 1
    os.utime(source, None)
    raster(bound, 99)
    service._materialize_auto_burn_severity(geneva, source_path=str(source), bound_tif=str(bound))
    assert len(calls) == 1
    record('alignment_identity', {'changed_source_pixels': 3, 'metadata_and_bound_pixel_reuse': True})


def test_alignment_auxiliary_target_uses_original_native(tmp_path):
    geneva, service, source, bound, target = alignment_fixture(tmp_path)
    with gdal.config_option('GDAL_TIFF_INTERNAL_MASK', 'NO'):
        ds = gdal.Open(str(target), gdal.GA_Update)
        ds.GetRasterBand(1).CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetMaskBand().Fill(0)
        ds = None
    assert Path(str(target) + '.msk').exists()
    raster(source, 3)
    service._materialize_auto_burn_severity(geneva, source_path=str(source), bound_tif=str(bound))
    with rasterio.open(target) as ds:
        values, mask, proof = ds.read(1).tolist(), ds.read_masks(1).tolist(), ds.tags().get(freshness.TIFF_PROOF)
    record('alignment_auxiliary', {'values': values, 'mask': mask, 'proof': proof})
    assert values == [[3, 3], [3, 3]] and mask == [[255, 255], [255, 255]]
    assert proof is None


def test_alignment_native_aba_preserves_prior(tmp_path, monkeypatch):
    geneva, service, source, bound, target = alignment_fixture(tmp_path)
    original, prior = source.read_bytes(), target.read_bytes()
    alternate = tmp_path / 'alternative.tif'
    raster(alternate, 3)
    native = alignment.raster_stacker
    target.unlink()
    # A proofless prior target forces a normal rebuild while retaining real bytes.
    replace_bytes(target, prior)
    ds = gdal.Open(str(target), gdal.GA_Update)
    ds.SetMetadataItem(freshness.TIFF_PROOF, None)
    ds = None
    prior = target.read_bytes()

    def aba_native(*args, **kwargs):
        replace_bytes(source, alternate.read_bytes())
        try:
            return native(*args, **kwargs)
        finally:
            replace_bytes(source, original)

    monkeypatch.setattr(alignment, 'raster_stacker', aba_native)
    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_auto_burn_severity(geneva, source_path=str(source), bound_tif=str(bound))
    record('alignment_aba', {'error_code': caught.value.code, 'status': caught.value.status_code,
                             'prior_preserved': target.read_bytes() == prior})
    assert caught.value.code == 'changed_source' and target.read_bytes() == prior


def test_alignment_changed_source_native_error_is_changed_source(tmp_path, monkeypatch):
    geneva, service, source, bound, target = alignment_fixture(tmp_path)
    ds = gdal.Open(str(target), gdal.GA_Update)
    ds.SetMetadataItem(freshness.TIFF_PROOF, None)
    ds = None
    prior = target.read_bytes()
    native = alignment.raster_stacker

    def fail_after_source_change(*args, **kwargs):
        replace_bytes(source, b'not a raster after observable replacement')
        return native(*args, **kwargs)

    monkeypatch.setattr(alignment, 'raster_stacker', fail_after_source_change)
    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_auto_burn_severity(geneva, source_path=str(source), bound_tif=str(bound))
    record('alignment_error', {'error_code': caught.value.code, 'status': caught.value.status_code,
                               'prior_preserved': target.read_bytes() == prior})
    assert target.read_bytes() == prior
    assert caught.value.code == 'changed_source' and caught.value.status_code == 409


def test_unverified_vrt_alignment_keeps_native_success_uncached(tmp_path, monkeypatch):
    geneva = owner(tmp_path)
    source, bound, vrt = tmp_path / 'source.tif', tmp_path / 'bound.tif', tmp_path / 'source.vrt'
    raster(source, 3)
    raster(bound, 1)
    gdal.Translate(str(vrt), str(source), format='VRT')
    native, calls = alignment.raster_stacker, []

    def counted(*args, **kwargs):
        calls.append(True)
        return native(*args, **kwargs)

    monkeypatch.setattr(alignment, 'raster_stacker', counted)
    service = alignment.GenevaHsgAssignmentService()
    for _ in range(2):
        target = service._materialize_auto_burn_severity(geneva, source_path=str(vrt), bound_tif=str(bound))
    with rasterio.open(target) as ds:
        proof = json.loads(ds.tags()[freshness.TIFF_PROOF])
        assert ds.read(1).tolist() == [[3, 3], [3, 3]]
    assert len(calls) == 2 and proof['dependencies'] is None
    record('unverified_vrt', {'native_calls': len(calls), 'dependencies': proof['dependencies']})


def test_geometry_stable_invalid_crosswalk_preserves_original_error(tmp_path):
    geneva, service, source, target = geometry_fixture(tmp_path)
    prior = target.read_bytes()
    geneva.artifact_io.write_json(geneva.wd, 'hru_map_legend.json',
                                 {'rows': [{'hru_value': 2, 'hru_id': 'only_two'}]})
    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_feature_collection_from_raster(geneva, source_path=source)
    record('stable_crosswalk_error', {'error_code': caught.value.code,
                                      'status': caught.value.status_code,
                                      'prior_preserved': target.read_bytes() == prior})
    assert caught.value.code == 'contract_violation' and caught.value.status_code == 500
    assert target.read_bytes() == prior


def test_geometry_native_completion_legend_disappearance_is_changed_source(tmp_path, monkeypatch):
    geneva, service, source, target = geometry_fixture(tmp_path)
    prior = target.read_bytes()
    legend = geneva.artifact_io.resolve_path(geneva.wd, 'hru_map_legend.json')
    actual_shapes = rasterio.features.shapes

    def delete_after_native_shapes(*args, **kwargs):
        yield from actual_shapes(*args, **kwargs)
        legend.unlink()

    monkeypatch.setattr(rasterio.features, 'shapes', delete_after_native_shapes)
    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_feature_collection_from_raster(geneva, source_path=source)
    record('materialization_missing_legend', {'error_code': caught.value.code,
                                              'status': caught.value.status_code,
                                              'prior_preserved': target.read_bytes() == prior})
    assert caught.value.code == 'changed_source' and caught.value.status_code == 409
    assert target.read_bytes() == prior


def test_geometry_hit_legend_disappearance_is_changed_source(tmp_path, monkeypatch):
    geneva, service, source, target = geometry_fixture(tmp_path)
    prior = target.read_bytes()
    legend = geneva.artifact_io.resolve_path(geneva.wd, 'hru_map_legend.json')
    read_json = geneva.artifact_io.read_json

    def remove_after_cached_read(wd, relpath):
        result = read_json(wd, relpath)
        if relpath == 'hru_map_features.wgs.geojson':
            legend.unlink()
        return result

    monkeypatch.setattr(geneva.artifact_io, 'read_json', remove_after_cached_read)
    error = None
    try:
        service.query_feature_collection(geneva)
    except (GenevaNoDbError, OSError) as caught:
        error = caught
    record('hit_missing_legend', {'error_type': type(error).__name__,
                                 'error_code': getattr(error, 'code', None),
                                 'status': getattr(error, 'status_code', None),
                                 'prior_preserved': target.read_bytes() == prior})
    assert isinstance(error, GenevaNoDbError) and error.code == 'changed_source' and error.status_code == 409
    assert target.read_bytes() == prior


def test_alignment_hit_source_disappearance_is_changed_source(tmp_path):
    geneva, service, source, bound, target = alignment_fixture(tmp_path)
    prior, calls = target.read_bytes(), []

    def selected():
        calls.append(True)
        if len(calls) == 2:
            source.unlink()
        return (str(source), str(bound))

    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_auto_burn_severity(geneva, source_path=str(source),
                                               bound_tif=str(bound), _selection=selected)
    record('hit_missing_source', {'error_code': caught.value.code, 'status': caught.value.status_code,
                                  'prior_preserved': target.read_bytes() == prior})
    assert caught.value.code == 'changed_source' and caught.value.status_code == 409
    assert target.read_bytes() == prior


def test_alignment_joint_guard_rechecks_source_after_bound_digest(tmp_path, monkeypatch):
    geneva, service, source, bound, target = alignment_fixture(tmp_path)
    prior = target.read_bytes()
    alternate = tmp_path / 'alternate.tif'
    raster(alternate, 3)
    digest = freshness.sha256_file

    def change_source_during_bound_check(path, *args, **kwargs):
        result = digest(path, *args, **kwargs)
        if Path(path) == bound:
            replace_bytes(source, alternate.read_bytes())
        return result

    monkeypatch.setattr(freshness, 'sha256_file', change_source_during_bound_check)
    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_auto_burn_severity(geneva, source_path=str(source), bound_tif=str(bound))
    record('joint_source_during_bound', {'error_code': caught.value.code,
                                        'status': caught.value.status_code,
                                        'prior_preserved': target.read_bytes() == prior})
    assert caught.value.code == 'changed_source' and caught.value.status_code == 409
    assert target.read_bytes() == prior


def test_alignment_missing_after_physical_guard_is_changed_source(tmp_path, monkeypatch):
    geneva, service, source, bound, target = alignment_fixture(tmp_path)
    prior = target.read_bytes()
    digest = freshness.sha256_file

    def remove_before_digest(path, *args, **kwargs):
        if Path(path) == source:
            source.unlink()
        return digest(path, *args, **kwargs)

    monkeypatch.setattr(freshness, 'sha256_file', remove_before_digest)
    with pytest.raises(GenevaNoDbError) as caught:
        service._materialize_auto_burn_severity(geneva, source_path=str(source), bound_tif=str(bound))
    record('missing_after_physical_guard', {'error_code': caught.value.code,
                                           'status': caught.value.status_code,
                                           'prior_preserved': target.read_bytes() == prior})
    assert caught.value.code == 'changed_source' and caught.value.status_code == 409
    assert target.read_bytes() == prior


def test_same_call_guard_preserves_unrelated_eio(tmp_path, monkeypatch):
    geneva, service, source, bound, target = alignment_fixture(tmp_path)
    observed = freshness.alignment_inputs(source, bound)
    failure = OSError(errno.EIO, 'injected stable-source I/O failure')

    def fail_digest(path, *args, **kwargs):
        raise failure

    monkeypatch.setattr(freshness, 'sha256_file', fail_digest)
    with pytest.raises(OSError) as caught:
        observed.check_unchanged()
    assert caught.value is failure
    record('stable_eio', {'errno': caught.value.errno, 'original_error_preserved': True})
