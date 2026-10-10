#!/usr/bin/env python3
"""Isolated same-build PASS regeneration and output-only watershed replay."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

import numpy as np
import pandas as pd
from wepppyo3 import wepp_interchange as native

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LIVE = Path('/wc1/runs/sc/scrawny-relay')
ROOT = Path('/wc1/holdouts/topanga-jan1993-output-replay-20261009')
SUFFIX = {'burned':Path(''), 'undisturbed':Path('_pups/omni/scenarios/undisturbed')}
HASHES = {'wepp_261009':'e1b1c244107216ca9edf4ccbaeb8d390e98440418d87beac2d5153b98191c7cc',
          'wepp_261009_hill':'37d8deaf7a4c78e83104db4d896db3ee10b77a5f5d3f3abe5ad718390e2cc228'}
FIELDS = ['event','year','julian','dur','tcs','oalpha','runoff','runvol','sbrunv','peakro']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def inventory(path):
    return {p.name:sha(p) for p in sorted(path.iterdir()) if p.is_file()}


def lane(mode, scenario):
    return ROOT/mode/SUFFIX[scenario]/'wepp'


def prepare():
    ROOT.mkdir(parents=True, exist_ok=False)
    identities = {}
    for name, expected in HASHES.items():
        binary = REPO/'wepp_runner/bin'/name
        assert sha(binary) == expected
        shutil.copy2(binary, ROOT/name)
    shutil.copy2(__file__, ROOT/'executed_runner.py')
    for scenario,suffix in SUFFIX.items():
        source = LIVE/suffix/'wepp/runs'
        before = inventory(source)
        target = lane('control',scenario)
        shutil.copytree(source, target/'runs')
        (target/'output').mkdir()
        assert inventory(target/'runs') == before == inventory(source)
        identities[scenario] = before
        assert (target/'runs/chan.inp').read_text().split() == ['1','600','0','1','412']
        for wid in range(1,285):
            log = (source/f'p{wid}.err').read_text()
            assert HASHES['wepp_261009_hill'] in log
            assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in log
            for line in (target/'runs'/f'p{wid}.run').read_text().splitlines():
                if line.endswith(('.man','.sol','.slp','.cli')):
                    local = (target/'runs'/line).resolve()
                    assert local.is_relative_to(ROOT) and local.is_file(), local
    save(ROOT/'staged-inputs.json', identities)
    print('PREPARED both scenarios, original binaries and byte-identical run directories',flush=True)


def execute(binary, runfile, work, log, timeout):
    start = time.monotonic()
    with runfile.open('rb') as inp, log.open('wb') as out:
        result = subprocess.run([str(ROOT/binary)], cwd=work, stdin=inp, stdout=out,
                                stderr=subprocess.STDOUT, timeout=timeout)
    text = log.read_text()
    assert result.returncode == 0, (runfile, result.returncode)
    assert not any(s in text for s in ('Fortran runtime error','Program received signal','Program stop'))
    assert list(map(int,re.findall(r'SIMULATION YEAR\s*=\s*(\d+)',text))) == list(range(1,46))
    return text, time.monotonic()-start


def hills():
    receipts = []
    for scenario,suffix in SUFFIX.items():
        old = pd.read_parquet(LIVE/suffix/'wepp/output/interchange/H.pass.parquet',columns=['wepp_id']+FIELDS)
        refs = {int(wid):g[FIELDS].reset_index(drop=True) for wid,g in old.groupby('wepp_id')}
        base = lane('control',scenario)
        logs = ROOT/f'{scenario}-hillslope-logs';logs.mkdir()
        def one(wid):
            text,seconds = execute('wepp_261009_hill',base/'runs'/f'p{wid}.run',base/'runs',logs/f'H{wid}.log',300)
            assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in text
            path = base/'output'/f'H{wid}.pass.dat'
            generated = pd.DataFrame(native.hillslope_pass_to_columns(str(path),1,0))[FIELDS]
            expected = refs[wid]
            assert generated.shape == expected.shape
            assert generated['event'].equals(expected['event'])
            for col in FIELDS[1:]:
                assert np.array_equal(generated[col].to_numpy(),expected[col].to_numpy(),equal_nan=True),(scenario,wid,col)
            return dict(scenario=scenario,wepp_id=wid,seconds=seconds,pass_sha256=sha(path),rows=len(generated),parity='exact selected PASS fields')
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(one,wid) for wid in range(1,285)]
            for job in as_completed(futures):
                receipts.append(job.result())
                if len(receipts)%16==0:
                    save(ROOT/'hills-progress.json',dict(completed=len(receipts),expected=568))
                    print(f'HILLS {len(receipts)}/568',flush=True)
        del old,refs
    save(ROOT/'hills-receipts.json',receipts)


def watersheds():
    shutil.copy2(__file__, ROOT/'watershed_runner.py')
    hills = json.loads((ROOT/'hills-receipts.json').read_text())
    assert len(hills) == 568
    for scenario in SUFFIX:
        base = lane('control',scenario)
        text, seconds = execute('wepp_261009',base/'runs/pw0.run',base/'runs',ROOT/f'{scenario}-control.log',1800)
        assert 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in text
        for name in ('chan.out','chanwb.out','tc_out.txt'):
            shutil.move(str(base/'runs'/name),base/'output'/name)
        parsed = ROOT/f'{scenario}-control-ebe.parquet'
        native.watershed_ebe_to_parquet(str(base/'output/ebe_pw0.txt'),str(parsed),1,0,start_year=1980,legacy_element_id=412)
        current = pd.read_parquet(parsed)
        original = pd.read_parquet(REPO/'docs/investigations/2026-10-09-watershed-return-period-comparisons/artifacts/snapshot'/f'topanga_gridmet_261009_{scenario}.parquet')
        metrics = ['year','month','day_of_month','runoff_volume','peak_runoff','sediment_yield']
        for col in metrics:
            assert np.array_equal(current[col].to_numpy(),original[col].to_numpy(),equal_nan=True),(scenario,'control EBE',col)
        save(ROOT/f'{scenario}-control.json',dict(seconds=seconds,ebe_parity='exact',output_hashes=inventory(base/'output')))
        print(f'CONTROL {scenario} matches original EBE',flush=True)
    # Mirror the relative parent/Omni layout; share only immutable regenerated PASS files.
    for scenario in SUFFIX:
        base = lane('control',scenario);full = lane('series',scenario)
        shutil.copytree(base/'runs',full/'runs')
        (full/'output').mkdir()
        for wid in range(1,285):
            source=base/'output'/f'H{wid}.pass.dat'
            (full/'output'/source.name).symlink_to(source)
        config=full/'runs/chan.inp'
        tokens=config.read_text().splitlines();assert tokens[0].split()==['1','600']
        tokens[0]='3 600';config.write_text('\n'.join(tokens)+'\n')
        before=inventory(base/'runs');after=inventory(full/'runs')
        assert {n for n in before if before[n]!=after[n]}=={'chan.inp'}
    receipts=[]
    for scenario in SUFFIX:
        base=lane('control',scenario);full=lane('series',scenario)
        text,seconds=execute('wepp_261009',full/'runs/pw0.run',full/'runs',ROOT/f'{scenario}-series.log',1800)
        assert 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in text
        for name in ('chan.out','chanwb.out','tc_out.txt'):
            shutil.move(str(full/'runs'/name),full/'output'/name)
        a=inventory(base/'output');b=inventory(full/'output')
        comparable=sorted(set(a)&set(b)-{'chan.out'})
        differences=[n for n in comparable if a[n]!=b[n]]
        assert not differences,(scenario,'observer difference',differences)
        assert a['chan.out']!=b['chan.out']
        record=dict(scenario=scenario,seconds=seconds,compared_files=comparable,
                    observer_differences=differences,series_output_hashes=b)
        receipts.append(record)
        save(ROOT/'watershed-receipts.json',receipts)
        print(f'SERIES {scenario} observer-neutral across {len(comparable)} files',flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','hills','watersheds'])
    args=parser.parse_args()
    {'prepare':prepare,'hills':hills,'watersheds':watersheds}[args.phase]()
