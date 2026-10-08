#!/usr/bin/env python3
"""Fresh, isolated three-case replay using retained, tested runner primitives."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = Path('/workdir/wepppy')
ROOT = Path('/workdir/warming-combined-release-20261007')
SOURCE = Path('/workdir/warming-rrinit-20261006/snapshot')
CASES = [('legacy10', 'wepp_260803', .10),
         ('combined10', 'wepp_261007', .10),
         ('legacy17', 'wepp_260803', .17)]
HASHES = {
    'wepp_260803': '4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5',
    'wepp_260803_hill': '86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7',
    'wepp_261007': 'ad5ef3e31be7e6da2517567fb211fe350cb7ff0ea9320282368182cb6157127b',
    'wepp_261007_hill': 'cba2927f489a324774180164f1b8065118fb3a1fa6b64737710b46b0f96036df'}


def main():
    from wepppy.wepp.management import read_management
    helper = REPO/'docs/work-packages/20261006_warming_rrinit_legacy/artifacts/run_experiment.py'
    spec = importlib.util.spec_from_file_location('runner', helper)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.test()
    assert {n:m.sha(REPO/'wepp_runner/bin'/n) for n in HASHES} == HASHES
    ROOT.mkdir(exist_ok=False)
    (ROOT/'binaries').mkdir()
    for name in HASHES:
        for suffix in ('', '.json'):
            shutil.copy2(REPO/'wepp_runner/bin'/(name+suffix), ROOT/'binaries'/(name+suffix))
        assert m.sha(ROOT/'binaries'/name) == HASHES[name]
        assert json.loads((ROOT/'binaries'/(name+'.json')).read_text())['sha256'] == HASHES[name]
    before = m.manifest(SOURCE)
    m.save(ROOT/'source-manifest.json', before)
    shutil.copy2(helper, ROOT/'runner-primitives.py')
    m.save(ROOT/'binaries.json', HASHES)
    m.save(ROOT/'design.json', dict(cases=CASES, baseline='legacy10',
        provisional_screen=dict(abs_yield_bias_pct=.1, NSE=.999, KGE=.999, R2=.999),
        gwstorage=0, bfcoeff=.04, dscoeff=0, period=['1980-01-01','2003-12-31']))
    for lane, binary, roughness in CASES:
        case = ROOT/lane
        shutil.copytree(SOURCE, case/'runs')
        (case/'output').mkdir()
        inventory = {}; changes = []
        mans = sorted(p for p in (case/'runs').glob('p*.man') if p.stem[1:].isdigit())
        assert len(mans) == 864
        for path in mans:
            old = path.read_text()
            original = [v for _,_,v in m.positions(old)]
            expected = [roughness if v == .1 else v for v in original]
            new = m.mutate(old, roughness)
            if new != old:
                path.write_text(new)
                changes.append(path.name)
            actual = [i.data.rrinit for i in read_management(str(path)).inis]
            assert actual == expected, path
            for value in actual:
                inventory[str(value)] = inventory.get(str(value), 0) + 1
        assert inventory == {str(roughness):1885, '0.06':2, '0.008':17}, inventory
        chan = case/'runs/chan.inp'
        original = chan.read_text()
        assert original.split() == ['1','600','0','1','1235']
        chan.write_text(re.sub(r'^1', '3', original, count=1))
        consumed = m.manifest(case/'runs')
        assert set(before) == set(consumed)
        assert {n for n in before if before[n] != consumed[n]} == set(changes)|{'chan.inp'}
        oldlane = 'rr17' if roughness == .17 else 'rr10'
        reference = json.loads((Path('/workdir/warming-rrinit-legacy-20261006')/oldlane/'inputs.json').read_text())
        assert consumed == reference['sha256']
        m.save(case/'inputs.json', dict(sha256=consumed, inventory=inventory, mutated_management=changes))
    assert m.manifest(ROOT/'legacy10/runs') == m.manifest(ROOT/'combined10/runs')
    summaries = []
    for lane, binary, roughness in CASES:
        case = ROOT/lane
        files = sorted((case/'runs').glob('p[0-9]*.run'))
        assert len(files) == 864
        results = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(m.execute, ROOT/'binaries'/(binary+'_hill'), p, case/'logs'/p.stem) for p in files]
            for f in as_completed(futures):
                results.append(f.result())
                if len(results) % 20 == 0:
                    progress = dict(lane=lane, completed=len(results), failed=sum(not r['success'] for r in results))
                    m.save(ROOT/'progress.json', progress)
                    print(progress, flush=True)
        m.save(case/'hillslopes.json', results)
        assert len(results) == 864 and all(r['success'] for r in results)
        watershed = m.execute(ROOT/'binaries'/binary, case/'runs/pw0.run', case/'logs/pw0')
        m.save(case/'watershed.json', watershed)
        assert watershed['success'], watershed
        for name in ('chan.out','chanwb.out'):
            shutil.move(case/'runs'/name, case/'output'/name)
        m.save(case/'outputs.json', m.manifest(case/'output'))
        summaries.append(dict(lane=lane, hillslopes=len(results), watershed=watershed))
        print('COMPLETED', lane, flush=True)
    control = ROOT/'output-mode-control'
    shutil.copytree(SOURCE, control/'runs')
    (control/'output').mkdir()
    for path in (ROOT/'combined10/output').glob('H*.pass.dat'):
        shutil.copy2(path, control/'output'/path.name)
    result = m.execute(ROOT/'binaries/wepp_261007', control/'runs/pw0.run', control/'logs/pw0')
    assert result['success'], result
    for name in ('chan.out','chanwb.out'):
        shutil.move(control/'runs'/name, control/'output'/name)
    base = json.loads((ROOT/'combined10/outputs.json').read_text())
    parity = {n:base[n] == h for n,h in m.manifest(control/'output').items()
              if n != 'chan.out' and not n.startswith('H')}
    m.save(ROOT/'output-mode-parity.json', dict(terminal=result, canonical_files=parity))
    assert len(parity) >= 7 and all(parity.values()), parity
    assert m.manifest(SOURCE) == before
    assert {n:m.sha(ROOT/'binaries'/n) for n in HASHES} == HASHES
    m.save(ROOT/'execution-summary.json', dict(cases=summaries, source_unchanged=True, observer_parity=True))
    print('ALL EXECUTIONS COMPLETE', flush=True)


if __name__ == '__main__':
    main()
