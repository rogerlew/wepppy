"""Screen engineered-surface hydraulics while retaining generated soil material."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('boundary_runtime',HERE/'runtime_diagnostic.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
a=d.a;b=d.b
ROOT=d.ROOT.parent/'engineered-surface-screen-v1'
SOURCE=d.ROOT.parent/'project-runtime-screen-v2'
TARGETS=dict(road=(0,),road_fill=(0,1),road_cap=(0,),road_fill_cap=(0,1))


def transform(ofes, reference, target):
    if target not in TARGETS:
        raise ValueError('Unknown engineered treatment')
    result=deepcopy(ofes)
    for ofe in TARGETS[target]:result[ofe]['ksatadj']='0'
    if target.endswith('_cap'):
        cap=float(reference['avke'])
        if not math.isfinite(cap) or cap<=0:raise ValueError('Invalid reference surface cap')
        if 200 not in [h['solthk'] for h in result[0]['horizons']]:
            raise ValueError('Missing 200mm treatment boundary')
        for h in result[0]['horizons']:
            if h['solthk']<=200:h['ksat']=min(h['ksat'],cap)
    return result



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
    reference=WeppSoilUtil(str(runs/'reference.sol')).obj['ofes'][0]
    soil.obj['ofes']=transform(before,reference,target)
    expected=deepcopy(soil.obj['ofes']);soil.write(str(runs/'p1.sol'))
    actual=WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']
    if actual!=expected:raise ValueError('Engineered surface readback mismatch')
    restored=deepcopy(actual)
    for index in TARGETS[target]:restored[index]['ksatadj']=before[index]['ksatadj']
    if target.endswith('_cap'):
        for h,old_h in zip(restored[0]['horizons'],before[0]['horizons']):
            if h['solthk']<=200:h['ksat']=old_h['ksat']
    if restored!=before:raise ValueError('Treatment changed undeclared material')
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
    profiles=tuple('-'.join(row['case'].values()) for row in json.loads((SOURCE/'results.json').read_text())
                   if row['case']['variant']=='erosion')
    ROOT.mkdir(exist_ok=False);(ROOT/'matrix-v1').mkdir();(ROOT/'analysis/cases').mkdir(parents=True)
    (ROOT/'inputs').symlink_to(SOURCE/'inputs',target_is_directory=True)
    source=json.loads((SOURCE/'declaration.json').read_text())
    if len(profiles)!=96:raise ValueError('Incomplete source panel')
    tasks=[(p,t) for p in profiles for t in TARGETS]
    b.dump(ROOT/'declaration.json',dict(tasks=tasks,targets=TARGETS,binary=source['binary'],
        script_sha256=b.digest(Path(__file__)),auditor_sha256=b.digest(Path(a.__file__)),
        hypothesis='Test road versus road/fill forest-adjustment removal, paired with a generated-soil surface conductivity cap',
        rationale='Engineered surface is not a disturbed forest. Cap upper200mm Ksat at configuration-matched legacy effective conductivity without increasing source Ksat; retain texture, rock, lower boundaries and deeper material. This cap is a testable transfer hypothesis, not identity of effective conductivity and horizon Ksat.',
        limits='Development screen only. Four predeclared policies, no per-case fitting. Legacy avke is an explicit surface parameterization prior, not substituted legacy soil material; all fill/buffer horizons remain generated and unchanged.'))
    shutil.copy2(__file__,ROOT/'executed-engineered-surface-screen.py')
    results=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for result in pool.map(execute,tasks):
            results.append(result);b.dump(ROOT/'partial-results.json',results);print(len(results),len(tasks),result['case'],result['status'],result.get('export_kg_yr'),flush=True)
    b.dump(ROOT/'results.json',results);b.dump(HERE/'engineered-surface-screen.json',results)


if __name__=='__main__':main()
