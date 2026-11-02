"""Original read-only full-period WINTER invocation and clean frost gate.

Hourly snow operands are windowed in admitted R05 v8. This reader explicitly
retains that limit; full-period invocation coverage comes from force=1 owners.
Source/build admission and complete ordinary-output parity are external gates.
"""
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

import read_r05_observation as framing


def require(condition, message):
    if not condition:
        raise ValueError(message)


def binding(path):
    path = Path(path).resolve()
    before = path.stat()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Input changed while hashing')
    return dict(path=str(path), sha256=digest, bytes=after.st_size, mtime_ns=after.st_mtime_ns)


def integer(value, low, high):
    require(type(value) is int and low <= value <= high, 'Integer range/type')
    return value


def census_rows(rows, calendar_dates, ofe_count=3):
    integer(ofe_count, 1, 2147483647)
    dates = [tuple(d) for d in calendar_dates]
    require(dates and dates == sorted(set(dates)), 'Calendar order/duplicates')
    for date in dates:
        require(len(date) == 2, 'Calendar shape')
        integer(date[0], 1, 2147483647); integer(date[1], 1, 366)
    allowed = set(dates)
    expected_daily = {(y, d, ip) for y, d in dates for ip in range(1, ofe_count + 1)}
    daily = {'DAY_OPEN': set(), 'DAY_CLOSE': set()}
    active = {}; completed = {}; pending = {}; last_date = None; total = 0
    hour_tags = ('WINTER_SNOW_PRE', 'SNOW_ENTRY', 'SNOW_RETURN', 'WINTER_SNOW_POST', 'WINTER_MELT_HOUR')
    stages = {'DAY_OPEN', 'DAY_CLOSE', 'WINTER_PRE', 'WINTER_POST'}
    for row in rows:
        total += 1
        date = (row['year'], row['day']); ip = row['ofe']; key = (*date, ip)
        require(date in allowed and type(ip) is int and 1 <= ip <= ofe_count, 'Unexpected clock/OFE')
        require(last_date is None or date >= last_date, 'Reversed date')
        last_date = date
        stage = row['snapshot']; tag = row['tag']; index = row['index']
        if stage in stages:
            slot = (key, stage); part = row['group']
            if part == 'LAYER':
                if index == 1:
                    require(slot not in pending, 'Duplicate snapshot')
                    pending[slot] = ['LAYER', 0]
                require(slot in pending and pending[slot][0] == 'LAYER' and index == pending[slot][1] + 1, 'Layer order')
                pending[slot][1] = index
                continue
            require(slot in pending and index == 0, 'Missing snapshot layers')
            state = pending[slot]
            require(part in ('PLANT', 'WATER', 'STATE') and state[0] == {'PLANT': 'LAYER', 'WATER': 'PLANT', 'STATE': 'WATER'}[part], 'Snapshot owner order')
            state[0] = part
            if part != 'STATE':
                continue
            require(row['values'][0] == state[1] and state[1] > 0, 'Snapshot layer count')
            del pending[slot]
            if stage in daily:
                require(key not in daily[stage], 'Duplicate daily owner')
                daily[stage].add(key)
            elif stage == 'WINTER_PRE':
                require(key not in active and key not in completed, 'Duplicate WINTER invocation')
                active[key] = dict(returned=False, hourly=[])
            else:
                require(key in active and active[key]['returned'], 'WINTER post without return')
                record = active.pop(key)
                sequence = [(h, t) for h in range(1, 25) for t in hour_tags]
                require(not record['hourly'] or record['hourly'] == sequence, 'Incomplete/duplicate/reordered hourly census')
                completed[key] = dict(key=list(key), observed_hours=list(range(1, 25)) if record['hourly'] else [])
        elif tag == 'WINTER_RETURN':
            require(index == 0 and key in active and not active[key]['returned'], 'Missing/duplicate WINTER return')
            active[key]['returned'] = True
        elif tag in hour_tags:
            require(key in active and not active[key]['returned'], 'Hour outside WINTER invocation')
            integer(index, 1, 24)
            active[key]['hourly'].append((index, tag))
    require(not active and not pending, 'Truncated invocation/snapshot')
    require(all(keys == expected_daily for keys in daily.values()), 'Incomplete daily calendar')
    require(completed, 'Empty WINTER census')
    return dict(version=1, basis='full_period_WINTER_PRE_RETURN_POST_invocations',
                hourly_fullperiod_observed=all(r['observed_hours'] for r in completed.values()),
                hourly_scope='Only actually retained windowed hours; no unobserved hours inferred',
                records=[completed[k] for k in sorted(completed)], calendar_dates=[list(d) for d in dates],
                ofe_count=ofe_count, trace_records=total, scientific_acceptance=False)


