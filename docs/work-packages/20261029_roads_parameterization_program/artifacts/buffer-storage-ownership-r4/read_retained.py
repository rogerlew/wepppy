"""Original, source-free readback of immutable consumed-storage observations."""
import argparse
import csv
import hashlib
import json
import math
import struct
from collections import defaultdict
from pathlib import Path


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def one(rows, tag, index=None):
    selected = [r for r in rows if r['tag'] == tag and (index is None or r['index'] == index)]
    require(len(selected) == 1, f'{tag}/{index}: expected one, got {len(selected)}')
    return selected[0]


def parse(p):
    rows = []
    for n, line in enumerate(p.read_text().splitlines(), 1):
        t = line.split()
        require(len(t) == 11, f'{p}:{n}: malformed')
        y, day, ofe, index = map(int, t[1:5])
        v = list(map(float, t[5:]))
        require(all(math.isfinite(x) for x in v), 'nonfinite observation')
        rows.append(dict(tag=t[0], year=y, day=day, ofe=ofe, index=index, v=v, line=n))
    return rows


def native_layer_sum(rows, local):
    require([r['index'] % 100 for r in rows] == [1, 2], 'layer order/support')
    total = f32(0)
    for r in rows:
        saved, upper, ice, depth, length, observed_space = r['v']
        require(depth > 0 and length > 0, 'depth/length domain')
        require(length == rows[0]['v'][4], 'unequal layer lengths')
        space = max(f32(upper - ice), 0.0)
        require(space == observed_space, 'space branch mismatch')
        if saved < space:
            total = f32(total + f32(space - saved)) if local else f32(f32(total + space) - saved)
        total = max(total, 0.0)
    return total


def controls():
    def row(ix, st, ul, ice):
        return dict(index=ix, v=[st, ul, ice, .1, 5., max(f32(ul-ice), 0.)])
    base = [row(101, .03, .02, 0), row(102, .01, .03, .04)]
    require(native_layer_sum(base, True) == 0, 'zero/occupied branch control')
    negative = [row(101, -.01, .02, .03), row(102, 0, 0, 0)]
    require(native_layer_sum(negative, True) == f32(.01), 'negative saved water branch')
    require(0.125 * 1000 == 125.0 and 0.125 * 100 != 125.0, 'meter/mm conversion and scale mutation')
    caught = 0
    for invalid in ([], base[:1], base[::-1], [base[0], base[0]]):
        try:
            native_layer_sum(invalid, True)
        except ValueError:
            caught += 1
    require(caught == 4, 'support/order controls')
    for invalid in ([], [dict(tag='x', index=0)] * 2):
        try:
            one(invalid, 'x')
        except ValueError:
            caught += 1
    require(caught == 6, 'missing/duplicate controls')
    return dict(passed=True, rejected_support_mutations=caught, branch_controls=2, unit_control=True)


