"""The development screen must preserve source material outside its declared scope."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
PATH = Path(__file__).resolve().parents[2]/'docs/work-packages/20261029_roads_parameterization_program/artifacts/screen.py'
SPEC = importlib.util.spec_from_file_location('roads_parameterization_screen', PATH)
screen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen)


def specimen():
    road = dict(ki=123, kr=.002, shcrit=4, ksatadj=1, ksatfac=.3, ksatrec=.01,
                res_lyr=dict(kslast=.001), horizons=[
                    dict(solthk=d, ksat=k, rfg=20, sand=60, clay=20, bd=1.4)
                    for d, k in ((150, 30), (200, 15), (400, 15), (900, 3))])
    return [road, deepcopy(road), deepcopy(road)]


@pytest.mark.parametrize('variant', screen.VARIANTS)
def test_generated_material_and_other_roles_preserved(variant):
    original = specimen()
    before = deepcopy(original)
    reference = dict(ki=2000000, kr=.0004, shcrit=2, horizons=[dict(rfg=65)])
    result = screen.transform(original, reference, variant)
    assert original == before
    assert result[1:] == before[1:]
    assert result[0]['res_lyr'] == before[0]['res_lyr']
    assert result[0]['horizons'][2:] == before[0]['horizons'][2:]
    for horizon, source in zip(result[0]['horizons'], before[0]['horizons']):
        for field in ('solthk', 'sand', 'clay', 'bd'):
            assert horizon[field] == source[field]
    if variant == 'roles':
        assert result == before
    if variant.startswith('compact'):
        # Both source layers above the boundary must be treated, not only first.
        assert {h['ksat'] for h in result[0]['horizons'][:2]} == {float(variant[7:])}
        assert {h['rfg'] for h in result[0]['horizons'][:2]} == {65}


def test_missing_boundary_cannot_silently_partially_treat_profile():
    source = specimen()
    source[0]['horizons'].pop(1)
    with pytest.raises(ValueError, match='boundary'):
        screen.transform(source, {}, 'roles')
