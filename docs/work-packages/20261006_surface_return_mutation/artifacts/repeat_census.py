#!/usr/bin/env python3
"""Isolated fixed-build census; no live run or canonical source writes."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
import datetime as dt
import difflib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

import numpy as np
import pandas as pd

from wepppy.wepp.peakflow_census.common import sha256_file, atomic_write_json
from wepppy.wepp.peakflow_census.mutations import apply_mutation, expected_mutation
from wepppy.wepp.peakflow_census.planning import trial_plan_from_dict

SITE = Path('/wc1/runs/ha/hand-to-mouth-drought')
SOURCES = {'burned': SITE / 'wepp/runs',
           'undisturbed': SITE / '_pups/omni/scenarios/undisturbed/wepp/runs'}
BUILD = Path('/workdir/wepp-forest-holdouts/20261006-surface-return.6SeF9A/candidate/src')
FIXED_SHA = '440fcebbeb2c51c2da46e258a53dce7ad609b783551ee2f5a6b1e18b368b2307'
SHARED = ('wepp_ui.txt', 'pmetpara.txt', 'snow.txt', 'gwcoeff.txt', 'chan.inp', 'chntyp.txt', 'tc.txt')
KEYS = ['year', 'day', 'ofe']


def freeze(root: Path, original: Path) -> None:
    root.mkdir(exist_ok=False, parents=True)
    assert sha256_file(BUILD / 'wepp_hill') == FIXED_SHA
    old = trial_plan_from_dict(json.loads(original.read_text()))
    records, manifests, ids = [], {}, {}
    for scenario, source in SOURCES.items():
        target = root / 'snapshot' / scenario / 'runs'
        target.mkdir(parents=True)
        ids[scenario] = sorted(int(p.stem[1:]) for p in source.glob('p[0-9]*.run'))
        names = [f'p{h}.{ext}' for h in ids[scenario] for ext in ('run', 'man', 'slp', 'cli', 'sol')]
        names += [name for name in SHARED if (source / name).exists()]
        before = {name: sha256_file(source / name) for name in names}
        for name in names:
            shutil.copy2(source / name, target / name)
        assert before == {name: sha256_file(target / name) for name in names}
        assert before == {name: sha256_file(source / name) for name in names}
        manifests[scenario] = {'source': str(source), 'sha256': before}
        assert (target / 'wepp_ui.txt').exists(), 'hourly context absent'
        for h in ids[scenario]:
            assert (target / f'p{h}.run').read_text().splitlines()[-2:] == ['45', '0']
        for t in old.trials:
            if t.scenario != scenario:
                continue
            p = target / t.relative_input
            e = expected_mutation(p, t.family, t.direction, t.requested_change)
            assert e['source_value'] == t.source_value, f'original mutation values changed: {t.trial_id}'
            records.append(replace(t, input_sha256=sha256_file(p)).as_dict())
    assert ids['burned'] == ids['undisturbed'] == list(range(1, 141))
    for h in ids['burned']:
        for ext in ('cli', 'slp'):
            name = f'p{h}.{ext}'
            assert manifests['burned']['sha256'][name] == manifests['undisturbed']['sha256'][name]
    atomic_write_json(root / 'inputs.json', manifests, overwrite=False)
    atomic_write_json(root / 'plan.json', {'original_plan_sha256': sha256_file(original),
        'fixed_binary_sha256': FIXED_SHA, 'trials': records, 'hillslopes': ids,
        'created_utc': dt.datetime.now(dt.timezone.utc).isoformat()}, overwrite=False)
    print(json.dumps({'root': str(root), 'requested': len(records),
                      'eligible': sum(t['eligibility'] == 'eligible' for t in records)}), flush=True)


def build_observer(root: Path) -> None:
    dest = root / 'observer-src'
    shutil.copytree(BUILD, dest)
    source = dest / 'irs.for'
    before = source.read_text()
    marker = '      return\n      end\n'
    assert before.count(marker) == 1
    addition = '''c     Offline census observation after final peak/duration bookkeeping.
      call census_output(year,sdate,nplane,runoff(1),peakro(1),
     1 surdra)
'''
    routine = '''
      subroutine census_output(yr,dy,n,r,p,s)
      integer yr,dy,n,j,lu
      real r(n),p(n),s(n)
      open(newunit=lu,file='census.csv',status='unknown',
     1 position='append',form='formatted')
      do j=1,n
        write(lu,1000) yr,dy,j,r(j),p(j),s(j)
      enddo
      close(lu)
 1000 format(i6,',',i4,',',i4,3(',',es24.16))
      return
      end
'''
    after = before.replace(marker, addition + marker) + routine
    assert all(len(line) <= 72 for line in (addition + routine).splitlines())
    source.write_text(after)
    (root / 'observer.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile='fixed/irs.for', tofile='observer/irs.for')))
    with (root / 'build.log').open('w') as log:
        subprocess.run(['make', '-j6', 'wepp_hill'], cwd=dest, stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=300)
    atomic_write_json(root / 'build.json', {'fixed_binary': str(BUILD / 'wepp_hill'),
        'fixed_sha256': FIXED_SHA, 'observer_binary': str(dest / 'wepp_hill'),
        'observer_sha256': sha256_file(dest / 'wepp_hill'),
        'patch_sha256': sha256_file(root / 'observer.patch'),
        'source_irs_sha256': sha256_file(BUILD / 'irs.for')}, overwrite=False)


def stage(root: Path, scenario: str, hill: int, target: Path) -> dict:
    source = root / 'snapshot' / scenario / 'runs'
    target.mkdir(parents=True, exist_ok=False)
    names = [f'p{hill}.{ext}' for ext in ('run', 'man', 'slp', 'cli', 'sol')]
    names += [name for name in SHARED if (source / name).exists()]
    for name in names:
        shutil.copy2(source / name, target / name)
    hashes = {name: sha256_file(target / name) for name in names}
    assert hashes == {name: sha256_file(source / name) for name in names}
    return hashes


def run_case(root: Path, scenario: str, hill: int, trial=None, lane='observer') -> dict:
    label = 'baseline' if trial is None else f'{trial.family}-{trial.direction}'
    parent = root / 'executions' / lane / scenario / f'h{hill}' / label
    runs = parent / 'runs'
    executable = BUILD / 'wepp_hill' if lane == 'fixed-parity' else root / 'observer-src/wepp_hill'
    if (parent / 'terminal.json').exists():
        prior = json.loads((parent / 'terminal.json').read_text())
        assert prior['success'] and prior['binary_sha256'] == sha256_file(executable)
        assert prior['inputs_after'] == {n: sha256_file(runs / n) for n in prior['inputs_after']}
        assert prior['outputs'] == {n: sha256_file(parent / 'output' / n) for n in prior['outputs']}
        if lane == 'observer':
            assert prior['trace_sha256'] == sha256_file(runs / 'census.csv')
        return prior
    before = stage(root, scenario, hill, runs)
    mutation = None if trial is None else apply_mutation(trial, runs).as_dict()
    after = {name: sha256_file(runs / name) for name in before}
    changed = [name for name in before if before[name] != after[name]]
    assert changed == ([] if trial is None else [trial.relative_input])
    output = parent / 'output'
    output.mkdir()
    executable = BUILD / 'wepp_hill' if lane == 'fixed-parity' else root / 'observer-src/wepp_hill'
    start = time.monotonic()
    with (runs / f'p{hill}.run').open('rb') as inp, (parent / 'stdout.log').open('wb') as out, (parent / 'stderr.log').open('wb') as err:
        proc = subprocess.run([str(executable)], cwd=runs, stdin=inp, stdout=out,
                              stderr=err, timeout=300, check=False)
    stdout = (parent / 'stdout.log').read_text()
    success = proc.returncode == 0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in stdout
    terminal = {'scenario': scenario, 'hill': hill, 'label': label, 'lane': lane,
        'success': success, 'returncode': proc.returncode, 'runtime_s': time.monotonic() - start,
        'binary_sha256': sha256_file(executable), 'mutation': mutation, 'changed_inputs': changed,
        'inputs_before': before, 'inputs_after': after,
        'outputs': {p.name: sha256_file(p) for p in output.iterdir() if p.is_file()}}
    if lane == 'observer' and success:
        frame = read_trace(parent)
        terminal['trace_sha256'] = sha256_file(runs / 'census.csv')
        terminal['trace_rows'] = len(frame)
        terminal['trace_years'] = [int(frame.year.min()), int(frame.year.max())]
        assert terminal['trace_years'] == [1980, 2024]
    atomic_write_json(parent / 'terminal.json', terminal, overwrite=False)
    assert success, f'failed {parent}'
    return terminal


def read_trace(parent: Path) -> pd.DataFrame:
    f = pd.read_csv(parent / 'runs/census.csv', header=None,
        names=KEYS + ['runoff_post_m', 'peak_m_s', 'surdra_realized_m'])
    assert not f.duplicated(KEYS).any()
    assert np.isfinite(f.to_numpy()).all()
    assert (f[['runoff_post_m', 'peak_m_s', 'surdra_realized_m']] >= 0).all().all()
    assert f.ofe.eq(1).all(), 'this campaign is single OFE only'
    return f


def parity(root: Path) -> None:
    build = json.loads((root / 'build.json').read_text())
    assert sha256_file(root / 'observer-src/wepp_hill') == build['observer_sha256']
    records = []
    for scenario in SOURCES:
        a = run_case(root, scenario, 106, lane='fixed-parity')
        b = run_case(root, scenario, 106)
        assert a['outputs'] == b['outputs'], f'canonical observer parity failed {scenario}'
        validate_report(root / 'executions/observer' / scenario / 'h106/baseline', 106)
        records.append({'scenario': scenario, 'hill': 106, 'canonical_files': len(a['outputs']),
                        'byte_identical': True, 'sha256': a['outputs']})
    atomic_write_json(root / 'parity.json', records, overwrite=False)


def execute(root: Path, workers: int) -> None:
    from wepppy.wepp.peakflow_census.planning import PlannedTrial
    assert all(r['byte_identical'] for r in json.loads((root / 'parity.json').read_text()))
    build = json.loads((root / 'build.json').read_text())
    assert sha256_file(root / 'observer-src/wepp_hill') == build['observer_sha256']
    plan = json.loads((root / 'plan.json').read_text())
    tasks = [(s, h, None) for s, hs in plan['hillslopes'].items() for h in hs if h != 106]
    tasks += [(t['scenario'], t['hillslope_id'], PlannedTrial(**t)) for t in plan['trials'] if t['eligibility'] == 'eligible']
    results, failures = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(run_case, root, *task): (task[0], task[1], 'baseline' if task[2] is None else task[2].trial_id) for task in tasks}
        for future in as_completed(jobs):
            try:
                result = future.result()
            except (OSError, ValueError, AssertionError, subprocess.SubprocessError) as exc:
                failures.append({'task': jobs[future], 'type': type(exc).__name__, 'error': str(exc)})
            else:
                results.append(result)
            atomic_write_json(root / 'progress.json', {'expected': len(tasks), 'complete': len(results), 'failures': failures})
            if (len(results) + len(failures)) % 25 == 0:
                print(f'complete={len(results)} failed={len(failures)} expected={len(tasks)}', flush=True)
    atomic_write_json(root / 'execution-summary.json', {'expected': len(tasks), 'complete': len(results), 'failures': failures})
    assert not failures


def read_sediment(parent: Path, hill: int) -> pd.DataFrame:
    f = pd.read_csv(parent / f'output/H{hill}.ebe.dat', sep=r'\s+', skiprows=3,
                    header=None)
    assert f.shape[1] == 14 and np.isfinite(f.to_numpy()).all()
    dates = pd.to_datetime({'year': f[2].astype(int) + 1979, 'month': f[1], 'day': f[0]})
    result = pd.DataFrame({'year': dates.dt.year, 'day': dates.dt.dayofyear,
                          'ofe': 1, 'sediment_kg_m': f[12]})
    assert not result.duplicated(KEYS).any()
    return result


def validate_report(parent: Path, hill: int) -> dict:
    trace = read_trace(parent)
    ef = pd.read_csv(parent / f'output/H{hill}.element.dat', sep=r'\s+', skiprows=2, header=None)
    dates = pd.to_datetime({'year': ef[3].astype(int) + 1979, 'month': ef[2], 'day': ef[1]})
    reported = pd.DataFrame({'year': dates.dt.year, 'day': dates.dt.dayofyear,
        'ofe': ef[0], 'runoff_mm': ef[5], 'peak_mm_h': ef[7]})
    aligned = trace.merge(reported, on=KEYS, validate='one_to_one')
    assert len(aligned) > 0
    dq = float((aligned.runoff_post_m * 1000 - aligned.runoff_mm).abs().max())
    dp = float((aligned.peak_m_s * 3.6e6 - aligned.peak_mm_h).abs().max())
    assert dq < .0006 and dp < .0006, (str(parent), dq, dp)
    positive = reported.loc[reported.runoff_mm.gt(0) | reported.peak_mm_h.gt(0)]
    assert len(positive.merge(trace, on=KEYS)) == len(positive)
    return {'matched_report_rows': len(aligned), 'max_runoff_rounding_mm': dq,
            'max_peak_rounding_mm_h': dp}


def aggregate(root: Path) -> None:
    plan = json.loads((root / 'plan.json').read_text())
    cache, pairs, sedpairs, checks = {}, [], [], []
    eligible = [t for t in plan['trials'] if t['eligibility'] == 'eligible']
    terminals = list((root / 'executions/observer').glob('*/*/*/terminal.json'))
    assert len(terminals) == len(eligible) + sum(len(hs) for hs in plan['hillslopes'].values())
    build = json.loads((root / 'build.json').read_text())
    for path in terminals:
        terminal = json.loads(path.read_text())
        assert terminal['success'] and terminal['binary_sha256'] == build['observer_sha256']
        assert terminal['trace_sha256'] == sha256_file(path.parent / 'runs/census.csv')
    for trial in eligible:
        s, h = trial['scenario'], trial['hillslope_id']
        directory = root / 'executions/observer' / s / f'h{h}'
        if (s, h) not in cache:
            cache[s, h] = (read_trace(directory / 'baseline'), read_sediment(directory / 'baseline', h))
            checks.append({'scenario': s, 'hill': h, 'label': 'baseline',
                           **validate_report(directory / 'baseline', h)})
        baseline, bs = cache[s, h]
        parent = directory / f"{trial['family']}-{trial['direction']}"
        terminal = json.loads((parent / 'terminal.json').read_text())
        assert terminal['success']
        realized, expected = terminal['mutation']['realized_value'], trial['expected_value']
        if isinstance(expected, dict):
            np.testing.assert_allclose([realized[k] for k in expected], list(expected.values()), rtol=1e-10, atol=0)
        else:
            np.testing.assert_allclose(realized, expected, rtol=1e-10, atol=0)
        mutant = read_trace(parent)
        ms = read_sediment(parent, h)
        # Model events: positive routed runoff OR positive peak at IRS exit.
        # Keep raw full IRS observations separately; absence is never zero-filled.
        b = baseline.loc[baseline.runoff_post_m.gt(0) | baseline.peak_m_s.gt(0)].copy()
        m = mutant.loc[mutant.runoff_post_m.gt(0) | mutant.peak_m_s.gt(0)].copy()
        b['baseline_event_present'] = True
        m['mutant_event_present'] = True
        paired = b.merge(m, on=KEYS, how='outer', suffixes=('_baseline', '_mutant'), validate='one_to_one')
        for col in ('baseline_event_present', 'mutant_event_present'):
            paired[col] = paired[col].eq(True)
        sp = bs.merge(ms, on=KEYS, how='outer', suffixes=('_baseline', '_mutant'), validate='one_to_one')
        for f in (paired, sp):
            for key in ('scenario', 'family', 'direction', 'hillslope_id', 'trial_id'):
                f[key] = trial[key]
        pairs.append(paired)
        sedpairs.append(sp)
        # End-to-end report readback confirms observation scale and final peak.
        checks.append({'trial_id': trial['trial_id'], **validate_report(parent, h)})
    combined, sediment = pd.concat(pairs, ignore_index=True), pd.concat(sedpairs, ignore_index=True)
    combined.to_parquet(root / 'event-pairs.parquet', index=False, compression='zstd')
    sediment.to_parquet(root / 'sediment-pairs.parquet', index=False, compression='zstd')
    atomic_write_json(root / 'report-readback.json', checks, overwrite=False)
    atomic_write_json(root / 'aggregation.json', {'eligible': len(eligible), 'baselines': len(cache),
        'event_pair_rows': len(combined), 'paired_rows': int((combined.baseline_event_present & combined.mutant_event_present).sum()),
        'baseline_only': int((combined.baseline_event_present & ~combined.mutant_event_present).sum()),
        'mutant_only': int((~combined.baseline_event_present & combined.mutant_event_present).sum()),
        'sediment_outer_rows': len(sediment),
        'event_ledger_sha256': sha256_file(root / 'event-pairs.parquet'),
        'sediment_ledger_sha256': sha256_file(root / 'sediment-pairs.parquet')}, overwrite=False)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['freeze', 'build', 'parity', 'execute', 'aggregate'])
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--original-plan', type=Path)
    p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    assert 1 <= a.workers <= 8
    if a.command == 'freeze':
        freeze(a.root, a.original_plan)
    else:
        {'build': build_observer, 'parity': parity, 'execute': lambda r: execute(r, a.workers), 'aggregate': aggregate}[a.command](a.root)


if __name__ == '__main__':
    main()
