"""Basin-independent source derivation and real filesystem/NoDb promotion."""
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

from wepppy.nodb.mods.postfire_debris_flow import source_preparation as preparation
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io, preflight
from wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow import PostfireDebrisFlow
from wepppy.nodb.mods.postfire_debris_flow.soil_inputs import META, SOURCE_ID, prepare_soil, prepared_sources
from tests.nodb.mods.test_postfire_debris_flow_production_soils import database, soil_raster

pytestmark = pytest.mark.integration


def basin(root, offset=0, mukey='7', primary=True):
    root.mkdir()
    source = root/'assets'; source.mkdir()
    grid = {'shape':[2,3], 'crs':'EPSG:32611', 'transform':[10,0,500000+offset,0,-10,4000000]}
    domain = np.array([[1,1,1],[1,1,0]],dtype='float64')
    soil_raster(source/'dem.tif', np.ones((2,3))*100,grid)
    soil_raster(source/'mask.tif', domain,grid)
    if primary:
        soils = root/'soils'; soils.mkdir()
        cache = database(soils/'ssurgo_tabular_cache.sqlite')
        import sqlite3
        with sqlite3.connect(cache) as conn:
            conn.execute('UPDATE component SET mukey=?',(mukey,))
        soil_raster(soils/'ssurgo.tif', np.array([[int(mukey),8,int(mukey)],[8,int(mukey),int(mukey)]],dtype='int32'),grid)
    catalog = source/'catalog.json'
    catalog.write_text(json.dumps(dict(schema_version=1, collection_by_mukey={'7':'SSURGO','11':'SSURGO','8':'STATSGO'},
                                      source='isolated multi-basin catalog fixture',retrieved_at='2026-09-14T00:00:00Z')))
    native_grid = {'shape':[12,12], 'crs':'EPSG:32611', 'transform':[10,0,499980,0,-10,4000020]}
    native = source/'thick.tif'
    soil_raster(native,np.arange(144,dtype='float64').reshape(12,12),native_grid)
    with rasterio.open(native) as ds:
        bounds = list(ds.bounds)
    evidence = source/'thick_evidence.json'
    evidence.write_text(json.dumps(dict(schema_version=1,source_id=SOURCE_ID,source='isolated original-THICK fixture',
                                        sha256=io.digest(native),grid=native_grid,bounds=bounds)))
    return grid, domain.astype(bool), dict(wd=root,dem=source/'dem.tif',mask=source/'mask.tif',
                                           collection_catalog=catalog,thick=native,thick_evidence=evidence)


def activate(root, receipt, monkeypatch):
    monkeypatch.setattr(preflight,'notify',lambda wd:None)
    controller = PostfireDebrisFlow.tryGetInstance(str(root))
    if controller is None:
        controller = PostfireDebrisFlow(str(root),'disturbed9002_wbt.cfg')
    preparation.promote_local_sources(controller,receipt,expected_sha256=io.digest(receipt))
    return controller


def test_two_basins_derive_different_keys_and_native_windows(tmp_path,monkeypatch):
    results = []
    for name,offset,key in [('first',0,'7'),('second',40,'11')]:
        root = tmp_path/name
        grid,domain,args = basin(root,offset,key)
        receipt = preparation.prepare_local_sources(**args)
        data = io.read_json(receipt)
        assert data['mukeys'] == sorted([key,'8'],key=int)
        assert not (root/META).exists()  # preparation is not activation
        activate(root,receipt,monkeypatch)
        sources = prepared_sources(root)
        assert sources['primary']['mukeys'] == [key]
        assert sources['fallback']['evidence_record']['grid'] == grid
        soil = prepare_soil(root,root/'soil_result',grid,domain)
        assert soil['source_cells'] == dict(primary=3,fallback=2,unavailable=0,outside=1)
        with rasterio.open(root/'soil_result/thickness_cm.tif') as ds:
            values = ds.read(1)
        assert values[0,0] == 100
        results.append(values[0,1])
    assert results[0] != results[1]  # same native source, different basin crop


