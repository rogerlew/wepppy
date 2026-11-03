"""Retained partial-preparation probe; full-context helper supersedes acceptance.

This probe omits configured UI/baseflow companions. Do not use its output as
evidence that the complete saved project configuration was executed.
"""
from pathlib import Path
import hashlib
import json
import os

from wepppy.nodb.core import Wepp, Watershed


def main():
    wd='/wc1/runs/mi/mipa-awake-20261102'
    evidence=Path('/wc1/holdouts/mipa-native-r6-20261102/actual-project-v1')
    evidence.mkdir(exist_ok=False)
    w=Wepp.getInstance(wd)
    before=w.wepp_bin
    w.wepp_bin='/wc1/holdouts/mipa-native-r6-20261102/final-pair/wepp_261029'
    translator=Watershed.getInstance(wd).translator_factory()
    w._prep_climates(translator)
    w._make_hillslope_runs(translator)
    runs=Path(w.runs_dir)
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in runs.iterdir() if p.is_file()}
    (evidence/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
    w.run_hillslopes(max_workers=4)
    outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(w.output_dir).iterdir() if p.is_file()}
    (evidence/'receipt.json').write_text(json.dumps({'uid':os.getuid(),'gid':os.getgid(),
        'clone':wd,'prior_clone_selection':before,'selected_pair':w.wepp_bin,
        'hills':len(list(runs.glob('p*.run'))),'outputs':outputs},indent=2)+'\n')
    print('Copied project completed',len(outputs),'outputs')


if __name__=='__main__':main()
