"""Recompute seed probabilities and retain a reproducible manual-review sample."""
from pathlib import Path
from datetime import date
import gzip
import json
import math
import subprocess
import sys
import tempfile

import pandas as pd
from study import ROOT, PAIRS, FOCAL, FLAGS, dump
from peakflow_phase1_replay import packetize, replay

def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,mid-half),min(1,mid+half)]

def analyze():
    seeds=json.loads((ROOT/'seeds.json').read_text())['inference']
    labels=[f'inference-{s:05}' for s in seeds]
    terminals=[json.loads((ROOT/'runs'/label/'terminal.json').read_text()) for label in labels]
    assert len(terminals)==100 and all(t['status']=='complete' for t in terminals)
    tables=[pd.read_parquet(ROOT/'runs'/label/'pairs.parquet') for label in labels]
    pairs=pd.concat(tables,ignore_index=True)
    assert not pairs.duplicated(['seed_label','pair','year','day','ofe','ordinal']).any()
    report=ROOT/'analysis';report.mkdir(exist_ok=False)
    original=pd.read_parquet(ROOT/'runs/original/pairs.parquet')
    signature_columns=['solver_baseline','solver_mutant','forcing_mode_baseline','forcing_mode_mutant']
    signatures=original[['pair','date','ofe','ordinal','peak_gt25pct_runoff_lt5pct',*signature_columns]].rename(columns={c:'original_'+c for c in ['peak_gt25pct_runoff_lt5pct',*signature_columns]})
    pairs=pairs.merge(signatures,on=['pair','date','ofe','ordinal'],how='left',validate='many_to_one')
    matched=pairs.peak_gt25pct_runoff_lt5pct & pairs.original_peak_gt25pct_runoff_lt5pct.fillna(False).astype(bool)
    for c in signature_columns:matched=matched & (pairs[c]==pairs['original_'+c])
    pairs['original_signature_recurred']=matched
    study_flags=(*FLAGS,'original_signature_recurred')
    pairs.to_parquet(report/'event-pairs.parquet',index=False)
    focal=[];any_rows=[];dates=[];overlaps=[]
    for pair in PAIRS:
        group=pairs[pairs.pair==pair]
        for flag in study_flags:
            byseed=group.groupby('seed_label')[flag].any().reindex(labels,fill_value=False)
            count=int(byseed.sum());lo,hi=wilson(count,100)
            any_rows.append({'pair':pair,'flag':flag,'k':count,'n':100,'probability':count/100,'ci95_low':lo,'ci95_high':hi})
            bydate=group.groupby(['date','seed_label'])[flag].any().groupby('date').sum()
            for day,k in bydate.items():
                lo,hi=wilson(int(k),100)
                dates.append({'pair':pair,'flag':flag,'date':day,'k':int(k),'n':100,'probability':int(k)/100,'ci95_low':lo,'ci95_high':hi})
            for day in FOCAL:
                sub=group[group.date==day]
                k=int(sub.groupby('seed_label')[flag].any().sum());lo,hi=wilson(k,100)
                focal.append({'pair':pair,'flag':flag,'date':day,'k':k,'n':100,'probability':k/100,'ci95_low':lo,'ci95_high':hi,'seeds_with_observer_event':sub.seed_label.nunique()})
        original_dates=set(original[(original.pair==pair)&original.peak_gt25pct_runoff_lt5pct].date)
        for label in labels:
            actual=set(group[(group.seed_label==label)&group.peak_gt25pct_runoff_lt5pct].date)
            overlaps.append({'pair':pair,'seed_label':label,'original_flagged_dates':len(original_dates),'retained':len(actual&original_dates),'lost':len(original_dates-actual),'new':len(actual-original_dates),'total_flagged_dates':len(actual)})
    for name,records in [('focal-probabilities',focal),('any-event-probabilities',any_rows),('date-probabilities',dates),('date-overlap',overlaps)]:
        pd.DataFrame(records).to_csv(report/f'{name}.csv',index=False)
    continuous=[]
    for t in terminals:
        for pair,(left,right,_,_) in PAIRS.items():
            for day in FOCAL:
                row={'seed':t['seed'],'pair':pair,'date':day}
                for tag,lane in [('baseline',left),('mutant',right)]:
                    row.update({tag+'_'+k:v for k,v in t['lanes'][lane]['focal'][day].items()})
                continuous.append(row)
    pd.DataFrame(continuous).to_csv(report/'focal-values.csv',index=False)
    summary={'status':'complete','seeds':100,'seed_labels':labels,'event_pairs':len(pairs),
             'distinct_climate_hashes':len({t['climate']['climate_sha256'] for t in terminals}),
             'all_fixed_climate_fields_equal':all(t['climate']['fixed_columns_equal'] for t in terminals),
             'all_observer_identities':sorted({t['observer_sha256'] for t in terminals}),
             'focal_probabilities':[r for r in focal if r['flag']=='peak_gt25pct_runoff_lt5pct'],
             'any_probabilities':[r for r in any_rows if r['flag']=='peak_gt25pct_runoff_lt5pct']}
    dump(report/'summary.json',summary)
    print(json.dumps(summary,indent=2))
    # Deterministic manual sample: original, smallest-seed persistent and lost
    # cases on each primary date. Packet and replay errors remain visible.
    selection=[]
    for pair,day in [('ksat','1980-02-14'),('cover','1986-02-15'),('dense','1986-02-15')]:
        selection.append((pair,day,'original','original'))
        group=pairs[(pairs.pair==pair)&(pairs.date==day)]
        for state in (True,False):
            eligible=group[group.peak_gt25pct_runoff_lt5pct==state].sort_values('seed')
            if len(eligible):selection.append((pair,day,eligible.iloc[0].seed_label,'persistent' if state else 'lost'))
    # Add one new strict-screen date per pair, ranked by frequency then date.
    for pair in PAIRS:
        old=set(original[(original.pair==pair)&original.peak_gt25pct_runoff_lt5pct].date)
        candidates=pd.DataFrame(dates)
        candidates=candidates[(candidates.pair==pair)&(candidates.flag=='peak_gt25pct_runoff_lt5pct')&(~candidates.date.isin(old))&(candidates.k>0)].sort_values(['k','date'],ascending=[False,True])
        if len(candidates):
            day=candidates.iloc[0].date
            g=pairs[(pairs.pair==pair)&(pairs.date==day)&pairs.peak_gt25pct_runoff_lt5pct].sort_values('seed')
            selection.append((pair,day,g.iloc[0].seed_label,'new-date'))
    dump(report/'manual-selection.json',[dict(pair=p,date=d,label=l,reason=r) for p,d,l,r in selection])
    records=[]
    for pair,day,label,reason in selection:
        for lane in PAIRS[pair][:2]:
            eventid=f'{label}-{pair}-{day}-{lane}'
            out=report/'manual'/eventid;out.mkdir(parents=True)
            with tempfile.TemporaryDirectory(prefix='topanga-review-') as temp:
                trace=Path(temp)/'trace.csv'
                with gzip.open(ROOT/'runs'/label/lane/'runs/peak_diag.csv.gz','rb') as source:
                    trace.write_bytes(source.read())
                d=date.fromisoformat(day)
                packet=packetize(trace,d.year,d.timetuple().tm_yday,'wepp-ea25ad79-gate21-observer',eventid,label+'-'+lane,'106',1,1)
                dump(out/'packet.json',packet)
            row={'pair':pair,'date':day,'label':label,'lane':lane,'reason':reason,
                 **packet['scalars'],**packet['production']}
            try:
                result=replay(out/'packet.json',ROOT/'bin/peak_replay')
                dump(out/'replay.json',result)
                row.update({'replay_status':'pass','selected_method_delta_m_s':result['selected_method_delta_m_s'],
                  'legacy_appmth_mm_h':result['legacy_input_replay']['appmth_peak_m_s']*3600000,
                  'legacy_hdrive_mm_h':result['legacy_input_replay']['hdrive_peak_m_s']*3600000,
                  'harmonized_appmth_mm_h':result['harmonized_forcing_diagnostic']['appmth_peak_m_s']*3600000,
                  'legacy_vstar':result['legacy_input_replay']['appmth']['vstar'],
                  'harmonized_vstar':result['harmonized_forcing_diagnostic']['appmth']['vstar']})
            except (AssertionError,ValueError,ZeroDivisionError,OverflowError,RuntimeError,subprocess.CalledProcessError) as e:
                row.update({'replay_status':'unresolved','error':repr(e)})
                dump(out/'replay-failure.json',{'error':repr(e)})
            records.append(row)
    pd.DataFrame(records).to_csv(report/'manual-review.csv',index=False)

if __name__=='__main__':analyze()
