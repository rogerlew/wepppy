"""Read back current native artifacts and verify source isolation."""
from pathlib import Path
import hashlib, json, math
import pyarrow.parquet as pq
from wepppy.nodb.mods.roads import _unrutted
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
from wepppy.weppcloud.routes.nodb_api._roads_detachment import read_detachment_view
from wepppy.wepp.interchange.roads_accounting import load
from validate_forest import inventory, SOURCE, ROOT

root=ROOT
assert inventory(SOURCE)==json.loads((root/'validation-source-before.json').read_text())
receipt=lifecycle.require_current(root)
summary=json.loads((root/'validation-slices-result.json').read_text())
manifest=json.loads((root/'wepp/roads/segments/roads.segment.pass.manifest.json').read_text())
ledger=load(root)
records={}
for h in (42,141):
    rows=[r for r in manifest if r.get('target_hillslope_topaz_id')==h and r.get('status')=='completed']
    assert len(rows)==2, rows
    area=0
    files={}
    for row in rows:
        identifier=row['segment_run_id']
        slope=root/'wepp/roads/runs'/f'p{identifier}.slp'
        area+=_unrutted.slope_area(slope)
        for ext in ('slp','sol','man','cli','run'):
            p=root/'wepp/roads/runs'/f'p{identifier}.{ext}'
            assert p.is_file()
            files[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
        pass_path=root/row['segment_pass_relpath']
        assert pass_path.is_file()
        files[str(pass_path.relative_to(root))]=hashlib.sha256(pass_path.read_bytes()).hexdigest()
    hill=next(r for r in summary['outslope_unrutted_hillslope_records'] if r['topaz_id_hill']==h)
    assert abs(area-hill['reference_area_m2'])<=1e-6
    assert hill['inclusion_ratio_by_segment'] and max(hill['inclusion_ratio_by_segment'].values()) < .60
    target=next(t for t in ledger['targets'] if t['id']==rows[0]['target_hillslope_wepp_id'])
    assert target['mode']=='replacement'
    records[h]={'geometry':hill,'emitted_area_m2':area,'native_files':files,'ledger_target':target}
pass_table=pq.read_table(root/'wepp/roads/output/interchange/H.pass.parquet').to_pandas()
wat_table=pq.read_table(root/'wepp/roads/output/interchange/totalwatsed3.parquet')
assert wat_table.num_rows>0
assert all(math.isfinite(float(v)) for v in pass_table.runvol)
view=read_detachment_view(root)
assert view['roads_detachment']['state']=='available'
assert all(f['properties']['roads_detachment']['state']=='complete' for f in view['features'])
# Verify the actual consumer uses each canonical replacement exactly once.
water_run = root/'wepp/roads/runs/pw0.run'
water_text = water_run.read_text().splitlines()
for identifier in (5,31):
    assert water_text.count(f'../output/H{identifier}.pass.dat') == 1
    target = next(t for t in ledger['targets'] if t['id']==identifier)
    receipt_sources = target['pass_receipt']['sources']
    assert len(receipt_sources)==2
    assert all(source['source_id'].startswith('roads:') for source in receipt_sources)
    closure=target['pass_receipt']['run_closure']
    assert all(abs(closure['residuals'][key]) <= budget for key,budget in closure['budgets'].items())
    assert all(ratio<=1.0 for ratio in closure['max_event_budget_ratios'].values())
    canonical=root/'wepp/roads/output'/f'H{identifier}.pass.dat'
    records[42 if identifier==5 else 141]['canonical_pass_sha256']=hashlib.sha256(canonical.read_bytes()).hexdigest()
assert (root/'wepp/roads/output/pass_pw0.txt').stat().st_size>0
retention={}
for current in (root/'wepp/roads/runs').glob('unrutted-*.slp'):
    expected=hashlib.sha256(current.read_bytes()).hexdigest()
    retained=[p for p in (root/'wepp/roads/history').rglob(current.name)
              if hashlib.sha256(p.read_bytes()).hexdigest()==expected]
    assert retained, f'No retained identical native geometry: {current.name}'
    retention[current.name]=str(retained[0].relative_to(root))
result={'source_unchanged':True,'retained_geometry':retention,
        'watershed_run_sha256':hashlib.sha256(water_run.read_bytes()).hexdigest(),'receipt':receipt,'hillslopes':records,
        'native_pass_rows':len(pass_table),'water_report_rows':wat_table.num_rows,
        'detachment_view_state':view['roads_detachment']['state'],
        'no_road_control':json.loads((root/'validation-no-road/result.json').read_text()),
        'full_upload_failure':json.loads((root/'validation-full-upload-failure.json').read_text())['error'],
        'scope':'valid slices with synthetic fill/buffer inputs; not full-site success'}
(root/'validation-evidence.json').write_text(json.dumps(result,indent=2))
print('EVIDENCE_OK',json.dumps({k:v for k,v in result.items() if k not in ('receipt','hillslopes','no_road_control')}))
