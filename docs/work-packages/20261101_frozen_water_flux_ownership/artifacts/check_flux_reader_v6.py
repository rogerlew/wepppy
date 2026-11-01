"""Generated complete support plus malformed controls; no model execution."""
import argparse,json,tempfile
from pathlib import Path
from read_flux_v5 import read,compare,STAGES

def fixture():
 lines=[]
 def rec(t,y,d,o,ix,v):lines.append(f'{t} {y} {d} {o} {ix} '+' '.join(map(str,v))+'\n')
 def st(t,d,o,h):
  for l in range(1,11):
   rec(t+'_W',3,d,o,h*100+l,[0.01,0.1,0.,0.05,0.1,l*0.1]);rec(t+'_K',3,d,o,h*100+l,[0.001,0.001,0.4,0.,0.,0.])
 for d in (19,20):
  for o in (1,2,3):
   for h in range(1,25):
    rec('BP_WBH_ALLOC',3,d,o,h,[0.]*6);st('BP_WBH_BEFORE',d,o,h);st('BP_WBH_PURK',d,o,h);rec('BP_WBH_SEEP',3,d,o,h,[0.]*6)
    if h==24:
     rec('FX_ET_PRE',3,d,o,h,[0.,0.,0.,0.,0.,1.]);rec('FX_REQUEST',3,d,o,1,[0.]*6);rec('FX_RETURN',3,d,o,1,[0.]*6);rec('FX_ET_POST',3,d,o,h,[0.,0.,0.,0.,0.,1.])
    for t in ['FX_ET','FX_CAP','FX_DRAIN']:st(t,d,o,h)
    rec('FX_DFLUX',3,d,o,h,[0.]*6);st('FX_LAT',d,o,h)
    rec('BP_WBH_FLUX',3,d,o,h,[0.]*6);rec('BP_WBH_RETURN',3,d,o,h,[0.]*6);st('BP_WBH_AFTER',d,o,h)
   st('FX_UP_PRE',d,o,0);rec('FX_UP_IN',3,d,o,0,[0.]*6);st('FX_UP_POST',d,o,0);rec('FX_UP_OUT',3,d,o,0,[0.]*6)
 return ''.join(lines)
def main(out):
 out.mkdir();text=fixture();base=out/'valid.txt';base.write_text(text);d=read(base,3,20);assert d['hourly_groups']==144 and d['daily_groups']==6 and d['outside_allowance']==0
 drainline=next(l for l in text.splitlines(True) if l.startswith('FX_DFLUX '));drainfirst=next(l for l in text.splitlines(True) if l.startswith('FX_DRAIN_W '))
 global_line='BP_IRS_ENTER 3 19 0 0 0 1 0 0 1 0\n'
 gp=out/'global.txt';gp.write_text(global_line+text);assert read(gp,3,20)['hourly_groups']==144
 failures={
 'global_wrong_index':global_line.replace('3 19 0 0','3 19 0 1')+text,
 'new_global_forbidden':global_line.replace('BP_IRS_ENTER','FX_DFLUX')+text,
 'flux_before_drain':text.replace(drainline,'',1).replace(drainfirst,drainline+drainfirst,1),
 'duplicate':text+text.splitlines(True)[0],
 'missing_layer':text.replace(next(l for l in text.splitlines(True) if l.startswith('FX_CAP_W ')),'',1),
 'nonfinite':text.replace('FX_REQUEST 3 19 1 1 0.0','FX_REQUEST 3 19 1 1 nan',1),
 'wrong_method':text.replace('FX_REQUEST 3 19 1 1 ','FX_REQUEST 3 19 1 2 ',1),
 'orphan_et':text.replace('FX_REQUEST 3 19 1 1 ','FX_REQUEST 3 19 2 1 ',1),
 'wrong_hour':text.replace('FX_ET_POST 3 19 1 24 ','FX_ET_POST 3 19 1 23 ',1),
 'unknown_tag':text.replace('FX_REQUEST','FX_UNKNOWN',1),
 'wrong_day':text.replace('FX_CAP_W 3 19 1','FX_CAP_W 3 18 1',1),
 'wrong_ofe':text.replace('FX_CAP_W 3 19 1','FX_CAP_W 3 19 4',1),
 'wrong_order':text.replace('FX_ET_W','FX_TMP_W',1).replace('FX_CAP_W','FX_ET_W',1).replace('FX_TMP_W','FX_CAP_W',1),
 'missing_uptake':text.replace(next(l for l in text.splitlines(True) if l.startswith('FX_UP_OUT ')),'',1),
 'daily_before_hours':''.join([l for l in text.splitlines(True) if l.startswith('FX_UP_')]+[l for l in text.splitlines(True) if not l.startswith('FX_UP_')]),
 'missing_flux':text.replace(next(l for l in text.splitlines(True) if l.startswith('FX_DFLUX ')),'',1),
 }
 rejected={}
 for name,value in failures.items():
  p=out/(name+'.txt');p.write_text(value)
  try:read(p,3,20)
  except (ValueError,KeyError) as e:rejected[name]=str(e)
  else:raise AssertionError(name)
 # Physical-reference/unsupported-interception flags remain visible.
 flagged=text.replace('FX_UP_POST_W 3 19 1 1 0.01 0.1 0.0 0.05 0.1','FX_UP_POST_W 3 19 1 1 0.01 0.1 0.0 0.05 0.2',1).replace('FX_UP_OUT 3 19 1 0 0.0 0.0 0.0','FX_UP_OUT 3 19 1 0 0.0 -0.001 0.0',1)
 fp=out/'flagged.txt';fp.write_text(flagged);fd=read(fp,3,20);assert fd['flagged_days']==1 and len(fd['days'][0]['flags'])>=2
 # Negative relative ice is distinct from negative physical ice.
 relative=text.replace('FX_CAP_W 3 19 1 101 0.01 0.1 0.0','FX_CAP_W 3 19 1 101 0.01 0.1 -0.001',1).replace('FX_CAP_K 3 19 1 101 0.001 0.001 0.4 0.0','FX_CAP_K 3 19 1 101 0.001 0.001 0.4 0.05',1)
 rp=out/'relative.txt';rp.write_text(relative);rd=read(rp,3,20);assert any(x[-1]=='negative_relative_coordinate' for x in rd['rows'][0]['flags']) and not any(x[-1]=='invalid_absolute_component_or_geometry' for x in rd['rows'][0]['flags'])
 # Independent nonzero stock/flux identities and a deliberately omitted sink.
 b={1:[0.02]};a={1:[0.01]}
 assert compare(b,a,[0.01],True)['within_declared_allowance']
 assert not compare(b,a,[0.0],True)['within_declared_allowance']
 assert compare(b,a,[-0.005,0.015],True)['within_declared_allowance']
 assert compare(b,{1:[-0.01]},[0.03],True)['zeroing_allowance_m']==0
 (out/'receipt.json').write_text(json.dumps(dict(passed=True,hourly_groups=144,daily_groups=6,malformed_rejected=rejected,nonzero_arithmetic_checks=4),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
