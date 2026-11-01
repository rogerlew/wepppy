"""Strict executed hourly flux support and stage-stock comparisons (meters)."""
import argparse,hashlib,json,math
from pathlib import Path
STAGES=['BP_WBH_BEFORE','BP_WBH_PURK','FX_ET','FX_CAP','FX_DRAIN','FX_LAT','BP_WBH_AFTER']
DAILY=['FX_UP_PRE','FX_UP_POST']
OPERANDS={'BP_WBH_ALLOC','BP_WBH_SEEP','BP_WBH_FLUX','BP_WBH_RETURN','FX_DFLUX'}
NEW={s+t for s in STAGES+DAILY if s.startswith('FX_') for t in ('_W','_K')}|{'FX_ET_PRE','FX_ET_POST','FX_REQUEST','FX_RETURN','FX_DCALL','FX_DFLUX','FX_UP_IN','FX_UP_OUT','FX_SWCALL'}
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def compare(before,after,flux,clamp=False):
 b=[v[0] for _,v in sorted(before.items())];a=[v[0] for _,v in sorted(after.items())]
 primitive=b+a+list(flux);scale=math.fsum(abs(x) for x in primitive)
 delta=math.fsum(a+[-x for x in b]);residual=math.fsum(a+[-x for x in b]+list(flux))
 allowance=lambda u:128*u/(1-128*u)*scale
 negative=any(x<0 for x in a+b)
 threshold=1e-9 if clamp and not negative else 0.
 return dict(change_m=delta,flux_terms_m=list(flux),residual_m=residual,reader_roundoff_m=allowance(2**-53),native_arithmetic_allowance_m=allowance(2**-24),zeroing_allowance_m=threshold,negative_ST=negative,within_declared_allowance=abs(residual)<=allowance(2**-53)+allowance(2**-24)+threshold)
