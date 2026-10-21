"""Replay full model decks from the supported isolated project fork."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

from replay_controlled import manifest


def main(args):
    args.root.mkdir(parents=True)
    runs = args.root / 'runs'
    shutil.copytree(args.source / 'wepp/runs', runs)
    (args.root / 'output').mkdir()
    cards = sorted(runs.glob('p[0-9]*.run'))
    for card in cards + [runs / 'pw0.run']:
        lines = card.read_text().splitlines()
        # Explicit legacy-to-current input selection, no text-pass fallback.
        lines = [line.replace('.pass.dat', '.hbp') for line in lines
                 if line.strip() and line != '../output/pass_pw0.txt']
        if card.name == 'pw0.run' and '../output/initcond_pw0.txt' in lines:
            # Current HBP prompt contract in wepp_runner._watershed_prompt_contract_lines:
            # no disabled initial-output filename; explicit impoundment slots.
            lines.remove('../output/initcond_pw0.txt')
            lines.insert(lines.index('pw0.str'), 'No')
            if 'pw0.imp' not in lines:
                lines.insert(lines.index('pw0.man'), 'pw0.imp')
        card.write_text('\n'.join(lines) + '\n')
    if args.observe:
        (runs / 'wepp_observe.on').touch()
    else:
        assert not (runs / 'wepp_observe.on').exists()
    assert not (runs / 'wepp_observe_frost.on').exists()
    (args.root / 'input_manifest.json').write_text(json.dumps(manifest(runs), indent=2))
    env = dict(os.environ)
    if args.observe:
        for flag, filename in [('WB33_M1A_BAL_DIAG', 'channel_balance.csv'),
                               ('WB33_M7_PUBLISH_TRACE', 'channel_publish.csv')]:
            env[flag] = '1'
            env[flag + '_PATH'] = str(args.root / filename)
    # Serial execution preserves unambiguous shared observer logs and files.
    results = []
    for card in cards + [runs / 'pw0.run']:
        start = time.monotonic()
        with card.open('rb') as inp, (args.root / (card.name + '.stdout')).open('wb') as out, (args.root / (card.name + '.stderr')).open('wb') as err:
            proc = subprocess.run([str(args.binary)], cwd=runs, stdin=inp, stdout=out, stderr=err,
                                  env=env, timeout=600)
        success = proc.returncode == 0 and 'SIMULATION SUCCESSFULLY' in (args.root / (card.name + '.stdout')).read_text(errors='replace')
        result = {'card': card.name, 'returncode': proc.returncode, 'success': success,
                  'seconds': time.monotonic() - start}
        if args.observe and (runs / 'wepp_observe.log').exists():
            (runs / 'wepp_observe.log').rename(args.root / (card.name + '.observe.log'))
        results.append(result)
        print(result, flush=True)
        if not success:
            break
    (args.root / 'execution.json').write_text(json.dumps({'binary': str(args.binary),
        'binary_sha256': hashlib.sha256(args.binary.read_bytes()).hexdigest(), 'observe': args.observe,
        'results': results, 'output_manifest': manifest(args.root / 'output')}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--observe', action='store_true')
    main(p.parse_args())
