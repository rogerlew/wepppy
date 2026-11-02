"""Original finite-campaign response analysis. No native execution or admission.

Uses validated, hash-bound daily ledgers; selectively extracts uncached plant
trajectories and demand/growth epochs. Distinct historical and repair contrasts.
"""
from collections import Counter, defaultdict
from fractions import Fraction as Q
from pathlib import Path
import argparse
import json
import math
import read_roads_final as ordinary
import read_r05_observation as observation

require=ordinary.require


class Bindings(ordinary.Bindings):
    def bind(self,path,expected=None):
        key=str(Path(path).resolve())
        if key in self.entries:
            require(expected is None or self.entries[key]['sha256']==expected,'Conflicting input hash')
            return Path(key)
        return super().bind(path,expected)

    def check(self):
        for path,before in list(self.entries.items()):
            super().bind(path,before['sha256'])

PLANT_UNITS={'lai(ip)':'m2 leaf / m2 ground','canhgt(ip)':'m','rtd(ip)':'m','rtmass(ip)':'kg/m2 total root mass',
    'vdmt(ip)':'kg/m2 vegetative dry matter','rmagt(ip)':'kg/m2 above-ground surface residue',
    'watstr(ip)':'dimensionless native carried stress','temstr(ip)':'dimensionless native temperature stress',
    'cancov(ip)':'fraction','rescov(ip)':'fraction','inrcov(ip)':'fraction','rilcov(ip)':'fraction'}
DAILY_TAGS={f'DAY_{stage}_{group}' for stage in ('OPEN','CLOSE') for group in ('PLANT','STATE')}
EPOCHS=('EVAPPM_PRE','EVAPPM_POST','PTGRP_PRE','PTGRP_POST','PTGRA_PRE','PTGRA_POST','SWU_PRE','SWU_POST','GROW_PRE','GROW_POST')
WINDOW_TAGS={f'{stage}_{group}' for stage in EPOCHS for group in ('PLANT','WATER','STATE')}|{'SWU_REQUEST','SWU_ACCEPT','SWU_STOCK','WB_ET_STORE','EVP_DEMAND'}


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def load(path):return json.loads(Path(path).read_text())


def scalar(value):
    if isinstance(value,float):require(math.isfinite(value),'Nonfinite response operand')
    return Q(value)


def series(a,b,clocks,extensive):
    """Exact signed changes, cancellation, first/last and contiguous persistence."""
    require(set(a)==set(b)==set(clocks) and clocks==sorted(set(clocks)),'Series coverage/duplicate/ordered clock')
    delta={k:scalar(b[k])-scalar(a[k]) for k in clocks}
    changed=[k for k in clocks if delta[k]]
    episodes=[];active=None
    for k in clocks:
        if delta[k]:
            if active is None:active=dict(start=list(k),last=list(k),days=0,positive_days=0,negative_days=0,sign_transitions=0,last_sign=1 if delta[k]>0 else -1)
            sign=1 if delta[k]>0 else -1
            active['sign_transitions']+=int(sign!=active['last_sign']);active['last_sign']=sign
            active['last']=list(k);active['days']+=1;active['positive_days']+=int(delta[k]>0);active['negative_days']+=int(delta[k]<0)
        elif active is not None:
            active['first_equal_after']=list(k);episodes.append(active);active=None
    if active is not None:active['first_equal_after']=None;episodes.append(active)
    def extremum(fn):
        k=fn(clocks,key=lambda k:delta[k]);return dict(clock=list(k),baseline_exact=str(scalar(a[k])),candidate_exact=str(scalar(b[k])),delta_exact=str(delta[k]))
    out=dict(changed_days=len(changed),first_difference=list(changed[0]) if changed else None,
        last_difference=list(changed[-1]) if changed else None,minimum=extremum(min),maximum=extremum(max),
        maximum_absolute=extremum(lambda keys,key:max(keys,key=lambda k:abs(key(k)))),episodes=episodes,
        first_values_exact=[str(scalar(x[clocks[0]])) for x in (a,b)],last_values_exact=[str(scalar(x[clocks[-1]])) for x in (a,b)],
        end_minus_start_exact=[str(scalar(x[clocks[-1]])-scalar(x[clocks[0]])) for x in (a,b)])
    out['lane_ranges']={label:dict(minimum_exact=str(min(map(scalar,lane.values()))),maximum_exact=str(max(map(scalar,lane.values()))),negative_days=sum(scalar(v)<0 for v in lane.values())) for label,lane in [('baseline',a),('candidate',b)]}
    if extensive:
        out.update(baseline_sum_exact=str(sum(map(scalar,a.values()),Q(0))),candidate_sum_exact=str(sum(map(scalar,b.values()),Q(0))),
                   delta_sum_exact=str(sum(delta.values(),Q(0))),positive_delta_sum_exact=str(sum((v for v in delta.values() if v>0),Q(0))),
                   negative_delta_sum_exact=str(sum((v for v in delta.values() if v<0),Q(0))))
    return out


