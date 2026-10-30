"""Isolate fill and buffer lower-boundary effects on native water failures."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('boundary_runtime',HERE/'runtime_diagnostic.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
a=d.a;b=d.b
ROOT=d.ROOT.parent/'boundary-diagnostic-v1'
SOURCE=d.ROOT.parent/'project-runtime-screen-v2'
PROFILES=('site-loam-inbare-gravel-high-erosion-project',
          'site-sand-inbare-gravel-high-erosion-project',
          'birmingham-sand-inbare-gravel-high-erosion-project',
          'birmingham-clay-inbare-gravel-high-rock-project',
          'flagstaff-sand-inbare-gravel-none-erosion-project',
          'flagstaff-clay-inbare-gravel-none-erosion-project')
TARGETS=dict(fill=(1,),buffer=(2,),both=(1,2))


def execute(task):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    profile,target=task
    source=SOURCE/'matrix-v1'/profile
    source_record=source/('record.json' if (source/'record.json').exists() else 'failure.json')
    old=json.loads(source_record.read_text())
    case=old['case'].copy();case['variant'] += '_'+target
    name='-'.join(case.values());folder=ROOT/'matrix-v1'/name
    runs=folder/'runs';out=folder/'output';runs.mkdir(parents=True,exist_ok=False);out.mkdir()
    for file,sha in old['inputs'].items():
        if b.digest(source/'runs'/file)!=sha:raise ValueError('Source input drift')
        shutil.copy2(source/'runs'/file,runs/file)
    shutil.copy2(source/'runs/reference.sol',runs/'reference.sol')
    declaration=json.loads((ROOT/'declaration.json').read_text())
    soil=WeppSoilUtil(str(runs/'p1.sol'));before=deepcopy(soil.obj['ofes'])
    for ofe in TARGETS[target]:soil.obj['ofes'][ofe]['res_lyr']['kslast']=declaration['conductivities_mm_h'][case['soil']]
    expected=deepcopy(soil.obj['ofes']);soil.write(str(runs/'p1.sol'))
    actual=WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']
    if actual!=expected or actual[0]!=before[0] or any(x['horizons']!=y['horizons'] for x,y in zip(actual,before)):
        raise ValueError('Boundary treatment/readback leaked into material or road')
    inputs={p.name:b.digest(p) for p in runs.iterdir() if p.name!='reference.sol'}
    binary=declaration['binary']
    if b.digest(binary['path'])!=binary['sha256']:raise ValueError('Binary drift')
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        proc=subprocess.run([binary['path']],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=180)
    common=dict(case=case,name=name,inputs=inputs,outputs={p.name:b.digest(p) for p in out.iterdir()},
                source_record_sha256=b.digest(source_record),soil_readback=actual)
    if proc.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        result=dict(common,status='native_failure',returncode=proc.returncode,reason=(runs/'stdout').read_text().splitlines()[-1],
                    stdout_sha256=b.digest(runs/'stdout'),stderr_sha256=b.digest(runs/'stderr'))
        b.dump(folder/'failure.json',result);return result
    _,width,length=b.slope_text(case['design'])
    manifest=json.loads((ROOT/'inputs/manifest.json').read_text())
    record=dict(common,status='completed',width_m=width,profile_length_m=length,
                metrics=b.parse_loss(out/'H1.loss.dat',width),
                wat_rows=b.validate_wat(out/'H1.wat.dat',manifest['climates'][case['climate']]))
    b.dump(folder/'record.json',record)
    audit=a.analyze_case((ROOT,case,ROOT/'analysis'))
    return dict(case=case,status='completed',export_kg_yr=record['metrics']['sediment_export_kg_yr'],
                negative_fluxes=audit['sediment']['negative_fluxes'],report_reconciled=audit['sediment']['report_reconciled'],
                ebe_mismatch_events=len(audit['ebe']['mismatches']),record_sha256=b.digest(folder/'record.json'))


def main():
    ROOT.mkdir(exist_ok=False);(ROOT/'matrix-v1').mkdir();(ROOT/'analysis/cases').mkdir(parents=True)
    (ROOT/'inputs').symlink_to(SOURCE/'inputs',target_is_directory=True)
    previous=ROOT.parent.parent/'roads-drainage-validation-20261029-v2/declaration.json'
    # Prior immutable declaration retains SSURGO restriction/source provenance.
    previous=Path('/wc1/runs/ro/roads-drainage-validation-20261029-v2/declaration.json')
    endpoints=json.loads(previous.read_text())['endpoints']
    source=json.loads((SOURCE/'declaration.json').read_text())
    tasks=[(p,t) for p in PROFILES for t in TARGETS]
    b.dump(ROOT/'declaration.json',dict(tasks=tasks,targets=TARGETS,binary=source['binary'],
        conductivities_mm_h={k:endpoints[k]['source'] for k in ('sand','clay','loam')},
        endpoint_source=str(previous),endpoint_source_sha256=b.digest(previous),
        script_sha256=b.digest(Path(__file__)),auditor_sha256=b.digest(Path(a.__file__)),
        hypothesis='Identify whether fill versus buffer lower-boundary impedance causes native hourly water failures',
        rationale='Reuse source-derived restriction conductivity for sand/clay and bottom material conductivity for unrestricted loam; do not choose values from sediment fit',
        limits='Sensitivity only: source Ksat is not proven effective bedrock drainage, and this is not a universal removal of attenuation. Existing geometry/runtime/road inputs and all horizons retained.'))
    shutil.copy2(__file__,ROOT/'executed-boundary-diagnostic.py')
    results=[]
    with ProcessPoolExecutor(max_workers=6) as pool:
        for result in pool.map(execute,tasks):
            results.append(result);print(result['case'],result['status'],result.get('export_kg_yr'),flush=True)
    b.dump(ROOT/'results.json',results);b.dump(HERE/'boundary-diagnostic.json',results)


if __name__=='__main__':main()
