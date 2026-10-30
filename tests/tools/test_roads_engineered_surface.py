"""Engineered surface hypotheses preserve deeper generated material and other roles."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

pytestmark=pytest.mark.unit
PATH=Path(__file__).resolve().parents[2]/'docs/work-packages/20261029_roads_parameterization_program/artifacts/engineered_surface_screen.py'
SPEC=importlib.util.spec_from_file_location('engineered_road_screen',PATH)
s=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(s)


def profile():
    ofe=dict(ksatadj='1',ksatfac='100',ksatrec='0.3',ki=1000,res_lyr=dict(kslast=.001),
             horizons=[dict(solthk=150,ksat=30,rfg=35),dict(solthk=200,ksat=3,rfg=55),dict(solthk=400,ksat=3,rfg=55)])
    return [deepcopy(ofe) for _ in range(3)]


@pytest.mark.parametrize('target',s.TARGETS)
def test_scope_and_cap_never_increase_source_conductivity(target):
    before=profile();snapshot=deepcopy(before)
    result=s.transform(before,{'avke':10},target)
    assert before==snapshot
    assert result[2]==before[2]
    assert result[0]['horizons'][2:]==before[0]['horizons'][2:]
    for i in (0,1,2):
        assert result[i]['res_lyr']==before[i]['res_lyr']
        assert result[i]['ksatadj']==('0' if i in s.TARGETS[target] else '1')
    if target.endswith('_cap'):
        assert [h['ksat'] for h in result[0]['horizons']]==[10,3,3]
    else:
        assert result[0]['horizons']==before[0]['horizons']
    assert result[1]['horizons']==before[1]['horizons']


@pytest.mark.parametrize('cap',[float('nan'),float('inf'),0,-1])
def test_invalid_surface_prior_rejected(cap):
    with pytest.raises(ValueError,match='Invalid reference surface cap'):
        s.transform(profile(),{'avke':cap},'road_cap')


def test_no_partial_treatment_without_boundary():
    before=profile();before[0]['horizons'].pop(1)
    with pytest.raises(ValueError,match='boundary'):
        s.transform(before,{'avke':10},'road_cap')
