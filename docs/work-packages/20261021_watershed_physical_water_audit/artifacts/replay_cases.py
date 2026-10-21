"""Fresh controlled release replays; source decks are read-only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

REPO = Path('/workdir/wepppy')
SPEC = importlib.util.spec_from_file_location('prior', REPO/'docs/work-packages/20261021_watershed_channel_routing_closure/artifacts/replay_controlled.py')
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)
BIN = REPO/'wepp_runner/bin/wepp_261021'

def run_case(args):
    root, name, fractions, mode = args
    case = root/f'{mode}-{name}'
    PRIOR.prepare(case, fractions)
    runs = case/'runs'
    card = runs/'p1.run'
    card.write_text(card.read_text().replace('.hbp', '.pass.dat'))
    # Explicit legacy ASCII prompt contract; no imported generated PASS data.
    lines = ['M','Yes','1','2','../output/pass_pw0.txt','1','M','Y',
             '../output/H1.pass.dat','Yes','No','../output/initcond_pw0.txt',
             '1','../output/loss_pw0.txt','Yes','../output/chnwb.txt','No',
             'Yes','../output/soil_pw0.txt','Yes','../output/plot_pw0.txt',
             'No','Yes','../output/ebe_pw0.txt','No','No','No','pw0.str',
             'pw0.chn','pw0.man','pw0.slp','pw0.cli','pw0.sol','0','44']
    (runs/'pw0.run').write_text('\n'.join(lines)+'\n')
    if mode == 'daily':
        (runs/'wepp_ui.txt').unlink()
    # Full hydrograph timestamps and daily channel balance for the single channel.
    (runs/'chan.inp').write_text('3 600\n0\n1\n2\n')
    (case/'input_manifest.json').write_text(json.dumps(PRIOR.manifest(runs),indent=2)+'\n')
    env=dict(os.environ)
    if any(k.startswith(('WB','WEPP_')) for k in env):
        raise RuntimeError('Uninventoried model environment')
    records=[]
    for filename,binary in [('p1.run', Path(str(BIN)+'_hill')),('pw0.run',BIN)]:
        start=time.monotonic()
        with (runs/filename).open('rb') as inp, (case/(filename+'.stdout')).open('wb') as out, (case/(filename+'.stderr')).open('wb') as err:
            proc=subprocess.run([str(binary)],cwd=runs,stdin=inp,stdout=out,stderr=err,env=env,timeout=1800)
        success=proc.returncode == 0 and 'SIMULATION SUCCESSFULLY' in (case/(filename+'.stdout')).read_text(errors='replace')
        records.append(dict(card=filename,binary=str(binary),sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),returncode=proc.returncode,success=success,seconds=time.monotonic()-start))
        if not success: break
    result=dict(case=case.name,mode=mode,fractions=fractions,results=records,outputs=PRIOR.manifest(case/'output'))
    (case/'execution.json').write_text(json.dumps(result,indent=2)+'\n')
    print(case.name,[(r['card'],r['success'],round(r['seconds'],1)) for r in records],flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    a.root.mkdir(parents=True,exist_ok=False)
    tasks=[(a.root,n,f,m) for m in ['daily','hourly'] for n,f in [('single',[1.]),('equal',[.5,.5]),('upper60',[.6,.4]),('lower60',[.4,.6]),('three',[.2,.3,.5])]]
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(run_case,tasks))
    (a.root/'execution.json').write_text(json.dumps(results,indent=2)+'\n')
    if not all(len(r['results'])==2 and all(x['success'] for x in r['results']) for r in results): raise SystemExit(1)
