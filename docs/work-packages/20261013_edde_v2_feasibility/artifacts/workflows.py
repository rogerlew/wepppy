"""Generate and execute standalone climate experiments from frozen real hillslopes."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
import pandas as pd

from wepppy.climates.cligen import CligenStationsManager
from wepppy.climates.edde.cligen import build_climate,read_cli,revise_prism
from wepppy.climates.edde.client import DataQualityError,sha256,write_json

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
ROOT=Path('/home/workdir/wepppy-scratch/edde-v2-20261013')
OLD=REPO/'docs/work-packages/20261008_dewpoint_openet/artifacts'
FIXTURES=Path('/home/workdir/wepppy-scratch/dewpoint-openet-20261008/fixtures')
NORMALS=REPO/'docs/work-packages/20261008_prism_stochastic_dewpoint/artifacts/normals.csv'
BINARY=REPO/'wepp_runner/bin/wepp_261010'


def normal(site):
    data=pd.read_csv(NORMALS,skiprows=10)
    data=data[(data.Name==site)&(data.Date!='Annual')]
    if len(data)!=12: raise ValueError('Expected 12 PRISM normals')
    return dict(ppt=data['ppt (mm)'].tolist(),tmax=data['tmax (degrees C)'].tolist(),
                tmin=data['tmin (degrees C)'].tolist(),
                provenance=dict(source=str(NORMALS.relative_to(REPO)),sha256=sha256(NORMALS),
                                period='1991-2020',resolution='800m',site=site,
                                sampling='native cell',units={'ppt':'mm/month','tmax':'C','tmin':'C'}))


def load_series(model,scenario,first,last,point):
    root=HERE/'queries'/model/scenario
    tables,metadata=[],[]
    for year in range(first,last+1):
        meta=json.loads((root/f'{year}.json').read_text())
        csv=root/f'{year}.csv'
        if meta['status']!='complete' or sha256(csv)!=meta['daily_sha256']:
            raise ValueError('Invalid acquisition provenance')
        frame=pd.read_csv(csv)
        tables.append(frame[frame.point==point]); metadata.append(meta)
    return pd.concat(tables,ignore_index=True),metadata


def execute(site,climate,root,years):
    root.mkdir(parents=True,exist_ok=False)
    runs=root/'runs';runs.mkdir();(root/'output').mkdir()
    fixture=FIXTURES/site['site']
    for name,digest in site['source_hashes'].items():
        source=fixture/name
        if sha256(source)!=digest:raise ValueError(f'Frozen fixture changed: {source}')
        shutil.copy2(source,runs/name)
    hill=site['hill']
    shutil.copy2(climate,runs/f'p{hill}.cli')
    control=runs/f'p{hill}.run'
    lines=control.read_text().splitlines();lines[-2]=str(years)
    control.write_text('\n'.join(lines)+'\n')
    consumed={p.name:sha256(p) for p in runs.iterdir() if p.is_file()}
    started=time.monotonic()
    with control.open('rb') as source,(root/'stdout.log').open('wb') as out,(root/'stderr.log').open('wb') as err:
        result=subprocess.run([str(BINARY)],cwd=runs,stdin=source,stdout=out,stderr=err,timeout=180,check=False)
    state=dict(status='incomplete',returncode=result.returncode,seconds=time.monotonic()-started,
               binary=str(BINARY.relative_to(REPO)),binary_sha256=sha256(BINARY),consumed=consumed)
    write_json(root/'execution.json',state)
    if result.returncode or 'WEPP COMPLETED' not in (root/'stdout.log').read_text().upper():
        raise RuntimeError(f'WEPP failed: {root}')
    rows=[]
    for line in (root/'output'/f'H{hill}.wat.dat').read_text().splitlines():
        fields=line.split()
        if len(fields)==25 and fields[0].isdigit():rows.append([float(v) for v in fields])
    data=np.asarray(rows)
    cli=read_cli(runs/f'p{hill}.cli')
    if len(data)!=len(cli) or not np.isfinite(data).all():raise ValueError('WEPP daily output invalid')
    dates=pd.DatetimeIndex(pd.to_datetime(data[:,2].astype(int).astype(str))+pd.to_timedelta(data[:,1]-1,unit='D'))
    if not dates.equals(cli.index):raise ValueError('WEPP date coverage differs from climate')
    # WEPP water output uses 0.01 mm formatting; match consumed precipitation.
    error=float(np.max(abs(data[:,3]-cli.prcp.to_numpy())))
    if error>.011:raise ValueError(f'WEPP precipitation differs: {error}')
    state.update(status='complete',days=len(data),precipitation_max_error_mm=error,
                 annual_p_mm=float(data[:,3].sum()/years),annual_runoff_mm=float(data[:,5].sum()/years),
                 annual_et_mm=float(data[:,6:9].sum()/years),annual_deep_percolation_mm=float(data[:,9].sum()/years),
                 annual_lateral_mm=float(data[:,12].sum()/years),
                 minimum_soil_water_mm=float(data[:,20].min()),maximum_swe_mm=float(data[:,15].max()),
                 outputs={p.name:sha256(p) for p in (root/'output').iterdir() if p.is_file()})
    write_json(root/'execution.json',state)
    return state


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--years',type=int,default=20)
    parser.add_argument('--tag',default='full')
    args=parser.parse_args()
    if not BINARY.exists():raise FileNotFoundError(BINARY)
    sites=[s for s in json.loads((OLD/'manifest.json').read_text())['sites']
           if s['slug'] in {'apostolic-saw','cryptic-beechnut'}]
    groups={'apostolic-saw':'apostolic-saw-h122','cryptic-beechnut':'cryptic-beechnut-h78'}
    selections=[('WRF-MPI','Historical',1995),('WRF-Nor','Historical',1995),
                ('WRF-MPI','SSP2-4.5',2060),('WRF-Nor','SSP2-4.5',2060),('WRF-MPI','SSP3-7.0',2080)]
    manager=CligenStationsManager()
    summary=[];jobs=[]
    for model,scenario,first in selections:
        for slug,point in groups.items():
            table,meta=load_series(model,scenario,first,first+args.years-1,point)
            location=next(p for p in meta[0]['points'] if p['name']==point)
            station=manager.get_closest_station((location['longitude'],location['latitude']))
            directory=ROOT/f'workflows-{args.tag}'/model/scenario/slug
            try:
                state=build_climate(table,meta,station,directory/'climate',seed=1001)
            except (DataQualityError, RuntimeError) as error:
                # Research boundary: retain rejected experiments, continue independent cases.
                summary.append(dict(model=model,scenario=scenario,group=slug,status='rejected',error=str(error)))
                print('rejected generation',model,scenario,slug,str(error),flush=True)
                continue
            summary.append(dict(model=model,scenario=scenario,group=slug,point=point,
                                station_distance_km=station.distance,days=state['days'],
                                maximum_source_error=state['maximum_source_error']))
            reference=normal(point)
            for site in [s for s in sites if s['slug']==slug]:
                revised=directory/'climate'/f'{site["site"]}-prism.cli'
                arms=[('single',directory/'climate/wepp.cli')]
                try:
                    revise_prism(directory/'climate/wepp.cli',revised,reference,normal(site['site']))
                except DataQualityError as error:
                    summary.append(dict(model=model,scenario=scenario,site=site['site'],arm='prism',
                                        status='rejected',error=str(error)))
                    print('rejected prism',model,scenario,site['site'],str(error),flush=True)
                else:
                    arms.append(('prism',revised))
                for arm,climate in arms:
                    jobs.append((site,climate,directory/site['site']/arm,args.years))
            print('generated',model,scenario,slug,flush=True)
    write_json(HERE/f'workflow-generation-{args.tag}.json',summary)
    def run(job):
        site,climate,root,years=job
        result=execute(site,climate,root,years)
        print('executed',str(root.relative_to(ROOT)),result['days'],flush=True)
        return dict(path=str(root.relative_to(ROOT)),site=site['site'],**result)
    with ThreadPoolExecutor(max_workers=4) as pool:executions=list(pool.map(run,jobs))
    write_json(HERE/f'workflow-generation-{args.tag}.json',summary)
    write_json(HERE/f'workflow-execution-{args.tag}.json',executions)


if __name__=='__main__':main()
