"""Read immutable histories; separate reset assignments from inherited mismatch."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy
import struct

OLD = Path('out/frozen-water-history-20261101')
PUB = Path('docs/work-packages/20261101_frozen_water_history_ownership/artifacts')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


def stock(layer):
    if not layer['available']:
        return None
    fine = layer['fine'].values()
    liquid = math.fsum(f['sw'] * f['u'] for f in fine) + layer['nw']
    ice = math.fsum(f['ice'] for f in fine)
    target = math.fsum(layer['dry'] * f['u'] for f in fine)
    return dict(liquid=liquid, ice=ice, total=liquid + ice,
                dry_target=target, available=liquid-target)


def decompose(before, after):
    if before['st'] != 0 or not before['available'] or not after['available']:
        raise ValueError('Not an available zero-ST reset')
    if before['n'] != after['n'] or before['fine'].keys() != after['fine'].keys():
        raise ValueError('Fine support changed')
    if after['nw'] != 0:
        raise ValueError('Zero reset left NWFRZZ')
    for j, a in before['fine'].items():
        b = after['fine'][j]
        if b['sw'] != before['dry'] or any(a[k] != b[k] for k in ('f', 'ice', 'u')):
            raise ValueError('Unexpected reset assignment or ice/support mutation')
    for key in ('dg', 'dry', 'ul', 'st', 'yst', 'frzw', 'frozen', 'soilw', 'saxfc'):
        if before[key] != after[key]:
            raise ValueError('Coarse field mutation in reset: ' + key)
    a, b = stock(before), stock(after)
    request = f32(before['st'] - before['yst'])
    change = b['total'] - a['total']
    inherited = before['yst'] - a['available']
    residual = change - request
    reset_error = b['liquid'] - a['dry_target']
    coarse_reference = before['yst'] + before['frzw'] + before['dry'] * before['dg']
    reference_mismatch = coarse_reference - a['total']
    coordinate_offset = a['dry_target'] + a['ice'] - (before['frzw'] + before['dry'] * before['dg'])
    k = 16 * before['n'] + 96
    gamma = k * 2**-53 / (1-k*2**-53)
    bound = 4 * gamma * math.fsum(abs(v) for v in [a['liquid'], b['liquid'], a['ice'], b['ice'], before['yst'], request, a['dry_target'], coarse_reference])
    errors = [reset_error, b['ice']-a['ice'], residual-inherited-reset_error,
              inherited-reference_mismatch-coordinate_offset]
    if any(abs(error) > bound for error in errors):
        raise ValueError('Assignment/decomposition reconstruction failed')
    return dict(before=a, after=b, coarse_ST=before['st'], coarse_YST=before['yst'],
                reconstructed_request_m=request, request_observed=False, fine_change_m=change,
                nominal_residual_m=residual, inherited_reference_mismatch_m=inherited,
                coarse_reference_mismatch_m=reference_mismatch, coordinate_offset_m=coordinate_offset,
                reset_assignment_error_m=reset_error, reconstruction_bound_m=bound,
                negative_fine_component=min(a['liquid'], a['ice'], b['liquid'], b['ice']) < 0,
                negative_coarse_component=(before['st']+before['dry']*(before['dg']-before['frozen']) < 0
                                          or before['frzw']+before['dry']*before['frozen'] < 0))


def main(scenario, out, declaration):
    declared = json.loads(declaration.read_text())
    files = declared['files']
    for path, digest in files.items():
        if sha(Path(path)) != digest:
            raise ValueError('Declared dependency drift: ' + path)
    reader = runpy.run_path(str(PUB / 'read_history.py'))
    trace = OLD / 'campaign-v1' / scenario / 'observer/runs/frwatc-history.txt'
    pair = json.loads((trace.parents[2] / 'receipt.json').read_text())
    if not pair['accepted'] or sha(trace) != pair['members'][1]['trace']['trace_sha256']:
        raise ValueError('Unaccepted or changed retained trace')
    supplement = json.loads((OLD / 'all-clearing-v3' / scenario / 'receipt.json').read_text())
    starts = {(r['event']['map'], r['layer']): r for r in supplement['clears']}
    endpoints = {r['id']: r['event']['seq'] for r in supplement['endpoints']}
    out.mkdir(parents=True, exist_ok=False)
    active = {}
    pending = {}
    counts = dict(mode1_maps=0, zero_layers=0, nonzero_layers=0, unavailable_zero_layers=0,
                  clearing_ids_started=0, clearing_ids_closed=0)
    ranges = {}
    def extent(key, value):
        row = ranges.setdefault(key, dict(count=0, min=value, max=value))
        row['count'] += 1
        row['min'] = min(row['min'], value)
        row['max'] = max(row['max'], value)
    with (out / 'resets.jsonl').open('x') as resets, (out / 'sequences.jsonl').open('x') as sequence:
        for event in reader['events'](trace):
            tag = event['tag']
            if tag == 'FOOTER':
                if active or pending:
                    raise ValueError('Unfinished mapping or clearing sequence')
                continue
            ofe = event['ofe']
            if tag == 'MAP_PRE':
                if ofe in active:
                    raise ValueError('Nested map')
                active[ofe] = dict(pre=event, zero=set(), requests=set())
            elif tag in {'D1_ZERO', 'D1_REQUEST'}:
                target = active[ofe]
                if target['pre']['map'] != event['map']:
                    raise ValueError('Branch identity drift')
                layer = event['other'][0][1]
                target['zero' if tag == 'D1_ZERO' else 'requests'].add(layer)
            elif tag == 'MAP_POST':
                target = active.pop(ofe)
                pre = target['pre']
                if any(pre[k] != event[k] for k in ('map', 'year', 'day', 'hour', 'mode', 'nsl', 'parent', 'epoch')):
                    raise ValueError('Return identity drift')
                if pre['mode'] == 1:
                    counts['mode1_maps'] += 1
                    if target['zero'] & target['requests'] or target['zero'] | target['requests'] != set(pre['layers']):
                        raise ValueError('Missing/overlapping layer branch coverage')
                    counts['nonzero_layers'] += len(target['requests'])
                    for layer in sorted(target['zero']):
                        a, b = pre['layers'][layer], event['layers'][layer]
                        if not a['available'] or not b['available']:
                            counts['unavailable_zero_layers'] += 1
                            continue
                        result = decompose(a, b)
                        counts['zero_layers'] += 1
                        for key in ('nominal_residual_m', 'inherited_reference_mismatch_m', 'reset_assignment_error_m', 'fine_change_m', 'coordinate_offset_m'):
                            extent(key, result[key])
                        resets.write(json.dumps(dict(event=reader['identity'](pre), layer=layer, **result))+'\n')
                for layer in event['layers']:
                    clear = starts.get((event['map'], layer))
                    if clear:
                        pending.setdefault((ofe, layer), []).append(clear['id'])
                        counts['clearing_ids_started'] += 1
            if tag in reader['SNAPSHOTS']:
                for layer, data in event['layers'].items():
                    ids = pending.get((ofe, layer), [])
                    if not ids:
                        continue
                    # Write one observed state with all referencing identities, avoiding invented disjoint transfers.
                    payload = dict(tag=tag, event=reader['identity'](event), layer=layer, clearing_ids=list(ids),
                                   coarse={k:data[k] for k in reader['COARSE']}, fine=stock(data))
                    sequence.write(json.dumps(payload)+'\n')
                    if tag == 'INIT_POST':
                        for identifier in ids:
                            if endpoints[identifier] != event['seq']:
                                raise ValueError('Next initialization join drift')
                        counts['clearing_ids_closed'] += len(ids)
                        pending.pop((ofe, layer))
    if counts['clearing_ids_started'] != len(starts) or counts['clearing_ids_closed'] != len(starts):
        raise ValueError('Incomplete clearing coverage')
    if sha(trace) != pair['members'][1]['trace']['trace_sha256']:
        raise ValueError('Retained trace changed')
    for path, digest in files.items():
        if sha(Path(path)) != digest:
            raise ValueError('Dependency changed during readback')
    receipt = dict(scenario=scenario, counts=counts, ranges=ranges, trace_sha256=sha(trace),
                   declaration_sha256=sha(declaration), outputs={p.name:sha(p) for p in out.iterdir()},
                   limitation='Net coarse changes do not identify accepted fluxes or individual internal writers.')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(scenario=scenario,counts=counts,ranges=ranges)))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scenario');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--declaration',type=Path,required=True)
    a=p.parse_args();main(a.scenario,a.out,a.declaration)
