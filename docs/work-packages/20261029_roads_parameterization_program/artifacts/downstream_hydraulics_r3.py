"""Same-format downstream conductivity controls after rejected legacy bridge."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse,json,re,shlex,shutil,subprocess
import continuation as c
import role_boundary_assessment_r3 as role
from wepppy.wepp.soils.utils import WeppSoilUtil
HERE=Path(__file__).resolve().parent
PARENT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
ROOT=PARENT/'downstream-hydraulics-r3'
BINARY=Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
LANES=('fill_fixed','buffer_cap','both')


def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def transform(text,source,legacy,lane):
    assert lane in LANES
    lines=text.splitlines(keepends=True)
    # Match native OFE land-use/adjustment lines, not quoted soil-name lines.
    flags=[i for i,l in enumerate(lines) if len(t:=shlex.split(l))==5 and t[0] in ('0','1') and t[1] in ('bare','forest')]
    assert len(flags)==3
    assert source[1]['ksatadj']=='1' and source[2]['ksatadj']=='0'
    if lane in ('fill_fixed','both'):
        i=flags[1];lines[i]=re.sub(r'^(\s*)1',r'\g<1>0',lines[i],count=1)
    cap=float(legacy[2]['avke']);assert cap>0
    horizon_indices=[i for i,l in enumerate(lines) if len(t:=l.split())==18 and t[0].replace('.','',1).isdigit()]
    assert len(horizon_indices)==sum(len(o['horizons']) for o in source)
    offset=sum(len(o['horizons']) for o in source[:2])
    if lane in ('buffer_cap','both'):
        for j,h in enumerate(source[2]['horizons']):
            if h['solthk']>200:continue
            i=horizon_indices[offset+j]
            # Replace only conductivity token; leave appended PTF predictions
            # and all other text unchanged, as in existing role conductivity caps.
            spans=list(re.finditer(r'\S+',lines[i]));s=spans[2]
            lines[i]=lines[i][:s.start()]+format(min(h['ksat'],cap),'.12g')+lines[i][s.end():]
    result=''.join(lines)
    changes=[i+1 for i,(a,b) in enumerate(zip(text.splitlines(keepends=True),lines)) if a!=b]
    assert changes
    return result,changes,cap


def declare():
    assert role.digest(BINARY)==role.SHA
    oldpath=PARENT/'legacy-soil-control-r3/results.json';rows=json.loads(oldpath.read_text());assert len(rows)==116
    ROOT.mkdir(exist_ok=False);tasks=[]
    for row in rows:
        case=row['case'];name='-'.join(case.values());source=role.MATRIX/'matrix-v1'/name
        original=json.loads((source/'record.json').read_text());assert original['physical_pass']
        legacy_folder=PARENT/'legacy-soil-control-r3/matrix-v1'/name
        legacy_record=json.loads((legacy_folder/'record.json').read_text())
        assert role.digest(legacy_folder/'runs/p1.sol')==legacy_record['inputs']['p1.sol']
        legacy=WeppSoilUtil(str(legacy_folder/'runs/p1.sol')).obj['ofes']
        for lane in LANES:
            folder=ROOT/'cases'/lane/name;runs=folder/'runs';runs.mkdir(parents=True);(folder/'output').mkdir()
            for fn,digest in original['inputs'].items():
                assert role.digest(source/'runs'/fn)==digest;shutil.copy2(source/'runs'/fn,runs/fn)
            text,changes,cap=transform((source/'runs/p1.sol').read_text(),original['soil_readback'],legacy,lane)
            (runs/'p1.sol').write_text(text);shutil.copy2(source/'runs/p1.sol',runs/'reference.sol')
            actual=WeppSoilUtil(str(runs/'p1.sol')).obj['ofes'];assert actual[0]==original['soil_readback'][0]
            inputs={n:role.digest(runs/n) for n in original['inputs']}
            assert {n for n in inputs if inputs[n]!=original['inputs'][n]}=={'p1.sol'}
            tasks.append(dict(case=case,lane=lane,group=row['group'],source=str(source),folder=str(folder),
                source_record_sha256=role.digest(source/'record.json'),legacy_record_sha256=role.digest(legacy_folder/'record.json'),
                buffer_cap_mm_h=cap,changed_lines=changes,inputs=inputs,soil_readback=actual,
                width_m=original['width_m'],profile_length_m=original['profile_length_m'],reference_kg_yr=row['reference_kg_yr']))
    d=dict(tasks=tasks,new_runs=348,binary_sha256=role.SHA,script_sha256=role.digest(Path(__file__)),
        dependencies={n:role.digest(HERE/n) for n in ('continuation.py','role_boundary_assessment_r3.py')},
        source_panel_sha256=role.digest(oldpath),
        contract='Same generated9002 format throughout. Fill lane: only fill ksatadj1->0. Buffer lane: only buffer upper200mm K=min(existing,configuration-matched legacy buffer avke). Both combines. No legacy role material/state copying, no road changes or road multiplier, no density/retention/erosion/restriction/runtime changes.',
        rationale='Isolate saturation-dependent bare-fill conductivity and forest-buffer surface conductivity as component hypotheses after format equivalence failed. Legacy avke is a declared parameter prior, not inferred equality to generated horizon K.',
        scientific_status='Diagnostic; physical transfer unvalidated. No production candidate promotion, per-case fitting, withheld or UI changes.')
    dump(ROOT/'declaration.json',d);dump(HERE/'downstream-hydraulics-r3-declaration.json',d);shutil.copy2(__file__,ROOT/'executed-study.py')
    print('Declared 348 same-format downstream controls',flush=True)


def execute(task):
    folder=Path(task['folder']);runs=folder/'runs';out=folder/'output';assert role.digest(BINARY)==role.SHA
    for n,d in task['inputs'].items():assert role.digest(runs/n)==d
    case=dict(task['case'],variant=task['lane'])
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        try:code=subprocess.run([str(BINARY)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300).returncode
        except subprocess.TimeoutExpired:code=None
    row=dict(task,case=case,binary_sha256=role.SHA,returncode=code,outputs={p.name:role.digest(p) for p in out.iterdir() if p.is_file()},
        stdout_sha256=role.digest(runs/'stdout'),stderr_sha256=role.digest(runs/'stderr'),status='native_failure',physical_pass=False,within=False)
    if code==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs/'stdout').read_text():
        row.update(status='completed',metrics=c.b.parse_loss(out/'H1.loss.dat',task['width_m']))
        row['audit']=c.audit(folder,case,row);row['physical_pass']=row['audit']['physical_pass']
        value=row['metrics']['sediment_export_kg_yr'];ref=row['reference_kg_yr']
        row.update(export_kg_yr=value,within=row['physical_pass'] and (.1<=value/ref<=10 if ref>1 else value<=max(1,10*ref)))
    dump(folder/'record.json',row);return row


def verify(task):
    folder=Path(task['folder']);row=json.loads((folder/'record.json').read_text());source=Path(task['source'])
    assert role.digest(source/'record.json')==task['source_record_sha256'];before=json.loads((source/'record.json').read_text())['soil_readback']
    for section,subdir in [('inputs','runs'),('outputs','output')]:
        for n,d in row[section].items():assert role.digest(folder/subdir/n)==d
    actual=WeppSoilUtil(str(folder/'runs/p1.sol')).obj['ofes'];assert actual==row['soil_readback']==task['soil_readback']
    restored=json.loads(json.dumps(actual))
    if task['lane'] in ('fill_fixed','both'):
        assert actual[1]['ksatadj']=='0';restored[1]['ksatadj']=before[1]['ksatadj']
    if task['lane'] in ('buffer_cap','both'):
        for i,h in enumerate(actual[2]['horizons']):
            if h['solthk']<=200:
                assert h['ksat']==min(before[2]['horizons'][i]['ksat'],task['buffer_cap_mm_h'])
                restored[2]['horizons'][i]['ksat']=before[2]['horizons'][i]['ksat']
    assert restored==before
    if row['status']=='completed':
        assert c.b.parse_loss(folder/'output/H1.loss.dat',row['width_m'])==row['metrics']
        assert c.audit(folder,row['case'],row)==row['audit']
    return row


def report(rows,verified):
    groups={lane:{group:dict(cases=len(items:=[r for r in rows if r['lane']==lane and r['group']==group]),
        physical_pass=sum(r['physical_pass'] for r in items),within=sum(r['within'] for r in items)) for group in sorted({r['group'] for r in rows})} for lane in LANES}
    d=dict(cases=len(rows),physical_pass=sum(r['physical_pass'] for r in rows),groups=groups,freshly_verified=verified,
        declaration_sha256=role.digest(ROOT/'declaration.json'),results_sha256=role.digest(ROOT/'results.json'))
    name='verification' if verified else 'summary';dump(ROOT/(name+'.json'),d);dump(HERE/f'downstream-hydraulics-r3-{name}.json',d)
    print(json.dumps(d,indent=2),flush=True)


def run(verification=False):
    d=json.loads((ROOT/'declaration.json').read_text());assert role.digest(Path(__file__))==d['script_sha256']
    for name,digest in d['dependencies'].items():assert role.digest(HERE/name)==digest
    rows=[]
    with ProcessPoolExecutor(max_workers=4 if verification else 8) as pool:
        for row in pool.map(verify if verification else execute,d['tasks']):
            rows.append(row)
            if len(rows)%40==0:print(len(rows),'/348',flush=True)
    if not verification:dump(ROOT/'results.json',rows)
    report(rows,verification)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('declare','run','verify'));a=p.parse_args().action
    if a=='declare':declare()
    else:run(a=='verify')
