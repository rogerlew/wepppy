"""Read-only physical-basis diagnostics; these are not behavioral model results."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def keyed(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[f] for f in fields)
        need(key not in result, f'duplicate support: {key}')
        result[key] = row
    return result


def required(mapping, key):
    need(key in mapping, f'missing required owner support: {key}')
    return mapping[key]


def fine_fraction(rock, density):
    need(0 <= rock < 1 and density > 0, 'rock/density domain')
    return 1 - rock*density/(rock*density+2650*(1-rock))


def diagnostic(upper, saved, dry, depth, por0, por_now, fine, ice):
    need(all(math.isfinite(x) for x in (upper,saved,dry,depth,por0,por_now,fine,ice)), 'nonfinite')
    need(0 < depth < 10 and 0 <= dry < 1 and 0 < por0 < 1 and 0 < por_now < 1 and 0 < fine <= 1, 'units/domain')
    need(ice == 0, 'unfrozen diagnostic only; ice cannot be silently ignored')
    water = saved + dry*depth
    actual_ceiling = upper + dry*depth
    pore = por0*depth
    current_pore = por_now*depth
    bulk = pore*fine
    current_bulk = current_pore*fine
    signed = upper-saved
    rounding = upper - (por0-dry)*depth
    # Different evaluation orders may differ by machine-double summation only.
    residual = signed - (pore-water) - rounding
    need(abs(residual) <= 1e-15, 'dry-coordinate identity')
    return dict(total_liquid_m=water, native_absolute_ceiling_m=actual_ceiling,
        initialized_pore_depth_m=pore, initialized_bulk_diagnostic_ceiling_m=bulk,
        current_soil_pore_diagnostic_ceiling_m=current_pore,
        current_soil_bulk_diagnostic_ceiling_m=current_bulk,
        native_signed_headroom_m=signed, dry_coordinate_identity_residual_m=residual,
        native_capacity_rounding_m=rounding,
        native_available_m=max(signed,0),
        initialized_bulk_signed_headroom_m=bulk-water,
        initialized_bulk_available_diagnostic_m=max(bulk-water,0),
        initialized_bulk_occupied_excess_m=max(water-bulk,0),
        current_soil_signed_headroom_m=current_pore-water,
        current_soil_occupied_excess_m=max(water-current_pore,0),
        current_bulk_signed_headroom_m=current_bulk-water,
        current_bulk_occupied_excess_m=max(water-current_bulk,0),
        native_occupied_excess_m=max(water-actual_ceiling,0),
        initialized_rock_capacity_difference_m=pore-bulk,
        current_porosity_capacity_shift_m=current_pore-pore)


def controls():
    base = diagnostic(.04,.02,.1,.1,.5,.45,.8,0)
    shifted = diagnostic(.035,.015,.15,.1,.5,.45,.8,0)
    need(abs(base['total_liquid_m']-shifted['total_liquid_m']) < 1e-15, 'dry shift total water')
    need(abs(base['native_signed_headroom_m']-shifted['native_signed_headroom_m']) < 1e-15,'dry shift headroom')
    need(fine_fraction(0,1400)==1, 'zero rock identity')
    fine = [fine_fraction(x,1400) for x in (0,.1,.5,.9)]
    need(all(a>b for a,b in zip(fine,fine[1:])), 'rock monotonicity')
    rejects = 0
    for fn in [lambda:keyed([{'x':1},{'x':1}],('x',)),
               lambda:diagnostic(.04,.02,.1,100,.5,.45,.8,0),
               lambda:diagnostic(.04,.02,.1,.1,.5,.45,.8,.001)]:
        try:fn()
        except ValueError:rejects+=1
    try:
        required(keyed([{'case':'B1','ofe':'1','layer':'1'}],('case','ofe','layer')),('B1','2','1'))
    except ValueError:rejects+=1
    need(rejects==4, 'negative controls')
    return dict(dry_coordinate_shift=True, zero_rock=True, monotone_rock=True,rejected_mutations=rejects)


def write_csv(p, rows):
    with p.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((a.source/'manifest.json').read_text())
    need(sha(a.source/'manifest.json')=='a31ace8d9c7f866e607dedff7162ad0dc6ba69ed9495a2896ef6ade5ddfafbc1','accepted manifest drift')
    before={}
    tables={}
    for name in ('initial-layers.csv','structural.csv','layers.csv','calls.csv'):
        f=a.source/name;s=f.stat();need(sha(f)==manifest['files'][name],f'input hash drift: {name}')
        before[name]=dict(sha256=sha(f),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
        tables[name]=list(csv.DictReader(f.open()))
    initial=keyed(tables['initial-layers.csv'],('case','lane','mode','ofe','layer'))
    structural=keyed(tables['structural.csv'],('case','lane','mode','year','day','consumer_ofe','layer'))
    call_keys=('case','lane','mode','year','day','consumer_ofe')
    calls=keyed(tables['calls.csv'],call_keys)
    consumed=keyed(tables['layers.csv'],call_keys+('owner_ofe','layer'))
    need(len(initial)==586 and len(structural)==432 and len(calls)==152 and len(consumed)==556,'frozen counts')
    rows=[];grouped={}
    for key,r in consumed.items():
        owner=required(initial,(r['case'],r['lane'],r['mode'],r['owner_ofe'],r['layer']))
        state=required(structural,(r['case'],r['lane'],r['mode'],r['year'],r['day'],r['owner_ofe'],r['layer']))
        for field,target in [('ul_m','ul_m'),('depth_m','depth_m'),('initial_porosity','initial_porosity')]:
            need(float(r[field])==float(owner[target]),f'owner join: {field}')
        need(float(r['dry_theta'])==float(owner['final_dry']),'dry epoch drift')
        val=diagnostic(float(r['ul_m']),float(r['saved_liquid_m']),float(r['dry_theta']),float(r['depth_m']),float(owner['initial_porosity']),float(state['current_porosity']),float(owner['fine_earth_factor']),float(r['live_frozen_m']))
        need(val['native_available_m']==float(r['available_m']),'native branch equality')
        row={k:r[k] for k in call_keys+('owner_ofe','layer','target','trace_line','local_snapshot_line','weight')}
        row.update(depth_m=float(r['depth_m']),initial_fine_earth_factor=float(owner['fine_earth_factor']),initial_rock_mass_fraction=float(owner['rfg_mass_fraction']),initial_porosity=float(owner['initial_porosity']),prior_soil_porosity=float(state['current_porosity']),dry_theta=float(r['dry_theta']),saved_liquid_m=float(r['saved_liquid_m']),**val)
        rows.append(row);grouped.setdefault(key[:6],[]).append(row)
    summaries=[]
    for key,parts in grouped.items():
        call=calls[key];row={k:call[k] for k in call_keys+('target',)}
        row['native_available_observed_m']=float(call['connected_available_m'])
        for field in ('total_liquid_m','native_absolute_ceiling_m','initialized_pore_depth_m','initialized_bulk_diagnostic_ceiling_m','current_soil_pore_diagnostic_ceiling_m','current_soil_bulk_diagnostic_ceiling_m','native_available_m','initialized_bulk_available_diagnostic_m','initialized_bulk_occupied_excess_m','current_soil_occupied_excess_m','current_bulk_occupied_excess_m','native_occupied_excess_m','initialized_rock_capacity_difference_m','current_porosity_capacity_shift_m'):
            row[field]=sum(float(v['weight'])*v[field] for v in parts)
        row['native_order_rounding_residual_m']=row['native_available_observed_m']-row['native_available_m']
        row['consumed_layers']=len(parts)
        summaries.append(row)
    targets=[r for r in summaries if r['consumer_ofe']=='3' and r['target']=='True']
    need(len(targets)==36,'target support')
    allkeys={(f'B{i}',lane,str(mode)) for i in range(1,10) for lane in ('legacy','modern') for mode in (0,1)}
    need({(r['case'],r['lane'],r['mode']) for r in targets}==allkeys,'all-nine coverage')
    initial_rows=[]
    for v in initial.values():
        d=float(v['depth_m']);dry=float(v['final_dry']);por=float(v['initial_porosity']);fine=float(v['fine_earth_factor'])
        w=float(v['scon_liquid_m'])+dry*d
        need(float(v['scon_liquid_m'])==float(v['wb_liquid_m']),'initial writer state equality')
        initial_rows.append(dict(case=v['case'],lane=v['lane'],mode=v['mode'],ofe=v['ofe'],layer=v['layer'],depth_m=d,initial_pore_depth_m=por*d,initial_bulk_diagnostic_ceiling_m=por*d*fine,initial_native_absolute_ceiling_m=float(v['ul_m'])+dry*d,initial_total_liquid_m=w,initial_bulk_saturation_ratio=w/(por*d*fine)))
    unique=keyed([v for v in rows if v['consumer_ofe']==v['owner_ofe']],('case','lane','mode','year','day','owner_ofe','layer'))
    need(len(unique)==304,'unique local snapshot support')
    role_counts=[]
    for lane in ('legacy','modern'):
        for ofe in ('1','2','3'):
            selected=[v for v in unique.values() if v['lane']==lane and v['owner_ofe']==ofe]
            excess=[v for v in selected if v['initialized_bulk_occupied_excess_m']>abs(v['native_capacity_rounding_m'])+1e-15]
            role_counts.append(dict(lane=lane,ofe=ofe,unique_owner_layer_snapshots=len(selected),above_initialized_bulk_basis=len(excess),maximum_excess_m=max(v['initialized_bulk_occupied_excess_m'] for v in selected)))
    write_csv(a.out/'initial-physical-basis.csv',initial_rows)
    write_csv(a.out/'unique-owner-summary.csv',role_counts)
    write_csv(a.out/'consumed-physical-basis.csv',rows);write_csv(a.out/'connected-physical-basis.csv',summaries);write_csv(a.out/'target-physical-basis.csv',targets)
    for name,entry in before.items():
        f=a.source/name;s=f.stat();need(dict(sha256=sha(f),bytes=s.st_size,mtime_ns=s.st_mtime_ns)==entry,'original mutation')
    summary=dict(passed=True,calls=len(calls),consumed_rows=len(rows),target_rows=len(targets),
        counts_raw_positive_including_rounding={field:sum(r[field]>0 for r in rows) for field in ('initialized_bulk_occupied_excess_m','current_soil_occupied_excess_m','current_bulk_occupied_excess_m','native_occupied_excess_m')},
        maximum_m={field:max(r[field] for r in rows) for field in ('initialized_bulk_occupied_excess_m','current_soil_occupied_excess_m','current_bulk_occupied_excess_m','native_occupied_excess_m')},
        resolved_excess_counts={field:sum(r[field] > abs(r['native_capacity_rounding_m']) + 1e-15 for r in rows) for field in ('initialized_bulk_occupied_excess_m','current_soil_occupied_excess_m','current_bulk_occupied_excess_m')},
        unique_owner_snapshots=len({(r['case'],r['lane'],r['mode'],r['year'],r['day'],r['owner_ofe'],r['layer']) for r in rows}),
        unique_owner_snapshots_above_initialized_bulk=len({(r['case'],r['lane'],r['mode'],r['year'],r['day'],r['owner_ofe'],r['layer']) for r in rows if r['initialized_bulk_occupied_excess_m'] > abs(r['native_capacity_rounding_m'])+1e-15}),
        rounding_separation='Raw positive excess is reported separately; resolved count must exceed absolute native UL rounding residual plus declared1e-15m double summation bound. This separates arithmetic print/rounding effects, not a physical acceptance tolerance.',
        controls=controls(),reader_sha256=sha(Path(__file__)),source_manifest_sha256=sha(a.source/'manifest.json'),inputs=before,
        outputs={f.name:sha(f) for f in a.out.glob('*.csv')},
        limits=['Selected consumed rows repeat upstream states; not independent events or annual prevalence.','All consumed adjusted ice zero; general frozen total-water partition not inferred.','POR*CPM*DG is a documented-basis diagnostic, not a model execution or accepted new capacity.','Current-POR diagnostic uses prior same-day SOIL POR and initialized CPM; fixed actual water, no clipping or flux repair.','Positive excess is relative to explicitly selected capacity basis; physical adequacy remains separately reviewed.'])
    (a.out/'receipt.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k in ('passed','counts_raw_positive_including_rounding','resolved_excess_counts','maximum_m','controls')}))


if __name__=='__main__':main()
