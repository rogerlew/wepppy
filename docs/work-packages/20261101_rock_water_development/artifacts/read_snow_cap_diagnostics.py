"""Original finite-window snow-cap, GRNA and EVAPPM diagnostic audit.

Source behavior is explicit. Strict arithmetic/readback is not scientific
acceptance, and represented budgets are retained with their signed errors.
"""
from collections import Counter
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import struct
import read_r05_observation as framing


def require(ok,message):
    if not ok:raise ValueError(message)


def f(value):
    try:answer=struct.unpack('>f',struct.pack('>f',value))[0]
    except (OverflowError,struct.error) as exc:raise ValueError('Binary32 overflow') from exc
    require(math.isfinite(answer),'Nonfinite binary32 result')
    return answer


def same(a,b):return struct.pack('>f',a)==struct.pack('>f',b)

def equal(actual,expected,message):
    require(len(actual)==len(expected) and all(same(a,b) for a,b in zip(actual,expected)),message)


def divide(a,b):
    require(b!=0,'Unsupported zero division coordinate')
    return f(a/b)


def cap(potential,depth,density):
    full=False;water=potential
    if potential>=0:
        require(density!=0,'Unsupported cap-owner zero density')
        full=divide(f(potential*f(1000.)),density)>=depth
        if full:water=f(depth*divide(density,f(1000.)))
    return water,full


def identity(pre):
    depth,density,owner_depth,owner_density,water_density,new,drift_new,drift_old=pre
    kind=1 if depth==owner_depth and density==owner_density else 0
    if not kind and depth>0 and depth==owner_depth and new==drift_new==drift_old==0:
        if density==divide(f(owner_density*owner_depth),depth):kind=2
    owned=kind>0 and depth>0 and density>0 and owner_density>0 and water_density==1000.
    return kind,owned


def transition(depth,density,water,water_density,rain,old_density,apply):
    debit_density=density if water>0 else old_density
    debit=(depth if apply else divide(f(water*water_density),density)) if water>0 else 0.
    remaining=f(depth-debit)
    if remaining<=0:
        release=f(f(depth*density)*f(.001));remaining=0.;newdensity=0.
    elif density>=350.:
        release=f(f(debit*density)*f(.001));newdensity=density
    else:
        newdensity=f(density*divide(depth,remaining))
        if newdensity<=350.:
            release=0.
            if rain>0:
                increase=divide(f(f(1000.)*rain),remaining)
                room=f(f(350.)-newdensity)
                if increase<=room:rain=0.;newdensity=f(newdensity+increase)
                else:rain=f(rain-divide(f(remaining*room),f(1000.)));newdensity=f(350.)
        else:release=f(f(f(newdensity-f(350.))*remaining)*f(.001));newdensity=f(350.)
    if newdensity>522.:newdensity=f(522.)
    if remaining<=0:newdensity=0.
    return dict(debit=debit,debit_density=debit_density,depth=remaining,density=newdensity,
                release=release,rain=rain)


