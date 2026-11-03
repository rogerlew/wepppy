"""Read immutable seed results; report engine differences without causal fitting."""
from collections import Counter
from pathlib import Path
import json
import math
import rebaseline_r7_seeds as seeds


def classify(row):
    if row['within']:
        return 'meaningful_pass' if row['meaningful'] else 'small_pass'
    if not row['meaningful']:
        return 'small_exceedance'
    return 'meaningful_low' if row['export_kg_yr'] < .1*row['reference_kg_yr'] else 'meaningful_high'


def main():
    root=seeds.ROOT
    rows=seeds.read(root/'results.json')
    summary=seeds.read(root/'summary.json')
    assert summary['results_sha256']==seeds.sha(root/'results.json')
    accepted=summary['seed_comparability_gate']
    assert accepted == (all(r['completed'] and r['physical_pass'] and r.get('particle_pass',False) and r.get('pass_completeness',False) for r in rows) and all(not r['changed_outputs'] for r in rows if r['version']=='r4'))
    assert len(rows)==36 and all(r['completed'] for r in rows)
    pairs={}
    for row in rows:
        seeds.common.verify_files(Path(row['folder']),row)
        key=(row['stratum'],row['lane'])
        assert row['version'] not in pairs.setdefault(key,{})
        pairs[key][row['version']]=row
    contrasts=[]
    for (stratum,lane),versions in sorted(pairs.items()):
        old,new=versions['r4'],versions['r7']
        assert old['inputs']==new['inputs'] and old['reference_kg_yr']==new['reference_kg_yr']
        water=[];sediment=[]
        for row in (old,new):
            assert len(row['audit']['water']['ofes'])==len(row['audit']['sediment']['ofes'])==3
        for before,after in zip(old['audit']['water']['ofes'],new['audit']['water']['ofes']):
            assert before.keys()==after.keys()
            water.append({key:after[key]-before[key] for key in before})
        for before,after in zip(old['audit']['sediment']['ofes'],new['audit']['sediment']['ofes']):
            assert before.keys()==after.keys()
            sediment.append({key:after[key]-before[key] for key in before})
        contrasts.append(dict(stratum=stratum,lane=lane,case=new['case'],
            reference_kg_yr=new['reference_kg_yr'],r4_kg_yr=old['export_kg_yr'],r7_kg_yr=new['export_kg_yr'],
            delta_export_kg_yr=new['export_kg_yr']-old['export_kg_yr'],
            r4_class=classify(old),r7_class=classify(new),
            r4_ratio=old['export_kg_yr']/old['reference_kg_yr'] if old['reference_kg_yr'] else None,
            r7_ratio=new['export_kg_yr']/new['reference_kg_yr'] if new['reference_kg_yr'] else None,
            r7_changed_outputs=new['changed_outputs'],water_ofe_deltas=water,sediment_ofe_deltas=sediment,
            full_water_closure_claim=False))
    counts={}
    for lane in sorted({r['lane'] for r in rows}):
        for version in ('r4','r7'):
            selected=[r for r in rows if r['lane']==lane and r['version']==version]
            positive=[math.log10(r['export_kg_yr']/r['reference_kg_yr']) for r in selected if r['export_kg_yr']>0 and r['reference_kg_yr']>0]
            counts[f'{lane}/{version}']=dict(classes=dict(Counter(classify(r) for r in selected)),
                mean_log10_ratio_positive_only=sum(positive)/len(positive) if positive else None,
                positive_ratio_count=len(positive),zero_reference_count=sum(r['reference_kg_yr']==0 for r in selected),
                zero_export_count=sum(r['export_kg_yr']==0 for r in selected))
    result=dict(results_sha256=seeds.sha(root/'results.json'),interpretation_driver_sha256=seeds.sha(__file__),
        summary=summary,interpretation_status='comparability_passed' if accepted else 'diagnostic_only_gate_failed',
        counts=counts,contrasts=contrasts,
        scope='Selected diagnostic seeds only; total engine-bundle effects; no FC/HK attribution, parameter acceptance or complete water closure')
    path=root/'interpretation.json'
    assert not path.exists()
    seeds.save(path,result)
    print(result['interpretation_status'])
    print(json.dumps(counts,indent=2))
    for row in contrasts:
        print(row['stratum'],row['lane'],row['r4_kg_yr'],row['r7_kg_yr'],row['r4_class'],row['r7_class'])


if __name__=='__main__':
    main()
