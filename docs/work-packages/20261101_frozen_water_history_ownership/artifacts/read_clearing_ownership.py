"""Supplement accepted immutable traces with ALL actual clearing identities.

The execution reader deliberately excludes invalid coordinate states from physical
signatures. That exclusion must not erase observed assignments or later boundaries.
No native invocation or reinterpretation of ordinary-output acceptance occurs here.
"""
import argparse
import json
from pathlib import Path
from read_history import events, identity, sha, stocks


def state(layer):
    result = stocks(layer)
    result['fine_available'] = bool(layer['available'])
    result['negative_coarse_components'] = [k for k in ['coarse_liquid', 'coarse_ice'] if result[k] < 0]
    result['negative_fine_components'] = ([k for k in ['fine_liquid', 'fine_ice'] if result[k] < 0]
                                           if layer['available'] else None)
    result['negative_nw'] = layer['nw'] < 0
    result['invalid_geometry'] = layer['dg'] <= 0 or layer['frozen'] < 0 or layer['frozen'] > layer['dg']
    if layer['available']:
        result['invalid_fine_geometry'] = any(f['u'] < 0 or f['f'] < 0 for f in layer['fine'].values())
    return result


def extract(trace, ledger):
    active = {}
    pending = {}
    clears = []
    endpoints = []
    with ledger.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False) + '\n')
        for event in events(trace):
            tag = event['tag']
            if tag == 'FOOTER':
                if active:
                    raise ValueError('Unmatched mapping')
                continue
            ofe = event['ofe']
            if tag == 'MAP_PRE':
                if ofe in active:
                    raise ValueError('Nested mapping')
                active[ofe] = dict(pre=event, before_clear={}, after_clear={})
            elif tag in {'D0_CLEAR_PRE', 'D0_CLEAR_POST'}:
                current = active[ofe]
                payload = event['other'][0]
                if payload[0] == 'G':
                    raise ValueError('Unavailable clearing operands prevent complete ledger')
                if current['pre']['map'] != event['map']:
                    raise ValueError('Clearing map drift')
                target = current['before_clear' if tag.endswith('PRE') else 'after_clear']
                layer = payload[1]
                if layer in target:
                    raise ValueError('Duplicate clearing boundary')
                target[layer] = payload[3]
            elif tag == 'MAP_POST':
                current = active.pop(ofe)
                before = current['pre']
                if before['map'] != event['map']:
                    raise ValueError('Mapping return drift')
                if before['mode'] == 0:
                    if set(current['before_clear']) != set(before['layers']) or set(current['after_clear']) != set(before['layers']):
                        raise ValueError('Missing clearing operands')
                    for layer, operands in current['before_clear'].items():
                        after_operands = current['after_clear'][layer]
                        if operands[0] > 0 and after_operands[0] == 0 and operands[1] < 0.0010000000474974513:
                            record = dict(id=f"{before['map']}:{layer}", event=identity(before), layer=layer,
                                cleared_m=operands[0], actual_frozen_at_clear_m=operands[1],
                                before=state(before['layers'][layer]), after=state(event['layers'][layer]))
                            clears.append(record)
                            pending.setdefault((ofe, layer), []).append(dict(record=record, observed=0, init_pre=None))
                            emit(dict(kind='clear', **record))
            if tag in {'INIT_PRE', 'INIT_POST', 'FROST_BLOCK_PRE', 'FROST_BLOCK_POST',
                       'WIN_POST', 'WB_PRE', 'WB_POST', 'IRS_WB_PRE', 'IRS_WB_POST'}:
                for layer, data in event['layers'].items():
                    items = pending.get((ofe, layer), [])
                    if not items:
                        continue
                    observed = state(data)
                    for item in items:
                        if item['observed'] < 12 or tag in {'INIT_PRE', 'INIT_POST'}:
                            emit(dict(kind='boundary', id=item['record']['id'], tag=tag,
                                      event=identity(event), stocks=observed))
                            item['observed'] += 1
                        if tag == 'INIT_PRE':
                            item['init_pre'] = dict(event=identity(event), stocks=observed)
                        elif tag == 'INIT_POST':
                            endpoint = dict(id=item['record']['id'], event=identity(event), stocks=observed,
                                            initialization_pre=item['init_pre'],
                                            interpretation='Next initialization endpoint; causal recovery unproved')
                            if item['init_pre'] and observed['fine_available'] and item['init_pre']['stocks']['fine_available']:
                                endpoint['initialization_fine_change_m'] = observed['fine_total'] - item['init_pre']['stocks']['fine_total']
                            endpoints.append(endpoint)
                            emit(dict(kind='endpoint', **endpoint))
                    if tag == 'INIT_POST':
                        pending.pop((ofe, layer), None)
        unresolved = [item['record']['id'] for items in pending.values() for item in items]
        for identifier in unresolved:
            emit(dict(kind='unresolved_end_of_history', id=identifier))
    return dict(actual_clearings=len(clears), clears=clears, endpoints=endpoints,
                unresolved_ids=unresolved,
                limitation='Assignments and later stocks are observed; no annual loss or causal recovery sum.')


def main(scenario, out):
    pair = json.loads((scenario / 'receipt.json').read_text())
    if not pair['accepted']:
        raise ValueError('Cannot interpret unaccepted observer')
    trace = scenario / 'observer/runs/frwatc-history.txt'
    expected = pair['members'][1]['trace']['trace_sha256']
    if sha(trace) != expected:
        raise ValueError('Trace drift')
    out.mkdir(parents=True, exist_ok=False)
    result = extract(trace, out / 'all-clearing-ledger.jsonl')
    prior = set()
    with (scenario / 'observer/ownership.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['kind'] == 'clear':
                prior.add(row['id'])
    actual = {row['id'] for row in result['clears']}
    if not prior <= actual or len(actual) != result['actual_clearings']:
        raise ValueError('Prior identity omitted or duplicate clearing identity')
    result.update(scenario=scenario.name, trace_sha256=expected,
                  original_valid_state_ledger_count=len(prior),
                  previously_excluded_ids=sorted(actual - prior),
                  source_sha256=sha(Path(__file__)), ledger_sha256=sha(out / 'all-clearing-ledger.jsonl'))
    if sha(trace) != expected:
        raise ValueError('Trace changed during readback')
    (out / 'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(scenario=scenario.name, actual_clearings=len(actual),
                         previously_excluded=len(actual-prior), unresolved=len(result['unresolved_ids']))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.scenario, args.out)
