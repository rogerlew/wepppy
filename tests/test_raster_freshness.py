"""Actual local raster dependency and native summary cache regressions."""
import errno
import os
from pathlib import Path

import numpy as np
import pytest
from osgeo import gdal, osr

from wepppy.all_your_base import raster_freshness as proof
from wepppy.nodb.mods.baer import sbs_map

pytestmark = pytest.mark.integration


def raster(path, values=((0, 1), (2, 3)), driver='GTiff'):
    array = np.array(values, dtype=np.uint8)
    ds = gdal.GetDriverByName('MEM').Create('', array.shape[1], array.shape[0], 1, gdal.GDT_Byte)
    ds.SetGeoTransform((500000, 30, 0, 5000060, 0, -30))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    ds.SetProjection(spatial.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(array)
    out = gdal.GetDriverByName(driver).CreateCopy(str(path), ds)
    out = ds = None
    return path


def rewrite(path, value):
    previous = path.stat()
    ds = gdal.Open(str(path), gdal.GA_Update)
    ds.GetRasterBand(1).Fill(value)
    ds = None
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    assert path.stat().st_size == previous.st_size


def assert_native_outcome(source):
    try:
        expected = sbs_map._summarize_sbs_raster_rust(str(source))
    except (RuntimeError, ValueError, OSError) as exc:
        with pytest.raises(type(exc)):
            sbs_map._summarize_sbs_raster(str(source))
    else:
        assert sbs_map._summarize_sbs_raster(str(source)) == expected


@pytest.fixture(autouse=True)
def clear_sbs_cache():
    sbs_map._summarize_sbs_raster_cached.cache_clear()
    yield
    sbs_map._summarize_sbs_raster_cached.cache_clear()


@pytest.mark.parametrize('driver,suffix', [('GTiff', '.tif'), ('AAIGrid', '.asc')])
def test_native_driver_proof_and_auxiliary_membership(tmp_path, driver, suffix):
    source = raster(tmp_path / ('source' + suffix), driver=driver)
    initial = proof.raster_dependency_signature(source)
    assert initial is not None
    world = source.with_suffix('.tfw' if driver == 'GTiff' else '.wld')
    world.write_text('30\n0\n0\n-30\n500015\n5000045\n')
    with_world = proof.raster_dependency_signature(source)
    assert with_world is not None and with_world != initial
    world.unlink()
    assert proof.raster_dependency_signature(source) == initial
    if driver == 'AAIGrid':
        prj = source.with_suffix('.prj')
        assert any(item[0] == str(prj) for item in initial[-1])


def test_summary_restored_mtime_and_same_byte_operations(tmp_path, monkeypatch):
    source = raster(tmp_path / 'source.tif')
    real = sbs_map._summarize_sbs_raster_rust
    calls = []
    def native(path):
        calls.append(path)
        return real(path)
    monkeypatch.setattr(sbs_map, '_summarize_sbs_raster_rust', native)
    first = sbs_map._summarize_sbs_raster(str(source))
    os.utime(source, None)
    source.chmod(0o640)
    replacement = tmp_path / 'replacement'
    replacement.write_bytes(source.read_bytes())
    replacement.replace(source)
    os.link(source, tmp_path / 'hardlink')
    assert sbs_map._summarize_sbs_raster(str(source)) == first
    assert len(calls) == 1
    rewrite(source, 3)
    second = sbs_map._summarize_sbs_raster(str(source))
    assert second != first
    assert second == real(str(source))
    assert len(calls) == 2


def test_native_mask_content_is_dependency(tmp_path):
    source = raster(tmp_path / 'source.tif')
    ds = gdal.Open(str(source), gdal.GA_Update)
    with gdal.config_option('GDAL_TIFF_INTERNAL_MASK', 'NO'):
        ds.GetRasterBand(1).CreateMaskBand(gdal.GMF_PER_DATASET)
    ds.GetRasterBand(1).GetMaskBand().WriteArray(np.array([[255, 255], [255, 255]], dtype=np.uint8))
    ds = None
    mask = Path(str(source) + '.msk')
    assert mask.exists()
    first = proof.raster_dependency_signature(source)
    assert first is not None
    ds = gdal.Open(str(mask), gdal.GA_Update)
    ds.GetRasterBand(1).Fill(0)
    ds = None
    assert proof.raster_dependency_signature(source) != first


def test_changed_native_miss_never_admitted(tmp_path, monkeypatch):
    source = raster(tmp_path / 'source.tif')
    real = sbs_map._summarize_sbs_raster_rust
    def racing(path):
        result = real(path)
        rewrite(source, 3)
        return result
    monkeypatch.setattr(sbs_map, '_summarize_sbs_raster_rust', racing)
    with pytest.raises(OSError) as error:
        sbs_map._summarize_sbs_raster(str(source))
    assert error.value.errno == errno.ESTALE
    assert sbs_map._summarize_sbs_raster_cached.cache_info().currsize == 0
    monkeypatch.setattr(sbs_map, '_summarize_sbs_raster_rust', real)
    assert sbs_map._summarize_sbs_raster(str(source)) == real(str(source))


def test_changed_cached_hit_rejected(tmp_path, monkeypatch):
    source = raster(tmp_path / 'source.tif')
    sbs_map._summarize_sbs_raster(str(source))
    real = sbs_map.observe_raster_dependencies
    calls = []
    def observe(path):
        result = real(path)
        calls.append(1)
        if len(calls) == 1:
            rewrite(source, 3)
        return result
    monkeypatch.setattr(sbs_map, 'observe_raster_dependencies', observe)
    with pytest.raises(OSError) as error:
        sbs_map._summarize_sbs_raster(str(source))
    assert error.value.errno == errno.ESTALE


def test_joint_observation_rejects_first_member_changed_while_hashing_second(tmp_path, monkeypatch):
    first = raster(tmp_path / 'a.tif')
    second = raster(tmp_path / 'b.tif')
    real = proof.sha256_file
    def digest(path):
        result = real(path)
        if path == str(second):
            rewrite(first, 3)
        return result
    monkeypatch.setattr(proof, 'sha256_file', digest)
    with pytest.raises(OSError) as error:
        proof.raster_dependency_signatures((first, second))
    assert error.value.errno == errno.ESTALE


@pytest.mark.parametrize('layout', ['vrt', 'pam', 'missing', 'empty'])
def test_unverified_preserves_native_boundary_without_cache(tmp_path, layout):
    source = raster(tmp_path / 'source.tif')
    if layout == 'vrt':
        destination = tmp_path / 'source.vrt'
        ds = gdal.Translate(str(destination), str(source), format='VRT')
        ds = None
        source = destination
    elif layout == 'pam':
        Path(str(source) + '.aux.xml').write_text('<PAMDataset/>')
    elif layout == 'missing':
        source.unlink()
    else:
        source.write_bytes(b'')
    assert proof.raster_dependency_signature(source) is None
    assert_native_outcome(source)
    assert sbs_map._summarize_sbs_raster_cached.cache_info().currsize == 0


def test_symlink_selection_and_retargeting(tmp_path):
    first = raster(tmp_path / 'first.tif')
    second = raster(tmp_path / 'second.tif', ((3, 3), (3, 3)))
    alias = tmp_path / 'alias.tif'
    alias.symlink_to(first)
    initial = proof.raster_dependency_signature(alias)
    assert initial is not None
    alias.unlink()
    alias.symlink_to(second)
    assert proof.raster_dependency_signature(alias) != initial


def test_denied_dependency_cannot_authorize_reuse(tmp_path):
    source = raster(tmp_path / 'source.tif')
    sbs_map._summarize_sbs_raster(str(source))
    source.chmod(0)
    try:
        assert proof.raster_dependency_signature(source) is None
        assert_native_outcome(source)
    finally:
        source.chmod(0o600)


@pytest.mark.parametrize('extension,world_extension', [
    ('.tiff', '.tiffw'), ('.tiff', '.TIFFW'), ('.foo', '.foow'), ('.foo', '.fow'),
])
def test_worldfile_native_naming_is_in_content_proof(tmp_path, extension, world_extension):
    source = tmp_path / ('source' + extension)
    ds = gdal.GetDriverByName('GTiff').Create(str(source), 2, 2, 1, gdal.GDT_Byte)
    ds.GetRasterBand(1).Fill(1)
    ds = None
    world = tmp_path / ('source' + world_extension)
    world.write_text('30\n0\n0\n-30\n500015\n5000045\n')
    initial = proof.raster_dependency_signature(source)
    assert initial is not None
    assert any(item[0] == str(world) for item in initial[-1])
    ds = gdal.Open(str(source))
    assert ds.GetGeoTransform()[0] == 500000
    ds = None
    previous = world.stat()
    world.write_text('30\n0\n0\n-30\n600015\n5000045\n')
    os.utime(world, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    assert proof.raster_dependency_signature(source) != initial


@pytest.mark.parametrize('suffix', ['.RPB', '_RPC.TXT', '.rpc.txt', '.IMD', '.rrd'])
def test_opaque_native_sidecar_is_unverified_before_restricted_inventory(tmp_path, suffix):
    source = raster(tmp_path / 'source.tif')
    (tmp_path / ('source' + suffix)).write_text('opaque native metadata')
    assert proof.raster_dependency_signature(source) is None


def test_auxiliary_replacement_rejects_instead_of_initial_unverified(tmp_path, monkeypatch):
    source = raster(tmp_path / 'source.tif')
    mask = raster(Path(str(source) + '.msk'))
    replacement = tmp_path / 'replacement.vrt'
    ds = gdal.Translate(str(replacement), str(source), format='VRT')
    ds = None
    original = gdal.OpenEx
    replaced = []
    def opening(path, *args, **kwargs):
        if str(path) == str(source) and not replaced:
            replacement.replace(mask)
            replaced.append(True)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(gdal, 'OpenEx', opening)
    with pytest.raises(OSError) as error:
        proof.raster_dependency_signature(source)
    assert error.value.errno == errno.ESTALE


def test_changed_then_restored_native_input_is_not_admitted(tmp_path, monkeypatch):
    source = raster(tmp_path / 'source.tif', ((1, 1), (1, 1)))
    accepted = source.read_bytes()
    version = source.stat()
    native = sbs_map._summarize_sbs_raster_rust
    def changed_then_restored(path):
        rewrite(source, 3)
        summary = native(path)
        source.write_bytes(accepted)
        os.utime(source, ns=(version.st_atime_ns, version.st_mtime_ns))
        return summary
    monkeypatch.setattr(sbs_map, '_summarize_sbs_raster_rust', changed_then_restored)
    with pytest.raises(OSError) as error:
        sbs_map._summarize_sbs_raster(str(source))
    assert error.value.errno == errno.ESTALE
    assert sbs_map._summarize_sbs_raster_cached.cache_info().currsize == 0


def test_symlink_parent_dotdot_keeps_native_path_meaning(tmp_path):
    target = tmp_path / 'target'
    (target / 'nested').mkdir(parents=True)
    (tmp_path / 'alias').symlink_to(target / 'nested', target_is_directory=True)
    raster(tmp_path / 'source.tif', ((1, 1), (1, 1)))
    actual = raster(target / 'source.tif', ((3, 3), (3, 3)))
    selected = str(tmp_path / 'alias' / '..' / 'source.tif')
    first = sbs_map._summarize_sbs_raster(selected)
    assert first == sbs_map._summarize_sbs_raster_rust(str(actual))
    rewrite(actual, 2)
    second = sbs_map._summarize_sbs_raster(selected)
    assert second != first
    assert second == sbs_map._summarize_sbs_raster_rust(str(actual))


def test_transient_companion_membership_is_read_guard_not_content_key(tmp_path):
    source = raster(tmp_path / 'source.tif')
    before = proof.observe_raster_dependencies((source,))
    before.check_unchanged()
    world = tmp_path / 'source.tfw'
    world.write_text('30\n0\n0\n-30\n500015\n5000045\n')
    world.unlink()
    after = proof.observe_raster_dependencies((source,))
    assert before == after
    assert hash(before) == hash(after)
    assert before.read_guard != after.read_guard
    with pytest.raises(OSError) as error:
        before.check_unchanged()
    assert error.value.errno == errno.ESTALE
    after.check_unchanged()
