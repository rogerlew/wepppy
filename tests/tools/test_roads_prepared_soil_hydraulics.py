"""Depth-treatment regression tests for the isolated Roads experiment."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

pytestmark = pytest.mark.unit
PATH = Path(__file__).resolve().parents[2]/'docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py'
SPEC = importlib.util.spec_from_file_location('roads_prepared_soil_experiment',PATH)
experiment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(experiment)


def profile():
    return {'nsl':3,'ki':1e6,'res_lyr':{'kslast':0.01},'horizons':[
        {'solthk':80.,'ksat':30.,'clay':10.,'bd':1.1},
        {'solthk':300.,'ksat':20.,'clay':20.,'bd':1.3},
        {'solthk':800.,'ksat':8.,'clay':30.,'bd':1.5}]}


def test_layer_split_preserves_deeper_material_and_other_ofes():
    ofes=[profile(),profile(),profile()]
    original=deepcopy(ofes)
    experiment.split_layer(ofes[0],200,3)
    assert ofes[1:]==original[1:]
    road=ofes[0]
    assert road['nsl']==4
    assert [h['solthk'] for h in road['horizons']]==[80,200,300,800]
    assert [h['ksat'] for h in road['horizons']]==[3,3,20,8]
    assert road['horizons'][2:]==original[0]['horizons'][1:]
    assert road['horizons'][1]['clay']==20
    assert road['ki']==original[0]['ki']
    assert road['res_lyr']==original[0]['res_lyr']


def test_existing_boundary_does_not_duplicate_horizon():
    soil=profile()
    experiment.split_layer(soil,300,1)
    assert soil['nsl']==3
    assert [h['ksat'] for h in soil['horizons']]==[1,1,8]


@pytest.mark.parametrize('depth,conductivity',[(0,1),(900,1),(200,-1),(float('nan'),1),(200,float('inf'))])
def test_invalid_treatment_fails_without_mutating_soil(depth,conductivity):
    soil=profile();original=deepcopy(soil)
    with pytest.raises(ValueError):experiment.split_layer(soil,depth,conductivity)
    assert soil==original
