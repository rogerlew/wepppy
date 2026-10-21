"""Extend paired released runs to short channels, tributaries, and a cascade."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from replay_cases import PRIOR,BIN
from wepppy.wepp.management import Management
from wepppy.wepp.soils.utils.multi_ofe import SoilMultipleOfeSynth
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')

def execute(args):
    mode,kind=args;base=ROOT/'release-matrix'/f'{mode}-upper60';root=ROOT/'networks'/f'{mode}-{kind}';runs=root/'runs'
    shutil.copytree(base/'runs',runs);(root/'output').mkdir()
    multi=kind!='short';nh=3 if multi else 1;nc=2 if kind=='cascade' else 1
    for h,width in [(1,100),(2,50),(3,200)][:nh]:
        for ext in ['run','man','sol','cli']:
            value=(base/'runs'/f'p1.{ext}').read_text()
            if ext=='run':value=value.replace('p1.',f'p{h}.').replace('H1.',f'H{h}.')
            (runs/f'p{h}.{ext}').write_text(value)
        (runs/f'p{h}.slp').write_text(f'97.5\n2\n180 {width}\n2 60\n0.0 0.1 1.0 0.1\n2 40\n0.0 0.1 1.0 0.1\n')
    card=(base/'runs/pw0.run').read_text().splitlines();assert card[5]=='1'
    card=card[:5]+[str(nh)]+sum((['M','Y',f'../output/H{h}.pass.dat'] for h in range(1,nh+1)),[])+card[9:]
    (runs/'pw0.run').write_text('\n'.join(card)+'\n')
    (runs/'pw0.str').write_text('99.1\n'+('2 2 3 1 0 0 0 0 0 0\n' if multi else '2 0 0 1 0 0 0 0 0 0\n')+('2 0 0 0 0 0 4 0 0 0\n' if nc==2 else ''))
    (runs/'pw0.slp').write_text('99.1\n'+str(nc)+'\n'+('180 1\n2 100\n0.0 0.05 1.0 0.05\n'*nc))
    if nc==2:
        man=Management(Key='audit-channel',ManagementFile='pw0.man',ManagementDir=str(base/'runs'));man.make_multiple_ofe(2);(runs/'pw0.man').write_text(str(man))
        SoilMultipleOfeSynth([str(base/'runs/pw0.sol')]*2).write(str(runs/'pw0.sol'))
        lines=(base/'runs/pw0.chn').read_text().splitlines();lines[1]='2';(runs/'pw0.chn').write_text('\n'.join(lines[:4]+lines[4:]*2)+'\n')
    (runs/'chan.inp').write_text(f'3 600\n0\n{nc}\n'+''.join(f'{nh+i}\n' for i in range(1,nc+1)))
    (root/'input_manifest.json').write_text(json.dumps(PRIOR.manifest(runs),indent=2)+'\n')
    results=[]
    for card in [f'p{h}.run' for h in range(1,nh+1)]+['pw0.run']:
        binary=BIN if card=='pw0.run' else Path(str(BIN)+'_hill');start=time.monotonic()
        with (runs/card).open('rb') as inp,(root/(card+'.stdout')).open('wb') as out,(root/(card+'.stderr')).open('wb') as err:
            p=subprocess.run([str(binary)],cwd=runs,stdin=inp,stdout=out,stderr=err,timeout=1800)
        success=p.returncode==0 and 'SIMULATION SUCCESSFULLY' in (root/(card+'.stdout')).read_text(errors='replace')
        results.append(dict(card=card,success=success,returncode=p.returncode,seconds=time.monotonic()-start,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest()))
        if not success:break
    receipt=dict(case=root.name,results=results,outputs=PRIOR.manifest(root/'output'))
    (root/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(root.name,[(r['card'],r['success']) for r in results],flush=True)
    return receipt
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(execute,[(m,k) for m in ['daily','hourly'] for k in ['short','tributaries','cascade']]))
    (ROOT/'networks/execution.json').write_text(json.dumps(results,indent=2)+'\n')
