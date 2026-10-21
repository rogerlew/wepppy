"""Daily, unequal tributary, cascade and impoundment coverage extensions."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import shutil

from wepppy.wepp.management import Management
from wepppy.wepp.soils.utils.multi_ofe import SoilMultipleOfeSynth
from replay_project import main as replay


def prepare(root, kind):
    base = Path('/wc1/holdouts/watershed-channel-routing-closure-20261021/controlled-baseline/upper60/runs')
    runs = root / 'wepp/runs'
    if kind == 'impoundment':
        shutil.copytree('/wc1/runs/wb/wb34-impoundment-cohort/wepp/runs', runs)
        card = (runs / 'pw0.run').read_text().splitlines()
        card[-1] = '44'
        (runs / 'pw0.run').write_text('\n'.join(card) + '\n')
        return
    shutil.copytree(base, runs)
    if kind == 'daily':
        (runs / 'wepp_ui.txt').unlink()
        return
    for hill, width in [(1, 100), (2, 50), (3, 200)]:
        for ext in ['run', 'man', 'cli', 'sol']:
            value = (base / f'p1.{ext}').read_text()
            if ext == 'run':
                value = value.replace('p1.', f'p{hill}.').replace('H1.', f'H{hill}.')
            (runs / f'p{hill}.{ext}').write_text(value)
        (runs / f'p{hill}.slp').write_text(f'97.5\n2\n180.0 {width}\n2 60\n0.0 0.1 1.0 0.1\n2 40\n0.0 0.1 1.0 0.1\n')
    card = (base / 'pw0.run').read_text().splitlines()
    card = card[:4] + ['3'] + sum((['M', 'Y', f'../output/H{h}.hbp'] for h in [1, 2, 3]), []) + card[8:]
    (runs / 'pw0.run').write_text('\n'.join(card) + '\n')
    (runs / 'pw0.str').write_text('99.1\n2 2 3 1 0 0 0 0 0 0\n')
    (runs / 'chan.inp').write_text('1 600\n0\n1\n4\n')
    if kind == 'cascade':
        (runs / 'pw0.str').write_text('99.1\n2 2 3 1 0 0 0 0 0 0\n2 0 0 0 0 0 4 0 0 0\n')
        m = Management(Key='closure-channel', ManagementFile='pw0.man', ManagementDir=str(base))
        m.make_multiple_ofe(2)
        (runs / 'pw0.man').write_text(str(m))
        SoilMultipleOfeSynth([str(base / 'pw0.sol')] * 2).write(str(runs / 'pw0.sol'))
        (runs / 'pw0.slp').write_text('99.1\n2\n180 1\n2 100\n0.0 0.05 1.0 0.05\n180 1\n2 100\n0.0 0.05 1.0 0.05\n')
        lines = (base / 'pw0.chn').read_text().splitlines()
        lines[1] = '2'
        (runs / 'pw0.chn').write_text('\n'.join(lines[:4] + lines[4:] * 2) + '\n')
        (runs / 'chan.inp').write_text('1 600\n0\n2\n4\n5\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--binary', type=Path)
    p.add_argument('--mode', choices=['prepare', 'baseline', 'off', 'on'], required=True)
    a = p.parse_args()
    for kind in ['daily', 'tributaries', 'cascade', 'impoundment']:
        source = a.root / 'sources' / kind
        if a.mode == 'prepare':
            prepare(source, kind)
        else:
            replay(SimpleNamespace(source=source, root=a.root / a.mode / kind,
                                   binary=a.binary, observe=a.mode == 'on'))
