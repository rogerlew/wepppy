"""Strict streaming reader for FH_SCHEMA 1; no model conservation tolerance."""
import argparse
from collections import Counter
import hashlib
import json
import math
import struct
from pathlib import Path

COARSE = 'dg dry ul st frzw frozen soilw yst nw saxfc'.split()
SNAPSHOTS = {'MAP_PRE', 'MAP_POST', 'INIT_PRE', 'INIT_POST',
             'FROST_BLOCK_PRE', 'FROST_BLOCK_POST', 'DAY_WIN_GATE',
             'WIN_PRE', 'WIN_POST', 'WB_PRE', 'WB_POST',
             'IRS_WB_PRE', 'IRS_WB_POST'}
MARKS = {'FN_INIT', 'FN_READY', 'WINTER_HOUR', 'WEATHER_ELIGIBLE',
         'FROST_CALL', 'FROST_DONE', 'WB_PATH'}
BRANCHES = set('D0_START D0_LAYER D0_SUPPORT D0_DRY_FLOOR D0_DRY_CLEAR '
               'D0_CLEAR_PRE D0_CLEAR_POST D0_FINISH D1_START D1_LAYER '
               'D1_ZERO D1_REQUEST D1_ABS_ACTIVE D1_NW_DRAIN D1_NW_AFTER '
               'D1_DRAIN_SUPPORT D1_DRAIN_CAP D1_DRAIN_AFTER D1_ADD '
               'D1_FROZEN_ROOM D1_FROZEN_ALLOC D1_SMALL_FROZEN '
               'D1_TOTAL_U D1_VOL_REQUEST D1_VOL_ACTIVE D1_UPDATE_SUPPORT '
               'D1_CARRY_APPLY D1_NEW_CARRY D1_UPDATE_END D1_END D1_FINISH'.split())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def numbers(values):
    result = [float(value) for value in values]
    if not all(math.isfinite(value) for value in result):
        raise ValueError('Nonfinite observation')
    return result


def validate(event):
    tag = event['tag']
    if tag in SNAPSHOTS:
        if event['other'] or set(event['layers']) != set(range(1, event['nsl'] + 1)):
            raise ValueError('Missing coarse support or unexpected payload')
        for layer in event['layers'].values():
            if set(layer['fine']) != set(range(1, layer['n'] + 1)):
                raise ValueError('Missing fine support')
    elif event['layers'] or len(event['other']) != 1:
        raise ValueError('Missing/duplicate event payload')
    elif tag in MARKS and event['other'][0][0] != 'V':
        raise ValueError('Wrong marker payload')
    elif tag in BRANCHES and event['other'][0][0] not in {'B', 'G'}:
        raise ValueError('Wrong branch payload')
    return event


