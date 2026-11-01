"""Compact accepted histories without annualizing representation residuals."""
import argparse
import json
from pathlib import Path
from read_history import sha


def summarize(root):
    receipt = json.loads((root / 'histories.json').read_text())
    rows = []
    for pair in receipt['cases']:
        observer = pair['members'][1]
        if not pair['accepted']:
            rows.append(dict(scenario=pair['scenario'], accepted=False,
                             failures=[r.get('error') for r in pair['members']]))
            continue
        t = observer['trace']
        directory = root / pair['scenario'] / 'observer'
        residual_effects = {}
        with (directory / 'transfers.jsonl').open() as stream:
            for line in stream:
                row = json.loads(line)
                key = ('invalid_' if row['invalid_state'] else '') + 'mode' + str(row['mode'])
                effect = residual_effects.setdefault(key, dict(layers=0, max_absolute_residual_m=0,
                          max_absolute_fine_change_m=0, max_request_rounding_difference_m=0))
                effect['layers'] += 1
                effect['max_absolute_residual_m'] = max(effect['max_absolute_residual_m'], abs(row['mapping_residual_m']))
                effect['max_absolute_fine_change_m'] = max(effect['max_absolute_fine_change_m'], abs(row['fine_change_m']))
                effect['max_request_rounding_difference_m'] = max(effect['max_request_rounding_difference_m'], abs(row['request_rounding_difference_m']))
        pending = {}
        endpoint_ranges = {}
        with (directory / 'ownership.jsonl').open() as stream:
            for line in stream:
                row = json.loads(line)
                if row['kind'] == 'clear':
                    pending[row['id']] = row
                elif row['kind'] == 'boundary' and row['tag'] == 'INIT_PRE':
                    pending[row['id']]['init_pre'] = row
                elif row['kind'] == 'endpoint':
                    item = pending.pop(row['id'])
                    before = item.get('init_pre')
                    if before and before['fine_available'] and row['fine_available']:
                        value = row['stocks']['fine_total'] - before['stocks']['fine_total']
                        key = 'observed_initialization_fine_change_m_not_causal_recovery'
                        extent = endpoint_ranges.setdefault(key, dict(count=0, min=value, max=value))
                        extent['count'] += 1
                        extent['min'] = min(extent['min'], value)
                        extent['max'] = max(extent['max'], value)
        rows.append(dict(scenario=pair['scenario'], accepted=True,
                         observed_frost_calls=t['counts'].get('FROST_CALL', 0),
                         weather_eligible=t['counts'].get('WEATHER_ELIGIBLE', 0), maps=t['maps'],
                         signature_counts=t['signature_counts'], signature_examples=t['signature_examples'],
                         signed_ranges=t['signed_ranges'], counts=t['counts'],
                         effects=residual_effects, ownership_counts=t['ownership_counts'],
                         clearing_events_without_next_initialization=t['clearing_events_without_next_initialization'],
                         endpoint_ranges=endpoint_ranges, daily_keys=observer['daily_keys'],
                         output_hashes=observer['output_hashes'], trace_sha256=t['trace_sha256'],
                         transfers_sha256=sha(directory / 'transfers.jsonl'),
                         ownership_sha256=sha(directory / 'ownership.jsonl')))
    return dict(passed=receipt['passed'], histories_sha256=sha(root / 'histories.json'), cases=rows,
                interpretation='Signed state differences and exposure counts; no annual external loss estimate.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--campaign', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    with a.out.open('x') as stream:
        json.dump(summarize(a.campaign), stream, indent=2, allow_nan=False)
        stream.write('\n')
