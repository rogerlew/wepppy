"""Scientific gates keep hard failures and small-load strata visible."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

pytestmark = pytest.mark.unit
PATH = Path(__file__).resolve().parents[2]/'docs/work-packages/20261029_roads_parameterization_program/artifacts/score_screen.py'
SPEC = importlib.util.spec_from_file_location('roads_parameterization_score', PATH)
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)


def panel(n=100):
    return [dict(case=dict(climate='a', soil='a', design='a', surface='a', traffic='a'),
        status='completed', within=True, meaningful=True, negative_fluxes=[],
        report_reconciled=True, ebe_mismatch_events=0) for _ in range(n)]


def test_native_failure_vetoes_otherwise_passing_numerical_gate():
    rows = panel()
    rows[0].update(status='native_failure', within=False)
    result = s.score(rows)
    assert result['numerical_gate']
    assert not result['physical_gate'] and not result['screen_gate']
    assert result['meaningful_load']['cases'] == 100
    assert result['meaningful_load']['passing'] == 99


def test_populated_small_load_group_cannot_hide_in_overall_rate():
    rows = panel()
    rows[0].update(meaningful=False, within=False)
    result = s.score(rows)
    assert result['overall']['fraction'] == .99
    assert not result['numerical_gate']


@pytest.mark.parametrize('change', [dict(negative_fluxes=[{'sediment_kg_m': -1}]),
                                    dict(report_reconciled=False), dict(ebe_mismatch_events=1)])
def test_physical_failures_cannot_be_accepted_by_good_fit(change):
    rows = panel()
    rows[0].update(change)
    assert s.score(rows)['numerical_gate']
    assert not s.score(rows)['screen_gate']


def test_minor_group_failure_vetoes_overall_success():
    rows = panel()
    rows[0]['case'] = deepcopy(rows[0]['case'])
    rows[0]['case']['soil'] = 'minority'
    rows[0]['within'] = False
    assert not s.score(rows)['numerical_gate']


def test_screen_success_is_not_model_acceptance():
    result = s.score(panel())
    assert result['screen_gate']
    assert not result['acceptance']
