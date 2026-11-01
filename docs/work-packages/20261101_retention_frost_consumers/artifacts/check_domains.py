"""Standalone logger and malformed reader controls; no WEPP invocation."""
import argparse,calendar,hashlib,json,os,subprocess
from pathlib import Path
from read_domains import read,detailed
HERE=Path(__file__).resolve().parent
DRIVER='''program controls
implicit none
call rdomain(1,0,0,1,1,0,.25d0,1.d0,0.d0,0.d0)
call rdomain(5,0,0,1,2,0,0.d0,1.d0,0.d0,0.d0)
call rdomain(1,0,0,1,3,0,1.d0,1.d0,0.d0,0.d0)
call rdomain(2,1,1,1,2,1,.1d0,.2d0,.01d0,0.d0)
call rdomain(2,1,1,1,2,2,.2d0,.2d0,0.d0,0.d0)
call rdomain(3,1,1,1,2,1,.1d0,0.d0,.01d0,0.d0)
call rdomain(4,1,1,1,1,1,.125d0,.25d0,0.d0,0.d0)
call rdomain(4,1,2,1,1,1,.125d0,.25d0,0.d0,0.d0)
call rdomain(0,0,0,0,0,0,0.d0,0.d0,0.d0,0.d0)
end program
'''
def main(root):
 root.mkdir();(root/'driver.f90').write_text(DRIVER)
 command=['/usr/bin/gfortran','-O0','-fcheck=all','-ffpe-trap=invalid,zero,overflow','-o',str(root/'probe'),str(root/'driver.f90'),str(HERE/'domain_logger.for')]
 p=subprocess.run(command,env={**os.environ,'PATH':'/usr/bin:/bin'},capture_output=True,text=True)
 (root/'build.stdout').write_text(p.stdout);(root/'build.stderr').write_text(p.stderr);p.check_returncode()
 results={}
 for enabled in (False,True):
  run=root/str(enabled);run.mkdir()
  if enabled:(run/'consumer_observe.on').touch()
  p=subprocess.run([str(root/'probe')],cwd=run,capture_output=True,text=True);p.check_returncode()
  if not enabled:
   assert not (run/'consumer-domains.txt').exists();continue
  data=read(run/'consumer-domains.txt',target=(1,2));assert data['sites']['2']['calls']==2 and data['sites']['2']['frozen_calls']==1
  assert data['sites']['3']['bad']==1 and data['sites']['1']['bad']==1
  assert [w['sequence'] for w in data['witnesses'].values()]==[3,6]
  results['valid']=data
 text=(root/'True/consumer-domains.txt').read_text();lines=text.splitlines(True)
 first=next(l for l in lines if l.startswith('S '));witness=next(l for l in lines if l.startswith('B '))
 failures={'footer':''.join(lines[:-1]),'duplicate':text.replace(first,first+first,1),'missing_witness':text.replace(witness,'',1),'nonfinite':text.replace('2.5000000000000000E-001','NaN',1),'witness_clock':text.replace(witness,' '.join(witness.split()[:6]+['1']+witness.split()[7:])+'\n',1),'footer_count':text.replace('RD_END','RD_END 1',1),'orphan':text.replace(first,'',1)}
 rejected={}
 for name,value in failures.items():
  path=root/(name+'.txt');path.write_text(value)
  try:read(path)
  except ValueError as e:rejected[name]=str(e)
  else:raise AssertionError(name)
 # Exact binary32 raw lateral reconstruction and selected summary matching.
 detail=root/'detail.txt';detail.write_text('RD_LAT 1 1 1 101 0.125 0.25 0 0.25 0.375 0.125\n')
 summary={'selected':{'1,1,4,1,1':{'count':1,'icy':0,'bad':0,'values':[.125,.125,.25,.25,.25,0]}}}
 assert detailed(detail,summary,(1,2),4)['records']==1
 summary['selected']['1,1,4,1,1']['icy']=1
 try:detailed(detail,summary,(1,2),4)
 except ValueError as e:rejected['frozen_summary']=str(e)
 else:raise AssertionError('frozen_summary')
 summary['selected']['1,1,4,1,1']['icy']=0
 detail.write_text(detail.read_text().replace('0.375','0.5'))
 try:detailed(detail,summary,(1,2),4)
 except ValueError as e:rejected['raw_lateral']=str(e)
 else:raise AssertionError('raw_lateral')
 # Complete daily support for both actual native profile sizes.
 for layers in (4,9):
  full=root/f'full-{layers}.txt';nrows=3*layers;days=0;calls=0
  with full.open('w') as stream:
   stream.write('RD_SCHEMA 1\n')
   for ofe in range(1,4):
    for layer in range(1,layers+1):stream.write(f'S 0 0 1 {ofe} {layer} 1 0 0 .25 .25 1 1 .75 0\n')
   for year in range(1,17):
    for day in range(1,367 if calendar.isleap(year) else 366):
     days+=1
     for ofe in range(1,4):
      for layer in range(2,layers+1):
       stream.write(f'S {year} {day} 2 {ofe} {layer} 24 0 0 .1 .1 .2 .2 .2 0\n');nrows+=1;calls+=24
   stream.write(f'RD_END {3*layers} {calls} 0 0 0 {nrows} {days+1}\n')
  assert read(full,layers=layers)['sites']['2']['calls']==calls
  try:read(full,layers=layers+1)
  except ValueError as e:rejected[f'full_support_{layers}']=str(e)
  else:raise AssertionError('full support')
 # Compiled exceptional-operand controls, under both diagnostic and native flags.
 nonfinite_driver="""program nf
use, intrinsic :: ieee_arithmetic
implicit none
double precision q,z
q=ieee_value(0.d0,ieee_quiet_nan)
z=ieee_value(0.d0,ieee_positive_inf)
call rdomain(2,1,1,1,2,1,q,1.d0,0.d0,0.d0)
call rdomain(4,1,1,1,2,2,1.d0,z,0.d0,0.d0)
call rdomain(0,0,0,0,0,0,0.d0,0.d0,0.d0,0.d0)
end program
"""
 (root/'nonfinite.f90').write_text(nonfinite_driver)
 for opt in ('-O0','-O2'):
  binary=root/('nf'+opt);cmd=['/usr/bin/gfortran',opt,'-ffpe-trap=invalid,zero,overflow','-finit-local-zero','-o',str(binary),str(root/'nonfinite.f90'),str(HERE/'domain_logger.for')]
  subprocess.run(cmd,check=True,env={**os.environ,'PATH':'/usr/bin:/bin'},capture_output=True)
  dest=root/opt;dest.mkdir();(dest/'consumer_observe.on').touch();subprocess.run([str(binary)],cwd=dest,check=True,capture_output=True)
  assert sum(l.startswith('N ') for l in (dest/'consumer-domains.txt').read_text().splitlines())==2
  try:read(dest/'consumer-domains.txt')
  except ValueError as e:rejected['compiled_nonfinite'+opt]=str(e)
  else:raise AssertionError('nonfinite admission')
 (root/'receipt.json').write_text(json.dumps(dict(passed=True,command=command,logger_sha256=hashlib.sha256((HERE/'domain_logger.for').read_bytes()).hexdigest(),reader_sha256=hashlib.sha256((HERE/'read_domains.py').read_bytes()).hexdigest(),rejected=rejected,results=results),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out.resolve())
