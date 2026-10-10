#!/usr/bin/env python3
"""Freeze reviewed watershed evidence; recompute return periods without live writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

import numpy as np
import pandas as pd

from wepppy.all_your_base.stats import weibull_series

HERE = Path(__file__).resolve().parent
PROJECTS = {
    'ascending-mourner': ('rattlesnake_260803', 673.745301),
    'anisotropic-sassafras': ('rattlesnake_261009', 673.745301),
    'phylogenetic-folly': ('topanga_synthetic_261009', 972.029631),
    'scrawny-relay': ('topanga_gridmet_261009', 972.029631),
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def capture(out):
    out.mkdir(parents=True, exist_ok=False)
    runs = []
    for runid, (label, area) in PROJECTS.items():
        root = Path('/wc1/runs')/runid[:2]/runid
        for scenario in ('burned', 'undisturbed'):
            live = root if scenario == 'burned' else root/'_pups/omni/scenarios/undisturbed'
            key = f'{label}_{scenario}'
            source = live/'wepp/output/interchange/ebe_pw0.parquet'
            copy = out/f'{key}.parquet'
            before = digest(source)
            shutil.copy2(source, copy)
            assert before == digest(copy) == digest(source), 'Source changed during capture'
            log = live/'wepp/runs/pw0.err'
            text = log.read_text()
            assert 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in text
            binary = re.search(r'binary_path="([^"]+)" binary_sha256=([0-9a-f]{64})', text)
            assert binary is not None
            climate = json.loads((live/'climate.nodb').read_text())['py/state']
            wepp = json.loads((live/'wepp.nodb').read_text())['py/state']
            inputs = {}
            for path in sorted((live/'wepp/runs').iterdir()):
                if path.is_file() and (path.suffix in ('.man', '.sol', '.slp', '.chn', '.str') or
                    path.name in ('pw0.cli', 'wepp_ui.txt', 'pmetpara.txt', 'snow.txt', 'gwcoeff.txt')):
                    inputs[path.name] = digest(path)
            caches = []
            for path in sorted((live/'wepp/output').glob('return_periods*.json')):
                target = out/f'{key}__{path.name}'
                shutil.copy2(path, target)
                caches.append(target.name)
            record = dict(key=key, project=runid, scenario=scenario, source=str(source),
                source_sha256=before, snapshot=copy.name,
                url=f'https://wc.bearhive.duckdns.org/weppcloud/runs/{runid}/disturbed9002_wbt/',
                report_area_ha=area, configured_binary=wepp['_wepp_bin'],
                executed_binary=binary.group(1), binary_sha256=binary.group(2),
                execution_log_sha256=digest(log), execution_header=text.splitlines()[:2],
                climate={k:climate.get(k) for k in ('_input_years', '_observed_start_year',
                    '_observed_end_year', '_climate_mode')}, input_sha256=inputs, cached_reports=caches)
            if runid == 'scrawny-relay':
                channel = live/'wepp/output/interchange/chan.out.parquet'
                target = out/f'{key}_channel.parquet'
                shutil.copy2(channel, target)
                assert digest(channel) == digest(target)
                record['channel_snapshot'] = target.name
                record['channel_source_sha256'] = digest(target)
            runs.append(record)
    save(out/'provenance.json', dict(scope='Read-only capture before January 1993 diagnosis',
        report_area_definition='WEPPcloud return-period normalization area, hectares', runs=runs))
    save(out/'manifest.json', {p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()})


def analyze(source, out):
    out.mkdir(parents=True, exist_ok=False)
    hashes = json.loads((source/'manifest.json').read_text())
    assert all(digest(source/name) == sha for name,sha in hashes.items())
    records = json.loads((source/'provenance.json').read_text())['runs']
    tables, windows, checks, calendar_findings = [], [], [], []
    frames = {}
    for record in records:
        frame = pd.read_parquet(source/record['snapshot'])
        frames[record['key']] = frame
        assert np.isfinite(frame[['runoff_volume', 'peak_runoff']]).all().all()
        assert frame.element_id.nunique() == 1
        assert frame.simulation_year.nunique() == record['climate']['_input_years']
        frame['_record_order'] = np.arange(len(frame))
        duplicates = frame.loc[frame.duplicated(['year', 'month', 'day_of_month'], keep=False)]
        calendar_findings.append(dict(case=record['key'], duplicate_rows=len(duplicates),
            dates=duplicates[['year','month','day_of_month']].drop_duplicates().to_dict('records')))
        for exclude, gringorten, setting in [(False, True, 'full_record_gringorten'),
                                            (True, False, 'exclude_first_two_weibull')]:
            data = frame.loc[frame.simulation_year.gt(2)] if exclude else frame
            years = data.year.nunique()
            periods = [2, 5, 10, 20, 25, 50] if years >= 50 else [2, 5, 10, 20, 25]
            selections = weibull_series(periods, years, method='cta',
                gringorten_correction=gringorten, days_per_year=len(data)/years)
            for column, measure in [('runoff_volume', 'Runoff'), ('peak_runoff', 'Peak Discharge')]:
                ordered = data.sort_values([column, '_record_order'], ascending=[False, True]).reset_index(drop=True)
                for period, index in selections.items():
                    row = ordered.iloc[index]
                    value = float(row[column])/(record['report_area_ha']*10 if measure == 'Runoff' else 1)
                    tables.append(dict(case=record['key'], setting=setting, method='cta', years=int(years),
                        measure=measure, units='mm' if measure == 'Runoff' else 'm3/s',
                        return_years=int(period), value=value, selected_rank=index+1,
                        year=int(row.year), month=int(row.month), day=int(row.day_of_month),
                        runoff_volume_m3=float(row.runoff_volume), peak_m3s=float(row.peak_runoff)))
            for name in record['cached_reports']:
                cached = json.loads((source/name).read_text())
                if cached['method'] != 'cta' or cached['exclude_months']:
                    continue
                if bool(cached['exclude_yr_indxs']) != exclude or cached['gringorten_correction'] != gringorten:
                    continue
                assert not exclude or cached['exclude_yr_indxs'] == [0, 1]
                for row in tables:
                    if row['case'] != record['key'] or row['setting'] != setting:
                        continue
                    saved = cached['return_periods'][row['measure']].get(str(row['return_years']))
                    if saved is not None:
                        assert np.isclose(row['value'], saved[row['measure']], rtol=1e-12, atol=1e-12)
                        checks.append(dict(cache=name, measure=row['measure'], return_years=row['return_years'], matches=True))
        if record['project'] == 'scrawny-relay':
            window = frame.loc[frame.year.eq(1993)&frame.month.eq(1)&frame.day_of_month.between(16,20)].copy()
            window.insert(0, 'scenario', record['scenario'])
            windows.append(window[['scenario','year','month','day_of_month','precip','runoff_volume','peak_runoff']])
    for label,_ in PROJECTS.values():
        columns = ['year', 'month', 'day_of_month', 'precip']
        assert frames[label+'_burned'][columns].equals(frames[label+'_undisturbed'][columns])
    pd.DataFrame(tables).to_csv(out/'return-periods.csv', index=False)
    pd.concat(windows).to_csv(out/'january-1993-window.csv', index=False)
    save(out/'validation.json', dict(runs=len(records), rows=len(tables), cache_comparisons=len(checks),
        all_cache_comparisons_match=True, burned_undisturbed_precipitation_matches=True,
        source_manifest_verified=True, calendar_findings=calendar_findings,
        limitation='Original records retained without calendar deduplication; no cause adjudication or new model execution'))
    save(out/'manifest.json', {p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    print(json.dumps(json.loads((out/'validation.json').read_text()), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['capture', 'analyze'])
    parser.add_argument('--source', type=Path, default=HERE/'artifacts/snapshot')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'capture':
        capture(args.out)
    else:
        analyze(args.source, args.out)
