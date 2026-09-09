"""Real project-grid preparation and generic stacking regression fixtures."""
from pathlib import Path
from types import SimpleNamespace
import json
import logging

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

pytestmark = pytest.mark.integration


def raster(path, values, *, nodata=None, mask=None, dtype='float64', transform=None):
    data = np.array(values, dtype=dtype, ndmin=2)
    with rasterio.open(path, 'w', driver='GTiff', width=data.shape[1], height=data.shape[0],
                       count=1, dtype=dtype, crs='EPSG:32610', nodata=nodata,
                       transform=transform or from_origin(500000,5000000,30,30)) as dst:
        dst.write(data,1)
        if mask is not None: dst.write_mask(np.array(mask,dtype='uint8',ndmin=2))
    return str(path)


@pytest.mark.parametrize('source_nodata', [None, -99])
def test_stacker_uncovered_and_valid_zero(tmp_path, source_nodata):
    from wepppy.all_your_base.geo import raster_stacker
    src=raster(tmp_path/'s.tif', [[0,2]], nodata=source_nodata, mask=[[255,0]])
    match=raster(tmp_path/'k.tif', [[11]*4])
    dst=tmp_path/'out.tif'
    raster_stacker(src,match,dst,dst_nodata=-9999,dst_dtype='float64')
    with rasterio.open(dst) as ds:
        assert ds.read(1).tolist() == [[0,-9999,-9999,-9999]]
        assert ds.nodata == -9999
        assert ds.transform == from_origin(500000,5000000,30,30)
    raster_stacker(src,match,dst)
    with rasterio.open(dst) as ds:
        assert ds.nodata == source_nodata
        assert ds.read(1)[0,0] == 0


@pytest.mark.parametrize('kwargs', [dict(dst_nodata=-9999,dst_dtype='uint8'), dict(dst_nodata=1.5,dst_dtype='int16'),dict(dst_nodata=0)])
def test_stacker_rejects_invalid_destination_before_write(tmp_path, kwargs):
    from wepppy.all_your_base.geo import raster_stacker
    src=raster(tmp_path/'s.tif', [[0,2]])
    out=tmp_path/'out.tif'
    with pytest.raises(ValueError): raster_stacker(src,src,out,**kwargs)
    assert not out.exists()


@pytest.fixture
def mapped_wepp(tmp_path):
    (tmp_path/'soils').mkdir()
    grid=raster(tmp_path/'key.tif', [[11]*5+[21,0,14]])
    source=raster(tmp_path/'source.tif', [[.0001]*4+[0,float('inf'),3,4]])
    return SimpleNamespace(wd=str(tmp_path),kslast_map=source,kslast=.05,
                           watershed_instance=SimpleNamespace(subwta=grid),logger=logging.getLogger('kslast-test'))


def test_map_rebuild_default_source_grid_and_diagnostics(mapped_wepp):
    from wepppy.nodb.core.kslast_map import prepare_kslast_map
    w=mapped_wepp
    result=prepare_kslast_map(w,['11','21'])
    assert result['11']['mean'] == pytest.approx(.01008)
    assert result['21']['mean'] == .05
    summary=json.loads((Path(w.wd)/'soils/kslast_summary.json').read_text())
    assert summary['normalization'] == dict(nonpositive=1,nonfinite=1,source_or_uncovered_missing=0)
    with rasterio.open(Path(w.wd)/'soils/kslast.tif') as ds:
        assert ds.nodata == -9999
        assert ds.read(1)[0,4:6].tolist() == [-9999,-9999]
    w.kslast=.5
    assert prepare_kslast_map(w,['11','21'])['21']['mean'] == .5
    raster(w.kslast_map, [[.2]*8])
    assert prepare_kslast_map(w,['11','21'])['11']['mean'] == .2
    raster(w.watershed_instance.subwta, [[11]*8])
    assert prepare_kslast_map(w,['11'])['11']['total_cell_count'] == 8


@pytest.mark.parametrize('default', [None,0,-1,float('nan'),float('inf')])
def test_missing_or_bad_default_fails_before_publication(mapped_wepp, default):
    from wepppy.nodb.core.kslast_map import prepare_kslast_map
    mapped_wepp.kslast=default
    with pytest.raises(ValueError): prepare_kslast_map(mapped_wepp,['11','21'])
    assert not (Path(mapped_wepp.wd)/'soils/kslast.tif').exists()


def test_no_map_ignores_stale_artifacts_and_bad_scalar(mapped_wepp):
    from wepppy.nodb.core.kslast_map import prepare_kslast_map
    mapped_wepp.kslast_map=None
    mapped_wepp.kslast=-1
    assert prepare_kslast_map(mapped_wepp,['11']) is None


