"""Run retained cases through the installed native writer and actual EDDE adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import time

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1] / '20261013_edde_v2_feasibility' / 'artifacts'
sys.path.insert(0, str(STUDY))
import workflows
from wepppy.climates.edde.cligen import read_cli, revise_prism
from wepppy.climates.edde.client import sha256, write_json
from wepppyo3.climate import cli_revision
import wepppyo3.climate.cli_revision_rust as native


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['baseline', 'patched'])
    args = parser.parse_args()
    state_file = HERE / 'writer-validation.json'
    if args.phase == 'baseline':
        root = Path(tempfile.mkdtemp(prefix='prism-writers-'))
        archives = json.loads((STUDY / 'evidence-index.json').read_text())['archives']
        entry = next(a for a in archives if a['path'] == 'generated-climates.tar.gz')
        source = STUDY / entry['path']
        if sha256(source) != entry['sha256']: raise ValueError('Source archive changed')
        with tarfile.open(source) as archive: archive.extractall(root, filter='data')
        fixture = workflows.OLD / 'fixtures.tar.gz'
        if sha256(fixture) != json.loads((workflows.OLD / 'fixtures-archive.json').read_text())['sha256']:
            raise ValueError('Fixture archive changed')
        with tarfile.open(fixture) as archive: archive.extractall(root, filter='data')
        state = dict(root=str(root), baseline_binary_sha256=sha256(Path(native.__file__)), cases=[])
    else:
        state = json.loads(state_file.read_text()); root = Path(state['root'])
        state['patched_cases'] = []
        state['patched_binary_sha256'] = sha256(Path(native.__file__))
        if state['patched_binary_sha256'] == state['baseline_binary_sha256']:
            raise ValueError('Stale native extension')
        state.update(uid=os.getuid(), gid=os.getgid(), groups=os.getgroups(), native_path=native.__file__)
    workflows.FIXTURES = root / 'fixtures'
    sites = json.loads((workflows.OLD / 'manifest.json').read_text())['sites']
    executions = []; timings = []
    for manifest in sorted((root / 'workflows-full').glob('*/*/*/climate/manifest.json')):
        if json.loads(manifest.read_text())['status'] != 'complete': continue
        source = manifest.parent / 'wepp.cli'
        model, scenario, group = manifest.relative_to(root / 'workflows-full').parts[:3]
        reference = workflows.normal({'apostolic-saw':'apostolic-saw-h122','cryptic-beechnut':'cryptic-beechnut-h78'}[group])
        for site in (s for s in sites if s['slug'] == group):
            target = workflows.normal(site['site'])
            directory = root / args.phase / model / scenario / site['site']
            directory.mkdir(parents=True, exist_ok=False)
            path = directory / 'native.cli'
            started = time.perf_counter()
            cli_revision(str(source), str(path), reference['ppt'], reference['tmax'], reference['tmin'],
                         target['ppt'], target['tmax'], target['tmin'])
            timings.append(time.perf_counter() - started)
            identity = dict(model=model, scenario=scenario, site=site['site'])
            if args.phase == 'baseline':
                state['cases'].append(dict(**identity, sha256=sha256(path)))
                continue
            baseline = root / 'baseline' / model / scenario / site['site'] / 'native.cli'
            expected_hash = next(c['sha256'] for c in state['cases'] if all(c[k] == v for k,v in identity.items()))
            if sha256(baseline) != expected_hash: raise ValueError('Baseline changed')
            old, current = read_cli(baseline), read_cli(path)
            bad = old.tmin > old.tmax
            if not (current.tmin <= current.tmax).all(): raise ValueError('Native inversion survived')
            pd.testing.assert_frame_equal(old.loc[~bad], current.loc[~bad])
            pd.testing.assert_frame_equal(old.drop(columns=['tmax','tmin']), current.drop(columns=['tmax','tmin']))
            edde_path = directory / 'edde.cli'
            result = revise_prism(source, edde_path, reference, target)
            edde = read_cli(edde_path)
            np.testing.assert_allclose(current[['tmax','tmin']], edde[['tmax','tmin']], atol=.100001, rtol=0)
            previous = manifest.parent / (site['site'] + '-prism.cli')
            if previous.exists(): pd.testing.assert_frame_equal(edde, read_cli(previous))
            record = dict(**identity, source_sha256=sha256(source), native_sha256=sha256(path),
                          native_corrected_serialized_days=int(bad.sum()), edde=result,
                          maximum_calendar_month_tmax_change_c=float((current.tmax-old.tmax).resample('MS').mean().abs().max()),
                          maximum_calendar_month_tmin_change_c=float((current.tmin-old.tmin).resample('MS').mean().abs().max()))
            if result['temperature_ordering']['corrected_days']:
                for arm in ['native','edde']:
                    execution = workflows.execute(site, directory / f'{arm}.cli', directory / f'wepp-{arm}', 20)
                    executions.append(dict(**identity, arm=arm, **execution))
            state.setdefault('patched_cases', []).append(record)
    state[args.phase + '_seconds'] = timings
    if args.phase == 'patched':
        state['executions'] = executions
        state['status'] = 'complete'
        evidence = HERE / 'writer-consumer-evidence.tar.gz'
        with tarfile.open(evidence, 'w:gz') as archive:
            for directory in (root / 'patched').glob('*/*/*'):
                for path in directory.iterdir():
                    if path.is_file(): archive.add(path, arcname=str(path.relative_to(root)), recursive=False)
                for run in directory.glob('wepp-*'):
                    for path in run.rglob('*'):
                        if path.is_file(): archive.add(path, arcname=str(path.relative_to(root)), recursive=False)
        state['archive'] = dict(path=evidence.name, sha256=sha256(evidence))
    write_json(state_file, state)
    print(args.phase, 'cases', len(timings), 'WEPP executions', len(executions))


if __name__ == '__main__': main()