def periods(a,b,dates,extensive):
    require(bool(dates),'Empty response calendar')
    result={'full_period':series(a,b,dates,extensive),'annual':{}}
    for year in sorted({k[0] for k in dates}):
        subset=[k for k in dates if k[0]==year]
        result['annual'][str(year)]=series({k:a[k] for k in subset},{k:b[k] for k in subset},subset,extensive)
    return result


def extract(trace,schema,dates,windows):
    """Selective decoding of already validated bytes; no second causal replay."""
    allowed=set(dates);daily={};selected=[];last=0;footer=False
    nextdays={dates[i+1] for i,k in enumerate(dates[:-1]) if observation.in_windows(k,windows)}
    with Path(trace).open() as stream:
        require(stream.readline().strip()=='R05_SCHEMA 1','Selective extraction schema')
        for line in stream:
            v=line.split();require(v and not footer,'Trailing/blank selective record')
            if v[0]=='R05_END':require(len(v)==2 and int(v[1])==last,'Selective footer');footer=True;continue
            require(len(v)>=8 and int(v[0])==last+1,'Selective record sequence');last+=1
            y,d,o,index=map(int,v[1:5]);tag,kind=v[5:7]
            want=tag in DAILY_TAGS or tag in WINDOW_TAGS and observation.in_windows((y,d),windows) or tag.startswith(('GROW_PRE_','GROW_POST_')) and tag in WINDOW_TAGS and (y,d) in nextdays
            if not want:continue
            require((y,d) in allowed and o in (1,2,3),'Selected record clock')
            group=next((g for g in ('PLANT','WATER','STATE') if tag.endswith('_'+g)),tag)
            fields=schema[group]['fields'];require(kind==schema[group]['kind'] and int(v[7])==len(fields) and len(v)==8+len(fields),'Selected operand schema')
            values=[observation.decode(word,kind) for word in v[8:]]
            if kind=='i':require(all(-(2**31)<=x<2**31 for x in values),'Native selected INTEGER range')
            row=dict(clock=[y,d,o],seq=last,tag=tag,index=index,fields=fields,values=values)
            if tag in DAILY_TAGS:
                key=(y,d,o,tag);require(index==0 and key not in daily,'Duplicate daily plant/state');daily[key]=row
            else:selected.append(row)
    require(footer,'Missing trace footer')
    require(set(daily)=={(y,d,o,tag) for y,d in dates for o in (1,2,3) for tag in DAILY_TAGS},'Daily trajectory census')
    return daily,selected


def ledger_index(rows,dates):
    indexed={}
    for row in rows:
        k=tuple(row[n] for n in ('year','day','ofe'));require(k not in indexed,'Duplicate daily ledger')
        require(row['flux_invocations']==1 and row['previous_close_equal'],'Unsupported ledger cadence/continuity')
        for group,names in {'inputs_m_exact':{'rain','melt','irrigation','furrow','surface_runon','subsurface_runon'},'outputs_m_exact':{'surface','lateral','deep','plant_et','soil_et','residue_et','tile'},'start_stores_m_exact':{'soil_liquid','soil_ice','canopy','residue'},'end_stores_m_exact':{'soil_liquid','soil_ice','canopy','residue'}}.items():
            require(set(row[group])==names,'Ledger owner component set')
        net=sum(map(Q,row['inputs_m_exact'].values()),Q(0))-sum(map(Q,row['outputs_m_exact'].values()),Q(0))
        change=sum(map(Q,row['end_stores_m_exact'].values()),Q(0))-sum(map(Q,row['start_stores_m_exact'].values()),Q(0))
        require(net==Q(row['net_flux_m_exact']) and change==Q(row['store_change_m_exact']) and net-change==Q(row['residual_m_exact']),'Cached ledger exact arithmetic')
        indexed[k]=row
    require(set(indexed)=={(y,d,o) for y,d in dates for o in (1,2,3)},'Daily ledger calendar')
    for ofe in (1,2,3):
        for before,after in zip(dates,dates[1:]):
            require(indexed[(*before,ofe)]['end_stores_m_exact']==indexed[(*after,ofe)]['start_stores_m_exact'],'Cached ledger continuity')
    return indexed


def geometry(folder):
    text=(folder/'runs/p1.slp').read_text();lines=[s.strip() for s in text.splitlines() if s.strip() and not s.lstrip().startswith('#')]
    require(len(lines)==9,'Slope geometry schema')
    width=ordinary.number(lines[2].split()[1]);lengths=[ordinary.number(lines[i].split()[1]) for i in (3,5,7)]
    areas=ordinary.geometry(text,float(width),float(sum(lengths)))
    ordinary.no_contours((folder/'runs/p1.man').read_text())
    return Q(width),[Q(width*x) for x in lengths],areas