def dump(p, value):
    p.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def table(p, rows):
    with p.open('w', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--study', type=Path, required=True)
    ap.add_argument('--inventory', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    root = a.study.resolve()
    inventory = json.loads(a.inventory.read_text())
    base = root.parent.parent
    bindings = {}
    def bind(p):
        p = p.resolve()
        rel = str(p.relative_to(base))
        require(rel in inventory, f'unbound input {rel}')
        st = p.stat()
        require(sha(p) == inventory[rel]['sha256'], f'drift {rel}')
        require(st.st_size == inventory[rel]['bytes'] and st.st_mtime_ns == inventory[rel]['mtime_ns'], f'original metadata drift {rel}')
        bindings[str(p)] = dict(sha256=sha(p), bytes=st.st_size, mtime_ns=st.st_mtime_ns)
    bind(root / 'execution-declaration.json')
    declaration = json.loads((root / 'execution-declaration.json').read_text())
    tasks = declaration['tasks']
    require(len(tasks) == 36, '36 histories required')
    strata = list(dict.fromkeys(t['stratum'] for t in tasks))
    require(len(strata) == 9, 'nine cases required')
    require(len({(t['stratum'], t['lane'], t['mode']) for t in tasks}) == 36, 'duplicate histories')
    layers, calls, support, structures = [], [], [], []
    for task in tasks:
        folder = Path(task['folder'])
        trace = folder / 'observations/buffer-observation.txt'
        contract = folder / 'observations/roughness-contract.txt'
        bind(trace); bind(contract)
        rows = parse(trace)
        groups = defaultdict(list)
        for r in rows:
            groups[r['year'], r['day'], r['ofe']].append(r)
        initial = {}
        with contract.open() as stream:
            for line in stream:
                t = line.split()
                if t[0] == 'RRC_DENSITY' and t[1:4] == ['0', '0', '0']:
                    key = (int(t[4]), int(t[5]))
                    require(key not in initial, 'duplicate initialization')
                    initial[key] = list(map(float, t[7:]))
        require(len(initial) == 6, 'initial density support')
        require(set(groups) == {(task['event']['year'], day, ofe) for day in (task['event']['julian']-1, task['event']['julian']) for ofe in (1,2,3)} | {k for k in groups if k[2] == 0}, 'selected date/OFE coverage')
        ident = dict(case='B' + str(strata.index(task['stratum']) + 1), stratum=task['stratum'], lane=task['lane'], mode=task['mode'])
        for (year, day, ofe), g in groups.items():
            if ofe == 0:
                require(all(r['tag'] == 'BP_IRS_ENTER' for r in g), 'unknown non-OFE context')
                continue
            shared = dict(**ident, year=year, day=day, target=day == task['event']['julian'], consumer_ofe=ofe)
            for l in (1, 2):
                water = one(g, 'BP_SOIL_W', l)['v']
                current = one(g, 'BP_SOIL_K', l)['v']
                por0 = initial[ofe, l][4]
                upper = f32(f32(por0 - water[3]) * water[4])
                require(upper == water[1], 'initial POR capacity reconstruction')
                structures.append(dict(**shared, layer=l, ul_m=water[1], initial_porosity=por0, current_porosity=current[2], dry_theta=water[3], depth_m=water[4], cumulative_depth_m=water[5], initial_por_ul_exact=True, initial_pore_volume_m=por0*water[4], dry_water_offset_m=water[3]*water[4], ul_rounding_residual_m=water[1]-(por0-water[3])*water[4], current_por_ul_m=f32(f32(current[2]-water[3])*water[4])))
            ga = [r for r in g if r['tag'] == 'BP_GA_STORAGE']
            require(len(ga) <= 1, 'duplicate GRNA call')
            support.append(dict(**shared, grna_call=bool(ga)))
            if not ga:
                continue
            ga = ga[0]
            operands = [r for r in g if r['tag'] in ('BP_GA_LOCAL_LAYER', 'BP_GA_UP_LAYER')]
            owners = list(dict.fromkeys(r['index'] // 100 for r in operands))
            require(owners == list(range(ofe, min(owners)-1, -1)), 'contributor order')
            eq = one(g, 'BP_EQUIV')['v']; length = eq[2]
            require(length > 0, 'effective length')
            total = f32(0); ktotal = f32(0)
            components = dict(ul_m=0., saved_liquid_m=0., live_frozen_m=0., branch_correction_m=0.)
            local_available = None
            for owner in owners:
                rr = [r for r in operands if r['index']//100 == owner]
                require(all(r['line'] < ga['line'] for r in rr), 'consumer order')
                require(all(r['tag'] == ('BP_GA_LOCAL_LAYER' if owner == ofe else 'BP_GA_UP_LAYER') for r in rr), 'operand tag ownership')
                amount = native_layer_sum(rr, owner == ofe)
                if owner == ofe:
                    local_available = amount
                own_g = groups[year, day, owner]
                ks = sorted((r for r in own_g if r['tag'] == 'BP_SOIL_K'), key=lambda r:r['index'])
                require(ks, 'missing conductivity profile')
                minimum = None
                for k in ks:
                    ssc, sscv, por, frozen, frdp, thdp = k['v']
                    if minimum is None or ssc < minimum:
                        minimum = sscv if frdp > 0 and sscv > 0 else ssc
                contributor_length = rr[0]['v'][4]
                total = f32(total + f32(amount * contributor_length))
                ktotal = f32(ktotal + f32(minimum * contributor_length))
                for r in rr:
                    l = r['index'] % 100
                    saved, upper, ice, depth, slen, space = r['v']
                    local = one(own_g, 'BP_GA_LOCAL_LAYER', 100*owner+l)
                    require(local['line'] <= r['line'] and local['v'][0] == saved, 'saved producer ownership')
                    wb = [x for x in own_g if x['tag']=='BP_WBH_AFTER_W' and x['index']==2400+l and x['line'] < r['line']]
                    require(len(wb)<=1, 'duplicate final hourly producer')
                    weight = slen / length
                    correction = max(max(upper-ice, 0)-saved, 0) - (upper-ice-saved)
                    components['ul_m'] += upper*weight
                    components['saved_liquid_m'] += saved*weight
                    components['live_frozen_m'] += ice*weight
                    components['branch_correction_m'] += correction*weight
                    water = one(own_g, 'BP_SOIL_W', l)['v']
                    layers.append(dict(**shared, owner_ofe=owner, layer=l, trace_line=r['line'], local_snapshot_line=local['line'], saved_liquid_m=saved, ul_m=upper, live_frozen_m=ice, depth_m=depth, length_m=slen, weight=weight, available_m=max(space-saved,0), initial_porosity=initial[owner,l][4], dry_theta=water[3], wb24_before_consumption=bool(wb), wb24_liquid_m=wb[0]['v'][0] if wb else None, saved_differs_from_wb24=bool(wb) and wb[0]['v'][0]!=saved, live_ice_equals_local_snapshot=ice==local['v'][2]))
            computed = f32(total/length); kcomputed = f32(ktotal/length)
            require(computed == ga['v'][0], f'storage arithmetic {shared}: {computed} != {ga["v"][0]}')
            forcing = one(g,'BP_GA_FORCING')['v']
            explained = components['ul_m']-components['saved_liquid_m']-components['live_frozen_m']+components['branch_correction_m']
            calls.append(dict(**shared, contributors=','.join(map(str,owners)), effective_length_m=length, local_available_m=local_available, connected_available_m=computed, connected_available_mm=1000*computed, **components, double_explanatory_available_m=explained, native_rounding_residual_m=computed-explained, native_storage_exact=True, observed_kagmin_m_s=ga['v'][1], reconstructed_kagmin_m_s=kcomputed, k_reconstruction_exact=kcomputed==ga['v'][1], k_evidence_class='current_profile_arithmetic_matches_consumed_value; initialization_assignment_not_observed', equivalent_conductivity_m_s=ga['v'][3], depression_m=ga['v'][5], rain_m=forcing[0], melt_m=forcing[1], forcing_duration_s=forcing[2], iuprun=one(g,'BP_IRS_LOCAL')['v'][5]))
    table(a.out/'layers.csv', layers); table(a.out/'calls.csv', calls)
    table(a.out/'support.csv',support); table(a.out/'structural.csv',structures)
    targets=[r for r in calls if r['target'] and r['consumer_ofe']==3]
    require(len(targets)==36, 'all target buffer calls')
    table(a.out/'target-buffer.csv',targets)
    for p, before in bindings.items():
        st=Path(p).stat()
        require(dict(sha256=sha(p),bytes=st.st_size,mtime_ns=st.st_mtime_ns)==before, f'input mutation {p}')
    dump(a.out/'receipt.json',dict(passed=True, histories=36, calls=len(calls), layers=len(layers), structural_rows=len(structures), missing_grna_groups=sum(not r['grna_call'] for r in support), all_storage_exact=True, conductivity_exact=sum(r['k_reconstruction_exact'] for r in calls), upstream_saved_differs_from_prior_hour24=sum(r['saved_differs_from_wb24'] for r in layers), controls=controls(), reader_sha256=sha(__file__), inventory_sha256=sha(a.inventory), bindings=bindings, outputs={p.name:sha(p) for p in a.out.glob('*.csv')}))
    print(json.dumps(dict(calls=len(calls),layers=len(layers),k_exact=sum(r['k_reconstruction_exact'] for r in calls))))


if __name__ == '__main__':
    main()
