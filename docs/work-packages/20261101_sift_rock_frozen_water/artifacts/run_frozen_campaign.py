"""Run declared full unchanged FRWATC fixtures; retain unassigned residuals."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

FIELDS = ['h','d','ul','saxfc','frozen','frzw','nw','st','yst','soilw']
TOL = 2e-8


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(command, cwd, prefix, env, stdin=None):
    receipt={'command':command,'cwd':str(cwd),'PATH':env['PATH'],'FC':env['FC']}
    try:
        result=subprocess.run(command,cwd=cwd,input=stdin,env=env,capture_output=True,text=True,timeout=60)
    except subprocess.TimeoutExpired as error:
        # Research process boundary: retain partial evidence before explicit failure.
        for suffix,value in [('stdout',error.stdout),('stderr',error.stderr)]:
            value=value or b''
            (cwd/(prefix+'.'+suffix)).write_bytes(value if isinstance(value,bytes) else value.encode())
        receipt.update(status='timeout',returncode=None)
        (cwd/(prefix+'-result.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        raise
    (cwd/(prefix+'.stdout')).write_text(result.stdout)
    (cwd/(prefix+'.stderr')).write_text(result.stderr)
    receipt.update(status='completed',returncode=result.returncode)
    (cwd/(prefix+'-result.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    return result


def read_states(text):
    states={};outside=None;inactive=None
    for line in text.splitlines():
        cols=line.split()
        if not cols:continue
        if cols[0]=='STATE':
            if len(cols)!=13:raise ValueError('STATE shape')
            stage=int(cols[1]);values=list(map(float,cols[3:]))
            if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite coarse state')
            if stage in states:raise ValueError('Duplicate STATE')
            states[stage]={'fine_ids':[], 'n':int(cols[2]),'coarse':dict(zip(FIELDS,values)),'fine':[]}
        elif cols[0]=='FINE':
            if len(cols)!=7:raise ValueError('FINE shape')
            values=list(map(float,cols[3:]))
            if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite fine state')
            stage=int(cols[1]);index=int(cols[2])
            if stage not in states or index in states[stage]['fine_ids']:raise ValueError('Duplicate or orphan FINE')
            states[stage]['fine_ids'].append(index)
            states[stage]['fine'].append(dict(zip(['f','sw','ice','u'],values)))
        elif cols[0]=='OUTSIDE':outside=list(map(float,cols[1:]))
        elif cols[0]=='INACTIVE_ERRORS':inactive=int(cols[1])
        else:raise ValueError('Unexpected driver output')
    if outside!=[-777.]*4 or inactive!=0:raise ValueError('Inactive-support mutation')
    for state in states.values():
        c=state['coarse'];fine=state['fine']
        if state['fine_ids']!=list(range(1,state['n']+1)):raise ValueError('Missing fine support')
        liquid=sum(f['sw']*f['u'] for f in fine)+c['nw'];ice=sum(f['ice'] for f in fine)
        coarse_liquid=c['st']+c['d']*(c['h']-c['frozen'])
        coarse_ice=c['frzw']+c['d']*c['frozen']
        if min(liquid,ice,coarse_liquid,coarse_ice)<-TOL:raise ValueError('Negative physical stock')
        state['stocks']={'fine_liquid':liquid,'fine_ice':ice,'fine_total':liquid+ice,
            'coarse_liquid':coarse_liquid,'coarse_ice':coarse_ice,'coarse_total':coarse_liquid+coarse_ice,
            'soilw_minus_coarse_liquid':c['soilw']-coarse_liquid,
            'geometry_residual':sum(f['f']+f['u'] for f in fine)-c['h'],
            'supports_above_native_1mm':sum(f['u']>0.0010000000474974513 for f in fine)}
        if not all(math.isfinite(x) for x in state['stocks'].values()):raise ValueError('Nonfinite derived stock')
    return states


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',required=True,type=Path);ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    here=Path(__file__).resolve().parent
    bindings=json.loads((here/'frozen-design-source-bindings.json').read_text())['files']
    build=a.out/'build';build.mkdir()
    for name,record in bindings.items():
        if sha(a.source/name)!=record['sha256']:raise ValueError('Native source drift: '+name)
        shutil.copyfile(a.source/name,build/name)
    shutil.copyfile(here/'frozen_driver.for',build/'driver.for')
    env=dict(os.environ);env['PATH']='/usr/bin:/bin:'+env.get('PATH','');env['FC']='/usr/bin/gfortran'
    flags=['-O0','-fcheck=all','-finit-real=snan','-ffpe-trap=invalid,zero,overflow','-ffixed-line-length-none']
    compiler=execute(['/usr/bin/gfortran','--version'],build,'compiler',env)
    if compiler.returncode:raise RuntimeError('Compiler unavailable')
    for source,stem in [('frwatc.for','frwatc'),('driver.for','driver')]:
        result=execute(['/usr/bin/gfortran',*flags,'-c',source,'-o',stem+'.o'],build,'compile-'+stem,env)
        if result.returncode:raise RuntimeError('Compile failure: '+stem)
    binary=build/'probe'
    result=execute(['/usr/bin/gfortran',*flags,'driver.o','frwatc.o','-o',str(binary)],build,'link',env)
    if result.returncode:raise RuntimeError('Link failure')
    cases=json.loads((here/'frozen-cases.json').read_text());results=[];failures=[]
    for case in cases:
        root=a.out/case['id'];root.mkdir();b=case['inputs'];modes=case['modes'];n=len(b['f'])
        stdin=f"{n} {modes[0]} {modes[1] if len(modes)>1 else -1} {case['delta']:.17g}\n"
        stdin+=' '.join(format(b[k],'.17g') for k in ['h','d','p','nw','saxfc'])+'\n'
        stdin+=''.join(' '.join(format(x,'.17g') for x in row)+'\n' for row in zip(b['f'],b['sw'],b['ice']))
        (root/'stdin.txt').write_text(stdin);(root/'case.json').write_text(json.dumps(case,indent=2)+'\n')
        try:
            result=execute([str(binary)],root,'execution',env,stdin)
            if result.returncode:
                raise ValueError('process_failure: '+str(result.returncode))
            states=read_states(result.stdout)
            if set(states)!={0,1,2,*([3] if len(modes)>1 else [])}:raise ValueError('Missing snapshot')
            delta=states[1]['coarse']['st']-states[0]['coarse']['st']
            checks=[]
            for index,mode in enumerate(modes):
                before=states[index+1];after=states[index+2]
                residuals={'fine_mutation':after['stocks']['fine_total']-before['stocks']['fine_total'],
                           'coarse_minus_fine_after':after['stocks']['coarse_total']-after['stocks']['fine_total']}
                if mode==0:
                    residuals['map_coarse_after_minus_fine_before']=after['stocks']['coarse_total']-before['stocks']['fine_total']
                    gate=[residuals['fine_mutation'],residuals['map_coarse_after_minus_fine_before']]
                else:
                    residuals['fine_minus_requested']=residuals['fine_mutation']-delta
                    gate=[residuals['fine_minus_requested']]
                if not all(math.isfinite(x) for x in residuals.values()):raise ValueError('Nonfinite residual')
                checks.append({'direction':mode,'residuals_m':residuals,'closed_within_fixture_bound':all(abs(x)<=TOL for x in gate)})
            normal_ok=all(c['closed_within_fixture_bound'] for c in checks)
            if case['group']=='normal' and not normal_ok:failures.append({'case':case['id'],'reason':'normal_control_residual'})
            results.append({'case':case,'actual_delta_m':delta,'states':states,'checks':checks,
                'normal_control':case['group']=='normal','normal_control_passed':normal_ok if case['group']=='normal' else None,
                'final_coarse_minus_requested_m':states[max(states)]['stocks']['coarse_total']-states[1]['stocks']['coarse_total']})
        except (ValueError, KeyError, IndexError, subprocess.TimeoutExpired) as error:
            failure={'case':case['id'],'reason':str(error),'error_type':type(error).__name__}
            failures.append(failure)
            results.append({'case':case,'validation_failure':failure})
            (root/'validation-failure.json').write_text(json.dumps(failure,indent=2)+'\n')
    pairs=[]
    by_id={r['case']['id']:r for r in results}
    for suffix in ['plus','minus']:
        required=['C-P-'+suffix,'E-P-'+suffix]
        if any('states' not in by_id[key] for key in required):
            pairs.append({'pair':suffix,'passed':False,'reason':'required_case_failed'})
            failures.append({'case':'dry-reference-'+suffix,'reason':'required_case_failed'})
            continue
        c=by_id[required[0]]['states'][3];e=by_id[required[1]]['states'][3]
        difference=max(abs(f['sw']-g['sw']) for f,g in zip(c['fine'],e['fine']))
        stock_difference=e['stocks']['fine_total']-c['stocks']['fine_total']
        passed=difference<=2e-7 and abs(stock_difference)<=TOL
        pairs.append({'pair':suffix,'max_fine_fraction_difference':difference,'fine_stock_difference_m':stock_difference,'passed':passed})
        if not passed:failures.append({'case':'dry-reference-'+suffix,'reason':'coordinate_control'})
    receipt={'scope':'Complete unchanged FRWATC mappings only, not frost energy or full hydrology',
        'cases':results,'coordinate_pairs':pairs,'unexpected_failures':failures,
        'source':bindings,'source_path':str(a.source.resolve()),'compiler_sha256':sha(Path('/usr/bin/gfortran')),
        'binary_sha256':sha(binary),'build_hashes':{p.name:sha(p) for p in build.iterdir() if p.is_file()},
        'declarations':{name:sha(here/name) for name in ['frozen-declaration.md','frozen-cases.json','frozen_driver.for','run_frozen_campaign.py']}}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    for name,record in bindings.items():
        if sha(a.source/name)!=record['sha256']:raise ValueError('Native source changed')
    print(json.dumps({'cases':len(results),'unexpected_failures':failures,'threshold_cases':sum(r['case']['group']=='threshold' for r in results)}))
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
