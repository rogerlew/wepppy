"""Study-only legacy-to-9002 equivalence preflight; never a production converter."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import json
import shlex
import shutil
import subprocess
import hashlib

import hydraulic_init_probe_r3 as probe
HERE=Path(__file__).resolve().parent
ROOT=probe.PARENT/'legacy-format-bridge-r3'


def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return probe.sha(p)


def convert(text):
    lines=[line for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    assert float(lines[0])==98.4 and lines[2].split()==['3','0']
    out=['9002','# Diagnostic format bridge: native-estimation sentinels; not writer-valid production soil.',lines[1],lines[2]]
    assert len(lines)==9
    for i in range(3):
        header=shlex.split(lines[3+2*i]);h=lines[4+2*i].split()
        assert header[2]=='1' and len(h)==6
        depth=float(h[0]);assert 200<=depth<=1800
        out.append("0 'bare' 'loam' 1 1")
        out.append(' '.join([repr(header[0]),repr(header[1]),'2',*header[3:8]]))
        # Native INPUT extends the final horizon by 200 mm. The duplicate
        # terminal 200 in a road is deliberate: it supplies the native-added
        # subsoil with estimation sentinels, not a production zero-thickness layer.
        for boundary,k in [('200',header[8]),(h[0],'0')]:
            out.append(' '.join([boundary,'0',k,'0','0','0',*h[1:],'0','0','0','0','0','0','0']))
        out.append('0 0 0')
    return '\n'.join(out)+'\n'


def states(stdout):
    return [line for line in stdout.splitlines() if line.startswith('ROAD_INIT_')]


def declare():
    old=json.loads((probe.ROOT/'results.json').read_text())
    tasks=[]
    ROOT.mkdir(exist_ok=False)
    for row in old['rows']:
        if row['kind']!='legacy':continue
        source=Path(row['source']);record=json.loads((source/'record.json').read_text())
        folder=ROOT/'cases'/row['material'];runs=folder/'runs';runs.mkdir(parents=True);(folder/'output').mkdir()
        for name,digest in record['inputs'].items():
            assert sha(source/'runs'/name)==digest;shutil.copy2(source/'runs'/name,runs/name)
        (runs/'p1.sol').write_text(convert((runs/'p1.sol').read_text()))
        inputs={n:sha(runs/n) for n in record['inputs']}
        assert {n for n in inputs if inputs[n]!=record['inputs'][n]}=={'p1.sol'}
        tasks.append(dict(material=row['material'],case=row['case'],source=str(source),folder=str(folder),
            source_record_sha256=sha(source/'record.json'),inputs=inputs,
            observation_source=str(probe.ROOT/'cases'/(row['material']+'-legacy'))))
    build=json.loads((probe.ROOT/'build.json').read_text())
    declaration=dict(tasks=tasks,build=build,script_sha256=sha(Path(__file__)),
        contract='Seven material preflight before full116panel. Change only soil syntax; missing-field estimation sentinels preserved, explicit top200 K=legacy avke, lower K sentinel, anisotropy zero. Preserve native final200mm extension. No role substitution unless exact output/state equivalence passes.',
        limitation='Diagnostic generator deliberately bypasses production validation; duplicate final200 boundary and zero FC/WP/BD/VG values are not deployable soils. No production/default changes.')
    dump(ROOT/'declaration.json',declaration);dump(HERE/'legacy-format-bridge-r3-declaration.json',declaration)
    shutil.copy2(__file__,ROOT/'executed-study.py')


def execute(task):
    source=Path(task['source']);old=json.loads((source/'record.json').read_text());folder=Path(task['folder']);runs=folder/'runs';out=folder/'output'
    assert sha(source/'record.json')==task['source_record_sha256']
    for n,d in task['inputs'].items():assert sha(runs/n)==d
    build=json.loads((ROOT/'declaration.json').read_text())['build'];binary=Path(build['binary']);assert sha(binary)==build['binary_sha256']
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        try:code=subprocess.run([str(binary)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300).returncode
        except subprocess.TimeoutExpired:code=None
    current={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    for n,d in old['outputs'].items():assert sha(source/'output'/n)==d
    observed=Path(task['observation_source']);original_states=states((observed/'runs/stdout').read_text());new_states=states((runs/'stdout').read_text())
    differences=[]
    for before,after in zip(original_states,new_states):
        if before!=after:differences.append(dict(before=before,after=after))
    result=dict(task,returncode=code,completed=code==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs/'stdout').read_text(),
        outputs=current,output_inventory_equal=set(current)==set(old['outputs']),changed_outputs=sorted(n for n in set(current)|set(old['outputs']) if current.get(n)!=old['outputs'].get(n)),
        initialized_states_equal=bool(new_states) and original_states==new_states,state_rows_before=len(original_states),state_rows_after=len(new_states),state_differences=differences,
        stdout_sha256=sha(runs/'stdout'),stderr_sha256=sha(runs/'stderr'))
    dump(folder/'record.json',result);return result


def run():
    declaration=json.loads((ROOT/'declaration.json').read_text());assert sha(Path(__file__))==declaration['script_sha256']
    with ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(execute,declaration['tasks']))
    report=dict(cases=len(rows),completed=sum(r['completed'] for r in rows),exact_output_matches=sum(not r['changed_outputs'] for r in rows),
        initialized_state_matches=sum(r['initialized_states_equal'] for r in rows),rows=rows)
    dump(ROOT/'results.json',report);dump(HERE/'legacy-format-bridge-r3-results.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('declare','run'));{'declare':declare,'run':run}[p.parse_args().action]()
