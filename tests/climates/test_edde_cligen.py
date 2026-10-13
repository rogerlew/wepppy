"""EDDE conditioning and explicit Multiple PRISM artifact semantics."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from wepppy.climates.edde.cligen import build_climate, normalize_daily, read_cli, revise_prism
from wepppy.climates.edde.client import DataQualityError



def source():
    dates=pd.date_range('2000-01-01','2000-12-31')
    table=pd.DataFrame(dict(point='fixture',date=dates,prday=np.where(np.arange(len(dates))%4==0,4.,0.),
                            tsmax=290.,tsmin=280.))
    meta=dict(status='complete',model='WRF-MPI',scenario='Historical',start='2000-01-01',end='2000-12-31',points=[{'name':'fixture','longitude':0,'latitude':0,'row':0,'col':0}],objects=[
        dict(variable='prday',netcdf_variable='PRECIP',units='kg m-2'),
        dict(variable='tsmax',netcdf_variable='T2MAX',units='K'),
        dict(variable='tsmin',netcdf_variable='T2MIN',units='K')])
    return table,[meta]


@pytest.mark.unit
def test_units_and_unchanged_source():
    table,meta=source()
    normalized=normalize_daily(table,meta)
    assert normalized.iloc[0].prcp_mm==4
    assert normalized.iloc[0].tmax==pytest.approx(16.85)
    assert table.tsmax.iloc[0]==290
    meta[0]['objects'][0]['units']='kg m-2 s-1'
    with pytest.raises(DataQualityError,match='units'):normalize_daily(table,meta)


@pytest.mark.parametrize('defect',['gap','negative','inverted','nan','partial'])
@pytest.mark.unit
def test_reject_bad_daily_inputs(defect):
    table,meta=source()
    if defect=='gap':table=table.drop(10)
    if defect=='negative':table.loc[10,'prday']=-1
    if defect=='inverted':table.loc[10,'tsmin']=300
    if defect=='nan':table.loc[10,'tsmax']=float('nan')
    if defect=='partial':table=table.iloc[1:]
    with pytest.raises(DataQualityError):normalize_daily(table,meta)


def normals(ppt=100,tmax=20,tmin=10):
    return dict(ppt=[ppt]*12,tmax=[tmax]*12,tmin=[tmin]*12,provenance=dict(period='1991-2020',sha256='fixture',units={'ppt':'mm/month','tmax':'C','tmin':'C'}))


@pytest.mark.unit
def test_prism_invalid_normals_do_not_emit(tmp_path):
    with pytest.raises(DataQualityError,match='positive'):
        revise_prism('unused',tmp_path/'out.cli',normals(0),normals())
    with pytest.raises(DataQualityError,match='finite'):
        revise_prism('unused',tmp_path/'out.cli',normals(float('nan')),normals())
    assert not (tmp_path/'out.cli').exists()


@pytest.mark.unit
def test_prism_preserves_existing_provenance(tmp_path):
    companion = tmp_path / 'out.prism.json'
    companion.write_text('prior evidence')
    with pytest.raises(ValueError, match='new file'):
        revise_prism('unused', tmp_path / 'out.cli', normals(), normals())
    assert companion.read_text() == 'prior evidence'
    assert not (tmp_path / 'out.cli').exists()


@pytest.mark.integration
def test_real_cligen_and_prism_generated_artifacts(tmp_path):
    from wepppy.climates.cligen import CligenStationsManager
    table,meta=source()
    station=CligenStationsManager().get_station_fromid('wa458928')
    if station is None:
        raise AssertionError('Required canonical Walla Walla station missing')
    result=build_climate(table,meta,station,tmp_path/'base',seed=1001)
    source_path=tmp_path/'base/wepp.cli'
    assert result['days']==366 and result['status']=='complete'
    assert read_cli(source_path).index[-1]==pd.Timestamp('2000-12-31')
    target=tmp_path/'target.cli'
    revise_prism(source_path,target,normals(),normals(150,22,11))
    base,actual=read_cli(source_path),read_cli(target)
    np.testing.assert_allclose(actual.prcp,base.prcp*1.5,atol=.05)
    np.testing.assert_allclose(actual.tmax,base.tmax+2,atol=.05)
    np.testing.assert_allclose(actual.tmin,base.tmin+1,atol=.05)
    assert (tmp_path/'base/daily.prn').is_file()
    assert target.with_suffix('.prism.json').is_file()
    from wepppy.climates.cligen import ClimateFile
    for name, value in [('prcp', -1.0), ('dur', 0.0)]:
        damaged = ClimateFile(str(source_path))
        damaged.replace_var(name, [(2000, 1, 1)], [value])
        bad_source = tmp_path / f'bad-{name}.cli'
        bad_output = tmp_path / f'revised-{name}.cli'
        damaged.write(str(bad_source))
        with pytest.raises(DataQualityError):
            revise_prism(bad_source, bad_output, normals(), normals())
        assert not bad_output.exists()
        assert not bad_output.with_suffix('.prism.json').exists()
    lines = source_path.read_text().splitlines()
    daily_line = next(i for i, line in enumerate(lines) if line.split()[:3] == ['1', '1', '2000'])
    values = lines[daily_line].split()
    values[10] = 'nan'  # Corrupt serialized wind without the writer's validation.
    lines[daily_line] = ' '.join(values)
    bad_source = tmp_path / 'nonfinite.cli'
    bad_source.write_text('\n'.join(lines) + '\n')
    with pytest.raises(DataQualityError, match='nonfinite'):
        revise_prism(bad_source, tmp_path / 'nonfinite-result.cli', normals(), normals())
    with pytest.raises(FileExistsError):build_climate(table,meta,station,tmp_path/'base',seed=1001)


@pytest.mark.unit
def test_reject_mismatched_prism_reference_period(tmp_path):
    reference,target=normals(),normals()
    target['provenance']['period']='1981-2010'
    with pytest.raises(DataQualityError,match='periods'):
        revise_prism('unused',tmp_path/'out.cli',reference,target)


@pytest.mark.unit
def test_reject_mixed_point_provenance():
    import copy
    table,meta=source()
    changed=copy.deepcopy(meta[0])
    changed['points'][0]['row']=1
    with pytest.raises(DataQualityError,match='locations'):
        normalize_daily(table,[meta[0],changed])
