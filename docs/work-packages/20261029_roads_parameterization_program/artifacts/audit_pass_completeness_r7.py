"""Calendar/terminal coverage gate for the declared three-OFE r4/r7 seed trial.

This supplements, rather than changes, audit_particle_closure_v2's numerical
criteria. Only the selected WEPP_PASS_COMPONENTS 3 hillslope format is accepted.
Daily record widths follow the owned wepp_interchange hill_pass reader.
"""
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import json
import math

import audit_particle_closure_v2 as particles


def daily_records(lines):
    """Return daily labels; reject incomplete records and component trailers."""
    sizes = {'EVENT': 26, 'SUBEVENT': 8, 'NO EVENT': 4}
    records = {}
    index = 6
    while index < len(lines):
        line = lines[index]
        index += 1
        label = line[:8].strip()
        if label not in sizes:
            raise ValueError('Unrecognized PASS daily record')
        fields = line[8:].split()
        while len(fields) < sizes[label] and index < len(lines):
            fields.extend(lines[index].split())
            index += 1
        if len(fields) != sizes[label]:
            raise ValueError('Truncated or malformed PASS daily record')
        year, julian = map(int, fields[:2])
        first = date(year, 1, 1)
        day = first + timedelta(days=julian - 1)
        if julian < 1 or day.year != year:
            raise ValueError('Invalid PASS Julian date')
        if day in records:
            raise ValueError('Duplicate PASS daily date')
        if not all(math.isfinite(float(t.replace('D', 'E').replace('d', 'e')))
                   for t in fields[2:]):
            raise ValueError('Nonfinite PASS daily field')
        records[day] = label
        if label == 'EVENT':
            if index == len(lines):
                raise ValueError('Missing PASS SRC3 trailer')
            source = lines[index].split()
            index += 1
            if (len(source) not in (4, 31) or source[0] != 'SRC3'
                    or tuple(map(int, source[1:3])) != (year, julian)
                    or (source[3], len(source)) not in (('0', 4), ('1', 31))):
                raise ValueError('Malformed PASS SRC3 trailer')
            if not all(math.isfinite(float(t.replace('D', 'E').replace('d', 'e')))
                       for t in source[4:]):
                raise ValueError('Nonfinite PASS SRC3 field')
    return records


def audit(record_path, climate):
    """Audit an immutable record against its frozen climate-manifest entry.

    ``climate`` requires first/last ISO dates, days, years and input sha256.
    Returns a JSON-safe certificate on success; invalid bindings, structure,
    calendar or positive terminal sediment coverage raise ValueError. No native
    execution, writes or numerical acceptance thresholds occur here.
    """
    record_path = Path(record_path)
    record = json.loads(record_path.read_text())
    folder = record_path.parent
    climate_hash = particles.digest(folder / 'runs/p1.cli')
    if climate_hash != climate['sha256'] or climate_hash != record['inputs']['p1.cli']:
        raise ValueError('Frozen climate input hash mismatch')
    first, last = date.fromisoformat(climate['first']), date.fromisoformat(climate['last'])
    count = (last - first).days + 1
    years = last.year - first.year + 1
    if (first.month, first.day, last.month, last.day) != (1, 1, 12, 31) or (
            count <= 0 or count != climate['days'] or years != climate['years']):
        raise ValueError('Invalid frozen full-year climate calendar')
    expected = {first + timedelta(days=i) for i in range(count)}
    pass_path, element_path = (folder / 'output' / f'H1.{kind}.dat'
                               for kind in ('pass', 'element'))
    pass_hash, element_hash = particles.digest(pass_path), particles.digest(element_path)
    if (pass_hash != record['outputs'][pass_path.name]
            or element_hash != record['outputs'][element_path.name]):
        raise ValueError('Output hash mismatch')
    lines = pass_path.read_text().splitlines()
    if (len(lines) < 6 or lines[0].rstrip() != 'WEPP_PASS_COMPONENTS 3'
            or lines[1].strip() != 'p1.cli'
            or lines[2].split() != [str(years), str(first.year)]):
        raise ValueError('Incomplete or incompatible PASS header/calendar')
    records = daily_records(lines)
    if set(records) != expected:
        raise ValueError('PASS daily calendar does not match frozen climate')
    # Reuse the reviewed native fixed-width ELEMENT reader; no whitespace guess.
    elements = particles.read_elements(element_path.read_text().splitlines()[2:],
                                       first.year, unavailable=[])
    terminal = {date(first.year + key[3] - 1, key[2], key[1]): fields
                for key, fields in elements.items() if key[0] == particles.TERMINAL_OFE}
    # ELEMENT is event-only; its absent dry days are valid. PASS owns the full
    # daily calendar, while terminal sediment dates must be inside that period.
    if not set(terminal) <= expected:
        raise ValueError('Terminal ELEMENT date lies outside frozen climate')
    positive = {day for day, fields in terminal.items() if Decimal(fields[23]) > 0}
    events = {day for day, label in records.items() if label == 'EVENT'}
    if not positive <= records.keys():
        raise ValueError('Positive terminal ELEMENT sediment lacks PASS daily record')
    # Native WSH PAS deliberately omits EVENT particle fields below its runoff
    # threshold. Preserve this valid state and expose the numerical audit gap.
    non_event = [dict(date=day.isoformat(), pass_label=records[day],
                      sedleave_kg_m_token=terminal[day][23],
                      runoff_mm_token=terminal[day][5])
                 for day in sorted(positive - events)]
    return dict(passed=True, audit_version=1, case=record['case'],
                record=str(record_path), record_sha256=particles.digest(record_path),
                pass_sha256=pass_hash, element_sha256=element_hash,
                climate_sha256=climate_hash, first=climate['first'], last=climate['last'],
                calendar_days=count, event_days=len(events),
                positive_terminal_days=len(positive), terminal_ofe=particles.TERMINAL_OFE,
                positive_terminal_non_event_dates=non_event,
                particle_audit_scope='Existing strict criteria apply to EVENT rows only; '
                    'positive terminal sediment on NO EVENT/SUBEVENT dates has no EVENT '
                    'particle payload and is not certified by that audit.',
                event_classification_source=dict(
                    commit='e0abe0581f77c6f66917e90daf8f8f429e9315c8',
                    path='src/wshpas.for', line=161,
                    condition='runoff(nplane).ge.0.001', runoff_units='m'),
                script_sha256=particles.digest(Path(__file__)))
