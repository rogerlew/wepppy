"""Publish a compact comparison only after all declared cases validate."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
from functools import partial
import json
import math
from pathlib import Path
import statistics
import shutil
import benchmark as b

METRICS=('sediment_export_kg_yr','spatial_net_loss_kg_yr','runoff_mm_yr')
FACTORS=('climate','soil','design','surface','traffic')


def verify_case(root, manifest, batch, case):
    d=root/batch/'-'.join(case.values())
    record=json.loads((d/'record.json').read_text())
    if record['case']!=case:
        raise ValueError('Case identity mismatch')
    for sub,key in [('runs','inputs'),('output','outputs')]:
        for name,expected in record[key].items():
            if b.digest(d/sub/name)!=expected:
                raise ValueError(f'Changed consumed artifact: {d/sub/name}')
    if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (d/'runs/stdout').read_text():
        raise ValueError(f'Native failure: {d}')
    metrics=b.parse_loss(d/'output/H1.loss.dat',record['width_m'])
    wat_rows=b.validate_wat(d/'output/H1.wat.dat',manifest['climates'][case['climate']])
    return dict(case=case,metrics=metrics,wat_rows=wat_rows,area_m2=record['modeled_area_m2'],
                record_sha256=b.digest(d/'record.json'),inputs=record['inputs'],outputs=record['outputs'])


def classify(candidate,reference):
    if reference==0:
        return None,'both_zero' if candidate==0 else 'reference_zero'
    ratio=candidate/reference
    return ratio,'within_factor_10' if .1<=ratio<=10 else 'below' if ratio<.1 else 'above'


def summary(rows):
    result={'count':len(rows)}
    for metric in METRICS:
        ratios=[r[metric+'_ratio'] for r in rows if r[metric+'_ratio'] is not None]
        groups=defaultdict(int)
        for r in rows:
            groups[r[metric+'_class']]+=1
        result[metric] = dict(groups,ratio_min=min(ratios) if ratios else None,
                             ratio_median=statistics.median(ratios) if ratios else None,
                             ratio_max=max(ratios) if ratios else None)
    return result


def publish(root,batch,destination,workers=8):
    manifest=json.loads((root/'inputs/manifest.json').read_text())
    cases=json.loads((root/batch/'cases.json').read_text())
    expected=list(b.matrix('validate',['generated','road_combined','all_combined','cloud_legacy']))
    if cases != expected:
        raise ValueError('Declared cases differ from the complete validation matrix')
    execution=json.loads((root/batch/'execution.json').read_text())
    if b.digest(root/batch/'execution-script.py')!=execution['harness_sha256']:
        raise ValueError('Execution source identity mismatch')
    if b.digest(root/'inputs/manifest.json')!=execution['manifest_sha256']:
        raise ValueError('Input manifest changed')
    for info in manifest['binaries'].values():
        if b.digest(info['path'])!=info['sha256']:
            raise ValueError('Pinned binary changed')
    for name,expected_hash in manifest['reference_templates'].items():
        if b.digest(root/name)!=expected_hash:
            raise ValueError('Reference template changed')
    for name,expected_hash in manifest['sources'].items():
        if b.digest(b.REPO/name)!=expected_hash:
            raise ValueError('Production builder source changed')
    resume=None
    if (root/batch/'resume.json').exists():
        resume=json.loads((root/batch/'resume.json').read_text())
        if b.digest(root/batch/'resume-execution-script.py')!=resume['harness_sha256']:
            raise ValueError('Resume execution source identity mismatch')
        for name,expected_hash in resume['completed_record_sha256'].items():
            if b.digest(root/batch/name/'record.json')!=expected_hash:
                raise ValueError('Previously completed record changed during resume')
    for name, info in manifest['soils'].items():
        if b.digest(root/'inputs/soils'/f'{name}.sol')!=info['sha256']:
            raise ValueError('Soil input changed')
    for name, info in manifest['climates'].items():
        if b.digest(root/'inputs/climates'/f'{name}.cli')!=info['sha256']:
            raise ValueError('Climate input changed')
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows=list(pool.map(partial(verify_case,root,manifest,batch),cases))
    key=lambda r:tuple(r['case'][k] for k in FACTORS)
    references={key(r):r for r in rows if r['case']['binary']=='legacy'}
    if len(references)*6 != len(cases) or len({tuple(c.values()) for c in cases}) != len(cases):
        raise ValueError('Incomplete or duplicate six-lane matrix')
    comparisons=[]
    for r in rows:
        if r['case']['binary']=='legacy':continue
        ref=references[key(r)]
        for name in ('p1.slp','p1.cli','p1.run'):
            if r['inputs'][name] != ref['inputs'][name]:
                raise ValueError(f'Unmatched geometry/climate/run contract: {key(r)} {name}')
        if r['case']['variant'] != 'cloud_legacy' and r['inputs']['p1.man'] != ref['inputs']['p1.man']:
            raise ValueError('Unexpected management change during soil comparison')
        if r['case']['variant'] == 'legacy' and r['inputs']['p1.sol'] != ref['inputs']['p1.sol']:
            raise ValueError('Binary-only control changed soil')
        row=dict(r['case'],area_m2=r['area_m2'],holdout=(r['case']['soil']=='clay' or r['case']['climate']=='charleston'))
        for metric in METRICS:
            value,base=r['metrics'][metric],ref['metrics'][metric]
            ratio,category=classify(value,base)
            row.update({metric:value,metric+'_reference':base,metric+'_ratio':ratio,
                        metric+'_class':category,metric+'_difference':value-base})
        row['reference_near_export_resolution']=ref['metrics']['sediment_export_kg_yr']<=ref['metrics']['export_resolution_kg']
        row['annual_export_min_kg']=min(x['sediment_export_kg'] for x in r['metrics']['annual_export'])
        row['annual_export_max_kg']=max(x['sediment_export_kg'] for x in r['metrics']['annual_export'])
        comparisons.append(row)
    groups={}
    for variant in sorted({r['variant'] for r in comparisons}):
        selected=[r for r in comparisons if r['variant']==variant]
        groups[variant]={'all':summary(selected), 'holdout':summary([r for r in selected if r['holdout']])}
        for factor in FACTORS:
            groups[variant][factor]={value:summary([r for r in selected if r[factor]==value])
                                    for value in sorted({r[factor] for r in selected})}
    destination.mkdir(exist_ok=False)
    with (destination/'comparisons.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(comparisons[0]));writer.writeheader();writer.writerows(comparisons)
    b.dump(destination/'summary.json',groups)
    b.dump(destination/'case-evidence.json',rows)
    b.dump(destination/'provenance.json',dict(root=str(root),batch=batch,cases=len(cases),
        execution=execution,resume=resume,report_sha256=b.digest(__file__),analyzer_sha256=b.digest(b.__file__),
        manifest=manifest,results_sha256=b.digest(root/batch/'results.json'),
        holdout_policy='Charleston and clay loam absent from 96-case screening; all combinations predeclared'))
    shutil.copy2(root/'reproduce/results.json',destination/'reference-reproduction.json')
    shutil.copy2(root/'screen-v2/analysis.json',destination/'screening.json')
    plot(comparisons,destination/'comparison.png')
    print(f'Published {len(cases)} verified cases, {len(comparisons)} comparisons to {destination}',flush=True)


def plot(rows,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    variants=('legacy','generated','road_combined','all_combined','cloud_legacy')
    fig, axes=plt.subplots(2,5,figsize=(16,7),layout='constrained')
    colors={'birmingham':'#0072B2','denver':'#D55E00','flagstaff':'#009E73','charleston':'#CC79A7','site':'#666666'}
    for j,variant in enumerate(variants):
        selected=[r for r in rows if r['variant']==variant]
        for i,metric in enumerate(METRICS[:2]):
            ax=axes[i,j]
            positive=[r for r in selected if r[metric]>0 and r[metric+'_reference']>0]
            for climate,color in colors.items():
                subset=[r for r in positive if r['climate']==climate]
                ax.scatter([r[metric+'_reference'] for r in subset],[r[metric] for r in subset],
                           c=color,s=8,alpha=.5,label=climate)
            values=[v for r in positive for v in (r[metric],r[metric+'_reference'])]
            lo,hi=min(values)*.7,max(values)*1.4
            ax.plot([lo,hi],[lo,hi],color='black',lw=.8)
            ax.fill_between([lo,hi],[lo*.1,hi*.1],[lo*10,hi*10],color='gray',alpha=.12)
            ax.set(xscale='log',yscale='log',xlim=(lo,hi),ylim=(lo,hi))
            ax.set_title(variant.replace('_',' ') + f'\n{len(selected)-len(positive)} zero pairs omitted')
            ax.set_xlabel('wepp2010 reference (kg/year)')
            if j==0:ax.set_ylabel(('Export' if i==0 else 'Spatial net loss')+'\nwepp_261026 (kg/year)')
    axes[0,0].legend(fontsize=7)
    fig.suptitle('Matched geometry and climate; shaded band = factor ten. Spatial net loss is not gross daily detachment.')
    fig.savefig(path,dpi=160)
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=b.DEFAULT_ROOT)
    parser.add_argument('--batch',default='validation-v3')
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args()
    publish(args.root,args.batch,args.destination,args.workers)