def ordinary_read(folder,dates):
    width,areas,floatareas=geometry(folder);watpath=folder/'output/H1.wat.dat'
    text=watpath.read_text();ordinary.wat(text,set(dates),floatareas)
    water={}
    for line in text.splitlines():
        v=line.split()
        if not v or not v[0].isdigit():continue
        o,d,y=map(int,v[:3]);water[y,d,o]=dict(zip(ordinary.WAT[3:],(Q(ordinary.number(t)) for t in v[3:])))
    sparse={}
    for kind in ('element','ebe'):
        sparse[kind]=ordinary.sparse((folder/f'output/H1.{kind}.dat').read_text(),kind,set(dates),dates[0][0])
    average,annual=ordinary.loss((folder/'output/H1.loss.dat').read_text(),float(width),sorted({y for y,d in dates}))
    reconciliation=ordinary.reconcile(sparse['element'],sparse['ebe'],float(width),sorted({y for y,d in dates}),average,annual)
    return dict(width=width,areas=areas,wat=water,sediment_reconciliation=reconciliation,**sparse)


def compare_ledgers(left,right,dates,areas):
    result={}
    groups={'inputs_m_exact':True,'outputs_m_exact':True,'start_stores_m_exact':False,'end_stores_m_exact':False}
    for ofe in (1,2,3):
        fields={}
        for group,extensive in groups.items():
            names=set(left[(*dates[0],ofe)][group]);require(names==set(right[(*dates[0],ofe)][group]),'Ledger component shape')
            for name in sorted(names):
                a={k:Q(left[(*k,ofe)][group][name])*1000 for k in dates};b={k:Q(right[(*k,ofe)][group][name])*1000 for k in dates}
                fields[group+'/'+name]=dict(meaning='Final reported EP, including its canopy contribution; not exclusively root uptake' if group=='outputs_m_exact' and name=='plant_et' else 'Final reported Es; not always identical to soil withdrawal' if group=='outputs_m_exact' and name=='soil_et' else 'Explicit native ledger component',unit='mm over local OFE area',local_area_m2_exact=str(areas[ofe-1]),kind='flux' if extensive else 'stock',**periods(a,b,dates,extensive))
                if extensive:
                    factor=areas[ofe-1]/1000
                    fields[group+'/'+name+'/volume']=dict(unit='m3 over local OFE area',**periods({k:v*factor for k,v in a.items()},{k:v*factor for k,v in b.items()},dates,True))
        for compartment in ('soil_liquid','soil_ice','canopy','residue'):
            a={k:(Q(left[(*k,ofe)]['end_stores_m_exact'][compartment])-Q(left[(*k,ofe)]['start_stores_m_exact'][compartment]))*1000 for k in dates}
            b={k:(Q(right[(*k,ofe)]['end_stores_m_exact'][compartment])-Q(right[(*k,ofe)]['start_stores_m_exact'][compartment]))*1000 for k in dates}
            fields['daily_store_change/'+compartment]=dict(unit='mm, closing minus opening stock',**periods(a,b,dates,True))
        for name in ('residual_m_exact','net_flux_m_exact','store_change_m_exact','snow_start_m_exact','snow_end_m_exact'):
            a={k:Q(left[(*k,ofe)][name])*1000 for k in dates};b={k:Q(right[(*k,ofe)][name])*1000 for k in dates}
            fields[name]=dict(unit='mm',**periods(a,b,dates,name in ('residual_m_exact','net_flux_m_exact','store_change_m_exact')))
        result[str(ofe)]=fields
    return result


def compare_plants(left,right,dates):
    result={}
    for ofe in (1,2,3):
        metrics={}
        for tag in sorted(DAILY_TAGS):
            fields=left[(*dates[0],ofe,tag)]['fields'];require(fields==right[(*dates[0],ofe,tag)]['fields'],'Plant field identity')
            for i,name in enumerate(fields):
                a={k:left[(*k,ofe,tag)]['values'][i] for k in dates};b={k:right[(*k,ofe,tag)]['values'][i] for k in dates}
                metrics[tag+'/'+name]=dict(unit='integer native state' if tag.endswith('_STATE') else PLANT_UNITS.get(name,'native auxiliary field, no physical-unit conversion'),kind='state, never summed',**periods(a,b,dates,False))
        result[str(ofe)]=metrics
    return result


