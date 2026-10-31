"""Replay unchanged Roads inputs under an isolated DEPEND ablation binary."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
import continuation as c
HERE=Path(__file__).resolve().parent
PARENT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
ROOT=PARENT/'depend-bounded-g1'
BINARY=ROOT/'bin/wepp'

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def execute(task):
    source,old,panel,sha=task;source=Path(source)
    folder=ROOT/panel/source.name;runs=folder/'runs';out=folder/'output'
    runs.mkdir(parents=True,exist_ok=False);out.mkdir()
    assert digest(BINARY)==sha
    for name,h in old['inputs'].items():
        assert digest(source/'runs'/name)==h
        shutil.copy2(source/'runs'/name,runs/name)
    if not (runs/'reference.sol').exists():shutil.copy2(runs/'p1.sol',runs/'reference.sol')
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        proc=subprocess.run([str(BINARY)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300)
    row=dict(case=old['case'],inputs=old['inputs'],soil_readback=old['soil_readback'],
             width_m=old['width_m'],profile_length_m=old['profile_length_m'],
             source=str(source),source_record_sha256=digest(source/'record.json'),
             folder=str(folder),binary_sha256=sha,returncode=proc.returncode,physical_pass=False,
             outputs={p.name:digest(p) for p in out.iterdir() if p.is_file()})
    row['changed_outputs']=[n for n in old['outputs'].keys()|row['outputs'].keys() if old['outputs'].get(n)!=row['outputs'].get(n)]
    if proc.returncode==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs/'stdout').read_text():
        row['metrics']=c.b.parse_loss(out/'H1.loss.dat',row['width_m'])
        row['audit']=c.audit(folder,row['case'],row);row['physical_pass']=row['audit']['physical_pass']
    for name,h in row['inputs'].items():assert digest(runs/name)==h
    save(folder/'record.json',row)
    return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument('panel',choices=['fixture','roads','downstream']);args=ap.parse_args()
    base=Path('/workdir/wepppy/out/roads-native-funding-20261031/r3-matrix840')
    if args.panel=='roads':
        rows=json.loads((base/'results.json').read_text());tasks=[(str(base/'matrix-v1'/'-'.join(r['case'].values())),r,'roads',digest(BINARY)) for r in rows];assert len(tasks)==840
    else:
        rows=json.loads((PARENT/'downstream-hydraulics-r3/results.json').read_text())
        if args.panel=='fixture':rows=[r for r in rows if not r['physical_pass']];assert len(rows)==1
        tasks=[(r['folder'],r,args.panel+'-'+r['lane'],digest(BINARY)) for r in rows]
    save(ROOT/(args.panel+'-declaration.json'),dict(script_sha256=digest(Path(__file__)),tasks=tasks))
    with ProcessPoolExecutor(max_workers=8) as pool:
        results=[]
        for row in pool.map(execute,tasks):
            results.append(row)
            print(len(results),row['case'],row['returncode'],row['physical_pass'],len(row['changed_outputs']),flush=True)
    save(ROOT/(args.panel+'-results.json'),results)
    save(ROOT/(args.panel+'-summary.json'),dict(cases=len(results),physical=sum(r['physical_pass'] for r in results),changed=sum(bool(r['changed_outputs']) for r in results),binary_sha256=digest(BINARY)))
if __name__=='__main__':main()
