"""Independent PASS readback, observer joins, channel residuals and controls."""
from pathlib import Path
import argparse
import calendar
import csv
import hashlib
import json
import math
import re
from functools import lru_cache

import numpy as np
from wepppyo3 import wepp_interchange

OBS = re.compile(r'^(WCL_\w+) y=\s*(\d+) d=\s*(\d+) e=\s*(\d+) c=\s*(\d+) s=\s*(\d+) v1=\s*(\S+) v2=\s*(\S+)')
EPS = float(np.finfo(np.float32).eps)


def residual(inflow, outflow, loss, start, end, baseflow=0):
    return inflow + baseflow - outflow - loss - (end - start)


def controls():
    # 100 input = 70 output + 10 loss + 20 storage increase.
    cases = [(100, 70, 10, 30, 50, 0), (200, 70, 10, 30, 50, 100),
             (100, 0, 10, 30, 50, 70), (40, 70, 10, 30, 50, -60),
             (100, 70, 10, 50, 30, 40)]
    names = ['zero', 'duplicate_inflow', 'drop_outflow', 'wrong_area_0.4', 'reverse_storage']
    result = {}
    for name, (i, o, l, s, e, expected) in zip(names, cases):
        actual = residual(i, o, l, s, e)
        assert actual == expected
        result[name] = {'expected_m3': expected, 'actual_m3': actual, 'detected': actual != 0}
    return result


@lru_cache(maxsize=2)
def observations(path):
    records = {}
    with path.open() as stream:
        for line in stream:
            match = OBS.match(line)
            if not match:
                continue
            tag, year, day, element, ofe, event, v1, v2 = match.groups()
            key = (tag, int(year), int(day), int(element))
            if key in records:
                raise ValueError(f'Duplicate observer record {key}')
            values = (float(v1), float(v2))
            if not all(math.isfinite(v) for v in values):
                raise ValueError(f'Nonfinite observer record {key}')
            records[key] = (int(ofe), int(event), *values)
    return records