def compare_ordinary(left,right,dates):
    require(left['width']==right['width'] and left['areas']==right['areas'],'Paired actual geometry differs')
    wat={};sediment={};presence={}
    for ofe in (1,2,3):
        fields={}
        for name in ordinary.WAT[3:]:
            a={k:left['wat'][(*k,ofe)][name] for k in dates};b={k:right['wat'][(*k,ofe)][name] for k in dates}
            fields[name]=dict(unit='m2' if name=='Area' else 'mm',**periods(a,b,dates,name in ordinary.FLUXES))
        area=sum(left['areas'][:ofe],Q(0))
        a={k:left['wat'][(*k,ofe)]['Q']*area/1000 for k in dates};b={k:right['wat'][(*k,ofe)]['Q']*area/1000 for k in dates}
        fields['Q_volume_m3']=dict(unit='m3, cumulative contributing OFE area, no contour',**periods(a,b,dates,True));wat[str(ofe)]=fields
        for kind,column,multiplier in [('element',23,left['width']),('ebe',12,left['width'])]:
            if kind=='ebe' and ofe!=3:continue
            keys={k for k in left[kind].keys()|right[kind].keys() if k[2]==ofe and k[:2] in set(dates)}
            presence[f'{kind}/{ofe}']=[dict(clock=list(k),baseline=k in left[kind],candidate=k in right[kind]) for k in sorted(keys)]
            a={k:Q(ordinary.number(left[kind][(*k,ofe)][column]))*multiplier if (*k,ofe) in left[kind] else Q(0) for k in dates}
            b={k:Q(ordinary.number(right[kind][(*k,ofe)][column]))*multiplier if (*k,ofe) in right[kind] else Q(0) for k in dates}
            sediment[f'{kind}/{ofe}']=dict(unit='kg leaving this OFE' if kind=='element' else 'kg delivered at hillslope outlet',absence='No emitted event contributes zero extensive export, never a zero stock',**periods(a,b,dates,True))
    return dict(wat=wat,sediment=sediment,sparse_union_presence=presence,sediment_reconciliation=dict(baseline=left['sediment_reconciliation'],candidate=right['sediment_reconciliation']))


def classify_demand(proof,rows):
    """Keep demand, actual accepted withdrawal and canopy partition distinct."""
    g=proof['records'];core=g['EVP_CORE'];require(all(math.isfinite(x) for x in core),'Nonfinite selected demand operand');request=Q(proof['EP_exact_m'])
    potential=Q(core[0])*Q(core[5])/1000
    raw_product=Q(core[0])*Q(core[1])*Q(core[5])*Q(observation.f32(.001))
    findings=[]
    if any(x<0 for x in (potential,request,Q(core[0]),Q(core[1]),Q(core[5]))):findings.append('negative_demand_or_coefficient')
    if findings:category='invalid_negative_demand_or_coefficient'
    elif request>0:category='positive_availability_limited_request'
    elif potential>0 and raw_product>0:category='positive_product_underflow_to_zero'
    elif potential>0:category='positive_potential_zero_availability_limited_request'
    else:category='zero_potential_or_inactive_demand'
    bytag=defaultdict(list)
    for row in rows:bytag[row['tag']].append(row)
    for tag in ('SWU_PRE_WATER','SWU_PRE_PLANT','SWU_POST_WATER','WB_ET_STORE'):
        require(len(bytag[tag])<=1,'Repeated selected daily demand owner')
    accepted=bytag['SWU_ACCEPT'];stocks=bytag['SWU_STOCK'];require(len(accepted)==len(stocks),'Selected withdrawal pair coverage')
    uptake=sum((Q(x['values'][1]) for x in accepted),Q(0));debit=Q(0);difference=Q(0);subtraction=Q(0);clamp=Q(0);layer_operations=[]
    for before,after in zip(accepted,stocks,strict=True):
        require(before['index']==after['index'] and before['seq']<after['seq'],'Withdrawal layer ordering')
        old,amount=before['values'];actual=after['values'][0]
        preclamp=observation.f32(old-amount);fires=preclamp<observation.f32(1e-10)
        require(actual==(0. if fires else preclamp),'Selected SWU subtraction/clamp replay')
        change=Q(old)-Q(actual);representation=Q(old)-Q(amount)-Q(preclamp);clamp_delta=Q(preclamp)-Q(actual)
        debit+=change;difference+=change-Q(amount);subtraction+=representation;clamp+=clamp_delta
        layer_operations.append(dict(layer=before['index'],preclamp_m=preclamp,clamp_branch=fires,subtraction_representation_debit_exact_m=str(representation),clamp_debit_exact_m=str(clamp_delta)))
    require(difference==subtraction+clamp,'Soil debit decomposition')
    pre=bytag['SWU_PRE_WATER'];plants=bytag['SWU_PRE_PLANT']
    if pre:
        require(bool(plants),'SWU root epoch absent')
        v=pre[0]['values'];root=plants[0]['values'][3]
        remaining=observation.f32(v[3]-v[0]) if v[0]>0 else v[3]
        withdrawal='canopy_covers_positive_request' if request>0 and remaining<=0 else 'positive_root_request' if remaining>0 else 'nonpositive_root_request'
        if remaining>0:
            accumulated=Q(stocks[-1]['values'][2]) if stocks else Q(0)
            withdrawal+=':native_full_accepted' if accumulated==Q(remaining) else ':native_partial_or_zero' if accumulated<Q(remaining) else ':native_above_request'
    else:
        remaining=None;root=None;withdrawal='SWU_not_called'
        growth=sorted(bytag['PTGRP_POST_PLANT']+bytag['PTGRA_POST_PLANT'],key=lambda x:x['seq'])
        if growth:
            root=growth[-1]['values'][3]
            withdrawal='inactive_nonpositive_postgrowth_roots' if root<=0 else 'skipped_zero_assigned_request' if request==0 else 'unexplained_positive_request_skip'
            if withdrawal=='unexplained_positive_request_skip':findings.append(withdrawal)
        else:findings.append('postgrowth_root_owner_not_observed')
        require(not accepted and not stocks,'Withdrawal records without SWU entry')
    store=bytag['WB_ET_STORE'];require(len(store)==1,'Missing selected final ET store')
    v=store[0]['values']
    return dict(clock=proof['clock'],ordinal=proof['ordinal'],demand_seq=proof['demand_seq'],
        diagnostic_potential_basal_exact_m=str(potential),actual_incoming_request_exact_m=str(request),
        request_classification=category,withdrawal_classification=withdrawal,
        etks=core[1],TAW=core[2],RAW=core[3],wftrp=core[4],etksden=core[7],denominator_nonpositive=core[7]<=0,
        pre_growth_root_depth=proof['pre_snapshot']['PLANT'][3],actual_SWU_root_depth=root,
        actual_SWU_incoming_EP_m=pre[0]['values'][3] if pre else None,root_remaining_request_m=remaining,accepted_root_sum_exact_m=str(uptake),accepted_minus_positive_root_request_exact_m=str(uptake-max(Q(0),Q(remaining))) if remaining is not None else None,actual_soil_debit_exact_m=str(debit),
        soil_debit_minus_accepted_exact_m=str(difference),subtraction_representation_debit_exact_m=str(subtraction),clamp_debit_exact_m=str(clamp),withdrawal_layer_operations=layer_operations,final_reported_EP_m=v[0],native_canopy_partition_m=v[6],
        canopy_input_m=v[3],canopy_remaining_m=v[5],
        native_accumulated_root_uptake_m=stocks[-1]['values'][2] if stocks else 0.,
        negative_findings=findings,epochs=rows,scientific_acceptance=False,
        limit='Diagnostic T0 is an exact-real expression, not a native intermediate. Potential/availability/denominator flags do not invent an unobserved branch or physiological denominator.')


