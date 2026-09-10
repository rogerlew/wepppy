"""Reproduce genuine Wallow CLI/NOAA result acceptance from immutable local snapshots.

Run with wctl run-python <this-file> <fresh-output>.
No acquisition, controller loading, rebuild or publication.
"""
import argparse
import json
import math
from pathlib import Path
import resource
import time

from wepppy.nodb.mods.postfire_debris_flow.rainfall_io import digest
from wepppy.nodb.mods.postfire_debris_flow.results import (
    RainfallInputs, build_m1_results, open_results, list_events, get_event)
from wepppy.nodb.mods.postfire_debris_flow.staley2017 import probability


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--frequency-source',choices=('cli','noaa'),default='noaa')
    args=parser.parse_args()
    here=Path(__file__).resolve().parent
    inventory=json.loads((here/'source_inventory.json').read_text())
    predecessor=here.parents[1]/'20260909_staley_m1_predictors/artifacts/generated/wallow-rebuilt-final'
    manifest=predecessor/'bundle/manifest.json'
    evidence=predecessor/'evidence.json'
    assert digest(evidence)==inventory['predictor_evidence_sha256']
    assert digest(manifest)==inventory['predictor_manifest_sha256']
    assert json.loads(manifest.read_text())['predictors']==json.loads(evidence.read_text())['predictors']
    snapshots={}
    for key,info in inventory['sources'].items():
        p=here/'sources'/Path(key).name
        assert digest(p)==info['sha256']
        snapshots[str(p)]=info['sha256']
    inputs=RainfallInputs(manifest,here/'sources/wepp_cli.parquet',
                         {str(manifest):inventory['predictor_manifest_sha256'],**snapshots},'woolen-refusal',
                         'ClimateMode.PRISM (5), CLIGEN 2015 station az020159',
                         'simulation_labels','Wallow final 2011-06-23 / prefire 2011-05-30',
                         cli_frequency_csv=here/'sources/wepp_cli_pds_mean_metric.csv',
                         noaa_csv=here/'sources/atlas14_intensity_pds_mean_metric.csv')
    start=time.perf_counter()
    m=build_m1_results(inputs,args.output,frequency_source=args.frequency_source,return_intervals=[1,2,5,10],
                       durations=[15,30,60],target_probabilities=[.5,.75])
    build_seconds=time.perf_counter()-start
    start=time.perf_counter();c=open_results(args.output,expected_manifest_sha256=digest(args.output/'manifest.json'))
    open_seconds=time.perf_counter()-start
    start=time.perf_counter();page=list_events(c,duration_minutes=15,sort='probability',descending=True,limit=5)
    list_seconds=time.perf_counter()-start
    start=time.perf_counter();detail=get_event(c,page['rows'][0]['event_id'])
    detail_seconds=time.perf_counter()-start
    values={k:v['value'] for k,v in m['predictor_snapshot']['predictors'].items()}
    for row in detail['rows']:
        assert math.isclose(row['rainfall_mm'],row['intensity_mm_per_hour']*row['duration_minutes']/60,rel_tol=1e-14)
        assert row['probability']==probability('M1',row['duration_minutes'],**values,rainfall_mm=row['rainfall_mm'])
    # Independently evaluated published 15-minute equation for a NOAA 1-year storm.
    import pyarrow.parquet as pq
    design=pq.read_table(args.output/'design.parquet').to_pylist()
    d=design[0]
    if args.frequency_source=='noaa':
        assert d['rainfall_mm']==56*.25==14
    q=.41*values['T']+.67*values['F']+.70*values['S']
    independent=1/(1+math.exp(-(-3.63+d['rainfall_mm']*q)))
    assert math.isclose(d['probability'],independent,rel_tol=1e-14)
    report={'source_inventory_sha256':digest(here/'source_inventory.json'),
            'result_manifest_sha256':digest(args.output/'manifest.json'),'tables':m['tables'],
            'build_seconds':build_seconds,'open_seconds':open_seconds,'list_seconds':list_seconds,
            'detail_seconds':detail_seconds,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'example_page':page,'example_detail':detail,'first_design_scenario':d,
            'limitations':['Fixed current predictors applied to synthetic climate events; no recovery forecast',
                           'Genuine NOAA frequency snapshot, not observed events','Local snapshot identity, no live controller freshness']}
    (args.output/'acceptance.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('tables','build_seconds','open_seconds','list_seconds','detail_seconds','peak_rss_kib')}))


if __name__=='__main__':main()