def events(path):
    """Require contiguous event IDs, complete support and a terminal footer."""
    event = None
    sequence = 0
    footer = False
    with path.open() as stream:
        if stream.readline().strip() != 'FH_SCHEMA 1':
            raise ValueError('Unknown schema')
        for line in stream:
            c = line.split()
            if not c or footer:
                raise ValueError('Empty/trailing record')
            if c[0] == 'E':
                if event is not None:
                    yield validate(event)
                if len(c) != 12 or c[1] not in SNAPSHOTS | MARKS | BRANCHES:
                    raise ValueError('Unknown event/shape')
                keys = 'seq map year day ofe hour mode nsl parent epoch'.split()
                event = dict(zip(keys, map(int, c[2:])))
                sequence += 1
                if event['seq'] != sequence:
                    raise ValueError('Noncontiguous event sequence')
                if not (1 <= event['ofe'] <= 100 and 1 <= event['nsl'] <= 10
                        and 1 <= event['year'] <= 16 and 1 <= event['day'] <= 366
                        and 0 <= event['hour'] <= 24 and event['parent'] >= 0
                        and event['epoch'] >= 0 and event['map'] >= 0):
                    raise ValueError('Invalid clock/support/identity')
                if event['day'] == 366 and event['year'] % 4:
                    raise ValueError('Invalid leap-day clock')
                event.update(tag=c[1], layers={}, other=[])
            elif c[0] == 'FH_END':
                if len(c) != 3 or int(c[1]) != sequence or event is None:
                    raise ValueError('Bad footer')
                yield validate(event)
                event = None
                footer = True
                yield {'tag': 'FOOTER', 'seq': sequence, 'maps': int(c[2])}
            else:
                if event is None or len(c) < 2 or int(c[1]) != sequence:
                    raise ValueError('Orphan payload')
                if c[0] == 'C':
                    if len(c) != 15:
                        raise ValueError('Bad coarse shape')
                    i, n, available = map(int, c[2:5])
                    if i in event['layers'] or not 1 <= i <= event['nsl']:
                        raise ValueError('Duplicate/invalid coarse support')
                    if available not in (0, 1) or not (1 <= n <= 10 if available else n == 0):
                        raise ValueError('Invalid fine availability')
                    event['layers'][i] = dict(zip(COARSE, numbers(c[5:])),
                                               n=n, available=available, fine={})
                elif c[0] == 'F':
                    if len(c) != 8:
                        raise ValueError('Bad fine shape')
                    i, j = map(int, c[2:4])
                    if i not in event['layers']:
                        raise ValueError('Orphan fine layer')
                    layer = event['layers'][i]
                    if j in layer['fine'] or not 1 <= j <= layer['n']:
                        raise ValueError('Duplicate/invalid fine support')
                    layer['fine'][j] = dict(zip(['f', 'sw', 'ice', 'u'], numbers(c[4:])))
                elif c[0] in {'B', 'G', 'V'}:
                    sizes = {'B': 10, 'G': 4, 'V': 3}
                    if len(c) != sizes[c[0]]:
                        raise ValueError('Bad branch/marker shape')
                    if c[0] == 'V':
                        event['other'].append(('V', int(c[2])))
                    else:
                        i, j = map(int, c[2:4])
                        if not 0 <= i <= event['nsl'] or not 0 <= j <= 10:
                            raise ValueError('Bad branch support')
                        event['other'].append((c[0], i, j, numbers(c[4:])))
                else:
                    raise ValueError('Unknown record')
    if not footer:
        raise ValueError('Missing footer/truncated observation')


def stocks(layer):
    coarse_liquid = layer['st'] + layer['dry'] * (layer['dg'] - layer['frozen'])
    coarse_ice = layer['frzw'] + layer['dry'] * layer['frozen']
    result = dict(coarse_liquid=coarse_liquid, coarse_ice=coarse_ice,
                  coarse_total=coarse_liquid + coarse_ice,
                  soilw_minus_coarse_liquid=layer['soilw'] - coarse_liquid)
    if layer['available']:
        fine = layer['fine'].values()
        liquid = math.fsum(f['sw'] * f['u'] for f in fine) + layer['nw']
        ice = math.fsum(f['ice'] for f in fine)
        result.update(fine_liquid=liquid, fine_ice=ice, fine_total=liquid + ice,
                      geometry_residual=math.fsum(f['f'] + f['u'] for f in fine) - layer['dg'])
    if not all(math.isfinite(x) for x in result.values()):
        raise ValueError('Nonfinite reconstructed stock')
    return result


def identity(event):
    return {k: event[k] for k in ('seq', 'map', 'year', 'day', 'ofe', 'hour', 'parent', 'epoch')}


