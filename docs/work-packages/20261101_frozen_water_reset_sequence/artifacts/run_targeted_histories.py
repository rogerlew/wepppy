"""Retarget an existing observation marker; identical executable and model inputs."""
import argparse,json,math,os,runpy,shutil,subprocess,sys,time
from pathlib import Path
from audit_resets_v2 import sha
HERE=Path(__file__).resolve().parent
RAW=Path('out/frozen-water-reset-20261101').resolve()
OLD=Path('out/frozen-water-history-20261101').resolve()
OLDPUB=Path('docs/work-packages/20261101_frozen_water_history_ownership/artifacts').resolve()
TARGETS={'zero-ks1':(3,20),'normal-ks1':(3,20),'high-ks1':(7,344)}
ENV={**os.environ,'PATH':'/usr/bin:/bin','FC':'/usr/bin/gfortran'}
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def freeze():
    build=json.loads((OLD/'campaign-v1/build-receipt.json').read_text())['after']
    files={str(OLD/'campaign-v1/build'/n):v['sha256'] for n,v in build.items()}
    for p in [Path(__file__),HERE/'targeted-declaration.md',OLDPUB/'run_history_campaign.py',OLDPUB/'read_history.py',HERE/'audit_resets_v2.py',HERE/'check_targeted_reader.py']:
        files[str(p)]=sha(p)
    inputs={}
    for scenario in TARGETS:
        root=OLD/'campaign-v1'/scenario/'observer';r=json.loads((root/'pre-execution.json').read_text());inputs[scenario]=r['inputs']
        for name,digest in r['inputs'].items():files[str(root/'runs'/name)]=digest
        for name in ['receipt.json']:
            p=root.parent/name;files[str(p)]=sha(p)
    for p,digest in files.items():
        if sha(Path(p))!=digest:raise ValueError('Declared source/input drift')
    libs=json.loads((OLD/'observer-runtime.json').read_text())['libraries']
    save(RAW/'targeted-freeze.json',dict(files=files,libraries=libs,inputs=inputs,targets=TARGETS,invocations=3))
def read_window(path,year,day):
    groups={};operands={};counts={}
    for line in path.read_text().splitlines():
        c=line.split()
        if len(c)!=11:raise ValueError('BPO shape')
        tag=c[0];y,d,ofe,ix=map(int,c[1:5]);v=list(map(float,c[5:]))
        if y!=year or d not in (day-1,day) or not all(math.isfinite(x) for x in v):raise ValueError('BPO clock/nonfinite')
        counts[tag]=counts.get(tag,0)+1
        if tag in {'BP_WBH_BEFORE_W','BP_WBH_PURK_W','BP_WBH_AFTER_W'}:
            hour,layer=divmod(ix,100);key=(y,d,ofe,hour)
            if not 1<=hour<=24 or not 1<=layer<=10:raise ValueError('BPO support')
            support=groups.setdefault(key,{}).setdefault(tag,{})
            if layer in support:raise ValueError('Duplicate BPO layer')
            support[layer]=v
        elif tag in {'BP_WBH_ALLOC','BP_WBH_FLUX','BP_WBH_SEEP','BP_WBH_RETURN'}:
            key=(y,d,ofe,ix);slot=operands.setdefault(key,{})
            if tag in slot:raise ValueError('Duplicate BPO operand')
            slot[tag]=v
    expected={(year,d,o,h) for d in (day-1,day) for o in (1,2,3) for h in range(1,25)}
    if set(groups)!=expected or set(operands)!=expected:raise ValueError('Incomplete two-day hourly support')
    rows=[]
    for key,stages in sorted(groups.items()):
        if set(stages)!={'BP_WBH_BEFORE_W','BP_WBH_PURK_W','BP_WBH_AFTER_W'} or any(set(a)!=set(range(1,11)) for a in stages.values()):raise ValueError('Incomplete stages/layers')
        if set(operands[key])!={'BP_WBH_ALLOC','BP_WBH_FLUX','BP_WBH_SEEP','BP_WBH_RETURN'}:raise ValueError('Incomplete flux operands')
        rows.append(dict(clock=list(key),stages=stages,operands=operands[key],
            top_before=stages['BP_WBH_BEFORE_W'][1][0],top_after_purk=stages['BP_WBH_PURK_W'][1][0],top_after=stages['BP_WBH_AFTER_W'][1][0]))
    return dict(records=counts,hourly_records=rows)
