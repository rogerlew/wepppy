"""Diagnostic boundary-flag endmember; only no-detected development materials."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import role_runtime_ablation as b

HERE=b.HERE
ROOT=b.ROOT/'no-detected-boundary-v1'

def read(p):return json.loads(p.read_text())
def declare():
    provenance=read(HERE/'restriction-provenance-v1.json')
    materials={r['mukey'] for r in provenance['materials'] if r['category']=='no_detected_horizon'}
    assert materials=={'2711184','2711250','1718494'}
    tasks=[]
    for score in read(b.LEGACY/'declaration.json')['cases']:
        case=score['case']
        if case['soil'] not in materials:continue
        source=b.prior.MATRIX/'matrix-v1'/'-'.join(case.values())
        tasks.append(dict(case=case,source=str(source),source_record_sha256=b.prior.digest(source/'record.json'),
                          reference_kg_yr=score['reference_kg_yr'],baseline_within=score['within'],group=b.prior.classify(score)))
    assert len(tasks)==52
    ROOT.mkdir(exist_ok=False)
    declaration=dict(tasks=tasks,cases=52,script_sha256=b.prior.digest(Path(__file__)),
        dependencies={n:b.prior.digest(HERE/n) for n in ('role_runtime_ablation.py','continuation.py','role_boundary_assessment.py','restriction-provenance-v1.json')},
        binary_sha256=b.prior.SHA,contract='Only res_lyr.slflag 1->0 in all OFEs of no-detected source materials. Keep other fields exact, including inactive thickness/Ksat, all horizons/200 mm breaks and hourly/PMET/snow. No material geology inference, new default, fitted value or withheld outcomes.',
        rationale='Class-specific endmember separates the imposed boundary from the generated material without changing conductivity magnitudes. Prior studies changed Ksat, not this flag contrast on the repaired engine.')
    b.dump(ROOT/'declaration.json',declaration);b.dump(HERE/'no-detected-boundary-v1-declaration.json',declaration)
    shutil.copy2(__file__,ROOT/'executed-study.py');print('Declared 52 cases.',flush=True)

def execute(task):
    source=Path(task['source']);old=read(source/'record.json')
    assert b.prior.digest(source/'record.json')==task['source_record_sha256']
    assert old['physical_pass'] and old['binary_sha256']==b.prior.SHA
    folder=ROOT/'matrix-v1'/source.name;runs=folder/'runs';output=folder/'output'
    runs.mkdir(parents=True,exist_ok=False);output.mkdir()
    for name,sha in old['inputs'].items():
        assert b.prior.digest(source/'runs'/name)==sha
        shutil.copy2(source/'runs'/name,runs/name)
    shutil.copy2(source/'runs/reference.sol',runs/'reference.sol')
    soil=b.WeppSoilUtil(str(runs/'p1.sol'));before=deepcopy(soil.obj)
    for ofe in soil.obj['ofes']:
        assert ofe['res_lyr']['slflag']==1
        ofe['res_lyr']['slflag']=0
    expected=deepcopy(soil.obj);soil.write(str(runs/'p1.sol'))
    actual=b.WeppSoilUtil(str(runs/'p1.sol')).obj;assert actual==expected
    restored=deepcopy(actual)
    for ofe in restored['ofes']:ofe['res_lyr']['slflag']=1
    assert restored==before
    inputs={p.name:b.prior.digest(p) for p in runs.iterdir() if p.name!='reference.sol'}
    assert {k for k,v in inputs.items() if v!=old['inputs'][k]}=={'p1.sol'}
    assert b.prior.digest(b.BINARY)==b.prior.SHA
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        proc=subprocess.run([str(b.BINARY)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300)
    record=dict(task,binary_sha256=b.prior.SHA,inputs=inputs,outputs={p.name:b.prior.digest(p) for p in output.iterdir()},
                soil_readback=actual['ofes'],width_m=old['width_m'],profile_length_m=old['profile_length_m'],
                returncode=proc.returncode,status='native_failure',physical_pass=False,within=False,
                baseline_kg_yr=old['metrics']['sediment_export_kg_yr'])
    if proc.returncode==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs/'stdout').read_text():
        record.update(status='completed',metrics=b.c.b.parse_loss(output/'H1.loss.dat',old['width_m']))
        record['audit']=b.c.audit(folder,record['case'],record)
        record['physical_pass']=record['audit']['physical_pass']
        value=record['metrics']['sediment_export_kg_yr'];ref=record['reference_kg_yr']
        record['within']=.1<=value/ref<=10 if ref>1 else value<=max(1,10*ref)
    else:record['terminal_output']=(runs/'stdout').read_text().splitlines()[-1]
    b.dump(folder/'record.json',record);return record

def run():
    d=read(ROOT/'declaration.json');assert d['script_sha256']==b.prior.digest(Path(__file__))
    for n,sha in d['dependencies'].items():assert b.prior.digest(HERE/n)==sha
    rows=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for row in pool.map(execute,d['tasks']):
            rows.append(row)
            if len(rows)%10==0:print(len(rows),'/52',flush=True)
    b.dump(ROOT/'results.json',rows)
    summary=dict(cases=len(rows),completed=sum(r['status']=='completed' for r in rows),physical_pass=sum(r['physical_pass'] for r in rows),
        groups={g:dict(cases=len(items:=[r for r in rows if r['group']==g]),within=sum(r['within'] and r['physical_pass'] for r in items)) for g in sorted({r['group'] for r in rows})},
        recovered=sum(not r['baseline_within'] and r['within'] and r['physical_pass'] for r in rows),
        regressions=sum(r['baseline_within'] and not(r['within'] and r['physical_pass']) for r in rows),results_sha256=b.prior.digest(ROOT/'results.json'))
    b.dump(ROOT/'summary.json',summary);b.dump(HERE/'no-detected-boundary-v1-summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--declare',action='store_true');args=parser.parse_args()
    declare() if args.declare else run()