def read(path,year,day,prior=None):
 groups={};daily={};et={};legacy=hashlib.sha256();count=0
 def put(d,tag,value,pos):
  if tag in d:raise ValueError('Duplicate tag/support')
  d[tag]=(value,pos)
 for pos,line in enumerate(Path(path).read_bytes().splitlines(keepends=True)):
  c=line.split()
  if len(c)!=11:raise ValueError('Record shape')
  tag=c[0].decode();y,d,o,ix=map(int,c[1:5]);v=list(map(float,c[5:]))
  if not all(math.isfinite(x) for x in v):raise ValueError('Nonfinite')
  if y!=year or d not in (day-1,day) or o not in (1,2,3):raise ValueError('Clock/OFE')
  if tag not in NEW:
   if tag.startswith('FX_'):raise ValueError('Unknown new tag')
   legacy.update(line)
  else:count+=1
  base=tag[:-2]
  if tag.endswith(('_W','_K')) and base in STAGES+DAILY:
   h,l=divmod(ix,100)
   if l not in range(1,11):raise ValueError('Layer support')
   if base in DAILY:
    if h!=0:raise ValueError('Daily stage index')
    g=daily.setdefault((y,d,o),{})
   else:
    if h not in range(1,25):raise ValueError('Hourly stage index')
    g=groups.setdefault((y,d,o,h),{})
   put(g,f'{tag}:{l}',v,pos)
  elif tag in OPERANDS or tag=='FX_DCALL':
   if ix not in range(1,25):raise ValueError('Operand hour')
   put(groups.setdefault((y,d,o,ix),{}),tag,v,pos)
  elif tag in {'FX_ET_PRE','FX_ET_POST','FX_REQUEST','FX_RETURN'}:
   if tag.startswith('FX_ET_') and ix!=24:raise ValueError('ET hour')
   if tag in {'FX_REQUEST','FX_RETURN'} and ix not in (1,2):raise ValueError('ET method')
   put(et.setdefault((y,d,o),{}),tag,(ix,v),pos)
  elif tag in {'FX_UP_IN','FX_UP_OUT','FX_SWCALL'}:
   if ix!=0:raise ValueError('Uptake index')
   put(daily.setdefault((y,d,o),{}),tag,v,pos)
 expected={(year,d,o,h) for d in (day-1,day) for o in (1,2,3) for h in range(1,25)}
 expday={k[:3] for k in expected}
 if set(groups)!=expected or set(daily)!=expday or set(et)!=expday:raise ValueError('Incomplete clock support')
 if prior and legacy.hexdigest()!=sha(prior):raise ValueError('Old BPO parity')
 def stage(g,s):
  keys=[f'{s}_{t}:{l}' for l in range(1,11) for t in ('W','K')]
  if not all(k in g for k in keys):raise ValueError('Missing layer/stage')
  positions=[g[k][1] for k in keys]
  if positions!=sorted(positions):raise ValueError('Stage layer order')
  return {l:g[f'{s}_W:{l}'][0] for l in range(1,11)},min(positions),max(positions)
 rows=[];days=[]
 for clock,g in sorted(groups.items()):
  states={};last=-1
  for s in STAGES:
   w,lo,hi=stage(g,s)
   if lo<=last:raise ValueError('Stage order')
   states[s]=w;last=hi
  if not OPERANDS<=set(g):raise ValueError('Missing operands')
  ix=clock[3];e=et[clock[:3]];metrics={}
  if ix==24:
   if set(e)!={'FX_ET_PRE','FX_ET_POST','FX_REQUEST','FX_RETURN'}:raise ValueError('ET support')
   ordered=[e[t][1] for t in ['FX_ET_PRE','FX_REQUEST','FX_RETURN','FX_ET_POST']]
   if ordered!=sorted(ordered) or ordered[0]<=stage(g,'BP_WBH_PURK')[2] or ordered[-1]>=stage(g,'FX_ET')[1]:raise ValueError('ET call order')
   pre=e['FX_ET_PRE'][0][1];post=e['FX_ET_POST'][0][1];req=e['FX_REQUEST'][0];ret=e['FX_RETURN'][0]
   method=1 if pre[5]==1 else 2
   if post[5]!=pre[5] or req[0]!=method or ret[0]!=method:raise ValueError('ET method disagreement')
   # RETURN: xx,es,eres,resint,ep,et; POST: ep,es,eres,resint,reserved0,flag.
   if [ret[1][i] for i in (4,1,2,3)]!=post[:4] or post[4]!=0.:raise ValueError('ET return disagrees')
   if pre[:3]!=[0.,0.,0.]:raise ValueError('ET caller initialization')
   flux=[post[3],-pre[3],post[1]]+([post[2]] if method==1 else [])
   metrics['ET']=compare(states['BP_WBH_PURK'],states['FX_ET'],flux,True)
   metrics['ET'].update(method=method,pre=pre,request=req[1],returned=ret[1],post=post,unsupported_negative_residue=pre[3]<0)
  else:metrics['ET']=compare(states['BP_WBH_PURK'],states['FX_ET'],[])
  if ix!=24 and states['BP_WBH_PURK']!=states['FX_ET']:raise ValueError('Nonfinal ET state change')
  metrics['capacity']=compare(states['FX_ET'],states['FX_CAP'],[])
  drain=g['FX_DFLUX'][0];called='FX_DCALL' in g
  if not stage(g,'FX_DRAIN')[2]<g['FX_DFLUX'][1]<stage(g,'FX_LAT')[1]:raise ValueError('Drain flux order')
  if called:
   cv,cp=g['FX_DCALL']
   if not stage(g,'FX_CAP')[2]<cp<stage(g,'FX_DRAIN')[1] or cv[0]!=drain[0] or cv[5]!=1:raise ValueError('Drain call contract')
  elif drain[0]!=0:raise ValueError('Absent drain call has nonzero flux')
  metrics['drain']=compare(states['FX_CAP'],states['FX_DRAIN'],[drain[0]])
  metrics['drain']['called']=called
  metrics['lateral']=compare(states['FX_DRAIN'],states['FX_LAT'],[g['BP_WBH_FLUX'][0][1]])
  metrics['surface']=compare(states['FX_LAT'],states['BP_WBH_AFTER'],[g['BP_WBH_FLUX'][0][0]])
  flags=[]
  for s,w in states.items():
   for l,v in w.items():
    k=g[f'{s}_K:{l}'][0]
    if v[0]<0 or v[2]<0:flags.append([s,l,'negative_relative_coordinate'])
    if v[0]+v[3]*(v[4]-k[3])<0 or v[2]+v[3]*k[3]<0 or v[3]<0 or v[4]<=0 or not 0<=k[3]<=v[4]:flags.append([s,l,'invalid_absolute_component_or_geometry'])
    if v[1:]!=states['BP_WBH_PURK'][l][1:] or k!=g[f'BP_WBH_PURK_K:{l}'][0]:flags.append([s,l,'support_or_hydraulic_change'])
  rows.append(dict(clock=list(clock),stages=states,metrics=metrics,flags=flags))
 for clock,g in sorted(daily.items()):
  pre,lo,hi=stage(g,'FX_UP_PRE');post,pl,ph=stage(g,'FX_UP_POST')
  last_hour=groups[clock+(24,)]
  if not stage(last_hour,'BP_WBH_AFTER')[2]<lo or not hi<g['FX_UP_IN'][1]<pl or not ph<g['FX_UP_OUT'][1]:raise ValueError('Uptake order')
  before=g['FX_UP_IN'][0];after=g['FX_UP_OUT'][0];called='FX_SWCALL' in g
  if called and (not g['FX_UP_IN'][1]<g['FX_SWCALL'][1]<pl or g['FX_SWCALL'][0]!=after):raise ValueError('SWU return/order')
  if called!=(before[0]>0 and before[3]>0):raise ValueError('SWU decision coverage')
  canopy=after[1]-after[2] if after[1]>0 else 0.
  uptake=after[0]-canopy if called else 0.
  prior_hour=next(r for r in rows if r['clock']==list(clock)+[24])
  flags=[]
  for label,w in [('FX_UP_PRE',pre),('FX_UP_POST',post)]:
   for l,v in w.items():
    k=g[f'{label}_K:{l}'][0];ref=last_hour[f'BP_WBH_AFTER_W:{l}'][0];kr=last_hour[f'BP_WBH_AFTER_K:{l}'][0]
    if v[1:]!=ref[1:] or k!=kr:flags.append([label,l,'support_or_hydraulic_change'])
    if v[0]<0 or v[2]<0:flags.append([label,l,'negative_relative_coordinate'])
    if v[0]+v[3]*(v[4]-k[3])<0 or v[2]+v[3]*k[3]<0 or v[3]<0 or v[4]<=0 or not 0<=k[3]<=v[4]:flags.append([label,l,'invalid_absolute_component_or_geometry'])
  if before[1]<0 or before[2]<0 or after[1]<0 or after[2]<0 or after[2]>after[1] or canopy<0 or uptake<0:flags.append(['uptake','unsupported_interception_or_negative_uptake'])
  if not called and pre!=post:flags.append(['uptake','no_call_stock_change'])
  days.append(dict(clock=list(clock),flags=flags,called=called,pre=before,post=after,canopy_m=canopy,root_uptake_m=uptake,uptake=compare(pre,post,[uptake],True),growth=compare(prior_hour['stages']['BP_WBH_AFTER'],pre,[]),stages={'pre':pre,'post':post}))
 comparisons=[v for row in rows for v in row['metrics'].values()]+[d[k] for d in days for k in ('uptake','growth')]
 return dict(passed=True,diagnostic_sha256=sha(path),legacy_filtered_sha256=legacy.hexdigest(),new_records=count,hourly_groups=len(rows),daily_groups=len(days),rows=rows,days=days,comparison_count=len(comparisons),outside_allowance=sum(not m['within_declared_allowance'] for m in comparisons),flagged_hours=sum(bool(r['flags']) for r in rows),flagged_days=sum(bool(d['flags']) for d in days))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('path',type=Path);ap.add_argument('--year',type=int,required=True);ap.add_argument('--day',type=int,required=True);ap.add_argument('--prior',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=read(a.path,a.year,a.day,a.prior)
 with a.out.open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
