"""Compact all-window and selected-event results; no native execution."""
import argparse,json,math,collections
from pathlib import Path

def main(root,out):
 results=[]
 for s in ['zero-ks1','normal-ks1','high-ks1']:
  p=root/s;d=json.loads((p/'observations.json').read_text());r=json.loads((p/'readback.json').read_text());assert r['passed']
  y,day=(7,343) if s=='high-ks1' else (3,19)
  event=next(x for x in d['rows'] if x['clock']==[y,day,1,24]);daily=next(x for x in d['days'] if x['clock']==[y,day,1])
  metrics={}
  for key in event['metrics']:
   rows=[x['metrics'][key] for x in d['rows']]
   metrics[key]=dict(comparisons=len(rows),nonzero_changes=sum(x['change_m']!=0 for x in rows),max_abs_residual_m=max(abs(x['residual_m']) for x in rows),outside_allowance=sum(not x['within_declared_allowance'] for x in rows))
  result=dict(scenario=s,hourly_groups=d['hourly_groups'],daily_groups=d['daily_groups'],flagged_hours=d['flagged_hours'],flagged_days=d['flagged_days'],flag_counts=dict(collections.Counter(f[-1] for x in d['rows']+d['days'] for f in x['flags'])),outside_allowance=d['outside_allowance'],metrics=metrics,ET_methods=sorted({x['metrics']['ET']['method'] for x in d['rows'] if x['clock'][3]==24}),actual_drain_calls=sum(x['metrics']['drain']['called'] for x in d['rows']),actual_SWU_calls=sum(x['called'] for x in d['days']),selected=dict(clock=event['clock'],top_ST_by_stage={k:v['1'][0] for k,v in event['stages'].items()},metrics=event['metrics'],daily=daily,flags=event['flags']),daily_comparisons=[{'clock':x['clock'],'flags':x['flags'],'called':x['called'],'uptake':x['uptake'],'growth':x['growth']} for x in d['days'])
  results.append(result)
 with out.open('x') as f:json.dump(dict(cases=results),f,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.root,a.out)
