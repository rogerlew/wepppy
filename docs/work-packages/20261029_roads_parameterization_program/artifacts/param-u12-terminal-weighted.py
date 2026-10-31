from decimal import Decimal,localcontext
import json
p='/tmp/param-u12-terminal-support.json';data=json.load(open(p))
for r in data['records']:
 if not r['negative_native_wet_points']:continue
 with localcontext() as ctx:
  ctx.prec=80
  A,B,K,END,PHI=map(Decimal.from_float,[r['a'],r['b'],r['ktrato'],r['wet_end'],r['phi']])
  pwr=-PHI;root=Decimal(r['root']);d0=END-root
  S0=-K*(2*A*END+B);S1=2*K*A
  results=[]
  for x in r['negative_native_coordinates']:
   d=END-Decimal.from_float(x);power=(pwr*(d/d0).ln()).exp()
   assert pwr!=1 and pwr!=2
   e=S0/(pwr-1)*(d-d0*power)+S1/(pwr-2)*(d*d-d0*d0*power)
   assert 0<=e<=-Decimal(r['last_wet_raw_capacity'])
   results.append(dict(coordinate=x,raw_vs_clipped_continuous_error=str(e)))
  r['weighted_error_at_native_wet_coordinates']=results
  print(r['label'],r['year'],r['day'],results)
data['summary']['max_weighted_native_coordinate_model_error']=max(float(x['raw_vs_clipped_continuous_error']) for r in data['records'] for x in r.get('weighted_error_at_native_wet_coordinates',[]))
open(p,'w').write(json.dumps(data,indent=2)+'\n')
