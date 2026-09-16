"""Kf source boundaries and independent scalar curve checks."""
from dataclasses import replace
import math
import numpy as np
import pytest
import rasterio
from rasterio.warp import transform_bounds
from rasterio.transform import from_origin
from wepppy.nodb.mods.postfire_debris_flow import kf_source as kf, rainfall_io as io
from wepppy.nodb.mods.postfire_debris_flow.response_curve import response_curve, rainfall_provenance
from tests.nodb.mods.test_postfire_debris_flow_integration import inputs, BINARY, refresh

pytestmark = pytest.mark.integration


def fake_native(grid, output):
    """Fixed synthetic source at the acquisition seam; keep real alignment/publication."""
    affine=rasterio.Affine(*grid['transform']); rows,cols=grid['shape']
    left,top=affine*(0,0);right,bottom=affine*(cols,rows)
    left,bottom,right,top=transform_bounds(grid['crs'],'EPSG:5069',left,bottom,right,top)
    shape=(math.ceil((top-bottom)/30)+2,math.ceil((right-left)/30)+2)
    transform=from_origin(left-30,top+30,30,30)
    with rasterio.open(output/'native_kf.tif','w',driver='GTiff',height=shape[0],width=shape[1],
                       count=1,dtype='float32',crs='EPSG:5069',transform=transform,nodata=np.nan) as ds:
        ds.write(np.full(shape,.14,dtype='float32'),1)
    (output/'requests').mkdir()
    io.write_json(output/'requests/request-001.json',{'fixture':True})
    io.write_json(output/'native_evidence.json',dict(object_identity=['"fixture"',100,None],
        native_grid=dict(shape=list(shape),crs='EPSG:5069',transform=list(transform)[:6]),
        native_sha256=io.digest(output/'native_kf.tif',io.MAX_PREDICTOR_BYTES),retrieved_at='2026-09-16T00:00:00+00:00'))


def test_acquire_and_schema3_roundtrip(inputs,tmp_path,monkeypatch):
    from wepppy.nodb.mods.postfire_debris_flow.integration import build_m1_predictors
    from wepppy.nodb.mods.postfire_debris_flow.predictor_v2 import load_artifacts
    monkeypatch.setattr(kf,'_native_window',fake_native)
    out=tmp_path/'kf'; m=kf.acquire_kf(inputs.dem,inputs.mask,out)
    assert m['valid_cells']==25 and m['missing_cells']==0
    assert m['units']=='USLE_customary' and m['field']=='KFFACT'
    for key,value in [('field','KWFACT'),('units','SI'),('aggregation','surface_0_15_cm'),('policy','unknown'),('schema_version',True)]:
        with pytest.raises(ValueError):kf.validate_manifest({**m,key:value})
    i=refresh(replace(inputs,k=out/'kf.tif',k_manifest=out/'manifest.json',soil_policy=kf.POLICY))
    build_m1_predictors(i,tmp_path/'predictors',wbt_executable=BINARY,support_policy='common_valid_v1')
    manifest=io.read_json(tmp_path/'predictors/manifest.json')
    io.validate_predictors(manifest)
    load_artifacts(tmp_path/'predictors',manifest,{},None)
    assert manifest['schema_version']==3
    assert manifest['predictors']['S']['value']==pytest.approx(.14)
    assert 'k_provenance' not in manifest
    with pytest.raises(FileExistsError):kf.acquire_kf(inputs.dem,inputs.mask,out)


@pytest.mark.parametrize('value',[-.2,1.1,np.inf,-np.inf])
def test_invalid_native_values_are_not_missing(value):
    with pytest.raises(ValueError):kf._usable(np.array([value]),np.array([True]))


def test_publisher_missing_sentinel_and_zero():
    values=np.array([np.float32(-.1),np.nan,0.,.14])
    assert kf._usable(values,np.ones(4,dtype=bool)).tolist()==[False,False,True,True]