def snow_proof(group,behavior):
    entry=group['SNOW_ENTRY'];inputs=group['SNOW_BRANCH_INPUT'];warm=group['SNOW_WARM_PACK']
    depth,density,previous_depth,old_density=warm
    tmax,tmin,drift_new,drift_old,densnf,water_density=inputs
    expected_depth=f(f(f(entry[2]+entry[7])+drift_new)+drift_old)
    numerator=f(f(entry[3]*f(entry[2]+drift_old))+f(densnf*f(entry[7]+drift_new)))
    expected_density=divide(numerator,expected_depth)
    equal(warm,[expected_depth,expected_density,entry[2],entry[3]],'Warm local pack construction mismatch')
    if depth>0:
        pre=group['SNOW_CAP_PRE'];raw=group['MELT_RAW'];returned=group['MELT_RETURN']
        equal(pre,[depth,density,entry[1],entry[5],water_density,entry[7],drift_new,drift_old],'Current/cap owner operand mismatch')
        equal(raw[5:7],pre[2:4],'MELT cap-owner operand mismatch')
        demand=f(f(.0254)*f(f(f(raw[0]+raw[1])+raw[2])+raw[3]))
        require(same(raw[4],demand),'MELT potential construction mismatch')
        water,full=cap(raw[4],raw[5],raw[6])
        require(group['MELT_CAP_FLAG']==[int(full)],'MELT cap predicate mismatch')
        equal(returned,[water,pre[2],pre[3]],'MELT cap result/owner mismatch')
        kind,owned=identity(pre)
        apply=behavior=='cap_candidate' and full and owned and water>0
        require(group['SNOW_CAP_FLAGS']==[int(full),int(owned),int(apply),kind],'SNOW cap ownership/application flags mismatch')
    else:
        pre=[depth,density,entry[1],entry[5],water_density,entry[7],drift_new,drift_old]
        water=0.;full=False;kind=0;owned=False;apply=False
    result=transition(depth,density,water,water_density,entry[6],old_density,apply)
    equal(group['SNOW_DEBIT'],[depth,result['debit'],water,result['debit_density']],'SNOW depth debit mismatch')
    expected=[result['depth']]*3+[result['debit_density'],result['density'],result['density'],
              result['rain'],entry[7],result['release'],result['release']]
    equal(group['SNOW_RETURN'],expected,'SNOW release/retained pack mismatch')
    local=Q(depth)*Q(density)/1000;owner=Q(pre[2])*Q(pre[3])/1000
    retained=Q(result['depth'])*Q(result['density'])/1000
    released=Q(result['release']);rain_change=Q(result['rain'])-Q(entry[6])
    bound=None;classification='not_applied'
    if apply:
        product=Q(depth)*Q(density);rounded=Q(f(depth*density));factor=Q(f(.001))
        bound=abs(rounded-product)*abs(factor)+abs(product)*abs(factor-Q(1,1000))
        bound+=abs(released-rounded*factor)+abs(local-owner)
        require(abs(released-owner)<=bound,'Operation-derived full-release bound mismatch')
        original=transition(depth,density,water,water_density,entry[6],old_density,False)
        classification='removed_positive_roundtrip_remainder' if original['depth']>0 else 'already_exhausted_original_roundtrip'
    return dict(full_cap=full,identity_kind=kind,owned=owned,applied=apply,classification=classification,
        owner_SWE_exact_m=str(owner),local_SWE_exact_m=str(local),released_exact_m=str(released),
        retained_exact_m=str(retained),local_budget_exact_m=str(released+retained+rain_change-local),
        owner_budget_exact_m=str(released+retained+rain_change-owner),
        operation_bound_exact_m=str(bound) if bound is not None else None,
        inputs=group,result=result,scientific_acceptance=False)


def grna_proof(group):
    np,positive,depression,clamped=group['GRNA_EXIT_FLAGS']
    require(np in (0,1) and all(v in (0,1) for v in (positive,depression,clamped)),'Invalid GRNA branch flags')
    require(not (np or depression or clamped) or positive==1,'GRNA branch flags lack positive-cumulative owner')
    raw=group.get('GRNA_PRE_CLAMP');result=group['GRNA_EXIT_RESULT'];post=group['IR_GRNA_POST']
    require((raw is not None)==(np!=0),'GRNA pre-clamp coverage mismatch')
    if raw is not None:
        require(same(raw[0],raw[1]),'GRNA runoff/excess identity mismatch')
        expected=raw[0]<f(1e-4)
        require(clamped==int(expected),'GRNA minimum-runoff predicate mismatch')
        equal(result,[0. if expected else raw[0],raw[2]],'GRNA clamp result mismatch')
        classification='preclamp_minimum_applied' if expected else 'preclamp_retained'
    else:
        require(clamped==0,'GRNA clamp without raw owner')
        classification='no_positive_cumulative_excess' if not positive else 'positive_cumulative_without_final_positive_result'
    equal([post[0],post[2]],result,'GRNA return/caller mismatch')
    return dict(classification=classification,flags=group['GRNA_EXIT_FLAGS'],records=group)


