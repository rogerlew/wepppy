"""Frozen buffer-only drainage and depth-representation diagnostics."""
from __future__ import annotations
import argparse
import calendar
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
PRIOR=Path('/wc1/runs/ro/roads-ofe-budget-20261029-v2')
PANEL=['site-sand-outunrut-gravel-high','site-clay-outunrut-paved-high',
       'birmingham-clay-outunrut-paved-low','denver-loam-outrut-gravel-low']
OFFSETS={'minus':-1.,'same':0.,'plus':1.}


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


old=module('ofe_study',REPO/'docs/work-packages/20261029_roads_ofe_budget/artifacts/study.py')
a=module('ofe_accounting',REPO/'docs/work-packages/20261029_roads_ofe_budget/artifacts/accounting.py')


def change_buffer(ofes,conductivity,offset):
    if not math.isfinite(conductivity) or conductivity<=0 or offset not in OFFSETS.values():
        raise ValueError('Invalid diagnostic treatment')
    changed=deepcopy(ofes)
    buffer=changed[2]
    if 200 not in [h['solthk'] for h in buffer['horizons']]:
        raise ValueError('Missing 200 mm boundary')
    if buffer['horizons'][-1]['solthk']+offset<=buffer['horizons'][-2]['solthk']:
        raise ValueError('Depth treatment crosses another boundary')
    buffer['res_lyr']['kslast']=conductivity
    buffer['horizons'][-1]['solthk']+=offset
    return changed


def expected_depth(bottom):
    # Exact audited reader: append 200 mm, cap at 1800, then whole 200 mm cells.
    return math.floor(min(bottom+200.,1800.)/200.)*200.


def stage(root):
    root.mkdir(exist_ok=False)
    (root/'inputs').mkdir();(root/'native-source').mkdir()
    manifest=json.loads((PRIOR/'inputs/manifest.json').read_text())
    a.dump(root/'manifest.json',manifest)
    sources={}
    for name in ('input.for','scon.for','watbal.for'):
        data=subprocess.check_output(['git','-C','/workdir/wepp-forest','show',f'{old.SOURCE_COMMIT}:src/{name}'])
        (root/'native-source'/name).write_bytes(data);sources[name]=hashlib.sha256(data).hexdigest()
    endpoints={}
    for profile in PANEL:
        prior=PRIOR/'factorial-v1'/(profile+'-modern-111')
        record=json.loads((prior/'record.json').read_text())
        for sub,key in [('runs','inputs'),('output','outputs')]:
            for name,sha in record[key].items():
                if a.digest(prior/sub/name)!=sha:raise ValueError('Prior artifact changed')
        shutil.copytree(prior/'runs',root/'inputs'/profile)
        shutil.copyfile(prior/'record.json',root/'inputs'/profile/'prior-record.json')
        soil=record['case']['soil'];buffer=record['soil_readback'][2]
        endpoint={'sand':1.512,'clay':3.276}.get(soil)
        if endpoint is None:
            if soil!='loam':raise ValueError('Undeclared specimen')
            endpoint=buffer['horizons'][-1]['ksat']
        endpoints[profile]=dict(current=buffer['res_lyr']['kslast'],source=endpoint,
                               input_bottom_mm=buffer['horizons'][-1]['solthk'])
    files=[Path(__file__),Path(old.__file__),Path(a.__file__),Path(old.e.__file__),Path(old.b.__file__),
           REPO/'wepppy/wepp/soils/utils/wepp_soil_util.py',REPO/'wepppy/wepp/soils/horizon_boundary.py']
    a.dump(root/'declaration.json',dict(panel=PANEL,endpoints=endpoints,offsets=OFFSETS,source_commit=old.SOURCE_COMMIT,
                                     native_source_sha256=sources,source_sha256={str(p.relative_to(REPO)):a.digest(p) for p in files},
                                     binary=manifest['binaries']['modern'],prior_root=str(PRIOR)))
    shutil.copyfile(__file__,root/'executed-experiment.py')
    print(json.dumps(endpoints,indent=2))


