"""Post hoc hydrologic cross-tab; separate from frozen ledger and summary."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import statistics
import duckdb

ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
q=lambda s:"'"+str(s).replace("'","''")+"'"
rows=json.loads((ROOT/'case-summary.json').read_text());by={r['case_id']:r for r in rows}
con=duckdb.connect();con.execute('SET threads=4')
con.execute('CREATE VIEW t AS SELECT * FROM read_parquet('+q(ROOT/'cases/*/paired-terminal.parquet')+')')
con.execute('''CREATE VIEW antecedent AS SELECT *,
 lag(legacy_soil_stock_m3) OVER(PARTITION BY case_id ORDER BY year,julian) AS legacy_previous_soil_stock_m3,
 lag(modern_soil_stock_m3) OVER(PARTITION BY case_id ORDER BY year,julian) AS modern_previous_soil_stock_m3,
 lag(legacy_porosity_capacity_mm*local_area_m2/1000) OVER(PARTITION BY case_id ORDER BY year,julian) AS legacy_previous_porosity_store_m3,
 lag(modern_porosity_capacity_mm*local_area_m2/1000) OVER(PARTITION BY case_id ORDER BY year,julian) AS modern_previous_porosity_store_m3
 FROM t''')
condition="original_group='small_exceedance' AND legacy_element_present AND modern_element_present AND legacy_sediment_in_kg-modern_sediment_in_kg>.001*width_m AND modern_sediment_out_kg-legacy_sediment_out_kg>.001*width_m"
fields=['case_id','climate','soil','surface','traffic','year','julian','width_m']
metrics=['sediment_in_kg','sediment_out_kg','surface_in_m3','surface_out_m3','lateral_in_m3','lateral_out_m3','rain_melt_m3','deep_percolation_m3','effective_duration_h','element_peak_runoff_mm_h','keff_mm_h','soil_stock_m3','previous_soil_stock_m3','previous_porosity_store_m3','profile_depth_mm','ki_si_kg_s_m4','kr_si_s_m','critical_shear_pa']
fields += [lane+'_'+field for lane in ('legacy','modern') for field in metrics]
events=con.execute('SELECT '+','.join(fields)+' FROM antecedent WHERE '+condition+' ORDER BY case_id,year,julian').fetch_arrow_table().to_pylist();assert len(events)==115

def summary(xs):
 vals=[x for x in xs if x is not None];assert all(math.isfinite(x) for x in vals)
 return dict(n=len(vals),undefined=len(xs)-len(vals),median=statistics.median(vals) if vals else None,min=min(vals) if vals else None,max=max(vals) if vals else None)

def paired(field):
 pairs=[(r['legacy_'+field],r['modern_'+field]) for r in events]
 return dict(modern_greater=sum(a is not None and b is not None and b>a for a,b in pairs),modern_less=sum(a is not None and b is not None and b<a for a,b in pairs),equal=sum(a==b for a,b in pairs),legacy_zero=sum(a==0 for a,b in pairs),ratio_modern_over_positive_legacy=summary([b/a if a is not None and b is not None and a>0 else None for a,b in pairs]),signed_difference=summary([b-a if a is not None and b is not None else None for a,b in pairs]))
legacy=json.loads((ROOT.parent/'legacy-soil-anchors-r4/results.json').read_text())
misses=[dict(case=r['case'],group=r['group'],reference_kg_yr=r['reference_kg_yr'],legacy_r4_kg_yr=r['metrics']['sediment_export_kg_yr']) for r in legacy if not r['within']]
annual={}
for group in sorted({r['group'] for r in rows}):
 selected=[r for r in rows if r['group']==group]
 annual[group]={}
 for roleidx,role in enumerate(('road','fill','buffer')):
  annual[group][role]={}
  for field in ('surface_out_m3','lateral_out_m3','lateral_in_m3','deep_percolation_m3'):
   vals=[r['lanes']['modern']['ofes'][roleidx][field]-r['lanes']['legacy']['ofes'][roleidx][field] for r in selected]
   annual[group][role][field]=dict(modern_greater=sum(x>0 for x in vals),modern_less=sum(x<0 for x in vals),delta=summary(vals),legacy_zero=sum(r['lanes']['legacy']['ofes'][roleidx][field]==0 for r in selected),modern_zero=sum(r['lanes']['modern']['ofes'][roleidx][field]==0 for r in selected))
ranked=json.loads((ROOT/'top-discrepancy-events.json').read_text());positive=[r for r in ranked if r['delta_reported_sediment_out_kg']>0];zero=[r for r in ranked if r['delta_reported_sediment_out_kg']==0];negative=[r for r in ranked if r['delta_reported_sediment_out_kg']<0]
(ROOT/'positive-ranked-discrepancy-events.json').write_text(json.dumps(positive,indent=2)+'\n')
negative_rank=con.execute('''SELECT case_id,original_group,year,julian,legacy_sediment_in_kg,modern_sediment_in_kg,legacy_sediment_out_kg,modern_sediment_out_kg,legacy_surface_in_m3,modern_surface_in_m3,legacy_surface_out_m3,modern_surface_out_m3,delta_reported_sediment_out_kg FROM t WHERE delta_reported_sediment_out_kg<0 QUALIFY row_number() OVER(PARTITION BY case_id ORDER BY delta_reported_sediment_out_kg,year,julian)<=3 ORDER BY case_id,delta_reported_sediment_out_kg''').fetch_arrow_table().to_pylist()
(ROOT/'exploratory-negative-discrepancy-events.json').write_text(json.dumps(negative_rank,indent=2)+'\n')
result=dict(status='Exploratory post hoc hydrologic associations; not a predeclared causal test or parameter acceptance.',script_sha256=sha(Path(__file__)),frozen_summary_sha256=sha(ROOT/'summary.json'),case_summary_sha256=sha(ROOT/'case-summary.json'),events=len(events),distinct_cases=len({x['case_id'] for x in events}),distinct_climate_dates=len({(x['climate'],x['year'],x['julian']) for x in events}),support='Printing-separated small-reference events: generated incoming sediment lower and outgoing sediment higher by more than combined F9.3 print intervals.',paired={field:paired(field) for field in ('surface_in_m3','surface_out_m3','lateral_in_m3','lateral_out_m3','rain_melt_m3','deep_percolation_m3','effective_duration_h','element_peak_runoff_mm_h','keff_mm_h')},events_detail=events,annual_hydrologic_differences=annual,legacy_r4_against_original_WEPP2010=dict(passing=116-len(misses),failing=len(misses),failure_groups=dict(Counter(r['group'] for r in misses)),misses=misses),ranked_event_selection_disclosure=dict(frozen_artifact_sha256=sha(ROOT/'top-discrepancy-events.json'),rows=len(ranked),positive=len(positive),zero=len(zero),negative=len(negative),wording_correction='Executed SQL retained three largest signed reported differences per case, including zeros; frozen declaration incorrectly said largest positive. Preserve the frozen artifact; positive selection explicitly excludes nonpositive rows. Separate negative-tail list is exploratory.',filtered_positive_sha256=sha(ROOT/'positive-ranked-discrepancy-events.json'),exploratory_negative_sha256=sha(ROOT/'exploratory-negative-discrepancy-events.json')),limitations=['Case-events share climate dates and legacy templates; they are not independent storms or material replicates.','A higher published Keff does not isolate infiltration/storage/routing because complete soil profiles differ.','Surface flow, lateral flow and water state can explain delivery changes without establishing a class-mixture cause.','Any next source-observation cases and rules require a new predeclaration before instrumentation; no new model run occurred.'])
(ROOT/'exploratory-hydrology.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:result[k] for k in ('events','distinct_cases','distinct_climate_dates','paired','ranked_event_selection_disclosure')},indent=2))
