"""Score the frozen 840-case development replay; never execute or retune WEPP.

Raw-case and equal-material gates are reported separately. Acceptance.md requires
equal material weighting; neither view is final scientific/withheld acceptance.
Intersections are descriptive, not additional retrospectively imposed gates.
"""
from collections import Counter, defaultdict
from itertools import combinations, product
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
CASE_KEYS = ('climate', 'soil', 'design', 'surface', 'traffic', 'variant', 'runtime')
AXES = ('climate', 'design', 'surface', 'traffic', 'soil', 'restriction')
OUTPUTS = {f'H1.{name}.dat' for name in ('loss', 'soil', 'pass', 'plot', 'wat', 'element', 'ebe')}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_execution_review(root, required_files):
    """Require the executed review receipt and the exact reviewed scoring inputs.

    Receipt keys use the declared service paths; values in required_files are
    their local paths, permitting readback from either canonical workspace mount.
    """
    receipt_path = root / 'execution-review.json'
    verified_path = root / 'execution-review-verified.json'
    verified = json.loads(verified_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    receipt_hash = digest(receipt_path)
    if verified['review_receipt_sha256'] != receipt_hash:
        raise ValueError('Executed review receipt identity drift')
    if receipt['panel_declaration_sha256'] != digest(root / 'declaration.json'):
        raise ValueError('Reviewed panel declaration identity drift')
    if any(receipt[field] is not True for field in
           ('implementation_review_pass', 'scientific_review_pass')):
        raise ValueError('Execution review approval gate failed')
    for service_path, local_path in required_files.items():
        if receipt['files'].get(service_path) != digest(local_path):
            raise ValueError(f'Reviewed scoring input identity drift: {service_path}')
    return dict(execution_review_sha256=receipt_hash,
                execution_review_verified_sha256=digest(verified_path))


def identity(case):
    return tuple(str(case[key]) for key in CASE_KEYS)


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def classify(value, reference):
    if value is None:
        return 'native_failure', False
    if not math.isfinite(value) or value < 0:
        return 'invalid_export', False
    if reference <= 1:
        passed = value <= max(1, 10 * reference)
        return ('small_pass' if passed else 'small_exceedance'), passed
    ratio = value / reference
    if .1 <= ratio <= 10:
        return 'meaningful_pass', True
    return ('meaningful_low' if ratio < .1 else 'meaningful_high'), False


def rates(rows):
    materials = defaultdict(list)
    for row in rows:
        materials[row['material_signature']].append(row)
    passing = sum(row['within'] for row in rows)
    per_material = {key: sum(row['within'] for row in group) / len(group)
                    for key, group in materials.items()}
    return dict(cases=len(rows), passing=passing,
                raw_fraction=passing / len(rows) if rows else None,
                materials=len(materials),
                equal_material_fraction=statistics.mean(per_material.values()) if materials else None)


def bias(rows):
    logs = [(row['material_signature'], math.log10(row['ratio']))
            for row in rows if row['ratio'] is not None and row['ratio'] > 0]
    groups = defaultdict(list)
    for material, value in logs:
        groups[material].append(value)
    values = [value for _, value in logs]
    return dict(positive_ratio_cases=len(values),
                mean_log10_positive_only=statistics.mean(values) if values else None,
                median_log10_positive_only=statistics.median(values) if values else None,
                equal_material_mean_log10_positive_only=(statistics.mean(
                    statistics.mean(group) for group in groups.values()) if groups else None),
                zero_reference_cases=sum(row['reference_kg_yr'] == 0 for row in rows),
                zero_export_cases=sum(row['export_kg_yr'] == 0 for row in rows),
                positive_reference_zero_export_cases=sum(
                    row['reference_kg_yr'] > 0 and row['export_kg_yr'] == 0 for row in rows),
                unavailable_exports=sum(row['export_kg_yr'] is None for row in rows),
                below_reference=sum(row['ratio'] is not None and row['ratio'] < 1 for row in rows),
                above_reference=sum(row['ratio'] is not None and row['ratio'] > 1 for row in rows))


def group_report(rows, axes):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[axis] for axis in axes)].append(row)
    return [dict(group=dict(zip(axes, values)), **rates(group), bias=bias(group))
            for values, group in sorted(groups.items())]


