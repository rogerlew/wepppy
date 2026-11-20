import json
import shutil
from pathlib import Path
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb import culvert_stream_selection as selection

pytestmark = pytest.mark.integration


def raster(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, 'w', driver='GTiff', width=values.shape[1], height=values.shape[0], count=1,
                       dtype='float32', crs='EPSG:32617', transform=from_origin(0, values.shape[0], 1, 1), nodata=0) as dst:
        dst.write(values.astype('float32'), 1)


@pytest.fixture
def candidates(tmp_path):
    pointer = np.zeros((9, 9)); streams = pointer.copy()
    for row in range(1, 4):
        pointer[row,row] = 4
        pointer[row,8-row] = 16
        streams[row,row] = streams[row,8-row] = 1
    for row in range(4, 8):
        pointer[row,4] = 8; streams[row,4] = 1
    raster(tmp_path/'topo/pointer.tif', pointer)
    raster(tmp_path/'topo/streams.tif', streams)
    raster(tmp_path/'mask.tif', np.ones((9,9)))
    selection.write_json(tmp_path/selection.POLICY, {'version':1})
    selection.prepare(tmp_path,tmp_path/'topo/pointer.tif',tmp_path/'topo/streams.tif',tmp_path/'topo/streams.tif',2)
    return tmp_path


def test_real_wbt_candidates_selection_resume_and_zero(candidates):
    root=candidates
    manifest=selection.ready_manifest(root)
    assert [c['passes'] for c in manifest['candidates']]==[2,1,0]
    for ident,xy,expected in [('trunk',(4.5,3.5),1),('branch',(1.5,7.5),0)]:
        run=root/'runs'/ident
        chosen=selection.select(root,run,ident,xy,'EPSG:32617',root/'mask.tif')
        receipt=json.loads((run/selection.RECEIPT).read_text())
        assert receipt['selected_passes']==expected
        assert selection.select(root,run,ident,xy,'EPSG:32617',root/'mask.tif')==chosen
    with pytest.raises(ValueError,match='No stream candidate'):
        selection.select(root,root/'runs/miss','miss',(0.5,8.5),'EPSG:32617',root/'mask.tif')
    assert json.loads((root/'runs/miss'/selection.RECEIPT).read_text())['state']=='failed'
    # Removing a selected artifact is an error, never a reason to silently refine.
    Path(chosen[1]).unlink()
    with pytest.raises(FileNotFoundError):
        selection.select(root,root/'runs/branch','branch',(1.5,7.5),'EPSG:32617',root/'mask.tif')


def test_archive_restore_and_identity_guard(candidates,tmp_path):
    from wepppy.rq.culvert_rq_manifest import _write_run_skeletons_zip
    root=candidates
    selection.select(root,root/'runs/trunk','trunk',(4.5,3.5),'EPSG:32617',root/'mask.tif')
    archive=_write_run_skeletons_zip(root)
    restored=tmp_path/'restored'
    with zipfile.ZipFile(archive) as z: z.extractall(restored)
    shutil.copyfile(root/'mask.tif',restored/'mask.tif')
    assert selection.reuse_ready(restored)
    paths=selection.select(restored,restored/'runs/trunk','trunk',(4.5,3.5),'EPSG:32617',restored/'mask.tif')
    assert all(Path(p).is_relative_to(restored) for p in paths)
    with Path(paths[0]).open('ab') as handle: handle.write(b'changed')
    with pytest.raises(ValueError,match='identity changed'):
        selection.select(restored,restored/'runs/trunk','trunk',(4.5,3.5),'EPSG:32617',restored/'mask.tif')


def test_intent_distinguishes_legacy_and_partial(tmp_path):
    assert selection.has_policy(tmp_path) is False
    selection.write_json(tmp_path/selection.POLICY, {'version':1})
    with pytest.raises(FileNotFoundError): selection.ready_manifest(tmp_path)
    selection.write_json(tmp_path/selection.MANIFEST, {'version':1,'state':'preparing'})
    with pytest.raises(ValueError,match='not ready'): selection.ready_manifest(tmp_path)
    (tmp_path/selection.POLICY).unlink()
    with pytest.raises(ValueError,match='without policy'): selection.has_policy(tmp_path)


