"""Recheck native artifacts and summarize prepared-soil experiment comparisons."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import json
from pathlib import Path
import experiment as e
b=e.b
METRICS=('sediment_export_kg_yr','spatial_net_loss_kg_yr','runoff_mm_yr')


def verify(folder):
    r=json.loads((folder/'record.json').read_text())
    if r['status']!='completed':raise ValueError(f'Incomplete case {folder}: {r.get("error")}')
    for group,directory in [('inputs','runs'),('outputs','output')]:
        for name,sha in r[group].items():
            if b.digest(folder/directory/name)!=sha:raise ValueError(f'Artifact changed: {folder}/{directory}/{name}')
    fresh=b.parse_loss(folder/'output/H1.loss.dat',r['width_m'])
    # Earlier execution records predate the additive annual-mean delta field.
    # Every recorded metric must still match, and fresh parsing enforces the gate.
    if any(key not in fresh or fresh[key]!=value for key,value in r['metrics'].items()):
        raise ValueError('Parsed loss differs from record')
    r['metrics']=fresh
    return r


def verify_case(task):
    root,batch,case,calendar=task
    name='-'.join(case.values());r=verify(root/batch/name)
    if r['case']!=case:raise ValueError('Case identity mismatch')
    if b.validate_wat(root/batch/name/'output/H1.wat.dat',calendar)!=r['wat_rows']:
        raise ValueError('WAT calendar changed')
    return name,r


def main(root,batch,dest,workers=8):
    dest.mkdir(exist_ok=False,parents=True)
    declared=json.loads((root/batch/'declaration.json').read_text())
    manifest=json.loads((root/'inputs/manifest.json').read_text())
    if b.digest(root/'inputs/manifest.json')!=declared['manifest_sha256']:raise ValueError('Manifest changed')
    tasks=[(root,batch,case,manifest['climates'][case['climate']]) for case in declared['cases']]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        records=dict(pool.map(verify_case,tasks))
    references={}
    rows=[]
    for name,r in records.items():
        c=r['case']
        if c['binary']!='modern':continue
        prefix='-'.join(c[k] for k in ('climate','soil','design','surface','traffic'))
        refname=prefix+'-legacy-legacy'
        if refname not in references:
            references[refname]=records.get(refname) or verify(e.OLD/'validation-v4'/refname)
        ref=references[refname]
        # Soil/binary may differ; climate, geometry, management and prompts must match.
        for key in ('p1.cli','p1.slp','p1.man','p1.run'):
            if r['inputs'][key]!=ref['inputs'][key]:raise ValueError(f'Pair input mismatch: {key}')
        row=dict(c,name=name,reference=refname,heldout=c['soil']=='holdout')
        for key in METRICS:
            v,base=r['metrics'][key],ref['metrics'][key]
            row[key]=v;row['ref_'+key]=base;row['delta_'+key]=v-base
            row['ratio_'+key]=v/base if base>0 else None
            row['within_'+key]=0.1<=v/base<=10 if base>0 else None
        row.update({f'pass_{k}':v for k,v in r.get('native',{}).items()})
        rows.append(row)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (dest/'comparisons.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    summary={}
    for variant in sorted({r['variant'] for r in rows}):
        selected=[r for r in rows if r['variant']==variant]
        groups={'all':selected,'holdout':[r for r in selected if r['heldout']]}
        groups.update({f'climate:{key}':[r for r in selected if r['climate']==key] for key in manifest['climates']})
        groups.update({f'soil:{key}':[r for r in selected if r['soil']==key] for key in manifest['soils']})
        groups.update({f'design:{key}':[r for r in selected if r['design']==key] for key in ('inbare','inveg','outrut','outunrut')})
        summary[variant]={}
        for group,items in groups.items():
            stats={'cases':len(items)}
            for key in METRICS:
                positive=[r for r in items if r['ref_'+key]>0]
                stats[key]={'positive_reference':len(positive),'within':sum(r['within_'+key] for r in positive),
                            'zero_to_positive':sum(r['ref_'+key]==0 and r[key]>0 for r in items),
                            'both_zero':sum(r['ref_'+key]==0 and r[key]==0 for r in items),
                            'max_absolute_difference':max((abs(r['delta_'+key]) for r in items),default=None)}
            summary[variant][group]=stats
    b.dump(dest/'summary.json',summary)
    b.dump(dest/'evidence.json',{'declaration':declared,'manifest_sha256':b.digest(root/'inputs/manifest.json'),
                               'analyzer_sha256':b.digest(__file__),'records':list(records.values()),
                               'references':list(references.values())})
    for variant,groups in summary.items():
        print(variant,groups['all']['sediment_export_kg_yr'],flush=True)
    print(f'Verified {len(records)} native cases and {len(references)} references',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=e.ROOT)
    parser.add_argument('--batch',default='diagnostic-v1')
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args();main(args.root,args.batch,args.destination,args.workers)
