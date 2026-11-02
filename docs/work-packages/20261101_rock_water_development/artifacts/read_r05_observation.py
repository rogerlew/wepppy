"""Strict R05 paired observer readback; original code, no native execution."""
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from r05_flow_joins import Joins
from r05_daily_ledger import Daily
from r05_causal_joins import Causal


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def decode(word,kind):
    if re.fullmatch('[0-9A-F]{16}',word) is None:
        raise ValueError('Malformed exact representation')
    raw=int(word,16)
    if kind=='i':return raw-(1<<64) if raw>>63 else raw
    if kind=='r':
        low=raw&0xffffffff
        expected=(0xffffffff00000000|low) if low>>31 else low
        if raw!=expected:raise ValueError('Invalid sign-extended binary32 representation')
        value=struct.unpack('>f',low.to_bytes(4,'big'))[0]
    elif kind=='d':value=struct.unpack('>d',raw.to_bytes(8,'big'))[0]
    else:raise ValueError('Unknown scalar kind')
    if not math.isfinite(value):raise ValueError('Nonfinite observed operand')
    return value


def records(path,schema):
    last=0;footer=False;header=False
    with Path(path).open() as stream:
        for line_number,line in enumerate(stream,1):
            v=line.split()
            if not v:raise ValueError('Blank observation record')
            if not header:
                if v!=['R05_SCHEMA','1']:raise ValueError('Missing schema header')
                header=True;continue
            if footer:raise ValueError('Records after footer')
            if v[0]=='R05_END':
                if len(v)!=2 or int(v[1])!=last:raise ValueError('Footer/census mismatch')
                footer=True;continue
            if len(v)<8:raise ValueError('Short observation')
            seq,year,day,ofe,index=map(int,v[:5]);tag,kind=v[5:7];count=int(v[7])
            if seq!=last+1:raise ValueError('Missing/duplicate/reordered observation')
            last=seq
            base=tag;snapshot=None
            for suffix in ('LAYER','PLANT','WATER','STATE'):
                if tag.endswith('_'+suffix):
                    snapshot=tag[:-len(suffix)-1];base=suffix;break
            if snapshot is not None and snapshot not in schema['_snapshot_stages']:
                raise ValueError('Unknown snapshot stage')
            if base not in schema or not isinstance(schema[base],dict):raise ValueError('Unknown observation tag')
            contract=schema[base]
            if kind!=contract['kind'] or count!=len(contract['fields']) or len(v)!=8+count:
                raise ValueError('Operand schema/count mismatch')
            values=[decode(x,kind) for x in v[8:]]
            yield dict(seq=seq,year=year,day=day,ofe=ofe,index=index,tag=tag,kind=kind,
                       fields=contract['fields'],bits=v[8:],values=values,snapshot=snapshot,group=base,line=line_number)
    if not header or not footer or last==0:raise ValueError('Incomplete observation stream')


def validate_windows(windows):
    if not isinstance(windows,list) or not 1<=len(windows)<=8:
        raise ValueError('Expected one through eight explicit windows')
    for w in windows:
        if not isinstance(w,list) or len(w)!=3 or not all(isinstance(x,int) for x in w) or not (w[0]>0 and 1<=w[1]<=w[2]<=366):
            raise ValueError('Invalid detailed window')
    if windows!=sorted(windows):raise ValueError('Unordered windows')
    for a,b in zip(windows,windows[1:]):
        if a[0]==b[0] and a[2]>=b[1]:raise ValueError('Overlapping windows')
    return windows


def in_windows(clock,windows):
    return any(clock[0]==w[0] and w[1]<=clock[1]<=w[2] for w in windows)


def f32(value):return struct.unpack('>f',struct.pack('>f',value))[0]


def cumulative_increment(increments,cumulative):
    if len(increments)!=len(cumulative) or not increments:
        raise ValueError('Missing increment/cumulative endpoints')
    previous=0.
    for increment,total in zip(increments,cumulative):
        previous=f32(previous+increment)
        if previous!=total:raise ValueError('Cumulative flux differs from native increment sum')
    return cumulative[-1]


