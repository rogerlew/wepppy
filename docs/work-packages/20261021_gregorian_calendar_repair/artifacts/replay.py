"""Regenerate paired hillslope/watershed outputs from a supported project fork."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def migrate_card(card):
    lines=[x.replace('.pass.dat','.hbp') for x in card.read_text().splitlines()
           if x.strip() and x!='../output/pass_pw0.txt']
    if card.name=='pw0.run' and '../output/initcond_pw0.txt' in lines:
        lines.remove('../output/initcond_pw0.txt')
        lines.insert(lines.index('pw0.str'),'No')
        if 'pw0.imp' not in lines:lines.insert(lines.index('pw0.man'),'pw0.imp')
    card.write_text('\n'.join(lines)+'\n')


def execute(binary,card,logroot):
    start=time.monotonic()
    with card.open('rb') as inp, (logroot/(card.name+'.stdout')).open('wb') as out, (logroot/(card.name+'.stderr')).open('wb') as err:
        p=subprocess.run([str(binary)],cwd=card.parent,stdin=inp,stdout=out,stderr=err,timeout=1800)
    success=p.returncode==0 and 'SIMULATION SUCCESSFULLY' in (logroot/(card.name+'.stdout')).read_text(errors='replace')
    return {'card':card.name,'returncode':p.returncode,'success':success,'seconds':time.monotonic()-start}


def main(a):
    a.root.mkdir(parents=True)
    runs=a.root/'runs';output=a.root/'output';output.mkdir()
    shutil.copytree(a.source/'wepp/runs',runs)
    cards=sorted(runs.glob('p[0-9]*.run'))
    if a.hbp:
        for card in cards+[runs/'pw0.run']:migrate_card(card)
    shared=[p for p in runs.iterdir() if p.is_file() and not re.match(r'p\d+\.',p.name)
            and p.suffix not in ('.err','.log') and p.name not in ('chan.out','chanwb.out','tc_out.txt','chntyp.txt')]
    def hill(card):
        case=a.root/'hills'/card.stem;wd=case/'runs';wd.mkdir(parents=True);(case/'output').mkdir()
        for p in list(runs.glob(card.stem+'.*'))+shared:shutil.copy2(p,wd/p.name)
        if a.observe:(wd/'wepp_observe.on').touch()
        result=execute(a.hill_binary,wd/card.name,case)
        if result['success']:
            for p in (case/'output').iterdir():shutil.copy2(p,output/p.name)
        return result
    results=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for future in as_completed([pool.submit(hill,c) for c in cards]):
            result=future.result();results.append(result)
            (a.root/'hills-execution.json').write_text(json.dumps(results,indent=2))
            print(result,flush=True)
    if not all(r['success'] for r in results):raise RuntimeError('hillslope failure: see retained logs')
    if a.observe:(runs/'wepp_observe.on').touch()
    result=execute(a.binary,runs/'pw0.run',a.root);results.append(result);print(result,flush=True)
    (a.root/'execution.json').write_text(json.dumps({'binary':str(a.binary),'binary_sha256':digest(a.binary),
      'hill_binary':str(a.hill_binary),'hill_sha256':digest(a.hill_binary),'hbp':a.hbp,
      'results':results,'output_hashes':{p.name:digest(p) for p in output.iterdir() if p.is_file()}},indent=2))
    if not result['success']:raise RuntimeError('watershed failure: see retained logs')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['source','root','binary','hill-binary']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--hbp',action='store_true');p.add_argument('--observe',action='store_true');p.add_argument('--workers',type=int,default=4)
    main(p.parse_args())
