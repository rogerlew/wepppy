"""Prepare and replay isolated constant-slope cases; never modify source inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

from wepppy.wepp.management import Management
from wepppy.wepp.soils.utils.multi_ofe import SoilMultipleOfeSynth


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def prepare(root, fractions):
    source = Path('/wc1/runs/wb/wb34-impoundment-cohort/wepp/runs')
    runs = root / 'runs'
    runs.mkdir(parents=True)
    (root / 'output').mkdir()
    for name in ['p1.run', 'p1.cli', 'pw0.chn', 'pw0.man', 'pw0.slp',
                 'pw0.cli', 'pw0.sol', 'pw0.imp', 'wepp_ui.txt', 'pmetpara.txt',
                 'snow.txt', 'gwcoeff.txt', 'chan.inp', 'chntyp.txt', 'tc.txt']:
        shutil.copy2(source / name, runs / name)
    man = Management(Key='closure-control', ManagementFile='p1.man', ManagementDir=str(source))
    if len(fractions) > 1:
        man.make_multiple_ofe(len(fractions))
    (runs / 'p1.man').write_text(str(man))
    SoilMultipleOfeSynth([str(source / 'p1.sol')] * len(fractions)).write(str(runs / 'p1.sol'))
    # Matched homogeneous 100 m x 100 m, 10% slope. Splitting may change
    # hydrology; conservation is evaluated independently in every case.
    slope = ['97.5', str(len(fractions)), '180.0 100.0']
    for fraction in fractions:
        slope += [f'2 {100 * fraction:.8f}', '0.0 0.1 1.0 0.1']
    (runs / 'p1.slp').write_text('\n'.join(slope) + '\n')
    (runs / 'pw0.str').write_text('99.1\n2 0 0 1 0 0 0 0 0 0\n')
    card = (source / 'pw0.run').read_text().splitlines()
    # Existing process-family card: replace 3 shard entries with one.
    assert card[4] == '3' and card[7] == '../output/H1.hbp'
    card = card[:4] + ['1'] + card[5:8] + card[14:]
    card[-1] = '44'
    (runs / 'pw0.run').write_text('\n'.join(card) + '\n')
    # Monitor the only channel, element 2, using the existing output selector.
    chan = (runs / 'chan.inp').read_text().splitlines()
    chan[-1] = '2'
    (runs / 'chan.inp').write_text('\n'.join(chan) + '\n')
    (root / 'input_manifest.json').write_text(json.dumps(manifest(runs), indent=2) + '\n')
    (root / 'case.json').write_text(json.dumps({'fractions': fractions, 'area_m2': 10000,
                                               'configured_years': 44, 'source': str(source)}, indent=2))


def execute(root, binary, observe):
    runs = root / 'runs'
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('WB', 'WEPP_')):
            raise RuntimeError(f'Uninventoried simulation environment: {key}')
    if observe:
        (runs / 'wepp_observe.on').touch()
        for flag, filename in [('WB33_M1A_BAL_DIAG', 'channel_balance.csv'),
                               ('WB33_M7_PUBLISH_TRACE', 'channel_publish.csv')]:
            env[flag] = '1'
            env[flag + '_PATH'] = str(root / filename)
    results = []
    for card in ['p1.run', 'pw0.run']:
        start = time.monotonic()
        with (runs / card).open('rb') as inp, (root / (card + '.stdout')).open('wb') as out, (root / (card + '.stderr')).open('wb') as err:
            proc = subprocess.run([str(binary)], cwd=runs, stdin=inp, stdout=out, stderr=err,
                                  env=env, timeout=600)
        text = (root / (card + '.stdout')).read_text(errors='replace')
        success = proc.returncode == 0 and 'SIMULATION SUCCESSFULLY' in text
        results.append({'card': card, 'returncode': proc.returncode, 'success': success,
                        'seconds': time.monotonic() - start})
        if not success:
            break
    (root / 'execution.json').write_text(json.dumps({'binary': str(binary),
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'observe': observe,
        'results': results, 'output_manifest': manifest(root / 'output')}, indent=2) + '\n')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--observe', action='store_true')
    args = parser.parse_args()
    for name, fractions in [('single', [1.0]), ('equal', [.5, .5]), ('upper60', [.6, .4]),
                            ('lower60', [.4, .6]), ('three', [.2, .3, .5])]:
        root = args.root / name
        prepare(root, fractions)
        print(name, execute(root, args.binary, args.observe), flush=True)
