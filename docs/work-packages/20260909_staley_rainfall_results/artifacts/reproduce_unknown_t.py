"""Historical unavailable-T diagnostic; not authentic current-project acceptance."""
import argparse
import json
from pathlib import Path

from wepppy.nodb.mods.postfire_debris_flow.rainfall_io import digest
from wepppy.nodb.mods.postfire_debris_flow.results import RainfallInputs, build_m1_results, open_results, list_events


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    args=parser.parse_args();here=Path(__file__).resolve().parent
    inventory=json.loads((here/'source_inventory.json').read_text())
    manifest=here.parents[1]/'20260909_staley_m1_predictors/artifacts/generated/wallow-final/bundle/manifest.json'
    climate=here/'sources/wepp_cli.parquet'
    hashes={str(manifest):inventory['historical_unknown_t_manifest_sha256'],
            str(climate):inventory['sources']['climate/wepp_cli.parquet']['sha256']}
    inputs=RainfallInputs(manifest,climate,hashes,'historical-Wallow-diagnostic',
                         'ClimateMode.PRISM (5); existing synthetic catalog','simulation_labels',
                         'Historical July 1 unknown-T diagnostic; not current final assessment')
    m=build_m1_results(inputs,args.output,frequency_source='cli',return_intervals=[1,2,5,10],
                       durations=[15,30,60],target_probabilities=[.5,.75])
    c=open_results(args.output,expected_manifest_sha256=digest(args.output/'manifest.json'))
    assert m['predictor_snapshot']['predictors']['T']['value'] is None
    assert set(c.events['reason'].to_pylist())=={'missing_predictors'}
    assert c.events['probability'].null_count==len(c.events)
    report={'manifest_sha256':digest(args.output/'manifest.json'),'rows':len(c.events),
            'predictor_manifest_sha256':hashes[str(manifest)],
            'example':list_events(c,duration_minutes=15,limit=1)['rows'],
            'status':'historical unavailable-state diagnostic only'}
    (args.output/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
