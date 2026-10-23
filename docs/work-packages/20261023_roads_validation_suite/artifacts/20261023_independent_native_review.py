import duckdb,hashlib,json,math
from pathlib import Path
import pyarrow.parquet as pq
from tests.roads.roads_matrix import CASES,execution_identity
root=Path("/tmp/roads-matrix-verified-oct23/roads_matrix0")
folder=root/"wepp/roads/output/interchange"
c=duckdb.connect()
for name,file in (("p","H.pass.parquet"),("w","H.wat.parquet"),("s","roads_segment_loss_summary.parquet")):
 c.read_parquet(str(folder/file)).create_view(name)
summaries={r["segment_run_id"]:r for r in pq.read_table(folder/"roads_segment_loss_summary.parquet").to_pylist()}
assert len(summaries)==516
assert c.sql("SELECT count(*) FROM (SELECT wepp_id FROM p GROUP BY wepp_id HAVING count(*)<>5844 OR count(DISTINCT sim_day_index)<>5844 OR min(sim_day_index)<>1 OR max(sim_day_index)<>5844 OR count(DISTINCT year)<>16 OR min(year)<>2000 OR max(year)<>2015)").fetchone()[0]==0
assert c.sql("SELECT count(*) FROM p WHERE make_date(year,month,day_of_month) <> DATE '2000-01-01' + (sim_day_index-1) OR date_part('doy',make_date(year,month,day_of_month)) <> julian").fetchone()[0]==0
assert c.sql("SELECT count(*) FROM (SELECT wepp_id,ofe_id FROM w GROUP BY wepp_id,ofe_id HAVING count(*)<>5844 OR count(DISTINCT sim_day_index)<>5844 OR min(Area)<=0 OR min(Area)<>max(Area))").fetchone()[0]==0
assert c.sql("SELECT count(*) FROM w WHERE make_date(year,month,day_of_month) <> DATE '2000-01-01' + (sim_day_index-1) OR date_part('doy',make_date(year,month,day_of_month)) <> julian").fetchone()[0]==0
aggregates=c.sql("SELECT wepp_id,sum(tdet)/16,sum(tdep)/16,sum(runvol*(sedcon_1+sedcon_2+sedcon_3+sedcon_4+sedcon_5))/16,sum(runvol)/16,sum(sbrunv)/16,sum(gwbfv)/16 FROM p GROUP BY wepp_id ORDER BY wepp_id").fetchall()
keys=("soil_loss_kg","sediment_deposition_kg","sediment_yield_kg","runoff_volume_m3","subrunoff_volume_m3","baseflow_volume_m3")
errors={key:0.0 for key in keys}
for identifier,*values in aggregates:
 for key,value in zip(keys,values):
  assert math.isfinite(value) and math.isfinite(summaries[identifier][key])
  errors[key]=max(errors[key],abs(value-summaries[identifier][key]))
  assert math.isclose(value,summaries[identifier][key],rel_tol=1e-12,abs_tol=1e-10)
area_error=0.0
areas=dict(c.sql("SELECT wepp_id,sum(Area) FROM (SELECT wepp_id,ofe_id,min(Area) AS Area FROM w GROUP BY wepp_id,ofe_id) GROUP BY wepp_id").fetchall())
geometry_error=0.0
records=[]
for identifier,case in enumerate(CASES,1):
 r=json.loads((root/f"case-{identifier}.json").read_text())
 records.append(r)
 s=summaries[identifier]
 assert s["simulation_years"]==16
 area_error=max(area_error,abs(areas[identifier]-s["modeled_area_m2"]))
 assert math.isclose(areas[identifier],s["modeled_area_m2"],rel_tol=1e-12,abs_tol=1e-10)
 assert math.isclose(s["soil_loss_kg"]/areas[identifier],s["soil_loss_density_kg_m2"],rel_tol=1e-12,abs_tol=1e-15)
 geometry_error=max(geometry_error,abs(r["emitted"]["width_m"]*sum(r["emitted"]["lengths_m"])-areas[identifier]))
 assert r["management_readback"]["schedule_years"]==200
double=next(r for r in records if r["case"]["control"]=="grade_double")
assert double["requested"]["road_slope_pct"]>40 and double["effective_geometry"]["road_slope_pct"]==40
assert double["clipping"]["road_grade"] is True
assert all(float(v)==0.4 for v in double["emitted"]["slope_lines"][0].replace(","," ").split()[1::2])
execution=json.loads((root/"execution-identity.json").read_text())
assert execution==execution_identity()
maximum=max(summaries.values(),key=lambda r:r["soil_loss_density_kg_m2"])
ratios=[r["sediment_yield_kg"]/r["soil_loss_kg"] for r in summaries.values() if r["soil_loss_kg"]!=0]
old=Path("/tmp/roads-pilot-oct23/roads_matrix0/wepp/roads/output")
new=Path("/tmp/roads-pilot-fixed-oct23/roads_matrix0/wepp/roads/output")
parity={p.name:hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256((new/p.name).read_bytes()).hexdigest() for p in old.glob("H*.pass.dat") if p.stat().st_size>1000 and (new/p.name).exists()}
assert len(parity)==14 and all(parity.values())
evidence=dict(root=str(root),cases=516,pass_daily_rows=c.sql("SELECT count(*) FROM p").fetchone()[0],wat_daily_ofe_rows=c.sql("SELECT count(*) FROM w").fetchone()[0],complete_pass_and_wat_calendars=True,annual_divisor=16,maximum_absolute_summary_errors=errors,maximum_absolute_area_error_m2=area_error,maximum_wat_vs_rounded_slope_area_error_m2=geometry_error,detachment_density_min=min(r["soil_loss_density_kg_m2"] for r in summaries.values()),detachment_density_max=maximum["soil_loss_density_kg_m2"],max_case=records[maximum["segment_run_id"]-1]["name"],maximum_case_annual_detachment_kg=maximum["soil_loss_kg"],maximum_case_area_m2=maximum["modeled_area_m2"],negative_deposition_cases=sum(r["sediment_deposition_kg"]<0 for r in summaries.values()),zero_deposition_cases=sum(r["sediment_deposition_kg"]==0 for r in summaries.values()),ratios_above_one=sum(v>1 for v in ratios),maximum_export_detachment_ratio=max(ratios),nonzero_pass_lateral_profiles=sum(r["subrunoff_volume_m3"]!=0 for r in summaries.values()),grade_double=dict(requested=double["requested"]["road_slope_pct"],effective=double["effective_geometry"]["road_slope_pct"],slope_line=double["emitted"]["slope_lines"][0],flag=double["clipping"]["road_grade"]),preexecution_identity_matches=True,native_sha256=execution["native_sha256"],pilot_pass_parity=parity,artifact_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder/"H.pass.parquet",folder/"H.wat.parquet",folder/"roads_segment_loss_summary.parquet",root/"execution-identity.json")})
print(json.dumps(evidence,indent=2,allow_nan=False))