def selected_demands(diagnostic,epochs,daily,dates):
    indexed=defaultdict(list)
    for row in epochs:indexed[tuple(row['clock'])].append(row)
    seen=set();proofs=[]
    for proof in diagnostic.get('evappm',[]):
        k=tuple(proof['clock']);require(k not in seen,'Repeated selected EVAPPM call requires explicit invocation split');seen.add(k)
        row=classify_demand(proof,indexed[k])
        position=dates.index(k[:2]);nextdate=dates[position+1] if position+1<len(dates) else None
        row['daily_close_plant']=daily[(*k,'DAY_CLOSE_PLANT')]
        row['next_day_growth_epochs']=[v for v in indexed[(*nextdate,k[2])] if v['tag'].startswith(('GROW_PRE_','GROW_POST_'))] if nextdate else []
        row['next_day_open_plant']=daily[(*nextdate,k[2],'DAY_OPEN_PLANT')] if nextdate else None
        row['next_day_growth_evidence_gap']=nextdate is not None and not row['next_day_growth_epochs']
        proofs.append(row)
    return proofs


def cache_contract(result,trace_hash,schema_hash,dates,windows,context=None):
    require(result.get('passed') is True and result['source_sha256']==trace_hash,'Validated readback/trace binding')
    require(result['reader_sha256']==ordinary.sha(observation.__file__),'Unknown validated reader identity')
    expected_helpers={str(Path(observation.__file__).parent/name):ordinary.sha(Path(observation.__file__).parent/name)
        for name in ('r05_flow_joins.py','r05_daily_ledger.py','r05_causal_joins.py')}
    require(result['helper_hashes']==expected_helpers,'Unknown validated helper identities')
    require(result['schema_sha256']==schema_hash and result['dates']==len(dates) and result['ofes']==3,'Readback schema/calendar identity')
    if context is not None:
        require(context['dates']==dates and context['windows']==windows and context['schema_sha256']==schema_hash,'Readback semantic context')
        require(context['reader_sha256']==result['reader_sha256'] and context['helper_hashes']==result['helper_hashes'] and context['ofes']==3,'Readback reader context')


