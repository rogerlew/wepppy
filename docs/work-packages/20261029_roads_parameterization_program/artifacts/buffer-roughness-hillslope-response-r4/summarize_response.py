"""Original source-free readback of the declared whole-hillslope response study."""
import argparse
import hashlib
import json
from pathlib import Path

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def save(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def scalar(group,tag,index):
    rows=group.get('raw_operands',{}).get(tag,[])
    assert len(rows)<=1,(tag,len(rows))
    return rows[0]['values'][index] if rows else None

def producer(group,tag,index):
    rows=[r for r in group['roughness_consumer_rows'] if r['tag']==tag]
    assert len(rows)<=1,(tag,len(rows))
    return rows[0]['values'][index] if rows else None

def target(group):
    geometry=group['raw_operands']['BP_GEOMETRY'][0]['values']
    width,length=geometry[:2]
    runoff=scalar(group,'BP_IRS_OUT',0);effective_length=scalar(group,'BP_IRS_OUT',3)
    handoff=group['sediment_handoff']
    return dict(ofe=group['ofe'],day=group['day'],route_entered=group['route_entered'],
        geometry_native_m=dict(width=width,local_length=length),
        consumed_roughness_m=producer(group,'RP_CTCARR',0),
        effective_critical_shear_Pa=scalar(group,'BP_ERODIBILITY',4),
        critical_shear_adjustment_factor=producer(group,'RP_CTCARR',2),
        crust_adjustment_factor=producer(group,'RP_CRUST_ACTIVE',2),
        crust_inactive_factor=producer(group,'RP_CRUST_INACTIVE',1),
        interrill_roughness_factor=producer(group,'RP_IR_DELIVERY',1),
        interrill_delivery_fraction=producer(group,'RP_IR_DELIVERY',2),
        effective_plane_conductivity_m_s=scalar(group,'BP_EQUIV',0),
        effective_plane_runoff_m=runoff,effective_plane_length_m=effective_length,
        surface_boundary_m3=None if runoff is None else runoff*effective_length*width,
        effective_duration_s=scalar(group,'BP_IRS_OUT',2),
        peak_m_s=scalar(group,'BP_IRS_OUT',1),
        published_boundary_sediment_kg_m=scalar(group,'BP_OFE_END',2),
        receiving_duration_handoff=handoff,
        consumed_ga_capacity=group['ga_capacity'],
        hourly_local_depth_sums_m=group['hourly_local_depth_sums_m'],
        hourly_upstream_depth_sums_m=group['hourly_upstream_depth_sums_m'],
        friction_observations=[r for r in group['roughness_consumer_rows'] if r['tag']=='RP_FRICTION'])

def fmt(value):
    return 'unavailable' if value is None else f'{value:.6g}'

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--independent',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();root=args.root.resolve();out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    independent=read(args.independent);verification=read(root/'verification.json')
    assert independent['independent_runtime_readback_passed'] and independent['full_period_runs']==36
    assert verification['passed'] and verification['full_period_runs']==36
    assert not independent['accepted_parameterization']
    for path,h in independent['bindings'].items():assert sha(path)==h,path
    declaration=read(root/'execution-declaration.json')
    tasks={(t['stratum'],t['lane'],t['mode']):t for t in declaration['tasks']};assert len(tasks)==36
    seeds=read(root.parent/'seeds.json')['seeds'];ids={s['stratum']:f'B{i+1}' for i,s in enumerate(seeds)}
    rows=[];bindings={str(args.independent.resolve()):sha(args.independent)}
    for pair in independent['pairs']:
        records=[];target_modes=[]
        for mode in (0,1):
            task=tasks[pair['stratum'],pair['lane'],mode];path=Path(task['folder'])/'record.json'
            record=read(path);assert record['physical_pass'] and record['coverage']['passed']
            assert record['metrics']['sediment_export_kg_yr']==pair['annual_off_on_kg_yr'][mode]
            records.append(record);bindings[str(path.resolve())]=sha(path)
            day=task['event']['julian']
            selected=[g for g in pair['bounded_process_off_on'][mode] if g['day']==day]
            assert sorted(g['ofe'] for g in selected)==[1,2,3]
            target_modes.append([target(g) for g in sorted(selected,key=lambda g:g['ofe'])])
        annual=[]
        for mode,r in enumerate(records):
            annual.append(dict(mode=mode,metrics=r['metrics'],
                sediment_roles=r['audit']['sediment']['ofes'],
                water_roles=r['audit']['water']['ofes'],
                historical_sediment_audit_width_m=r['width_m'],
                note='Sediment audit uses recorded metadata width; water audit uses emitted geometry. Preserve historical audit basis, not a new geometry normalization.'))
        rows.append(dict(case=ids[pair['stratum']],stratum=pair['stratum'],lane=pair['lane'],
            expected_null=pair['expected_null'],reference_kg_yr=pair['reference_kg_yr'],
            annual_off_on_kg_yr=pair['annual_off_on_kg_yr'],annual_delta_kg_yr=pair['annual_delta_kg_yr'],
            original_envelope_off_on_pass=pair['original_envelope_off_on_pass'],
            annual_roles_off_on=annual,target_day_roles_off_on=target_modes))
    assert len(rows)==18
    for path in (root/'verification.json',root/'execution-declaration.json',root.parent/'seeds.json',Path(__file__).resolve()):
        bindings[str(path.resolve())]=sha(path)
    summary=dict(full_period_runs=36,profile_pairs=9,accepted_parameterization=False,
        original_isolation_campaign_status='failed; unchanged',
        interpretation='Selected complete-history model response under same persistence rule; not physical validation or a whole-matrix result.',
        modern_envelope_recoveries=independent['modern_envelope_recoveries'],
        modern_envelope_regressions=independent['modern_envelope_regressions'],
        selected_panel_improvement_criterion=independent['selected_panel_improvement_criterion'],
        rows=rows,bindings=bindings,
        limits=['Whole-hillslope native feedback permitted; protected/off/null/accounting gates unchanged.',
                'Signed net exchange and receiving-duration handoffs are not gross production or tagged origins.',
                'Hourly sums use reported native operand depths with their local/upstream length support; not independent complete water closure.',
                'Missing producer branches remain unavailable; a prior-day or skipped value is not fabricated.',
                'Natural interrill delivery suppression and friction/crust/shear effects coexist; no storage-only attribution.'])
    save(out/'summary.json',summary)
    lines=['# Annual sediment response for all nine pairs','',
           'All values are kg/year. O4 is the fresh control; U1 retains initial buffer roughness. The reference and envelope are unchanged.','',
           '| Case | Soil lane | FSWEPP2 reference | O4 | U1 | U1 minus O4 | Envelope O4 / U1 |',
           '| --- | --- | ---: | ---: | ---: | ---: | --- |']
    for r in rows:
        status=' / '.join('pass' if x else 'fail' for x in r['original_envelope_off_on_pass'])
        lines.append(f"| {r['case']} | {r['lane']} | {fmt(r['reference_kg_yr'])} | {fmt(r['annual_off_on_kg_yr'][0])} | {fmt(r['annual_off_on_kg_yr'][1])} | {fmt(r['annual_delta_kg_yr'])} | {status} |")
    (out/'annual-response.md').write_text('\n'.join(lines)+'\n')
    save(out/'readback-receipt.json',dict(passed=True,script_sha256=sha(__file__),
        summary_sha256=sha(out/'summary.json'),table_sha256=sha(out/'annual-response.md'),input_bindings=bindings))
    print(json.dumps(dict(passed=True,runs=36,recoveries=summary['modern_envelope_recoveries'],regressions=summary['modern_envelope_regressions'])))

if __name__=='__main__':main()