def daily_ledger(inputs,outputs,start,end):
    required_inputs={'rain','melt','irrigation','furrow','surface_runon','subsurface_runon'}
    required_outputs={'surface','lateral','deep','plant_et','soil_et','residue_et','tile'}
    required_stores={'soil_liquid','soil_ice','canopy','residue'}
    if set(inputs)!=required_inputs or set(outputs)!=required_outputs or set(start)!=required_stores or set(end)!=required_stores:
        raise ValueError('Missing or duplicated water ownership component')
    flux=sum(map(Fraction,inputs.values()))-sum(map(Fraction,outputs.values()))
    delta=sum(map(Fraction,end.values()))-sum(map(Fraction,start.values()))
    return dict(net_flux_m_exact=str(flux),store_change_m_exact=str(delta),residual_m_exact=str(flux-delta),
                requires_interpretation=flux!=delta,scientific_acceptance=False,
                scope='Recorded soil, canopy and residue ledger; RM already contains melt, so snow stock is separate.')


def read(path,schema_path,dates,windows,ofes=3):
    schema=json.loads(Path(schema_path).read_text())
    dates=[tuple(map(int,d)) for d in dates];allowed=set(dates)
    if len(allowed)!=len(dates) or dates!=sorted(dates):raise ValueError('Invalid configured calendar')
    windows=validate_windows(windows)
    counts=Counter();daily=Counter();calls=Counter();modes=Counter();layers={};first_values={};pending=None;last_date=None;seen_dates=[];stacks={};opened=set();closed=set()
    total=0;water_order={};weather_clocks=set()
    joined=Joins(windows);daily_owners=Daily();causal=Causal(windows)
    for row in records(path,schema):
        total+=1;clock=(row['year'],row['day']);tag=row['tag'];ip=row['ofe'];stage=row['snapshot']
        if clock not in allowed or not 1<=ip<=ofes:
            raise ValueError('Clock/OFE outside declaration')
        if clock!=last_date:
            if last_date is not None and clock<=last_date:raise ValueError('Reversed observer clock')
            seen_dates.append(clock);last_date=clock
        owner=(clock,ip)
        if owner in closed:raise ValueError('Observation after daily close')
        if owner not in opened and stage!='DAY_OPEN':raise ValueError('Observation before daily open')
        if tag=='CLOCK_WEATHER':
            if clock in weather_clocks or any((clock,j) not in opened for j in range(1,ofes+1)):raise ValueError('Weather clock before all openings or repeated')
            if ip!=1 or row['index']!=0 or row['values']!=[clock[0],clock[1],clock[0],clock[1]]:raise ValueError('Native/observer weather clock mismatch')
            weather_clocks.add(clock)
        elif stage!='DAY_OPEN' and clock not in weather_clocks:raise ValueError('Process observation before weather clock')
        if stage is None:
            if pending is not None:raise ValueError('Interrupted state snapshot')
            force=schema[tag]['force']
        else:force=schema['_snapshot_stages'][stage]
        if force==0 and not in_windows(clock,windows):
            raise ValueError('Detailed record outside bounded window')
        joined.consume(row);daily_owners.consume(row);causal.consume(row)
        counts[tag]+=1
        if tag=='WB_DISPATCH':
            modes[str(row['values'][0])]+=1
            if row['values'][0]!=1:raise ValueError('Uninstrumented daily consumer mode executed')
            calls[(clock,ip,'WB_DISPATCH')]+=1
        if stage is not None:
            group=row['group']
            if pending is None:
                if group!='LAYER' or row['index']!=1:raise ValueError('Missing snapshot layer start')
                pending=dict(stage=stage,clock=clock,ip=ip,layer_count=0,step='LAYER')
            if (stage,clock,ip)!=(pending['stage'],pending['clock'],pending['ip']):raise ValueError('Snapshot ownership changed')
            if group=='LAYER':
                if pending['step']!='LAYER' or row['index']!=pending['layer_count']+1:raise ValueError('Missing/reordered layer')
                pending['layer_count']+=1
            elif group=='PLANT':
                if pending['step']!='LAYER':raise ValueError('Plant snapshot order')
                pending['step']='PLANT'
            elif group=='WATER':
                if pending['step']!='PLANT':raise ValueError('Water snapshot order')
                pending['step']='WATER'
            elif group=='STATE':
                if pending['step']!='WATER' or row['values'][0]!=pending['layer_count']:raise ValueError('Layer/state census mismatch')
                if ip in layers and layers[ip]!=row['values'][0]:raise ValueError('Computational layer count changed')
                layers[ip]=row['values'][0];calls[(clock,ip,stage)]+=1
                stack=stacks.setdefault(owner,[])
                if stage=='WB_ENTRY':
                    if owner in water_order:raise ValueError('Nested daily water order')
                    water_order[owner]=dict(et=0,growth=0,swu=0,expected_growth={1:'PTGRA',2:'PTGRP'}.get(row['values'][4]) if row['values'][2]==1 else None)
                elif owner in water_order:
                    order=water_order[owner]
                    if stage in ('EVAP_PRE','EVAPPM_PRE'):
                        if order['et'] or order['growth'] or order['swu']:raise ValueError('ET repeated or after growth/withdrawal')
                        order['et']=1
                    if stage in ('PTGRP_PRE','PTGRA_PRE'):
                        if order['et']!=1 or order['growth'] or order['swu'] or stage[:-4]!=order['expected_growth']:raise ValueError('Growth dispatch/order mismatch')
                        order['growth']=1
                    if stage=='SWU_PRE':
                        if order['et']!=1 or order['swu'] or (order['expected_growth'] and not order['growth']):raise ValueError('Withdrawal before ET/growth or repeated')
                        order['swu']=1
                    if stage=='WB_RETURN':
                        if order['et']!=1 or (order['expected_growth'] and order['growth']!=1):raise ValueError('Missing ET/growth owner')
                        del water_order[owner]
                if stage=='DAY_OPEN':
                    if owner in opened:raise ValueError('Duplicate daily open')
                    opened.add(owner)
                elif stage=='DAY_CLOSE':
                    if stack:raise ValueError('Daily close with active owner')
                    closed.add(owner)
                elif stage=='WB_ENTRY':stack.append('WB')
                elif stage=='WB_RETURN':
                    if not stack or stack.pop()!='WB':raise ValueError('Reversed or unmatched WB return')
                elif stage.endswith('_PRE'):stack.append(stage[:-4])
                elif stage.endswith('_POST'):
                    if not stack or stack.pop()!=stage[:-5]:raise ValueError('Reversed or unmatched owner return')
                if stage in ('DAY_OPEN','DAY_CLOSE'):daily[(clock,ip,stage)]+=1
                pending=None
        if tag not in first_values:first_values[tag]=row
    if any(stacks.values()):raise ValueError('Unclosed native owner')
    if pending is not None or seen_dates!=dates or weather_clocks!=allowed:raise ValueError('Incomplete calendar or snapshot')
    for clock in dates:
        for ip in range(1,ofes+1):
            for stage in ('DAY_OPEN','DAY_CLOSE'):
                if daily[(clock,ip,stage)]!=1:raise ValueError('Missing/duplicate complete daily census')
            for before,after in [('WB_ENTRY','WB_RETURN'),('EVAP_PRE','EVAP_POST'),('EVAPPM_PRE','EVAPPM_POST'),('PTGRP_PRE','PTGRP_POST'),('PTGRA_PRE','PTGRA_POST'),('SWU_PRE','SWU_POST'),('GROW_PRE','GROW_POST'),('INITGR_PRE','INITGR_POST')]:
                if calls[(clock,ip,before)]!=calls[(clock,ip,after)]:raise ValueError('Unpaired owner calls')
            if calls[(clock,ip,'WB_DISPATCH')]<1:raise ValueError('Missing daily water consumer')
            if calls[(clock,ip,'WB_DISPATCH')]!=calls[(clock,ip,'WB_ENTRY')]:raise ValueError('Dispatch/actual consumer mismatch')
    joins=joined.finish();ledgers=daily_owners.finish();causal_result=causal.finish()
    return dict(passed=True,joins=joins,causal=causal_result,daily_ledgers=ledgers,records=total,counts=dict(counts),dates=len(dates),ofes=ofes,layers=layers,executed_modes=dict(modes),
        source_sha256=sha(path),schema_sha256=sha(schema_path),reader_sha256=sha(__file__),
        helper_hashes={str(Path(__file__).parent/n):sha(Path(__file__).parent/n) for n in ('r05_flow_joins.py','r05_daily_ledger.py','r05_causal_joins.py')},
        call_counts=[dict(year=c[0][0],day=c[0][1],ofe=c[1],owner=c[2],calls=n) for c,n in sorted(calls.items()) if n],
        first_records=first_values,scientific_acceptance=False,scope='Exact observations and owner/census completeness, not full water closure.')