def extraction_cache(trace,schema_path,dates,windows,trace_hash,root,bindings):
    context=dict(trace_sha256=trace_hash,schema_sha256=ordinary.sha(schema_path),dates=[list(k) for k in dates],windows=windows,
                 extractor_sha256=ordinary.sha(Path(__file__)),decoder_sha256=ordinary.sha(observation.__file__))
    if root is not None:
        root=Path(root)
        if root.exists():
            receipt=load(bindings.bind(root/'receipt.json'))
            require(receipt.get('passed') is True and receipt['context']==context,'Extraction cache identity')
            data=load(bindings.bind(root/'extraction.json',receipt['extraction_sha256']))
            daily={tuple(row['clock'])+(row['tag'],):row for row in data['daily']}
            require(len(daily)==len(data['daily'])==len(dates)*12,'Cached extraction cardinality')
            return daily,data['epochs']
    daily,epochs=extract(trace,load(schema_path),dates,windows)
    if root is not None:
        root.mkdir(parents=True,exist_ok=False)
        save(root/'extraction.json',dict(daily=list(daily.values()),epochs=epochs))
        save(root/'receipt.json',dict(passed=True,context=context,extraction_sha256=ordinary.sha(root/'extraction.json')))
        bindings.bind(root/'extraction.json');bindings.bind(root/'receipt.json')
    return daily,epochs


def read_lane(folder,task,receipt,schema_path,bindings,cached_envelope,cache_root=None):
    folder=Path(folder);dates=list(map(tuple,task['calendar']['dates']))
    require(receipt.get('passed') is True,'Failed lane receipt')
    require({k:v for k,v in receipt['inputs'].items() if k!='r05_observe.on'}==task['inputs'],'Declared physical input identity')
    require(set(receipt['inputs'])==set(task['inputs'])|{'r05_observe.on'},'Observed input set')
    expected_windows=''.join(' '.join(map(str,w))+'\n' for w in task['windows'])
    require((folder/'runs/r05_observe.on').read_text()==expected_windows,'Actual selected-window sidecar')
    require(set(receipt['outputs'])==ordinary.OUTPUTS,'Seven-file output contract')
    for name,digest in receipt['outputs'].items():bindings.bind(folder/'output'/name,digest)
    for name,digest in receipt['inputs'].items():bindings.bind(folder/'runs'/name,digest)
    trace=bindings.bind(folder/'runs/r05-observation.txt',receipt['trace_sha256'])
    path=bindings.bind(folder/'observation-readback.json',receipt['readback_sha256']);cached=load(path)
    result=cached['result'] if cached_envelope else cached
    cache_contract(result,receipt['trace_sha256'],ordinary.sha(schema_path),task['calendar']['dates'],task['windows'],cached['context'] if cached_envelope else None)
    for helper,digest in result['helper_hashes'].items():bindings.bind(helper,digest)
    schema=load(schema_path);daily,epochs=extraction_cache(trace,schema_path,dates,task['windows'],receipt['trace_sha256'],cache_root,bindings)
    diagnostic=None
    if 'diagnostic_sha256' in receipt:
        diagnostic=load(bindings.bind(folder/'diagnostic-readback.json',receipt['diagnostic_sha256']))
        require(diagnostic.get('passed') is True and diagnostic['windows']==task['windows'],'Diagnostic cache scope')
        require(diagnostic['behavior']==('cap_candidate' if task['lane']=='candidate' else 'observer'),'Diagnostic behavioral lane')
        require(any(v['sha256']==ordinary.sha(schema_path) and Path(v['path']).resolve()==schema_path for v in diagnostic['bindings']),'Diagnostic schema identity')
        require(any(v['sha256']==receipt['trace_sha256'] and Path(v['path']).resolve()==trace for v in diagnostic['bindings']),'Diagnostic trace binding')
    return dict(ledger=ledger_index(result['daily_ledgers'],dates),plant=daily,epochs=epochs,
                ordinary=ordinary_read(folder,dates),demand=selected_demands(diagnostic,epochs,daily,dates) if diagnostic else None,
                diagnostic_available=diagnostic is not None)


def compare(left,right,dates,label):
    require(left['ordinary']['areas']==right['ordinary']['areas'],'Local area identity')
    return dict(contrast=label,scientific_acceptance=False,
        ledger=compare_ledgers(left['ledger'],right['ledger'],dates,left['ordinary']['areas']),
        plant=compare_plants(left['plant'],right['plant'],dates),ordinary=compare_ordinary(left['ordinary'],right['ordinary'],dates),
        selected_demand=dict(baseline=left['demand'],candidate=right['demand']),
        selected_growth_epochs=dict(baseline=left['epochs'],candidate=right['epochs']),
        diagnostic_coverage=dict(baseline=left['diagnostic_available'],candidate=right['diagnostic_available']),
        limits=['No pond or all-storage closure claim; residuals remain signed.',
                'Full daily states do not provide detailed formula attribution outside declared windows.',
                'Unexplained material episodes require scientific disposition; no new magnitude threshold is defined.',
                'Observed growth/stress carry is not validation of a physiological ratio.'])


