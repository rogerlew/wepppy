"""Retain, quantify and report upstream coupling after the strict check failed."""
import argparse
import json
from pathlib import Path
import shutil

import experiment as e


def differences(reference, changed, fields):
    if set(reference)!=set(changed):raise ValueError('Comparison calendar mismatch')
    result=[]
    for ofe in (1,2):
        values={}
        for field in fields:
            deltas=[changed[day][ofe][field]-reference[day][ofe][field] for day in sorted(reference)]
            values[field]=dict(changed_days=sum(v!=0 for v in deltas),max_abs=max(abs(v) for v in deltas),sum_delta=sum(deltas))
        result.append(values)
    return result


def reconcile(root):
    import pyarrow.parquet as pq
    dest=root/'reconciliation-v2';dest.mkdir(exist_ok=False)
    shutil.copyfile(__file__,dest/'executed-reconcile.py')
    records=json.loads((root/'runs/summary.json').read_text())
    fields=('P','RM','Q','Ep','Es','Er','Dp','UpStrmQ','SubRIn','latqcc','SoilWaterTotal','ProfileDepth','ProfilePorosityCap','ProfileFCStore','ProfileWPStore')
    results=[];coupling=[];sources={}
    for profile in e.PANEL:
        control=profile+'--current--same'
        w0=e.a.grouped(pq.read_table(root/'runs'/control/'output/interchange/H.wat.parquet').to_pylist(),fields)
        er0=e.a.grouped(pq.read_table(root/'runs'/control/'output/interchange/H.element.parquet').to_pylist(),('SedLeave','PeakRO','EffDur'))
        for record in [r for r in records if r['profile']==profile]:
            name=record['name'];folder=root/'runs'/name
            path=root/'analysis'/(name+'.json')
            result=json.loads(path.read_text());sources[str(path)]=e.a.digest(path)
            if result['record']!=record:raise ValueError('Partial analysis record mismatch')
            for sub,key in [('runs','inputs'),('output','outputs')]:
                for filename,sha in record[key].items():
                    if e.a.digest(folder/sub/filename)!=sha:raise ValueError('Native artifact drift')
            w=e.a.grouped(pq.read_table(folder/'output/interchange/H.wat.parquet').to_pylist(),fields)
            er=e.a.grouped(pq.read_table(folder/'output/interchange/H.element.parquet').to_pylist(),('SedLeave','PeakRO','EffDur'))
            diff=differences(w0,w,fields)
            sediment=[]
            for ofe in (1,2):
                dates=set(er)|set(er0)
                delta=[er.get(day,{}).get(ofe,{}).get('SedLeave',0)-er0.get(day,{}).get(ofe,{}).get('SedLeave',0) for day in sorted(dates)]
                common=set(er)&set(er0)
                sediment.append(dict(changed_dates=sum(v!=0 for v in delta),sum_delta_kg_m=sum(delta),max_abs_kg_m=max(abs(v) for v in delta),
                                     max_common_peakro_delta_mm_hr=max(abs(er[d][ofe]['PeakRO']-er0[d][ofe]['PeakRO']) for d in common),
                                     max_common_effdur_delta_hr=max(abs(er[d][ofe]['EffDur']-er0[d][ofe]['EffDur']) for d in common)))
            exact=all(v['changed_days']==0 for o in diff for v in o.values()) and all(v['changed_dates']==0 for v in sediment)
            coupling.append(dict(name=name,upstream_exact=exact,water=diff,sediment=sediment,
                                 element_date_symmetric_difference=len(set(er)^set(er0))))
            result['upstream_exact']=exact
            results.append(result)
    same_grid=[]
    for profile in e.PANEL:
        for conductivity in ('current','source'):
            selected=[r for r in records if r['profile']==profile and r['drainage']==conductivity]
            control=next(r for r in selected if r['depth']=='same');plus=next(r for r in selected if r['depth']=='plus')
            exact=control['outputs']==plus['outputs']
            if not exact:raise ValueError('Same-grid negative control failed')
            same_grid.append(dict(profile=profile,drainage=conductivity,native_outputs_identical=True))
    references=[]
    for profile in e.PANEL:
        current=json.loads((root/'inputs'/profile/'prior-record.json').read_text())
        folder=e.PRIOR/'factorial-v1'/(profile+'-legacy-legacy')
        record=json.loads((folder/'record.json').read_text())
        for sub,key in [('runs','inputs'),('output','outputs')]:
            for filename,sha in record[key].items():
                if e.a.digest(folder/sub/filename)!=sha:raise ValueError('Reference artifact drift')
        for key in ('p1.man','p1.slp','p1.cli','p1.run'):
            if record['inputs'][key]!=current['inputs'][key]:raise ValueError('Unmatched reference scenario')
        references.append(dict(profile=profile,path=str(folder/'record.json'),sha256=e.a.digest(folder/'record.json'),binary=record['binary']))
    declaration=json.loads((root/'declaration.json').read_text())
    if e.a.digest(declaration['binary']['path'])!=declaration['binary']['sha256']:raise ValueError('Binary drift')
    e.a.dump(dest/'results.json',results);e.a.dump(dest/'upstream-coupling.json',coupling)
    e.a.dump(dest/'same-grid-controls.json',same_grid);e.a.dump(dest/'legacy-reference-provenance.json',references)
    e.a.dump(dest/'partial-analysis-hashes.json',sources)
    e.a.dump(dest/'acceptance.json',dict(native_runs=len(results),control_replays=sum(r.get('control_reproduced',False) for r in results),
                                        depth_readbacks=24,upstream_input_invariance=24,upstream_output_exact=sum(r['upstream_exact'] for r in results),
                                        same_grid_pairs=8,report_reconciled=sum(r['sediment']['report_reconciled'] for r in results),
                                        ebe_mismatch_events=sum(len(r['ebe']['mismatches']) for r in results),production_candidate_accepted=False))
    print((dest/'acceptance.json').read_text())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();reconcile(args.root)