def read(path, transfers_path=None, ledger_path=None):
    counts = Counter()
    ranges = {}
    active = {}
    parents = {}
    clocks = {}
    daily_keys = set()
    last_map = 0
    map_count = 0
    pending = {}
    ownership_counts = Counter()
    signature_counts = Counter()
    examples = {}
    outputs = []
    if transfers_path:
        outputs.append(transfers_path.open('x'))
    if ledger_path:
        outputs.append(ledger_path.open('x'))
    transfer_stream = outputs[0] if transfers_path else None
    ledger_stream = outputs[-1] if ledger_path else None

    def emit(stream, row):
        if stream:
            stream.write(json.dumps(row, allow_nan=False) + '\n')

    def extent(key, value):
        record = ranges.setdefault(key, dict(count=0, min=value, max=value))
        record['count'] += 1
        record['min'] = min(record['min'], value)
        record['max'] = max(record['max'], value)

    def signature(name, event, layer, details):
        signature_counts[name] += 1
        examples.setdefault(name, dict(event=identity(event), layer=layer, **details))

    try:
        for event in events(path):
            tag = event['tag']
            counts[tag] += 1
            if tag == 'FOOTER':
                if active or parents or event['maps'] != map_count:
                    raise ValueError('Unmatched map/call or footer map count')
                continue
            ofe = event['ofe']
            clock = event['year'], event['day']
            if clock < clocks.get(ofe, clock):
                raise ValueError('Reversed daily clock')
            clocks[ofe] = clock
            if tag == 'FROST_CALL':
                if ofe in parents or event['parent']:
                    raise ValueError('Nested frost invocation')
                parents[ofe] = event['seq']
            elif event['parent'] != parents.get(ofe, 0):
                raise ValueError('Frost parent drift')
            if tag == 'FROST_DONE':
                if ofe not in parents:
                    raise ValueError('Unmatched frost return')
                del parents[ofe]
            if tag == 'DAY_WIN_GATE':
                day_key = (ofe, event['day'], event['year'])
                if day_key in daily_keys:
                    raise ValueError('Duplicate daily gate')
                daily_keys.add(day_key)
            if tag in MARKS:
                counts[f"{tag}:value={event['other'][0][1]}"] += 1
            if tag in SNAPSHOTS:
                for i, layer in event['layers'].items():
                    layer['stocks'] = stocks(layer)
                    layer['invalid'] = (layer['dg'] <= 0 or layer['frozen'] < 0
                        or layer['frozen'] > layer['dg'] or layer['nw'] < 0
                        or min(layer['stocks'][k] for k in ('coarse_liquid', 'coarse_ice', 'coarse_total')) < 0)
                    if layer['available']:
                        layer['invalid'] = layer['invalid'] or min(layer['stocks'][k]
                            for k in ('fine_liquid', 'fine_ice', 'fine_total')) < 0
                        layer['invalid'] = layer['invalid'] or any(
                            f['u'] < 0 or f['f'] < 0 or f['ice'] < 0 or f['sw'] < 0
                            for f in layer['fine'].values())
                    if layer['invalid']:
                        counts['invalid_layer_snapshots'] += 1
                        examples.setdefault('invalid_state', dict(event=identity(event), layer=i,
                            dg=layer['dg'], frozen=layer['frozen'], nw=layer['nw'], stocks=layer['stocks']))
                    if not layer['available']:
                        counts['unavailable_layer_snapshots'] += 1
                    else:
                        for f in layer['fine'].values():
                            if f['u'] < 0 or f['f'] < 0 or f['ice'] < 0 or f['sw'] < 0:
                                counts['invalid_geometry_or_negative_fine_stock'] += 1
            if tag == 'MAP_PRE':
                if event['map'] != last_map + 1 or ofe in active or event['mode'] not in (0, 1):
                    raise ValueError('Map identity/order')
                last_map = event['map']
                active[ofe] = dict(pre=event, branches=[])
            elif tag in BRANCHES:
                if ofe not in active or event['map'] != active[ofe]['pre']['map']:
                    raise ValueError('Orphan branch')
                entry = active[ofe]['pre']
                if any(event[k] != entry[k] for k in ('year', 'day', 'hour', 'mode', 'nsl', 'parent', 'epoch')):
                    raise ValueError('Branch identity drift')
                if not tag.startswith('D' + str(entry['mode']) + '_'):
                    raise ValueError('Branch direction drift')
                active[ofe]['branches'].append(event)
            elif tag == 'MAP_POST':
                if ofe not in active:
                    raise ValueError('Orphan map return')
                mapping = active.pop(ofe)
                pre = mapping['pre']
                if any(pre[k] != event[k] for k in ('map', 'ofe', 'year', 'day', 'hour', 'mode', 'nsl', 'parent', 'epoch')):
                    raise ValueError('Map return identity drift')
                map_count += 1
                branches = mapping['branches']
                prefix = 'D' + str(pre['mode']) + '_'
                for suffix in ('START', 'FINISH'):
                    if sum(b['tag'] == prefix + suffix for b in branches) != 1:
                        raise ValueError('Missing/duplicate mapping boundary')
                layers_seen = [b['other'][0][1] for b in branches if b['tag'] == prefix + 'LAYER']
                if sorted(layers_seen) != list(range(1, pre['nsl'] + 1)):
                    raise ValueError('Missing/duplicate branch layer coverage')
                available_branches = [b for b in branches if b['other'][0][0] == 'B']
                counts['unavailable_branch_records'] += len(branches) - len(available_branches)
                by_layer = {}
                for b in available_branches:
                    by_layer.setdefault(b['other'][0][1], []).append(b)
                profile = []
                for i, before in pre['layers'].items():
                    after = event['layers'][i]
                    if not before['available'] or not after['available'] or before['n'] != after['n']:
                        counts['unavailable_mapping_layers'] += 1
                        continue
                    bs, ass = before['stocks'], after['stocks']
                    delta = ass['fine_total'] - bs['fine_total']
                    local = by_layer.get(i, [])
                    if any(b['other'][0][0] == 'G' and b['other'][0][1] in (0, i) for b in branches):
                        counts['unavailable_mapping_layers'] += 1
                        continue
                    tags = {b['tag'] for b in local}
                    request_reconstructed = before['st'] - before['yst']
                    request = struct.unpack('f', struct.pack('f', request_reconstructed))[0]
                    request_observed = next((b['other'][0][3][0] for b in local if b['tag'] == 'D1_REQUEST'), None)
                    if request_observed is not None:
                        request = request_observed
                    invalid = before['invalid'] or after['invalid']
                    residual = (ass['coarse_total'] - bs['fine_total'] if pre['mode'] == 0
                                else delta - request)
                    key = ("invalid_" if invalid else "") + f"direction_{pre['mode']}"
                    extent(key + '_residual_m', residual)
                    extent(key + '_fine_change_m', delta)
                    if not invalid:
                        profile.append(residual)
                    emit(transfer_stream, dict(event=identity(pre), layer=i, mode=pre['mode'],
                         before=bs, after=ass, request_m=request, fine_change_m=delta,
                         mapping_residual_m=residual, branch_tags=sorted(tags), invalid_state=invalid,
                         native_request_observed=request_observed,
                         request_double_reconstruction_m=request_reconstructed,
                         request_rounding_difference_m=request-request_reconstructed))
                    if invalid:
                        counts['invalid_mapping_layers_excluded_from_signatures'] += 1
                        continue
                    if pre['mode'] == 1 and request_observed is None and 'D1_ZERO' not in tags:
                        raise ValueError('Missing native request/zero-ST branch')
                    if pre['mode'] == 0:
                        thin = [f for f in before['fine'].values()
                                if 0 < f['u'] <= 0.0010000000474974513 and f['sw'] != before['dry']]
                        if thin:
                            signature('F_positive_thin_support', pre, i, dict(cells=len(thin), residual_m=residual))
                        clear_pre = [b['other'][0][3] for b in local if b['tag'] == 'D0_CLEAR_PRE']
                        clear_post = [b['other'][0][3] for b in local if b['tag'] == 'D0_CLEAR_POST']
                        if len(clear_pre) != 1 or len(clear_post) != 1:
                            raise ValueError('Missing/duplicate clearing boundary')
                        if clear_pre[0][0] > 0 and clear_post[0][0] == 0 and clear_pre[0][1] < 0.0010000000474974513:
                            signature('H_frozen_liquid_clear', pre, i, dict(cleared_m=clear_pre[0][0], fine_change_m=delta))
                            item = dict(id=f"{pre['map']}:{i}", event=identity(pre), layer=i,
                                        cleared_m=clear_pre[0][0], after=ass, observations=0)
                            pending.setdefault((ofe, i), []).append(item)
                            emit(ledger_stream, dict(kind='clear', **item))
                    else:
                        if 'D1_REQUEST' in tags and 'D1_ABS_ACTIVE' not in tags and request != 0:
                            signature('I_absolute_gate', pre, i, dict(request_m=request, residual_m=residual))
                        if 'D1_VOL_REQUEST' in tags and 'D1_VOL_ACTIVE' not in tags:
                            values = next(b['other'][0][3] for b in local if b['tag'] == 'D1_VOL_REQUEST')
                            if values[0] != 0:
                                signature('I_volumetric_gate', pre, i, dict(volumetric_request=values[0], residual_m=residual))
                        if any(b['tag'] == 'D1_UPDATE_SUPPORT' and b['other'][0][3][0] <= 0.0010000000474974513 for b in local):
                            signature('G_update_support_skip', pre, i, dict(residual_m=residual))
                if len(profile) == pre['nsl']:
                    extent(f"direction_{pre['mode']}_profile_residual_m", math.fsum(profile))
            # Every pending clearing keeps its own identity across later maps.
            # Bounded endpoints describe subsequent stocks, never restored-water causality.
            if tag in {'INIT_PRE', 'INIT_POST', 'FROST_BLOCK_PRE', 'FROST_BLOCK_POST',
                       'WIN_POST', 'WB_PRE', 'WB_POST', 'IRS_WB_PRE', 'IRS_WB_POST'}:
                for i, layer in event['layers'].items():
                    items = pending.get((ofe, i), [])
                    for item in items:
                        if item['observations'] < 12:
                            emit(ledger_stream, dict(kind='boundary', id=item['id'], tag=tag,
                                 event=identity(event), stocks=layer['stocks'],
                                 fine_available=bool(layer['available']),
                                 ownership='unresolved_composite_or_unobserved_writers'))
                            item['observations'] += 1
                    if tag == 'INIT_POST':
                        ownership_counts['clears_followed_to_next_initialization'] += len(items)
                        for item in items:
                            emit(ledger_stream, dict(kind='endpoint', id=item['id'], event=identity(event),
                                 stocks=layer['stocks'], fine_available=bool(layer['available']),
                                 ownership='initialization_endpoint_not_causal_recovery'))
                        pending.pop((ofe, i), None)
        unresolved = sum(map(len, pending.values()))
        for items in pending.values():
            for item in items:
                emit(ledger_stream, dict(kind='end_of_history', **item))
    finally:
        for stream in outputs:
            stream.close()
    return dict(trace_sha256=sha(path), counts=dict(counts), maps=map_count,
                signature_counts=dict(signature_counts), signature_examples=examples,
                signed_ranges=ranges, ownership_counts=dict(ownership_counts),
                clearing_events_without_next_initialization=unresolved,
                daily_gate_keys=sorted(daily_keys),
                limitations=['No annual water-loss sum; representation differences are not external fluxes.',
                             'Composite frost block and coarse boundaries do not isolate internal ownership.',
                             'Final VARWAT is not interpreted as unapplied water.',
                             'INIT_PRE epoch identifies target initialization, not prior-state provenance.',
                             'Missing fine provenance is unavailable, never zero.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    result = read(args.trace, args.out / 'transfers.jsonl', args.out / 'ownership.jsonl')
    (args.out / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