def test_ready_retry_preserves_inputs_and_candidates(candidates):
    root=candidates
    before={p: (p.stat().st_mtime_ns, selection.digest(p)) for p in (root/'topo').rglob('*.tif')}
    assert selection.reuse_ready(root)
    selection.prepare(root,root/'topo/pointer.tif',root/'topo/streams.tif',root/'topo/streams.tif',2)
    assert before=={p:(p.stat().st_mtime_ns,selection.digest(p)) for p in before}
    with (root/'topo/pointer.tif').open('ab') as handle: handle.write(b'changed')
    with pytest.raises(ValueError,match='identity changed'): selection.reuse_ready(root)


def test_zero_override_and_polygon_coverage(candidates):
    root=candidates
    # Empty watershed cannot qualify even when the point lies on a stream.
    raster(root/'empty.tif',np.zeros((9,9)))
    with pytest.raises(ValueError,match='No stream candidate'):
        selection.select(root,root/'runs/empty','empty',(4.5,3.5),'EPSG:32617',root/'empty.tif')
    assert 'no_watershed_coverage' in (root/'runs/empty'/selection.RECEIPT).read_text()
    zero=root/'zero';zero.mkdir();(zero/'topo').mkdir()
    shutil.copyfile(root/'topo/pointer.tif',zero/'topo/pointer.tif')
    shutil.copyfile(root/'topo/streams.tif',zero/'topo/streams.tif')
    shutil.copyfile(root/'mask.tif',zero/'mask.tif')
    selection.write_json(zero/selection.POLICY,{'version':1})
    selection.prepare(zero,zero/'topo/pointer.tif',zero/'topo/streams.tif',zero/'topo/streams.tif',0)
    selected=selection.select(zero,zero/'runs/a','a',(1.5,7.5),'EPSG:32617',zero/'mask.tif')
    assert Path(selected[0])==zero/'topo/streams.tif'


def test_incomplete_receipt_state_cannot_rebuild_shared_topology(candidates):
    root=candidates
    selection.select(root,root/'runs/a','a',(4.5,3.5),'EPSG:32617',root/'mask.tif')
    before=selection.digest(root/'topo/pointer.tif')
    (root/selection.MANIFEST).unlink()
    with pytest.raises(ValueError,match='missing stream candidates'):
        selection.reuse_ready(root)
    assert selection.digest(root/'topo/pointer.tif')==before