def prepared_inputs(campaign,prior,bindings):
    declaration=load(bindings.bind(campaign/'declaration.json'))
    olddecl=load(bindings.bind(prior/'declaration.json'));oldagg=load(bindings.bind(prior/'receipt.json'))
    require(oldagg.get('passed') is True and len(oldagg['cases'])==12 and len(oldagg['paired_readbacks'])==6,'Completed prior aggregate required')
    for root in (campaign,prior):
        build_path=bindings.bind(root/'build-receipt.json');build=load(build_path)
        approval=load(bindings.bind(root/'run-approval.json'))
        require(build.get('passed') is True and approval.get('run_allowed') is True,'Actual build/run approval required')
        require(approval['build_receipt_sha256']==ordinary.sha(build_path) and approval['declaration_sha256']==ordinary.sha(root/'declaration.json'),'Run approval identity')
        for review in approval['reviews'].values():bindings.bind(review['path'],review['sha256'])
    for module in (Path(__file__),Path(ordinary.__file__),Path(observation.__file__)):bindings.bind(module)
    require(len(declaration['tasks'])==21,'Declared 21-history scope')
    identities=[(t['name'],t['lane']) for t in declaration['tasks']]
    require(len(identities)==len(set(identities)) and sum(lane=='r4_observer' for _,lane in identities)==3,'Declared lane identities')
    old={(r['name'],r['lane']):r for r in oldagg['cases']};require(len(old)==12 and all(r.get('passed') is True for r in old.values()),'Prior lane identity/completion')
    return declaration,olddecl,oldagg,old


def case_result(campaign,prior,out,name,declaration,olddecl,old,bindings):
    tasks=declaration['tasks'];selected=[t for t in tasks if t['name']==name]
    require({t['lane'] for t in selected} in ({'observer','candidate','candidate_plain'},{'observer','candidate','candidate_plain','r4_observer'}),'Complete declared case lane set')
    current={}
    for t in selected:
        row=load(bindings.bind(campaign/'cases'/name/t['lane']/'receipt.json'))
        require(row.get('passed') is True and (row['name'],row['lane'])==(name,t['lane']),'Completed individual lane required')
        if t['lane']=='candidate_plain':require(row['inputs']==t['inputs'],'Clean declared physical inputs')
        current[t['lane']]=row
    require(current['candidate_plain']['outputs']==current['candidate']['outputs'],'Candidate clean/observed parity')
    for filename,digest in current['candidate_plain']['inputs'].items():bindings.bind(campaign/'cases'/name/'candidate_plain/runs'/filename,digest)
    for filename,digest in current['candidate_plain']['outputs'].items():bindings.bind(campaign/'cases'/name/'candidate_plain/output'/filename,digest)
    require(set(current['candidate_plain']['outputs'])==ordinary.OUTPUTS,'Clean seven-file output contract')
    task=next(t for t in selected if t['lane']=='observer');dates=list(map(tuple,task['calendar']['dates']))
    schema=bindings.bind(declaration['schema']);oldschema=bindings.bind(olddecl['schema'])
    lanes={}
    for lane in ('observer','candidate'):
        t=next(t for t in selected if t['lane']==lane)
        require(t['calendar']==task['calendar'],'Paired calendar definition')
        lanes[lane]=read_lane(campaign/'cases'/name/lane,t,current[lane],schema,bindings,True,out/'extractions'/lane)
    save(out/'a8-to-cap.json',compare(lanes['observer'],lanes['candidate'],dates,'a8 observer → cap observed; clean seven-file parity verified'))
    require(old[name,'candidate']['outputs']==current['observer']['outputs'],'Historical a8 ordinary bridge')
    if 'r4_observer' in current:
        row=current['r4_observer'];require(row['outputs']==old[name,'baseline']['outputs'],'Historical r4 ordinary bridge')
        t=next(t for t in selected if t['lane']=='r4_observer')
        require(t['calendar']==task['calendar'],'Fresh r4 calendar bridge')
        base=read_lane(campaign/'cases'/name/'r4_observer',t,row,schema,bindings,True,out/'extractions'/'r4_observer');final=lanes['observer'];basis='fresh declared r4 and a8 observer counterlanes'
    else:
        pair=[]
        for lane in ('baseline','candidate'):
            historical_task=next(t for t in olddecl['tasks'] if t['name']==name and t['lane']==lane)
            require(historical_task['calendar']==task['calendar'],'Historical calendar bridge')
            folder=prior/'cases'/name/lane
            require(load(bindings.bind(folder/'receipt.json'))==old[name,lane],'Historical aggregate/per-case receipt identity')
            pair.append(read_lane(folder,historical_task,old[name,lane],oldschema,bindings,False,out/'extractions'/('prior-'+lane)))
        base,final=pair;basis='retained completed R05 r4/a8 pair; a8 ordinary bridge verified'
    save(out/'r4-to-a8.json',compare(base,final,dates,'r4 → a8; '+basis))
    return dict(name=name,current_lane_receipts=current,historical_basis=basis,
                outputs={str(out/filename):ordinary.sha(out/filename) for filename in ('a8-to-cap.json','r4-to-a8.json')})


