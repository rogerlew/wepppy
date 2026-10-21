"""Replay retained inputs with the corrected reader and fresh same-build hillslopes."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import sys
import shutil

OLD = Path(__file__).resolve().parents[2] / '20261021_watershed_channel_routing_closure/artifacts'
sys.path.insert(0, str(OLD))
from replay_project import main as replay

ROOT = Path('/workdir/hbp-schema2-calendar-selection-20261021')
HOLDOUT = Path('/wc1/holdouts/watershed-channel-routing-closure-20261021')
LOCAL = Path('/workdir/watershed-channel-routing-closure-20261021')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--case', choices=['single', 'upper60', 'real'], required=True)
    p.add_argument('--mode', choices=['off', 'on'], required=True)
    a = p.parse_args()
    if a.case == 'real':
        source = LOCAL / 'real-project-second'
    else:
        source = ROOT / 'sources' / (a.case + '-' + a.mode)
        shutil.copytree(HOLDOUT / 'controlled-baseline' / a.case / 'runs', source / 'wepp/runs')
    replay(SimpleNamespace(source=source, root=ROOT / a.mode / a.case,
                           binary=ROOT / 'candidate-source/src/wepp', observe=a.mode == 'on'))
