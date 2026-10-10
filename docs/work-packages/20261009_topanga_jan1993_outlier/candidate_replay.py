#!/usr/bin/env python3
"""One bounded CHRQIN correction, fresh same-build hills and watershed runs."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

import numpy as np
import pandas as pd
from wepppyo3 import wepp_interchange as native

from output_replay import SUFFIX, FIELDS, sha, save, inventory

HERE=Path(__file__).resolve().parent
ROOT=Path('/wc1/holdouts/chrqin-normalization-candidate-20261009-v2')
BUILDS={'wepp':Path('/wc1/holdouts/chrqin-candidate-watershed-src'),
        'wepp_hill':Path('/wc1/holdouts/chrqin-candidate-hill-src')}
PRIOR=Path('/wc1/holdouts/topanga-jan1993-output-replay-20261009/control')
SITES={'topanga':dict(live=Path('/wc1/runs/sc/scrawny-relay'),source=PRIOR,years=45,hills=284,start_year=1980),
       'rattlesnake':dict(live=Path('/wc1/runs/an/anisotropic-sassafras'),source=Path('/wc1/runs/an/anisotropic-sassafras'),years=100,hills=73,start_year=1)}


def execute(binary, runfile, cwd, logfile, years, timeout):
    started=time.monotonic()
    with runfile.open('rb') as inp,logfile.open('wb') as out:
        r=subprocess.run([str(ROOT/binary)],cwd=cwd,stdin=inp,stdout=out,stderr=subprocess.STDOUT,timeout=timeout)
    text=logfile.read_text()
    assert r.returncode==0 and not any(s in text for s in ['Fortran runtime error','Program received signal','Program stop'])
    assert list(map(int,re.findall(r'SIMULATION YEAR\s*=\s*(\d+)',text)))==list(range(1,years+1))
    return text,time.monotonic()-started


def run_case(key):
    site,scenario=key;cfg=SITES[site];suffix=SUFFIX[scenario]
    case=ROOT/site/suffix/'wepp';live=cfg['live']/suffix/'wepp'
    calendar=ROOT/site/'calendar.parquet'
    baseline=pd.read_parquet(live/'output/interchange/H.pass.parquet',columns=['wepp_id']+FIELDS)
    refs={int(wid):g[FIELDS].reset_index(drop=True) for wid,g in baseline.groupby('wepp_id')}
    assert len(refs)==cfg['hills']
    logs=ROOT/f'{site}-{scenario}-hills';logs.mkdir()
    def hill(wid):
        text,seconds=execute('wepp_hill',case/'runs'/f'p{wid}.run',case/'runs',logs/f'H{wid}.log',cfg['years'],600)
        assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in text
        p=case/'output'/f'H{wid}.pass.dat'
        fresh=pd.DataFrame(native.hillslope_pass_to_columns(str(p),1,0,cli_calendar_path=str(calendar)))[FIELDS]
        old=refs[wid]
        assert fresh.shape==old.shape and fresh.event.equals(old.event),(site,scenario,wid,'shape/event')
        for column in FIELDS[1:]:
            assert np.array_equal(fresh[column],old[column],equal_nan=True),(site,scenario,wid,column)
        physical_hash=sha(p)
        if site=='topanga':
            assert physical_hash==sha(cfg['source']/suffix/'wepp/output'/p.name),(scenario,wid,'raw PASS')
        return dict(wepp_id=wid,seconds=seconds,pass_sha256=physical_hash,records=len(fresh),selected_fields_equal=True)
    receipts=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(hill,i) for i in range(1,cfg['hills']+1)]):
            receipts.append(f.result())
            if len(receipts)%32==0: print(site,scenario,'hills',len(receipts),flush=True)
    save(ROOT/f'{site}-{scenario}-hills.json',receipts)
    del baseline,refs
    text,seconds=execute('wepp',case/'runs/pw0.run',case/'runs',ROOT/f'{site}-{scenario}-watershed.log',cfg['years'],1800)
    assert 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in text
    for name in ('chan.out','chanwb.out','tc_out.txt'):
        shutil.move(str(case/'runs'/name),case/'output'/name)
    parquet=ROOT/f'{site}-{scenario}-ebe.parquet'
    native.watershed_ebe_to_parquet(str(case/'output/ebe_pw0.txt'),str(parquet),1,0,
        cli_calendar_path=str(calendar),start_year=cfg['start_year'],legacy_element_id=412 if site=='topanga' else 104)
    f=pd.read_parquet(parquet)
    original=pd.read_parquet(live/'output/interchange/ebe_pw0.parquet')
    assert len(f)==len(original)
    for column in ['year','month','day_of_month','precip']:
        assert np.array_equal(f[column],original[column],equal_nan=True),(site,scenario,column)
    save(ROOT/f'{site}-{scenario}-receipt.json',dict(site=site,scenario=scenario,years=cfg['years'],
        seconds=seconds,rows=len(f),completed=True,binary_sha256=sha(ROOT/'wepp'),
        hill_binary_sha256=sha(ROOT/'wepp_hill'),output_sha256=inventory(case/'output')))
    print(site,scenario,'WATERSHED COMPLETE',len(f),'rows',flush=True)


def main():
    ROOT.mkdir(parents=True,exist_ok=False)
    for name,build in BUILDS.items():
        profile='includes_hill' if name=='wepp_hill' else 'includes_watershed'
        for inc in ['pmxhil.inc','pmxpln.inc','pmxelm.inc','pntype.inc']:
            assert sha(build/inc)==sha(build/profile/inc),(name,inc)
        shutil.copy2(build/name,ROOT/name)
    shutil.copy2(__file__,ROOT/'executed_runner.py')
    identities={}
    for site,cfg in SITES.items():
        for scenario,suffix in SUFFIX.items():
            source=cfg['source']/suffix/'wepp/runs';target=ROOT/site/suffix/'wepp'
            before=inventory(source);shutil.copytree(source,target/'runs');(target/'output').mkdir()
            assert inventory(target/'runs')==before==inventory(source)
            identities[f'{site}/{scenario}']=before
        shutil.copy2(cfg['live']/'climate/wepp_cli.parquet',ROOT/site/'calendar.parquet')
    save(ROOT/'inputs.json',identities)
    save(ROOT/'build.json',dict(binaries={n:sha(ROOT/n) for n in ['wepp','wepp_hill']},
        source_base='692c225e672844c71114bbdda851625616ebbba9',
        change='CHRQIN excludes qin0(0) only when nt0=0; all positive-time samples remain in normalization'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run_case,[(s,c) for s in SITES for c in SUFFIX]))


if __name__=='__main__':
    main()
