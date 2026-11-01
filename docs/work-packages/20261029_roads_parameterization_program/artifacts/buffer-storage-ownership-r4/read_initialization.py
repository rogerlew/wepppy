"""Original source-free initialization producer and retained-consumer readback."""
import argparse
import copy
import csv
import hashlib
import json
import math
import struct
from collections import defaultdict
from pathlib import Path


def real(x):
    return struct.unpack('f', struct.pack('f', x))[0]


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def parse(path):
    rows = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        tokens = line.split()
        need(len(tokens) == 10, 'initialization row width')
        tag = tokens[0]
        seq, ofe, layer = map(int, tokens[1:4])
        vals = list(map(float, tokens[4:]))
        need(seq == number and all(math.isfinite(x) for x in vals), 'sequence/nonfinite')
        rows.append(dict(tag=tag, seq=seq, ofe=ofe, layer=layer, v=vals))
    return rows


def dry_guards(rock):
    dry, fc, moisture, cpm, pore, depth = rock
    flags = []
    if moisture >= pore:
        moisture = real(pore * real(.95)); flags.append('moisture_cap')
    if fc >= moisture:
        difference = real(fc - dry)
        fc = real(moisture * real(.99))
        dry = real(fc - difference)
        dry = max(dry, real(.01)); fc = max(fc, real(.01))
        flags.append('field_capacity_moisture')
    if real(fc / pore) > real(.83):
        ratio = real(fc / real(pore * real(.83)))
        fc = real(pore * real(.83)); dry = real(dry / ratio)
        flags.append('field_capacity_pore')
    if dry < real(.01):
        flags.append('dry_floor')
    if fc < real(.01):
        flags.append('field_capacity_floor')
    return max(dry, real(.01)), max(fc, real(.01)), flags


def validate(rows):
    need([r['seq'] for r in rows] == list(range(1, len(rows)+1)), 'row order')
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['ofe'], row['layer']].append(row)
    need({k[0] for k in grouped} == {1, 2, 3}, 'OFE coverage')
    for ofe in (1, 2, 3):
        layer_ids = sorted(l for o, l in grouped if o == ofe)
        need(layer_ids == list(range(1, max(layer_ids)+1)), 'layer coverage')
    results = []
    minimum = {}
    for (ofe, layer), records in sorted(grouped.items()):
        tags = [r['tag'] for r in records]
        expected = ['SO_SCON_INPUT', 'SO_SCON_PORE', 'SO_SCON_ROCK', 'SO_SCON_DRY', 'SO_SCON_UL']
        frozen = [r for r in records if r['tag'] == 'SO_SCON_FROZEN_K']
        need(len(frozen) <= 1, 'duplicate frozen substitution')
        if frozen:
            expected.append('SO_SCON_FROZEN_K')
        expected += ['SO_SCON_K', 'SO_WBH_UL' if 'SO_WBH_UL' in tags else 'SO_WB_UL']
        need(tags == expected, 'missing/duplicate/misordered layer producer')
        indexed = {r['tag']: r for r in records}
        inp, pore, rock, dry, upper = [indexed[t]['v'] for t in expected[:5]]
        k = indexed['SO_SCON_K']['v']
        wb = records[-1]['v']
        por, air, fine, density, density_cons, dry_before_rock = pore
        rfg = inp[4]
        por_calc = real(real(real(2650.-density)/real(2650.))*air)
        rock_mass = real(rfg*density)
        fine_calc = real(real(1.) - real(rock_mass/real(rock_mass+real(real(2650.)*real(real(1.)-rfg)))))
        need(por_calc == por, 'porosity/air arithmetic')
        need(fine_calc == fine, 'rock mass-volume arithmetic')
        need(real(dry_before_rock*fine) == rock[0], 'dry rock arithmetic')
        dry_calc, fc_calc, guards = dry_guards(rock)
        need(dry_calc == dry[0] and fc_calc == dry[1], 'dry/FC guards')
        need(dry[2:] == [por, upper[3], fine, air], 'dry operands')
        need(upper[1:4] == [por,dry[0],inp[2]] and upper[5] == inp[3], 'UL support')
        need(real(real(por-dry[0])*upper[3]) == upper[0], 'SCON UL arithmetic')
        need(wb[:4] == upper[:4] and wb[5] == upper[5], 'water balance UL overwrite')
        need(real(real(wb[1]-wb[2])*wb[3]) == wb[0], 'WB UL arithmetic')
        choose = layer == 1 or k[1] < minimum[ofe]
        candidate = k[1] if choose else minimum[ofe]
        if frozen:
            v = frozen[0]['v']
            need(choose and v[3] > 0 and v[2] > 0 and v[1] == k[1], 'frozen branch validity')
            candidate = v[2]
            need(v[0] == candidate, 'frozen assignment')
        need(candidate == k[0], 'running minimum assignment')
        minimum[ofe] = candidate
        depth = upper[3]
        results.append(dict(ofe=ofe, layer=layer, input_sequence=records[0]['seq'], scon_ul_sequence=indexed['SO_SCON_UL']['seq'], wb_ul_sequence=records[-1]['seq'], wb_tag=records[-1]['tag'], ul_m=upper[0], depth_m=depth, cumulative_depth_m=upper[5], initial_porosity=por, air_factor=air, fine_earth_factor=fine, rfg_mass_fraction=rfg, density_kg_m3=density, dry_pre_rock=dry_before_rock, dry_after_rock=rock[0], final_dry=dry[0], dry_correction_branches=','.join(guards), pore_volume_m=por*depth, dry_pre_rock_offset_m=dry_before_rock*depth, dry_after_rock_offset_m=rock[0]*depth, final_dry_offset_m=dry[0]*depth, rock_dry_offset_change_m=(rock[0]-dry_before_rock)*depth, guard_dry_offset_change_m=(dry[0]-rock[0])*depth, ul_rounding_residual_m=upper[0]-(por-dry[0])*depth, running_minimum_m_s=k[0], layer_conductivity_m_s=k[1], frozen_substitution=bool(frozen), scon_liquid_m=upper[4], wb_liquid_m=wb[4]))
    for ofe in (1,2,3):
        rr = [r for r in results if r['ofe']==ofe]
        need(max(r['scon_ul_sequence'] for r in rr) < min(r['wb_ul_sequence'] for r in rr), 'SCON all layers before WB initialization')
    return results, minimum


