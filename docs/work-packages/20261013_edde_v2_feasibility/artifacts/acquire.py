"""Bounded reproducible multidecade acquisition; one process per model/scenario.

Run with the repository virtualenv from the repository root. Large cached NetCDF
objects stay in scratch; small point tables and source manifests are retained.
"""
import argparse
import json
from pathlib import Path
import resource
import time

from wepppy.climates.edde.client import EddeClient, Point, sha256, write_json

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/home/workdir/wepppy-scratch/edde-v2-20261013')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model', choices=['WRF-MPI','WRF-Nor'])
    parser.add_argument('scenario', choices=['Historical','SSP2-4.5','SSP3-7.0'])
    parser.add_argument('--first', type=int, required=True)
    parser.add_argument('--last', type=int, required=True)
    args = parser.parse_args()
    records = json.loads((HERE/'location-eligibility.json').read_text())
    points = [Point(r['name'],r['longitude'],r['latitude']) for r in records
              if r['model']==args.model and r['eligible']]
    root = HERE/'queries'/args.model/args.scenario
    root.mkdir(parents=True,exist_ok=True)
    client = EddeClient(SCRATCH/'cache'/args.model/args.scenario)
    for year in range(args.first,args.last+1):
        csv, manifest = root/f'{year}.csv', root/f'{year}.json'
        if manifest.exists():
            saved=json.loads(manifest.read_text())
            if saved['status']=='complete' and sha256(csv)==saved['daily_sha256']:
                print(args.model,args.scenario,year,'verified resume',flush=True)
                continue
        write_json(manifest,dict(status='incomplete',year=year))
        started=time.monotonic()
        table, meta=client.query(points,args.model,args.scenario,f'{year}-01-01',f'{year}-12-31',
                                 ['prday','tsmax','tsmin'])
        table.to_csv(csv,index=False)
        meta.update(daily_sha256=sha256(csv),wall_seconds=time.monotonic()-started,
                    process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        write_json(manifest,meta)
        print(args.model,args.scenario,year,len(table),round(meta['wall_seconds'],2),flush=True)


if __name__=='__main__': main()