def material_families(tasks):
    """Collapse labels only when every matched emitted soil context agrees.

    SLID is an identifying label. Preserve all other parsed model fields,
    including texture, restriction settings and role-specific conditioning.
    """
    families = defaultdict(dict)
    for task in tasks:
        context = tuple(task['case'][key] for key in CASE_KEYS if key != 'soil')
        soil = [{key: value for key, value in ofe.items() if key != 'slid'}
                for ofe in task['soil_readback']]
        families[task['case']['soil']][context] = signature(soil)
    return {soil: signature(sorted(contexts.items())) for soil, contexts in families.items()}


def validate_membership(rows, tasks, baseline):
    maps = []
    for label, records in (('results', rows), ('declaration', tasks), ('baseline', baseline)):
        mapping = {identity(row['case']): row for row in records}
        if len(records) != 840 or len(mapping) != 840:
            raise ValueError(f'{label}: expected 840 unique cases')
        maps.append(mapping)
    if not (maps[0].keys() == maps[1].keys() == maps[2].keys()):
        raise ValueError('Missing or unexpected panel case')
    axes = [sorted({key[i] for key in maps[1]}) for i in range(5)]
    if list(map(len, axes)) != [5, 7, 4, 2, 3] or set(maps[1]) != {
            (*key, 'erosion_road_cap', 'project') for key in product(*axes)}:
        raise ValueError('Panel does not match frozen development dimensions/treatment')
    return maps


