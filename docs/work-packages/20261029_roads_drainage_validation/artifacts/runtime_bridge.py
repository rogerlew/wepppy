"""Bounded runtime-mode bridge, declared after discovering absent wepp_ui.txt."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('bridge_study',HERE/'study.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
b=s.b
ROOT=s.ROOT/'runtime-bridge-v1'
SHARED=s.REPO/'tests/roads/data/shared'


def cases():
    for runtime,climates in (('ui-only',s.CLIMATES),('site-shared',('site',))):
        for climate,soil,design,drainage in itertools.product(climates,s.SOILS,('outrut','outunrut'),('current','source')):
            yield dict(climate=climate,soil=soil,design=design,surface='gravel',traffic='high',drainage=drainage,runtime=runtime)


def stage(root):
    root.mkdir(exist_ok=False)
    (root/'inputs').symlink_to(s.ROOT/'inputs',target_is_directory=True)
    (root/'reference').symlink_to(s.ROOT/'reference',target_is_directory=True)
    shutil.copytree(SHARED,root/'shared')
    declaration=json.loads((s.ROOT/'declaration.json').read_text())
    declaration.update(cases=list(cases()),expected_cases=192,
        runtime_shared_sha256={p.name:b.digest(p) for p in (root/'shared').iterdir()},
        runtime_source_sha256={str(p.relative_to(s.REPO)):b.digest(p) for p in (Path(__file__),s.REPO/'wepppy/nodb/mods/roads/roads.py',s.REPO/'wepppy/nodb/core/wepp_prep_service.py')},
        mode='ui-only adds only empty wepp_ui.txt; site-shared copies existing Roads fixture shared files unchanged',
        rationale='Current and preceding simplified experiments omit native UI switch present in project Roads workspaces; isolate mode before claiming physical or production parity')
    b.dump(root/'declaration.json',declaration)
    shutil.copy2(__file__,root/'executed-runtime-bridge.py')
    print('Frozen 160 UI-only + 32 site-shared runs',flush=True)


def execute(task):
    from wepp_runner import make_hillslope_run
    from wepppy.wepp.soils.utils import WeppSoilUtil
    root,case=task;name='-'.join(case.values());folder=root/'matrix-v1'/name
    runs=folder/'runs';out=folder/'output';runs.mkdir(parents=True,exist_ok=False);out.mkdir()
    declaration=json.loads((root/'declaration.json').read_text())
    manifest=json.loads((root/'inputs/manifest.json').read_text())
    b.reference_soil(root,s.TEXTURES[case['soil']],case['design'],case['surface'],case['traffic'],runs/'reference.sol')
    prepared=s.e.build_soil(root,case['soil'],'roles',runs/'reference.sol',runs/'p1.sol')
    soil=WeppSoilUtil(str(runs/'p1.sol'))
    expected=s.buffer_change(prepared['ofes'],declaration['endpoints'][case['soil']][case['drainage']])
    soil.obj['ofes']=expected;soil.write(str(runs/'p1.sol'))
    if WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']!=expected:raise ValueError('Soil readback mismatch')
    man={'outrut':'3outrut.man','outunrut':'3outunr.man'}[case['design']]
    shutil.copy2(root/'reference/api/db/wepproad/managements'/man,runs/'p1.man')
    slope,width,length=b.slope_text(case['design']);(runs/'p1.slp').write_text(slope)
    shutil.copy2(root/'inputs/climates'/f"{case['climate']}.cli",runs/'p1.cli')
    make_hillslope_run(1,16,str(runs),reveg=False,wepp_bin='wepp_261026')
    lines=(runs/'p1.run').read_text().splitlines()
    if lines[6]!='1' or lines[5]!='../output/H1.pass.dat':raise ValueError('Prompt drift')
    lines[6]='2';(runs/'p1.run').write_text('\n'.join(lines)+'\n')
    if case['runtime']=='ui-only':(runs/'wepp_ui.txt').write_bytes(b'')
    elif case['runtime']=='site-shared':
        for p in (root/'shared').iterdir():shutil.copy2(p,runs/p.name)
    else:raise ValueError('Undeclared runtime')
    inputs={p.name:b.digest(p) for p in runs.iterdir() if p.name!='reference.sol'}
    binary=declaration['binaries']['modern']
    if b.digest(binary['path'])!=binary['sha256']:raise ValueError('Binary drift')
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        proc=subprocess.run([binary['path']],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=180)
    log=(runs/'stdout').read_text()
    if proc.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in log:raise ValueError('Native failure')
    if 'WEPP hourly water seepage update set (UI code)' not in log:raise ValueError('UI mode not activated')
    record=dict(case=case,name=name,status='completed',width_m=width,profile_length_m=length,soil_readback=expected,
                inputs=inputs,outputs={p.name:b.digest(p) for p in out.iterdir()},
                metrics=b.parse_loss(out/'H1.loss.dat',width),wat_rows=b.validate_wat(out/'H1.wat.dat',manifest['climates'][case['climate']]))
    s.check_files(folder,record);b.dump(folder/'record.json',record);return name


def run(root,workers):
    declaration=json.loads((root/'declaration.json').read_text())
    for path,sha in declaration['runtime_source_sha256'].items():
        if b.digest(s.REPO/path)!=sha:raise ValueError('Runtime source drift')
    for name,sha in declaration['runtime_shared_sha256'].items():
        if b.digest(root/'shared'/name)!=sha:raise ValueError('Runtime shared drift')
    (root/'matrix-v1').mkdir(exist_ok=False)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for index,name in enumerate(pool.map(execute,((root,c) for c in declaration['cases'])),1):
            print(f'{index}/192 {name}',flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('stage','run'))
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args()
    if args.action=='stage':stage(args.root)
    else:run(args.root,args.workers)


if __name__=='__main__':main()
