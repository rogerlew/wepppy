"""Disposable native publication/access probes; no named project mutation."""
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest
import rasterio
from osgeo import gdal, osr

from wepppy.all_your_base.geo import raster_stacker
from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators import _cache_freshness as freshness
from wepppy.nodb.mods.geneva.collaborators.hsg_assignment_service import GenevaHsgAssignmentService
from wepppy.nodb.mods.geneva.collaborators.hru_map_geometry_service import GenevaHruMapGeometryService


def raster(path, value=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    ds = gdal.GetDriverByName('GTiff').Create(str(path), 2, 2, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    ds.SetProjection(spatial.ExportToWkt())
    ds.GetRasterBand(1).Fill(value)
    ds = None


def mask(path):
    with gdal.config_option('GDAL_TIFF_INTERNAL_MASK', 'NO'):
        ds = gdal.Open(str(path), gdal.GA_Update)
        ds.GetRasterBand(1).CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetMaskBand().Fill(0)
        ds = None


def state(path):
    with rasterio.open(path) as ds:
        return {'pixels': ds.read(1).tolist(), 'mask': ds.read_masks(1).tolist()}


def record(name, **data):
    result = {'uid': os.geteuid(), **data}
    Path(__file__).with_name(f'geneva_security_{name}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


def fixture(tmp_path):
    geneva = SimpleNamespace(wd=str(tmp_path / 'run'), artifact_io=GenevaArtifactIO())
    root = geneva.artifact_io.root_dir(geneva.wd)
    source, bound = tmp_path / 'sources/source.tif', tmp_path / 'sources/bound.tif'
    raster(source, 3)
    raster(bound, 1)
    return geneva, root, source, bound


def align(geneva, source, bound):
    return GenevaHsgAssignmentService()._materialize_auto_burn_severity(
        geneva, source_path=str(source), bound_tif=str(bound))


def test_real_readonly_native_writer_compatibility(tmp_path):
    assert os.geteuid() != 0
    geneva, root, source, bound = fixture(tmp_path)
    direct = tmp_path / 'direct.tif'
    target = root / 'inputs/burn_severity_4class.tif'
    for path in (direct, target):
        raster(path, 1)
        path.chmod(0o444)
    outcomes = {}
    for name, operation, target_path in (
        ('old_native', lambda: raster_stacker(source, bound, direct, resample='near'), direct),
        ('new_service', lambda: align(geneva, source, bound), target),
    ):
        try:
            operation()
            outcomes[name] = {'result': 'success', **state(target_path)}
        except Exception as exc:
            outcomes[name] = {'result': type(exc).__name__, 'error': str(exc), **state(target_path)}
    record('readonly_native', outcomes=outcomes)
    assert outcomes['new_service']['result'] == outcomes['old_native']['result']


@pytest.mark.parametrize('kind', ['json', 'tiff'])
def test_destination_alias_retarget_during_final_validation_rejects(tmp_path, monkeypatch, kind):
    geneva, root, source, bound = fixture(tmp_path)
    outputs = root / 'outputs'
    outputs.mkdir()
    old, new = outputs / ('old.' + kind), outputs / ('new.' + kind)
    if kind == 'tiff':
        raster(old, 1)
        raster(new, 2)
        lexical = root / 'inputs/burn_severity_4class.tif'
        lexical.parent.mkdir()
        operation = lambda: align(geneva, source, bound)
    else:
        raster(root / 'hru_map.tif', 1)
        (root / 'hru_map_legend.json').write_text(json.dumps({'rows': [{'hru_value': 1, 'hru_id': 'one'}]}))
        old.write_text('{"type":"FeatureCollection","features":[]}')
        new.write_text('{"type":"FeatureCollection","features":[]}')
        lexical = root / 'hru_map_features.wgs.geojson'
        operation = lambda: GenevaHruMapGeometryService().query_feature_collection(geneva)
    lexical.symlink_to(old)
    prior_old, prior_new = old.read_bytes(), new.read_bytes()
    publish = freshness._Attempt.publish

    def intercepted(self, candidate, *, clean_tiff=False, validate=None):
        def swap_after_validation():
            if validate is not None:
                validate()
            lexical.unlink()
            lexical.symlink_to(new)
        return publish(self, candidate, clean_tiff=clean_tiff, validate=swap_after_validation)

    monkeypatch.setattr(freshness._Attempt, 'publish', intercepted)
    error = None
    try:
        operation()
    except Exception as exc:
        error = {'type': type(exc).__name__, 'code': getattr(exc, 'code', None), 'message': str(exc)}
    result = {'error': error, 'prior_old_preserved': old.read_bytes() == prior_old,
              'prior_new_preserved': new.read_bytes() == prior_new, 'selected_target': str(lexical.resolve())}
    record('late_alias_' + kind, **result)
    assert error is not None and error['code'] == 'changed_source'
    assert result['prior_old_preserved'] and result['prior_new_preserved']


def test_late_external_mask_rejects_before_atomic_publish(tmp_path, monkeypatch):
    geneva, root, source, bound = fixture(tmp_path)
    target = root / 'inputs/burn_severity_4class.tif'
    raster(target, 1)
    publish = freshness._Attempt.publish

    def intercepted(self, candidate, *, clean_tiff=False, validate=None):
        def add_mask_after_validation():
            if validate is not None:
                validate()
            mask(target)
        return publish(self, candidate, clean_tiff=clean_tiff, validate=add_mask_after_validation)

    monkeypatch.setattr(freshness._Attempt, 'publish', intercepted)
    error = None
    try:
        align(geneva, source, bound)
    except Exception as exc:
        error = {'type': type(exc).__name__, 'code': getattr(exc, 'code', None)}
    record('late_mask', error=error, target=state(target))
    assert error is not None and error['code'] == 'changed_source'
    assert state(target)['pixels'] == [[1, 1], [1, 1]]


def test_existing_mask_uses_actual_native_compatibility(tmp_path):
    geneva, root, source, bound = fixture(tmp_path)
    target = root / 'inputs/burn_severity_4class.tif'
    raster(target, 1)
    mask(target)
    align(geneva, source, bound)
    statuses = [json.loads(path.read_text()) for path in (root / 'cache_attempts').glob('*/status.json')]
    record('existing_mask', target=state(target), statuses=statuses)
    assert state(target) == {'pixels': [[3, 3], [3, 3]], 'mask': [[255, 255], [255, 255]]}
    assert statuses[-1]['compatibility_native_overwrite'] is True


@pytest.mark.parametrize('mode', [0o600, 0o640])
def test_stable_target_symlink_modes_and_private_attempts(tmp_path, mode):
    geneva, root, source, bound = fixture(tmp_path)
    target = root / 'outputs/target.tif'
    raster(target, 1)
    target.chmod(mode)
    lexical = root / 'inputs/burn_severity_4class.tif'
    lexical.parent.mkdir()
    lexical.symlink_to(target)
    align(geneva, source, bound)
    attempts = list((root / 'cache_attempts').iterdir())
    assert lexical.is_symlink() and lexical.resolve() == target
    assert stat.S_IMODE(target.stat().st_mode) == mode
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o700 for path in attempts)
    assert all(stat.S_IMODE((path / 'status.json').stat().st_mode) == 0o600 for path in attempts)
    record('stable_mode_' + oct(mode), target=state(target), mode=stat.S_IMODE(target.stat().st_mode))
