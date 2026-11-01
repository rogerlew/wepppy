"""UNEXECUTED DRAFT: observer campaign blocked by comparator admission failure."""
import argparse,json,os,re,shutil,subprocess,time
from pathlib import Path
import campaign as c
from read_domains import read as domains,detailed
from read_flux import read as flux
PREP=c.RAW/'prepared-v3'
SOURCE=c.RAW/'observer-source-v5'
ROOT=c.RAW/'observer-v1'
FREEZE=c.RAW/'observer-declaration-v1.json'
def runtime(binary):
 if os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH'):raise ValueError('Loader override')
 output=subprocess.check_output(['/usr/bin/ldd',str(binary)],env=c.ENV,text=True)
 return {str(Path(p).resolve()):c.sha(p) for p in re.findall(r'(/[^\s()]+)',output)}
def prepare():
 d=json.loads((PREP/'declaration.json').read_text());c.check(d['dependencies'])
 if c.inventory(PREP/'base-build')!=d['base_inventory']:raise ValueError('Base inventory')
 comp=c.RAW/'comparators-v1';r=json.loads((comp/'receipt.json').read_text())
 if not r['passed'] or len(r['cases'])!=12:raise ValueError('Comparator gate')
 files=[Path(__file__),c.HERE/'campaign.py',c.HERE/'select_window.py',c.HERE/'domain_logger.for',c.HERE/'read_domains.py',c.HERE/'read_flux.py',c.HERE/'check_domains.py',c.HERE/'check_flux.py',PREP/'declaration.json',SOURCE/'receipt.json',comp/'receipt.json',comp/'selected-windows.json',c.NATIVE_READER,c.RAW/'domain-controls-v5/receipt.json',c.RAW/'flux-controls-v1/4/receipt.json',c.RAW/'flux-controls-v1/9/receipt.json']
 for x in ('watbal_hourly.for','main.for'):files.append(SOURCE/x)
 for x in ('gfortran','gcc','as','ld','make'):files.append(Path('/usr/bin')/x)
 for x in ('f951','cc1','collect2'):
  compiler='/usr/bin/gfortran' if x=='f951' else '/usr/bin/gcc'
  files.append(Path(subprocess.check_output([compiler,'-print-prog-name='+x],env=c.ENV,text=True).strip()).resolve())
 for cell in c.CELLS:
  case=comp/c.name(cell);files.append(case/'receipt.json')
  case_r=json.loads((case/'receipt.json').read_text())
  c.check({str(case/'output'/p):h for p,h in case_r['output_hashes'].items()})
  if c.sha(case/'runs/frwatc-history.txt')!=case_r['frost_sha256']:raise ValueError('Comparator frost drift')
  files.extend(case/'output'/p for p in case_r['output_hashes']);files.append(case/'runs/frwatc-history.txt')
 deps={str(p):c.sha(p) for p in files};deps.update(d['libraries'])
 c.save(FREEZE,dict(dependencies=deps,base_inventory=d['base_inventory'],inputs=d['inputs'],libraries=d['libraries'],source=c.inventory(SOURCE),windows=json.loads((comp/'selected-windows.json').read_text())['windows'],process_count=12,cells=c.CELLS,stop_rule='Stop remaining observer invocations on execution, parity, or structural-reader failure. Preserve executed evidence; version any repair before resuming.'))
 print('Observer declaration frozen; no build or model execution')
