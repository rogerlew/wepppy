"""Read native outputs, consumer inputs, placement provenance and source isolation."""
from pathlib import Path
import json, math, os
import pyarrow.parquet as pq
from wepppy.nodb.mods.roads import _unrutted
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
from wepppy.wepp.interchange.roads_accounting import load
from wepppy.weppcloud.routes.nodb_api._roads_detachment import read_detachment_view
import validate_forest as base
full=Path('/wc1/runs/ru/rupc2-misty-validation')
short=Path('/wc1/runs/ru/rupc2-misty-shortfill')
shapes=Path('/wc1/runs/ru/rupc2-native-shapes-accepted')
assert base.inventory(base.SOURCE)==json.loads((full/'validation-source-before.json').read_text())
assert base.inventory(base.SOURCE)==json.loads((short/'validation-source-before.json').read_text())
full_result=json.loads((full/'validation-result.json').read_text())
assert full_result['status']=='failed' and full_result['failed_segment_count']==5
assert not lifecycle.available(full)
original=json.loads(Path('/wc1/runs/ru/rupc-misty-validation/validation-full-upload-failure.json').read_text())
full_rows={r['segment_hillslope_id']:r for r in full_result['segment_execution_records'] if 'segment_hillslope_id' in r}
fields=('segment_hillslope_id','target_hillslope_topaz_id','status','reason','placement_adjustment',
        'original_top_landuse_length_m','hillslope_length_m','road_width_m','fill_length_m',
        'top_landuse_length_m','bottom_landuse_length_m','placement_source','discha_median_m')
dispositions=[]
for row in original['failed_segments']:
    current=full_rows[row['segment_hillslope_id']]
    dispositions.append({k:current.get(k) for k in fields})
assert sum(r['status']=='completed' for r in dispositions)==3
summary=json.loads((short/'validation-result.json').read_text())
assert summary['status']=='completed'
assert summary['unrutted_placement_policy']==_unrutted.PLACEMENT_POLICY
receipt=lifecycle.require_current(short)
rows=json.loads((short/'wepp/roads/segments/roads.segment.pass.manifest.json').read_text())
assert len(rows)==24 and all(r['status']=='completed' for r in rows)
files={}; areas={}; profiles=[]
for row in rows:
    identifier=row['segment_run_id'];hill=row['target_hillslope_topaz_id']
    slp=short/'wepp/roads/runs'/f'p{identifier}.slp'
    areas[hill]=areas.get(hill,0.)+_unrutted.slope_area(slp)
    for item in row['parameterization']['input_files']:
        assert base.digest(short/item['relpath'])==item['sha256']
    for ext in ('slp','sol','man','cli','run'):
        p=short/'wepp/roads/runs'/f'p{identifier}.{ext}'
        files[str(p.relative_to(short))]=base.digest(p)
    passed=short/row['segment_pass_relpath'];files[str(passed.relative_to(short))]=base.digest(passed)
    if row['design']=='outslope_unrutted':
        assert row['placement_policy']==_unrutted.PLACEMENT_POLICY
        if row['placement_adjustment']=='top_of_hillslope':
            assert row['top_landuse_length_m']==0 and row['upslope_runon_assumed_zero']
        profiles.append({k:row.get(k) for k in (*fields,'contributor_ofe_count','top_ofe_compensation_m','bottom_ofe_compensation_m')})
hills=[]
for hill in summary['outslope_unrutted_hillslope_records']:
    if hill['area_accounting_status']=='complete':
        emitted=areas[hill['topaz_id_hill']]
        assert abs(emitted-hill['reference_area_m2'])<=1e-6
        hills.append({**hill,'readback_area_m2':emitted})
ledger=load(short);water=short/'wepp/roads/runs/pw0.run';water_lines=water.read_text().splitlines()
replacements=[]
for target in ledger['targets']:
    if target['mode']!='replacement':continue
    assert water_lines.count(f"../output/H{target['id']}.pass.dat")==1
    assert all(v['source_id'].startswith('roads:') for v in target['pass_receipt']['sources'])
    closure=target['pass_receipt']['run_closure']
    assert all(abs(closure['residuals'][k])<=v for k,v in closure['budgets'].items())
    assert all(v<=1 for v in closure['max_event_budget_ratios'].values())
    replacements.append(target)
view=read_detachment_view(short)
assert view['roads_detachment']['state']=='available'
assert any('no runoff from land above' in (f['properties']['roads_detachment']['reason'] or '') for f in view['features'])
wat=pq.read_table(short/'wepp/roads/output/interchange/totalwatsed3.parquet')
assert wat.num_rows==5844
passed=pq.read_table(short/'wepp/roads/output/interchange/H.pass.parquet').to_pandas()
assert all(math.isfinite(float(v)) for v in passed.runvol)
assert (short/'wepp/roads/output/pass_pw0.txt').stat().st_size>0
shape_result=json.loads((shapes/'validation-result.json').read_text())
for row in shape_result.values():
    assert row['pass_rows']==5844
    for name,sha in row['files'].items():assert base.digest(shapes/name)==sha
candidate={str(p):base.digest(p) for p in map(Path,[
 'wepppy/nodb/mods/roads/_unrutted.py','wepppy/nodb/mods/roads/roads.py',
 'wepppy/wepp/interchange/_roads_lifecycle.py','wepppy/weppcloud/routes/nodb_api/_roads_detachment.py'])}
evidence={'contract_checkpoint':'f46d59422009d5adb8641b1d2b7494cd5f9b788a',
 'candidate_sources':candidate,'runtime_identity':{'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups()},
 'source_unchanged':True,'full_30m_fill_dispositions':dispositions,
 'short_5m_fill_run':{'root':str(short),'profiles':profiles,'hillslopes':hills,'replacement_receipts':replacements,
 'native_files':files,'watershed_run_sha256':base.digest(water),'receipt':receipt,
 'pass_rows':len(passed),'report_rows':wat.num_rows,'inspection':view['roads_detachment']},
 'native_shapes':shape_result,'scope':'Synthetic 30m/5m fill and exact-fit probes; not site calibration or deployment'}
(short/'validation-evidence.json').write_text(json.dumps(evidence,indent=2))
print('EVIDENCE_OK',len(dispositions),len(profiles),len(hills),flush=True)
