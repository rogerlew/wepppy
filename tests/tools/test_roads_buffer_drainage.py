"""Boundary-only diagnostic treatments must preserve other soil material."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

pytestmark=pytest.mark.unit
PATH=Path(__file__).resolve().parents[2]/'docs/work-packages/20261029_roads_buffer_drainage/artifacts/experiment.py'
SPEC=importlib.util.spec_from_file_location('roads_buffer_experiment',PATH)
e=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(e)


def soils():
    return [dict(ki=1.,sat=.75,res_lyr=dict(kslast=.00151,slflag=1,ui_bdrkth=10000),
                 horizons=[dict(solthk=200.,ksat=60.,clay=12.),dict(solthk=400.,ksat=9.72,clay=31.)]) for _ in range(3)]


@pytest.mark.parametrize('offset',[-1.,0.,1.])
def test_buffer_treatment_preserves_upstream_and_all_material(offset):
    original=soils();before=deepcopy(original)
    result=e.change_buffer(original,1.512,offset)
    assert original==before
    assert result[:2]==original[:2]
    assert result[2]['horizons'][0]==original[2]['horizons'][0]
    assert result[2]['horizons'][-1]==dict(solthk=400+offset,ksat=9.72,clay=31.)
    result[2]['horizons'][-1]['solthk']-=offset
    result[2]['res_lyr']['kslast']=.00151
    assert result==original


@pytest.mark.parametrize('conductivity,offset',[(0,0),(-1,0),(float('nan'),0),(float('inf'),0),(1,2)])
def test_invalid_treatment_rejected(conductivity,offset):
    with pytest.raises(ValueError):e.change_buffer(soils(),conductivity,offset)


def test_missing_normalization_and_crossed_boundary_rejected():
    profiles=soils();profiles[2]['horizons'][0]['solthk']=150
    with pytest.raises(ValueError,match='200'):e.change_buffer(profiles,1,0)
    profiles=soils();profiles[2]['horizons'][-1]['solthk']=201
    with pytest.raises(ValueError,match='crosses'):e.change_buffer(profiles,1,-1)


@pytest.mark.parametrize('bottom,expected',[(399,400),(400,600),(401,600),(1599,1600),(1600,1800),(1601,1800)])
def test_source_audited_computational_depth(bottom,expected):
    assert e.expected_depth(bottom)==expected