@pytest.mark.parametrize('hostile',['symlink','vrt','changed'])
def test_native_artifact_substitution_rejected(inputs,tmp_path,monkeypatch,hostile):
    from wepppy.nodb.mods.postfire_debris_flow import source_acquisition
    def supervise(operation,worker,args,output,seconds):
        fake_native(args[0],output)
        path=output/'native_kf.tif';path.unlink()
        if hostile=='symlink':path.symlink_to(inputs.dem)
        elif hostile=='vrt':path.write_text('<VRTDataset rasterXSize="1" rasterYSize="1"/>')
        else:path.write_bytes(b'changed')
    monkeypatch.setattr(source_acquisition,'_supervise',supervise)
    with pytest.raises(ValueError):kf.acquire_kf(inputs.dem,inputs.mask,tmp_path/'kf')
    assert (tmp_path/'kf/incomplete.json').exists()
    assert not (tmp_path/'kf/manifest.json').exists()


@pytest.mark.parametrize('duration,coefficients',[(15,(-3.63,.41,.67,.70)),(30,(-3.61,.26,.39,.50)),(60,(-3.21,.17,.20,.220))])
def test_curve_independent_coefficients(duration,coefficients):
    predictors=dict(T=.65,F=.4,S=.14)
    manifest=dict(model='M1',predictor_snapshot={'predictors':{k:{'value':v} for k,v in predictors.items()}})
    markers=[dict(duration_minutes=duration,intensity_mm_per_hour=i) for i in (24.,36.,48.,60.)]
    curve=response_curve(manifest,markers,duration)
    assert curve['status']=='available' and 101<=len(curve['points'])<=106
    b,ct,cf,cs=coefficients; slope=ct*.65+cf*.4+cs*.14
    assert curve['p50']['intensity_mm_per_hour']==pytest.approx(-b/slope*60/duration)
    for row in curve['points']:
        assert row['probability']==pytest.approx(1/(1+math.exp(-(b+row['intensity_mm_per_hour']*duration/60*slope))))
    assert all(i in [p['intensity_mm_per_hour'] for p in curve['points']] for i in (24,36,48,60))


@pytest.mark.parametrize('fire,direction',[(0,'constant'),(-1,'decreasing')])
def test_curve_preserves_nonincreasing_engine_semantics(fire,direction):
    m=dict(model='M1',predictor_snapshot={'predictors':{k:{'value':v} for k,v in dict(T=0,F=fire,S=0).items()}})
    result=response_curve(m,[],15)
    assert result['direction']==direction and result['p50']['status']=='unavailable'


def test_rainfall_provenance_does_not_infer_measurements_from_dates():
    assert rainfall_provenance({'climate_mode':'GridMetPRISM','date_semantics':'calendar'},'noaa')['subdaily_origin']=='modeled_disaggregated'
    assert rainfall_provenance({'climate_mode':'UserDefined'},'cli')['subdaily_origin']=='not_recorded'


def test_curve_inverse_arithmetic_failure_is_unavailable():
    m=dict(model='M1',predictor_snapshot={'predictors':{k:{'value':v} for k,v in dict(T=0,F=1e-308,S=0).items()}})
    curve=response_curve(m,[],15)
    assert curve['status']=='unavailable' and curve['reason']=='arithmetic_overflow'
    assert curve['points']==[]


def test_native_replacement_after_decode_cannot_be_blessed(inputs,tmp_path,monkeypatch):
    monkeypatch.setattr(kf,'_native_window',fake_native)
    original=kf.prepare
    def replace_native(path,*args,**kwargs):
        result=original(path,*args,**kwargs)
        (Path(path).parent/'native_kf.tif').write_bytes(b'replaced after decode')
        return result
    from pathlib import Path
    monkeypatch.setattr(kf,'prepare',replace_native)
    with pytest.raises(ValueError,match='Retained native Kf changed'):
        kf.acquire_kf(inputs.dem,inputs.mask,tmp_path/'kf')
    assert not (tmp_path/'kf/manifest.json').exists()
