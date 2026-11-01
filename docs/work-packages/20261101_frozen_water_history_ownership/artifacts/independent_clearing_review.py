from pathlib import Path
import argparse,json,hashlib,math
p=argparse.ArgumentParser();p.add_argument('scenario');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=Path('out/frozen-water-history-20261101');s=json.loads((r/'all-clearing-v3'/a.scenario/'receipt.json').read_text())
direct_path=r/('scientific-active-high-v3' if a.scenario=='high-ks1' else 'scientific-active-'+a.scenario.split('-')[0]+'-v2')/'receipt.json';d=json.loads(direct_path.read_text())
observed={f"{x['map']}:{x['layer']}":x['nw'] for x in d['H'] if x['post_nw']==0}; actual={x['id']:x['cleared_m'] for x in s['clears']};assert observed==actual
ends={x['id']:x for x in s['endpoints']}; maps={x['id']:x for x in s['next_mappings']};assert set(ends)==set(actual) and not s['unresolved_ids']
clears=s['clears'];pending={};seen_init=set();seen_map=set();event=None;maxerr=0;checks=0; rawF=0; rawG={"zero":0,"positive_thin":0,"negative":0}
# Compare first following mapping and initialization event identities; independently reconstruct endpoint stocks.
targets={}
for e in s['endpoints']:
 targets.setdefault(e['event']['seq'],[]).append(e)
for e in s['next_mappings']:targets.setdefault(e['event']['seq'],[]).append(e)
def finish():
 global maxerr,checks
 if event is None or event['seq'] not in targets:return
 for endpoint in targets[event['seq']]:
  layer=int(endpoint['id'].split(':')[1]);v=event['c'][layer];dg,dry,ul,st,ice,frozen,soilw,yst,nw,fc=v
  cl=st+dry*(dg-frozen);ci=ice+dry*frozen;vals=dict(coarse_liquid=cl,coarse_ice=ci,coarse_total=cl+ci)
  if layer in event['f']:
   fs=event['f'][layer];fl=math.fsum(x[1]*x[3] for x in fs)+nw;fi=math.fsum(x[2] for x in fs);vals.update(fine_liquid=fl,fine_ice=fi,fine_total=fl+fi)
  for k,v in vals.items():
   err=abs(v-endpoint['stocks'][k]);maxerr=max(maxerr,err);assert err<1e-16;checks+=1
with (r/'campaign-v1'/a.scenario/'observer/runs/frwatc-history.txt').open() as stream:
 for line in stream:
  t=line.split()
  if t[0]=='E':
   finish();tag=t[1];seq=int(t[2]);ofe=int(t[6]);event=dict(seq=seq,c={},f={})
   for c in clears:
    ident=c['id'];key=(c['event']['ofe'],c['layer'])
    if ofe!=key[0] or seq<=c['event']['seq'] or (tag=='MAP_POST' and int(t[3])==c['event']['map']):continue
    if tag=='MAP_POST' and ident not in seen_map and ident not in seen_init:
     assert maps[ident]['event']['seq']==seq;seen_map.add(ident)
    if tag=='INIT_POST' and ident not in seen_init:
     assert ends[ident]['event']['seq']==seq;assert ends[ident]['next_mapping_censored_by_initialization']==(ident not in seen_map);seen_init.add(ident)
  elif t[0]=='B':
   v=list(map(float,t[4:]))
   if tag=='D0_SUPPORT' and 0<v[0]<=0.0010000000474974513 and v[2]!=v[3]:rawF+=1
   if tag=='D1_UPDATE_SUPPORT' and v[0]<=0.0010000000474974513:rawG['zero' if v[0]==0 else ('positive_thin' if v[0]>0 else 'negative')]+=1
  elif t[0]=='C' and event['seq'] in targets:event['c'][int(t[2])]=list(map(float,t[5:]))
  elif t[0]=='F' and event['seq'] in targets:event['f'].setdefault(int(t[2]),[]).append(list(map(float,t[4:])))
finish();assert seen_init==set(actual) and seen_map==set(maps)
result=dict(scenario=a.scenario,all_D0_positive_thin_cells=rawF,all_D1_skipped_support_cells=rawG,all_clear_ids_and_magnitudes_exact=True,clears=len(actual),first_initialization_endpoints=len(seen_init),first_mapping_endpoints=len(seen_map),endpoint_stock_values_checked=checks,max_stock_difference_m=maxerr,supplement_receipt_sha256=hashlib.sha256((r/'all-clearing-v3'/a.scenario/'receipt.json').read_bytes()).hexdigest())
with a.out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