def execute(task):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    root,profile,drainage,depth=task
    declaration=json.loads((root/'declaration.json').read_text())
    folder=root/'runs'/f'{profile}--{drainage}--{depth}'
    shutil.copytree(root/'inputs'/profile,folder/'runs');(folder/'output').mkdir()
    runs=folder/'runs';prior=json.loads((runs/'prior-record.json').read_text())
    soil=WeppSoilUtil(str(runs/'p1.sol'))
    conductivity=declaration['endpoints'][profile][drainage]
    expected=change_buffer(soil.obj['ofes'],conductivity,OFFSETS[depth])
    soil.obj['ofes']=expected;soil.write(str(runs/'p1.sol'))
    actual=WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']
    if actual!=expected:raise ValueError('Emitted soil readback mismatch')
    inputs={p.name:a.digest(p) for p in runs.iterdir() if p.name.startswith('p1.')}
    binary=declaration['binary']
    if a.digest(binary['path'])!=binary['sha256']:raise ValueError('Binary drift')
    with (runs/'p1.run').open() as stdin,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        proc=subprocess.run([binary['path']],cwd=runs,stdin=stdin,stdout=stdout,stderr=stderr,timeout=180)
    if proc.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        raise ValueError('Native failed')
    for name,sha in inputs.items():
        if a.digest(runs/name)!=sha:raise ValueError('Consumed input drift')
    calendar_info=json.loads((root/'manifest.json').read_text())['climates'][prior['case']['climate']]
    record=dict(name=folder.name,profile=profile,drainage=drainage,depth=depth,conductivity_mm_h=conductivity,
                expected_depth_mm=expected_depth(actual[2]['horizons'][-1]['solthk']),soil_readback=actual,
                inputs=inputs,outputs={p.name:a.digest(p) for p in (folder/'output').iterdir()},
                metrics=old.b.parse_loss(folder/'output/H1.loss.dat',prior['width_m']),
                wat_rows=old.b.validate_wat(folder/'output/H1.wat.dat',calendar_info),status='completed')
    a.dump(folder/'record.json',record)
    return record


def run(root):
    declaration=json.loads((root/'declaration.json').read_text())
    for path,sha in declaration['source_sha256'].items():
        if a.digest(REPO/path)!=sha:raise ValueError('Staged code changed')
    (root/'runs').mkdir(exist_ok=False)
    tasks=[(root,p,k,d) for p,k,d in itertools.product(PANEL,('current','source'),OFFSETS)]
    results=[]
    with ProcessPoolExecutor(max_workers=6) as pool:
        for result in pool.map(execute,tasks):
            results.append(result);print(f'{len(results)}/24 completed',flush=True)
    a.dump(root/'runs/summary.json',results)


