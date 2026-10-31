"""Rehash emitted decks/outputs, recompute physical audits and observe coupled state."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json
import math
import shutil

import road_pore_screen_r3 as study
import hydraulic_init_probe_r3 as probe
c=study.c
role=study.role
ROOT=study.ROOT


def verify(task):
    folder=Path(task['folder']);row=json.loads((folder/'record.json').read_text())
    source=Path(task['source']);assert role.digest(source/'record.json')==task['source_record_sha256']
    old=json.loads((source/'record.json').read_text())
    assert row['inputs']==task['inputs'] and row['soil_readback']==task['soil_readback']
    for section,subdir in [('inputs','runs'),('outputs','output')]:
        for name,digest in row[section].items():assert role.digest(folder/subdir/name)==digest
    assert role.digest(folder/'runs/stdout')==row['stdout_sha256']
    assert role.digest(folder/'runs/stderr')==row['stderr_sha256']
    assert {n for n in row['inputs'] if row['inputs'][n]!=old['inputs'][n]}=={'p1.sol'}
    actual=study.WeppSoilUtil(str(folder/'runs/p1.sol')).obj['ofes']
    assert actual==row['soil_readback'] and actual[1:]==old['soil_readback'][1:]
    for after,before in zip(actual[0]['horizons'],old['soil_readback'][0]['horizons']):
        if before['solthk']>200:assert after==before;continue
        for key in ('solthk','sand','clay','orgmat','cec','rfg','anisotropy'):assert after[key]==before[key]
        if task['lane'] in ('pore','coupled'):
            bd0=min(2.,max(.8,before['bd']));bd1=after['bd']
            assert math.isclose((bd1-bd0)/2.65,.02,abs_tol=1e-10)
            scale=(1-bd1/2.65)/(1-bd0/2.65)
            for field in ('fc','wp'):assert math.isclose(after[field],before[field]*scale,rel_tol=1e-10)
        else:
            for field in ('bd','fc','wp'):assert after[field]==before[field]
        assert math.isclose(after['ksat'],before['ksat']/(2.4 if task['lane'] in ('conductivity','coupled') else 1),rel_tol=1e-10)
    if row['status']=='completed':
        assert c.b.parse_loss(folder/'output/H1.loss.dat',row['width_m'])==row['metrics']
        assert c.audit(folder,row['case'],row)==row['audit']
    return dict(folder=str(folder),record_sha256=role.digest(folder/'record.json'),physical_pass=row['physical_pass'])


def main():
    declaration=json.loads((ROOT/'declaration.json').read_text())
    assert role.digest(ROOT/'executed-study.py')==declaration['script_sha256']
    assert role.digest(study.BINARY)==declaration['binary_sha256']
    with ProcessPoolExecutor(max_workers=4) as pool:checked=list(pool.map(verify,declaration['tasks']))
    baseline_probe=json.loads((probe.ROOT/'results.json').read_text())
    build=json.loads((probe.ROOT/'build.json').read_text())
    original_probe_root=probe.ROOT;probe.ROOT=ROOT/'init-readback';probe.ROOT.mkdir(exist_ok=False)
    probe.dump(probe.ROOT/'declaration.json',dict(build=build))
    observations=[]
    for material in probe.MATERIALS:
        task=next(t for t in declaration['tasks'] if t['lane']=='coupled' and t['case']['soil']==material)
        source=Path(task['folder']);record=json.loads((source/'record.json').read_text())
        if not record['physical_pass']:
            observations.append(dict(material=material,status='not_observed_failed_candidate'));continue
        observed=probe.execute(dict(material=material,kind='coupled',case=record['case'],source=str(source),source_record_sha256=role.digest(source/'record.json')))
        original=next(r for r in baseline_probe['rows'] if r['material']==material and r['kind']=='generated')
        assert original['source']==task['source']
        pairs=[]
        for new in observed['states']:
            old=next(s for s in original['states'] if (s['stage'],s['ofe'],s['layer'])==(new['stage'],new['ofe'],new['layer']))
            if new['ofe']!=1:assert new==old
            if new['ofe']==1 and new['stage']=='ROAD_INIT_WATBAL_INIT':pairs.append(dict(before=old,after=new))
        observations.append(dict(material=material,status='observed',exact_raw_output_parity=observed['raw_output_parity'],road_initialization=pairs))
    report=dict(cases=len(checked),physical_pass=sum(r['physical_pass'] for r in checked),all_input_output_hashes_verified=True,
                all_native_audits_recomputed=True,checks=checked,initialization_observations=observations,
                script_sha256=role.digest(Path(__file__)),declaration_sha256=role.digest(ROOT/'declaration.json'),results_sha256=role.digest(ROOT/'results.json'))
    probe.dump(ROOT/'verification.json',report);probe.dump(study.HERE/'road-pore-screen-r3-verification.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','initialization_observations')},indent=2))


if __name__=='__main__':main()
