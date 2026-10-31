"""Original paired summaries and exact hourly-return readback; no native runs."""
from collections import defaultdict
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parent
OBS=ROOT.parent/'buffer-process-observation-r4/observer-o3'
ANALYSIS=OBS.parent/'analysis-o3'
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
inputs={str(p):sha(p) for p in (Path(__file__),ANALYSIS/'declaration.json',ANALYSIS/'results.json',ANALYSIS/'reconciliation.json',OBS/'verification.json',OBS/'execution-declaration.json')}
for t in read(OBS/'execution-declaration.json')['tasks']:
 p=Path(t['folder'])/'observations/buffer-observation.txt';inputs[str(p)]=sha(p)
assert not (ROOT/'summary-declaration.json').exists()
save(ROOT/'summary-declaration.json',dict(scope='Post-observation descriptive summary of all nine declared target pairs; exact REAL hourly return accumulation and ROCHEK-to-IRS addition checks on all traced days. No new selection/native run/parameters.',input_sha256=inputs))
rows=[];checks=[]
labels={'small_paved_dry_legacy':'B1 · Denver paved / dry legacy', 'small_gravel_less_runon':'B2 · Flagstaff gravel / less runon','small_gravel_dry_legacy':'B3 · Denver gravel / dry legacy','passing_same_signature':'B4 · Passing / same signature','underprediction_less_supply':'B5 · Underprediction / lower supply','underprediction_not_less_supply':'B6 · Underprediction / unresolved tiny supply','small_passing_control':'B7 · Small-reference passing control','meaningful_high':'B8 · Meaningful overprediction','underprediction_other_geometry':'B9 · Underprediction / rutted geometry'}
results=read(ANALYSIS/'results.json'); tasks=read(OBS/'execution-declaration.json')['tasks']
for a,t in zip(results,tasks):
 assert (a['stratum'],a['lane'])==(t['stratum'],t['lane'])
 groups=defaultdict(lambda:defaultdict(list))
 for line in (Path(t['folder'])/'observations/buffer-observation.txt').read_text().splitlines():
  f=line.split();groups[(int(f[2]),int(f[3]))][f[0]].append((int(f[4]),list(map(float,f[5:]))))
 for x in a['day_ofe']:
  g=groups[(x['day'],x['ofe'])];hourly=sorted(g['BP_WBH_FLUX']);assert [i for i,v in hourly]==list(range(1,25))
  accumulated=0.
  for i,v in hourly:
   accumulated=f32(accumulated+v[0]);assert accumulated==v[3],(a['stratum'],a['lane'],x['day'],x['ofe'],i)
  rc=g['BP_ROCHEK_OUT'];ir=g['BP_IRS_OUT'];addition=None
  if rc:
   assert len(rc)==len(ir)==1
   expected=f32(rc[0][1][0]+f32(f32(accumulated*x['geometry_native'][1])/ir[0][1][3]))
   addition=dict(before_m=rc[0][1][0],expected_m=expected,observed_m=ir[0][1][0],exact=expected==ir[0][1][0])
   assert addition['exact'],(a['stratum'],a['lane'],x['day'],x['ofe'],addition)
  checks.append(dict(stratum=a['stratum'],lane=a['lane'],day=x['day'],ofe=x['ofe'],all24_accumulations_exact=True,return_depth_local_m=accumulated,rochek_to_irs_addition=addition))
  if x['day']!=a['event']['julian'] or x['ofe']!=3:continue
  d=x['published'];cap=x['ga_capacity'][0];s=x['sediment'];h=x['hourly'];eq=x['equivalent_parameters'];ir=x['irs_result_raw']
  rows.append(dict(label=labels[a['stratum']],stratum=a['stratum'],lane=a['lane'],case_id=a['event']['case_id'],year=a['event']['year'],julian=x['day'],
   roughness_mm=x['roughness_m']*1000,depression_storage_mm=x['depression_storage_m']*1000,
   observed_first_two_layer_weighted_available_storage_mm=cap['observed_storage_m']*1000,
   observed_weighted_min_conductivity_mm_h=cap['observed_weighted_min_k_m_s']*3.6e6,
   local_effective_conductivity_mm_h=x['local_effective_k_m_s']*3.6e6,
   initial_equivalent_length_m=eq[2],final_irs_effective_length_m=ir[3],
   published_surface_in_m3=d['surface_in_m3'],published_surface_out_m3=d['surface_out_m3'],
   published_lateral_in_m3=d['lateral_in_m3'],published_lateral_out_m3=d['lateral_out_m3'],
   native_hourly_return_depth_local_m=accumulated,return_m3_using_emitted_local_area=accumulated*d['local_area_m2'],
   published_sediment_in_kg=d['sediment_in_kg'],published_sediment_out_kg=d['sediment_out_kg'],
   native_grid_net_exchange_kg=s['grid_net_kg_m']*d['width_m'],native_upstream_event_mass_kg=s['upstream_observed_event_mass_kg_m']*d['width_m'],
   native_incoming_class_rates=s['incoming_classes'],native_outgoing_class_rates=s['outgoing_classes'],
   grna_excess_flag=x['grna_generated_excess_flag'],rochek_to_irs_addition=addition,
   post_irs_to_day_end_runoff_unchanged=h['post_irs_to_day_end_effective_depth_change_m']==0.,
   first_two_layer_contributors=cap['contributors'],native_soil_density_branches=x['raw_selected_tags'].get('BP_SOIL_DENSITY',[])))
assert len(rows)==18 and len(checks)==108 and all(sha(p)==h for p,h in inputs.items())
save(ROOT/'paired-target-table.json',rows)
save(ROOT/'hourly-return-reconciliation.json',dict(passed=True,day_ofe_rows=108,exact_REAL_hourly_additions=108*24,
 exact_rochek_to_irs_additions=sum(c['rochek_to_irs_addition'] is not None for c in checks),rows=checks,
 units='Surface-return depths use the local OFE area; incoming per-bin return/lateral depths use upstream OFE area. The emitted-area table and native REAL geometry are retained separately.',
 scope='Exact source-expression readback for these observed additions only; not a full layer water-balance or final hydrograph validation.',summary_declaration_sha256=sha(ROOT/'summary-declaration.json')))
lines=['| Pair | Available storage mm L→M | Weighted minimum K mm/h L→M | Buffer surface water out m³ L→M | Hourly surface return m³ L→M | Buffer sediment out kg L→M |', '| --- | ---: | ---: | ---: | ---: | ---: |']
for i in range(0,len(rows),2):
 l,m=rows[i:i+2];assert l['lane']=='legacy' and m['lane']=='modern'
 keys=['observed_first_two_layer_weighted_available_storage_mm','observed_weighted_min_conductivity_mm_h','published_surface_out_m3','return_m3_using_emitted_local_area','published_sediment_out_kg']
 lines.append('| '+l['label']+' | '+' | '.join(f"{l[k]:.3f} → {m[k]:.3f}" for k in keys)+' |')
(ROOT/'paired-target-table.md').write_text('\n'.join(lines)+'\n')
print('All108 hourly accumulation frames and',sum(c['rochek_to_irs_addition'] is not None for c in checks),'ROCHEK-to-IRS additions reproduce exact REAL values',flush=True)
