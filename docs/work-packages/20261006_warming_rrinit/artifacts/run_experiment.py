#!/usr/bin/env python3
"""Bounded offline rrinit experiment; never writes to the original run."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

SOURCE = Path('/wc1/runs/wa/warming-championship/wepp/runs')
ROOT = Path('/workdir/warming-rrinit-20261006')
BIN = Path('/workdir/wepp-forest-holdouts/20261006-surface-return.6SeF9A/candidate/src')
HASHES = {'wepp': '49a3e6cf199fa68388b76736caa82937e487ee894aaac46a1032845fa407a32c',
          'wepp_hill': '440fcebbeb2c51c2da46e258a53dce7ad609b783551ee2f5a6b1e18b368b2307'}


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def manifest(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def positions(text):
    start = text.index('# Initial Condition Section')
    end = text.index('#  Surface Effects Section', start)
    # Cropland-format initial roughness records have exactly five real tokens.
    found = []
    lines = list(re.finditer(r'[^\n]+', text[start:end]))
    for index, line in enumerate(lines):
        tokens = list(re.finditer(r'\S+', line.group()))
        if len(tokens) != 5:
            continue
        try:
            vals = [float(t.group()) for t in tokens]
        except ValueError:
            continue
        # The management code (1/2/3) immediately precedes roughness. The other
        # five-real record is snow/tillage and follows the rtyp code; distinguish
        # it by requiring the previous two records to both be integer codes.
        if index < 2 or not all(re.fullmatch(r'\s*\d+\s*(?:#.*)?', lines[j].group())
                                for j in (index-1, index-2)):
            continue
        a = start + line.start() + tokens[3].start()
        b = start + line.start() + tokens[3].end()
        found.append((a, b, vals[3]))
    return found


def mutate(text, value):
    result = text
    for a, b, old in reversed(positions(text)):
        if old == 0.1 and value != 0.1:
            result = result[:a] + f'{value:.5f}' + result[b:]
    return result


def test():
    text = '# Initial Condition Section\n1\n2\n400 0.1 1 0.10000 0\n1\n0 0 0 0 0\n1\n2\n400 0.06 1 0.06000 0\n1\n2\n400 0.008 1 0.00800 0\n#  Surface Effects Section\n'
    assert [v for _, _, v in positions(mutate(text, .17))] == [.17, .06, .008]
    assert mutate(text, .1) == text
    assert mutate(text, .6).replace('0.60000', '0.10000') == text
    assert len(positions(text.replace('\n1\n2\n', '\n5\n2\n'))) == 3
    print('Token mutation tests passed', flush=True)


def execute(binary, runfile, logs):
    logs.mkdir(parents=True, exist_ok=False)
    start = time.time()
    with runfile.open('rb') as inp, (logs/'stdout').open('wb') as out, (logs/'stderr').open('wb') as err:
        try:
            rc = subprocess.run([str(binary)], cwd=runfile.parent, stdin=inp,
                                stdout=out, stderr=err, timeout=14400).returncode
        except subprocess.TimeoutExpired:
            rc = 'timeout'
    result = dict(run=runfile.name, returncode=rc, seconds=time.time()-start,
                  success=rc == 0 and 'SIMULATION SUCCESSFULLY' in (logs/'stdout').read_text(errors='replace'))
    save(logs/'terminal.json', result)
    return result


def stage():
    from wepppy.wepp.management import read_management
    assert {n: sha(BIN/n) for n in HASHES} == HASHES
    ROOT.mkdir(exist_ok=False)
    before = manifest(SOURCE)
    shutil.copytree(SOURCE, ROOT/'snapshot')
    assert manifest(SOURCE) == before == manifest(ROOT/'snapshot')
    save(ROOT/'source-manifest.json', before)
    save(ROOT/'binaries.json', {'root': str(BIN), 'sha256': HASHES})
    mans = sorted(p for p in (ROOT/'snapshot').glob('p*.man') if p.stem[1:].isdigit())
    assert len(mans) == 864
    inventory = Counter()
    for p in mans:
        raw = [v for _, _, v in positions(p.read_text())]
        parsed = [i.data.rrinit for i in read_management(str(p)).inis]
        assert raw == parsed, (p.name, raw, parsed)
        inventory.update(raw)
    assert inventory == Counter({.1:1885, .06:2, .008:17}), inventory
    save(ROOT/'inventory.json', dict(inventory))
    print('Source inventory verified', dict(inventory), flush=True)
    for lane, value in [('rr10', .1), ('rr17', .17), ('rr60', .6)]:
        case = ROOT/lane
        shutil.copytree(ROOT/'snapshot', case/'runs')
        (case/'output').mkdir()
        mutations = []
        for p in mans:
            dest = case/'runs'/p.name
            old = p.read_text()
            new = mutate(old, value)
            if new != old:
                dest.write_text(new)
            expected = [value if v == .1 else v for _, _, v in positions(old)]
            actual = [i.data.rrinit for i in read_management(str(dest)).inis]
            assert actual == expected, (dest, actual, expected)
            mutations.append(dict(file=p.name, before=[v for _, _, v in positions(old)], after=actual))
        chan = case/'runs/chan.inp'
        original = chan.read_text()
        assert original.split() == ['1','600','0','1','1235']
        chan.write_text(re.sub(r'^1', '3', original, count=1))
        after = manifest(case/'runs')
        changed = [n for n in before if before[n] != after[n]]
        allowed = {x['file'] for x in mutations if x['before'] != x['after']} | {'chan.inp'}
        assert set(changed) == allowed
        save(case/'inputs.json', {'sha256':after, 'changed_files': changed, 'rrinit':mutations})
        print('Staged and readback verified', lane, len(changed), flush=True)
    assert manifest(SOURCE) == before


def run():
    summaries = []
    for lane in ('rr10', 'rr17', 'rr60'):
        case = ROOT/lane
        files = sorted(p for p in (case/'runs').glob('p*.run') if p.stem[1:].isdigit())
        results = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(execute, BIN/'wepp_hill', p, case/'logs'/p.stem) for p in files]
            for f in as_completed(futures):
                result = f.result()
                results.append(result)
                print(lane, len(results), result, flush=True)
                if len(results) % 20 == 0:
                    save(ROOT/'progress.json', {'lane':lane, 'hillslopes_complete':len(results), 'failed':sum(not r['success'] for r in results)})
        save(case/'hillslopes.json', results)
        assert len(results) == 864 and all(r['success'] for r in results)
        watershed = execute(BIN/'wepp', case/'runs/pw0.run', case/'logs/pw0')
        save(case/'watershed.json', watershed)
        assert watershed['success'], watershed
        for name in ('chan.out', 'chanwb.out'):
            shutil.move(case/'runs'/name, case/'output'/name)
        outputs = manifest(case/'output')
        save(case/'outputs.json', outputs)
        summaries.append(dict(lane=lane, hillslope_count=len(results), watershed=watershed))
        print('Completed', lane, flush=True)
    # Output-only control: reuse verified baseline passes in an isolated replay.
    control = ROOT/'output-mode-control'
    shutil.copytree(ROOT/'snapshot', control/'runs')
    (control/'output').mkdir()
    for p in (ROOT/'rr10/output').glob('H*.pass.dat'):
        shutil.copy2(p, control/'output'/p.name)
    result = execute(BIN/'wepp', control/'runs/pw0.run', control/'logs/pw0')
    assert result['success'], result
    for name in ('chan.out', 'chanwb.out'):
        shutil.move(control/'runs'/name, control/'output'/name)
    bm = json.loads((ROOT/'rr10/outputs.json').read_text())
    cm = manifest(control/'output')
    checked = {n: bm[n] == h for n,h in cm.items() if n not in ('chan.out',) and not n.startswith('H')}
    save(ROOT/'output-mode-parity.json', {'terminal': result, 'canonical_files': checked})
    assert checked and all(checked.values()), checked
    assert manifest(SOURCE) == json.loads((ROOT/'source-manifest.json').read_text())
    save(ROOT/'execution-summary.json', {'cases':summaries, 'source_unchanged':True, 'output_mode_parity':True})
    print('ALL EXECUTIONS AND PARITY COMPLETE', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    a = parser.parse_args()
    test()
    if not a.test:
        stage()
        run()
