"""Compare actual routing reader values and legacy event/PASS date labels."""
from pathlib import Path
from datetime import date,timedelta
import json,re
import duckdb
import numpy as np
B=Path('/workdir/wepp-gregorian-repair-20261021')
A=Path(__file__).resolve().parent
con=duckdb.connect()
rows=con.execute('select year,julian,runoff,runvol from read_parquet(?) order by year,julian',[str(B/'hbp400-final/output/interchange/H.pass.parquet')]).fetchall()
lookup={(y,d):(np.float32(q).item(),np.float32(v).item()) for y,d,q,v in rows}
pattern=re.compile(r'^(WCL_READ_Q|WSHC_BEG|WSHC_END) y=\s*(\d+) d=\s*(\d+) e=\s*(\d+).*?v1=\s*(\S+) v2=\s*(\S+)')
reads={};beg=set();end=set()
with (B/'hbp400-observe/runs/wepp_observe.log').open() as stream:
 for line in stream:
  if not line.startswith(('WCL_READ_Q','WSHC_BEG','WSHC_END')):continue
  m=pattern.match(line);assert m,line
  tag,y,d,e,v1,v2=m.groups();key=(int(y),int(d))
  if tag=='WCL_READ_Q':
   assert key not in reads
   reads[key]=(float(v1),float(v2))
  elif tag=='WSHC_BEG':beg.add(key)
  else:end.add(key)
print('TRACE_COUNTS',len(reads),len(lookup),len(beg),len(end),'missing read',list(set(lookup)-set(reads))[:3], 'extra read',list(set(reads)-set(lookup))[:3],flush=True)
assert set(reads)==set(lookup)
assert beg==end and beg.issubset(reads)
mismatches=[k for k in lookup if not np.allclose(reads[k],lookup[k],rtol=1e-7,atol=1e-9)]
assert not mismatches,mismatches[:5]
nonzero=[i for i,(y,d,q,v) in enumerate(rows) if v>0]
neighbor={}
for offset in [-1,0,1]:
 count=0
 for i in nonzero:
  j=i+offset
  if 0<=j<len(rows):
   y,d,_,_=rows[i];oy,od,_,_=rows[j]
   count+=int(np.allclose(reads[(y,d)],lookup[(oy,od)],rtol=1e-7,atol=1e-9))
 neighbor[str(offset)]=count
# Released ASCII: compare daily PASS surface-runoff values with calendar-dated hill EBE.
events={}
for line in (B/'ascii-baseline-hill/output/H1.ebe.dat').read_text().splitlines()[3:]:
 f=line.split()
 if len(f)>5:events[date(int(f[2]),int(f[1]),int(f[0]))]=float(f[4])
ordinal=0;counts={};examples=[];checked=0;missing=[]
with (B/'ascii-baseline-hill/output/H1.pass.dat').open() as stream:
 for line in stream:
  if line[:8] not in ('EVENT   ','SUBEVENT','NO EVENT'):continue
  ordinal+=1
  if line[:8]!='EVENT   ' or ordinal>73048:continue
  y=int(line[10:15]);d=int(line[16:21]);q=float(line[22:].split()[3])*1000
  actual=date(1,1,1)+timedelta(days=ordinal-1)
  label=date(y,1,1)+timedelta(days=d-1)
  if actual not in events:missing.append(str(actual));continue
  assert abs(events[actual]-q)<=0.051,(actual,events[actual],q)
  checked+=1;offset=(actual-label).days;counts[str(offset)]=counts.get(str(offset),0)+1
  if offset and len(examples)<5:examples.append({'pass_year':y,'pass_julian':d,'pass_gregorian_label':str(label),'hill_ebe_date':str(actual),'runoff_mm':events[actual]})
result={'corrected_400_year_trace':{'days':len(reads),'nonzero_surface_runoff_days':len(nonzero),'same_day_payload_mismatches':len(mismatches),'matches_against_pass_day_offsets':neighbor,'routing_begin_end_keys_match':True,'channel_routing_days':len(beg)},'released_ascii_hill':{'matched_events':checked,'event_date_minus_pass_date_days':counts,'missing_hill_ebe':missing,'examples':examples}}
original=Path('/wc1/runs/ch/chemotherapeutic-scope/wepp/output')
example={}
for name in ['H1.ebe.dat','ebe_pw0.txt']:
 for line in (original/name).open():
  f=line.split()
  if len(f)>4 and f[:3]==['2','5','102']:example[name]=line.strip()
for line in (original/'H1.pass.dat').open():
 f=line.split()
 if line[:8]=='EVENT   ' and f[1:3]==['102','121']:
  example['H1.pass.dat']={'year':102,'julian':121,'gregorian_label':'0102-05-01','runoff_mm':float(line[22:].split()[3])*1000}
result['original_run_example']=example
(A/'audit-results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
