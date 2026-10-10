#!/usr/bin/env python3
"""Preserve the user-supplied same-input old-release comparison, read-only."""
import hashlib
import json
from pathlib import Path
import shutil

import pandas as pd
from wepppy.all_your_base.stats import weibull_series

HERE=Path(__file__).resolve().parent
OUT=HERE/'artifacts/260803-comparison'
OLD=Path('/wc1/runs/ei/eighty-five-synthetic')
NEW=Path('/wc1/runs/sc/scrawny-relay')
FROZEN=HERE.parents[1]/'investigations/2026-10-09-watershed-return-period-comparisons/artifacts/snapshot'
HILL_SHA='86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7'
WS_SHA='4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def content(p):
    return [s.strip() for s in p.read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    identities=[];events=[];periods=[]
    for scenario,suffix in [('burned',''),('undisturbed','_pups/omni/scenarios/undisturbed')]:
        old=OLD/suffix;new=NEW/suffix;inputs={};comments=[]
        for ext in ['cli','slp','man','sol','chn','str','run']:
            a={p.name:p for p in (old/'wepp/runs').glob('*.'+ext)}
            b={p.name:p for p in (new/'wepp/runs').glob('*.'+ext)}
            assert a.keys()==b.keys()
            for name in a:
                ha,hb=sha(a[name]),sha(b[name])
                if ha!=hb:
                    assert ext=='sol' and content(a[name])==content(b[name]),name
                    comments.append(name)
                inputs[name]=dict(old_sha256=ha,new_sha256=hb)
        for name in ['chan.inp','wepp_ui.txt','pmetpara.txt','snow.txt','gwcoeff.txt','tc.txt']:
            a=old/'wepp/runs'/name;b=new/'wepp/runs'/name
            assert sha(a)==sha(b);inputs[name]=dict(old_sha256=sha(a),new_sha256=sha(b))
        logs={}
        for wid in range(1,285):
            p=old/'wepp/runs'/f'p{wid}.err';t=p.read_text()
            assert HILL_SHA in t and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in t
            logs[p.name]=sha(p)
        p=old/'wepp/runs/pw0.err';t=p.read_text()
        assert WS_SHA in t and 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in t
        logs[p.name]=sha(p)
        p=old/'wepp/output/interchange/ebe_pw0.parquet'
        target=OUT/f'260803-{scenario}-ebe.parquet';before=sha(p)
        shutil.copy2(p,target);assert sha(target)==before==sha(p)
        original=FROZEN/f'topanga_gridmet_261009_{scenario}.parquet'
        assert sha(new/'wepp/output/interchange/ebe_pw0.parquet')==sha(original)
        identities.append(dict(scenario=scenario,old_project=str(old),new_project=str(new),
            old_snapshot=target.name,old_ebe_sha256=before,new_frozen_ebe_sha256=sha(original),
            old_hillslope_binary_sha256=HILL_SHA,old_watershed_binary_sha256=WS_SHA,
            old_execution_header=t.splitlines()[:2],successful_old_hillslope_logs=284,
            log_sha256=logs,input_sha256=inputs,comment_only_soil_differences=comments))
        for version,path in [('260803',target),('261009',original)]:
            f=pd.read_parquet(path)
            assert len(f)==16437 and set(f.year)==set(range(1980,2025))
            window=f.loc[f.year.eq(1993)&f.month.eq(1)&f.day_of_month.between(16,20)].copy()
            window.insert(0,'scenario',scenario);window.insert(0,'version',version);events.append(window)
            indices=weibull_series([2,5,10,20,25],45,gringorten_correction=True,days_per_year=len(f)/45)
            for metric in ['runoff_volume','peak_runoff']:
                ordered=f.sort_values([metric,'sim_day_index'],ascending=[False,True]).reset_index(drop=True)
                for interval,index in indices.items():
                    row=ordered.iloc[index]
                    periods.append(dict(version=version,scenario=scenario,interval=interval,
                        measure=metric,value=float(row[metric])/(9720.29631 if metric=='runoff_volume' else 1),
                        units='mm' if metric=='runoff_volume' else 'm3/s',year=int(row.year),
                        month=int(row.month),day=int(row.day_of_month)))
    pd.concat(events).to_csv(OUT/'january16-20.csv',index=False)
    pd.DataFrame(periods).to_csv(OUT/'return-periods.csv',index=False)
    (OUT/'provenance.json').write_text(json.dumps(identities,indent=2)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in sorted(OUT.iterdir())},indent=2)+'\n')
    print('Verified both scenarios: matching effective inputs, 568 old-build hillslope logs, two watershed logs and frozen-new-result identities.')


if __name__=='__main__':
    main()
