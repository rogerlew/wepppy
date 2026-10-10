#!/usr/bin/env python3
"""Reuse the frozen mutation design with the unreleased normalization candidate."""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

FOREST = Path('/home/workdir/wepp-forest-release-20261009')
HELPERS = FOREST/'docs/work-packages/20261007-channel-discharge-closure'
ROOT = Path('/wc1/holdouts/chrqin-mutation-20261010')
OLD = Path('/wc1/holdouts/wepp-261009-mutation-20261009')
BUILD = Path('/wc1/holdouts/chrqin-candidate-hill-src')
SHA = '219be50ac94a7ffa01589eb22251586caea53d5e856f7af0feaea2c12fa6433a'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


runner = module('candidate_census', HELPERS/'mutation_support/repeat_census.py')
runner.BUILD = ROOT/'candidate-src'
runner.FIXED_SHA = SHA


def prepare():
    assert runner.sha256_file(BUILD/'wepp_hill') == SHA
    ROOT.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, ROOT/'runner.py')
    shutil.copytree(OLD/'snapshot', ROOT/'snapshot')
    inputs = json.loads((OLD/'inputs.json').read_text())
    for scenario, data in inputs.items():
        assert data['sha256'] == {n: runner.sha256_file(ROOT/'snapshot'/scenario/'runs'/n)
                                 for n in data['sha256']}
    shutil.copy2(OLD/'inputs.json', ROOT/'inputs.json')
    plan = json.loads((OLD/'plan.json').read_text())
    plan.update(previous_census_plan_sha256=runner.sha256_file(OLD/'plan.json'),
                fixed_binary_sha256=SHA, candidate='Unreleased CHRQIN normalization',
                created_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    for trial in plan['trials']:
        source = ROOT/'snapshot'/trial['scenario']/'runs'/trial['relative_input']
        assert runner.sha256_file(source) == trial['input_sha256']
        expected = runner.expected_mutation(source, trial['family'], trial['direction'], trial['requested_change'])
        assert expected['source_value'] == trial['source_value']
    runner.atomic_write_json(ROOT/'plan.json', plan, overwrite=False)
    shutil.copytree(BUILD, runner.BUILD, ignore=shutil.ignore_patterns('*.o', 'wepp'))
    runner.atomic_write_json(ROOT/'preparation.json', dict(
        candidate_sha256=SHA, source=str(BUILD), frozen_input_source=str(OLD/'snapshot'),
        source_manifest={p.name: runner.sha256_file(p) for p in runner.BUILD.iterdir() if p.is_file()},
        helper_sha256=runner.sha256_file(HELPERS/'mutation_support/repeat_census.py'),
        requested=len(plan['trials']), eligible=sum(t['eligibility']=='eligible' for t in plan['trials'])), overwrite=False)
    runner.build_observer(ROOT)


def execute():
    runner.parity(ROOT)
    runner.execute(ROOT, 8)
    runner.aggregate(ROOT)
    subprocess.run([sys.executable, str(HELPERS/'mutation_support/plot_figures.py'),
                    '--root', str(ROOT), '--output', str(ROOT/'figures'),
                    '--build-label', 'CHRQIN candidate',
                    '--estimator-label', 'Hourly MIXPEAK unchanged'], check=True)
    auditor = module('candidate_audit', HELPERS/'summarize_steady_mutation.py')
    auditor.main(ROOT, runner, SHA)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'execute'])
    args = parser.parse_args()
    {'prepare': prepare, 'execute': execute}[args.command]()
