"""Reconcile unchanged outputs and summarize the bounded paired observer panel."""
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
import argparse,hashlib,json,math,struct
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parent
OBS=ROOT.parent/'observer-o3'
LEDGER=ROOT.parent.parent/'event-supply-retention-r4-v3'
ART=Path('/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts')
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def only(by,tag):
 r=by.get(tag,[]);assert len(r)<=1,(tag,len(r));return r[0]['v'] if r else None

def dependencies():
 paths=[Path(__file__),OBS/'execution-declaration.json',OBS/'verification.json',OBS/'results.json',OBS/'observer-map.json',ROOT.parent/'seeds.json',ART/'buffer-process-observation-r4-o3-independent-full-readback.json']
 for task in read(OBS/'execution-declaration.json')['tasks']:
  folder=Path(task['folder']);cid=task['event']['case_id'];lane=task['lane']
  paths.extend([folder/'record.json',folder/'observations/buffer-observation.txt',folder/'particle-audit.json',folder/'output/H1.wat.dat',folder/'output/H1.element.dat',LEDGER/'cases'/cid/'receipt.json',LEDGER/'cases'/cid/f'{lane}-daily-ofe.parquet'])
 return {str(p.resolve()):sha(p) for p in paths}

def declare():
 assert not (ROOT/'declaration.json').exists()
 assert read(OBS/'verification.json')['passed']
 independent=read(ART/'buffer-process-observation-r4-o3-independent-full-readback.json')
 assert independent['runtime_and_exact_output_readback_passed'] and independent['lanes']==18
 save(ROOT/'declaration.json',dict(scope='All nine predeclared pairs and both traced days, all three OFEs. No new selection/native execution or parameter changes.',dependencies=dependencies(),methods=['Compare native OFE_END sediment directly to emitted ELEMENT kg/m under unchanged F9.3 half-unit bound; missing rows remain unavailable.','Compare hourly-WAT cumulative Q to source-ordered REAL expression reconstructed from end runoff and observed IRS effective length when available; retain exact print quantum, no arbitrary tolerance.','Reconstruct first-two-layer consumed available storage and minimum-conductivity length weighting in double for diagnostic residuals; observed native result remains authoritative.','Report roughness/depression storage, effective lengths, GRNA generated-excess branch, post-IRS versus end runoff, hourly surface-return/lateral allocation, actual sediment rates/current-duration mass versus upstream published event mass and resolved grid net exchange.','Whole-profile differences and selected extremes do not isolate causes; roughness alone and terminal class fractions are not causal tests.']))

