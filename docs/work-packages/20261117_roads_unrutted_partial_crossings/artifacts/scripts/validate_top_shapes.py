"""Native exact-fit and short-downhill probes in a separate minimal project copy."""
from pathlib import Path
import hashlib, json, shutil
import pyarrow.parquet as pq
from wepppy.nodb.mods.roads import Roads, _unrutted
from wepppy.wepp.interchange.hill_pass_interchange import run_wepp_hillslope_pass_interchange
import validate_forest as base
base.SOURCE=Path('/wc1/runs/ru/rupc2-misty-shortfill')
base.ROOT=root=Path('/wc1/runs/ru/rupc2-native-shapes-accepted')
if root.exists():
    raise RuntimeError('Refuse to overwrite native shape evidence')
root.mkdir()
for path in base.SOURCE.glob('*.nodb'):
    (root/path.name).write_text(json.dumps(base.rebase(json.loads(path.read_text()))))
shutil.copy2(base.SOURCE/'config.cfg',root/'config.cfg')
(root/'wepp/runs').mkdir(parents=True)
shutil.copy2(base.SOURCE/'wepp/runs/p31.cli',root/'wepp/runs/p31.cli')
r=Roads.getInstance(str(root));r._ensure_roads_dirs()
result={}
for identifier,hill in [(990001,24.3),(990002,25.3)]:
    plan=_unrutted.placement(hill,4.1,20.2,100.,10.)
    plan.update(parity_profile={'sim_length_m':4.1},fill_profile={'fill_length_m':20.2,'fill_slope_pct':10.},
                top_landuse_slope_pct=10.,bottom_landuse_slope_pct=10.)
    lengths,slopes,roles=_unrutted.profile_parts(plan)
    stem=Path(r.roads_runs_dir)/f'probe{identifier}'
    slp=stem.with_suffix('.slp');sol=stem.with_suffix('.sol');man=stem.with_suffix('.man')
    area=_unrutted.write_slope(slp,100.,lengths,slopes)
    soil_template=r._resolve_legacy_soil_template_path(design='outslope_rutted',surface='gravel',soil_texture='loam')
    r._build_routed_mofe_soil_file(template_path=soil_template,output_path=sol,traffic='low',surface='gravel',rfg_pct=20.,ofe_order=roles)
    r._build_routed_mofe_management_file(template_path=r._resolve_legacy_management_template_path(traffic='low'),output_path=man,ofe_order=roles)
    r._run_segment_hillslope(segment_run_id=identifier,climate_wepp_id=31,sim_years=16,wepp_bin=r.wepp_instance.wepp_bin,
        single_ofe_management_path=man,single_ofe_soil_path=sol,single_ofe_slope_path=slp)
    provenance=r._parameterization_runtime_readbacks[str(Path(r.roads_runs_dir)/f'p{identifier}.sol')]
    assert [v['role'] for v in provenance['ofes']]==(['road','fill'] if identifier==990001 else ['road','fill','buffer'])
    files={str(p.relative_to(root)):base.digest(p) for p in Path(r.roads_runs_dir).glob(f'p{identifier}.*') if p.is_file()}
    passed=Path(r.roads_output_dir)/f'H{identifier}.pass.dat'
    files[str(passed.relative_to(root))]=base.digest(passed)
    result[str(identifier)]={'placement':plan,'roles':roles,'lengths':lengths,'emitted_area_m2':area,'files':files,'parameterization':provenance}
table=pq.read_table(run_wepp_hillslope_pass_interchange(r.roads_output_dir)).to_pandas()
for identifier,group in table.groupby('wepp_id'):
    assert len(group)==5844
    assert group.runvol.map(lambda x: __import__('math').isfinite(x)).all()
    result[str(identifier)]['pass_rows']=len(group)
    result[str(identifier)]['runoff_m3']=float(group.runvol.sum())
(root/'validation-result.json').write_text(json.dumps(result,indent=2))
print('NATIVE_SHAPES_OK', {k:v['roles'] for k,v in result.items()},flush=True)
