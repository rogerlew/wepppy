#!/usr/bin/env python3
"""Archive candidate hillslope checks without replacing released reports."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
from wepppyo3 import wepp_interchange as native

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE/'artifacts/hillslope-studies'
MUTATION = Path('/wc1/holdouts/chrqin-mutation-20261010')
RELEASE = Path('/wc1/holdouts/wepp-261009-mutation-20261009')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def matrix():
    out = OUT/'disturbed'
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2('/tmp/chrqin-ranking-contracts.log', out/'contract-tests.log')
    spec = importlib.util.spec_from_file_location('matrix_analysis', REPO/'tests/disturbed/analyze_matrix.py')
    analysis = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = analysis
    spec.loader.exec_module(analysis)
    roots = {lane: Path(f'/wc1/holdouts/chrqin-disturbed-{lane}-20261010/disturbed_matrix0')
             for lane in ('candidate', 'release')}
    identities = {}
    save(out/'builds.json', {
        'candidate': sha(Path('/wc1/holdouts/chrqin-normalization-candidate-20261009-v2/wepp_hill')),
        'release': sha(REPO/'wepp_runner/bin/wepp_261009_hill'),
        'execution_runtime': 'Both matrices use the same weppcloud container via wctl',
        'analysis_runtime': 'Host .venv native parser; identical parser for both lanes',
        'harness': {str(p.relative_to(REPO)): sha(p) for p in (
            REPO/'tests/disturbed/test_disturbed_matrix.py', REPO/'tests/disturbed/conftest.py',
            REPO/'tests/disturbed/analyze_matrix.py')}})
    rows = []
    for lane, root in roots.items():
        log = Path(f'/tmp/chrqin-disturbed-{lane}.log')
        assert '99 passed' in log.read_text(), log
        shutil.copy2(log, out/f'{lane}-pytest.log')
        identities[lane] = {folder: {p.name: sha(p) for p in sorted((root/folder).iterdir()) if p.is_file()}
                            for folder in ('runs', 'output')}
        for wid in range(1, 97):
            p = pd.DataFrame(native.hillslope_pass_to_columns(
                str(root/'output'/f'H{wid}.pass.dat'), version_major=1, version_minor=0))
            e = pd.DataFrame(native.hillslope_ebe_to_columns(
                str(root/'output'/f'H{wid}.ebe.dat'), start_year=2000, version_major=1, version_minor=0))
            assert len(p) == 36525 and set(p.year) == set(range(2000, 2100))
            for frame in (p, e):
                assert np.isfinite(frame.select_dtypes(include='number')).all().all()
                assert not frame.duplicated(['year', 'julian']).any()
            event = p.loc[p.event.eq('EVENT')]
            texture, severity, vegetation = analysis.wepp_id_to_params(wid)
            rows.append(dict(lane=lane, id=wid, texture=texture, vegetation=vegetation,
                             severity=severity, runoff_mm=float(e.Runoff.sum()),
                             sediment_kg_m=float(e['Sed.Del'].sum()),
                             pass_sediment_kg=float((event[[f'sedcon_{i}' for i in range(1, 6)]].sum(axis=1)*event.runvol).sum()),
                             peak_m3_s=float(event.peakro.max()) if len(event) else 0.,
                             events=len(event)))
        events = analysis.load_all_events(root/'output')
        peaks = analysis.load_all_peak_events(root/'output')
        analysis.require_full_matrix(events, peaks)
        context = (f'# {lane.title()} Disturbed Ranking Validation\n\n'
                   '2026-10-10. Fresh 96-case, 100-year container run with adopted defaults,\n'
                   'including young forest and low-severity forest RRINIT 6 cm.\n'
                   'Candidate is unreleased CHRQIN normalization; reference is wepp_261009.\n'
                   'Hillslope sensitivity only, not channel validation or promotion approval.\n')
        (out/f'{lane}-rankings.md').write_text(analysis.generate_full_report(
            analysis.analyze_all_comparisons(events, peaks), context=context))
    save(out/'identities.json', identities)
    changes = {}
    for folder in ('runs', 'output'):
        a, b = identities['candidate'][folder], identities['release'][folder]
        changes[folder] = dict(candidate_files=len(a), release_files=len(b),
                               candidate_only=sorted(a.keys()-b.keys()), release_only=sorted(b.keys()-a.keys()),
                               changed=[n for n in a.keys() & b.keys() if a[n] != b[n]])
    frame = pd.DataFrame(rows)
    frame.to_csv(out/'cases.csv', index=False)
    ranks = []
    for (lane, texture, vegetation), group in frame.groupby(['lane', 'texture', 'vegetation']):
        group = group.sort_values('severity')
        for metric in ('runoff_mm', 'pass_sediment_kg', 'peak_m3_s'):
            values = group[metric].to_numpy()
            ranks.append(dict(lane=lane, texture=texture, vegetation=vegetation, metric=metric,
                              unburned=values[0], low=values[1], moderate=values[2], high=values[3],
                              nondecreasing=bool((np.diff(values) >= 0).all())))
    rankings = pd.DataFrame(ranks)
    rankings.to_csv(out/'rankings.csv', index=False)
    counts = rankings.groupby(['lane', 'metric']).nondecreasing.sum()
    save(out/'summary.json', dict(cases_per_build=96, file_comparison=changes,
                                  ordered_combinations={f'{lane}:{metric}': int(value)
                                                        for (lane, metric), value in counts.items()}))
    print((out/'summary.json').read_text(), flush=True)


def mutation():
    out = OUT/'mutation'
    out.mkdir(parents=True, exist_ok=False)
    summary = json.loads((MUTATION/'audit-summary.json').read_text())
    assert summary['complete_model_cases'] == 1368 and summary['failed_cases'] == 0
    source, observed = MUTATION/'candidate-src', MUTATION/'observer-src'
    changed = [p.name for p in source.glob('*.for') if sha(p) != sha(observed/p.name)]
    assert changed == ['irs.for'], changed
    reversed_source = subprocess.check_output(
        ['patch', '--reverse', '--silent', '--output=-', str(observed/'irs.for'),
         str(MUTATION/'observer.patch')])
    assert reversed_source == (source/'irs.for').read_bytes()
    save(out/'observer-source-audit.json', dict(changed_fortran_files=changed,
        reverse_patch_restores_candidate=True, candidate_irs_sha256=sha(source/'irs.for'),
        observer_irs_sha256=sha(observed/'irs.for')))
    checks = {}
    for name in ('event-pairs.parquet', 'sediment-pairs.parquet'):
        a, b = pd.read_parquet(MUTATION/name), pd.read_parquet(RELEASE/name)
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        checks[name] = dict(rows=len(a), exact_numeric_parity=True,
                            candidate_sha256=sha(MUTATION/name), release_sha256=sha(RELEASE/name))
    receipts = []
    changed = []
    for path in sorted((MUTATION/'executions').glob('*/*/*/*/terminal.json')):
        rel = path.relative_to(MUTATION)
        current, previous = json.loads(path.read_text()), json.loads((RELEASE/rel).read_text())
        assert current['success'] and current['returncode'] == 0
        assert current['inputs_after'] == previous['inputs_after']
        for name, digest in current['outputs'].items():
            assert sha(path.parent/'output'/name) == digest
        if current['outputs'] != previous['outputs']:
            changed.append(str(rel))
        receipts.append(dict(relative_case=str(rel), **current))
    assert len(receipts) == 1378
    save(out/'receipts.json', receipts)
    save(out/'release-comparison.json', dict(ledgers=checks, runs_compared=len(receipts),
                                             changed_standard_outputs=changed))
    names = ['inputs.json', 'plan.json', 'preparation.json', 'build.json', 'parity.json',
             'mutation-parity.json', 'execution-summary.json', 'aggregation.json',
             'terminal-inventory.csv', 'all-report-readback.json', 'audit-summary.json',
             'tail-context.json', 'largest-peak-sensitivities.csv', 'analysis-manifest.json',
             'build.log', 'observer.patch']
    for name in names:
        shutil.copy2(MUTATION/name, out/name)
    shutil.copytree(MUTATION/'figures', out/'figures')
    shutil.copy2('/tmp/chrqin-mutation-execute.log', out/'execution.log')
    for name in ('repeat_census.py', 'plot_figures.py'):
        shutil.copy2(MUTATION/'mutation_support'/name, out/name)
    shutil.copy2('/tmp/chrqin-mutation-harness-tests.log', out/'harness-tests.log')
    print(json.dumps(checks, indent=2), flush=True)


def matrix_inputs():
    roots = [Path(f'/wc1/holdouts/chrqin-disturbed-{lane}-20261010/disturbed_matrix0/runs')
             for lane in ('candidate', 'release')]
    records = []
    for path in sorted(roots[0].iterdir()):
        if path.suffix == '.err' or not path.is_file():
            continue
        a, b = path.read_text(), (roots[1]/path.name).read_text()
        same = a == b
        if not same:
            assert path.suffix == '.sol'
            # Only the generated build-date comment is permitted to differ.
            clean = lambda text: [line for line in text.splitlines()
                                  if not line.startswith('#   Build Date: ')]
            assert clean(a) == clean(b), path
        records.append(dict(name=path.name, byte_identical=same,
                            only_generated_build_date_differs=not same))
    save(OUT/'disturbed/input-audit.json', dict(
        physical_inputs_equal=True, files_checked=len(records),
        generated_soil_timestamp_differences=sum(not r['byte_identical'] for r in records),
        err_files='Execution logs, not physical inputs; include differing run paths and binary identities',
        records=records))


def manifest():
    save(OUT/'manifest.json', {str(p.relative_to(OUT)): dict(sha256=sha(p), bytes=p.stat().st_size)
                              for p in sorted(OUT.rglob('*')) if p.is_file() and p != OUT/'manifest.json'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['matrix', 'matrix-inputs', 'mutation', 'manifest'])
    args = parser.parse_args()
    {'matrix': matrix, 'matrix-inputs': matrix_inputs,
     'mutation': mutation, 'manifest': manifest}[args.command]()