def test_archive_only_rejected_mixed_directory_authoritative(mapped_wepp):
    from wepppy.nodb.core.kslast_map import prepare_kslast_map
    wd=Path(mapped_wepp.wd)
    archive=wd/'soils.nodir'; archive.write_bytes(b'legacy archive left untouched')
    (wd/'soils').rmdir()
    with pytest.raises(FileNotFoundError,match='archive-only'): prepare_kslast_map(mapped_wepp,['11','21'])
    (wd/'soils').mkdir()
    prepare_kslast_map(mapped_wepp,['11','21'])
    assert archive.read_bytes() == b'legacy archive left untouched'


def test_bad_map_and_missing_keys_fail(mapped_wepp):
    from wepppy.nodb.core.kslast_map import prepare_kslast_map
    with pytest.raises(ValueError,match='keys mismatch'): prepare_kslast_map(mapped_wepp,['11','21','31'])
    Path(mapped_wepp.kslast_map).write_bytes(b'corrupt')
    with pytest.raises(rasterio.errors.RasterioIOError): prepare_kslast_map(mapped_wepp,['11','21'])


@pytest.mark.parametrize('multi_ofe', [False, True])
def test_both_orchestrators_use_grid_mean_before_worker_submission(mapped_wepp, monkeypatch, multi_ofe):
    from concurrent.futures import Future
    import wepppy.nodb.core.wepp as wm
    import wepppy.nodb.core.wepp_prep_service as service
    captured=[]
    class Pool:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def submit(self, func, args):
            captured.append(args)
            future=Future(); future.set_result((args[0],0.0)); return future
    monkeypatch.setattr(wm,'prep_multi_ofe_hillslope',lambda args:(captured.append(args) or (args[0],0.0)))
    monkeypatch.setattr(wm,'createProcessPoolExecutor',lambda **kwargs:Pool())
    monkeypatch.setattr(service,'createProcessPoolExecutor',lambda **kwargs:Pool())
    w=mapped_wepp
    w.class_name='Wepp'
    w.runs_dir=str(Path(w.wd)/'wepp/runs')
    w.climate_instance=SimpleNamespace(input_years=2)
    w.watershed_instance.subs_summary={'11':{},'21':{}}
    w.watershed_instance.clip_hillslopes_configured=False
    w.watershed_instance.clip_hillslope_length=300
    w.soils_instance=SimpleNamespace(clip_soils=False,clip_soils_depth=1,clip_soils_minimum=False,
            clip_soils_minimum_depth=1,initial_sat=.5,
            sub_iter=lambda:iter([('11',SimpleNamespace(fname='11.sol')),('21',SimpleNamespace(fname='21.sol'))]))
    for key in ['11','21']: (Path(w.wd)/'soils'/f'{key}.sol').write_text('worker source fixture')
    translator=SimpleNamespace(wepp=lambda *,top:top)
    if multi_ofe: wm.Wepp._prep_multi_ofe(w,translator,max_workers=1)
    else: service.WeppPrepService().prep_soils(w,translator,max_workers=1)
    values={arg[0]:arg[5 if multi_ofe else 3] for arg in captured}
    assert values == {'11':pytest.approx(.01008),'21':.05}
    for arg in captured:
        pars=arg[13 if multi_ofe else 4]
        assert pars['aggregation']=='project_cell_area_mean'
        assert 'lng' not in pars
    captured.clear()
    w.kslast=None
    with pytest.raises(ValueError,match='Missing parameter coverage'):
        if multi_ofe: wm.Wepp._prep_multi_ofe(w,translator,max_workers=1)
        else: service.WeppPrepService().prep_soils(w,translator,max_workers=1)
    assert captured == []


@pytest.mark.parametrize('values,nodata,dtype', [([0,2],1e-300,'float32'),([.1,2],0,'int16'),([.6,2],1,'int16')])
def test_stacker_rejects_cast_sentinel_collisions(tmp_path, values,nodata,dtype):
    from wepppy.all_your_base.geo import raster_stacker
    source=raster(tmp_path/'s.tif', [values])
    destination=tmp_path/'out.tif'
    with pytest.raises(ValueError):
        raster_stacker(source,source,destination,dst_nodata=nodata,dst_dtype=dtype)
    assert not destination.exists()


def test_stacker_rejects_resampling_generated_sentinel(tmp_path):
    from wepppy.all_your_base.geo import raster_stacker
    src=raster(tmp_path/'s.tif',[[-1,1]])
    target=raster(tmp_path/'k.tif',[[11]],transform=from_origin(500000,5000000,60,30))
    with pytest.raises(ValueError,match='collides'):
        raster_stacker(src,target,tmp_path/'out.tif',resample='average',dst_nodata=0)


