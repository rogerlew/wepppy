"""Predeclared incremental road pore/conductivity sensitivity; no production rule."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import json
import math
import shutil
import subprocess

import continuation as c
import role_boundary_assessment_r3 as role
from wepppy.wepp.soils.utils import WeppSoilUtil

HERE=Path(__file__).resolve().parent
PARENT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
ROOT=PARENT/'road-pore-screen-r3'
BINARY=Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
LANES=('pore','conductivity','coupled')
DELTA_PHI=.02
K_DIVISOR=2.4


def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def transform(text, ofes, lane):
    assert lane in LANES
    lines=text.splitlines(keepends=True)
    indices=[]
    for i,line in enumerate(lines):
        fields=line.split()
        if len(fields)==18 and fields[0].replace('.','',1).isdigit():indices.append(i)
    assert len(indices)==sum(len(o['horizons']) for o in ofes)
    allowed=[]
    for j,h in enumerate(ofes[0]['horizons']):
        if h['solthk']>200:continue
        idx=indices[j];tokens=lines[idx].split();original=list(tokens)
        assert float(tokens[0])==h['solthk']
        if lane in ('pore','coupled'):
            # Native INPUT clamps positive density below .8 to .8. Perturb the
            # consumed value, not an already clipped source value.
            bd0=min(2.,max(.8,float(tokens[1])));phi0=1-bd0/2.65
            bd1=bd0+2.65*DELTA_PHI;scale=(phi0-DELTA_PHI)/phi0
            assert .8<=bd1<=2. and 0<scale<1
            tokens[1]=format(bd1,'.12g')
            # Fixed normalized retention shape; this is an explicit research
            # translation of a pore-volume change, not a fitted road PTF.
            for k in (4,5,11,12,16,17):tokens[k]=format(float(tokens[k])*scale,'.12g')
        if lane in ('conductivity','coupled'):
            for k in (2,15):tokens[k]=format(float(tokens[k])/K_DIVISOR,'.12g')
        assert 0<float(tokens[5])<float(tokens[4])<1
        changed=[k for k,(x,y) in enumerate(zip(original,tokens)) if x!=y]
        assert set(changed)<={1,2,4,5,11,12,15,16,17}
        lines[idx]='\t'+'\t '.join(tokens)+'\n'
        allowed.append(dict(line=idx+1,depth_mm=h['solthk'],changed_columns_zero_based=changed))
    assert any(x['depth_mm']==200 for x in allowed)
    result=''.join(lines)
    # Every non-target line is byte-identical, including all fill/buffer records.
    for i,(before,after) in enumerate(zip(text.splitlines(keepends=True),lines)):
        if i+1 not in {r['line'] for r in allowed}:assert before==after
    return result,allowed


def declare():
    assert role.digest(BINARY)==role.SHA
    baseline=PARENT/'legacy-soil-control-r3/results.json';rows=json.loads(baseline.read_text())
    assert len(rows)==116
    ROOT.mkdir(exist_ok=False);tasks=[]
    for old in rows:
        case=old['case'];name='-'.join(case.values());source=role.MATRIX/'matrix-v1'/name
        record=json.loads((source/'record.json').read_text())
        assert record['physical_pass'] and record['binary_sha256']==role.SHA
        for filename,digest in record['inputs'].items():assert role.digest(source/'runs'/filename)==digest
        for lane in LANES:
            folder=ROOT/'cases'/lane/name;runs=folder/'runs';runs.mkdir(parents=True,exist_ok=False);(folder/'output').mkdir()
            for filename in record['inputs']:shutil.copy2(source/'runs'/filename,runs/filename)
            text,changes=transform((source/'runs/p1.sol').read_text(),record['soil_readback'],lane)
            (runs/'p1.sol').write_text(text);shutil.copy2(source/'runs/p1.sol',runs/'reference.sol')
            actual=WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']
            assert actual[1:]==record['soil_readback'][1:]
            for new,h in zip(actual[0]['horizons'],record['soil_readback'][0]['horizons']):
                if h['solthk']>200:assert new==h
            inputs={filename:role.digest(runs/filename) for filename in record['inputs']}
            assert {f for f in inputs if inputs[f]!=record['inputs'][f]}=={'p1.sol'}
            tasks.append(dict(lane=lane,case=case,group=old['group'],source=str(source),folder=str(folder),
                source_record_sha256=role.digest(source/'record.json'),inputs=inputs,soil_readback=actual,changes=changes,
                reference_kg_yr=old['reference_kg_yr'],width_m=record['width_m'],profile_length_m=record['profile_length_m']))
    declaration=dict(tasks=tasks,new_runs=len(tasks),binary_sha256=role.SHA,script_sha256=role.digest(Path(__file__)),
        baseline_sha256=role.digest(baseline),dependencies={n:role.digest(HERE/n) for n in ('continuation.py','role_boundary_assessment_r3.py')},
        delta_raw_porosity=DELTA_PHI,conductivity_divisor=K_DIVISOR,
        scientific_status='requires_scientific_review; incremental sensitivity, not a transferable constructed-road prescription',
        rationale='Martin et al. 2024 observed mean surface saturation decrease .02 and Ksat division 2.4 in trafficked forest soils. Extrapolation to constructed roads and uniform upper200mm is a model gap. Fixed normalized retention-shape scaling is a declared research translation; not measured FC/WP or validated Rosetta compaction response.',
        source='https://doi.org/10.1186/s13595-024-01265-4',
        invariants='Current hourly/PMET/snow, erosion, texture, OM, rock, fill/buffer, below200mm and restrictions fixed. Apply incremental changes to existing capped candidate, not repeated source conditioning. No withheld/default/UI changes.',
        acceptance='All physical outputs required; report all96misses and20controls separately; no selected-panel pass promotes a candidate. Reject any standalone recommendation with control regressions.')
    dump(ROOT/'declaration.json',declaration);dump(HERE/'road-pore-screen-r3-declaration.json',declaration)
    shutil.copy2(__file__,ROOT/'executed-study.py')
    print(f'Declared and read back {len(tasks)} input decks',flush=True)


def execute(task):
    folder=Path(task['folder']);runs=folder/'runs';output=folder/'output'
    assert role.digest(BINARY)==role.SHA
    for name,digest in task['inputs'].items():assert role.digest(runs/name)==digest
    case=dict(task['case']);case['variant']='pore_'+task['lane']
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as out,(runs/'stderr').open('w') as err:
        try:
            proc=subprocess.run([str(BINARY)],cwd=runs,stdin=inp,stdout=out,stderr=err,timeout=300);code=proc.returncode
        except subprocess.TimeoutExpired:code=None
    row=dict(task,case=case,binary_sha256=role.SHA,outputs={p.name:role.digest(p) for p in output.iterdir() if p.is_file()},
             returncode=code,status='native_failure',physical_pass=False,within=False,stdout_sha256=role.digest(runs/'stdout'),stderr_sha256=role.digest(runs/'stderr'))
    if code==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs/'stdout').read_text():
        row.update(status='completed',metrics=c.b.parse_loss(output/'H1.loss.dat',task['width_m']))
        row['audit']=c.audit(folder,case,row);row['physical_pass']=row['audit']['physical_pass']
        value=row['metrics']['sediment_export_kg_yr'];ref=task['reference_kg_yr']
        row.update(export_kg_yr=value,within=row['physical_pass'] and (.1<=value/ref<=10 if ref>1 else value<=max(1,10*ref)))
    dump(folder/'record.json',row);return row


def run():
    declaration=json.loads((ROOT/'declaration.json').read_text())
    assert role.digest(Path(__file__))==declaration['script_sha256']
    for name,digest in declaration['dependencies'].items():assert role.digest(HERE/name)==digest
    rows=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for row in pool.map(execute,declaration['tasks']):
            rows.append(row)
            if len(rows)%30==0:print(len(rows),'/348',flush=True)
    dump(ROOT/'results.json',rows)
    summarize(rows)


def summarize(rows):
    summary={}
    for lane in LANES:
        lane_rows=[r for r in rows if r['lane']==lane]
        summary[lane]=dict(cases=len(lane_rows),physical_pass=sum(r['physical_pass'] for r in lane_rows),
            groups={group:dict(cases=len(items:=[r for r in lane_rows if r['group']==group]),within=sum(r['within'] for r in items)) for group in sorted({r['group'] for r in rows})})
    report=dict(summary=summary,declaration_sha256=role.digest(ROOT/'declaration.json'),results_sha256=role.digest(ROOT/'results.json'))
    dump(HERE/'road-pore-screen-r3-summary.json',report);dump(ROOT/'summary.json',report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','run'))
    {'declare':declare,'run':run}[parser.parse_args().action]()
