"""Coupling diagnostics preserve tiny changes and reject incomplete comparisons."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest

pytestmark=pytest.mark.unit
PATH=Path(__file__).resolve().parents[2]/'docs/work-packages/20261029_roads_buffer_drainage/artifacts/reconcile.py'


@pytest.fixture
def analyzer(monkeypatch):
    # The tested pure comparison helper does not call experiment orchestration.
    # Fixture-scoped placeholder prevents collection-time module/path pollution.
    monkeypatch.setitem(__import__('sys').modules,'experiment',SimpleNamespace())
    spec=importlib.util.spec_from_file_location('buffer_coupling_diagnostics',PATH)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def test_tiny_upstream_change_is_recorded_without_tolerance(analyzer):
    reference={(1,1):{1:{'Q':1.},2:{'Q':2.}}}
    changed={(1,1):{1:{'Q':1.000001},2:{'Q':2.}}}
    result=analyzer.differences(reference,changed,('Q',))
    assert result[0]['Q']['changed_days']==1
    assert result[0]['Q']['max_abs']==pytest.approx(.000001)
    assert result[1]['Q']['changed_days']==0


def test_upstream_calendar_mismatch_rejected(analyzer):
    with pytest.raises(ValueError,match='calendar'):
        analyzer.differences({(1,1):{}},{},('Q',))
