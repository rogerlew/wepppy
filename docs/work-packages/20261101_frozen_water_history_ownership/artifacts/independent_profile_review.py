from pathlib import Path
import json, math, collections,hashlib, argparse
parser=argparse.ArgumentParser(); parser.add_argument("scenario"); parser.add_argument("--out",type=Path,required=True);args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
r=Path('out/frozen-water-history-20261101/campaign-v1')/args.scenario/'observer'; assert (r/'readback.json').exists() and (r.parent/'receipt.json').exists(); sums=collections.defaultdict(list); validG=set(); invalid=collections.Counter()
for line in (r/'transfers.jsonl').open():
 t=json.loads(line)
 if t['invalid_state']:
  for side in ('before','after'):
   for k in ('coarse_ice','coarse_liquid','fine_ice','fine_liquid'):
    if t[side][k]<0: invalid[side+'_'+k]+=1
 elif t['mode']==1:
  m=t['event']['map']; sums[m].append(t['mapping_residual_m'])
  if 'D1_UPDATE_SUPPORT' in t['branch_tags']:validG.add((m,t['layer']))
incomplete={k:len(v) for k,v in sums.items() if len(v)!=10}
if incomplete: raise ValueError('Incomplete valid profile groups: '+str(incomplete))
hi=max(sums,key=lambda k:math.fsum(sums[k]));lo=min(sums,key=lambda k:math.fsum(sums[k])); print('extremes',hi,math.fsum(sums[hi]),lo,math.fsum(sums[lo]))
skips=collections.Counter(); layers=collections.defaultdict(set); extreme=[]; h=[]; cleared_post={}; event=None
for line in (r/'runs/frwatc-history.txt').open():
 if line.startswith('E '):
  t=line.split();event=(t[1],int(t[3]),int(t[2]))
 elif line.startswith('B '):
  t=line.split();tag,m,seq=event;i=int(t[2]);v=list(map(float,t[4:]))
  if tag=='D1_UPDATE_SUPPORT' and (m,i) in validG and v[0]<=0.0010000000474974513:
   kind='zero' if v[0]==0 else ('positive_thin' if v[0]>0 else 'negative');skips[kind]+=1;layers[kind].add((m,i))
  if m in (hi,lo) and tag in ('D1_START','D1_REQUEST','D1_END','D1_FINISH','D1_NEW_CARRY','D1_CARRY_APPLY','D1_ZERO'): extreme.append(dict(map=m,tag=tag,layer=i,values=v))
  if tag=='D0_CLEAR_POST': cleared_post[(m,i)]=v[0]
  if tag=='D0_CLEAR_PRE' and v[0]>0 and v[1]<0.0010000000474974513:h.append(dict(map=m,layer=i,nw=v[0]))
valid_h=[json.loads(l) for l in (r/'ownership.jsonl').open() if json.loads(l)['kind']=='clear']
for x in h: x['post_nw']=cleared_post[(x['map'],x['layer'])]
result=dict(scenario=args.scenario,profile_groups_all_ten_layers=True,valid_H=[dict(id=x['id'],cleared_m=x['cleared_m']) for x in valid_h],max_profile_map=hi,max_profile_m=math.fsum(sums[hi]),min_profile_map=lo,min_profile_m=math.fsum(sums[lo]),skipped_cells=dict(skips),skipped_unique_layers={k:len(v) for k,v in layers.items()},invalid_negative_components=dict(invalid),H=h,extreme_branch_records=extreme)
(args.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='extreme_branch_records'}));print('extreme records',json.dumps(extreme))