def test_fallback_only_without_primary_mapping_or_cache(tmp_path,monkeypatch):
    root = tmp_path/'fallback'
    grid,domain,args = basin(root,primary=False)
    receipt = preparation.prepare_local_sources(**args)
    assert io.read_json(receipt)['mukeys'] == []
    activate(root,receipt,monkeypatch)
    assert prepared_sources(root)['primary'] is None
    result = prepare_soil(root,root/'soil_result',grid,domain)
    assert result['source_cells']['fallback'] == 5


def test_stale_repreparation_preserves_previous_input_manifest(tmp_path,monkeypatch):
    root = tmp_path/'stale'
    _,_,args = basin(root)
    first = preparation.prepare_local_sources(**args)
    controller = activate(root,first,monkeypatch)
    accepted = (root/META).read_bytes()
    second = preparation.prepare_local_sources(**args)
    with args['dem'].open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(io.RainfallError,match='changed'):
        preparation.promote_local_sources(controller,second,expected_sha256=io.digest(second))
    assert (root/META).read_bytes() == accepted
    assert second.exists()


def test_cross_project_receipt_is_not_promoted(tmp_path,monkeypatch):
    root = tmp_path/'first'; _,_,args = basin(root)
    receipt = preparation.prepare_local_sources(**args)
    other = tmp_path/'other'; basin(other,40,'11')
    controller = PostfireDebrisFlow(str(other),'disturbed9002_wbt.cfg')
    with pytest.raises(io.RainfallError,match='this project'):
        preparation.promote_local_sources(controller,receipt,expected_sha256=io.digest(receipt))
    assert not (other/META).exists()


def test_failed_atomic_install_preserves_previous_input(tmp_path,monkeypatch):
    root = tmp_path/'failed'; _,_,args = basin(root)
    receipt = preparation.prepare_local_sources(**args)
    controller = activate(root,receipt,monkeypatch)
    before = (root/META).read_bytes()
    replacement = preparation.prepare_local_sources(**args)
    replace = preparation.os.replace
    def fail_install(source,destination,**kwargs):
        if Path(destination).name == 'soil_sources.json':
            raise OSError('injected atomic install failure')
        return replace(source,destination,**kwargs)
    monkeypatch.setattr(preparation.os,'replace',fail_install)
    with pytest.raises(OSError,match='atomic install'):
        preparation.promote_local_sources(controller,replacement,expected_sha256=io.digest(replacement))
    assert (root/META).read_bytes() == before
    assert list(replacement.parent.glob('promotion-*.json'))


def test_key_collection_is_bounded_before_request_construction(monkeypatch):
    monkeypatch.setattr(io,'MAX_TEXT',12)
    with pytest.raises(io.RainfallError,match='key list'):
        preparation._keys(np.array([[123,456,789]],dtype=float),np.ones((1,3),dtype=bool),np.ones((1,3),dtype=bool))


@pytest.mark.parametrize('cell', [(0,0), (1,2)])
def test_malformed_mukey_inside_or_outside_domain_rejected(tmp_path, cell):
    root = tmp_path/'invalid'; _,_,args = basin(root)
    with rasterio.open(root/'soils/ssurgo.tif','r+') as ds:
        values = ds.read(1); values[cell] = 0; ds.write(values,1)
    with pytest.raises(io.RainfallError, match='positive integer'):
        preparation.prepare_local_sources(**args)


@pytest.mark.parametrize('field', ['collection_catalog', 'thick_evidence'])
def test_malformed_present_evidence_rejected(tmp_path, field):
    root = tmp_path/'invalid'; _,_,args = basin(root)
    record = json.loads(args[field].read_text())
    if field == 'collection_catalog':
        record['collection_by_mukey']['7'] = {'unexpected':'object'}
    else:
        record['schema_version'] = True
    args[field].write_text(json.dumps(record))
    with pytest.raises(io.RainfallError, match='Malformed|unverified'):
        preparation.prepare_local_sources(**args)


def test_oversized_catalog_is_not_retained(tmp_path):
    root = tmp_path/'oversized'; _,_,args = basin(root)
    args['collection_catalog'].write_bytes(b' '*(io.MAX_TEXT+1))
    with pytest.raises(io.RainfallError):
        preparation.prepare_local_sources(**args)
    assert not list((root/'postfire_debris_flow/source_preparation').glob('*/sources/collection_catalog.json'))