def evap_proof(group,snapshot):
    core=group['EVP_CORE'];owner=group['EVP_CORE_OWNER'];soil=group['EVP_SOIL_DEMAND'];demand=group['EVP_DEMAND']
    state=snapshot['STATE'];plant=snapshot['PLANT'];water=snapshot['WATER']
    require(owner==[state[1],state[3],state[0]],'EVAPPM crop/layer owner mismatch')
    require(len(snapshot['LAYER'])==owner[2],'EVAPPM layer snapshot coverage mismatch')
    equal([demand[3],demand[4],demand[5]],[water[1],water[0],water[2]],'EVAPPM carry owner changed before demand')
    equal(demand[6:8],plant[:2],'EVAPPM demand/plant epoch mismatch')
    ep=f(f(f(core[0]*core[1])*core[5])*f(.001))
    potes=f(f(core[0]*soil[4])*f(.001))
    require(same(soil[6],potes),'EVAPPM potential soil demand mismatch')
    residue=group.get('EVP_RESIDUE_BRANCH');needs=potes>demand[3]
    require((residue is not None)==needs,'EVAPPM residue branch coverage mismatch')
    if needs:
        bpotes=f(potes-demand[3]);combined=min(f(soil[4]*soil[3]),f(residue[1]*residue[2]))
        es=f(divide(f(combined*bpotes),soil[4])+demand[3])
        equal([residue[0],residue[3],residue[4]],[bpotes,combined,es],'EVAPPM residue arithmetic mismatch')
    else:es=potes
    equal(demand[:2],[ep,es],'EVAPPM final EP/ES construction mismatch')
    return dict(owner=owner,residue_branch=needs,records=group,pre_snapshot=snapshot,
                EP_exact_m=str(Q(ep)),ES_exact_m=str(Q(es)),scientific_acceptance=False)


def bind(path):
    path=Path(path);s=path.stat()
    return dict(path=str(path.resolve()),sha256=framing.sha(path),size=s.st_size,mtime_ns=s.st_mtime_ns)


