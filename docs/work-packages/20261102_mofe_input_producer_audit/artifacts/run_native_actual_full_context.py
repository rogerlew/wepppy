"""Supplement partial-preparation evidence with the complete configured workflow."""
from pathlib import Path
import hashlib
import json
import os
import shutil

from wepppy.nodb.core import Wepp


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    wd = Path('/wc1/runs/mi/mipa-awake-20261102')
    evidence = Path('/wc1/holdouts/mipa-native-r6-20261102/actual-project-full-v1')
    evidence.mkdir(exist_ok=False)
    shutil.copytree(wd / 'wepp', evidence / 'prior-partial-preparation')
    w = Wepp.getInstance(str(wd))
    w.wepp_bin = 'wepp_261029'
    settings = {k: getattr(w, k) for k in (
        'run_frost', 'run_baseflow', 'run_wepp_ui', 'run_pmet', 'run_snow', 'multi_ofe')}
    (evidence / 'settings.json').write_text(json.dumps(settings, indent=2) + '\n')
    w.prep_hillslopes(max_workers=4)
    runs = Path(w.runs_dir)
    manifest = {p.name: sha(p) for p in runs.iterdir()
                if p.is_file() and p.suffix != '.err'}
    (evidence / 'inputs.json').write_text(json.dumps(manifest, indent=2) + '\n')
    Path(w.output_dir).rename(evidence / 'prior-output-at-execution')
    Path(w.output_dir).mkdir()
    w.run_hillslopes(max_workers=4)
    outputs = {p.name: sha(p) for p in Path(w.output_dir).iterdir() if p.is_file()}
    assert len(list(runs.glob('p*.run'))) == 72
    assert len(outputs) == 504
    (evidence / 'receipt.json').write_text(json.dumps({
        'uid': os.getuid(), 'gid': os.getgid(), 'clone': str(wd),
        'selected_pair': w.wepp_bin, 'settings': settings,
        'hills': 72, 'outputs': outputs,
    }, indent=2) + '\n')
    print('Complete configured copied-project workflow PASS', len(outputs), 'outputs')


if __name__ == '__main__':
    main()