def readback(case, hill=1):
    if (case / 'runs/wepp_observe.log').exists():
        obs = observations(case / 'runs/wepp_observe.log')
    else:
        obs = observations(case / f'p{hill}.run.observe.log')
        obs.update({k: v for k, v in observations(case / 'pw0.run.observe.log').items() if k[3] == hill})
    path = case / f'output/H{hill}.hbp'
    data = wepp_interchange.hillslope_pass_to_columns(str(path), 1, 0, pass_family='hbp')
    dates = list(zip(data['year'], data['julian']))
    expected = [(y, d) for y in range(min(data['year']), max(data['year']) + 1)
                for d in range(1, 366 + calendar.isleap(y))]
    configured_years = int((case / 'runs/pw0.run').read_text().splitlines()[-1])
    assert max(data['year']) - min(data['year']) + 1 == configured_years
    dense = [(y, d) for y in range(min(data['year']), max(data['year']) + 1) for d in range(1, 367)]
    assert dates == dense, 'Incomplete or duplicate schema-2 PASS directory'
    index = {date: i for i, date in enumerate(dates)}
    assert len(obs) == 9 * len(expected), 'Missing or excess observer records'
    sequential_max_delta = 0.
    first_date_mismatch = None
    index_physical = set(expected)
    maxima = {'writer_payload_m3': 0., 'payload_reader_m3': 0., 'lateral_area_m3': 0.}
    omitted_surface = omitted_lateral = 0.
    events = {}
    violations = []
    for sequence, (year, day) in enumerate(expected):
        i = index[(year, day)]
        if dates[sequence] != (year, day) and first_date_mismatch is None:
            first_date_mismatch = {"routing_date": [year, day], "sequential_payload_date": dates[sequence]}
        def get(tag):
            return obs[(tag, year, day, hill if tag.startswith('WCL_READ') else 1)]
        _, event, lateral, tile = get('WCL_SELECTED')
        events[event] = events.get(event, 0) + 1
        assert event == {'NO EVENT': 0, 'SUBEVENT': 1, 'EVENT': 2}[data['event'][i]]
        raw_surface = get('WCL_RAW_Q')[3]
        raw_lat_depth = get('WCL_RAW_L')[2]
        length, width = get('WCL_AREA')[2:]
        physical_lat = float(np.float32(np.float32(np.float32(raw_lat_depth) * np.float32(length)) * np.float32(width)))
        if event >= 1:
            maxima['lateral_area_m3'] = max(maxima['lateral_area_m3'], abs(lateral - physical_lat))
            if abs(lateral - physical_lat) > 4 * EPS * abs(physical_lat):
                violations.append([year, day, 'terminal_area', lateral - physical_lat])
        selected = {'runvol': raw_surface if event == 2 else 0., 'sbrunv': lateral if event >= 1 else 0.,
                    'drrunv': tile if event >= 1 else 0., 'gwbfv': get('WCL_GW')[2], 'gwdsv': get('WCL_GW')[3]}
        loaded = {'runvol': get('WCL_READ_Q')[3], 'sbrunv': get('WCL_READ_L')[3],
                  'drrunv': get('WCL_READ_T')[3], 'gwbfv': get('WCL_READ_G')[2], 'gwdsv': get('WCL_READ_G')[3]}
        for key, value in selected.items():
            payload = data[key][i]
            delta = abs(value - payload)
            maxima['writer_payload_m3'] = max(maxima['writer_payload_m3'], delta)
            if delta > 0.51e-9 + EPS * abs(value):
                violations.append([year, day, key + '_writer_payload', delta])
            sequential_max_delta = max(sequential_max_delta, abs(loaded[key] - float(np.float32(data[key][sequence]))))
            delta = abs(loaded[key] - payload)
            maxima['payload_reader_m3'] = max(maxima['payload_reader_m3'], delta)
            if delta > 0.51e-9 + EPS * abs(payload):
                violations.append([year, day, key + '_payload_reader', delta])
        omitted_surface += raw_surface - selected['runvol']
        omitted_lateral += physical_lat - selected['sbrunv']
    return {'days': len(expected), 'serialized_slots': len(dates),
            'synthetic_slots': len(dates) - len(expected),
            'first_sequential_date_mismatch': first_date_mismatch,
            'sequential_payload_reader_max_delta_m3': sequential_max_delta, 'years': [min(data['year']), max(data['year'])],
            'hbp_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'event_counts': events,
            'maximum_deltas': maxima, 'omitted_surface_m3': omitted_surface,
            'omitted_lateral_m3': omitted_lateral, 'violation_count': len(violations), 'first_violations': violations[:10],
            'unconsumed_tail_volume_m3': {k: sum(data[k][len(expected):]) for k in ['runvol','sbrunv','drrunv','gwbfv']},
            'physical_payload_volumes_m3': {k: sum(data[k][index[d]] for d in expected) for k in ['runvol','sbrunv','drrunv','gwbfv']},
            'consumed_synthetic_volumes_m3': {k: sum(data[k][i] for i in range(len(expected)) if dates[i] not in index_physical) for k in ['runvol','sbrunv','drrunv','gwbfv']}}


def channel_ledger(case, label):
    with (case / 'channel_balance.csv').open() as f:
        balance = {}
        for r in csv.DictReader(f):
            key = (int(r['year']), int(r['sdate']), int(r['ielmt']))
            if key in balance:
                raise ValueError('Duplicate channel balance record')
            balance[key] = r
    rows = []
    seen = set()
    last_storage = {}
    with (case / 'channel_publish.csv').open() as f:
        for r in csv.DictReader(f):
            key = (int(r['year']), int(r['sdate']), int(r['ielmt']))
            if key in seen:
                raise ValueError('Duplicate channel publication')
            seen.add(key)
            b = balance[key]
            assert r['kernel_ok'] == '1' and r['status_message'] == 'WBK_ROUTE_06_OK'
            vals = [float(r[k]) for k in ['inflow_m3', 'outflow_m3', 'loss_m3', 'kernel_baseflow_m3']]
            start, end = float(b['lastStor']), float(b['sfnl'])
            if not all(math.isfinite(v) for v in vals + [start, end]):
                raise ValueError('Nonfinite channel ledger')
            if key[2] in last_storage:
                assert start == last_storage[key[2]], 'Discontinuous channel storage'
            last_storage[key[2]] = end
            inflow, outflow, loss, baseflow = vals
            res = residual(inflow, outflow, loss, start, end, baseflow)
            bound = 16 * EPS * (sum(abs(v) for v in vals) + abs(start) + abs(end)) + 1e-12
            denom = max(abs(inflow) + abs(baseflow), abs(outflow) + abs(loss), abs(end - start))
            rows.append(dict(case=label, year=key[0], day=key[1], element=key[2],
                             inflow=inflow, baseflow=baseflow, outflow=outflow, loss=loss,
                             storage_start=start, storage_end=end, residual=res, tolerance=bound,
                             normalized=res / denom if denom else 0., within_arithmetic_bound=abs(res) <= bound))
    assert seen == set(balance), 'Channel diagnostic join incomplete'
    for element in last_storage:
        dates = [(r['year'], r['day']) for r in rows if r['element'] == element]
        expected = [(y, d) for y in range(min(d[0] for d in dates), max(d[0] for d in dates) + 1) for d in range(1, 366 + calendar.isleap(y))]
        assert dates == expected, 'Incomplete channel calendar'
    return rows


