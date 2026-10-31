"""Report unchanged acceptance gates, including every native failure."""
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import statistics
import continuation as c
b=c.b


def summarize(records):
    def group(rows):
        meaningful=[r for r in rows if r.get('reference_kg_yr',0)>1]
        small=[r for r in rows if 'reference_kg_yr' in r and r['reference_kg_yr']<=1]
        ratios=[r['export_kg_yr']/r['reference_kg_yr'] for r in meaningful if r.get('export_kg_yr',0)>0]
        return dict(cases=len(rows),numerical_pass=sum(r['within'] for r in rows),physical_pass=sum(r['physical_pass'] for r in rows),
            native_failures=sum(r['status']!='completed' for r in rows),
            meaningful_cases=len(meaningful),meaningful_pass=sum(r['within'] for r in meaningful),
            small_cases=len(small),small_pass=sum(r['within'] for r in small),
            min_positive_ratio=min(ratios) if ratios else None,max_positive_ratio=max(ratios) if ratios else None,
            median_positive_ratio=statistics.median(ratios) if ratios else None,
            mean_log10_positive_ratio=statistics.mean(math.log10(v) for v in ratios) if ratios else None,
            completed_zero_for_meaningful=sum(r.get('export_kg_yr')==0 for r in meaningful),
            missing_reference=sum('reference_kg_yr' not in r for r in rows))
    result=dict(overall=group(records),strata={},intersections={})
    for dimension in ('climate','soil','design','surface','traffic','variant'):
        groups=defaultdict(list)
        for r in records:groups[r['case'][dimension]].append(r)
        result['strata'][dimension]={key:group(rows) for key,rows in groups.items()}
    groups=defaultdict(list)
    for r in records:
        groups['/'.join(r['case'][k] for k in ('climate','soil','design','surface','traffic'))].append(r)
    result['intersections']={key:group(rows) for key,rows in groups.items()}
    result['failures']=[dict(case=r['case'],status=r['status'],within=r['within'],physical_pass=r['physical_pass'],
                             export_kg_yr=r.get('export_kg_yr'),reference_kg_yr=r.get('reference_kg_yr')) for r in records if not r['within'] or not r['physical_pass']]
    result['equal_material_pass_fraction']=statistics.mean(g['numerical_pass']/g['cases'] for g in result['strata']['soil'].values())
    result['final_scientific_acceptance']=False
    result['acceptance_deferred_reason']='Daily coupling limitation, production/full-project and withheld gates remain unresolved.'
    return result


def main():
    for name in ('rebaseline-v1','development-pilot-v1','cap-only-v1','development-matrix-v1','exact-legacy-v1'):
        root=c.ROOT/name
        if not (root/'results.json').exists():continue
        records=json.loads((root/'results.json').read_text())
        # Failed rebaseline controls also need reference membership for group denominators.
        for r in records:
            if 'reference_kg_yr' not in r:
                case=r['case'];profile='-'.join(case[k] for k in ('climate','soil','design','surface','traffic'))
                ref=b.DEFAULT_ROOT/'validation-v4'/f'{profile}-legacy-legacy/record.json'
                rr=json.loads(ref.read_text());c.e.a.s.check_files(ref.parent,rr)
                r['reference_kg_yr']=rr['metrics']['sediment_export_kg_yr']
        summary=summarize(records)
        b.dump(root/'stratified-summary.json',summary);b.dump(c.HERE/f'{name}-stratified.json',summary)
        print(name,summary['overall'],flush=True)


if __name__=='__main__':main()
