"""Version 2 research EVENT particle audit; no change to numeric criteria.

ELEMENT fixed widths match wepppyo3/wepp_interchange/src/hill_element.rs and
native SEDOUT format1000 / CONTIN format1200. This declared Roads audit requires
all 26 current columns; it does not guess whitespace boundaries or support
older 24-column decks implicitly. All-star unrelated diagnostics are explicitly
reported as unavailable; required particle fields must be finite. Original
audit_particle_closure.py is frozen.
"""
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal, InvalidOperation
from pathlib import Path
import argparse
import calendar
import datetime
import hashlib
import json
import math

D = Decimal
AUDIT_VERSION = 2
TERMINAL_OFE = 3  # Preserve the original declared three-OFE Roads scope.
ELEMENT_FIELD_WIDTHS = (3, 3, 3, 5, 9, 9, 8, 8, 8, 6, 8, 8, 8, 7,
                        9, 9, 9, 9, 7, 7, 7, 7, 7, 9)
ELEMENT_OPTIONAL_FIELD_WIDTHS = (9, 9)
ELEMENT_WIDTHS = ELEMENT_FIELD_WIDTHS + ELEMENT_OPTIONAL_FIELD_WIDTHS
ELEMENT_NAMES = ('OFE DD MM YYYY Precip Runoff EffInt PeakRO EffDur Enrich '
                 'Keff Sm LeafArea CanHgt Cancov IntCov RilCov LivBio DeadBio '
                 'Ki Kr Tcrit RilWid SedLeave QRain QSnow').split()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def quantum(token):
    return D(10) ** D(token).as_tuple().exponent / D(2)


def parse_element_line(line, start_year):
    """Return exactly the native fields, rejecting malformed rows explicitly."""
    if len(line) < sum(ELEMENT_WIDTHS) or line[sum(ELEMENT_WIDTHS):].strip():
        raise ValueError('ELEMENT row does not match the 26-column native width')
    fields = []
    offset = 0
    for width in ELEMENT_WIDTHS:
        token = line[offset:offset + width].strip()
        if not token:
            raise ValueError('Empty ELEMENT fixed-width field')
        fields.append(token)
        offset += width
    try:
        ofe, day, month, simyear = map(int, fields[:4])
        if ofe < 1 or simyear < 1:
            raise ValueError('Invalid ELEMENT OFE or simulation year')
        datetime.date(start_year + simyear - 1, month, day)
        values = []
        for index, token in enumerate(fields[4:], 4):
            if set(token) == {'*'}:
                if index == 23:
                    raise ValueError('Unavailable required ELEMENT SedLeave')
                continue  # Raw token retained; read_elements reports its absence.
            values.append(float(token))
    except (ValueError, InvalidOperation) as exc:
        raise ValueError('Invalid ELEMENT date or numeric field') from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Nonfinite ELEMENT field')
    return fields


def read_elements(lines, start_year, *, unavailable=None):
    elements = {}
    for number, line in enumerate(lines, 3):
        fields = parse_element_line(line, start_year)
        key = tuple(map(int, fields[:4]))
        if key in elements:
            raise ValueError(f'Duplicate ELEMENT OFE/date at line {number}: {key}')
        elements[key] = fields
        for column, token in zip(ELEMENT_NAMES[4:], fields[4:]):
            if set(token) == {'*'}:
                if unavailable is None:
                    raise ValueError('Unavailable diagnostic requires an explicit report')
                unavailable.append(dict(line=number, key=list(key), column=column,
                                        token=token, reason='native printed value unavailable'))
    return elements


