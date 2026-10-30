"""Reject invalid scientific budgets and exercise unequal-area conservation."""
from copy import deepcopy
import importlib.util
import itertools
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
PATH = Path(__file__).resolve().parents[2] / 'docs/work-packages/20261029_roads_ofe_budget/artifacts/accounting.py'
SPEC = importlib.util.spec_from_file_location('roads_ofe_accounting', PATH)
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


def sediment():
    return [dict(year=2000, julian=1, OFE=i, SedLeave=v) for i,v in enumerate((2., 5., 3.),1)]


def test_sediment_boundary_exchange_and_independent_reconciliation():
    result, days = a.sediment_budget(sediment(), 4, 2, 6)
    assert [o['net_kg_yr'] for o in result['ofes']] == [4, 6, -4]
    assert result['ofes'][2]['negative_daily_net_kg_yr'] == -4
    assert a.ebe_check([dict(year=2000,julian=1,**{'Sed.Del':3.})],days)['dates'] == 1
    with pytest.raises(ValueError, match='ELEMENT/report'):
        a.sediment_budget(sediment(),4,2,7)
    with pytest.raises(ValueError, match='EBE/ELEMENT'):
        a.ebe_check([dict(year=2000,julian=1,**{'Sed.Del':4.})],days)
    with pytest.raises(ValueError, match='Missing EBE'):
        a.ebe_check([],days)


@pytest.mark.parametrize('failure', ['duplicate','missing','nonfinite','invalid_date','negative'])
def test_bad_element_records_rejected(failure):
    rows=sediment()
    if failure=='duplicate': rows.append(rows[0])
    if failure=='missing': rows.pop()
    if failure=='nonfinite': rows[0]['SedLeave']=float('nan')
    if failure=='invalid_date': rows[0]['julian']=367
    if failure=='negative': rows[0]['SedLeave']=-1
    with pytest.raises(ValueError): a.sediment_budget(rows,4,2,6)


def water():
    rows=[]
    for j in (1,2):
        for i,(area,q,up,sub,lat) in enumerate([(100.,10.,0.,0.,2.),(200.,10.,5.,1.,1.),(300.,10.,10.,2/3,1.)],1):
            rows.append(dict(year=2000,julian=j,OFE=i,Area=area,Q=q,UpStrmQ=up,SubRIn=sub,latqcc=lat,
                             P=20.,RM=20.,Ep=0.,Es=0.,Er=0.,Dp=0.,Tile=0.,SoilWaterTotal=100.))
    return rows


def test_cumulative_runoff_uses_cumulative_area_and_lateral_uses_local_area():
    result=a.water_budget(water(),[100,200,300],{(2000,1),(2000,2)},1)
    assert [o['surface_out_m3_yr'] for o in result['ofes']]==[2,6,12]
    assert [o['surface_in_m3_yr'] for o in result['ofes']]==[0,2,6]
    assert result['max_lateral_transfer_delta_m3']==pytest.approx(0)
    assert result['residual_days']==1
    assert result['residual_is_complete_water_closure'] is False


@pytest.mark.parametrize('failure', ['calendar','duplicate','missing','nonfinite','area','surface','lateral'])
def test_bad_water_records_rejected(failure):
    rows=water()
    dates={(2000,1),(2000,2)}
    if failure=='calendar': dates.add((2000,3))
    if failure=='duplicate':rows.append(rows[0])
    if failure=='missing':rows.pop()
    if failure=='nonfinite':rows[0]['Q']=float('inf')
    if failure=='area':rows[0]['Area']=101
    if failure=='surface':rows[1]['UpStrmQ']=6
    if failure=='lateral':rows[1]['SubRIn']=2
    with pytest.raises(ValueError):a.water_budget(rows,[100,200,300],dates,1)


def factorial():
    records=[]
    for bits in itertools.product('01',repeat=3):
        ofes=[]
        for i,bit in enumerate(bits):
            ofes.append(dict(ki=i+1,ksatadj=int(bit),ksatfac=1.,ksatrec=1.,horizons=[
                dict(solthk=200,ksat=10 if bit=='0' else 1,clay=20),dict(solthk=400,ksat=5,clay=30)]))
        records.append(dict(case=dict(variant=''.join(bits)),soil_readback=ofes))
    return records


def test_factorial_fixed_fields_and_lower_horizons():
    records=factorial()
    a.validate_factorial(records)
    changed=deepcopy(records)
    changed[-1]['soil_readback'][0]['ki']=99
    with pytest.raises(ValueError):a.validate_factorial(changed)
    changed=deepcopy(records)
    # A consistent deep hydraulic toggle is still disallowed.
    for r in changed:
        if r['case']['variant'][0]=='1':r['soil_readback'][0]['horizons'][1]['ksat']=1
    with pytest.raises(ValueError,match='Deeper'):a.validate_factorial(changed)
    changed=deepcopy(records)
    changed[1]['soil_readback'][0]['ksatfac']=99
    with pytest.raises(ValueError,match='leaked'):a.validate_factorial(changed)


def test_diagnostic_mode_retains_reconciliation_failure_without_widening_bound():
    result,days=a.sediment_budget(sediment(),4,2,7,strict=False)
    assert result['report_reconciled'] is False
    assert result['report_delta_kg_yr']==-1
    assert result['report_bound_kg_yr']<.01
    result=a.ebe_check([dict(year=2000,julian=1,**{'Sed.Del':4.})],days,strict=False)
    assert result['mismatches']==[dict(date=(2000,1),ebe_kg_m=4.,element_kg_m=3.,delta_kg_m=1.)]
    # Diagnostic mode still rejects missing scientific records.
    with pytest.raises(ValueError):a.ebe_check([],days,strict=False)
