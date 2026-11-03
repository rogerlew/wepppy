"""Frozen magnitude arithmetic and explicit failure denominators; no native runs."""
from copy import deepcopy
import importlib.util
import json
from itertools import product
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
PATH = (Path(__file__).resolve().parents[2] /
        'docs/work-packages/20261029_roads_parameterization_program/artifacts/score_r7_panel.py')


@pytest.fixture(scope='module')
def scorer():
    spec = importlib.util.spec_from_file_location('roads_r7_panel_score', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('value,reference,category,passed', [
    (1., 0., 'small_pass', True), (1.01, 0., 'small_exceedance', False),
    (10., 1., 'small_pass', True), (10.01, 1., 'small_exceedance', False),
    (.2, 2., 'meaningful_pass', True), (20., 2., 'meaningful_pass', True),
    (.199, 2., 'meaningful_low', False), (20.01, 2., 'meaningful_high', False),
    (0., 2., 'meaningful_low', False), (None, 2., 'native_failure', False),
    (float('nan'), 2., 'invalid_export', False), (-1., 0., 'invalid_export', False),
])
def test_frozen_thresholds_without_zero_epsilon(scorer, value, reference, category, passed):
    assert scorer.classify(value, reference) == (category, passed)


def test_equal_material_weight_does_not_follow_case_multiplicity(scorer):
    rows = [dict(material_signature='a', within=True)] * 9
    rows += [dict(material_signature='b', within=False)]
    result = scorer.rates(rows)
    assert result['cases'] == 10 and result['passing'] == 9
    assert result['raw_fraction'] == .9
    assert result['equal_material_fraction'] == .5


@pytest.fixture
def panel():
    tasks, rows, baseline = [], [], []
    metadata = {f's{i}': {'category': 'mineral' if i < 3 else 'no_detected'} for i in range(7)}
    for c, s, d, surface, traffic in product(range(5), range(7), range(4), range(2), range(3)):
        case = dict(climate=f'c{c}', soil=f's{s}', design=f'd{d}', surface=str(surface),
                    traffic=str(traffic), variant='erosion_road_cap', runtime='project')
        inputs = {'p1.sol': f'material{s}'}
        tasks.append(dict(case=case, inputs=inputs, reference_kg_yr=2., prior_export_kg_yr=2.,
                          soil_readback=[dict(slid=f'label{s}', ksat=s)]))
        rows.append(dict(case=case, inputs=inputs, reference_kg_yr=2.,
                         metrics={'sediment_export_kg_yr': 2.}, completed=True,
                         physical_pass=True, particle_pass=True, pass_completeness=True))
        baseline.append(dict(case=case, inputs=deepcopy(inputs),
                             soil_readback=deepcopy(tasks[-1]['soil_readback']),
                             metrics={'sediment_export_kg_yr': 2.}))
    return rows, tasks, baseline, metadata


def test_complete_panel_failure_denominators_and_zero_bias(scorer, panel):
    rows, tasks, baseline, metadata = panel
    rows[0]['completed'] = False
    rows[1]['metrics']['sediment_export_kg_yr'] = 0.
    rows[2]['physical_pass'] = False  # Numeric agreement never clears the physical veto.
    result = scorer.score(rows, tasks, baseline, metadata)
    meaningful = result['load_strata']['meaningful']
    assert meaningful['overall']['cases'] == 840
    assert meaningful['overall']['passing'] == 838
    assert meaningful['bias']['unavailable_exports'] == 1
    assert meaningful['bias']['positive_reference_zero_export_cases'] == 1
    assert meaningful['bias']['positive_ratio_cases'] == 838
    assert len(result['physical_failures']) == 2
    assert len(result['magnitude_regressions']) == 2
    assert not result['physical_gate'] and not result['fixed_input_development_gate']
    assert not result['final_scientific_acceptance']
    assert result['load_strata']['small']['overall']['cases'] == 0
    assert len(meaningful['intersections_report_only']) == 57
    assert result['equal_material_numerical_gate']  # Tiny intersection failures aren't new 90% gates.


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'unexpected'])
def test_exact_declared_membership_required(scorer, panel, mutation):
    rows, tasks, baseline, metadata = panel
    if mutation == 'missing':
        rows.pop()
    elif mutation == 'duplicate':
        rows[-1] = deepcopy(rows[0])
    else:
        rows[-1] = deepcopy(rows[-1])
        rows[-1]['case']['soil'] = 'withheld'
    with pytest.raises(ValueError):
        scorer.score(rows, tasks, baseline, metadata)