def score(rows, tasks, baseline, material_metadata):
    actual, declared, previous = validate_membership(rows, tasks, baseline)
    family = material_families(tasks)
    material_ids = {task['case']['soil'] for task in tasks}
    if material_ids != set(material_metadata):
        raise ValueError('Material provenance does not match development panel')
    normalized = []
    for key, task in sorted(declared.items()):
        row, old = actual[key], previous[key]
        reference = task['reference_kg_yr']
        if not math.isfinite(reference) or reference < 0:
            raise ValueError('Invalid frozen reference')
        prior = old['metrics']['sediment_export_kg_yr']
        if task['inputs'] != old['inputs'] or task['soil_readback'] != old['soil_readback']:
            raise ValueError('Frozen input/material drift')
        if prior != task['prior_export_kg_yr'] or not math.isfinite(prior) or prior < 0:
            raise ValueError('Historical comparison drift')
        if row['inputs'] != task['inputs'] or row['reference_kg_yr'] != reference:
            raise ValueError('Candidate input/reference drift')
        complete = row.get('completed', False)
        value = row['metrics']['sediment_export_kg_yr'] if complete else None
        category, within = classify(value, reference)
        prior_category, prior_within = classify(prior, reference)
        valid_value = value is not None and math.isfinite(value) and value >= 0
        gates = {name: row.get(name, False) is True for name in
                 ('completed', 'physical_pass', 'particle_pass', 'pass_completeness')}
        normalized.append(dict(case=row['case'], case_id='|'.join(key),
            **{axis: row['case'][axis] for axis in AXES if axis != 'restriction'},
            restriction=material_metadata[row['case']['soil']]['category'],
            material_signature=family[row['case']['soil']],
            soil_signature=signature([{k: v for k, v in ofe.items() if k != 'slid'}
                                      for ofe in task['soil_readback']]),
            input_signature=signature(task['inputs']),
            reference_kg_yr=reference, meaningful=reference > 1,
            export_kg_yr=value if valid_value else None,
            invalid_export_token=repr(value) if value is not None and not valid_value else None,
            previous_export_kg_yr=prior, classification=category, within=within,
            previous_classification=prior_category, previous_within=prior_within,
            ratio=value / reference if valid_value and reference > 0 else None,
            delta_reference_kg_yr=value - reference if valid_value else None,
            delta_r4_kg_yr=value - prior if valid_value else None,
            gates=gates, valid=all(gates.values()) and valid_value))
    strata = {}
    for name, meaningful in (('meaningful', True), ('small', False)):
        selected = [row for row in normalized if row['meaningful'] == meaningful]
        major = {axis: group_report(selected, (axis,)) for axis in AXES}
        overall = rates(selected)
        gate = {}
        for metric in ('raw_fraction', 'equal_material_fraction'):
            gate[metric] = ((overall[metric] is None or overall[metric] >= .95)
                and all(group[metric] >= .9 for groups in major.values() for group in groups))
        strata[name] = dict(overall=overall, bias=bias(selected), major_strata=major,
            numerical_gates=gate, intersections_report_only=[
                dict(axes=list(axes), groups=group_report(selected, axes))
                for length in range(2, len(AXES) + 1) for axes in combinations(AXES, length)])
    aliases = {}
    for field in ('material_signature', 'soil_signature', 'input_signature'):
        grouped = defaultdict(list)
        for row in normalized:
            grouped[row[field]].append(row['case_id'])
        aliases[field] = dict(unique=len(grouped), groups=dict(sorted(grouped.items())))
    physical_failures = [row['case_id'] for row in normalized if not row['valid']]
    raw_gate = all(s['numerical_gates']['raw_fraction'] for s in strata.values())
    equal_gate = all(s['numerical_gates']['equal_material_fraction'] for s in strata.values())
    failures = [row for row in normalized if not row['within'] or not row['valid']]
    # Ratios at zero export are explicit severe underpredictions, not log epsilon.
    def severity(row):
        if not row['valid'] or row['classification'] == 'meaningful_low' and row['export_kg_yr'] == 0:
            return (2, 0, row['case_id'])
        value, ref = row['export_kg_yr'], row['reference_kg_yr']
        excess = (abs(math.log10(value / ref)) if row['meaningful']
                  else value / max(1, 10 * ref))
        return (1, excess, row['case_id'])
    return dict(cases=normalized, load_strata=strata, aliases=aliases,
        material_families_by_source_id=family,
        material_weighting='Equal emitted-soil families across matched contexts; SLID labels excluded. Raw case metrics also retained.',
        raw_numerical_gate=raw_gate, equal_material_numerical_gate=equal_gate,
        physical_gate=not physical_failures, physical_failures=physical_failures,
        fixed_input_development_gate=equal_gate and not physical_failures,
        magnitude_recoveries=[row['case_id'] for row in normalized if not row['previous_within'] and row['within']],
        magnitude_regressions=[row['case_id'] for row in normalized if row['previous_within'] and not row['within']],
        worst_cases={label: [row['case_id'] for row in sorted(
            (row for row in failures if row['meaningful'] == flag), key=severity, reverse=True)[:50]]
            for label, flag in (('meaningful', True), ('small', False))},
        worst_case_ranking='Within each load stratum: invalid executions/zero meaningful exports first, then absolute log10 ratio or small-load upper-bound exceedance factor. All failures remain in cases.',
        final_scientific_acceptance=False,
        scope='Frozen conditioned U12 development replay only; no withheld, fresh-producer, field, complete water/particle closure, default or UI acceptance')


