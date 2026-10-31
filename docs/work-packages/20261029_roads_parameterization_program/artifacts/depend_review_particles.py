from pathlib import Path
from decimal import Decimal
import json, math, collections
root=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/depend-bounded-g1')
result={}
for panel in ['downstream-fill_fixed','downstream-buffer_cap','downstream-both','roads']:
 cases=events=positive=0;bad=[];maxdelta=0
 for rec in sorted((root/panel).glob('*/record.json')):
  cases+=1;lines=(rec.parent/'output/H1.pass.dat').read_text().splitlines();npart=int(lines[4].split()[0]);assert npart==5
  for j,line in enumerate(lines):
   if not line.startswith('EVENT'):continue
   f=line.split();off=1
   while len(f)<17+2*npart:
    f+=lines[j+off].split();off+=1
   assert len(f)==17+2*npart
   conc=list(map(float,f[15:20]));frac=list(map(float,f[20:25]));events+=1
   if not all(math.isfinite(x) and x>=0 for x in conc+frac):bad.append([str(rec),f[:3],'negative/nonfinite'])
   if any(x>1 for x in frac):bad.append([str(rec),f[:3],'fraction>1'])
   if sum(conc)>0:
    positive+=1;delta=abs(sum(frac)-1);maxdelta=max(maxdelta,delta)
    tol=sum(float(Decimal(x).as_tuple().exponent and Decimal(10)**Decimal(x).as_tuple().exponent or Decimal(1))/2 for x in f[20:25])
    if delta>tol+1e-12:bad.append([str(rec),f[:3],'fraction sum',delta,tol])
 result[panel]=dict(cases=cases,event_rows=events,positive_sediment_rows=positive,max_fraction_sum_delta=maxdelta,failures=bad)
print(json.dumps(result,indent=2));Path('/tmp/depend-particle-review.json').write_text(json.dumps(result,indent=2)+'\n')