def summarize(rows):
    worst = max(rows, key=lambda r: abs(r['residual']))
    return {'rows': len(rows), 'signed_m3': sum(r['residual'] for r in rows),
            'absolute_m3': sum(abs(r['residual']) for r in rows), 'worst': worst,
            'outside_arithmetic_bound': sum(not r['within_arithmetic_bound'] for r in rows),
            'negative_loss_rows': sum(r['loss'] < 0 for r in rows)}



def observed_controls(rows, output):
    # Choose an actual observed row with independently measurable mutations.
    source = next(r for r in rows if min(r['inflow'], r['outflow'], abs(r['storage_end'] - r['storage_start'])) > 100 * r['tolerance'])
    records = []
    changes = [('unchanged', {}, 0.),
               ('duplicate_inflow', {'inflow': source['inflow'] * 2}, source['inflow']),
               ('drop_outflow', {'outflow': 0.}, source['outflow']),
               ('wrong_area', {'inflow': source['inflow'] * .4}, -.6 * source['inflow']),
               ('reverse_storage', {'storage_start': source['storage_end'], 'storage_end': source['storage_start']}, 2 * (source['storage_end'] - source['storage_start']))]
    for name, mutation, delta in changes:
        row = dict(source, **mutation)
        row['control'] = name
        row['expected_delta'] = delta
        records.append(row)
    path = output / 'observed_control_ledgers.csv'
    with path.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
    results = {}
    # Read the copied CSV back; evaluate changed boundary values, never the
    # stored residual column (which intentionally still holds the original).
    with path.open() as f:
        for row in csv.DictReader(f):
            actual = residual(*(float(row[k]) for k in ['inflow','outflow','loss','storage_start','storage_end','baseflow']))
            delta = actual - source['residual']
            expected = float(row['expected_delta'])
            assert math.isclose(delta, expected, rel_tol=1e-12, abs_tol=1e-12)
            detected = abs(actual) > float(row['tolerance'])
            assert detected == (row['control'] != 'unchanged')
            results[row['control']] = {'actual_residual_m3': actual, 'expected_delta_m3': expected,
                                       'measured_delta_m3': delta, 'detected': detected}
    return {'source_observed_record': source, 'copied_csv': str(path), 'results': results}


def pipeline_controls(source, output):
    originals = {}
    for filename in ['channel_balance.csv', 'channel_publish.csv']:
        with (source / filename).open() as f:
            originals[filename] = list(csv.DictReader(f))
    results = {}
    for name in ['duplicate_balance', 'missing_day', 'nonfinite_inflow']:
        target = output / name
        target.mkdir(exist_ok=True)
        for filename, original in originals.items():
            rows = [dict(r) for r in original]
            if name == 'duplicate_balance' and filename == 'channel_balance.csv':
                rows.append(dict(rows[0]))
            if name == 'missing_day':
                rows.pop()
            if name == 'nonfinite_inflow' and filename == 'channel_publish.csv':
                rows[0]['inflow_m3'] = 'nan'
            with (target / filename).open('w') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        try:
            channel_ledger(target, name)
        except (ValueError, AssertionError) as exc:
            results[name] = {'rejected': True, 'reason': str(exc), 'retained_path': str(target)}
        else:
            raise AssertionError(f'Corrupted pipeline input accepted: {name}')
    return results

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=True)
    all_rows = []
    summaries = {}
    for case in sorted(a.root.iterdir()):
        if not (case / 'execution.json').exists():
            continue
        execution = json.loads((case / 'execution.json').read_text())
        assert len(execution['results']) == 2 and all(r['success'] for r in execution['results'])
        read = readback(case)
        rows = channel_ledger(case, case.name)
        assert len(rows) == read['days'], 'Incomplete single-channel calendar'
        all_rows += rows
        summaries[case.name] = {'pass': read, 'channel': summarize(rows)}
    with (a.output / 'volume_ledger.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0])); w.writeheader(); w.writerows(all_rows)
    (a.output / 'residual_summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
    (a.output / 'diagnostic_controls.json').write_text(json.dumps({'hand_computable': controls(), 'observed_mutations': observed_controls(all_rows, a.output)}, indent=2) + '\n')
