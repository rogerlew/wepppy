"""Compact comparator outcomes without admitting incomplete histories."""
import collections,json,re
from pathlib import Path
import campaign as c
root=c.RAW/'comparators-v1';all_results=json.loads((root/'receipt.json').read_text());rows=[]
for cell in c.CELLS:
 dest=root/c.name(cell);r=json.loads((dest/'receipt.json').read_text())
 row={k:r[k] for k in ('cell','returncode','completion','passed')};row['receipt_sha256']=c.sha(dest/'receipt.json')
 row.update(full_calendar_rows=r.get('full_calendar_rows'),frost_calls=r.get('frost',{}).get('counts',{}).get('FROST_CALL',0) if r['passed'] else None,frost_done=r.get('frost',{}).get('counts',{}).get('FROST_DONE',0) if r['passed'] else None,output_hashes=r.get('output_hashes'))
 if not r['passed']:
  text=(dest/'runs/stdout').read_text();row['failure_diagnostic']=next(l.strip() for l in text.splitlines() if 'HOURLY_WATER_UNMET' in l)
  row['last_announced_year']=int(re.findall(r'SIMULATION YEAR\s*=\s*(\d+)',text)[-1]);row['stderr']=(dest/'runs/stderr').read_text()
  # Retain last complete coarse snapshot and last event as prefix evidence only.
  counts=collections.Counter();last=None;snapshot=None;current=None
  for line in (dest/'runs/frwatc-history.txt').open():
   v=line.split()
   if v[0]=='E':
    counts[v[1]]+=1;last=line.strip()
    if current and len(current['rows'])==current['nsl']:snapshot=current
    current=dict(event=line.strip(),nsl=int(v[9]),rows=[]) if v[1] in ('WB_PRE','IRS_WB_PRE') else None
   elif v[0]=='C' and current:current['rows'].append(list(map(float,v[5:])))
  row['prefix_only']=dict(event_counts=dict(counts),last_event=last,last_complete_snapshot=snapshot,not_full_history_admission=True)
  row['partial_daily_rows']=sum(len(line.split())==25 and line.split()[0].isdigit() for line in (dest/'output/H1.wat.dat').open())
  row['trace_sha256']=c.sha(dest/'runs/frwatc-history.txt')
 rows.append(row)
nulls={str(ks):next(x for x in rows if x['cell']==[c.PANEL[0],'baseline',ks])['output_hashes']==next(x for x in rows if x['cell']==[c.PANEL[0],'candidate',ks])['output_hashes'] for ks in (0,1)}
changes=[]
for k in c.PANEL:
 for ks in (0,1):
  a=next(x for x in rows if x['cell']==[k,'baseline',ks]);b=next(x for x in rows if x['cell']==[k,'candidate',ks]);valid=a['passed'] and b['passed']
  changes.append(dict(chkey=k,ksflag=ks,complete_pair=valid,changed_outputs=[p for p,v in a['output_hashes'].items() if v!=b['output_hashes'][p]] if valid else None))
result=dict(campaign_passed=all_results['passed'],processes=len(rows),complete_histories=sum(x['passed'] for x in rows),failed_histories=sum(not x['passed'] for x in rows),observer_native_builds=0,observer_processes=0,zero_rock_nulls=nulls,cases=rows,comparisons=changes,windows=all_results['windows'],decision='Retention admission failed; consumer observer and selected flux campaign deferred. No model repair or promotion.')
c.save(c.RAW/'summary.json',result);c.save(c.HERE/'summary.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('cases','comparisons','windows')}))