def main():
 decl=read(ROOT/'declaration.json');assert decl['dependencies']==dependencies()
 results=[];sed_checks=[];water_checks=[];unavailable=[];reconstructed=[]
 for task in read(OBS/'execution-declaration.json')['tasks']:
  folder=Path(task['folder']);cid=task['event']['case_id'];lane=task['lane'];record=read(folder/'record.json')
  assert record['ordinary_output_parity'] and record['coverage']['passed']
  receipt=read(LEDGER/'cases'/cid/'receipt.json')
  assert receipt['lanes'][lane]['record']['sha256']==task['source_record_sha256']
  table=pq.read_table(LEDGER/'cases'/cid/f'{lane}-daily-ofe.parquet').to_pylist()
  daily={(r['julian'],r['OFE']):r for r in table if r['year']==task['event']['year'] and r['julian'] in (task['event']['julian']-1,task['event']['julian'])}
  assert len(daily)==6
  wat={}
  for line in (folder/'output/H1.wat.dat').read_text().splitlines():
   fields=line.split()
   if fields and fields[0].isdigit() and int(fields[2])==task['event']['year']:
    if int(fields[1]) in (task['event']['julian']-1,task['event']['julian']):wat[(int(fields[1]),int(fields[0]))]=fields
  groups=defaultdict(list);latest_k={};pending=defaultdict(list);capacities=defaultdict(list)
  for number,line in enumerate((folder/'observations/buffer-observation.txt').read_text().splitlines(),1):
   a=line.split();year,day,ip,ix=map(int,a[1:5]);v=list(map(float,a[5:]));tag=a[0]
   assert year==task['event']['year'] and all(math.isfinite(x) for x in v)
   r=dict(tag=tag,index=ix,v=v,line=number);groups[(day,ip)].append(r)
   if tag=='BP_INFPAR':latest_k[ip]=dict(value=v[5],day=day,line=number)
   if tag in ('BP_GA_LOCAL_LAYER','BP_GA_UP_LAYER'):pending[(day,ip)].append(r)
   if tag=='BP_GA_STORAGE':
    rows=pending.pop((day,ip));by_contributor=defaultdict(list)
    for x in rows:by_contributor[x['index']//100].append(x)
    eq=[x for x in groups[(day,ip)] if x['tag']=='BP_EQUIV'];assert len(eq)==1;length=eq[0]['v'][2]
    terms=[]
    for contributor,rr in sorted(by_contributor.items()):
     assert sorted(x['index']%100 for x in rr)==[1,2]
     assert len({x['v'][4] for x in rr})==1
     capacity=math.fsum(max(x['v'][5]-x['v'][0],0.) for x in rr)
     terms.append(dict(ofe=contributor,length_m=rr[0]['v'][4],capacity_m_double=capacity,
         stock_m=math.fsum(x['v'][0] for x in rr),available_upper_m=math.fsum(x['v'][5] for x in rr),
         minimum_conductivity=latest_k.get(contributor),layers=rr))
    stored=math.fsum(x['capacity_m_double']*x['length_m'] for x in terms)/length
    all_k=all(x['minimum_conductivity'] for x in terms)
    weighted_k=math.fsum(x['minimum_conductivity']['value']*x['length_m'] for x in terms)/length if all_k else None
    cap=dict(observed_storage_m=v[0],double_reconstructed_storage_m=stored,storage_residual_m=v[0]-stored,
        observed_weighted_min_k_m_s=v[1],double_reconstructed_min_k_m_s=weighted_k,
        min_k_residual_m_s=None if weighted_k is None else v[1]-weighted_k,effective_length_m=length,
        contributor_length_sum_m=math.fsum(x['length_m'] for x in terms),contributors=terms)
    capacities[(day,ip)].append(cap);reconstructed.append(dict(stratum=task['stratum'],lane=lane,day=day,ofe=ip,**cap))
  assert not pending
  summaries=[]
  for (day,ip),ld in sorted(daily.items()):
   by=defaultdict(list)
   for r in groups[(day,ip)]:by[r['tag']].append(r)
   end=only(by,'BP_OFE_END');owner=only(by,'BP_OWNER');geo=only(by,'BP_GEOMETRY');assert end and owner and geo
   native_mass=end[2]
   if ld['element_present']:
    difference=D.from_float(native_mass)-D(str(ld['sediment_out_kg_m']))
    assert abs(difference)<=D('.0005'),(task['stratum'],lane,day,ip,'ELEMENT',difference)
    sed_checks.append(dict(stratum=task['stratum'],lane=lane,day=day,ofe=ip,difference_kg_m=str(difference),bound_kg_m='.0005'))
   else:unavailable.append(dict(stratum=task['stratum'],lane=lane,day=day,ofe=ip,field='ELEMENT absent',native_observed_kg_m=native_mass))
   irs=only(by,'BP_IRS_OUT');qtoken=wat[(day,ip)][5];q=D(qtoken);bound=D(5).scaleb(q.as_tuple().exponent-1)
   qcalc=None
   if irs is not None:qcalc=f32(f32(f32(end[1]*1000.)*irs[3])/geo[2])
   elif end[1]==0:qcalc=0.
   if qcalc is not None:
    difference=D.from_float(qcalc)-q
    check=dict(stratum=task['stratum'],lane=lane,day=day,ofe=ip,difference_mm=str(difference),printed_bound_mm=str(bound),matches_printing_interval=abs(difference)<=bound)
    water_checks.append(check)
    assert check['matches_printing_interval'],check
   else:unavailable.append(dict(stratum=task['stratum'],lane=lane,day=day,ofe=ip,field='No current observed effective length for WAT expression'))
   local=only(by,'BP_IRS_LOCAL');eq=only(by,'BP_EQUIV');ga=only(by,'BP_GA_OUT');rin=only(by,'BP_ROUTE_IN_SCALE');rout=only(by,'BP_SLOSS_OUT_SCALE')
   flow=only(by,'BP_SLOSS_OUT_FLOW');sin=None
   if rin:
    scale=rin[4]*rin[1]*rin[2]/rin[3]
    upstream=only(defaultdict(list,((tag,[r for r in groups[(day,ip-1)] if r['tag']==tag]) for tag in ['BP_OFE_END'])),'BP_OFE_END') if ip>1 else None
    grid=sorted(by['BP_GRID'],key=lambda r:r['index']);assert [r['index'] for r in grid]==list(range(2,102))
    sin=dict(incoming_rate_kg_m_s=rin[5],receiving_duration_s=rin[4],incoming_normalized=rin[0],
       incoming_mass_using_receiving_duration_kg_m=rin[0]*scale,upstream_observed_event_mass_kg_m=None if upstream is None else upstream[2],
       native_grid_start_kg_m=grid[0]['v'][2],native_grid_end_kg_m=grid[-1]['v'][3],
       grid_positive_net_kg_m=math.fsum(max(r['v'][3]-r['v'][2],0.) for r in grid),
       grid_negative_net_kg_m=math.fsum(min(r['v'][3]-r['v'][2],0.) for r in grid),
       grid_net_kg_m=grid[-1]['v'][3]-grid[0]['v'][2],
       incoming_classes=[dict(index=r['index'],fraction=r['v'][0],rate_kg_m_s=r['v'][0]*r['v'][1]) for r in by['BP_CLASS_IN']],
       class_input_unavailable=bool(by['BP_CLASS_IN_UNAVAILABLE']),
       outgoing_classes=[dict(index=r['index'],fraction=r['v'][0],rate_kg_m_s=r['v'][0]*rout[5]) for r in by['BP_SLOSS_OUT_CLASS']])
   # Hourly return/lateral values are phase-specific local or upstream-area depths.
   local_area=geo[0]*geo[1];up_geo=only(defaultdict(list,((tag,[r for r in groups[(day,ip-1)] if r['tag']==tag]) for tag in ['BP_GEOMETRY'])),'BP_GEOMETRY') if ip>1 else None
   upstream_area=up_geo[0]*up_geo[1] if up_geo else 0.
   h=dict(local_area_native_m2=local_area,upstream_area_native_m2=upstream_area,
       incoming_hourly_surface_return_m3=math.fsum(r['v'][0] for r in by['BP_WBH_SOURCE'])*upstream_area,
       incoming_hourly_lateral_m3=math.fsum(r['v'][1] for r in by['BP_WBH_SOURCE'])*upstream_area,
       outgoing_hourly_surface_return_m3=math.fsum(r['v'][0] for r in by['BP_WBH_FLUX'])*local_area,
       outgoing_hourly_lateral_m3=math.fsum(r['v'][1] for r in by['BP_WBH_FLUX'])*local_area,
       allocated_fin_m3=math.fsum(r['v'][0] for r in by['BP_WBH_ALLOC'])*local_area,
       post_irs_to_day_end_effective_depth_change_m=None if irs is None else end[1]-irs[0])
   summaries.append(dict(day=day,ofe=ip,role=ld['role'],published=ld,roughness_m=None if local is None else local[0],
      depression_storage_m=None if local is None else local[2],local_effective_k_m_s=None if local is None else local[3],
      local_suction_m=None if local is None else local[4],equivalent_parameters=eq,
      ga_capacity=capacities[(day,ip)],grna_generated_excess_flag=None if ga is None else ga[5],grna_result_raw=ga,
      irs_result_raw=irs,owner_raw=owner,end_raw=end,geometry_native=geo,sediment=sin,hourly=h,
      raw_selected_tags={tag:by[tag] for tag in ('BP_ROCHEK_ENTER','BP_ROCHEK_OUT','BP_RUNON_CAP','BP_SOIL_DENSITY','BP_SOIL_ROUGH','BP_SOIL_DECAY','BP_SOIL_DECAY_OUT','BP_STRESS','BP_PARAM','BP_ERODIBILITY','BP_GA_FORCING') if by[tag]}))
  # Serialize dates explicitly without changing numerical fields.
  for x in summaries:x['published']['date']=x['published']['date'].isoformat()
  results.append(dict(stratum=task['stratum'],lane=lane,event=task['event'],trace_sha256=sha(folder/'observations/buffer-observation.txt'),day_ofe=summaries))
 assert len(results)==18 and len(sed_checks)+sum(x['field']=='ELEMENT absent' for x in unavailable)==108
 assert decl['dependencies']==dependencies()
 save(ROOT/'results.json',results)
 save(ROOT/'reconciliation.json',dict(passed=True,lanes=18,day_ofe_rows=108,element_checks=len(sed_checks),water_checks=len(water_checks),sediment=sed_checks,water=water_checks,unavailable=unavailable,
     reconstructed_grna_calls=len(reconstructed),max_storage_double_reconstruction_residual_m=max(abs(x['storage_residual_m']) for x in reconstructed),
     max_min_k_double_reconstruction_residual_m_s=max(abs(x['min_k_residual_m_s']) for x in reconstructed if x['min_k_residual_m_s'] is not None),
     statement='Printing checks are unchanged. Double reconstruction residuals are descriptive, not new tolerances or model acceptance.',declaration_sha256=sha(ROOT/'declaration.json'),results_sha256=sha(ROOT/'results.json')))
 print('Reconciled',len(sed_checks),'ELEMENT and',len(water_checks),'WAT represented rows;18lanes/108day-OFE',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('declare','analyze'));a=p.parse_args()
 {'declare':declare,'analyze':main}[a.action]()
