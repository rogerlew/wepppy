#!/usr/bin/env python3
"""Canonical Disturbed matrix: assess low forest RRINIT 4 versus 6 cm."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

import run_sensitivity as study

ROOT = Path('/wc1/holdouts/rrinit-low-forest-4v6-20261009')
FORESTS = {'forest', 'deciduous forest', 'mixed forest', 'young forest'}


def prepare():
    m = study.matrix
    assert study.sha(study.BINARY) == study.SHA
    assert m.WEPP_BINARY == 'wepp_261009'
    ROOT.mkdir(parents=True, exist_ok=False)
    shutil.copy2(study.BINARY, ROOT/'wepp_hill')
    for name in ('run_sensitivity.py', 'low_forest_trial.py'):
        shutil.copy2(study.HERE/name, ROOT/name)
    soil_dir = study.REPO/'wepppy/wepp/soils/soilsdb/data/Forest'
    man_dir = study.REPO/'wepppy/wepp/management/data'
    lookup_path = study.REPO/'wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv'
    lookup = m.read_disturbed_land_soil_lookup(str(lookup_path))
    plan = []
    for texture in m.TEXTURES:
        for vegetation in m.VEG_TYPES:
            for severity in m.SEVERITIES:
                wid = m.generate_wepp_id(texture, severity, vegetation)
                runs = ROOT/'prepared'/f'H{wid:03d}'/'runs'
                runs.mkdir(parents=True)
                m.stage_shared_inputs(runs)
                m.prepare_slope(wid, study.MATRIX/'data/canonical_slope.slp', runs)
                m.prepare_climate(wid, study.MATRIX/'data/mckenzie_2000_2099.cli', runs)
                m.prepare_management(wid, vegetation, severity, man_dir, runs, 100)
                m.prepare_soil_9002(wid, texture, vegetation, severity, soil_dir, lookup, runs)
                m.create_run_file(wid, 100, runs)
                management = study.Management.load(None, f'p{wid}.man', str(runs), None)
                initial = management.inis[0].data.rrinit
                study.save(runs.parent/'inputs.json', study.manifest(runs))
                levels = [initial]
                if severity == 1 and vegetation in FORESTS:
                    assert initial == .04
                    levels.append(.06)
                for rr in levels:
                    plan.append(dict(case=f'steep/H{wid:03d}_rr{rr:.5f}', id=wid,
                        texture=texture, vegetation=vegetation, severity=severity,
                        profile='steep', rrinit_m=rr, reference_rrinit_m=initial,
                        reference=rr == initial))
    assert len(plan) == 112 and sum(t['reference'] for t in plan) == 96
    study.save(ROOT/'plan.json', plan)
    sources = [lookup_path, study.MATRIX/'test_disturbed_matrix.py',
               study.MATRIX/'data/canonical_slope.slp',
               study.MATRIX/'data/mckenzie_2000_2099.cli']
    sources += [man_dir/n for n in sorted(set(m.MANAGEMENT_FILES.values()))]
    sources += [soil_dir/n for n in m.CANONICAL_SOILS.values()]
    shared = study.REPO/'tests/wepp_runner/fixtures/hillslope_smoke/runs'
    sources += [shared/n for n in ('wepp_ui.txt', 'snow.txt', 'pmetpara.txt',
                                  'gwcoeff.txt', 'chan.inp', 'chntyp.txt')]
    study.save(ROOT/'identity.json', dict(binary_sha256=study.SHA,
        native_sha256=study.sha(Path(study.native.wepp_interchange_rust.__file__)),
        sources={str(p.relative_to(study.REPO)): study.sha(p) for p in sources},
        scope='Canonical profile only; low forest 4 to 6 cm; no production edits'))


def execute():
    assert study.sha(ROOT/'wepp_hill') == study.SHA
    plan = json.loads((ROOT/'plan.json').read_text())
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(study.run_case, trial) for trial in plan]
        for future in as_completed(jobs):
            results.append(future.result())
            study.save(ROOT/'progress.json', dict(expected=len(plan), complete=len(results)))
            if len(results) % 8 == 0:
                print(f'COMPLETE {len(results)}/{len(plan)}', flush=True)
    pd.DataFrame(results).sort_values(['id', 'rrinit_m']).to_csv(ROOT/'case-results.csv', index=False)
    study.save(ROOT/'execution.json', dict(expected=len(plan), complete=len(results), failures=[]))


def read_case(row):
    case = ROOT/'cases'/row['case']
    p = pd.read_parquet(case/'peaks.parquet')
    p['sediment_kg'] = p[[f'sedcon_{i}' for i in range(1, 6)]].sum(axis=1)*p.runvol
    return p, pd.read_parquet(case/'events.parquet')


def analyze():
    execution = json.loads((ROOT/'execution.json').read_text())
    assert execution['complete'] == execution['expected'] == 112 and not execution['failures']
    out = ROOT/'analysis'
    out.mkdir(exist_ok=False)
    f = pd.read_csv(ROOT/'case-results.csv')
    data = {row['case']: read_case(row) for row in f.to_dict('records')}
    f['pass_sediment_kg'] = [data[c][0].sediment_kg.sum() for c in f['case']]
    refs = f.loc[f.reference].set_index('id')
    comparisons = []
    annual = []
    events = []
    metrics = ['runoff_mm', 'pass_surface_m3', 'pass_lateral_m3', 'pass_baseflow_m3',
               'pass_drain_m3', 'sediment_kg_m', 'pass_sediment_kg',
               'interrill_kg_m2', 'mean_detachment_kg_m2', 'mean_deposition_kg_m2',
               'peak_max_m3_s', 'peak_p95_m3_s', 'return_component_m3']
    for row in f.loc[~f.reference].to_dict('records'):
        baseline = refs.loc[row['id']]
        record = {k: row[k] for k in ('id', 'texture', 'vegetation', 'case')}
        for metric in metrics:
            b, t = float(baseline[metric]), float(row[metric])
            record.update({metric+'_baseline': b, metric+'_trial': t,
                           metric+'_delta': t-b,
                           metric+'_pct': 100*(t/b-1) if b else np.nan})
        p, e = data[row['case']]
        bp, be = data[baseline['case']]
        for kind, trial, base, fields in (
            ('pass', p, bp, ['runvol', 'peakro', 'sediment_kg']),
            ('ebe', e, be, ['Runoff', 'Sed.Del'])):
            paired = trial.merge(base, on=['year', 'julian'], how='outer',
                suffixes=('_trial', '_baseline'), indicator=True, validate='one_to_one')
            record[kind+'_trial_only_dates'] = int(paired._merge.eq('left_only').sum())
            record[kind+'_baseline_only_dates'] = int(paired._merge.eq('right_only').sum())
            for field in fields:
                b = paired[field+'_baseline'].fillna(0)
                t = paired[field+'_trial'].fillna(0)
                delta = t-b
                record[kind+'_'+field+'_changed_dates'] = int(delta.ne(0).sum())
                for idx in delta.abs().nlargest(5).index:
                    event = paired.loc[idx]
                    events.append(dict(id=row['id'], texture=row['texture'], vegetation=row['vegetation'],
                        kind=kind, field=field, year=int(event.year), julian=int(event.julian),
                        presence=str(event['_merge']), baseline=float(b.loc[idx]),
                        trial=float(t.loc[idx]), delta=float(delta.loc[idx])))
        for year in range(2000, 2100):
            record_year = dict(id=row['id'], texture=row['texture'], vegetation=row['vegetation'], year=year)
            for label, peaks, ebe in [('baseline', bp, be), ('trial', p, e)]:
                py = peaks.loc[peaks.year.eq(year)]
                ey = ebe.loc[ebe.year.eq(year)]
                for metric, value in dict(surface_m3=py.runvol.sum(), sediment_kg=py.sediment_kg.sum(),
                    runoff_mm=ey.Runoff.sum(), sediment_kg_m=ey['Sed.Del'].sum(),
                    peak_m3_s=py.peakro.max() if len(py) else 0).items():
                    record_year[metric+'_'+label] = float(value)
            annual.append(record_year)
        for label, source in [('baseline', baseline), ('trial', row)]:
            record['rough_min_m_'+label] = float(source['rough_min_m'])
            record['rough_max_m_'+label] = float(source['rough_max_m'])
            record['rif_zero_days_'+label] = int(source['rif_zero_days'])
        comparisons.append(record)
    ranks = []
    proposed = f.loc[f.reference & ~f.id.isin(f.loc[~f.reference, 'id']) | ~f.reference]
    assert len(proposed) == len(refs) == 96 and not proposed.id.duplicated().any()
    for policy, frame in [('current', f.loc[f.reference]), ('low_forest_6cm', proposed)]:
        for (texture, vegetation), group in frame.groupby(['texture', 'vegetation']):
            group = group.sort_values('severity')
            assert list(group.severity) == [0, 1, 2, 3]
            for metric in ('runoff_mm', 'pass_sediment_kg', 'peak_max_m3_s'):
                values = group[metric].to_numpy()
                ranks.append(dict(policy=policy, texture=texture, vegetation=vegetation,
                    metric=metric, unburned=values[0], low=values[1], moderate=values[2], high=values[3],
                    nondecreasing=bool((np.diff(values) >= 0).all())))
    pd.DataFrame(comparisons).to_csv(out/'comparisons.csv', index=False)
    pd.DataFrame(annual).to_csv(out/'annual.csv', index=False)
    pd.DataFrame(events).to_csv(out/'largest-events.csv', index=False)
    pd.DataFrame(ranks).to_csv(out/'rankings.csv', index=False)
    f.to_csv(out/'cases.csv', index=False)
    records = {}
    for row in f.to_dict('records'):
        case = ROOT/'cases'/row['case']
        receipt = json.loads((case/'receipt.json').read_text())
        assert receipt['success'] and receipt['outputs'] == study.manifest(case/'output')
        inputs = json.loads((case/'inputs.json').read_text())
        assert inputs == study.manifest(case/'runs')
        records[row['case']] = dict(receipt=receipt, inputs=inputs)
    study.save(out/'receipts.json', records)
    print(pd.DataFrame(comparisons)[['texture', 'vegetation', 'runoff_mm_pct',
        'pass_sediment_kg_pct', 'peak_max_m3_s_pct']].to_string(index=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'execute', 'analyze'])
    args = parser.parse_args()
    study.ROOT = ROOT
    {'prepare': prepare, 'execute': execute, 'analyze': analyze}[args.command]()
