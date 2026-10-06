#!/usr/bin/env python3
"""Topanga frozen-deck seed experiment; run only in its isolated bundle root."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta, datetime, timezone
import gzip
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'tools'))
from observer import parse_trace
from pairing import pair_events
from peakflow_phase1_fixture import event_values

LANES = ('ksat20','ksat35','cover90','cover80','dense')
PAIRS = {'ksat': ('ksat20','ksat35','ksat','plus'),
         'cover': ('cover90','cover80','cover','minus'),
         'dense': ('cover90','dense','management','plus')}
FOCAL = ('1980-02-14','1986-02-15','1995-01-10','2005-01-09','2021-12-30')
FLAGS = ('candidate','peak_gt25pct_runoff_lt5pct','peak_twofold','solver_changed',
         'surplus_rate_twofold','forcing_mode_changed','event_presence_changed','expected_response_reversal')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')

def cli_rows(path):
    lines=path.read_text().splitlines()
    rows=[line.split() for line in lines[15:] if line.strip()]
    arr=np.array(rows,dtype=float)
    assert arr.shape == (16437,13), (str(path),arr.shape)
    dates=[date(int(r[2]),int(r[1]),int(r[0])) for r in arr]
    assert dates == [date(1980,1,1)+timedelta(days=i) for i in range(16437)]
    assert np.isfinite(arr).all()
    return lines[:15],rows,arr

def verify_bundle():
    for relative,expected in json.loads((ROOT/'bundle-manifest.json').read_text()).items():
        assert sha(ROOT/relative)==expected, relative

def climate(seed, directory):
    directory.mkdir()
    original=ROOT/'inputs/ksat20/p106.cli'
    headers,old_tokens,old=cli_rows(original)
    if seed is None:
        shutil.copy2(original,directory/'p106.cli')
        return {'seed':None,'climate_sha256':sha(directory/'p106.cli'),'original_control':True}
    for name in ('ws.prn','ca041484.par'):
        shutil.copy2(ROOT/'climate-source'/name,directory/name)
    command=[str(ROOT/'bin/cligen532'),'-ica041484.par','-Ows.prn','-oraw.cli','-t6','-I2',f'-r{seed}']
    with (directory/'cligen.log').open('wb') as log:
        result=subprocess.run(command,cwd=directory,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert result.returncode==0
    log=(directory/'cligen.log').read_text(errors='replace')
    for marker in ('FORTRAN runtime error','IEEE_INVALID_FLAG','failed to converge','NaN','error termination.'):
        assert marker.lower() not in log.lower(), marker
    quality_errors=re.findall(r'<<\s*(.*?)\s*>>',log)
    tested_variables=re.findall(r'Parm:([^\n]+?)(?:Month:|Mon:)',log)
    replaced={'Prob. of Precip','Precip. Amt.','Max. Temp.','Min. Temp.',
              'Radiation','Temp. Dew Pt.','Wind Vel.','Wind Dir.'}
    assert set(x.strip() for x in quality_errors+tested_variables)<=replaced, 'quality warning in non-replaced variable'
    if 'could not produce desired level of quality' in log.lower():assert quality_errors
    _,_,generated=cli_rows(directory/'raw.cli')
    _,_,ws=cli_rows(ROOT/'climate-source/wepp.cli')
    assert np.array_equal(generated[:,[0,1,2,3,7,8]],ws[:,[0,1,2,3,7,8]])
    # GridMET overwrites rad/wind/dew point and PRISM spatially corrects P/T.
    # Preserve all archived daily fields and the original writer's .1f storm
    # precision. The unseeded acceptance checks this reconstruction exactly.
    records=[]
    for old_row,raw_row in zip(old_tokens,generated,strict=True):
        row=old_row.copy()
        for j in (4,5,6):row[j]=format(raw_row[j],'.1f')
        records.append(' '.join(row))
    headers[2]=headers[2]+f' STUDY_SEED={seed}'
    (directory/'p106.cli').write_text('\n'.join(headers+records)+'\n')
    _,_,prepared=cli_rows(directory/'p106.cli')
    fixed=[0,1,2,3,7,8,9,10,11,12]
    assert np.array_equal(prepared[:,fixed],old[:,fixed])
    assert np.array_equal(prepared[:,4:7],np.array([[float(format(v,'.1f')) for v in row] for row in generated[:,4:7]]))
    assert (prepared[:,4]>=0).all() and ((prepared[:,5]>=0)&(prepared[:,5]<=1)).all()
    return {'seed':seed,'command':command,'raw_sha256':sha(directory/'raw.cli'),
            'climate_sha256':sha(directory/'p106.cli'),
            'quality_errors_replaced_variables':quality_errors,
            'quality_policy':'retain warnings; allowed only for independently frozen observed daily variables',
            'storm_values_changed':int(np.count_nonzero(prepared[:,4:7]!=old[:,4:7])),
            'fixed_columns_equal':True,'records':len(prepared)}

def one_lane(lane, parent, climate_path):
    target=parent/lane
    runs=target/'runs';out=target/'output'
    shutil.copytree(ROOT/'inputs'/lane,runs)
    out.mkdir()
    shutil.copy2(climate_path,runs/'p106.cli')
    assert sha(runs/'p106.cli')==sha(climate_path)
    for p in (ROOT/'inputs'/lane).iterdir():
        if p.name!='p106.cli':assert sha(p)==sha(runs/p.name)
    (runs/'peak_diag.on').touch()
    before={p.name:sha(p) for p in runs.iterdir() if p.is_file()}
    start=time.monotonic()
    with (runs/'p106.run').open('rb') as stdin, (target/'stdout.txt').open('wb') as stdout, (target/'stderr.txt').open('wb') as stderr:
        result=subprocess.run([str(ROOT/'bin/wepp_hill')],cwd=runs,stdin=stdin,stdout=stdout,stderr=stderr,timeout=180)
    assert result.returncode==0, (lane,result.returncode)
    assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (target/'stdout.txt').read_text()
    for name,h in before.items():assert sha(runs/name)==h,(lane,name)
    trace=parse_trace(runs/'peak_diag.csv',lane,106)
    assert not trace.duplicated(['year','day','ofe','ordinal']).any()
    trace.to_parquet(target/'events.parquet',index=False)
    focal={d:event_values(out,date.fromisoformat(d)) for d in FOCAL}
    outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    report={'lane':lane,'seconds':time.monotonic()-start,'inputs':before,'outputs':outputs,
            'trace_sha256':sha(runs/'peak_diag.csv'),'events':len(trace),'focal':focal}
    dump(target/'terminal.json',report)
    # Lossless compression retains all raw outputs with original hashes above.
    for p in [runs/'peak_diag.csv',*out.iterdir()]:
        if p.is_file():
            with p.open('rb') as src,gzip.open(str(p)+'.gz','wb',compresslevel=1) as dst:
                shutil.copyfileobj(src,dst)
            p.unlink()
    return trace,report

def one_seed(label,seed):
    parent=ROOT/'runs'/label
    parent.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    try:
        provenance=climate(seed,parent/'climate')
        dump(parent/'climate-manifest.json',provenance)
        tables={};reports={}
        for lane in LANES:
            tables[lane],reports[lane]=one_lane(lane,parent,parent/'climate/p106.cli')
        paired=[]
        for pair,(left,right,family,direction) in PAIRS.items():
            trial=SimpleNamespace(trial_id=label+'-'+pair,scenario=pair,hillslope_id=106,family=family,direction=direction)
            table=pair_events(tables[left],tables[right],trial)
            table['date']=[(date(int(y),1,1)+timedelta(days=int(d)-1)).isoformat() for y,d in zip(table.year,table.day)]
            table['pair']=pair;table['seed_label']=label;table['seed']=seed
            paired.append(table)
        pairs=pd.concat(paired,ignore_index=True)
        pairs.to_parquet(parent/'pairs.parquet',index=False)
        focal_rows=[]
        for pair in PAIRS:
            for d in FOCAL:
                subset=pairs[(pairs.pair==pair)&(pairs.date==d)]
                focal_rows.append({'pair':pair,'date':d,'present_records':len(subset),**{flag:bool(subset[flag].any()) for flag in FLAGS}})
        terminal={'status':'complete','label':label,'seed':seed,'seconds':time.monotonic()-start,
                  'climate':provenance,'pair_rows':len(pairs),'focal_flags':focal_rows,
                  'lanes':reports,'observer_sha256':sha(ROOT/'bin/wepp_hill')}
        dump(parent/'terminal.json',terminal)
        print(json.dumps({'label':label,'status':'complete','seconds':terminal['seconds'],'focal_flags':focal_rows[:2]}),flush=True)
        return terminal
    except Exception as exc:
        # Deliberate study job boundary: preserve traceback and fail the batch.
        dump(parent/'failed.json',{'status':'failed','label':label,'seed':seed,'error':repr(exc),'traceback':traceback.format_exc()})
        raise

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['control','pilot','inference']);p.add_argument('--workers',type=int,default=4)
    args=p.parse_args();assert 1<=args.workers<=4
    verify_bundle()
    seeds=json.loads((ROOT/'seeds.json').read_text())
    if args.phase=='control':conditions=[('original',None)]
    elif args.phase=='pilot':conditions=[(f'pilot-{s:05}',s) for s in seeds['pilot']]+[('repeat-12345',12345)]
    else:
        assert (ROOT/'pilot-acceptance.json').is_file()
        assert json.loads((ROOT/'pilot-acceptance.json').read_text())['status']=='pass'
        conditions=[(f'inference-{s:05}',s) for s in seeds['inference']]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(one_seed,label,seed) for label,seed in conditions]
        results=[future.result() for future in as_completed(futures)]
    dump(ROOT/f'{args.phase}-complete.json',{'status':'complete','conditions':len(results),'labels':[r['label'] for r in results], 'finished_at':datetime.now(timezone.utc).isoformat()})

if __name__=='__main__':main()
