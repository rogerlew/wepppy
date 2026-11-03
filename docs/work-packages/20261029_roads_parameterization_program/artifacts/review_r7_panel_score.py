"""Independent arithmetic and artifact readback of the completed frozen r7 panel.

This does not import the scorer, execute WEPP, or regenerate native interchange.
Seven source IDs are verified to remain seven distinct emitted material families.
"""
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import hashlib
import json
import math
import statistics

import combined_hydraulics_r4 as common

ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/panel840-v1')
ART = Path(__file__).resolve().parent
KEYS = ('climate', 'soil', 'design', 'surface', 'traffic', 'variant', 'runtime')
AXES = ('climate', 'design', 'surface', 'traffic', 'soil', 'restriction')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def key(row):
    return tuple(row['case'][name] for name in KEYS)


def passed(value, reference):
    return (.1 <= value / reference <= 10) if reference > 1 else value <= max(1, 10 * reference)


def check_fraction(actual, expected):
    assert actual == expected or math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-14)


def check_group(saved, rows):
    assert saved['cases'] == len(rows) and saved['passing'] == sum(row['pass'] for row in rows)
    check_fraction(saved['raw_fraction'], sum(row['pass'] for row in rows) / len(rows))
    materials = defaultdict(list)
    for row in rows:
        materials[row['soil']].append(row)
    assert saved['materials'] == len(materials)
    check_fraction(saved['equal_material_fraction'], statistics.mean(
        sum(row['pass'] for row in group) / len(group) for group in materials.values()))
    if 'bias' not in saved:
        return
    bias = saved['bias']
    positive = [row for row in rows if row['reference'] > 0 and row['value'] > 0]
    logs = [math.log10(row['value'] / row['reference']) for row in positive]
    assert bias['positive_ratio_cases'] == len(positive)
    assert bias['zero_reference_cases'] == sum(row['reference'] == 0 for row in rows)
    assert bias['zero_export_cases'] == sum(row['value'] == 0 for row in rows)
    assert bias['positive_reference_zero_export_cases'] == sum(row['reference'] > 0 and row['value'] == 0 for row in rows)
    assert bias['unavailable_exports'] == 0
    assert bias['below_reference'] == sum(row['reference'] > 0 and row['value'] < row['reference'] for row in rows)
    assert bias['above_reference'] == sum(row['reference'] > 0 and row['value'] > row['reference'] for row in rows)
    if not logs:
        assert bias['mean_log10_positive_only'] is bias['median_log10_positive_only'] is bias['equal_material_mean_log10_positive_only'] is None
        return
    check_fraction(bias['mean_log10_positive_only'], statistics.mean(logs))
    check_fraction(bias['median_log10_positive_only'], statistics.median(logs))
    means = [statistics.mean(math.log10(row['value'] / row['reference']) for row in group
                            if row['reference'] > 0 and row['value'] > 0)
             for group in materials.values() if any(row['reference'] > 0 and row['value'] > 0 for row in group)]
    check_fraction(bias['equal_material_mean_log10_positive_only'], statistics.mean(means))


def check_partition(saved_groups, rows, axes):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[axis] for axis in axes)].append(row)
    assert len(saved_groups) == len(groups)
    assert {tuple(group['group'][axis] for axis in axes) for group in saved_groups} == set(groups)
    for saved in saved_groups:
        check_group(saved, groups[tuple(saved['group'][axis] for axis in axes)])
    return len(groups)