def test_material_aliases_ignore_labels_but_preserve_model_values(scorer, panel):
    _, tasks, _, _ = panel
    for task in tasks:
        if task['case']['soil'] == 's6':
            task['soil_readback'][0]['ksat'] = 5
    families = scorer.material_families(tasks)
    assert families['s5'] == families['s6']
    assert len(set(families.values())) == 6
    tasks[-1]['soil_readback'][0]['ksat'] = 9
    assert scorer.material_families(tasks)['s5'] != scorer.material_families(tasks)['s6']


@pytest.fixture
def execution_review(scorer, tmp_path):
    required = {}
    for name in ('score_r7_panel.py', 'restriction-provenance-v1.json', 'acceptance.md'):
        local_path = tmp_path / name
        local_path.write_text(f'frozen {name}\n')
        required[f'/workdir/wepppy/docs/{name}'] = local_path
    (tmp_path / 'declaration.json').write_text('{"tasks": []}\n')
    receipt = dict(panel_declaration_sha256=scorer.digest(tmp_path / 'declaration.json'),
                   implementation_review_pass=True, scientific_review_pass=True,
                   files={name: scorer.digest(path) for name, path in required.items()})
    receipt_path = tmp_path / 'execution-review.json'
    receipt_path.write_text(json.dumps(receipt))
    verified = dict(review_receipt_sha256=scorer.digest(receipt_path))
    (tmp_path / 'execution-review-verified.json').write_text(json.dumps(verified))
    return tmp_path, required


def test_executed_review_binds_service_paths_to_local_scoring_inputs(scorer, execution_review):
    root, required = execution_review
    result = scorer.verify_execution_review(root, required)
    assert result['execution_review_sha256'] == scorer.digest(root / 'execution-review.json')
    assert result['execution_review_verified_sha256'] == scorer.digest(root / 'execution-review-verified.json')


@pytest.mark.parametrize('name', [
    'execution-review.json', 'declaration.json', 'score_r7_panel.py',
    'restriction-provenance-v1.json', 'acceptance.md',
])
def test_executed_review_rejects_post_freeze_byte_drift(scorer, execution_review, name):
    root, required = execution_review
    with (root / name).open('a') as stream:
        stream.write('\n')  # Even parse-equivalent changes invalidate the reviewed bytes.
    with pytest.raises(ValueError, match='identity drift'):
        scorer.verify_execution_review(root, required)


@pytest.mark.parametrize('mutation', ['missing_verification', 'missing_binding', 'wrong_path', 'unapproved'])
def test_executed_review_cannot_skip_required_boundary(scorer, execution_review, mutation):
    root, required = execution_review
    receipt_path = root / 'execution-review.json'
    verified_path = root / 'execution-review-verified.json'
    receipt = json.loads(receipt_path.read_text())
    if mutation == 'missing_verification':
        verified_path.unlink()
        with pytest.raises(FileNotFoundError):
            scorer.verify_execution_review(root, required)
        return
    if mutation in ('missing_binding', 'wrong_path'):
        key = next(iter(required))
        value = receipt['files'].pop(key)
        if mutation == 'wrong_path':
            receipt['files'][f'/other/{Path(key).name}'] = value
    else:
        receipt['scientific_review_pass'] = False
    receipt_path.write_text(json.dumps(receipt))
    verified_path.write_text(json.dumps(dict(review_receipt_sha256=scorer.digest(receipt_path))))
    with pytest.raises(ValueError):
        scorer.verify_execution_review(root, required)
