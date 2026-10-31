"""Recompute U12 paired output hashes, physical checks and frozen magnitude scores."""
from pathlib import Path
import json,hashlib,collections,datetime
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/param-sign-u12-combined')
OLD=Path('/workdir/wepppy/out/roads-native-funding-20261031/r3-matrix840')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def key(c):return tuple(c[k] for k in ['climate','soil','design','surface','traffic'])
def within(x,ref):return .1<=x/ref<=10 if ref>1 else x<=max(1,10*ref)
refs={key(r['case']):r for r in json.loads((OLD/'magnitude-scores.json').read_text())}
result={'time':str(datetime.datetime.now(datetime.timezone.utc)),'panels':{}}
for panel,rows in [('downstream',json.loads((ROOT/'downstream-results.json').read_text())),('roads',[json.loads(p.read_text()) for p in sorted((ROOT/'roads').glob('*/record.json'))])]:
 summary=collections.Counter();bylane=collections.defaultdict(collections.Counter);files=collections.Counter();details=[];allrows=[]
 for r in rows:
  oldpath=Path(r['source'])/'record.json';assert sha(oldpath)==r['source_record_sha256'];old=json.loads(oldpath.read_text());folder=Path(r['folder'])
  assert r['inputs']==old['inputs']
  for n,h in r['inputs'].items():assert sha(folder/'runs'/n)==h
  changed=[]
  for n,h in r['outputs'].items():
   assert sha(folder/'output'/n)==h
   if h!=old['outputs'].get(n):changed.append(n)
  assert set(changed)==set(r['changed_outputs'])
  s=bylane[r['case']['variant']];s['cases']+=1
  assert r['physical_pass'] and r['returncode']==0
  assert not r['audit']['invalid_water_rows'] and not r['audit']['sediment']['negative_fluxes'] and not r['audit']['ebe']['mismatches']
  assert r['audit']['sediment']['report_reconciled']
  s['physical']+=1
  if changed:s['changed_output_cases']+=1
  files.update(changed)
  ref=refs[key(r['case'])]['reference_kg_yr'];newval=r['metrics']['sediment_export_kg_yr'];newwithin=within(newval,ref)
  s['meaningful_total' if ref>1 else 'small_total']+=1
  s['meaningful_within' if ref>1 else 'small_within']+=int(newwithin)
  group=old.get('group','unknown')
  if group.endswith('_pass'):s['control_total']+=1;s['control_within']+=int(newwithin)
  row=dict(case=r['case'],group=group,reference=ref,new=newval,newwithin=newwithin,changed_outputs=changed)
  if old['physical_pass']:
   oldval=old['metrics']['sediment_export_kg_yr'];oldwithin=within(oldval,ref)
   assert r['outputs']['H1.wat.dat']==old['outputs']['H1.wat.dat']
   assert r['outputs']['H1.soil.dat']==old['outputs']['H1.soil.dat']
   row.update(old=oldval,oldwithin=oldwithin,delta=newval-oldval,ratio=newval/oldval if oldval else None)
   s['recovered_magnitude']+=int(newwithin and not oldwithin)
   s['regressed_magnitude']+=int(oldwithin and not newwithin)
   s['increased_annual']+=int(newval>oldval);s['decreased_annual']+=int(newval<oldval)
   s['unchanged_annual']+=int(newval==oldval)
  else:row['prior_failure']=old['returncode'];s['recovered_native_failure']+=1
  allrows.append(row)
  if changed:details.append(row)
 for v in bylane.values():summary.update(v)
 result['panels'][panel]={'counts':dict(summary),'lanes':dict(bylane),'changed_files':dict(files),'changed_cases':details,'all_cases':allrows}
 print(panel,dict(summary));print('lanes',dict(bylane));print('files',dict(files))
 print('largest changes',sorted([r for r in details if 'delta'in r],key=lambda r:abs(r['delta']),reverse=True)[:7])
Path(__file__).with_name('param-u12-scientific-output-review.json').write_text(json.dumps(result,indent=2)+'\n')
