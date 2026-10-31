"""Deterministic observational seed declaration; no model execution or tuning."""
from pathlib import Path
import json
import hashlib
import duckdb

ROOT=Path(__file__).resolve().parent
P=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
LEDGER=P/'event-supply-retention-r4-v3'
PACKET=Path('/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/event-supply-ledger-r4')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
quote=lambda p:"'"+str(p).replace("'","''")+"'"
assert not (ROOT/'seeds.json').exists()
rows=json.loads((LEDGER/'case-summary.json').read_text());by={r['case_id']:r for r in rows}
tasks={r['case_id']:r for r in json.loads((LEDGER/'declaration.json').read_text())['tasks']}
con=duckdb.connect();con.execute('SET threads=2')
con.execute('CREATE VIEW t AS SELECT * FROM read_parquet('+quote(LEDGER/'cases/*/paired-terminal.parquet')+')')
zero=[r['case_id'] for r in rows if r['surface']=='paved' and all(r['lanes'][lane]['ofes'][0]['sediment_out_kg']==0 for lane in ('legacy','modern'))];assert len(zero)==37
pattern=[r['case_id'] for r in rows if r['group']=='meaningful_pass' and r['lanes']['modern']['ofes'][1]['sediment_out_kg']<r['lanes']['legacy']['ofes'][1]['sediment_out_kg'] and r['lanes']['modern']['ofes'][2]['sediment_out_kg']>r['lanes']['legacy']['ofes'][2]['sediment_out_kg']];assert len(pattern)==13
list_sql=lambda xs:'('+','.join(quote(x) for x in xs)+')'
robust="legacy_sediment_in_kg-modern_sediment_in_kg>.001*width_m AND modern_sediment_out_kg-legacy_sediment_out_kg>.001*width_m"
positive="modern_sediment_out_kg-legacy_sediment_out_kg>.001*width_m"
negative="legacy_sediment_out_kg-modern_sediment_out_kg>.001*width_m"
rules=[
 ('small_paved_dry_legacy',"original_group='small_exceedance' AND case_id IN "+list_sql(zero)+" AND legacy_surface_out_m3=0 AND "+robust,'DESC','Actual zero-road paved contrast with legacy dry buffer outlet.'),
 ('small_gravel_less_runon',"original_group='small_exceedance' AND surface='gravel' AND modern_surface_in_m3<legacy_surface_in_m3 AND "+robust,'DESC','Larger generated outlet export despite less incoming water and sediment.'),
 ('small_gravel_dry_legacy',"original_group='small_exceedance' AND surface='gravel' AND legacy_surface_out_m3=0 AND "+robust,'DESC','Gravel counterpart to the absent legacy outlet-flow support.'),
 ('passing_same_signature',"original_group='meaningful_pass' AND case_id IN "+list_sql(pattern)+" AND "+positive,'DESC','Passing control with the same annual lower-fill/higher-outlet signature.'),
 ('underprediction_less_supply',"original_group='meaningful_low' AND legacy_sediment_in_kg-modern_sediment_in_kg>.001*width_m AND "+negative,'ASC','Opposite direction with lower incoming generated sediment supply.'),
 ('underprediction_not_less_supply',"original_group='meaningful_low' AND modern_sediment_in_kg>=legacy_sediment_in_kg AND "+negative,'ASC','Opposite direction without lower incoming generated sediment on the selected day.'),
 ('small_passing_control',"original_group='small_pass' AND case_id IN "+list_sql(zero)+" AND "+positive,'DESC','Passing small-reference zero-road control.'),
 ('meaningful_high',"original_group='meaningful_high' AND "+positive,'DESC','Meaningful overprediction contrast beyond the small-reference group.'),
 ('underprediction_other_geometry',"original_group='meaningful_low' AND design!='outunrut' AND "+negative,'ASC','Largest opposite-direction discrepancy outside outsloped unrutted geometry; protects transfer interpretation.'),
]
selected=[];seen=set()
fields=['case_id','original_group','year','julian','width_m','local_area_m2','cumulative_area_m2','delta_reported_sediment_out_kg']
for lane in ('legacy','modern'):
 for field in ('sediment_in_kg','sediment_out_kg','surface_in_m3','surface_out_m3','lateral_in_m3','lateral_out_m3','effective_duration_h','element_peak_runoff_mm_h','soil_stock_m3','porosity_capacity_mm','profile_depth_mm','keff_mm_h','critical_shear_pa'):
  fields.append(lane+'_'+field)
for name,condition,direction,why in rules:
 eligible="legacy_element_present AND modern_element_present AND "+condition
 if seen:eligible+=' AND case_id NOT IN '+list_sql(sorted(seen))
 sql='SELECT '+','.join(fields)+' FROM t WHERE '+eligible+' ORDER BY delta_reported_sediment_out_kg '+direction+',case_id,year,julian LIMIT 1'
 candidate=con.execute(sql).fetch_arrow_table().to_pylist()
 if not candidate:
  selected.append(dict(stratum=name,status='no eligible distinct case; no silent replacement',selection_sql=sql,rationale=why));continue
 e=candidate[0];ident=e['case_id'];seen.add(ident);task=tasks[ident]
 for lane in ('legacy','modern'):
  prev=con.execute('SELECT year,julian,'+lane+'_soil_stock_m3,'+lane+'_porosity_capacity_mm,'+lane+'_profile_depth_mm FROM t WHERE case_id=? AND (year<? OR (year=? AND julian<?)) ORDER BY year DESC,julian DESC LIMIT 1',[ident,e['year'],e['year'],e['julian']]).fetchone()
  e[lane+'_previous_day']=dict(zip(('year','julian','soil_stock_m3','porosity_capacity_mm','profile_depth_mm'),prev)) if prev else None
 selected.append(dict(stratum=name,status='selected',selection_sql=sql,rationale=why,event=e,native_year_index=e['year']-task['first_year']+1,calendar_first_year=task['first_year'],calendar_last_year=task['last_year'],case_summary=by[ident],input_records=task['records'],paired_terminal_sha256=sha(LEDGER/'cases'/ident/'paired-terminal.parquet')))
result=dict(scope='Predeclared source-observation seeds from completed ledger; no native/source observation executed.',script_sha256=sha(Path(__file__)),ledger_manifest_sha256=sha(PACKET/'manifest.json'),ledger_case_summary_sha256=sha(LEDGER/'case-summary.json'),ledger_declaration_sha256=sha(LEDGER/'declaration.json'),rules='First eligible distinct case per ordered stratum; largest signed positive or most negative daily outlet difference as specified, then case id/year/day. Both ELEMENT observations required, positive/negative export difference beyond unchanged combined native print interval. No outcome-based replacement after tracing.',selected_pairs=len(seen),planned_full_period_native_runs=2*len(seen),seeds=selected)
(ROOT/'seeds.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
for s in selected:
 print(s['stratum'],s['status'],s.get('event',{}).get('case_id'),s.get('event',{}).get('year'),s.get('event',{}).get('julian'),s.get('event',{}).get('delta_reported_sediment_out_kg'))
