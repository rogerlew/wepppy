"""Scientific comparison must preserve treatments and explicitly handle zeros."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

pytestmark = pytest.mark.unit
PATH = Path(__file__).resolve().parents[2]/'docs/work-packages/20261029_roads_drainage_validation/artifacts/study.py'
SPEC = importlib.util.spec_from_file_location('roads_drainage_validation',PATH)
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


def test_zero_reference_is_not_a_factor_ten_success():
    assert s.comparison(0,0) == dict(ratio=None,within=None,zero_reference=True,zero_match=True)
    assert s.comparison(1,0)['zero_match'] is False
    assert s.comparison(0,1)['within'] is False


@pytest.mark.parametrize('value,reference',[(float('nan'),1),(1,float('inf')),(-1,1),(1,-1)])
def test_nonfinite_or_negative_metric_rejected(value,reference):
    with pytest.raises(ValueError): s.comparison(value,reference)


@pytest.mark.parametrize('value,expected',[(0.099,False),(.1,True),(10,True),(10.001,False)])
def test_factor_ten_boundaries(value,expected):
    assert s.comparison(value,1)['within'] is expected


def test_buffer_only_material_preservation():
    ofes=[dict(ki=10,res_lyr=dict(slflag=1,kslast=.01,ui_bdrkth=10000),
               horizons=[dict(solthk=200,ksat=20),dict(solthk=400,ksat=10)]) for _ in range(3)]
    before=deepcopy(ofes)
    changed=s.buffer_change(ofes,3.276)
    assert ofes==before
    assert changed[:2]==before[:2]
    changed[2]['res_lyr']['kslast']=.01
    assert changed==before
    with pytest.raises(ValueError):s.buffer_change(ofes,0)
    ofes[1]['horizons'][0]['solthk']=150
    with pytest.raises(ValueError,match='normalized'):s.buffer_change(ofes,1)


def test_matrix_pairing_and_conservative_selection():
    cases=list(s.cases())
    assert len(cases)==len({tuple(c.values()) for c in cases})==1920
    profiles={tuple(c[k] for k in ('climate','soil','design','surface','traffic')) for c in cases}
    assert len(profiles)==960
    assert all(s.policy(soil)=='current' for soil in ('sand','new_lithic'))
    assert all(s.policy(soil)=='source' for soil in ('clay','new_lowk','new_open'))
