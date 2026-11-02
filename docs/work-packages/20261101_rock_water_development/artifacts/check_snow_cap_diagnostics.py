"""Original runtime-contract controls; retained synthetic traces, no native run."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import struct
import sys
import read_snow_cap_diagnostics as r


def words(value,kind):
    if kind=='i':bits=int(value)&((1<<64)-1)
    elif kind=='r':
        bits=int.from_bytes(struct.pack('>f',r.f(value)),'big')
        if bits>>31:bits|=0xffffffff00000000
    else:bits=int.from_bytes(struct.pack('>d',value),'big')
    return f'{bits:016X}'


def write_trace(path,rows,schema):
    lines=['R05_SCHEMA 1']
    for n,(tag,values,index) in enumerate(rows,1):
        base=tag
        for suffix in ('LAYER','PLANT','WATER','STATE'):
            if tag.endswith('_'+suffix):base=suffix;break
        contract=schema[base];kind=contract['kind'];assert len(values)==len(contract['fields'])
        lines.append(' '.join(map(str,[n,1,1,1,index,tag,kind,len(values)]+[words(v,kind) for v in values])))
    lines.append(f'R05_END {len(rows)}');path.write_text('\n'.join(lines)+'\n')


def snow_group(depth=.01,density=350.,behavior='cap_candidate',raw=None,rain=0.):
    depth,density,rain=map(r.f,(depth,density,rain))
    current=r.divide(r.f(density*depth),depth)
    entry=[depth]*3+[density]*3+[rain,0.]
    group={'SNOW_ENTRY':entry,'SNOW_BRANCH_INPUT':[1.,1.,0.,0.,100.,1000.],
           'SNOW_WARM_PACK':[depth,current,depth,density],
           'SNOW_CAP_PRE':[depth,current,depth,density,1000.,0.,0.,0.]}
    if raw is None:raw=[1.,0.,0.,0.,r.f(.0254),depth,density,1.,1.,1.]
    group['MELT_RAW']=list(raw)
    water,full=r.cap(raw[4],depth,density);kind,owned=r.identity(group['SNOW_CAP_PRE'])
    applied=behavior=='cap_candidate' and full and owned and water>0
    group['MELT_CAP_FLAG']=[int(full)];group['MELT_RETURN']=[water,depth,density]
    group['SNOW_CAP_FLAGS']=[int(full),int(owned),int(applied),kind]
    result=r.transition(depth,current,water,1000.,rain,density,applied)
    group['SNOW_DEBIT']=[depth,result['debit'],water,result['debit_density']]
    group['SNOW_RETURN']=[result['depth']]*3+[result['debit_density'],result['density'],result['density'],result['rain'],0.,result['release'],result['release']]
    return group


def fixture(behavior='cap_candidate'):
    rows=[]
    def emit(tag,values,index=0):rows.append((tag,list(values),index))
    def snapshot(stage,water,plant=None):
        emit(stage+'_LAYER',[0.]*12,1)
        emit(stage+'_PLANT',plant if plant is not None else [0.]*15)
        emit(stage+'_WATER',water)
        emit(stage+'_STATE',[1,1,1,2,0,0,0,0,0,0,0])
    group=snow_group(behavior=behavior);depth=group['SNOW_ENTRY'][0];density=group['SNOW_ENTRY'][5]
    water=[0.]*16;water[10]=water[11]=depth;water[12]=density
    snapshot('WINTER_PRE',water)
    total=0.
    for hour in range(1,25):
        if depth>0:
            group=snow_group(depth,density,behavior)
        else:
            group={'SNOW_ENTRY':[0.]*8,'SNOW_BRANCH_INPUT':[1.,1.,0.,0.,100.,1000.],'SNOW_RETURN':[0.]*10}
        emit('WINTER_SNOW_PRE',[depth,depth,density,0.,0.,0.],hour)
        for tag,values in group.items():emit(tag,values,hour)
        ret=group['SNOW_RETURN'];emit('WINTER_SNOW_POST',[ret[1],ret[2],ret[5],ret[8],ret[6],ret[7],ret[0],ret[3],ret[4]],hour)
        emit('WINTER_MELT_HOUR',[ret[8],ret[6],ret[7],ret[1],ret[2],ret[5]],hour)
        depth,density=ret[0],ret[5];total=r.f(total+ret[8])
    emit('WINTER_RETURN',[0.,total,depth,depth,density,total])
    water[9]=total;water[10]=water[11]=depth;water[12]=density;snapshot('WINTER_POST',water)
    emit('IR_GRNA_PRE',[0.,1.,2.,0.])
    emit('GRNA_PRE_CLAMP',[r.f(.00005),r.f(.00005),2.])
    emit('GRNA_EXIT_FLAGS',[1,1,0,1]);emit('GRNA_EXIT_RESULT',[0.,2.]);emit('IR_GRNA_POST',[0.,1.,2.,0.])
    water=[0.]*16;water[0]=r.f(.0002);water[1]=r.f(.001)
    plant=[0.]*15;plant[0]=2.;plant[1]=3.;snapshot('EVAPPM_PRE',water,plant)
    core=[0.]*23;core[0]=5.;core[1]=.5;core[5]=.75
    soil=[0.]*7;soil[3]=.5;soil[4]=.25;soil[6]=r.f(r.f(5.*.25)*r.f(.001))
    bp=r.f(soil[6]-water[1]);combined=.125;es=r.f(r.divide(r.f(combined*bp),.25)+water[1])
    emit('EVP_RESIDUE_BRANCH',[bp,.5,1.2,combined,es]);emit('EVP_CORE',core)
    emit('EVP_CORE_OWNER',[1,2,1]);emit('EVP_SOIL_DEMAND',soil)
    ep=r.f(r.f(r.f(5.*.5)*.75)*r.f(.001))
    emit('EVP_DEMAND',[ep,es,0.,water[1],water[0],0.,2.,3.,.5]);snapshot('EVAPPM_POST',water,plant)
    return rows


def run(root,schema_path):
    root=Path(root);root.mkdir(exist_ok=False);schema=json.loads(Path(schema_path).read_text())
    shutil.copy2(schema_path,root/'schema.json');schema_path=root/'schema.json'
    names=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        names.append(name)
    def audit(name,rows,behavior='cap_candidate'):
        p=root/(name+'.txt');write_trace(p,rows,schema)
        return r.audit(p,schema_path,[[1,1,1]],behavior)
    base=fixture();proof=audit('valid',base);(root/'valid-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    check('full_mandatory_family_coverage',proof['counts']['snow_calls']==24 and proof['counts']['evappm_calls']==proof['counts']['grna_calls']==1)
    check('candidate_direct_exhaustion',proof['counts']['applied_caps']>=1)
    check('nonzero_budgets_not_silently_zero',any(r.Q(s['owner_budget_exact_m'])!=0 for s in proof['snow']))
    observer=audit('observer',fixture('observer'),'observer')
    check('observer_never_applies_candidate',observer['counts']['applied_caps']==0)
    check('scientific_acceptance_false',not proof['scientific_acceptance'])
    def reject(name,rows,behavior='cap_candidate'):
        try:audit(name,rows,behavior)
        except ValueError as exc:
            (root/(name+'-rejection.json')).write_text(json.dumps(dict(error=str(exc)))+'\n');names.append(name)
        else:raise AssertionError('Expected rejection '+name)
    def drop(tags):return [x for x in base if x[0] not in tags]
    for tag in ['SNOW_BRANCH_INPUT','SNOW_WARM_PACK','SNOW_CAP_PRE','MELT_CAP_FLAG','SNOW_CAP_FLAGS','SNOW_DEBIT',
                'GRNA_EXIT_FLAGS','GRNA_EXIT_RESULT','EVP_CORE','EVP_CORE_OWNER','EVP_SOIL_DEMAND','EVP_RESIDUE_BRANCH']:
        reject('missing_'+tag,drop({tag}))
    reject('omitted_whole_MELT_family',drop({'SNOW_CAP_PRE','MELT_RAW','MELT_CAP_FLAG','MELT_RETURN','SNOW_CAP_FLAGS','SNOW_DEBIT'}))
    reject('omitted_whole_GRNA_family',drop({'GRNA_PRE_CLAMP','GRNA_EXIT_FLAGS','GRNA_EXIT_RESULT'}))
    reject('omitted_whole_EVP_extra_family',drop({'EVP_CORE','EVP_CORE_OWNER','EVP_SOIL_DEMAND','EVP_RESIDUE_BRANCH'}))
    for tag in ['MELT_CAP_FLAG','GRNA_EXIT_FLAGS','EVP_CORE']:
        rows=deepcopy(base);at=next(i for i,x in enumerate(rows) if x[0]==tag);rows.insert(at,deepcopy(rows[at]));reject('duplicate_'+tag,rows)
    def alter(tag,index,value,name):
        rows=deepcopy(base);at=next(i for i,x in enumerate(rows) if x[0]==tag);rows[at][1][index]=value;reject(name,rows)
    alter('MELT_CAP_FLAG',0,0,'cap_flag_without_predicate')
    alter('SNOW_CAP_FLAGS',2,0,'candidate_application_missing')
    alter('SNOW_CAP_FLAGS',3,0,'wrong_pack_identity')
    alter('MELT_RETURN',1,.02,'wrong_cap_owner')
    alter('SNOW_DEBIT',1,0.,'changed_depth_debit')
    alter('SNOW_RETURN',8,0.,'changed_released_water')
    alter('SNOW_RETURN',0,.001,'changed_retained_depth')
    alter('GRNA_EXIT_FLAGS',0,2,'invalid_GRNA_branch')
    alter('GRNA_EXIT_FLAGS',3,0,'missing_minimum_clamp_flag')
    alter('EVP_CORE_OWNER',0,2,'wrong_crop_owner')
    alter('EVP_DEMAND',0,.01,'changed_EP_construct')
    alter('EVP_RESIDUE_BRANCH',3,.5,'changed_residue_coefficient')
    alter('SNOW_BRANCH_INPUT',0,-10.,'warm_family_on_cold_branch')
    reject('behavior_not_inferred',base,'observer')
    rows=deepcopy(base);at=next(i for i,x in enumerate(rows) if x[0]=='MELT_RETURN');tag,v,_=rows[at];rows[at]=(tag,v,2);reject('cross_hour_join',rows)
    for left,right in [('MELT_CAP_FLAG','MELT_RETURN'),('GRNA_EXIT_FLAGS','GRNA_EXIT_RESULT'),('EVP_CORE','EVP_CORE_OWNER')]:
        rows=deepcopy(base);a=next(i for i,x in enumerate(rows) if x[0]==left);b=next(i for i,x in enumerate(rows) if x[0]==right);rows[a],rows[b]=rows[b],rows[a];reject('reordered_'+left,rows)
    check('identity_kind2_reconstruction',r.identity([r.f(.0017002057284116745),r.f(r.f(350.*r.f(.0017002057284116745))/r.f(.0017002057284116745)),r.f(.0017002057284116745),350.,1000.,0.,0.,0.])[0]==2)
    require_group=snow_group();require_group['SNOW_CAP_PRE'][5]=r.f(1e-8)
    # A mismatched new pack cannot reuse the owner lineage predicate.
    check('new_pack_rejects_lineage',not r.identity([.125,.5,.125,1.,1000.,.01,0.,0.])[1])
    tiny=r.f(2**-80);water=r.f(tiny*.35*.25);returned,full=r.cap(water,tiny,350.)
    check('legitimate_tiny_partial',not full and returned==water)
    returned,full=r.cap(r.f(2**-149),r.f(2**-149),350.)
    check('represented_zero_cap_not_exhaustion',full and returned==0.)
    for flags,label in [([0,0,0,0],'no_positive_cumulative'),([0,1,1,0],'positive_without_final_result')]:
        g=deepcopy(proof['grna'][0]['records']);del g['GRNA_PRE_CLAMP'];g['GRNA_EXIT_FLAGS']=flags
        g['GRNA_EXIT_RESULT']=[0.,0.];g['IR_GRNA_POST']=[0.,1.,0.,0.]
        check('valid_GRNA_'+label,r.grna_proof(g)['flags']==flags)
    g=deepcopy(proof['grna'][0]['records']);threshold=r.f(1e-4)
    g['GRNA_PRE_CLAMP']=[threshold,threshold,2.];g['GRNA_EXIT_FLAGS']=[1,1,0,0]
    g['GRNA_EXIT_RESULT']=[threshold,2.];g['IR_GRNA_POST']=[threshold,1.,2.,0.]
    check('GRNA_exact_threshold_retained',r.grna_proof(g)['classification']=='preclamp_retained')
    g=deepcopy(proof['evappm'][0]['records']);pre=deepcopy(proof['evappm'][0]['pre_snapshot'])
    del g['EVP_RESIDUE_BRANCH'];pre['WATER'][1]=r.f(.01);g['EVP_DEMAND'][3]=r.f(.01);g['EVP_DEMAND'][1]=g['EVP_SOIL_DEMAND'][6]
    check('valid_EVP_no_residue_branch',not r.evap_proof(g,pre)['residue_branch'])
    for rain in (.001,.01):
        raw=[r.f(.01),0.,0.,0.,r.f(r.f(.0254)*r.f(.01)),r.f(.01),100.,1.,1.,1.]
        group=snow_group(.01,100.,raw=raw,rain=rain);answer=r.snow_proof(group,'cap_candidate')
        check('partial_snow_rain_retention_'+str(rain),not answer['applied'] and answer['result']['depth']>0)
    tiny=r.f(2**-149);thermal=r.f(2**-140)
    raw=[thermal,0.,0.,0.,r.f(r.f(.0254)*thermal),tiny,350.,1.,1.,1.]
    answer=r.snow_proof(snow_group(tiny,350.,raw=raw),'cap_candidate')
    check('zero_cap_full_group_does_not_apply',answer['full_cap'] and not answer['applied'] and answer['result']['depth']==tiny)
    group={'SNOW_ENTRY':[.125,.125,.125,350.,350.,350.,0.,0.],
        'SNOW_BRANCH_INPUT':[1.,1.,0.,-.25,100.,1000.],
        'SNOW_WARM_PACK':[-.125,350.,.125,350.],
        'SNOW_DEBIT':[-.125,0.,0.,350.]}
    result=r.transition(-.125,350.,0.,1000.,0.,350.,False)
    group['SNOW_RETURN']=[0.,0.,0.,350.,0.,0.,0.,0.,result['release'],result['release']]
    check('nonpositive_current_pack_has_debit_without_MELT',not r.snow_proof(group,'cap_candidate')['full_cap'])
    historical=[];historical_bindings=[]
    rawroot=Path('out/rock-water-development-20261101')
    for climate,days in [('flagstaff',[13]),('birmingham',[7,9])]:
        for lane in ('baseline','candidate'):
            path=rawroot/('R05-'+climate+'-mechanism-v1')/(lane+'-window.jsonl')
            oldbinding=r.bind(path);needed={}
            for line in path.open():
                row=json.loads(line)
                if row['ofe']==2 and row['day'] in days and row['tag'] in ('MELT_RAW','MELT_RETURN','SNOW_RETURN'):
                    needed[(row['day'],row['index'],row['tag'])]=row
            for day in days:
                hour=17 if climate=='birmingham' and day==7 else 18
                source=needed[(day,hour,'MELT_RAW')];ret=needed[(day,hour,'MELT_RETURN')];snow=needed[(day,hour,'SNOW_RETURN')]
                group=snow_group(source['values'][5],source['values'][6],'observer',source['values'])
                r.equal(group['MELT_RETURN'],ret['values'],'Historical cap result')
                r.equal(group['SNOW_RETURN'],snow['values'],'Historical release/retained state')
                oldproof=r.snow_proof(group,'observer')
                newgroup=snow_group(source['values'][5],source['values'][6],'cap_candidate',source['values'])
                newproof=r.snow_proof(newgroup,'cap_candidate')
                check('actual_'+climate+'_'+lane+'_'+str(day),newproof['applied'] and not oldproof['applied'])
                historical.append(dict(case=climate,lane=lane,clock=[source['year'],day,2,hour],
                    actual_sequences=[source['seq'],ret['seq'],snow['seq']],observer=oldproof,candidate_arithmetic=newproof,
                    scope='Actual historical cap/return operands. New flags/branch inputs reconstructed for pure control; no compiled candidate observation.'))
            assert oldbinding==r.bind(path);historical_bindings.append(oldbinding)
    for design in ('inbare','outunrut'):
        for lane in ('baseline','candidate'):
            path=rawroot/('R05-denver-'+design+'-mechanism-v1')/(lane+'-window.jsonl');oldbinding=r.bind(path)
            selected=[]
            for line in path.open():
                row=json.loads(line)
                if row['day']==132 and row['ofe']==3 and row['tag'] in ('EVAPPM_PRE_PLANT','EVAPPM_PRE_WATER','EVAPPM_PRE_STATE','EVP_DEMAND','EVAPPM_POST_STATE'):
                    selected.append(row)
            tags=[row['tag'] for row in selected]
            check('actual_Denver_demand_order_'+design+'_'+lane,tags==['EVAPPM_PRE_PLANT','EVAPPM_PRE_WATER','EVAPPM_PRE_STATE','EVP_DEMAND','EVAPPM_POST_STATE'])
            demand=selected[3]['values'];r.equal(demand[6:8],selected[0]['values'][:2],'Historical Denver pre-demand canopy epoch')
            r.equal(demand[3:6],[selected[1]['values'][1],selected[1]['values'][0],selected[1]['values'][2]],'Historical Denver carry epoch')
            historical.append(dict(case='denver-'+design,lane=lane,sequences=[v['seq'] for v in selected],
                demand=demand,scope='Historical demand ordering/carry/plant epochs only; new CORE fields await actual observation.'))
            assert oldbinding==r.bind(path);historical_bindings.append(oldbinding)
    (root/'historical-controls.json').write_text(json.dumps(historical,indent=2)+'\n')
    report=dict(assertions=len(names),controls=names,scientific_acceptance=False,native_executions=0,
                reader=r.bind(Path(r.__file__)),schema=r.bind(schema_path),historical_bindings=historical_bindings)
    (root/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Provide fresh output directory and schema path')
    print(json.dumps(run(sys.argv[1],sys.argv[2]),indent=2))