def run_case(campaign,prior,out,name):
    campaign=Path(campaign).resolve();prior=Path(prior).resolve();out=Path(out).resolve()
    require(not out.exists(),'Response root must be fresh');bindings=Bindings()
    declaration,olddecl,oldagg,old=prepared_inputs(campaign,prior,bindings)
    require(name in {t['name'] for t in declaration['tasks']},'Undeclared response case')
    # Gate every required receipt before creating any response output.
    for t in (t for t in declaration['tasks'] if t['name']==name):
        require(load(bindings.bind(campaign/'cases'/name/t['lane']/'receipt.json')).get('passed') is True,'Case lanes incomplete')
    out.mkdir();result=case_result(campaign,prior,out,name,declaration,olddecl,old,bindings);bindings.check()
    result.update(passed=True,scientific_acceptance=False,scope='Completed-case response only; final 21-history aggregate still required',
        campaign_declaration_sha256=ordinary.sha(campaign/'declaration.json'),prior_aggregate_sha256=ordinary.sha(prior/'receipt.json'),
        reader_sha256=ordinary.sha(Path(__file__)),bindings=bindings.entries)
    save(out/'case-receipt.json',result);return result


def run(campaign,prior,out,completed_cases=()):
    campaign=Path(campaign).resolve();prior=Path(prior).resolve();out=Path(out).resolve()
    require(not out.exists(),'Response root must be fresh');bindings=Bindings()
    aggregate=load(bindings.bind(campaign/'receipt.json'));require(aggregate.get('passed') is True,'Completed aggregate required')
    declaration,olddecl,oldagg,old=prepared_inputs(campaign,prior,bindings)
    require(len(aggregate['cases'])==21 and len(aggregate['paired_readbacks'])==9,'Final campaign cardinality')
    current={(row['name'],row['lane']):row for row in aggregate['cases']}
    require(len(current)==21 and all(row.get('passed') is True for row in current.values()),'Complete unique campaign lanes')
    require(set(current)=={(t['name'],t['lane']) for t in declaration['tasks']},'Final declared lane identity')
    for group in ('bindings','paired_readbacks'):
        for path,digest in aggregate[group].items():bindings.bind(path,digest)
    ready={}
    for folder in completed_cases:
        result=load(bindings.bind(Path(folder)/'case-receipt.json'));name=result['name']
        require(name not in ready and result.get('passed') is True,'Duplicate/incomplete case cache')
        require(result['campaign_declaration_sha256']==ordinary.sha(campaign/'declaration.json') and result['prior_aggregate_sha256']==ordinary.sha(prior/'receipt.json') and result['reader_sha256']==ordinary.sha(Path(__file__)),'Completed-case cache identity')
        require(result['current_lane_receipts']=={lane:row for (case,lane),row in current.items() if case==name},'Case cache/final aggregate join')
        for path,entry in result['bindings'].items():
            bindings.bind(path,entry['sha256']);require(bindings.entries[str(Path(path).resolve())]==entry,'Case input metadata drift')
        for path,digest in result['outputs'].items():bindings.bind(path,digest)
        ready[name]=result
    names=sorted({t['name'] for t in declaration['tasks']});require(len(names)==6 and set(ready)<=set(names),'Six-case response scope')
    out.mkdir();summaries=[]
    for name in names:
        if name in ready:result=ready[name]
        else:
            case=out/name;case.mkdir();result=case_result(campaign,prior,case,name,declaration,olddecl,old,bindings)
            require(result['current_lane_receipts']=={lane:row for (n,lane),row in current.items() if n==name},'Actual final case receipt join')
        summaries.append({k:result[k] for k in ('name','historical_basis','outputs')})
    bindings.check();result=dict(passed=True,scientific_acceptance=False,cases=summaries,bindings=bindings.entries,
        reused_completed_cases=sorted(ready),collection='Validated ledger reuse; cached selective plant/state and window-epoch extraction; ordinary files parsed separately.',
        acceptance='Final response coverage only; independent consequence and release gates remain separate.')
    save(out/'receipt.json',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--campaign',required=True);parser.add_argument('--prior',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--case');parser.add_argument('--completed-case',action='append',default=[])
    args=parser.parse_args()
    if args.case:
        require(not args.completed_case,'Case mode cannot claim final case aggregation')
        run_case(args.campaign,args.prior,args.out,args.case)
    else:run(args.campaign,args.prior,args.out,args.completed_case)