def canonical(tag):
    return re.sub('_(R4|FINAL)$','',tag)


def exact(values):
    return [Fraction(x) for x in values]


def first_witness(witnesses,baseline,candidate):
    """Use lane-local precedence; do not invent a cross-lane total order."""
    if not witnesses:return None
    orders=[{key:i for i,key in enumerate(lane)} for lane in (baseline,candidate)]
    firsts=[next((key for key in lane if key in witnesses),None) for lane in (baseline,candidate)]
    present=list(dict.fromkeys(key for key in firsts if key is not None))
    if len(present)==1:
        return dict(witnesses[present[0]],ordering_status='unique_lane_first')
    left,right=present
    relations={-1 if order[left]<order[right] else 1 for order in orders if left in order and right in order}
    if len(relations)==1:
        chosen=left if -1 in relations else right
        return dict(witnesses[chosen],ordering_status='consistent_lane_precedence')
    return dict(ordering_status='ambiguous_lane_precedence',year=next(iter(witnesses.values()))['year'],
                day=next(iter(witnesses.values()))['day'],
                baseline_first=witnesses[firsts[0]] if firsts[0] is not None else None,
                candidate_first=witnesses[firsts[1]] if firsts[1] is not None else None)


def pair(path_r4,path_final,schema_path,dates,windows,ofes=3):
    """Stream per-day matching, retaining every changed owner-key in the window."""
    checks=[read(p,schema_path,dates,windows,ofes) for p in (path_r4,path_final)]
    schema=json.loads(Path(schema_path).read_text())
    def days(path):
        current=None;rows=[]
        for row in records(path,schema):
            clock=(row['year'],row['day'])
            if current is not None and clock!=current:
                yield current,rows;rows=[]
            current=clock;rows.append(row)
        if current is not None:yield current,rows
    def indexed(rows):
        counts=Counter();result={}
        for row in rows:
            # Final-only expansion-result observations have no r4 counterpart.
            if row['tag']=='WB_EXACT_INPUT':continue
            base=(row['ofe'],canonical(row['tag']),row['index'])
            counts[base]+=1;result[(*base,counts[base])]=row
        return result
    changed_counts=Counter();representations=Counter();first=None;first_daily=None;first_numeric=None;first_branch=None;first_representation=None;window_diffs=[];days_different=0
    for left,right in zip(days(path_r4),days(path_final),strict=True):
        if left[0]!=right[0]:raise ValueError('Paired calendar mismatch')
        clock=left[0];a=indexed(left[1]);b=indexed(right[1]);changed=False
        # Semantic dictionaries preserve each lane's within-day insertion order.
        # Never compare absolute sequence numbers from separate traces.
        keys=list(a)+[k for k in b if k not in a]
        witnesses={};representation_witnesses={}
        for key in keys:
            x,y=a.get(key),b.get(key)
            if x is not None and y is not None and x['kind']!=y['kind']:
                representations[key[1]]+=1
                representation_witnesses[key]=dict(year=clock[0],day=clock[1],key=list(key),baseline=x,candidate=y)
            if x is not None and y is not None and exact(x['values'])==exact(y['values']):continue
            changed=True;changed_counts[key[1]]+=1
            witness=dict(year=clock[0],day=clock[1],ofe=key[0],tag=key[1],index=key[2],ordinal=key[3],
                         kind='branch_or_call_presence' if x is None or y is None else 'exact_operand',baseline=x,candidate=y)
            witnesses[key]=witness
            if in_windows(clock,windows):window_diffs.append(witness)
        if first is None:first=first_witness(witnesses,a,b)
        if first_numeric is None:first_numeric=first_witness({k:v for k,v in witnesses.items() if v['kind']=='exact_operand'},a,b)
        if first_branch is None:first_branch=first_witness({k:v for k,v in witnesses.items() if v['kind']=='branch_or_call_presence'},a,b)
        if first_daily is None:first_daily=first_witness({k:v for k,v in witnesses.items() if k[1].startswith(('DAY_OPEN_','DAY_CLOSE_'))},a,b)
        if first_representation is None:first_representation=first_witness(representation_witnesses,a,b)
        days_different+=int(changed)
    return dict(passed=True,checks=[{k:v for k,v in c.items() if k not in ('call_counts','first_records','daily_ledgers')} for c in checks],
                first_numeric_divergence=first_numeric,first_branch_presence_divergence=first_branch,
                representation_counts=dict(representations),first_representation_difference=first_representation,
                changed_days=days_different,changed_owner_keys=dict(changed_counts),first_exact_observed_divergence=first,
                first_daily_state_divergence=first_daily,detailed_window_differences=window_diffs,
                ordering='First source day, then lane-local semantic order. Conflicting or incomparable lane-first witnesses are explicit ambiguities. Detailed differences are baseline key order followed by candidate-only keys, not a merged chronology. Not an unobserved first instruction.',
                scientific_acceptance=False,causal_chain_complete=False)
