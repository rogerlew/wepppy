"""Reproduce two distinct negative-flux inputs with UI mode off/on."""
from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
PRIOR=Path('/wc1/runs/ro/roads-drainage-validation-20261029-v2')
ROOT=Path('/wc1/runs/ro/roads-parameterization-program-20261029/mode-diagnostic-v1')
SPEC=importlib.util.spec_from_file_location('prior_audit',REPO/'docs/work-packages/20261029_roads_drainage_validation/artifacts/analyze.py')
a=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(a)
b=a.b
PROFILES=('flagstaff-new_lithic-inbare-gravel-none','flagstaff-new_lithic-outrut-gravel-none')


def execute(task):
    profile,drainage,ui=task
    source=PRIOR/'matrix-v1'/f'{profile}-{drainage}'
    previous=json.loads((source/'record.json').read_text());a.s.check_files(source,previous)
    case=previous['case'].copy()
    if ui:case['runtime']='ui-only'
    name='-'.join(case.values());folder=ROOT/'matrix-v1'/name
    runs=folder/'runs';out=folder/'output';runs.mkdir(parents=True,exist_ok=False);out.mkdir()
    for file in previous['inputs']:shutil.copy2(source/'runs'/file,runs/file)
    shutil.copy2(source/'runs/reference.sol',runs/'reference.sol')
    if ui:(runs/'wepp_ui.txt').write_bytes(b'')
    inputs={p.name:b.digest(p) for p in runs.iterdir() if p.name!='reference.sol'}
    declaration=json.loads((ROOT/'declaration.json').read_text());binary=declaration['binary']
    if b.digest(binary['path'])!=binary['sha256']:raise ValueError('Binary drift')
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        result=subprocess.run([binary['path']],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=180)
    if result.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        raise ValueError('Native failure')
    record=dict(case=case,name=name,status='completed',width_m=previous['width_m'],profile_length_m=previous['profile_length_m'],
        soil_readback=previous['soil_readback'],inputs=inputs,outputs={p.name:b.digest(p) for p in out.iterdir()},
        metrics=b.parse_loss(out/'H1.loss.dat',previous['width_m']),
        wat_rows=b.validate_wat(out/'H1.wat.dat',json.loads((ROOT/'inputs/manifest.json').read_text())['climates']['flagstaff']))
    a.s.check_files(folder,record);b.dump(folder/'record.json',record)
    audit=a.analyze_case((ROOT,case,ROOT/'analysis'))
    audit['mode_off_control_exact']=None if ui else all(record['outputs'][k]==sha for k,sha in previous['outputs'].items())
    return audit


def main():
    ROOT.mkdir(exist_ok=False);(ROOT/'matrix-v1').mkdir();(ROOT/'analysis/cases').mkdir(parents=True)
    (ROOT/'inputs').symlink_to(PRIOR/'inputs',target_is_directory=True)
    tasks=[(p,d,ui) for p in PROFILES for d in ('current','source') for ui in (False,True)]
    binary=json.loads((PRIOR/'declaration.json').read_text())['binaries']['modern']
    b.dump(ROOT/'declaration.json',dict(tasks=tasks,binary=binary,purpose='Diagnostic reproduction; no candidate fitting',
        script_sha256=b.digest(Path(__file__)),auditor_sha256=b.digest(Path(a.__file__))))
    shutil.copy2(__file__,ROOT/'executed-mode-diagnostic.py')
    with ProcessPoolExecutor(max_workers=4) as pool:results=list(pool.map(execute,tasks))
    b.dump(ROOT/'results.json',results)
    compact=[dict(case=r['case'],export_kg_yr=r['metrics']['sediment_export_kg_yr'],
        negative_fluxes=r['sediment']['negative_fluxes'],report_reconciled=r['sediment']['report_reconciled'],
        ebe_mismatch_events=len(r['ebe']['mismatches']),mode_off_control_exact=r['mode_off_control_exact']) for r in results]
    b.dump(HERE/'mode-diagnostic.json',compact);print(json.dumps(compact,indent=2),flush=True)


if __name__=='__main__':main()