def run():
 d=json.loads(FREEZE.read_text());approval=json.loads((c.RAW/'observer-approval.json').read_text())
 if approval['declaration_sha256']!=c.sha(FREEZE):raise ValueError('Approval declaration')
 c.check({**d['dependencies'],**approval['reviews']})
 if c.inventory(PREP/'base-build')!=d['base_inventory'] or c.inventory(SOURCE)!=d['source']:raise ValueError('Build source drift')
 ROOT.mkdir();shutil.copytree(PREP/'base-build',ROOT/'build')
 for p in ('watbal_hourly.for','main.for'):shutil.copy2(SOURCE/p,ROOT/'build/src'/p)
 before=c.inventory(ROOT/'build');cmd=['/usr/bin/make','-j4','FC=/usr/bin/gfortran','LINKER=/usr/bin/gfortran','wepp'];start=time.time()
 c.save(ROOT/'build-pre.json',dict(command=cmd,PATH=c.ENV['PATH'],before=before,declaration_sha256=c.sha(FREEZE)))
 with (ROOT/'build.stdout').open('xb') as out,(ROOT/'build.stderr').open('xb') as err:
  p=subprocess.run(cmd,cwd=ROOT/'build/src',env=c.ENV,stdout=out,stderr=err,timeout=300)
 c.save(ROOT/'build-receipt.json',dict(command=cmd,returncode=p.returncode,seconds=time.time()-start,before=before,after=c.inventory(ROOT/'build'),stdout_sha256=c.sha(ROOT/'build.stdout'),stderr_sha256=c.sha(ROOT/'build.stderr')))
 p.check_returncode();binary=ROOT/'build/src/wepp';libraries=runtime(binary)
 if libraries!=d['libraries']:raise ValueError('Observer runtime mismatch')
 c.save(ROOT/'runtime.json',dict(binary_sha256=c.sha(binary),libraries=libraries))
 fixed=c.inventory(ROOT/'build');reader=c.load_module(c.NATIVE_READER,'native_read');source=json.loads((c.PRIOR/'fixtures-v1/receipt.json').read_text());results=[]
 for cell in c.CELLS:
  c.check(d['dependencies'])
  k,r,ks=cell;target=d['windows'][k]['target'];target=target or [0,0]
  dest=ROOT/c.name(cell);runs=dest/'runs';runs.mkdir(parents=True);(dest/'output').mkdir()
  shutil.copytree(PREP/c.name(cell),runs,dirs_exist_ok=True)
  c.check({str(runs/p):h for p,h in d['inputs'][c.name(cell)].items()})
  (runs/'buffer_observe.on').write_text(f'{target[0]} {target[1]}\n');(runs/'consumer_observe.on').touch(exist_ok=False)
  inputs=c.inventory(runs);comparator=c.RAW/'comparators-v1'/c.name(cell);comp=json.loads((comparator/'receipt.json').read_text())
  c.save(dest/'pre-execution.json',dict(cell=cell,inputs=inputs,binary_sha256=c.sha(binary),declaration_sha256=c.sha(FREEZE),comparator_receipt_sha256=c.sha(comparator/'receipt.json'),target=target))
  result=c.execute(binary,runs,dest);result.update(cell=cell,target=target)
  try:
   if result['returncode']!=0 or not result['completion']:raise ValueError('Native process incomplete')
   fixture=next(x for x in source['cases'] if x['id']=='source-'+k)[r];result.update(reader.read(dest,fixture))
   result['frost_sha256']=c.sha(runs/'frwatc-history.txt')
   if result['output_hashes']!=comp['output_hashes'] or result['frost_sha256']!=comp['frost_sha256']:raise ValueError('Ordinary output or full frost parity')
   result['parity']=True;layers=len(result['initialization'])//3
   domain=domains(runs/'consumer-domains.txt',layers=layers,target=target);c.save(dest/'domain-readback.json',domain)
   result['domains']={a:b for a,b in domain.items() if a!='selected'}
   if target!=[0,0]:
    result['selected_domains']=detailed(runs/'buffer-observation.txt',domain,target,layers)
    fx=flux(runs/'buffer-observation.txt',*target,layers);c.save(dest/'flux-readback.json',fx)
    result['flux']={a:b for a,b in fx.items() if a not in ('rows','days')}
   else:result['flux_gap']='No eligible baseline frozen target'
   c.check({str(runs/p):h for p,h in inputs.items()})
   result['observation_hashes']={p:c.sha(runs/p) for p in ('consumer-domains.txt','buffer-observation.txt')}
  except (ValueError,KeyError,OSError,OverflowError,ZeroDivisionError) as error:result.update(passed=False,error=str(error))
  c.save(dest/'receipt.json',result);results.append(result)
  print(json.dumps(dict(cell=cell,passed=result['passed'],error=result.get('error'))),flush=True)
  if not result['passed']:break
 c.check(d['dependencies'])
 if c.inventory(ROOT/'build')!=fixed:raise ValueError('Postrun build drift')
 zero=[x for x in results if x['cell'][0]==c.PANEL[0]]
 nulls={str(s):len([x for x in zero if x['cell'][2]==s])==2 and len({json.dumps(x.get('output_hashes'),sort_keys=True) for x in zero if x['cell'][2]==s})==1 for s in (0,1)}
 passed=len(results)==12 and all(x['passed'] for x in results) and all(nulls.values())
 c.save(ROOT/'receipt.json',dict(passed=passed,cases=results,zero_rock_nulls=nulls))
 if not passed:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);a=p.parse_args();prepare() if a.action=='prepare' else run()
