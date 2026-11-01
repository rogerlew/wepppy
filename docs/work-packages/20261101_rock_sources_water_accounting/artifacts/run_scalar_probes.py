"""Compile hash-bound native fragments in private, disposable scalar fixtures."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import struct
import subprocess


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


HEADER = '''      program probe
      implicit none
      integer i,mn,iplane,ii,nsl(1),norun(1)
      real por(2,1),cpm(2,1),thetdr(2,1),dg(2,1),sat(1)
      real st(2,1),ul(2,1),frzw(2,1),surdra(1),ui_scrunf(1)
      real coca(2,1),fc(2),drfc(2),fin,fzul,fffx
      i=1
      mn=1
      iplane=1
      ii=1
      nsl=2
      norun=0
      por=0.
      cpm=1.
      thetdr=0.
      dg=0.
      sat=0.
      st=0.
      ul=0.
      frzw=0.
      surdra=0.
      ui_scrunf=0.
      coca=1.
      fc=0.
      drfc=0.
      fin=0.
      fzul=0.
      fffx=0.
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    declaration = Path(__file__).with_name('scalar-source-declaration.json')
    declared = json.loads(declaration.read_text())
    sources = {}
    for name, record in declared.items():
        p = a.source/name
        if sha(p) != record['sha256']:
            raise ValueError(f'Source identity mismatch: {name}')
        sources[name] = p.read_text().splitlines(keepends=True)
        (a.out/name).write_bytes(p.read_bytes())

    def fragment(name, start, end):
        if [start, end] not in declared[name]['slices']:
            raise ValueError('Undeclared source range')
        return ''.join(sources[name][start-1:end])

    cases = []
    for cpm in (1., .5, .25):
        for sat in (0., .5, 1.):
            dry = .0625*cpm
            effective_sat = max(sat, dry/(.5*cpm))
            expected_st = max(0., (effective_sat*.5*cpm-dry)*.125)
            expected_ul = (.5-dry)*.125
            body = f'''      por=.5
      cpm={cpm}
      dg=.125
      thetdr={dry}
      sat={sat}
'''+fragment('scon.for',510,518)+'''      write(*,*) sat(1),st(1,1),ul(1,1)
'''
            cases.append({'id': f'init_cpm{cpm}_sat{sat}', 'kind':'initialization',
                'body':body, 'inputs':{'cpm':cpm,'sat':sat,'dry':dry,'por':.5,'dg':.125},
                'expected':[effective_sat,expected_st,expected_ul],
                'effective_limit_above_dry':(.5*cpm-dry)*.125})
    for mode, name, lower, top in [('daily','watbal.for',(500,520),(794,821)),
                                  ('hourly','watbal_hourly.for',(623,643),(899,931))]:
        for tag, fin, initial, ice in [('no_input',0.,[.029,.025],[0.,.01]),
                                     ('with_input_branch',2e-6,[.029,.025],[0.,.01]),
                                     ('small_excess',0.,[.0300005,.01],[0.,0.])]:
            st = list(map(f32,initial)); u=f32(.03); ice=list(map(f32,ice)); flux=0.
            ceiling=max(0.,f32(u-ice[1])) if f32(fin)>f32(1e-6) else u
            if st[1]>ceiling:
                st[0]=f32(st[0]+f32(st[1]-ceiling));st[1]=ceiling
            ceiling=max(0.,f32(u-ice[0]));excess=f32(st[0]-ceiling)
            if excess>(f32(1e-6) if mode=='hourly' else 0.):
                flux=excess;st[0]=ceiling
            body=f'''      ul=.03
      st(1,1)={initial[0]}
      st(2,1)={initial[1]}
      frzw(1,1)={ice[0]}
      frzw(2,1)={ice[1]}
      fin={fin}
'''+fragment(name,*lower)+fragment(name,*top)+'''      write(*,*) st(1,1),st(2,1),surdra(1)
'''
            cases.append({'id':mode+'_'+tag,'kind':'overflow','body':body,
                'inputs':{'st':initial,'ul':[.03,.03],'frzw':ice,'fin':fin},
                'expected':st+[flux],'initial_sum_st':sum(map(f32,initial))})
    for label, ul, trap in [('native_control',.4375,False),('diagnostic_limit',.1875,True)]:
        body=f'''      dg=1.
      fc=.125
      coca=.9375
      ul={ul}
'''+fragment('watbal_hourly.for',652,652)+'''      st(1,1)=drfc(1)
'''+fragment('watbal_hourly.for',768,769)+'''      write(*,*) drfc(1),ul(1,1)-drfc(1),fffx
'''
        cases.append({'id':'drainage_'+label,'kind':'drainage','body':body,
            'inputs':{'ul':ul,'fc':.125,'coca':.9375,'dg':1.,'st':'drfc'},
            'expected_trap':trap,'expected':[.1875,.25,0.] if not trap else None})
    env=dict(os.environ);env['PATH']='/usr/bin:/bin:'+env.get('PATH','');env['FC']='/usr/bin/gfortran'
    compiler=subprocess.check_output(['/usr/bin/gfortran','--version'],env=env,text=True)
    (a.out/'compiler.txt').write_text(compiler)
    results=[]
    for case in cases:
        directory=a.out/case['id'];directory.mkdir()
        wrapper=directory/'probe.for';wrapper.write_text(HEADER+case.pop('body')+'      end\n')
        binary=(directory/'probe').resolve()
        command=['/usr/bin/gfortran','-O0','-fcheck=all','-ffpe-trap=invalid,zero,overflow',
                 '-ffixed-line-length-none',str(wrapper.resolve()),'-o',str(binary)]
        (directory/'case.json').write_text(json.dumps(case,indent=2)+'\n')
        (directory/'compile-command.json').write_text(json.dumps(command)+'\n')
        def execute(command, prefix, timeout):
            receipt = {'command': command, 'cwd': str(directory.resolve()),
                       'timeout_seconds': timeout, 'PATH': env['PATH'], 'FC': env['FC']}
            try:
                result = subprocess.run(command, cwd=directory, env=env,
                                        capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired as error:
                # Retain partial process evidence at this explicit execution boundary.
                for suffix, value in [('stdout', error.stdout), ('stderr', error.stderr)]:
                    value = value or b''
                    (directory/(prefix+'.'+suffix)).write_bytes(value if isinstance(value, bytes) else value.encode())
                receipt.update(status='timeout', returncode=None)
                (directory/(prefix+'-result.json')).write_text(json.dumps(receipt, indent=2)+'\n')
                raise
            (directory/(prefix+'.stdout')).write_text(result.stdout)
            (directory/(prefix+'.stderr')).write_text(result.stderr)
            receipt.update(status='completed', returncode=result.returncode,
                           stdout=prefix+'.stdout', stderr=prefix+'.stderr')
            (directory/(prefix+'-result.json')).write_text(json.dumps(receipt, indent=2)+'\n')
            return result

        compiled=execute(command, 'compile', 60)
        if compiled.returncode:
            raise RuntimeError(f'Compile failed: {directory}')
        executed=execute([str(binary)], 'execution', 10)
        case.update(returncode=executed.returncode,wrapper_sha256=sha(wrapper),binary_sha256=sha(binary))
        if case.get('expected_trap'):
            if executed.returncode != -8 or 'Floating-point exception' not in executed.stderr:
                raise AssertionError('Expected diagnostic SIGFPE not observed')
            case['disposition']='expected_invalid_domain_counterexample'
        else:
            if executed.returncode:
                raise RuntimeError(f'Unexpected execution failure: {directory}')
            actual=list(map(float,executed.stdout.split()))
            if len(actual)!=3 or not all(math.isfinite(x) for x in actual+case['expected']) or any(abs(x-y)>2e-8 for x,y in zip(actual,case['expected'])):
                raise AssertionError((case['id'],actual,case['expected']))
            case['observed']=actual;case['disposition']='matches_reference'
            if case['kind']=='overflow':
                residual=sum(actual)-case['initial_sum_st']
                if not math.isfinite(residual) or abs(residual)>2e-8:raise AssertionError('Unclosed scalar stock/flux')
                case['signed_stock_plus_surface_flux_residual_m']=residual
        results.append(case)
    for name,record in declared.items():
        if sha(a.source/name)!=record['sha256']:raise ValueError('Source changed during probe')
    receipt={'scope':'17 unchanged-source fragment probes; no full-model or promoted candidate claim',
        'declaration_sha256':sha(declaration),
        'scientific_declaration_sha256':sha(Path(__file__).with_name('scalar-declaration.md')),
        'source_path':str(a.source.resolve()),'PATH':env['PATH'],'FC':env['FC'],
        'runner_sha256':sha(Path(__file__)),
        'compiler_sha256':sha(Path('/usr/bin/gfortran')),'source':declared,'results':results}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'cases':len(results),'expected_counterexamples':sum(c.get('expected_trap',False) for c in results)}))


if __name__ == '__main__':
    main()
