"""Evaluate a proposed midpoint repair; no production formula is changed.

Run inside the existing development container with wctl exec -T weppcloud.
Inputs come from hash-verified committed archives; outputs use a new temp root.
"""
import json
import os
from pathlib import Path
import tarfile
import tempfile

import numpy as np
import pandas as pd

from wepppy.climates.cligen import ClimateFile
from wepppy.climates.edde.cligen import read_cli, _validate_cli
from wepppy.climates.edde.client import sha256, write_json
import workflows


def main():
    here = Path(__file__).resolve().parent
    root = Path(tempfile.mkdtemp(prefix='prism-inversion-evaluation-'))
    index = json.loads((here / 'evidence-index.json').read_text())
    record = next(a for a in index['archives'] if a['path'] == 'generated-climates.tar.gz')
    archive = here / record['path']
    if sha256(archive) != record['sha256']:
        raise ValueError('Climate evidence archive hash mismatch')
    with tarfile.open(archive) as source:
        source.extractall(root, filter='data')
    fixture = workflows.OLD / 'fixtures.tar.gz'
    expected = json.loads((workflows.OLD / 'fixtures-archive.json').read_text())['sha256']
    if sha256(fixture) != expected:
        raise ValueError('Fixture archive hash mismatch')
    with tarfile.open(fixture) as source:
        source.extractall(root, filter='data')
    workflows.FIXTURES = root / 'fixtures'
    sites = json.loads((workflows.OLD / 'manifest.json').read_text())['sites']
    groups = {'apostolic-saw': 'apostolic-saw-h122', 'cryptic-beechnut': 'cryptic-beechnut-h78'}
    rows, changed_days, executions = [], [], []
    for manifest in sorted((root / 'workflows-full').glob('*/*/*/climate/manifest.json')):
        state = json.loads(manifest.read_text())
        if state['status'] != 'complete':
            continue
        source_path = manifest.parent / 'wepp.cli'
        frame = read_cli(source_path)
        _validate_cli(frame)
        model, scenario, group = manifest.relative_to(root / 'workflows-full').parts[:3]
        reference = workflows.normal(groups[group])
        months = frame.index.month.to_numpy() - 1
        dates = [(d.year, d.month, d.day) for d in frame.index]
        for site in (s for s in sites if s['slug'] == group):
            target = workflows.normal(site['site'])
            raw_max = frame.tmax.to_numpy() + (np.array(target['tmax']) - reference['tmax'])[months]
            raw_min = frame.tmin.to_numpy() + (np.array(target['tmin']) - reference['tmin'])[months]
            prcp = frame.prcp.to_numpy() * (np.array(target['ppt']) / reference['ppt'])[months]
            bad = raw_min > raw_max
            mid = raw_max / 2 + raw_min / 2
            fixed_max, fixed_min = np.where(bad, mid, raw_max), np.where(bad, mid, raw_min)
            if np.any(fixed_min > fixed_max):
                raise ValueError('Candidate did not restore ordering')
            if not np.array_equal(fixed_max[~bad], raw_max[~bad]) or not np.array_equal(fixed_min[~bad], raw_min[~bad]):
                raise ValueError('Candidate changed valid days')
            np.testing.assert_allclose((fixed_max + fixed_min) / 2, mid, rtol=0, atol=1e-12)
            output = root / 'candidates' / model / scenario / site['site']
            output.mkdir(parents=True)
            path = output / 'midpoint.cli'
            cli = ClimateFile(str(source_path))
            for name, values in [('prcp', prcp), ('tmax', fixed_max), ('tmin', fixed_min)]:
                cli.replace_var(name, dates, values)
            cli.write(str(path))
            actual = read_cli(path)
            _validate_cli(actual)
            if not actual.index.equals(frame.index):
                raise ValueError('Date coverage changed')
            # Paired serializer control isolates correction from existing 0.1 C rounding.
            raw_path = output / 'unrepaired.cli'
            cli.replace_var('tmax', dates, raw_max)
            cli.replace_var('tmin', dates, raw_min)
            cli.write(str(raw_path))
            raw = read_cli(raw_path)
            for name in ['dur', 'tp', 'ip', 'rad', 'w-vl', 'w-dir', 'tdew']:
                np.testing.assert_array_equal(actual[name], raw[name])
            np.testing.assert_array_equal(actual.prcp, raw.prcp)
            np.testing.assert_array_equal(actual.loc[~bad], raw.loc[~bad])
            previous = manifest.parent / f'{site["site"]}-prism.cli'
            if previous.exists():
                pd.testing.assert_frame_equal(actual, read_cli(previous))
            identity = dict(model=model, scenario=scenario, site=site['site'])
            monthly = []
            for month in range(1, 13):
                selected = months == month - 1
                monthly.append(dict(month=month,
                    tmax_c=float(np.mean(fixed_max[selected] - raw_max[selected])),
                    tmin_c=float(np.mean(fixed_min[selected] - raw_min[selected])),
                    serialized_tmax_c=float((actual.tmax[selected] - raw.tmax[selected]).mean()),
                    serialized_tmin_c=float((actual.tmin[selected] - raw.tmin[selected]).mean())))
            for i in np.flatnonzero(bad):
                changed_days.append(dict(**identity, date=str(frame.index[i].date()),
                    source_tmax_c=float(frame.tmax.iloc[i]), source_tmin_c=float(frame.tmin.iloc[i]),
                    adjusted_tmax_c=float(raw_max[i]), adjusted_tmin_c=float(raw_min[i]),
                    midpoint_c=float(mid[i]), written_tmax_c=float(actual.tmax.iloc[i]),
                    written_tmin_c=float(actual.tmin.iloc[i])))
            rows.append(dict(**identity, days=len(frame), corrected_days=int(bad.sum()),
                source_sha256=sha256(source_path), output_sha256=sha256(path),
                maximum_midpoint_correction_c=float(np.max(abs(fixed_max - raw_max))),
                maximum_one_sided_or_swap_correction_c=float(np.maximum(raw_min - raw_max, 0).max()),
                maximum_written_midpoint_change_c=float(np.max(abs((actual.tmax + actual.tmin - raw.tmax - raw.tmin) / 2))),
                maximum_calendar_month_written_temperature_change_c=float(
                    (actual[['tmax', 'tmin']] - raw[['tmax', 'tmin']]).resample('MS').mean().abs().max().max()),
                monthly_corrections=monthly))
            if bad.any():
                executions.append(dict(**identity, **workflows.execute(site, path, output / 'wepp', 20)))
    # Retain exact repaired files and WEPP control/input/output evidence, not raw caches.
    evidence = here / 'prism-inversion-patch-evidence.tar.gz'
    with tarfile.open(evidence, 'w:gz') as archive:
        for path in sorted((root / 'candidates').glob('**/*')):
            if path.is_file() and (path.parent / 'wepp').exists():
                archive.add(path, arcname=str(path.relative_to(root)), recursive=False)
        for execution in sorted((root / 'candidates').glob('**/wepp')):
            for path in sorted(execution.rglob('*')):
                if path.is_file():
                    archive.add(path, arcname=str(path.relative_to(root)), recursive=False)
    pd.DataFrame(changed_days).to_csv(here / 'prism-inversion-patch-days.csv', index=False)
    write_json(here / 'prism-inversion-patch-evaluation.json', dict(
        status='complete', scope='candidate evaluation only; production writers unchanged',
        environment='development weppcloud container', uid=os.getuid(), gid=os.getgid(),
        scratch=str(root), source_archive_sha256=record['sha256'], fixture_sha256=expected,
        script_sha256=sha256(Path(__file__)), candidate='midpoint only on inverted adjusted extrema',
        records=rows, executions=executions,
        evidence=dict(path=evidence.name, sha256=sha256(evidence), bytes=evidence.stat().st_size)))
    print('Validated', len(rows), 'revisions;', len(changed_days), 'corrected days;', len(executions), 'fresh WEPP runs')


if __name__ == '__main__':
    main()
