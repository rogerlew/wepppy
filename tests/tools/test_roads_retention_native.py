"""Failed scientific trials retain evidence without invoking the model again."""
import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ART = Path(__file__).resolve().parents[2] / 'docs/work-packages/20261029_roads_parameterization_program/artifacts'


@pytest.fixture
def helper(monkeypatch):
    monkeypatch.syspath_prepend(str(ART))
    spec = importlib.util.spec_from_file_location('roads_retention_native', ART / 'run_r7_retention_native.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_partial_native_artifacts_survive_auditor_failure(helper, tmp_path, monkeypatch):
    root = tmp_path / 'retained'
    root.mkdir()
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    (scratch / 'input').write_text('bound input')
    task = dict(folder=str(scratch), mode='ordinary', arm='default', label='B2',
                staged_files=helper.local_inventory(scratch))
    monkeypatch.setattr(helper, 'ROOT', root)
    monkeypatch.setattr(helper, 'validate_policy', lambda *_: None)

    def fail_after_native(_):
        (scratch / 'stdout').write_text('native completed; retained partial evidence')
        raise ValueError('calendar audit failed')

    monkeypatch.setattr(helper, 'ordinary', fail_after_native)
    with pytest.raises(ValueError, match='calendar audit failed'):
        helper.execute_retained(task, None)
    destination = root / 'failures/ordinary/default/B2'
    assert helper.local_inventory(destination) == helper.local_inventory(scratch)
    receipt = json.loads((root / 'failure.json').read_text())
    assert receipt['exception_type'] == 'ValueError'
    assert receipt['files']['stdout'] == helper.seeds.sha(scratch / 'stdout')


def test_changed_staged_input_stops_before_model_and_is_retained(helper, tmp_path, monkeypatch):
    root = tmp_path / 'retained'
    root.mkdir()
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    (scratch / 'input').write_text('declared')
    task = dict(folder=str(scratch), mode='ordinary', arm='default', label='B3',
                staged_files=helper.local_inventory(scratch))
    (scratch / 'input').write_text('changed')
    monkeypatch.setattr(helper, 'ROOT', root)
    monkeypatch.setattr(helper, 'ordinary', lambda *_: pytest.fail('Model must not run'))
    with pytest.raises(AssertionError):
        helper.execute_retained(task, None)
    assert (root / 'failures/ordinary/default/B3/input').read_text() == 'changed'
    assert (root / 'failure.json').is_file()
