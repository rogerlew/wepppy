"""Run twelve declared controls against complete unchanged FRWATC."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from audit_resets_v2 import decompose, stock, sha

HERE=Path(__file__).resolve().parent
RAW=Path('out/frozen-water-reset-20261101').resolve()
SOURCE=Path('out/sift-rock-frozen-water-20261101/frozen-campaign-v1/build').resolve()
PREVIOUS=Path('docs/work-packages/20261101_sift_rock_frozen_water/artifacts')
ENV={**os.environ,'PATH':'/usr/bin:/bin','FC':'/usr/bin/gfortran'}
FLAGS=['-O0','-fcheck=all','-finit-real=snan','-ffpe-trap=invalid,zero,overflow','-ffixed-line-length-none']


def save(path,data):
    with path.open('x') as stream:json.dump(data,stream,indent=2,allow_nan=False);stream.write('\n')


def execute(command,cwd,stem,stdin=None):
    record=dict(started=time.time(),command=list(map(str,command)),cwd=str(cwd),PATH=ENV['PATH'],FC=ENV['FC'],timeout_seconds=60)
    with (cwd/(stem+'.stdout')).open('xb') as stdout,(cwd/(stem+'.stderr')).open('xb') as stderr:
        source=stdin.open('rb') if stdin else subprocess.DEVNULL
        try:
            r=subprocess.run(record['command'],cwd=cwd,stdin=source,stdout=stdout,stderr=stderr,env=ENV,timeout=60)
            record.update(status='completed',returncode=r.returncode)
        except subprocess.TimeoutExpired:record.update(status='timeout',returncode=None)
        finally:
            if stdin:source.close()
    record.update(elapsed_seconds=time.time()-record['started'],stdout_sha256=sha(cwd/(stem+'.stdout')),stderr_sha256=sha(cwd/(stem+'.stderr')))
    save(cwd/(stem+'-result.json'),record);return record


def read(text,case):
    states={};inactive=None
    for line in text.splitlines():
        c=line.split()
        if not c:raise ValueError('Empty native row')
        if c[0]=='INACTIVE_ERRORS':
            if inactive is not None or len(c)!=2:raise ValueError('Duplicate sentinel result')
            inactive=int(c[1]);continue
        if c[0] not in {'C','F'} or len(c)!=(14 if c[0]=='C' else 8):raise ValueError('Native output shape')
        stage,i,j=map(int,c[1:4]);values=list(map(float,c[4:]))
        if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite native output')
        layers=states.setdefault(stage,{})
        if c[0]=='C':
            if i in layers or j!=len(case['layers'][i-1]['f']):raise ValueError('Duplicate or wrong coarse support')
            layers[i]=dict(zip('dg dry ul saxfc frozen frzw nw st yst soilw'.split(),values),n=j,available=1,fine={})
        else:
            if i not in layers or j in layers[i]['fine'] or not 1<=j<=layers[i]['n']:raise ValueError('Missing/duplicate fine support')
            layers[i]['fine'][j]=dict(zip(['f','sw','ice','u'],values))
    expected={0,1} if case['sequence']==1 else {0,1,2,3,4}
    if set(states)!=expected or inactive!=0:raise ValueError('Missing stage or inactive mutation')
    for layers in states.values():
        if set(layers)!=set(range(1,len(case['layers'])+1)):raise ValueError('Missing layer')
        for a in layers.values():
            if set(a['fine'])!=set(range(1,a['n']+1)):raise ValueError('Missing fine cell')
    return states


def freeze():
    bindings=json.loads((PREVIOUS/'frozen-design-source-bindings.json').read_text())['files']
    files={str(SOURCE/n):r['sha256'] for n,r in bindings.items()}
    for n in ['reset_driver.for','reset-cases.json','declare_cases.py','audit_resets_v2.py','run_reset_controls.py','control-declaration.md']:
        files[str(HERE/n)]=sha(HERE/n)
    files[str(PREVIOUS/'frozen-design-source-bindings.json')]=sha(PREVIOUS/'frozen-design-source-bindings.json')
    tools={str(Path(p).resolve()):sha(Path(p)) for p in ['/usr/bin/gfortran','/usr/bin/as','/usr/bin/ld']}
    for name in ['f951','collect2']:
        p=Path(subprocess.check_output(['/usr/bin/gfortran','-print-prog-name='+name],env=ENV,text=True).strip()).resolve();tools[str(p)]=sha(p)
    libraries=json.loads(Path('out/frozen-water-history-20261101/observer-runtime.json').read_text())['libraries']
    for p,digest in {**files,**tools,**libraries}.items():
        if sha(Path(p))!=digest:raise ValueError('Pre-execution source/tool drift: '+p)
    save(RAW/'control-freeze.json',dict(files=files,tools=tools,libraries=libraries,flags=FLAGS,invocations=12))


def run():
    frozen=json.loads((RAW/'control-freeze.json').read_text());approval=json.loads((RAW/'control-approval.json').read_text())
    if approval['status']!='approved' or approval['freeze_sha256']!=sha(RAW/'control-freeze.json'):raise ValueError('Missing exact prereview')
    dependencies={**frozen['files'],**frozen['tools'],**frozen['libraries']}
    dependencies.update(approval['reviews'])
    for p,digest in dependencies.items():
        if sha(Path(p))!=digest:raise ValueError('Dependency drift: '+p)
    root=RAW/'controls-v1';root.mkdir();build=root/'build';build.mkdir()
    names=json.loads((PREVIOUS/'frozen-design-source-bindings.json').read_text())['files']
    for n in names:shutil.copyfile(SOURCE/n,build/n)
    shutil.copyfile(HERE/'reset_driver.for',build/'driver.for')
    result=execute(['/usr/bin/gfortran',*FLAGS,'driver.for','frwatc.for','-o','probe'],build,'build')
    if result['returncode']!=0:raise RuntimeError('Compile failed; retained')
    runtime_text=subprocess.check_output(['/usr/bin/ldd',str(build/'probe')],env=ENV,text=True)
    runtime={}
    for line in runtime_text.splitlines():
        for word in line.split():
            if word.startswith('/'):
                path=Path(word).resolve();runtime[str(path)]=sha(path)
    save(root/'runtime.json',dict(ldd=runtime_text,libraries=runtime,binary_sha256=sha(build/'probe')))
    if runtime!=frozen['libraries']:raise ValueError('Linked runtime differs from frozen declaration')
    cases=json.loads((HERE/'reset-cases.json').read_text())
    if len(cases)!=12 or len({c['id'] for c in cases})!=12:raise ValueError('Panel drift')
    results=[]
    for case in cases:
        dest=root/case['id'];dest.mkdir();save(dest/'case.json',case)
        text=f"{len(case['layers'])} {case['sequence']}\n"
        for a in case['layers']:
            text+=' '.join(map(str,[len(a['f']),*[a[k] for k in ['h','d','p','nw','saxfc','st','yst']]]))+'\n'
            for values in zip(a['f'],a['sw'],a['ice']):text+=' '.join(map(str,values))+'\n'
        (dest/'stdin.txt').write_text(text)
        result=execute([build/'probe'],dest,'execution',dest/'stdin.txt');result['id']=case['id']
        try:
            if result['returncode']!=0:raise ValueError('Native process failed')
            states=read((dest/'execution.stdout').read_text(),case)
            steps=[(0,1)] if case['sequence']==1 else [(2,3),(3,4)]
            resets=[]
            for pre,post in steps:
                for i,a in states[pre].items():
                    if a['st']==0:resets.append(dict(pre=pre,post=post,layer=i,**decompose(a,states[post][i])))
            if case['sequence']==2:
                if states[0][1]['nw']<=0 or states[1][1]['nw']!=0:raise ValueError('Clearing positive control failed')
                if states[3]!=states[4]:raise ValueError('Repeated reset changed state')
                if any(abs(x['fine_change_m'])>x['reconstruction_bound_m'] for x in resets if x['pre']==3):raise ValueError('Repeated reset water change')
            result.update(passed=True,states=states,resets=resets)
        except (ValueError,KeyError,IndexError) as error:result.update(passed=False,error=str(error))
        save(dest/'readback.json',result);results.append(result)
    by={r['id']:r for r in results};pairs={}
    if all(r['passed'] for r in results):
        zero=by['mismatch-zero']['states'];positive=by['mismatch-positive']['states']
        pairs['positive_subthreshold_no_fine_change']=positive[0][1]['fine']==positive[1][1]['fine']
        pairs['zero_branch_resets_wet_fine']=zero[0][1]['fine']!=zero[1][1]['fine']
        cz=by['carry-zero-middle']['states'];cp=by['carry-positive-middle']['states']
        pairs['carry_reaches_bottom_through_zero_middle']=stock(cz[1][3])['liquid']<stock(cz[0][3])['liquid']
        pairs['positive_middle_consumes_carry_bottom_unchanged']=cp[0][3]['fine']==cp[1][3]['fine']
    passed=all(r['passed'] for r in results) and len(pairs)==4 and all(pairs.values())
    for p,digest in dependencies.items():
        if sha(Path(p))!=digest:raise ValueError('Dependency changed during control campaign')
    save(root/'receipt.json',dict(passed=passed,cases=results,paired_checks=pairs,binary_sha256=sha(build/'probe'),
         build_files={p.name:sha(p) for p in build.iterdir()},freeze_sha256=sha(RAW/'control-freeze.json'),all_dependencies_unchanged=True))
    print(json.dumps(dict(passed=passed,cases=len(results),paired_checks=pairs)))
    if not passed:raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);a=p.parse_args()
    freeze() if a.action=='freeze' else run()