def compare_event(fields, element, width):
    """Preserve v1 Decimal fraction and mass criteria without relaxation."""
    conc = list(map(D, fields[15:20]))
    frac = list(map(D, fields[20:25]))
    if not all(x.is_finite() and x >= 0 for x in conc + frac):
        raise ValueError('Nonfinite or negative PASS particle value')
    fsum = sum(frac)
    ftol = sum(quantum(t) for t in fields[20:25])
    vol = D(fields[7])
    if not vol.is_finite() or vol < 0:
        raise ValueError('Invalid PASS EVENT volume')
    mass = vol * sum(conc)
    boundary = D(element[23]) * width
    mtol = (quantum(fields[7]) * sum(conc)
            + abs(vol) * sum(quantum(t) for t in fields[15:20])
            + quantum(fields[7]) * sum(quantum(t) for t in fields[15:20])
            + quantum(element[23]) * width)
    causes = []
    if sum(conc) and abs(fsum - 1) > ftol:
        causes.append('fraction_sum')
    if abs(mass - boundary) > mtol:
        causes.append('class_bulk_mass')
    if any(x > 1 for x in frac):
        causes.append('fraction_above_one')
    return dict(causes=causes, fraction_sum=str(fsum), fraction_bound=str(ftol),
                class_mass_kg=str(mass), bulk_mass_kg=str(boundary),
                mass_bound_kg=str(mtol))


def audit(record):
    record = Path(record)
    r = json.loads(record.read_text())
    folder = record.parent
    p = folder / 'output/H1.pass.dat'
    e = folder / 'output/H1.element.dat'
    phash, ehash = digest(p), digest(e)
    if phash != r['outputs'][p.name] or ehash != r['outputs'][e.name]:
        raise ValueError(f'Output hash mismatch: {record}')
    lines = p.read_text().splitlines()
    first = int(lines[2].split()[1])
    width = D(str(r['width_m']))
    if not width.is_finite() or width <= 0:
        raise ValueError('Invalid declared hillslope width')
    unavailable = []
    elements = read_elements(e.read_text().splitlines()[2:], first, unavailable=unavailable)
    rows = positive = 0
    flags = []
    seen = set()
    for j, line in enumerate(lines):
        fields = line.split()
        if not fields or fields[0] != 'EVENT':
            continue
        offset = 1
        while len(fields) < 27:
            if j + offset >= len(lines):
                raise ValueError('Truncated PASS EVENT')
            fields += lines[j + offset].split()
            offset += 1
        if len(fields) != 27:
            raise ValueError('PASS EVENT does not have 27 fields')
        y, day = map(int, fields[1:3])
        if y < first or not 1 <= day <= 365 + int(calendar.isleap(y)):
            raise ValueError('Invalid PASS EVENT calendar')
        if (y, day) in seen:
            raise ValueError(f'Duplicate PASS EVENT: {(y, day)}')
        seen.add((y, day))
        date = datetime.date(y, 1, 1) + datetime.timedelta(days=day - 1)
        key = (TERMINAL_OFE, date.day, date.month, y - first + 1)
        if key not in elements:
            raise ValueError(f'Missing terminal ELEMENT row: {key}')
        element = elements[key]
        result = compare_event(fields, element, width)
        rows += 1
        positive += int(bool(sum(map(D, fields[15:20]))))
        if result['causes']:
            flags.append(dict(year=y, julian=day, **result,
                              pass_tokens=fields, element_tokens=element))
    return dict(case=r['case'], record=str(record), record_sha256=digest(record),
                pass_sha256=phash, element_sha256=ehash, events=rows,
                positive_events=positive, flags=flags, passed=not flags,
                audit_version=AUDIT_VERSION,
                numeric_unavailable_diagnostics=unavailable,
                particle_required_fields_available=True,
                structure_valid=True)


def summarize(rows):
    if not rows:
        raise ValueError('No audit records selected')
    return dict(audit_version=AUDIT_VERSION, cases=len(rows),
                events=sum(r['events'] for r in rows),
                positive_events=sum(r['positive_events'] for r in rows),
                flagged_cases=sum(not r['passed'] for r in rows),
                flagged_events=sum(len(r['flags']) for r in rows),
                unavailable_diagnostic_fields=sum(len(r['numeric_unavailable_diagnostics']) for r in rows),
                cases_with_unavailable_diagnostics=sum(bool(r['numeric_unavailable_diagnostics']) for r in rows),
                rows=rows,
                script_sha256=digest(Path(__file__)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=Path)
    ap.add_argument('--pattern', default='seed-*/*/record.json')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    paths = sorted(args.root.glob(args.pattern))
    if args.workers < 1:
        ap.error('--workers must be positive')
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(audit, paths))
    result = summarize(rows)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