def extract_snow_census(trace_path, schema_path, calendar_dates, ofe_count=3):
    inputs = [binding(p) for p in (trace_path, schema_path, __file__, framing.__file__)]
    schema = json.loads(Path(schema_path).read_text())
    require(schema['WINTER_RETURN']['force'] == 1 and all(schema['_snapshot_stages'][s] == 1 for s in ('WINTER_PRE', 'WINTER_POST', 'DAY_OPEN', 'DAY_CLOSE')), 'Full-period owner schema')
    result = census_rows(framing.records(trace_path, schema), calendar_dates, ofe_count)
    require(inputs == [binding(p['path']) for p in inputs], 'Mutated census dependency')
    result['bindings'] = inputs
    return result


_PATTERN = re.compile(r'(WFR_SUM_CALL|WFR_SUM_GUAR)\s+y=\s*([+-]?\d+)\s+d=\s*([+-]?\d+)\s+e=\s*([+-]?\d+)\s+c=\s*([+-]?\d+)\s+s=\s*([+-]?\d+)\s+v1=\s*(\S+)\s+v2=\s*(\S+)')


def counter(token):
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError('Malformed counter') from exc
    require(value.is_finite() and value == value.to_integral_value() and 0 <= value <= 24, 'Nonintegral/nonfinite/out-of-range counter')
    return int(value)


def validate_frost(log_path, expected_census):
    before = binding(log_path)
    require(expected_census.get('version') == 1, 'Census version')
    keys = [tuple(r['key']) for r in expected_census['records']]
    require(keys and len(keys) == len(set(keys)), 'Empty/duplicate expected keys')
    dates = {tuple(d) for d in expected_census['calendar_dates']}
    for y, d, ip in keys:
        integer(y, 1, 2147483647); integer(d, 1, 366)
        integer(ip, 1, expected_census['ofe_count'])
        require((y, d) in dates, 'Expected key outside calendar')
    expected = set(keys); seen = {'WFR_SUM_CALL': {}, 'WFR_SUM_GUAR': {}}
    with Path(log_path).open() as stream:
        for line in stream:
            match = _PATTERN.fullmatch(line.strip())
            require(match is not None, 'Unexpected/malformed frost record')
            tag, y, d, ip, channel, segment, a, b = match.groups()
            key = (int(y), int(d), int(ip))
            require(key in expected and int(channel) == 0 and int(segment) == 0, 'Unexpected frost clock/owner')
            require(key not in seen[tag], 'Duplicate frost summary')
            values = (counter(a), counter(b))
            require(values[0] == values[1] if tag == 'WFR_SUM_CALL' else values == (0, 0), 'Executed FROSTN or nonzero guard')
            seen[tag][key] = values
    require(all(set(v) == expected for v in seen.values()), 'Missing frost summary')
    require(before == binding(log_path), 'Mutated frost log')
    return dict(passed=True, invocation_count=len(expected), eligible=sum(v[0] for v in seen['WFR_SUM_CALL'].values()),
                skipped=sum(v[1] for v in seen['WFR_SUM_CALL'].values()), executed=0, guards=0,
                log_binding=before, scientific_acceptance=False,
                scope='Exact invocation-key and counter proof; source/admission/ordinary parity external')