def main():
    files = {name: sha(ROOT / name) for name in ('declaration.json', 'summary.json', 'results.json',
        'score.json', 'execution-review.json', 'execution-review-verified.json')}
    score, rows, declaration = (read(ROOT / name) for name in ('score.json', 'results.json', 'declaration.json'))
    review = read(ROOT / 'execution-review.json')
    verified = read(ROOT / 'execution-review-verified.json')
    assert verified['review_receipt_sha256'] == files['execution-review.json']
    assert review['panel_declaration_sha256'] == files['declaration.json']
    assert review['implementation_review_pass'] and review['scientific_review_pass']
    assert all(sha(Path(path)) == digest for path, digest in review['files'].items())
    assert sha(ROOT / 'bin/r7') == declaration['binary_sha256']
    provenance_paths = dict(declaration_sha256=ROOT / 'declaration.json', results_sha256=ROOT / 'results.json',
        baseline_sha256=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/param-sign-u12-combined/roads-results.json'),
        restriction_provenance_sha256=ART / 'restriction-provenance-v1.json', scorer_sha256=ART / 'score_r7_panel.py',
        acceptance_sha256=ART.parent / 'acceptance.md', execution_review_sha256=ROOT / 'execution-review.json',
        execution_review_verified_sha256=ROOT / 'execution-review-verified.json')
    assert score['provenance'] == {name: sha(path) for name, path in provenance_paths.items()}
    baseline = {key(row): row for row in read(provenance_paths['baseline_sha256'])}
    tasks = {key(row): row for row in declaration['tasks']}
    scored = {key(row): row for row in score['cases']}
    assert len(rows) == len(tasks) == len(scored) == len(baseline) == 840
    assert {key(row) for row in rows} == tasks.keys() == scored.keys() == baseline.keys()
    metadata = {row['mukey']: row['category'] for row in read(ART / 'restriction-provenance-v1.json')['materials']}
    families = defaultdict(dict)
    normalized, references = [], {}
    changed_outputs = unchanged_exports = 0
    for row in rows:
        identifier = key(row)
        task, old, saved = tasks[identifier], baseline[identifier], scored[identifier]
        assert row['completed'] and row['returncode'] == 0
        assert row['binary_sha256'] == declaration['binary_sha256']
        assert row['inputs'] == task['inputs'] == old['inputs']
        assert row['soil_readback'] == task['soil_readback'] == old['soil_readback']
        folder = Path(row['folder'])
        assert str(folder) == task['folder']
        for section, directory in (('inputs', 'runs'), ('auxiliary_inputs', 'runs'), ('execution_logs', 'runs'), ('outputs', 'output')):
            for name, digest in row[section].items():
                assert sha(folder / directory / name) == digest
        assert len(row['outputs']) == 7
        assert common.c.b.parse_loss(folder / 'output/H1.loss.dat', row['width_m']) == row['metrics']
        record_path = folder / 'record.json'
        record = read(record_path)
        assert all(record[name] == row[name] for name in ('case', 'metrics', 'inputs', 'outputs', 'binary_sha256'))
        for name, field in (('particle-audit.json', 'particle_pass'), ('pass-completeness.json', 'pass_completeness')):
            certificate = read(folder / name)
            assert certificate['record_sha256'] == sha(record_path) and certificate['passed'] == row[field]
            assert certificate['pass_sha256'] == row['outputs']['H1.pass.dat']
            assert certificate['element_sha256'] == row['outputs']['H1.element.dat']
        reference_path = Path(task['reference_record'])
        if str(reference_path) not in references:
            assert sha(reference_path) == task['reference_record_sha256']
            reference_record = read(reference_path)
            for name, digest in reference_record['outputs'].items():
                assert sha(reference_path.parent / 'output' / name) == digest
            references[str(reference_path)] = reference_record['metrics']['sediment_export_kg_yr']
        reference = references[str(reference_path)]
        value, prior = row['metrics']['sediment_export_kg_yr'], old['metrics']['sediment_export_kg_yr']
        assert reference == row['reference_kg_yr'] == saved['reference_kg_yr']
        assert value == saved['export_kg_yr'] and prior == saved['previous_export_kg_yr']
        assert saved['within'] == passed(value, reference) and saved['previous_within'] == passed(prior, reference)
        assert saved['delta_r4_kg_yr'] == value - prior
        assert saved['delta_reference_kg_yr'] == value - reference
        assert saved['valid'] == all(row[name] for name in ('completed', 'physical_pass', 'particle_pass', 'pass_completeness'))
        normalized.append(dict(**row['case'], restriction=metadata[row['case']['soil']],
            value=value, reference=reference, **{'pass': passed(value, reference)}))
        context = tuple(row['case'][name] for name in KEYS if name != 'soil')
        families[row['case']['soil']][context] = json.dumps([{k: v for k, v in ofe.items() if k != 'slid'}
                                                          for ofe in row['soil_readback']], sort_keys=True)
        assert set(row['changed_outputs']) == {name for name, digest in row['outputs'].items() if digest != row['prior_outputs'][name]}
        changed_outputs += len(row['changed_outputs'])
        unchanged_exports += value == prior
    assert len({json.dumps(sorted(contexts.items())) for contexts in families.values()}) == 7
    group_count = 0
    for name, population in score['load_strata'].items():
        selected = [row for row in normalized if (row['reference'] > 1) == (name == 'meaningful')]
        check_group(dict(**population['overall'], bias=population['bias']), selected)
        for axis in AXES:
            group_count += check_partition(population['major_strata'][axis], selected, (axis,))
        intersections = population['intersections_report_only']
        assert {tuple(item['axes']) for item in intersections} == {
            axes for length in range(2, 7) for axes in combinations(AXES, length)}
        for item in intersections:
            group_count += check_partition(item['groups'], selected, tuple(item['axes']))
    assert not score['magnitude_recoveries'] and not score['magnitude_regressions']
    assert not any(score[name] for name in ('raw_numerical_gate', 'equal_material_numerical_gate', 'physical_gate',
                                          'fixed_input_development_gate', 'final_scientific_acceptance'))
    assert files == {name: sha(ROOT / name) for name in files}
    result = dict(score_readback_pass=True, scientific_acceptance=False, artifact_sha256=files,
        reader_sha256=sha(Path(__file__)), cases=840, unique_references=len(references),
        strata_and_intersection_groups_checked=group_count, loss_reports_reparsed=840,
        native_output_hashes_checked=5880, changed_outputs=changed_outputs, unchanged_annual_exports=unchanged_exports,
        magnitude_recoveries=0, magnitude_regressions=0,
        load_strata={name: population['overall'] for name, population in score['load_strata'].items()},
        physical_failures=score['physical_failures'], scope='Artifact and independent scoring arithmetic; no native execution or renewed physical closure audit')
    with (ART / 'resumption-r7-panel-score-qa.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
