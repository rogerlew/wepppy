"""Isolated Roads prepared-soil experiment; never modifies production projects."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[4]
PRIOR = REPO/'docs/work-packages/20261029_roads_soil_benchmark/artifacts'
sys.path.insert(0, str(PRIOR))
import benchmark as b
ROOT = Path('/wc1/runs/ro/roads-prepared-soil-hydraulics-20261029')
OLD = b.DEFAULT_ROOT
SOURCES = dict(b.SPECIMENS, holdout='/wc1/runs/cl/clogging-starch/soils/2711195.sol')
PANEL = [('site','sand','outunrut','gravel','high'),
         ('birmingham','clay','outunrut','paved','low'),
         ('denver','loam','outrut','gravel','low'),
         ('birmingham','loam','outrut','gravel','low'),
         ('charleston','silt','inveg','gravel','low')]
BASE_VARIANTS = ['raw','prepared_raw','format9002','forest_all','bare_all',
                 'road_bare','fill_bare','buffer_forest','roles',
                 'roles_fixed','roles_fixed_erosion','roles_fixed_ki',
                 'roles_fixed_kr','roles_fixed_tau','roles_fixed_rock',
                 'roles_fixed_all','project_roles']
HYDRO_VARIANTS = [f'layer{depth}_k{k}' for depth in (50,200,400) for k in (1,3,10)]


def split_layer(ofe, depth, conductivity):
    """Set conductivity through a cumulative depth; preserve all deeper material."""
    if not math.isfinite(depth) or not math.isfinite(conductivity) or depth <= 0 or conductivity <= 0:
        raise ValueError('Layer depth and conductivity must be positive finite values')
    horizons = ofe['horizons']
    if depth > horizons[-1]['solthk']:
        raise ValueError('Treatment exceeds profile depth')
    result=[]
    previous=0.0
    for original in horizons:
        h=deepcopy(original)
        bottom=float(h['solthk'])
        if bottom <= previous:
            raise ValueError('Nonincreasing horizon depths')
        if previous < depth < bottom:
            upper=deepcopy(h)
            upper['solthk']=depth
            upper['ksat']=conductivity
            result.append(upper)
        elif bottom <= depth:
            h['ksat']=conductivity
        result.append(h)
        previous=bottom
    ofe['horizons']=result
    ofe['nsl']=len(result)


def stage(root):
    from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture
    from wepppy.nodb.mods.disturbed.disturbed import read_disturbed_land_soil_lookup
    from wepppy.nodb.core.wepp import prep_soil
    root.mkdir(exist_ok=False)
    shutil.copytree(OLD/'reference',root/'reference')
    shutil.copytree(OLD/'inputs/climates',root/'inputs/climates')
    inputs=root/'inputs'
    (inputs/'soils').mkdir()
    lookup_path=REPO/'wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv'
    shutil.copy2(lookup_path,inputs/'lookup.csv')
    lookup=read_disturbed_land_soil_lookup(str(lookup_path))
    manifest=json.loads((OLD/'inputs/manifest.json').read_text())
    manifest['soils']={}
    manifest['prepared']={}
    manifest['holdout']={'soil':'holdout','source':SOURCES['holdout']}
    manifest['preparation']={'primary':{'initial_sat':0.75,'kslast':None,'clip':False},
                            'project_control':{'initial_sat':0.75,'kslast':0.01,'clip_depth_mm':700},
                            'lookup_sha256':b.digest(lookup_path)}
    for name,source in SOURCES.items():
        target=inputs/'soils'/f'{name}.sol';shutil.copy2(source,target)
        soil=WeppSoilUtil(str(target))
        if soil.datver!=7778 or len(soil.obj['ofes'])!=1:
            raise ValueError('Expected one-OFE generated base specimen')
        texture=simple_texture(clay=soil.clay,sand=soil.sand)
        manifest['soils'][name]={'source':source,'sha256':b.digest(target),'texture':texture,'data':soil.obj}
        dest=inputs/'prepared'/name;dest.mkdir(parents=True)
        manifest['prepared'][name]={}
        for mode in ('raw','format','forest','bare'):
            intermediate=dest/f'{mode}-conditioned.sol'
            if mode=='raw':
                shutil.copy2(target,intermediate)
            else:
                replacements=lookup[(texture, mode if mode in ('forest','bare') else 'forest')].copy()
                if mode=='format':
                    # Supply required format metadata without landuse parameter overrides.
                    replacements={k:replacements[k] for k in ('luse','stext','ksatadj','ksatfac','ksatrec')}
                    replacements.update(ksatadj=0,ksatfac=1.0,ksatrec=0.0)
                soil.to_over9000(replacements,version=9002).write(str(intermediate))
            for project in (False,True):
                out=dest/f'{mode}{"-project" if project else ""}.sol'
                prep_soil((name,str(intermediate),str(out),0.01 if project else None,None,
                           0.75,project,700,False,None))
                parsed=WeppSoilUtil(str(out)).obj
                manifest['prepared'][name][out.stem]={'sha256':b.digest(out),'data':parsed}
    # Retain a real project-prepared artifact as a lineage example, not a new model baseline.
    example=Path('/wc1/runs/cl/clogging-starch/wepp/runs/p1.sol')
    shutil.copy2(example,inputs/'actual-project-p1.sol')
    manifest['actual_project_example']={'source':str(example),'sha256':b.digest(example)}
    sources=[Path(__file__),PRIOR/'benchmark.py',REPO/'wepppy/wepp/soils/utils/wepp_soil_util.py',
             REPO/'wepppy/nodb/core/wepp.py',REPO/'wepppy/nodb/mods/disturbed/disturbed.py',lookup_path]
    manifest['source_hashes']={str(p.relative_to(REPO)):b.digest(p) for p in sources}
    manifest['study']={'hydraulic_depths_mm':[50,200,400],'conductivities_mm_h':[1,3,10],
                      'rationale':'Exploratory brackets around production 200 mm conditioning and legacy road conductivities; not measured compaction values',
                      'version':9002,'prepared_path':'owned to_over9000 + prep_soil; function-level replay, not full project orchestration'}
    b.dump(inputs/'manifest.json',manifest)
    print('Staged five specimens, four preparation modes, two boundary settings',flush=True)


def build_soil(root,soil_key,variant,legacy,output):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    def prepared(mode,project=False):
        path=root/'inputs/prepared'/soil_key/f'{mode}{"-project" if project else ""}.sol'
        return WeppSoilUtil(str(path))
    if variant=='raw':
        soil=WeppSoilUtil(str(root/'inputs/soils'/f'{soil_key}.sol'))
        modes=None
    elif variant=='prepared_raw':
        soil=prepared('raw');modes=None
    else:
        modes={'format9002':['format']*3,'forest_all':['forest']*3,'bare_all':['bare']*3,
               'road_bare':['bare','format','format'],'fill_bare':['format','bare','format'],
               'buffer_forest':['format','format','forest']}.get(variant,['bare','bare','forest'])
        soil=prepared(modes[0],variant=='project_roles')
    soil.obj['ofes']=[deepcopy(soil.obj['ofes'][0]) for _ in range(3)] if modes is None else [
        deepcopy(prepared(mode,variant=='project_roles').obj['ofes'][0]) for mode in modes]
    soil.obj['ntemp']=3
    road=soil.obj['ofes'][0]
    reference=WeppSoilUtil(str(legacy)).obj['ofes'][0]
    if variant.startswith('roles_fixed') or variant.startswith('layer'):
        road.update(ksatadj=0,ksatfac=1.0,ksatrec=0.0)
    if variant.startswith('layer'):
        d,k=variant.removeprefix('layer').split('_k')
        split_layer(road,float(d),float(k))
    if variant in ('roles_fixed_erosion','roles_fixed_all'):
        for key in ('ki','kr','shcrit'):road[key]=reference[key]
    if variant in ('roles_fixed_ki','roles_fixed_kr','roles_fixed_tau'):
        key={'roles_fixed_ki':'ki','roles_fixed_kr':'kr','roles_fixed_tau':'shcrit'}[variant]
        road[key]=reference[key]
    if variant in ('roles_fixed_rock','roles_fixed_all'):
        road['horizons'][0]['rfg']=reference['horizons'][0]['rfg']
    soil.obj['header'].append(f'Isolated prepared-soil experiment: {variant}')
    soil.write(str(output))
    readback=WeppSoilUtil(str(output)).obj
    # Writer prints finite precision (including fitted hydraulic fields); retain readback.
    if len(readback['ofes'])!=3 or any(o['nsl']!=len(o['horizons']) for o in readback['ofes']):
        raise ValueError('Prepared soil assembly readback failed')
    return readback


def native_diagnostics(source,target):
    import pyarrow.parquet as pq
    from wepppyo3 import wepp_interchange
    from wepppy.wepp.interchange.versioning import INTERCHANGE_VERSION
    wepp_interchange.hillslope_pass_files_to_parquet([str(source)],str(target),
        INTERCHANGE_VERSION.major,INTERCHANGE_VERSION.minor,cli_calendar_path=None,
        pass_family='legacy_ascii',compression='snappy')
    rows=pq.read_table(target).to_pylist()
    if len(rows)!=5844 or len({r['year'] for r in rows})!=16:
        raise ValueError('Incomplete PASS diagnostic calendar')
    keys=('runvol','sbrunv','gwbfv','tdet','tdep')
    if any(not math.isfinite(float(r[k])) for r in rows for k in keys):
        raise ValueError('Nonfinite PASS diagnostic')
    return {**{k:sum(r[k] for r in rows)/16 for k in keys},
            'pass_export_kg_yr':sum(r['runvol']*sum(r[f'sedcon_{i}'] for i in range(1,6)) for r in rows)/16}


def execute(task):
    root,batch,case=task
    from wepp_runner import make_hillslope_run
    manifest=json.loads((root/'inputs/manifest.json').read_text())
    name='-'.join(case.values())
    folder=root/batch/name;runs=folder/'runs';out=folder/'output'
    runs.mkdir(parents=True,exist_ok=False);out.mkdir()
    texture='loam' if case['soil']=='holdout' else case['soil']
    b.reference_soil(root,texture,case['design'],case['surface'],case['traffic'],runs/'reference.sol')
    if case['variant']=='legacy':
        shutil.copy2(runs/'reference.sol',runs/'p1.sol')
        soil_readback=None
    else:
        soil_readback=build_soil(root,case['soil'],case['variant'],runs/'reference.sol',runs/'p1.sol')
    man={'inbare':'3inslope','inveg':'3inslope','outrut':'3outrut','outunrut':'3outunr'}[case['design']]
    man+='n.man' if case['traffic']=='none' else '.man'
    shutil.copy2(root/'reference/api/db/wepproad/managements'/man,runs/'p1.man')
    slope,width,length=b.slope_text(case['design']);(runs/'p1.slp').write_text(slope)
    shutil.copy2(root/'inputs/climates'/f"{case['climate']}.cli",runs/'p1.cli')
    make_hillslope_run(1,16,str(runs),reveg=False,wepp_bin='wepp_261026')
    runfile=runs/'p1.run';lines=runfile.read_text().splitlines()
    if lines[6]!='1' or lines[5]!='../output/H1.pass.dat':raise ValueError('Runner prompt drift')
    lines[6]='2';runfile.write_text('\n'.join(lines)+'\n')
    binary=manifest['binaries'][case['binary']]
    if b.digest(binary['path'])!=binary['sha256']:raise ValueError('Binary drift')
    record={'case':case,'name':name,'status':'prepared','width_m':width,'profile_length_m':length,
            'soil_readback':soil_readback,'binary':binary,
            'inputs':{p.name:b.digest(p) for p in runs.iterdir()}}
    b.dump(folder/'record.json',record)
    start=time.monotonic()
    with runfile.open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        try:
            proc=subprocess.run([binary['path']],stdin=inp,stdout=stdout,stderr=stderr,cwd=runs,timeout=120)
        except subprocess.TimeoutExpired:
            record.update(status='failed',error='Native timeout')
            b.dump(folder/'record.json',record);return record
    record['elapsed_s']=time.monotonic()-start
    try:
        if proc.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
            raise ValueError(f'Native completion failed: {proc.returncode}')
        record['metrics']=b.parse_loss(out/'H1.loss.dat',width)
        record['wat_rows']=b.validate_wat(out/'H1.wat.dat',manifest['climates'][case['climate']])
        if case['binary']=='modern':record['native']=native_diagnostics(out/'H1.pass.dat',out/'pass.parquet')
        record['status']='completed'
    except (ValueError,IndexError) as exc:
        record.update(status='failed',error=str(exc))
    record['outputs']={p.name:b.digest(p) for p in out.iterdir()}
    b.dump(folder/'record.json',record)
    return record


def run(root,batch,phase,variants,workers):
    dest=root/batch;dest.mkdir(exist_ok=False)
    shutil.copy2(__file__,dest/'executed-experiment.py')
    shutil.copy2(PRIOR/'benchmark.py',dest/'executed-benchmark.py')
    if phase=='diagnostic':panel=PANEL
    else:panel=list(itertools.product(('birmingham','denver','flagstaff','charleston','site'),SOURCES,
                                      ('inbare','inveg','outrut','outunrut'),('gravel','paved'),('high','low','none')))
    tasks=[]
    for values in panel:
        common=dict(zip(('climate','soil','design','surface','traffic'),values))
        for variant in variants:
            tasks.append((root,batch,dict(common,binary='modern',variant=variant)))
        for binary in ('legacy','modern'):
            if phase=='diagnostic' or common['soil']=='holdout':
                tasks.append((root,batch,dict(common,binary=binary,variant='legacy')))
    b.dump(dest/'declaration.json',{'phase':phase,'variants':variants,'cases':[t[2] for t in tasks],
                                 'script_sha256':b.digest(__file__),'manifest_sha256':b.digest(root/'inputs/manifest.json')})
    records=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for record in pool.map(execute,tasks):
            records.append(record)
            if len(records)%10==0:print(f'{len(records)}/{len(tasks)} completed records',flush=True)
    b.dump(dest/'summary.json',{'records':records,'failed':sum(r['status']!='completed' for r in records)})
    print(f'Finished {len(records)} cases; failures={sum(r["status"]!="completed" for r in records)}',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('stage','diagnostic','validation'))
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--batch',default='diagnostic-v1')
    parser.add_argument('--variants',nargs='+',default=BASE_VARIANTS+HYDRO_VARIANTS)
    parser.add_argument('--workers',type=int,default=12)
    args=parser.parse_args()
    if args.command=='stage':stage(args.root)
    else:run(args.root,args.batch,args.command,args.variants,args.workers)
