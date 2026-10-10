#!/usr/bin/env python3
"""Freeze version-trace and observer evidence for the localized source defect."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pandas as pd

from output_replay import sha, save
from version_trace import ROOT, SFX

HERE=Path(__file__).resolve().parent
OUT=HERE/'artifacts/mechanism'


def main():
    observer=ROOT/'observer'
    receipt=json.loads((observer/'receipt.json').read_text())
    assert not receipt['differences'] and len(receipt['compared_files'])==293
    OUT.mkdir(parents=True,exist_ok=False)
    pattern=re.compile(r'^(\S+) y=\s*(\d+) d=\s*(\d+) e=\s*(\d+) c=\s*(\d+) s=\s*(\d+) v1=\s*(\S+) v2=\s*(\S+)')
    log=observer/SFX/'wepp/runs/wepp_observe.log';rows=[]
    for line in log.read_text().splitlines():
        m=pattern.match(line)
        assert m,line
        rows.append([m[1],*[int(m[i]) for i in range(2,7)],float(m[7]),float(m[8])])
    f=pd.DataFrame(rows,columns=['tag','year','julian','wepp_id','channel_ordinal','nseg_or_stage','v1','v2'])
    assert set(f.year)=={1993} and set(f.julian)=={16,17,18}
    f.to_csv(OUT/'observer-values.csv',index=False)
    g=f.loc[f.julian.eq(18)&f.tag.str.startswith('J')]
    a=g.pivot(index='wepp_id',columns='tag',values='v1')
    b=g.pivot(index='wepp_id',columns='tag',values='v2')
    result=pd.DataFrame(dict(outlet_peak=a.JQPK,inlet_max=a.JIN,lateral_max=b.JIN,
        initial_min=a.JPOST,initial_max=b.JPOST,linear_initial_max=b.JPRE,
        c1=a.JC12,c2=b.JC12,c3=a.JC3K,K_seconds=b.JC3K,
        end_state_min=a.JEND,end_state_max=b.JEND))
    result.to_csv(OUT/'january18-channel-summary.csv')
    versions=[]
    for version in ['260803','261009']:
        r=json.loads((ROOT/version/'receipt.json').read_text())
        assert r['outlet_parity']=='exact frozen EBE fields'
        frame=pd.read_parquet(ROOT/version/'ebe.parquet')
        frame=frame.loc[frame.year.eq(1993)&frame.month.eq(1)&frame.day_of_month.between(10,24)].copy()
        frame.insert(0,'version',version);versions.append(frame)
        shutil.copy2(ROOT/version/'receipt.json',OUT/f'{version}-receipt.json')
    pd.concat(versions).to_csv(OUT/'paired-version-events-january10-24.csv',index=False)
    shutil.copy2(ROOT/'260803/hills-receipts.json',OUT/'260803-hills-receipts.json')
    shutil.copy2(observer/'receipt.json',OUT/'observer-neutrality.json')
    shutil.copy2(observer/'build.json',OUT/'observer-build.json')
    shutil.copy2(log,OUT/'wepp_observe.log')
    shutil.copy2(ROOT/'executed_runner.py',OUT/'version-trace-runner.py')
    patches=[]
    original=Path('/home/workdir/wepp-forest-release-20261009/src')
    for name in ['wshchr.for','wepp_observe.for']:
        diff=subprocess.run(['diff','-u','--label',f'a/src/{name}','--label',f'b/src/{name}',str(original/name),str(ROOT/'observer-source'/name)],capture_output=True,text=True)
        assert diff.returncode==1
        patches.append(diff.stdout)
    (OUT/'observer-only.patch').write_text(''.join(patches))
    sources={}
    for name in ['chrqin.for','eqroot.for','mixpass.for']:
        assert sha(original/name)==sha(ROOT/'observer-source'/name)
        sources[name]=sha(original/name)
    save(OUT/'probe-build.json',dict(probe_sha256=sha(ROOT/'chrqin_probe'),
        source_sha256=sources,compiler='/usr/bin/gfortran 13.3.0',
        flags='-fno-align-commons -mcmodel=medium -g -fbacktrace -O2 -ffixed-form -ffixed-line-length-72 -ffpe-trap=invalid,zero,overflow -finit-local-zero -no-pie',
        linked_objects=['chrqin.o','eqroot.o','mixpass.o'],scope='Actual unchanged production routines, not a surrogate model'))
    save(OUT/'manifest.json',{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()})
    probe=HERE/'artifacts/source-probe'
    save(probe/'manifest.json',{p.name:sha(p) for p in sorted(probe.iterdir()) if p.is_file() and p.name!='manifest.json'})
    print('Preserved observer-only patch, exact parity receipts, paired versions and actual-routine probe provenance.')


if __name__=='__main__':
    main()