def test_artifact_change_during_hash_verification_rejected(tmp_path, monkeypatch):
    root = tmp_path/'race'; _,_,args = basin(root)
    receipt = preparation.prepare_local_sources(**args)
    controller = activate(root,receipt,monkeypatch)
    before = (root/META).read_bytes()
    replacement = preparation.prepare_local_sources(**args)
    native = replacement.parent/'fallback_native.tif'
    digest = io.digest
    def change_after_hash(path, *args, **kwargs):
        value = digest(path,*args,**kwargs)
        if Path(path) == native:
            with native.open('ab') as stream:
                stream.write(b'changed')
        return value
    monkeypatch.setattr(io,'digest',change_after_hash)
    with pytest.raises(io.RainfallError, match='changed'):
        preparation.promote_local_sources(controller,replacement,expected_sha256=digest(replacement))
    assert (root/META).read_bytes() == before


def test_directory_swap_cannot_redirect_atomic_write(tmp_path, monkeypatch):
    root = tmp_path/'race'; _,_,args = basin(root)
    receipt = preparation.prepare_local_sources(**args)
    controller = activate(root,receipt,monkeypatch)
    replacement = preparation.prepare_local_sources(**args)
    outside = tmp_path/'outside'; outside.mkdir()
    destination = (root/META).parent
    moved = destination.with_name('retained_inputs')
    replace = preparation.os.replace
    def swap_before_replace(source,target,**kwargs):
        if Path(target).name == 'soil_sources.json':
            destination.rename(moved)
            destination.symlink_to(outside,target_is_directory=True)
        return replace(source,target,**kwargs)
    monkeypatch.setattr(preparation.os,'replace',swap_before_replace)
    preparation.promote_local_sources(controller,replacement,expected_sha256=io.digest(replacement))
    assert not (outside/'soil_sources.json').exists()
    assert (moved/'soil_sources.json').exists()


def test_file_promotion_does_not_save_or_notify_nodb(tmp_path, monkeypatch):
    root = tmp_path/'file_only'; _,_,args = basin(root)
    receipt = preparation.prepare_local_sources(**args)
    controller = PostfireDebrisFlow(str(root),'disturbed9002_wbt.cfg')
    def unexpected(*args, **kwargs):
        raise AssertionError('Unrelated NoDb save/notification called')
    monkeypatch.setattr(PostfireDebrisFlow,'dump',unexpected)
    monkeypatch.setattr(preflight,'notify',unexpected)
    result = preparation.promote_local_sources(controller,receipt,expected_sha256=io.digest(receipt))
    assert result['status'] == 'committed'
    assert result['warnings'] == []


def test_lost_nodb_ownership_prevents_commit(tmp_path, monkeypatch):
    root = tmp_path/'lost_lock'; _,_,args = basin(root)
    receipt = preparation.prepare_local_sources(**args)
    controller = activate(root,receipt,monkeypatch)
    before = (root/META).read_bytes()
    replacement = preparation.prepare_local_sources(**args)
    def lost(*args):
        raise RuntimeError('injected lost ownership')
    monkeypatch.setattr(PostfireDebrisFlow,'_assert_lock_owned_for_dump',lost)
    with pytest.raises(RuntimeError,match='lost ownership'):
        preparation.promote_local_sources(controller,replacement,expected_sha256=io.digest(replacement))
    assert (root/META).read_bytes() == before


def test_postcommit_unlock_failure_reports_committed_warning(tmp_path, monkeypatch, caplog):
    root = tmp_path/'cleanup'; _,_,args = basin(root)
    receipt = preparation.prepare_local_sources(**args)
    controller = PostfireDebrisFlow(str(root),'disturbed9002_wbt.cfg')
    unlock = PostfireDebrisFlow.unlock
    def fail_release(self,*args,**kwargs):
        unlock(self,*args,**kwargs)
        raise RuntimeError('injected cleanup failure')
    monkeypatch.setattr(PostfireDebrisFlow,'unlock',fail_release)
    result = preparation.promote_local_sources(controller,receipt,expected_sha256=io.digest(receipt))
    assert result['status'] == 'committed'
    assert result['warnings'] == ['nodb_release_failed:RuntimeError']
    assert 'committed with cleanup warning' in caplog.text
    assert (root/META).read_bytes() == (receipt.parent/'soil_sources.json').read_bytes()
