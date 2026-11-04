"""Disposable real-service Roads parameterization workflow evidence helpers.

This script creates and inspects a canonical disposable run. Browser mutations and
native execution are performed by the companion browser script through real routes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

SOURCE = Path('/wc1/runs/ro/roads-parameterization-program-20261103/revised-project-sensitivity-v1/w4-f30')
RUN = Path('/wc1/runs/ro/roads-param-ui-20261103-v1')
RAW = Path('/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-workflow-v1')
CONFIG = 'disturbed9002-wbt-mofe'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def inventory(root, prefixes=None):
    paths = [Path(root)] if prefixes is None else [Path(root) / name for name in prefixes]
    return {str(p.relative_to(root)): sha(p) for path in paths for p in sorted(path.rglob('*'))
            if p.is_file() and not any(x in p.parts for x in ('_query_engine','_logs')) and not p.name.endswith('.log')}


def rebase(value):
    if isinstance(value, dict):
        return {k: rebase(v) for k,v in value.items()}
    if isinstance(value, list):
        return [rebase(v) for v in value]
    if isinstance(value, str) and (value == str(SOURCE) or value.startswith(str(SOURCE) + '/')):
        return str(RUN) + value[len(str(SOURCE)):]
    return value


def prepare():
    if RAW.exists() or RUN.exists():
        raise FileExistsError('Use a fresh exclusive evidence root and run ID')
    RAW.mkdir()
    before = inventory(SOURCE)
    mask = os.umask(0); os.umask(mask)
    save(RAW / 'preparation-declaration.json', {
        'source':str(SOURCE),'run':str(RUN),'config':CONFIG,
        'source_inventory':before,'script_sha256':sha(__file__),
        'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'umask':oct(mask),
        'scope':'disposable clone; public browser routes/RQ execution after source readiness',
        'production_source_approval_ancestor':'73b5da4ac',
    })
    shutil.copytree(SOURCE, RUN, ignore=shutil.ignore_patterns('*.log','_logs','_query_engine','export'))
    for p in RUN.glob('*.nodb'):
        p.write_text(json.dumps(rebase(json.loads(p.read_text()))))
    if inventory(SOURCE) != before:
        raise AssertionError('Source mutated during disposable copy')
    save(RAW/'baseline-before.json',inventory(RUN,('wepp/runs','wepp/output')))
    roads = json.loads((RUN/'roads.nodb').read_text())['py/state']
    assert '_parameterization' not in roads
    save(RAW/'preparation-completed.json', {'run':str(RUN),'source_preserved':True,
        'legacy_unbound':True,'baseline_files':len(inventory(RUN,('wepp/runs','wepp/output'))),
        'config':CONFIG,'uid':os.getuid(),'gid':os.getgid()})
    print('Prepared disposable legacy-unbound run', RUN.name)


def readback(label):
    state = json.loads((RUN/'roads.nodb').read_text())['py/state']
    from wepppy.nodb.mods.roads import Roads
    controller=Roads.getInstance(str(RUN))
    param=getattr(controller,'_parameterization',None)
    source_ok = inventory(SOURCE) == json.loads((RAW/'preparation-declaration.json').read_text())['source_inventory']
    baseline_ok = inventory(RUN,('wepp/runs','wepp/output')) == json.loads((RAW/'baseline-before.json').read_text())
    assert source_ok and baseline_ok
    data = {'label':label,'parameterization':param,'roads_params':state.get('_roads_params'),
        'source_preserved':source_ok,'baseline_preserved':baseline_ok,
        'nodb_sha256':sha(RUN/'roads.nodb'),'uid':os.getuid(),'gid':os.getgid()}
    manifest=RUN/'wepp/roads/segments/roads.segment.pass.manifest.json'
    if manifest.exists():
        rows=json.loads(manifest.read_text())
        data['manifest_type']=type(rows).__name__
        data['rows']=len(rows)
        data['parameterization_rows']=sum('parameterization' in row for row in rows)
        data['manifest_sha256']=sha(manifest)
    save(RAW/f'{label}-readback.json',data)
    print(label,'source/baseline preserved; parameterization', 'bound' if param else 'absent')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['prepare','readback']);parser.add_argument('--label',default='current')
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    else:readback(args.label)