def test_four_to_three_preserves_trunk_and_matches_wbt(tmp_path, monkeypatch):
    from whitebox_tools import WhiteboxTools

    # Older WhiteboxTools wrappers change the process working directory.
    monkeypatch.chdir(tmp_path)
    pointer=np.zeros((33,33)); streams=pointer.copy()
    sources=[(1,c) for c in range(2,33,4)]
    while len(sources)>1:
        merged=[]
        for left,right in zip(sources[::2],sources[1::2]):
            target=(left[0]+(right[1]-left[1])//2,(left[1]+right[1])//2)
            for row,col in [left,right]:
                step=1 if col<target[1] else -1
                while row<target[0]:
                    streams[row,col]=1;pointer[row,col]=4 if step==1 else 16
                    row+=1;col+=step
            merged.append(target)
        sources=merged
    row,col=sources[0]
    for row in range(row,32):streams[row,col]=1;pointer[row,col]=8
    raster(tmp_path/'pointer.tif',pointer);raster(tmp_path/'streams.tif',streams)
    raster(tmp_path/'mask.tif',np.ones((33,33)))
    selection.write_json(tmp_path/selection.POLICY,{'version':1})
    selection.prepare(tmp_path,tmp_path/'pointer.tif',tmp_path/'streams.tif',tmp_path/'streams.tif',4)
    selection.select(tmp_path,tmp_path/'runs/a','a',(16.5,12.5),'EPSG:32617',tmp_path/'mask.tif')
    receipt=selection.read_json(tmp_path/'runs/a'/selection.RECEIPT)
    assert receipt['selected_passes']==3
    assert [x['passes'] for x in receipt['attempted']]==[4,3]
    wbt=WhiteboxTools(verbose=False,raise_on_error=True)
    current=tmp_path/'topo/stream_candidates/order.tif'
    for step in range(1,5):
        output=tmp_path/f'wbt-{step}.tif'
        wbt.prune_strahler_stream_order(str(current),str(output),binary_output=step==4)
        with rasterio.open(output) as a, rasterio.open(tmp_path/f'topo/stream_candidates/pass_{step}/streams.tif') as b:
            assert np.array_equal(np.ma.filled(a.read(1,masked=True)>0,False),b.read(1)>0)
        current=output


@pytest.fixture
def original_outlets(tmp_path, monkeypatch):
    """Actual native FindOutlet on the original network; the road point is off-stream."""
    from wepppy.nodb.culverts_runner import CulvertsRunner
    from shapely.geometry import box, mapping

    monkeypatch.chdir(tmp_path)
    root = tmp_path
    pointer = np.full((9, 9), 8.0); streams = np.zeros((9, 9))
    for row in range(1, 9):
        pointer[row, 4] = 8
        streams[row, 4] = 1
    raster(root/'topo/pointer.tif', pointer)
    raster(root/'topo/streams.tif', streams)
    raster(root/'topo/dem.tif', np.ones((9, 9)))
    raster(root/'mask.tif', np.ones((9, 9)))
    crs = {'type': 'name', 'properties': {'name': 'EPSG:32617'}}
    for name, geometry in [('points', {'type': 'Point', 'coordinates': [3.5, 1.5]}),
                           ('watersheds', mapping(box(0, 0, 9, 9)))]:
        selection.write_json(root/f'{name}.geojson', {'type': 'FeatureCollection', 'crs': crs,
            'features': [{'type': 'Feature', 'properties': {'Point_ID': 'a'}, 'geometry': geometry}]})
    selection.write_json(root/selection.POLICY,
                         {'version': 1, 'selection_basis': selection.ORIGINAL_OUTLET_BASIS})
    runner = object.__new__(CulvertsRunner)
    selection.prepare_original_outlets(root, root/'topo/pointer.tif', root/'topo/streams.tif',
        root/'topo/dem.tif', root/'points.geojson', root/'watersheds.geojson', runner)
    return root, runner


def _prepare_original_candidates(root):
    selection.prepare(root, root/'topo/pointer.tif', root/'topo/streams.tif',
                      root/'topo/streams.tif', 1, dem=root/'topo/dem.tif')


def test_off_stream_road_point_resolves_before_pruning_and_is_fixed(original_outlets):
    root, _ = original_outlets
    outlet = selection.original_outlet(root, 'a')
    assert outlet['coordinates'] == [4.5, 0.5]
    assert outlet['supplied_point'] == [3.5, 1.5]
    assert not (root/selection.MANIFEST).exists()
    _prepare_original_candidates(root)
    chosen = selection.select(root, root/'runs/a', 'a', (3.5, 1.5), 'EPSG:32617', root/'mask.tif')
    receipt = selection.read_json(root/'runs/a'/selection.RECEIPT)
    assert receipt['selected_passes'] == 0
    assert receipt['attempted'][0]['reason'] == 'outlet_not_retained'
    assert receipt['point'] == [3.5, 1.5]
    assert receipt['cell'] == [7, 3]
    # Crop translation is coordinate-based, not a reuse of original row/column.
    with rasterio.open(chosen[0]) as src:
        window = rasterio.windows.Window(2, 3, 5, 6)
        profile = src.profile.copy()
        profile.update(width=5, height=6, transform=src.window_transform(window))
        cropped = root/'cropped.tif'
        with rasterio.open(cropped, 'w', **profile) as dst:
            dst.write(src.read(1, window=window), 1)
    output = root/'run-outlet.geojson'
    selection.install_original_outlet(root, 'a', cropped, output)
    feature = json.loads(output.read_text())['features'][0]
    assert feature['geometry']['coordinates'] == outlet['coordinates']
    assert feature['properties']['row'] == 5
    assert feature['properties']['column'] == 2
    assert selection.select(root, root/'runs/a', 'a', (3.5, 1.5), 'EPSG:32617', root/'mask.tif') == chosen


def test_original_outlet_identity_and_source_changes(original_outlets):
    root, runner = original_outlets
    _prepare_original_candidates(root)
    record = selection.read_json(root/selection.ORIGINAL_OUTLETS)
    record['outlets']['a']['coordinates'][0] += 1
    selection.write_json(root/selection.ORIGINAL_OUTLETS, record)
    with pytest.raises(ValueError, match='identity changed'):
        selection.select(root, root/'runs/a', 'a', (3.5, 1.5), 'EPSG:32617', root/'mask.tif')
    with (root/'points.geojson').open('a') as handle: handle.write(' ')
    with pytest.raises(ValueError, match='inputs changed'):
        selection.prepare_original_outlets(root, root/'topo/pointer.tif', root/'topo/streams.tif',
            root/'topo/dem.tif', root/'points.geojson', root/'watersheds.geojson', runner)


def test_original_outlet_archive_restore(original_outlets, tmp_path):
    from wepppy.rq.culvert_rq_manifest import _write_run_skeletons_zip
    root, _ = original_outlets
    _prepare_original_candidates(root)
    selection.select(root, root/'runs/a', 'a', (3.5, 1.5), 'EPSG:32617', root/'mask.tif')
    archive = _write_run_skeletons_zip(root)
    restored = tmp_path/'restored'
    with zipfile.ZipFile(archive) as z: z.extractall(restored)
    assert selection.reuse_ready(restored)
    shutil.copyfile(root/'mask.tif', restored/'mask.tif')
    selection.select(restored, restored/'runs/a', 'a', (3.5, 1.5), 'EPSG:32617', restored/'mask.tif')
    (restored/selection.ORIGINAL_OUTLETS).unlink()
    with pytest.raises(FileNotFoundError): selection.reuse_ready(restored)


def test_unresolved_original_outlet_is_explicit(original_outlets):
    root, runner = original_outlets
    (root/selection.ORIGINAL_OUTLETS).unlink()
    raster(root/'topo/streams.tif', np.zeros((9, 9)))
    selection.prepare_original_outlets(root, root/'topo/pointer.tif', root/'topo/streams.tif',
        root/'topo/dem.tif', root/'points.geojson', root/'watersheds.geojson', runner)
    record = selection.read_json(root/selection.ORIGINAL_OUTLETS)
    assert record['state'] == 'ready'
    assert record['outlets']['a']['state'] == 'failed'
    with pytest.raises(ValueError, match='No original stream outlet'):
        selection.original_outlet(root, 'a')


def test_unknown_selection_basis_rejected(tmp_path):
    selection.write_json(tmp_path/selection.POLICY, {'version': 1, 'selection_basis': 'unknown'})
    with pytest.raises(ValueError, match='Unknown stream selection basis'):
        selection.has_policy(tmp_path)


def test_original_outlet_policy_cannot_be_downgraded(original_outlets):
    root, _ = original_outlets
    _prepare_original_candidates(root)
    selection.select(root, root/'runs/a', 'a', (3.5, 1.5), 'EPSG:32617', root/'mask.tif')
    selection.write_json(root/selection.POLICY, {'version': 1})
    with pytest.raises(ValueError, match='selection basis'): selection.has_policy(root)
    (root/selection.ORIGINAL_OUTLETS).unlink()
    with pytest.raises(ValueError, match='selection basis'): selection.has_policy(root)
    (root/selection.MANIFEST).unlink()
    with pytest.raises(ValueError, match='selection basis'): selection.has_policy(root)
    (root/selection.POLICY).unlink()
    with pytest.raises(ValueError, match='without policy'): selection.has_policy(root)


def test_orphan_original_outlet_record_is_not_legacy(tmp_path):
    selection.write_json(tmp_path/selection.ORIGINAL_OUTLETS, {'version': 1, 'state': 'preparing'})
    with pytest.raises(ValueError, match='without policy'): selection.has_policy(tmp_path)
