"""Check HTTP projections, saved curves, attachments, and final run preservation."""
from pathlib import Path
import json,math,hashlib
O=Path(__file__).resolve().parent
R=Path('/wc1/runs/th/thespian-cleanness')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
a=json.loads((O/'numeric_audit.json').read_text()); T,F,S=[a['predictors'][k] for k in ['T','F','S']]
co={15:(-3.71,.32,.33,.47),30:(-3.79,.21,.19,.36),60:(-3.46,.14,.10,.18)}
checks=[]
for d,(b,ct,cf,cs) in co.items():
 local=json.loads((O/f'report_{d}.json').read_text()); live=json.loads((O/f'browser/thespian-cleanness/payload_{d}.json').read_text())
 live.pop('urls'); assert live==local
 errors=[abs(x['probability']-1/(1+math.exp(-(b+x['rainfall_mm']*(ct*T+cf*F+cs*S))))) for x in live['response_curve']['points']]
 assert max(errors)<1e-12
 checks.append({'duration':d,'points':len(errors),'max_curve_probability_error':max(errors),'live_equals_local':True})
records=json.loads((O/'browser/thespian-cleanness/evidence.json').read_text())
for r in records:
 if r.get('stage')=='attachment':assert r['sha256']==sha(R/'postfire_debris_flow'/r['name'])
before=json.loads((O/'protected_before.json').read_text())
changed=[n for n,h in before.items() if sha(R/n)!=h]
assert not changed
out={'checks':checks,'attachments_verified':sum(r.get('stage')=='attachment' for r in records),'protected_files':len(before),'changed':changed,'status':'PASS'}
(O/'closeout_checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
