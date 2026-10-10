#!/usr/bin/env python3
"""Fresh paired Cedar runs; preserve the frozen 10 cm RRINIT experiment."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from wepppyo3 import wepp_interchange as native

HERE = Path(__file__).resolve().parent
FOREST = Path('/home/workdir/wepp-forest-release-20261009')
HELPERS = FOREST/'docs/work-packages/20261007-channel-discharge-closure'
ROOT = Path('/wc1/holdouts/chrqin-cedar-20261010')
SOURCE = Path('/workdir/warming-rrinit-20261006/snapshot')
CANDIDATE = Path('/wc1/holdouts/chrqin-normalization-candidate-20261009-v2')
spec = importlib.util.spec_from_file_location('cedar_runner', HELPERS/'run_factorial.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
BINARIES = {
    'candidate': {'wepp': (CANDIDATE/'wepp', '0eb062812786064b230091ac0144f7502bc225964ea982dd76ebfc68abc6b76d'),
                  'wepp_hill': (CANDIDATE/'wepp_hill', '219be50ac94a7ffa01589eb22251586caea53d5e856f7af0feaea2c12fa6433a')},
    'release': {'wepp': (FOREST/'release/wepp_261009', 'e1b1c244107216ca9edf4ccbaeb8d390e98440418d87beac2d5153b98191c7cc'),
                'wepp_hill': (FOREST/'release/wepp_261009_hill', '37d8deaf7a4c78e83104db4d896db3ee10b77a5f5d3f3abe5ad718390e2cc228')},
}


def execute(lane):
    root = ROOT/lane
    case = root/'off'
    expected = json.loads((runner.S1/'legacy10/inputs.json').read_text())['sha256']
    shutil.copytree(SOURCE, case/'runs')
    (case/'output').mkdir()
    chan = case/'runs/chan.inp'
    assert chan.read_text().split() == ['1', '600', '0', '1', '1235']
    chan.write_text('3 600\n0\n1\n1235\n')
    # Preserve the historical selector-only edit exactly, including whitespace.
    old = (SOURCE/'chan.inp').read_text()
    chan.write_text(re.sub(r'^1', '3', old, count=1))
    assert runner.manifest(case/'runs') == expected
    runner.save(case/'inputs.json', expected)
    (root/'bin').mkdir()
    for name, (source, digest) in BINARIES[lane].items():
        assert runner.sha(source) == digest
        shutil.copy2(source, root/'bin'/name)
    runner.save(root/'build.json', {name: {'source': str(path), 'sha256': digest}
                                   for name, (path, digest) in BINARIES[lane].items()})
    files = sorted(p for p in (case/'runs').glob('p*.run') if re.fullmatch(r'p[0-9]+', p.stem))
    assert len(files) == 864

    def model(name, runfile):
        logdir = case/'logs'/runfile.stem
        result = runner.execute(root/'bin'/name, runfile, logdir)
        assert result['success'], result
        text = (logdir/'stdout').read_text()
        assert list(map(int, re.findall(r'SIMULATION YEAR\s*=\s*(\d+)', text))) == list(range(1, 25))
        return result

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(model, 'wepp_hill', p) for p in files]):
            results.append(future.result())
            if len(results) % 64 == 0:
                print(lane, 'HILLS', len(results), '/864', flush=True)
    runner.save(case/'hillslopes.json', results)
    hills = runner.manifest(case/'output')
    assert len(hills) == 864*7
    runner.save(case/'outputs-hills.json', hills)
    runner.save(case/'pass-provenance.json', dict(generated_in_this_run=True,
        binary_sha256=runner.sha(root/'bin/wepp'), hill_binary_sha256=runner.sha(root/'bin/wepp_hill'),
        sha256={n: h for n, h in hills.items() if n.endswith('.pass.dat')}))
    print(lane, 'WATERSHED START', flush=True)
    result = model('wepp', case/'runs/pw0.run')
    runner.save(case/'watershed.json', result)
    for name in ('chan.out', 'chanwb.out', 'tc_out.txt'):
        if (case/'runs'/name).exists():
            shutil.move(case/'runs'/name, case/'output'/name)
    runner.save(case/'outputs.json', runner.manifest(case/'output'))
    print(lane, 'WATERSHED COMPLETE; FRESH TOTALWATSED CONVERSION', flush=True)
    with (root/'yield-conversion.log').open('w') as log:
        subprocess.run([sys.executable, str(HELPERS/'convert_component_yield.py'),
                        '--root', str(root), '--extension', str(native.wepp_interchange_rust.__file__),
                        '--output', str(root/'yield-optimized')], stdout=log, stderr=subprocess.STDOUT, check=True)
    print(lane, 'COMPLETE', flush=True)


def main():
    ROOT.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, ROOT/'runner.py')
    runner.save(ROOT/'source-manifest.json', runner.manifest(SOURCE))
    runner.save(ROOT/'helpers.json', {name: runner.sha(HELPERS/name) for name in
                                    ('run_factorial.py', 'convert_component_yield.py')})
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(execute, BINARIES))
    assert runner.manifest(SOURCE) == json.loads((ROOT/'source-manifest.json').read_text())
    a = json.loads((ROOT/'release/off/outputs-hills.json').read_text())
    b = json.loads((ROOT/'candidate/off/outputs-hills.json').read_text())
    runner.save(ROOT/'hillslope-parity.json', dict(files=len(a), same_names=a.keys() == b.keys(),
        changed=sorted(n for n in a.keys() | b.keys() if a.get(n) != b.get(n))))


if __name__ == '__main__':
    main()
