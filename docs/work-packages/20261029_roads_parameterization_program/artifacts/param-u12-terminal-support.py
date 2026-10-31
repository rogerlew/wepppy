from pathlib import Path
from decimal import Decimal,localcontext
import struct,json,hashlib,collections
base=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/param-sign-observe-u12')
f32=lambda x:struct.unpack('f',struct.pack('f',float(x)))[0]
def prev(x):
 bits=struct.unpack('I',struct.pack('f',x))[0]
 return struct.unpack('f',struct.pack('I',bits-1))[0]
records=[]
for label in ['ordinary','depend_failure','buffer_control','buffer_cap']:
 p=base/label/'runs/stdout'
 for line in p.read_text().splitlines():
  tok=line.split()
  if not tok or tok[0]!='NC_DEP':continue
  # year/day/ofe xb xe obeg oend a b c phi theta du q k load min
  year,day,ofe=map(int,tok[1:4]);vals=list(map(float,tok[4:]))
  xb,xe,obeg,oend,a,b,c,phi,theta,du,q,k,load,reported=vals
  a,b,c,phi,theta,du,q,k,load=map(f32,[a,b,c,phi,theta,du,q,k,load])
  assert oend==f32(oend) and obeg==f32(obeg)
  assert a>=0 and b<0 and c>0 and q<0 and phi<0 and oend==-q and obeg<oend
  with localcontext() as ctx:
   ctx.prec=80
   A,B,C,K,END,BEGIN=map(Decimal.from_float,[a,b,c,k,oend,obeg])
   root=-C/B if A==0 else (-B-(B*B-4*A*C).sqrt())/(2*A)
   poly=lambda x:(A*x+B)*x+C
   assert poly(BEGIN)>=0 and 2*A*END+B<0
   minimum=poly(END)*K
   assert minimum<0 and BEGIN<root<END
   last=prev(oend);lastcap=poly(Decimal.from_float(last))*K
   count=0;x=last;points=[]
   while x>=obeg and poly(Decimal.from_float(x))<0:
    points.append(x);count+=1;x=prev(x)
    assert count<10000
   records.append(dict(label=label,year=year,day=day,ofe=ofe,xb=xb,xe=xe,wet_end=oend,
     a=a,b=b,c=c,phi=phi,theta=theta,du=du,q=q,ktrato=k,entry_load=load,
     root=str(root),negative_width=str(END-root),terminal_raw_capacity=str(minimum),
     last_wet_float32=last,last_wet_raw_capacity=str(lastcap),negative_native_wet_points=count,
     negative_native_coordinates=points,capacity_derivative_integral_bound=str(-minimum),
     trace_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
summary=dict(cases=len(records),by_label=dict(collections.Counter(r['label'] for r in records)),
 any_negative_native_wet=sum(r['negative_native_wet_points']>0 for r in records),
 max_negative_native_wet=max(r['negative_native_wet_points'] for r in records),
 max_terminal_capacity_bound=max(float(r['capacity_derivative_integral_bound']) for r in records),
 max_negative_width=max(float(r['negative_width']) for r in records),
 max_last_wet_negative_capacity=max(max(0,-float(r['last_wet_raw_capacity'])) for r in records))
Path('/tmp/param-u12-terminal-support.json').write_text(json.dumps(dict(summary=summary,records=records),indent=2)+'\n')
print(json.dumps(summary,indent=2))
for r in records:
 if r['negative_native_wet_points']:print({k:r[k] for k in ['label','year','day','ofe','negative_native_wet_points','last_wet_raw_capacity','capacity_derivative_integral_bound']})
