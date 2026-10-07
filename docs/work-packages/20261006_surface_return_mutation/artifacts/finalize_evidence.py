#!/usr/bin/env python3
"""Reconcile immutable model terminals independently of progress callbacks."""
import argparse
import json
from pathlib import Path
import datetime as dt

import pandas as pd

from wepppy.wepp.peakflow_census.common import sha256_file, atomic_write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args()
    r = a.root
    plan = json.loads((r / 'plan.json').read_text())
    build = json.loads((r / 'build.json').read_text())
    expected = {(s, h, 'baseline') for s, hills in plan['hillslopes'].items() for h in hills}
    expected |= {(t['scenario'], t['hillslope_id'], f"{t['family']}-{t['direction']}")
                 for t in plan['trials'] if t['eligibility'] == 'eligible'}
    records = []
    for path in sorted((r / 'executions/observer').glob('*/*/*/terminal.json')):
        t = json.loads(path.read_text())
        assert t['success'] and t['returncode'] == 0
        assert t['binary_sha256'] == build['observer_sha256']
        assert t['trace_years'] == [1980, 2024]
        assert t['trace_sha256'] == sha256_file(path.parent / 'runs/census.csv')
        records.append({'scenario': t['scenario'], 'hill': t['hill'], 'label': t['label'],
                        'runtime_s': t['runtime_s'], 'trace_rows': t['trace_rows'],
                        'terminal': str(path.relative_to(r)), 'terminal_sha256': sha256_file(path)})
    observed = {(t['scenario'], t['hill'], t['label']) for t in records}
    assert observed == expected and len(records) == len(expected) == 1368
    pd.DataFrame(records).to_csv(r / 'terminal-inventory.csv', index=False)
    checks = json.loads((r / 'report-readback.json').read_text())
    assert len(checks) == 1368
    summary = {'status': 'all_model_runs_complete_and_independently_reconciled',
        'baselines': 280, 'eligible_mutations': 1088, 'excluded_mutations': 32,
        'complete_model_runs': len(records), 'failed_model_runs': 0,
        'configured_years_per_run': 45, 'report_readback_checks': len(checks),
        'max_runoff_rounding_mm': max(t['max_runoff_rounding_mm'] for t in checks),
        'max_peak_rounding_mm_h': max(t['max_peak_rounding_mm_h'] for t in checks),
        'reconciled_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'coordinator_disposition': 'SIGINT after every model terminal and independent aggregation completed; no child model process remained. Coordinator was only draining per-completion progress-file fsync calls. progress.json is a retained incomplete acknowledgment count, not final run status.',
        'authority': 'terminal-inventory.csv plus aggregation.json and report-readback.json'}
    atomic_write_json(r / 'execution-summary.json', summary, overwrite=False)
    f = pd.read_parquet(r / 'event-pairs.parquet')
    f = f.loc[f.baseline_event_present & f.mutant_event_present & f.peak_m_s_baseline.ge(1e-7) & f.peak_m_s_mutant.gt(0)].copy()
    f['ratio'] = f.peak_m_s_mutant / f.peak_m_s_baseline
    f['surface_return'] = f.surdra_realized_m_baseline.gt(0) | f.surdra_realized_m_mutant.gt(0)
    extra = {}
    for factor in (2, 5):
        tail = f.loc[f.ratio.gt(factor) | f.ratio.lt(1/factor)]
        extra[str(factor)] = {'rows': len(tail), 'surface_return': int(tail.surface_return.sum()),
            'no_surface_return': int((~tail.surface_return).sum()),
            'baseline_peak_max_mm_h': float(tail.peak_m_s_baseline.max() * 3.6e6),
            'mutant_peak_max_mm_h': float(tail.peak_m_s_mutant.max() * 3.6e6)}
    atomic_write_json(r / 'tail-context.json', extra, overwrite=False)
    names = ['plan.json', 'inputs.json', 'input-comparison.json', 'build.json', 'observer.patch',
             'parity.json', 'aggregation.json', 'report-readback.json', 'event-pairs.parquet',
             'sediment-pairs.parquet', 'execution-summary.json', 'terminal-inventory.csv',
             'tail-context.json', 'repeat_census.py', 'repeat_census_analysis.py', 'plot_figures.py',
             'audit_inputs.py', 'test_repeat.py', 'finalize_evidence.py']
    names += [f'figures/figure-{n}.png' for n in (1, 2, 3)] + ['figures/figure-statistics.json']
    atomic_write_json(r / 'artifact-manifest.json', {'host': 'forest.tail305ec9.ts.net',
        'root': str(r), 'files': {n: {'sha256': sha256_file(r / n), 'bytes': (r / n).stat().st_size} for n in names}}, overwrite=False)
    print(json.dumps(summary, indent=2))
    print(json.dumps(extra, indent=2))


if __name__ == '__main__':
    main()