def test_publication_rejects_escaping_soils_symlink(mapped_wepp, tmp_path):
    from wepppy.nodb.core.kslast_map import prepare_kslast_map
    soil=Path(mapped_wepp.wd)/'soils';soil.rmdir()
    outside=tmp_path.parent/(tmp_path.name+'-outside');outside.mkdir()
    soil.symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='escapes'):
        prepare_kslast_map(mapped_wepp,['11','21'])
    assert list(outside.iterdir()) == []


def test_lock_contention_and_failed_validation_leave_previous_pair(mapped_wepp):
    from wepppy.nodb.core.kslast_map import prepare_kslast_map
    from wepppy.runtime_paths.thaw_freeze import maintenance_lock
    from wepppy.runtime_paths.errors import NoDirError
    w=mapped_wepp
    prepare_kslast_map(w,['11','21'])
    paths=[Path(w.wd)/'soils'/name for name in ['kslast.tif','kslast_summary.json']]
    before=[p.read_bytes() for p in paths]
    with maintenance_lock(w.wd,'soils',purpose='test-competing-writer'):
        with pytest.raises(NoDirError): prepare_kslast_map(w,['11','21'])
    w.kslast=None
    with pytest.raises(ValueError): prepare_kslast_map(w,['11','21'])
    assert [p.read_bytes() for p in paths] == before
    assert not list((Path(w.wd)/'soils').glob('.kslast-*'))


def test_in_run_soils_alias_supported(mapped_wepp):
    from wepppy.nodb.core.kslast_map import prepare_kslast_map
    wd=Path(mapped_wepp.wd);(wd/'soils').rename(wd/'soil-data')
    (wd/'soils').symlink_to(wd/'soil-data',target_is_directory=True)
    assert prepare_kslast_map(mapped_wepp,['11','21'])['11']['mean'] == pytest.approx(.01008)


@pytest.mark.parametrize('multi_ofe', [False,True])
@pytest.mark.parametrize('developed', [False,True])
def test_real_soil_workers_propagate_mean_to_every_ofe(mapped_wepp, multi_ofe, developed):
    import copy
    from wepppy.nodb.core.kslast_map import prepare_kslast_map, kslast_provenance
    from wepppy.nodb.core.wepp import prep_soil, prep_multi_ofe_hillslope
    from wepppy.wepp.soils.utils import WeppSoilUtil
    w=mapped_wepp;wd=Path(w.wd);runs=wd/'wepp/runs';runs.mkdir(parents=True)
    fixture=Path(__file__).parents[1]/'omni/fixtures/honeyed_marathoner_sediment_inversion/run_root/wepp/runs'
    soil=WeppSoilUtil(str(fixture/'p118.sol'))
    soil.obj['ofes'][0]['luse']='developed' if developed else 'forest'
    soil.obj['ofes']=[copy.deepcopy(soil.obj['ofes'][0]) for _ in range(2)]
    soil.obj['ntemp']=2
    source=wd/'soils/hill_11.mofe.sol';soil.write(str(source))
    original=WeppSoilUtil(str(source))
    records=prepare_kslast_map(w,['11','21']);value=records['11']['mean'];pars=kslast_provenance(w.kslast_map,records['11'])
    if multi_ofe:
        slope=wd/'watershed/slope_files/hillslopes/hill_11.mofe.slp';slope.parent.mkdir(parents=True)
        slope.write_text('97.5\n2\n0 30\n2 30\n0,0.1 1,0.1\n2 30\n0,0.1 1,0.1\n')
        (wd/'landuse').mkdir();(wd/'landuse/hill_11.mofe.man').write_bytes((fixture/'p118.man').read_bytes())
        prep_multi_ofe_hillslope(('11',1,w.wd,str(runs),2,value,.5,False,300,False,1,False,1,pars))
    else:
        prep_soil(('11',str(source),str(runs/'p1.sol'),value,pars,.5,False,1,False,1))
    generated=WeppSoilUtil(str(runs/'p1.sol'))
    assert len(generated.obj['ofes'])==2
    for i,ofe in enumerate(generated.obj['ofes']):
        expected=original.obj['ofes'][i]['res_lyr']['kslast'] if developed else value
        assert float(ofe['res_lyr']['kslast']) == pytest.approx(float(expected), rel=1e-12)


def test_stacker_dtype_override_checks_inherited_nodata(tmp_path):
    from wepppy.all_your_base.geo import raster_stacker
    src=raster(tmp_path/'s.tif',[[.1,2]],nodata=0)
    with pytest.raises(ValueError,match='collides'):
        raster_stacker(src,src,tmp_path/'out.tif',dst_dtype='int16')
