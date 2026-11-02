"""Pure response-reader controls and retained ordinary-output compatibility probe."""
from copy import deepcopy
from fractions import Fraction as Q
from pathlib import Path
import json
import shutil
import struct
import sys
import read_snow_cap_response as r


def run(root):
    root=Path(root);root.mkdir(exist_ok=False);checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    def reject(name,call):
        try:call()
        except (ValueError,KeyError) as error:
            (root/(name+'.txt')).write_text(str(error)+'\n');checks.append(name);return
        raise AssertionError('Accepted '+name)
    dates=[(1,365),(2,1),(2,2),(2,3)]
    a={k:0 for k in dates};b=dict(zip(dates,[2,-2,0,1]))
    proof=r.periods(a,b,dates,True)
    check('full_period_signed_cancellation_visible',proof['full_period']['delta_sum_exact']=='1' and proof['full_period']['positive_delta_sum_exact']=='3' and proof['full_period']['negative_delta_sum_exact']=='-2')
    check('annual_not_hidden_by_total',proof['annual']['1']['delta_sum_exact']=='2' and proof['annual']['2']['delta_sum_exact']=='-1')
    check('persistent_sign_reversal_same_episode',proof['full_period']['episodes'][0]['days']==2 and proof['full_period']['episodes'][0]['first_equal_after']==[2,2])
    check('unrecovered_last_episode',proof['full_period']['episodes'][-1]['first_equal_after'] is None)
    check('stock_not_summed','delta_sum_exact' not in r.periods(a,b,dates,False)['full_period'])
    reject('missing_daily_key',lambda:r.periods(a,{dates[0]:0},dates,True))
    reject('duplicate_calendar',lambda:r.periods(a,b,dates+dates[:1],True))
    reject('nonfinite_series',lambda:r.periods(a,dict(b,**{})|{dates[0]:float('nan')},dates,True))
    check('exact_small_difference_retained',r.series({(1,1):Q(1)},{(1,1):Q(1)+Q(1,10**30)},[(1,1)],False)['changed_days']==1)
    schema={'PLANT':{'kind':'r','fields':['lai(ip)','watstr(ip)']},'STATE':{'kind':'i','fields':['crop']}}
    def bits(value,kind):
        if kind=='i':return format(value&((1<<64)-1),'016X')
        value=struct.unpack('>i',struct.pack('>f',value))[0];return format(value&((1<<64)-1),'016X')
    lines=['R05_SCHEMA 1'];seq=0
    for y,d in [(1,1),(1,2)]:
        for o in (1,2,3):
            for tag in sorted(r.DAILY_TAGS):
                group=tag.rsplit('_',1)[-1];kind=schema[group]['kind'];values=[.5,.75] if group=='PLANT' else [1]
                seq+=1;lines.append(' '.join(map(str,[seq,y,d,o,0,tag,kind,len(values),*[bits(v,kind) for v in values]])))
    lines.append(f'R05_END {seq}');trace=root/'synthetic-trace.txt';trace.write_text('\n'.join(lines)+'\n')
    daily,epochs=r.extract(trace,schema,[(1,1),(1,2)],[[1,1,1]])
    check('selective_daily_coverage',len(daily)==24 and not epochs)
    bad=root/'missing-footer.txt';bad.write_text('\n'.join(lines[:-1])+'\n')
    reject('missing_trace_footer',lambda:r.extract(bad,schema,[(1,1),(1,2)],[[1,1,1]]))
    reject('trajectory_wrong_calendar',lambda:r.extract(trace,schema,[(1,1)],[[1,1,1]]))
    duplicate=deepcopy(lines);v=duplicate[2].split();v[5]=duplicate[1].split()[5];v[6:]=duplicate[1].split()[6:];duplicate[2]=' '.join(v)
    bad=root/'duplicate-state.txt';bad.write_text('\n'.join(duplicate)+'\n')
    reject('duplicate_daily_state',lambda:r.extract(bad,schema,[(1,1),(1,2)],[[1,1,1]]))
    p=dict(records={'EVP_CORE':[10.,1.,.1,.05,.01,.5,0.,.1]+[0.]*15},EP_exact_m=str(Q(.005)),pre_snapshot={'PLANT':[.5,1.,.5,.2]},clock=[1,1,1],ordinal=1,demand_seq=10)
    row=lambda tag,values,seq=20,index=0:dict(tag=tag,values=values,seq=seq,index=index,clock=[1,1,1])
    store=row('WB_ET_STORE',[.005,0.,0.,.01,0.,.005,.005],seq=40)
    pre=row('SWU_PRE_WATER',[.01,0.,0.,.005]+[0.]*12)
    plant=row('SWU_PRE_PLANT',[.5,1.,.5,.2])
    result=r.classify_demand(p,[pre,plant,store])
    check('canopy_covered_positive_request',result['withdrawal_classification']=='canopy_covers_positive_request' and result['accepted_root_sum_exact_m']=='0')
    check('potential_separate_from_request',result['diagnostic_potential_basal_exact_m']=='1/200')
    z=deepcopy(p);z['records']['EVP_CORE'][1]=0.;z['EP_exact_m']='0'
    check('positive_potential_zero_availability',r.classify_demand(z,[store])['request_classification']=='positive_potential_zero_availability_limited_request')
    tiny=deepcopy(p);tiny['records']['EVP_CORE'][0]=1e-40;tiny['records']['EVP_CORE'][5]=1e-10;tiny['EP_exact_m']='0'
    check('positive_product_underflow_distinct',r.classify_demand(tiny,[store])['request_classification']=='positive_product_underflow_to_zero')
    reject('missing_final_ET_owner',lambda:r.classify_demand(p,[]))
    reject('duplicate_SWU_epoch',lambda:r.classify_demand(p,[pre,pre,plant,store]))
    accept=row('SWU_ACCEPT',[2.**-30,15.*2.**-34],seq=25,index=1);stock=row('SWU_STOCK',[0.,15.*2.**-34,15.*2.**-34],seq=26,index=1)
    pre2=deepcopy(pre);pre2['values'][:4]=[0.,0.,0.,.0625]
    actual=r.classify_demand(p,[pre2,plant,accept,stock,store])
    check('zeroing_separate_from_accepted_uptake',Q(actual['clamp_debit_exact_m'])==Q(1,2**34) and Q(actual['subtraction_representation_debit_exact_m'])==0)
    rounding_accept=row('SWU_ACCEPT',[r.observation.f32(.1),r.observation.f32(.01)],seq=25,index=1)
    preclamp=r.observation.f32(rounding_accept['values'][0]-rounding_accept['values'][1])
    rounding_stock=row('SWU_STOCK',[preclamp,rounding_accept['values'][1],rounding_accept['values'][1]],seq=26,index=1)
    rounding=r.classify_demand(p,[pre2,plant,rounding_accept,rounding_stock,store])
    check('subtraction_rounding_without_clamp',Q(rounding['subtraction_representation_debit_exact_m'])!=0 and rounding['clamp_debit_exact_m']=='0')
    negative=deepcopy(p);negative['EP_exact_m']='-1/1000'
    check('negative_EP_invalid_not_underflow',r.classify_demand(negative,[store])['request_classification']=='invalid_negative_demand_or_coefficient')
    negative=deepcopy(p);negative['records']['EVP_CORE'][1]=-1.
    check('negative_availability_coefficient_invalid',r.classify_demand(negative,[store])['request_classification']=='invalid_negative_demand_or_coefficient')
    nonfinite=deepcopy(p);nonfinite['records']['EVP_CORE'][0]=float('inf')
    reject('nonfinite_selected_demand',lambda:r.classify_demand(nonfinite,[store]))
    check('ordered_episode_sign_transitions',proof['full_period']['episodes'][0]['sign_transitions']==1)
    stockbad=deepcopy(stock);stockbad['index']=2
    reject('withdrawal_wrong_layer_join',lambda:r.classify_demand(p,[pre2,plant,accept,stockbad,store]))
    # Existing parser compatibility without native execution or re-reading a full trace.
    retained=Path('out/rock-water-development-20261101/R05-water-v3/cases/flagstaff-2711184-outrut-paved-high/baseline')
    decl=r.load(Path('out/rock-water-development-20261101/R05-water-v3/declaration.json'))
    t=next(t for t in decl['tasks'] if t['name']==retained.parent.name and t['lane']=='baseline')
    ordinary=r.ordinary_read(retained,list(map(tuple,t['calendar']['dates'])))
    check('retained_ordinary_parser_compatibility',len(ordinary['wat'])==17532)
    check('retained_sediment_reconciliation',ordinary['sediment_reconciliation']['reconciled'])
    fake=deepcopy(ordinary);clock=next(iter(fake['element']));old=list(fake['element'][clock]);del fake['element'][clock]
    # One missing event remains a presence difference; its exported mass is not discarded.
    small_dates=[clock[:2]]
    pair=r.compare_ordinary(ordinary,fake,small_dates)
    check('sparse_keyed_union_preserves_disappeared_event',any(not x['candidate'] for x in pair['sparse_union_presence'][f'element/{clock[2]}']))
    check('event_mass_uses_emitted_width',Q(pair['sediment'][f'element/{clock[2]}']['full_period']['baseline_sum_exact'])==Q(r.ordinary.number(old[23]))*ordinary['width'])
    cached=r.load(retained/'observation-readback.json')
    metadata={k:v for k,v in cached.items() if k not in ('daily_ledgers','call_counts','first_records')}
    r.cache_contract(metadata,metadata['source_sha256'],metadata['schema_sha256'],t['calendar']['dates'],t['windows'])
    check('retained_validated_cache_identity',True)
    for label,key,value in [('cache_trace_mismatch','source_sha256','bad'),('cache_reader_mismatch','reader_sha256','bad'),('cache_calendar_mismatch','dates',2),('cache_failure','passed',False)]:
        wrong=deepcopy(metadata);wrong[key]=value
        reject(label,lambda wrong=wrong:r.cache_contract(wrong,metadata['source_sha256'],metadata['schema_sha256'],t['calendar']['dates'],t['windows']))
    firstdate=tuple(t['calendar']['dates'][0]);rows=[x for x in cached['daily_ledgers'] if (x['year'],x['day'])==firstdate]
    check('retained_exact_ledger_arithmetic',len(r.ledger_index(rows,[firstdate]))==3)
    reject('duplicate_ledger_owner',lambda:r.ledger_index(rows+rows[:1],[firstdate]))
    reject('missing_ledger_OFE',lambda:r.ledger_index(rows[:2],[firstdate]))
    wrong=deepcopy(rows);wrong[0]['residual_m_exact']='1'
    reject('perturbed_exact_ledger',lambda:r.ledger_index(wrong,[firstdate]))
    wrong=deepcopy(rows);wrong[0]['flux_invocations']=2
    reject('unsupported_multiple_flux_invocations',lambda:r.ledger_index(wrong,[firstdate]))
    wrong=deepcopy(rows);wrong[0]['inputs_m_exact']['unknown_store']='0'
    reject('unknown_ledger_component',lambda:r.ledger_index(wrong,[firstdate]))
    proof=r.compare_ledgers(r.ledger_index(rows,[firstdate]),r.ledger_index(rows,[firstdate]),[firstdate],ordinary['areas'])
    check('identical_ledger_contrast_zero',proof['1']['daily_store_change/canopy']['full_period']['delta_sum_exact']=='0')
    check('local_flux_volume_explicit',proof['1']['outputs_m_exact/surface/volume']['unit']=='m3 over local OFE area')
    context=dict(dates=t['calendar']['dates'],windows=t['windows'],schema_sha256=metadata['schema_sha256'],reader_sha256=metadata['reader_sha256'],helper_hashes=metadata['helper_hashes'],ofes=3)
    r.cache_contract(metadata,metadata['source_sha256'],metadata['schema_sha256'],t['calendar']['dates'],t['windows'],context)
    check('explicit_cached_context_passes',True)
    context['windows']=[]
    reject('wrong_diagnostic_window_cache',lambda:r.cache_contract(metadata,metadata['source_sha256'],metadata['schema_sha256'],t['calendar']['dates'],t['windows'],context))
    specimen=root/'bound-input.txt';specimen.write_text('before')
    bindings=r.ordinary.Bindings();bindings.bind(specimen);specimen.write_text('after')
    reject('input_hash_drift',bindings.check)
    campaign=root/'incomplete-campaign';prior=root/'prior';campaign.mkdir();prior.mkdir()
    for folder in (campaign,prior):r.save(folder/'declaration.json',{});r.save(folder/'receipt.json',dict(passed=False))
    reject('incomplete_campaign_before_output_creation',lambda:r.run(campaign,prior,root/'must-not-exist'))
    check('failed_gate_creates_no_success_root',not (root/'must-not-exist').exists())
    schemafile=root/'synthetic-schema.json';r.save(schemafile,schema)
    cache=root/'extraction-cache';cached_daily,cached_epochs=r.extraction_cache(trace,schemafile,[(1,1),(1,2)],[[1,1,1]],r.ordinary.sha(trace),cache,r.Bindings())
    original_extract=r.extract
    def forbidden_extract(*args,**kwargs):raise AssertionError('Cache reuse reparsed trace')
    r.extract=forbidden_extract
    try:
        replay_daily,replay_epochs=r.extraction_cache(trace,schemafile,[(1,1),(1,2)],[[1,1,1]],r.ordinary.sha(trace),cache,r.Bindings())
        check('bound_extraction_reuse_no_trace_decode',cached_daily==replay_daily and cached_epochs==replay_epochs)
        reject('wrong_extraction_window_context',lambda:r.extraction_cache(trace,schemafile,[(1,1),(1,2)],[[1,1,2]],r.ordinary.sha(trace),cache,r.Bindings()))
    finally:r.extract=original_extract
    corrupt=root/'corrupt-extraction-cache';shutil.copytree(cache,corrupt);(corrupt/'extraction.json').write_text('{}')
    reject('corrupted_extraction_payload_hash',lambda:r.extraction_cache(trace,schemafile,[(1,1),(1,2)],[[1,1,1]],r.ordinary.sha(trace),corrupt,r.Bindings()))
    native_overflow=deepcopy(lines)
    for i,line in enumerate(native_overflow):
        v=line.split()
        if len(v)>8 and v[5].endswith('_STATE'):v[8]=bits(2**31,'i');native_overflow[i]=' '.join(v);break
    bad=root/'integer-overflow-trace.txt';bad.write_text('\n'.join(native_overflow)+'\n')
    reject('native_state_integer_overflow',lambda:r.extract(bad,schema,[(1,1),(1,2)],[[1,1,1]]))
    receipt=dict(passed=True,assertions=len(checks),controls=checks,native_execution=False,
        helper_sha256=r.ordinary.sha(Path(r.__file__)),control_sha256=r.ordinary.sha(Path(__file__)),
        retained_ordinary_inputs={str(p):r.ordinary.sha(p) for p in [retained/'runs/p1.slp',retained/'runs/p1.man',*[retained/f'output/H1.{suffix}.dat' for suffix in ('wat','element','ebe','loss')]]})
    r.save(root/'receipt.json',receipt);return receipt

if __name__=='__main__':print(json.dumps(run(sys.argv[1]),indent=2))
