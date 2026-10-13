"""Canadian point-climate smoke tests on a frozen U.S. hillslope (not Canadian projects)."""
import argparse
import json
from pathlib import Path

from wepppy.climates.cligen import CligenStationsManager
from wepppy.climates.edde.cligen import build_climate
from wepppy.climates.edde.client import DataQualityError,write_json
from workflows import HERE,ROOT,OLD,load_series,execute


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--years',type=int,default=20)
    parser.add_argument('--tag',default='full');args=parser.parse_args()
    sites=json.loads((OLD/'manifest.json').read_text())['sites']
    fixture=next(s for s in sites if s['site']=='apostolic-saw-h122')
    manager=CligenStationsManager();summary=[]
    for model in ['WRF-MPI','WRF-Nor']:
        for scenario,first in [('Historical',1995),('SSP2-4.5',2060)]:
            for point in ['Vancouver','Calgary','Edmonton','Winnipeg','Toronto','Montreal','Quebec','Halifax']:
                table,meta=load_series(model,scenario,first,first+args.years-1,point)
                location=next(p for p in meta[0]['points'] if p['name']==point)
                station=manager.get_closest_station((location['longitude'],location['latitude']))
                root=ROOT/f'canadian-{args.tag}'/model/scenario/point
                record=dict(model=model,scenario=scenario,point=point,station=station.par,
                            station_distance_km=station.distance,
                            limitation='U.S. station auxiliary weather and frozen U.S. hillslope; not a Canadian watershed acceptance test')
                try:
                    result=build_climate(table,meta,station,root/'climate',seed=1001)
                    record['generation']=dict(days=result['days'],maximum_source_error=result['maximum_source_error'])
                    record['execution']=execute(fixture,root/'climate/wepp.cli',root/'wepp',args.years)
                    record['status']='complete'
                except (DataQualityError,RuntimeError) as error:
                    # Keep scientific/consumer rejection explicit while testing remaining locations.
                    record.update(status='rejected',error=str(error))
                summary.append(record)
                write_json(HERE/f'canadian-workflows-{args.tag}.json',summary)
                print(model,scenario,point,record['status'],flush=True)


if __name__=='__main__':main()