def analyze(root):
    import pyarrow.parquet as pq
    from wepppy.wepp.interchange.hill_element_interchange import run_wepp_hillslope_element_interchange
    from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange
    from wepppy.wepp.interchange.hill_ebe_interchange import run_wepp_hillslope_ebe_interchange
    dest=root/'analysis';dest.mkdir(exist_ok=False)
    shutil.copyfile(__file__,dest/'executed-experiment.py')
    records=json.loads((root/'runs/summary.json').read_text())
    if len(records)!=24 or len({r['name'] for r in records})!=24:raise ValueError('Incomplete panel')
    manifest=json.loads((root/'manifest.json').read_text());results=[];waters={};elements={}
    fields=('P','RM','Q','Ep','Es','Er','Dp','UpStrmQ','SubRIn','latqcc','SoilWaterTotal','ProfileDepth','ProfilePorosityCap','ProfileFCStore','ProfileWPStore')
    for record in records:
        profile=record['profile'];folder=root/'runs'/record['name']
        prior=json.loads((root/'inputs'/profile/'prior-record.json').read_text())
        for sub,key in [('runs','inputs'),('output','outputs')]:
            for name,sha in record[key].items():
                if a.digest(folder/sub/name)!=sha:raise ValueError('Native artifact changed')
        expected=change_buffer(prior['soil_readback'],record['conductivity_mm_h'],OFFSETS[record['depth']])
        if record['soil_readback']!=expected:raise ValueError('Treatment invariant failed')
        for key in ('p1.man','p1.slp','p1.cli','p1.run'):
            if record['inputs'][key]!=prior['inputs'][key]:raise ValueError('Profile input drift')
        climate=manifest['climates'][prior['case']['climate']];first=int(climate['first'].split('-')[0]);last=int(climate['last'].split('-')[0])
        dates={(y,j) for y in range(first,last+1) for j in range(1,366+calendar.isleap(y))}
        erows=pq.read_table(run_wepp_hillslope_element_interchange(folder/'output',start_year=first,expected_hillslopes=1)).to_pylist()
        wrows=pq.read_table(run_wepp_hillslope_wat_interchange(folder/'output',expected_hillslopes=1)).to_pylist()
        brows=pq.read_table(run_wepp_hillslope_ebe_interchange(folder/'output',start_year=first,expected_hillslopes=1)).to_pylist()
        sediment,edays=a.sediment_budget(erows,prior['width_m'],16,record['metrics']['sediment_export_kg_yr'],strict=False)
        wdays=a.grouped(wrows,fields,dates)
        if not set(edays)<=dates:raise ValueError('ELEMENT calendar outside climate')
        lines=[line for line in (folder/'runs/p1.slp').read_text().splitlines() if line and not line.startswith('#')]
        width=float(lines[2].split()[1]);areas=[width*float(lines[i].split()[1]) for i in (3,5,7)]
        water=a.water_budget(wrows,areas,dates,16)
        depth_set={r['ProfileDepth'] for r in wrows if r['OFE']==3}
        if depth_set!={record['expected_depth_mm']}:raise ValueError(f'Native depth unexpected: {depth_set}')
        control=PRIOR/'factorial-v1'/(profile+'-legacy-legacy');legacy=json.loads((control/'record.json').read_text())
        for name,sha in legacy['outputs'].items():
            if a.digest(control/'output'/name)!=sha:raise ValueError('Legacy reference drift')
        reference=old.b.parse_loss(control/'output/H1.loss.dat',prior['width_m'])['sediment_export_kg_yr']
        late_dates={d for d in dates if d[0]>first}
        late_water=a.water_budget([r for r in wrows if r['year']>first],areas,late_dates,15)
        annual=[]
        for year in range(first,last+1):
            subset=[r for r in wrows if r['year']==year]
            annual.append(dict(year=year,water=a.water_budget(subset,areas,{d for d in dates if d[0]==year},1)['ofes'],
                               sediment_report_kg=record['metrics']['annual_export'][year-first]['sediment_export_kg']))
        buffer=[r for r in wrows if r['OFE']==3]
        capacity=max(r['ProfilePorosityCap'] for r in buffer)
        if capacity<=0:raise ValueError('Invalid storage capacity')
        state=dict(profile_depth_mm=record['expected_depth_mm'],porosity_capacity_mm=[min(r['ProfilePorosityCap'] for r in buffer),capacity],
                   mean_soil_water_mm=sum(r['SoilWaterTotal'] for r in buffer)/len(buffer),
                   days_at_90pct_capacity=sum(r['SoilWaterTotal']>=.9*r['ProfilePorosityCap'] for r in buffer),
                   initial_sat=record['soil_readback'][2]['sat'])
        result=dict(record=record,sediment=sediment,ebe=a.ebe_check(brows,edays,strict=False),water=water,state=state,
                    annual=annual,late_water=late_water,legacy_export_kg_yr=reference,
                    ratio_to_2010=record['metrics']['sediment_export_kg_yr']/reference if reference>0 else None,
                    late_export_kg_yr=sum(x['sediment_report_kg'] for x in annual[1:])/15)
        if record['drainage']=='current' and record['depth']=='same':
            result['control_reproduced']=all(record['outputs'][key]==sha for key,sha in prior['outputs'].items())
            if not result['control_reproduced']:raise ValueError('Control native reproduction failed')
        results.append(result);waters[record['name']]=wdays;elements[record['name']]=edays
        a.dump(dest/(record['name']+'.json'),result)
        print(f'{len(results)}/24 analyzed',flush=True)
    invariance=[]
    for result in results:
        r=result['record'];name=r['name'];control=r['profile']+'--current--same'
        for date,day in waters[name].items():
            for ofe in (1,2):
                for key in fields:
                    if day[ofe][key]!=waters[control][date][ofe][key]:raise ValueError(f'Upstream water changed: {name}, {date}, {ofe}, {key}')
        for date in set(elements[name])|set(elements[control]):
            for ofe in (1,2):
                value=elements[name].get(date,{}).get(ofe,{}).get('SedLeave',0.)
                original=elements[control].get(date,{}).get(ofe,{}).get('SedLeave',0.)
                if value!=original:raise ValueError(f'Upstream sediment changed: {name}, {date}, {ofe}')
        invariance.append(dict(name=name,upstream_water_and_sediment_identical=True))
    a.dump(dest/'results.json',results);a.dump(dest/'upstream-invariance.json',invariance)
    a.dump(dest/'acceptance.json',dict(native_runs=24,control_replays=4,depth_readbacks=24,upstream_invariance=24,
                                     report_reconciled=sum(r['sediment']['report_reconciled'] for r in results),
                                     ebe_mismatch_events=sum(len(r['ebe']['mismatches']) for r in results),production_candidate_accepted=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['stage','run','analyze'])
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();globals()[args.command](args.root)