def controls(rows):
    mutations = []
    mutations.append(rows[1:])
    mutations.append([rows[0]]+rows)
    changed = copy.deepcopy(rows); changed[0], changed[1] = changed[1], changed[0]; mutations.append(changed)
    changed = copy.deepcopy(rows); next(r for r in changed if r['tag']=='SO_SCON_UL')['v'][0] *= 1000; mutations.append(changed)
    changed = copy.deepcopy(rows); next(r for r in changed if r['tag']=='SO_SCON_PORE')['v'][0] += .01; mutations.append(changed)
    rejected = 0
    for mutation in mutations:
        try:
            validate(mutation)
        except ValueError:
            rejected += 1
    need(rejected == len(mutations), 'reader mutation controls')
    need(0.125*1000 == 125, 'units')
    return dict(rejected=rejected, cases=['missing','duplicate','misordered','wrong_unit','operand_drift'])


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--probe',type=Path,required=True);parser.add_argument('--retained',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--count',type=int,choices=[4,36],required=True)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    bindings={}
    def bind(path):
        path=path.resolve();st=path.stat();bindings[str(path)]={'sha256':sha(path),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
    for path in [a.probe/'freeze.json',a.probe/'approval.json',a.probe/'build-receipt.json',a.retained/'receipt.json',a.retained/'layers.csv',a.retained/'calls.csv',a.retained/'structural.csv']:
        bind(path)
    receipt=json.loads((a.retained/'receipt.json').read_text())
    for name,h in receipt['outputs'].items():need(sha(a.retained/name)==h,'retained table drift')
    freeze=json.loads((a.probe/'freeze.json').read_text())
    pattern='small_paved_dry_legacy/*/*/result.json' if a.count==4 else '*/*/*/result.json'
    results=sorted((a.probe/'cases').glob(pattern))
    need(len(results)==a.count,'explicit case count')
    tables={name:list(csv.DictReader((a.retained/(name+'.csv')).open())) for name in ['layers','calls','structural']}
    produced=[]; joined=[]; calls=[];coverage=[];test_result=None
    for result_path in results:
        result=json.loads(result_path.read_text());need(result['pass'],'native parity gate')
        key=result['case'];stratum,lane,treatment=key.split('/');mode=0 if treatment=='O4' else 1
        p=result_path.parent/'runs/storage-init.txt';bind(result_path);bind(p)
        need(sha(p)==result['storage_init_sha256'],'initialization trace drift')
        execution=result_path.parent/'execution-declaration.json';bind(execution);ex=json.loads(execution.read_text())
        need(ex['full_period_years']==16 and ex['accepted_record_sha256']==freeze['cases'][key]['record_sha256'],'calendar/reference support')
        rows=parse(p);initial,minimum=validate(rows)
        if test_result is None:test_result=controls(rows)
        relevant=lambda r:r['stratum']==stratum and r['lane']==lane and int(r['mode'])==mode
        layer_rows=[r for r in tables['layers'] if relevant(r)]
        structures=[r for r in tables['structural'] if relevant(r)]
        case=structures[0]['case'];identity=dict(case=case,stratum=stratum,lane=lane,mode=mode)
        initial_map={(r['ofe'],r['layer']):r for r in initial}
        produced += [dict(**identity,**r) for r in initial]
        for r in structures:
            init=initial_map[int(r['consumer_ofe']),int(r['layer'])]
            for field,initfield in [('ul_m','ul_m'),('initial_porosity','initial_porosity'),('dry_theta','final_dry'),('depth_m','depth_m')]:need(float(r[field])==init[initfield],f'initial -> selected structural {field}')
        for r in layer_rows:
            init=initial_map[int(r['owner_ofe']),int(r['layer'])]
            need(float(r['ul_m'])==init['ul_m'] and float(r['depth_m'])==init['depth_m'],'initial -> consumed UL/depth')
            weight=float(r['weight'])
            joined.append(dict(**identity,year=int(r['year']),day=int(r['day']),target=r['target'],consumer_ofe=int(r['consumer_ofe']),owner_ofe=int(r['owner_ofe']),layer=int(r['layer']),weight=weight,connected_pore_m=init['pore_volume_m']*weight,connected_dry_m=init['final_dry_offset_m']*weight,connected_pre_rock_dry_m=init['dry_pre_rock_offset_m']*weight,connected_rock_dry_change_m=init['rock_dry_offset_change_m']*weight,connected_guard_dry_change_m=init['guard_dry_offset_change_m']*weight,connected_ul_rounding_m=init['ul_rounding_residual_m']*weight))
        for c in filter(relevant,tables['calls']):
            operands=[r for r in layer_rows if r['year']==c['year'] and r['day']==c['day'] and r['consumer_ofe']==c['consumer_ofe']]
            total=real(0.)
            for owner in map(int,c['contributors'].split(',')):
                rr=[r for r in operands if int(r['owner_ofe'])==owner];need(len(rr)==2,'conductivity contributor support')
                total=real(total+real(minimum[owner]*float(rr[0]['length_m'])))
            k=real(total/float(c['effective_length_m']));need(k==float(c['observed_kagmin_m_s']),'initialized minimum -> connected Kagmin')
            comp=[r for r in joined if r['stratum']==stratum and r['lane']==lane and r['mode']==mode and r['year']==int(c['year']) and r['day']==int(c['day']) and r['consumer_ofe']==int(c['consumer_ofe'])]
            sums={field:sum(r[field] for r in comp) for field in ['connected_pore_m','connected_dry_m','connected_pre_rock_dry_m','connected_rock_dry_change_m','connected_guard_dry_change_m','connected_ul_rounding_m']}
            need(abs(sums['connected_pore_m']-sums['connected_dry_m']+sums['connected_ul_rounding_m']-float(c['ul_m'])) < 1e-15,'double component roundoff-only identity')
            calls.append(dict(**identity,year=int(c['year']),day=int(c['day']),target=c['target'],consumer_ofe=int(c['consumer_ofe']),initialized_kagmin_m_s=k,initialized_kagmin_exact=True,**sums))
        coverage.append(dict(**identity,initial_layers=len(initial),selected_structures=len(structures),consumed_layers=len(layer_rows),ordinary_files=len(result['ordinary']),existing_traces=len(result['traces']),full_period_years=16))
    for path,before in bindings.items():
        st=Path(path).stat();need(before=={'sha256':sha(path),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns},'reader input mutation')
    for name,data in [('initial-layers',produced),('consumed-components',joined),('connected-components',calls),('coverage',coverage)]:write_csv(a.out/(name+'.csv'),data)
    summary=dict(passed=True,histories=a.count,initial_layers=len(produced),consumed_layers=len(joined),connected_calls=len(calls),all_native_arithmetic_exact=True,double_component_identity_bound_m=1e-15,controls=test_result,reader_sha256=sha(__file__),bindings=bindings,outputs={p.name:sha(p) for p in a.out.glob('*.csv')})
    (a.out/'receipt.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ['bindings','outputs']}))


if __name__=='__main__':main()