def verify_artifacts(root, rows, tasks):
    """Do not turn stale/missing artifacts into a numeric score."""
    by_id = {identity(row['case']): row for row in rows}
    references = {}
    for task in tasks:
        row = by_id[identity(task['case'])]
        if row['folder'] != task['folder']:
            raise ValueError('Execution folder drift')
        folder = Path(row['folder'])
        reference = Path(task['reference_record'])
        if str(reference) not in references:
            if digest(reference) != task['reference_record_sha256']:
                raise ValueError('Reference record drift')
            saved_reference = json.loads(reference.read_text())
            if saved_reference['metrics']['sediment_export_kg_yr'] != task['reference_kg_yr']:
                raise ValueError('Reference quantity drift')
            for name, value in saved_reference['outputs'].items():
                if Path(name).name != name or digest(reference.parent / 'output' / name) != value:
                    raise ValueError('Reference output drift')
            references[str(reference)] = (task['reference_record_sha256'], task['reference_kg_yr'])
        if references[str(reference)] != (task['reference_record_sha256'], task['reference_kg_yr']):
            raise ValueError('Repeated reference identity/quantity drift')
        for name, value in row['execution_logs'].items():
            if Path(name).name != name or digest(folder / 'runs' / name) != value:
                raise ValueError('Execution diagnostic drift')
        for section, directory in (('inputs', 'runs'), ('auxiliary_inputs', 'runs'), ('outputs', 'output')):
            expected = task.get(section, {}) if section != 'outputs' else row['outputs']
            for name, value in expected.items():
                if Path(name).name != name or digest(folder / directory / name) != value:
                    raise ValueError(f'Artifact drift: {folder}/{name}')
        if not row.get('completed', False):
            continue
        if set(row['outputs']) != OUTPUTS:
            raise ValueError('Incomplete ordinary output set')
        saved = json.loads((folder / 'record.json').read_text())
        for field in ('case', 'inputs', 'outputs', 'metrics', 'completed', 'physical_pass', 'binary_sha256'):
            if saved[field] != row[field]:
                raise ValueError(f'Execution record drift: {field}')
        record_hash = digest(folder / 'record.json')
        for name, field in (('particle-audit.json', 'particle_pass'),
                            ('pass-completeness.json', 'pass_completeness')):
            certificate = json.loads((folder / name).read_text())
            if certificate['record_sha256'] != record_hash or certificate['passed'] != row[field]:
                raise ValueError('Audit certificate drift')
            if certificate['pass_sha256'] != row['outputs']['H1.pass.dat'] or certificate['element_sha256'] != row['outputs']['H1.element.dat']:
                raise ValueError('Audited output drift')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    acceptance = HERE.parent / 'acceptance.md'
    metadata_path = HERE / 'restriction-provenance-v1.json'
    repository = HERE.parents[3]
    reviewed_files = {str(Path('/workdir/wepppy') / path.relative_to(repository)): path
                      for path in (Path(__file__).resolve(), metadata_path, acceptance)}
    review_provenance = verify_execution_review(root, reviewed_files)
    declaration = json.loads((root / 'declaration.json').read_text())
    summary = json.loads((root / 'summary.json').read_text())
    rows = json.loads((root / 'results.json').read_text())
    baseline = json.loads(args.baseline.read_text())
    tasks = declaration['tasks']
    validate_membership(rows, tasks, baseline)
    if digest(args.baseline) != declaration['source_panel_sha256']:
        raise ValueError('Frozen baseline identity drift')
    if digest(root / 'results.json') != summary['results_sha256']:
        raise ValueError('Summary/results identity drift')
    if digest(root / 'bin/r7') != declaration['binary_sha256']:
        raise ValueError('Binary drift')
    if not summary['source_and_dependency_integrity'] or any(
            row['binary_sha256'] != declaration['binary_sha256'] for row in rows):
        raise ValueError('Execution identity/integrity gate failed')
    for field, counter in (('completed', 'native_pass'), ('physical_pass', 'physical_pass'),
                           ('particle_pass', 'particle_pass'), ('pass_completeness', 'pass_completeness')):
        if summary[counter] != sum(row.get(field, False) is True for row in rows):
            raise ValueError(f'Summary counter drift: {counter}')
    bound_acceptance = [value for name, value in declaration['dependencies'].items()
                        if Path(name).name == 'acceptance.md']
    if bound_acceptance != [digest(acceptance)]:
        raise ValueError('Frozen acceptance identity drift')
    verify_artifacts(root, rows, tasks)
    metadata = {row['mukey']: row for row in json.loads(metadata_path.read_text())['materials']}
    report = score(rows, tasks, baseline, metadata)
    report['provenance'] = dict(declaration_sha256=digest(root / 'declaration.json'),
        results_sha256=digest(root / 'results.json'), baseline_sha256=digest(args.baseline),
        restriction_provenance_sha256=digest(metadata_path), scorer_sha256=digest(__file__),
        acceptance_sha256=digest(acceptance), **review_provenance)
    # Exclusive creation preserves every prior score and candidate checkpoint.
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('raw_numerical_gate',
        'equal_material_numerical_gate', 'physical_gate', 'final_scientific_acceptance')}))


if __name__ == '__main__':
    main()