def audit(path,schema_path,windows,behavior):
    require(behavior in ('observer','cap_candidate'),'Explicit behavior required')
    windows=framing.validate_windows(windows)
    paths=[Path(path),Path(schema_path),Path(__file__),Path(framing.__file__)]
    before=[bind(p) for p in paths]
    schema=json.loads(Path(schema_path).read_text())
    required={'SNOW_BRANCH_INPUT':6,'SNOW_WARM_PACK':4,'SNOW_CAP_PRE':8,'SNOW_CAP_FLAGS':4,
              'MELT_CAP_FLAG':1,'GRNA_EXIT_FLAGS':4,'GRNA_EXIT_RESULT':2,'EVP_CORE':23,
              'EVP_CORE_OWNER':3,'EVP_SOIL_DEMAND':7,'EVP_RESIDUE_BRANCH':5}
    require(all(k in schema and len(schema[k]['fields'])==n for k,n in required.items()),'Required v8 diagnostic schema missing')
    field_order={
        'SNOW_BRANCH_INPUT':['tmax','tmin','drift_new','drift_old','new_snow_density','water_density'],
        'SNOW_WARM_PACK':['current_depth','current_density','prior_local_depth','prior_density'],
        'SNOW_CAP_PRE':['current_depth','current_density','cap_depth','cap_density','water_density','new_snow','drift_new','drift_old'],
        'SNOW_CAP_FLAGS':['cap_executed','same_pack','direct_debit_applied','identity_kind'],
        'SNOW_DEBIT':['current_depth','snow_debit','water_melt','debit_density'],
        'MELT_CAP_FLAG':['existing_cap_executed'],
        'GRNA_PRE_CLAMP':['raw_runoff','accumulated_excess','duration'],
        'GRNA_EXIT_FLAGS':['np','positive_cumulative_excess_entered','depression_absorbed','minimum_runoff_clamped'],
        'GRNA_EXIT_RESULT':['runoff','duration'],
        'EVP_CORE':['etorc','etks','TAW','RAW','wftrp','kcbcon','tpdp','etksden','rawpaj','etcsc','kcbadj','kcb','rawp','rhd','fwv','ed','emaxt','dlt','rn','gma','ee','tave','eo'],
        'EVP_CORE_OWNER':['nowcrp','crpindx','nsl'],
        'EVP_SOIL_DEMAND':['TEW','REW','wfevp','etkr','etke','epdp','potes'],
        'EVP_RESIDUE_BRANCH':['bpotes','eaj','kcmax','kecon','es']}
    require(all(k in schema and schema[k]['fields']==fields for k,fields in field_order.items()),'Diagnostic field ownership/order mismatch')
    winter={};evap={};grna={};snapshots={};ordinal=Counter();counts=Counter()
    snow_witnesses=[];evap_witnesses=[];grna_witnesses=[];winter_witnesses=[]
    selected_rows=0;total_rows=0
    snow_tags={'WINTER_SNOW_PRE','SNOW_ENTRY','SNOW_BRANCH_INPUT','SNOW_WARM_PACK','SNOW_CAP_PRE',
               'MELT_RAW','MELT_CAP_FLAG','MELT_RETURN','SNOW_CAP_FLAGS','SNOW_DEBIT','SNOW_RETURN',
               'WINTER_SNOW_POST','WINTER_MELT_HOUR'}
    snow_next={'SNOW_ENTRY':'SNOW_BRANCH_INPUT','SNOW_CAP_PRE':'MELT_RAW','MELT_RAW':'MELT_CAP_FLAG',
               'MELT_CAP_FLAG':'MELT_RETURN','MELT_RETURN':'SNOW_CAP_FLAGS','SNOW_CAP_FLAGS':'SNOW_DEBIT',
               'SNOW_DEBIT':'SNOW_RETURN','SNOW_RETURN':'WINTER_SNOW_POST','WINTER_SNOW_POST':'WINTER_MELT_HOUR'}
    def snapshot(row,key):
        stage=row['snapshot'];part=row['group'];slot=(key,stage)
        if part=='LAYER':
            if row['index']==1:
                require(slot not in snapshots,'Duplicate/incomplete snapshot entry')
                snapshots[slot]=dict(LAYER=[],phase='LAYER',first_seq=row['seq'])
            require(slot in snapshots and snapshots[slot]['phase']=='LAYER','Snapshot layer order')
            require(row['index']==len(snapshots[slot]['LAYER'])+1,'Snapshot layer coverage')
            snapshots[slot]['LAYER'].append(row['values'])
            return None
        require(slot in snapshots and row['index']==0,'Missing snapshot layer/owner')
        block=snapshots[slot]
        expected={'PLANT':'LAYER','WATER':'PLANT','STATE':'WATER'}
        require(part in expected and block['phase']==expected[part],'Snapshot component order')
        block[part]=row['values'];block['phase']=part
        if part!='STATE':return None
        require(block['STATE'][0]==len(block['LAYER']) and block['STATE'][0]>0,'Snapshot layer count')
        del snapshots[slot];return {k:v for k,v in block.items() if k!='phase'}
    for row in framing.records(path,schema):
        total_rows+=1
        require(row['year']>0 and 1<=row['day']<=366 and row['ofe']>0,'Invalid observation clock')
        if not framing.in_windows((row['year'],row['day']),windows):continue
        selected_rows+=1;tag=row['tag'];key=(row['year'],row['day'],row['ofe']);values=row['values']
        if row['snapshot'] in ('WINTER_PRE','WINTER_POST','EVAPPM_PRE','EVAPPM_POST'):
            block=snapshot(row,key)
            if block is None:continue
            stage=row['snapshot']
            if stage=='WINTER_PRE':
                require(key not in winter,'Overlapping WINTER invocation')
                ordinal[(key,'winter')]+=1
                winter[key]=dict(ordinal=ordinal[(key,'winter')],hours=0,group=None,returned=False,pre=block)
            elif stage=='WINTER_POST':
                require(key in winter,'WINTER return without entry');active=winter[key]
                require(active['hours']==24 and active['group'] is None and active['returned'],'Incomplete WINTER mandatory call coverage')
                ret=active['return_values'];water=block['WATER']
                equal([water[8],water[9],water[10],water[11],water[12]],ret[:5],'WINTER return/post snapshot mismatch')
                winter_witnesses.append(dict(clock=key,ordinal=active['ordinal'],hours=24,return_values=ret));del winter[key]
            elif stage=='EVAPPM_PRE':
                require(key not in evap,'Overlapping EVAPPM invocation')
                ordinal[(key,'evap')]+=1
                evap[key]=dict(ordinal=ordinal[(key,'evap')],pre=block,records={},phase='start',proved=False)
            else:
                require(key in evap and evap[key]['proved'],'EVAPPM missing mandatory demand records')
                del evap[key];counts['evappm_calls']+=1
            continue
        if tag in snow_tags:
            require(key in winter,'Snow record outside actual WINTER invocation');active=winter[key]
            require(1<=row['index']<=24,'Snow hour range')
            if tag=='WINTER_SNOW_PRE':
                require(active['group'] is None and row['index']==active['hours']+1,'Missing/duplicate/reordered snow hour')
                previous=active.get('last_pack')
                if previous is None:
                    previous=[active['pre']['WATER'][10],active['pre']['WATER'][10],active['pre']['WATER'][12]]
                equal(values[:3],previous,'Snow pack identity across hourly calls')
                active['group']=dict(hour=row['index'],records={tag:values},next='SNOW_ENTRY',first_seq=row['seq'])
                continue
            group=active['group'];require(group is not None and row['index']==group['hour'],'Snow clock/call join mismatch')
            require(tag==group['next'] and tag not in group['records'],'Missing/duplicate/reordered snow owner')
            group['records'][tag]=values;g=group['records']
            if tag=='SNOW_ENTRY':
                p=g['WINTER_SNOW_PRE']
                equal(values,[p[0],p[0],p[0],p[2],p[2],p[2],p[4],p[5]],'SNOW entry/common pack mismatch')
            if tag=='SNOW_BRANCH_INPUT':
                mean=divide(f(values[0]+values[1]),f(2.))
                group['warm']=g['SNOW_ENTRY'][0]>0 and mean>=0
                group['next']='SNOW_WARM_PACK' if group['warm'] else 'SNOW_RETURN'
                continue
            if tag=='SNOW_WARM_PACK':
                group['next']='SNOW_CAP_PRE' if values[0]>0 else 'SNOW_DEBIT'
                continue
            if tag=='SNOW_RETURN':
                require(same(values[0],values[1]) and same(values[0],values[2]) and same(values[4],values[5])
                        and same(values[8],values[9]),'SNOW return common/local consistency')
                require(same(values[7],g['SNOW_ENTRY'][7]),'SNOW changed snowfall input')
                if group['warm']:
                    proof=snow_proof(g,behavior)
                    proof.update(clock=key,ordinal=active['ordinal'],hour=group['hour'],first_seq=group['first_seq'],return_seq=row['seq'])
                    snow_witnesses.append(proof);counts['warm_snow_calls']+=1
                    counts['applied_caps']+=int(proof['applied']);counts['full_caps']+=int(proof['full_cap'])
                else:counts['nonwarm_snow_calls']+=1
            if tag=='WINTER_SNOW_POST':
                ret=g['SNOW_RETURN']
                equal(values,[ret[1],ret[2],ret[5],ret[8],ret[6],ret[7],ret[0],ret[3],ret[4]],'SNOW return/WINTER caller mismatch')
            if tag=='WINTER_MELT_HOUR':
                ret=g['SNOW_RETURN']
                equal(values,[ret[8],ret[6],ret[7],ret[1],ret[2],ret[5]],'Hourly melt export mismatch')
                active['last_pack']=[ret[1],ret[2],ret[5]]
                active['hours']+=1;active['group']=None;counts['snow_calls']+=1
            else:group['next']=snow_next[tag]
            continue
        if tag=='WINTER_RETURN':
            require(key in winter and row['index']==0,'WINTER return owner/clock')
            active=winter[key]
            require(not active['returned'] and active['hours']==24 and active['group'] is None,'WINTER return before complete hourly coverage')
            active['returned']=True;active['return_values']=values
            continue
        if tag in ('IR_GRNA_PRE','GRNA_PRE_CLAMP','GRNA_EXIT_FLAGS','GRNA_EXIT_RESULT','IR_GRNA_POST'):
            require(row['index']==0,'GRNA index')
            if tag=='IR_GRNA_PRE':
                require(key not in grna,'Overlapping GRNA call');ordinal[(key,'grna')]+=1
                grna[key]=dict(records={tag:values},phase='start',ordinal=ordinal[(key,'grna')],first_seq=row['seq']);continue
            require(key in grna,'GRNA missing caller entry');active=grna[key];g=active['records']
            require(tag not in g,'Duplicate GRNA owner')
            expected={'GRNA_PRE_CLAMP':('start',),'GRNA_EXIT_FLAGS':('start','GRNA_PRE_CLAMP'),
                      'GRNA_EXIT_RESULT':('GRNA_EXIT_FLAGS',),'IR_GRNA_POST':('GRNA_EXIT_RESULT',)}
            require(active['phase'] in expected[tag],'Missing/reordered GRNA owners')
            g[tag]=values;active['phase']=tag
            if tag=='IR_GRNA_POST':
                proof=grna_proof(g);proof.update(clock=key,ordinal=active['ordinal'],first_seq=active['first_seq'],return_seq=row['seq'])
                grna_witnesses.append(proof);counts['grna_calls']+=1;del grna[key]
            continue
        if tag in ('EVP_CORE','EVP_CORE_OWNER','EVP_SOIL_DEMAND','EVP_RESIDUE_BRANCH','EVP_DEMAND'):
            require(row['index']==0 and key in evap,'EVAPPM demand lacks actual invocation')
            active=evap[key];g=active['records'];require(tag not in g,'Duplicate EVAPPM demand owner')
            expected={'EVP_RESIDUE_BRANCH':('start',),'EVP_CORE':('start','EVP_RESIDUE_BRANCH'),
                      'EVP_CORE_OWNER':('EVP_CORE',),'EVP_SOIL_DEMAND':('EVP_CORE_OWNER',),'EVP_DEMAND':('EVP_SOIL_DEMAND',)}
            require(active['phase'] in expected[tag],'Missing/reordered EVAPPM demand owners')
            g[tag]=values;active['phase']=tag
            if tag=='EVP_DEMAND':
                proof=evap_proof(g,active['pre']);proof.update(clock=key,ordinal=active['ordinal'],first_seq=active['pre']['first_seq'],demand_seq=row['seq'])
                evap_witnesses.append(proof);active['proved']=True
    require(not winter and not evap and not grna and not snapshots,'Incomplete diagnostic invocation at footer')
    require(selected_rows>0,'No records in selected windows')
    require(before==[bind(p) for p in paths],'Diagnostic inputs changed while reading')
    budgets=Counter()
    for proof in snow_witnesses:
        budgets['nonzero_local_budget']+=Q(proof['local_budget_exact_m'])!=0
        budgets['nonzero_owner_budget']+=Q(proof['owner_budget_exact_m'])!=0
    applied=[p for p in snow_witnesses if p['applied']]
    signed={label:dict(local_exact_m=str(sum((Q(p['local_budget_exact_m']) for p in rows),Q(0))),
                      owner_exact_m=str(sum((Q(p['owner_budget_exact_m']) for p in rows),Q(0))))
            for label,rows in [('all_warm_calls',snow_witnesses),('applied_caps',applied)]}
    return dict(passed=True,scientific_acceptance=False,behavior=behavior,windows=windows,bindings=before,
                total_records=total_rows,selected_records=selected_rows,counts=dict(counts),budget_counts=dict(budgets),
                signed_budget_summaries=signed,classification_counts=dict(Counter(p['classification'] for p in snow_witnesses)),
                affected_hours=[dict(clock=p['clock'],ordinal=p['ordinal'],hour=p['hour']) for p in applied],
                affected_days=sorted(set(tuple(p['clock'][:2]) for p in applied)),
                snow=snow_witnesses,grna=grna_witnesses,evappm=evap_witnesses,winter=winter_witnesses,
                scope='Strict selected-call diagnostic joins and binary32 semantics. Full R05 readback remains mandatory; no physical admission.')