def run():
    frozen=json.loads((RAW/'targeted-freeze.json').read_text());approval=json.loads((RAW/'targeted-approval.json').read_text())
    if approval['status']!='approved' or approval['freeze_sha256']!=sha(RAW/'targeted-freeze.json'):raise ValueError('No exact review')
    for p,digest in {**frozen['files'],**frozen['libraries'],**approval['reviews']}.items():
        if sha(Path(p))!=digest:raise ValueError('Dependency drift')
    sys.path.insert(0,str(OLDPUB));validate=runpy.run_path(str(OLDPUB/'run_history_campaign.py'))['output_check']
    root=RAW/'targeted-v1';root.mkdir();results=[];binary=OLD/'campaign-v1/build/src/wepp'
    for scenario,(year,day) in TARGETS.items():
        dest=root/scenario;runs=dest/'runs';runs.mkdir(parents=True);(dest/'output').mkdir()
        source=OLD/'campaign-v1'/scenario/'observer';old=json.loads((source.parent/'receipt.json').read_text())['members'][1]
        for name in frozen['inputs'][scenario]:shutil.copyfile(source/'runs'/name,runs/name)
        (runs/'buffer_observe.on').write_text(f'{year} {day}\n')
        inputs={n:sha(runs/n) for n in frozen['inputs'][scenario]}
        if [n for n in inputs if inputs[n]!=frozen['inputs'][scenario][n]]!=['buffer_observe.on']:raise ValueError('Unexpected input mutation')
        r=dict(PATH=ENV['PATH'],FC=ENV['FC'],scenario=scenario,inputs=inputs,binary_sha256=sha(binary),started=time.time(),command=[str(binary)],cwd=str(runs),timeout_seconds=900)
        save(dest/'pre-execution.json',r)
        with (runs/'p1.run').open('rb') as stdin,(runs/'stdout').open('xb') as stdout,(runs/'stderr').open('xb') as stderr:
            try:
                proc=subprocess.run([str(binary)],cwd=runs,stdin=stdin,stdout=stdout,stderr=stderr,env=ENV,timeout=900);r.update(returncode=proc.returncode,status='completed')
            except subprocess.TimeoutExpired:r.update(returncode=None,status='timeout')
        r['elapsed_seconds']=time.time()-r['started'];r['stdout_sha256']=sha(runs/'stdout');r['stderr_sha256']=sha(runs/'stderr');save(dest/'execution-result.json',r)
        try:
            if r['returncode']!=0 or 'WEPP COMPLETED' not in (runs/'stdout').read_text():raise ValueError('Native completion failed')
            r.update(validate(dest))
            if r['output_hashes']!=old['output_hashes']:raise ValueError('Ordinary output parity failed')
            trace=sha(runs/'frwatc-history.txt')
            if trace!=old['trace']['trace_sha256']:raise ValueError('Full fine/coarse trace parity failed')
            if any(sha(runs/n)!=v for n,v in inputs.items()):raise ValueError('Runtime input mutation')
            r.update(passed=True,trace_sha256=trace,buffer_observation_sha256=sha(runs/'buffer-observation.txt'),window=read_window(runs/'buffer-observation.txt',year,day))
        except (ValueError,OSError,KeyError) as error:r.update(passed=False,error=str(error))
        save(dest/'readback.json',r);results.append(r);print(scenario,r['passed'],flush=True)
    for p,digest in {**frozen['files'],**frozen['libraries']}.items():
        if sha(Path(p))!=digest:raise ValueError('Original dependency changed')
    save(root/'receipt.json',dict(cases=results,passed=all(r['passed'] for r in results),frozen_dependencies_unchanged=True))
    if not all(r['passed'] for r in results):raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);a=p.parse_args();freeze() if a.action=='freeze' else run()
