"""Read-only R02/U12 ordinary-output and Decimal particle comparison.

No native execution, imports of historical writers, or certificate reuse. Stocks
are compared as stocks; sparse event absence is retained explicitly. Main refuses
partial aggregates and writes only a new R02-readback-v1 directory.
"""
import argparse
import calendar
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import datetime as dt
from decimal import Decimal as D
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RAW = REPO / 'out/rock-water-development-20261101'
ROOT = RAW / 'R02-v1'
OLD = REPO / 'out/roads-parameterization-program-20261031/param-sign-u12-combined'
KEYS = ('climate', 'soil', 'design', 'surface', 'traffic')
VALUES = (('birmingham', 'charleston', 'denver', 'flagstaff', 'site'),
          ('1718465', '1718494', '1718510', '1856573', '2711184', '2711250', '53949'),
          ('inbare', 'inveg', 'outrut', 'outunrut'), ('gravel', 'paved'), ('high', 'low', 'none'))
EXPECTED = set(itertools.product(*VALUES))
OUTPUTS = {'H1.' + x + '.dat' for x in ('ebe', 'element', 'loss', 'pass', 'plot', 'soil', 'wat')}
WAT = 'OFE J Y P RM Q Ep Es Er Dp UpStrmQ SubRIn latqcc Total-Soil frozwt Snow-Water QOFE Tile Irr Area SoilWaterTotal ProfileDepth ProfilePorosityCap ProfileFCStore ProfileWPStore'.split()
ELEMENT = 'OFE DD MM YYYY Precip Runoff EffInt PeakRO EffDur Enrich Keff Sm LeafArea CanHgt Cancov IntCov RilCov LivBio DeadBio Ki Kr Tcrit RilWid SedLeave QRain QSnow'.split()
EBE = 'day mo year Precp Runoff IR-det Av-det Mx-det Point Av-dep Max-dep Point Sed.Del ER'.split()
FLUXES = set('P RM Q Ep Es Er Dp UpStrmQ SubRIn latqcc QOFE Tile Irr'.split())
NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


class Bindings:
    def __init__(self):
        self.entries = {}

    def bind(self, path, expected=None):
        path = Path(path).resolve()
        st = path.stat()
        entry = dict(sha256=sha(path), bytes=st.st_size, mtime_ns=st.st_mtime_ns)
        require(expected is None or entry['sha256'] == expected, f'Hash drift: {path}')
        require(str(path) not in self.entries or self.entries[str(path)] == entry, f'Read drift: {path}')
        self.entries[str(path)] = entry
        return path

    def check(self):
        for p, before in list(self.entries.items()):
            self.bind(p, before['sha256'])


def key(row):
    return tuple(row['case'][k] for k in KEYS)


def coverage(rows):
    ks = [key(r) for r in rows]
    require(len(ks) == len(set(ks)) and set(ks) == EXPECTED, 'Case domain missing/duplicate/wrong')
    require(all(r['case'].get('variant') == 'erosion_road_cap' and r['case'].get('runtime') == 'project' for r in rows), 'Wrong conditioning')


def number(token, nonnegative=False):
    value = D(token.replace('D', 'E'))
    require(value.is_finite(), 'Nonfinite number')
    require(not nonnegative or value >= 0, 'Negative constrained number')
    return value


def insert(rows, key_, value):
    require(key_ not in rows, f'Duplicate key: {key_}')
    rows[key_] = value


def climate(text):
    rows = {}
    for line in text.splitlines()[15:]:
        f = line.split()
        require(len(f) == 13, 'Climate framing')
        day, month, year = map(int, f[:3])
        date = dt.date(year, month, day)
        insert(rows, (year, date.timetuple().tm_yday), None)
    years = sorted({y for y, j in rows})
    require(years and years == list(range(years[0], years[-1] + 1)), 'Climate year continuity')
    require(set(rows) == {(y, j) for y in years for j in range(1, 366 + calendar.isleap(y))}, 'Incomplete climate')
    return set(rows), years


def geometry(text, width, length, return_width=False):
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith('#')]
    require(len(lines) == 9 and lines[1] == '3', 'Three-OFE geometry')
    width_token = lines[2].split()[1]
    actual_width = float(number(width_token, True))
    lengths = []; length_tokens = []
    for i in (3, 5, 7):
        n, size = lines[i].split()
        values = list(map(float, lines[i + 1].replace(',', ' ').split()))
        require(len(values) == int(n) * 2 and values[0] == 0 and values[-2] == 1, 'Slope points')
        require(all(math.isfinite(v) for v in values) and all(a < b for a, b in zip(values[::2], values[2::2])), 'Slope coordinate order')
        lengths.append(float(number(size, True))); length_tokens.append(size)
    require(actual_width > 0 and all(x > 0 for x in lengths), 'Nonpositive geometry')
    require(abs(number(width_token) - number(str(width))) <= quantum(width_token) and abs(sum(number(t) for t in length_tokens) - number(str(length))) <= sum(quantum(t) for t in length_tokens), 'Geometry receipt mismatch')
    areas = [actual_width * x for x in lengths]
    return (areas, actual_width) if return_width else areas


def no_contours(management):
    contours = re.findall(r'^\s*(\d+)\s*# looper; number of Contouring scenarios', management, re.M)
    require(contours == ['0'], 'Q cumulative-area conversion requires zero contour scenarios')


def wat(text, dates, areas):
    header = next((l.split() for l in text.splitlines() if l.split()[:3] == ['OFE', 'J', 'Y']), None)
    require(header == WAT, 'WAT schema')
    rows = {}
    for line in text.splitlines():
        f = line.split()
        if not f or not f[0].isdigit():
            continue
        require(len(f) == 25, 'WAT width')
        o, j, y = map(int, f[:3])
        values = [float(number(t)) for t in f[3:]]
        require(o in (1, 2, 3) and (y, j) in dates, 'WAT source-year clock')
        require(abs(values[16] - areas[o - 1]) <= .0051, 'WAT geometry area')
        insert(rows, (y, j, o), values)
    require(set(rows) == {(y, j, o) for y, j in dates for o in (1, 2, 3)}, 'WAT missing date/OFE')
    return rows


def sparse(text, kind, dates, first):
    rows = {}
    lines = text.splitlines()
    expected_header = ELEMENT if kind == 'element' else EBE
    require(lines[0 if kind == 'element' else 1].split() == expected_header, 'Sparse header identity')
    skip, size = (2, 26) if kind == 'element' else (3, 14)
    for line in text.splitlines()[skip:]:
        f = line.split()
        if not f:
            continue
        require(len(f) == size, f'{kind} schema')
        if kind == 'element':
            ofe, day, month, relative = map(int, f[:4])
            require(ofe in (1, 2, 3), 'ELEMENT OFE')
            start = 4
        else:
            day, month, relative = map(int, f[:3]); ofe = 3; start = 3
        date = dt.date(first + relative - 1, month, day)
        clock = (date.year, date.timetuple().tm_yday, ofe)
        require(clock[:2] in dates and relative >= 1, 'Sparse relative-year clock')
        for index, token in enumerate(f[start:], start):
            if '*' in token:
                require(kind == 'element' and index == 11 and set(token) == {'*'}, 'Star outside Sm')
            else:
                number(token)
        insert(rows, clock, f)
    if kind == 'element':
        by_date = defaultdict(set)
        for y, j, o in rows:
            by_date[y, j].add(o)
        require(all(ofes == {1, 2, 3} for ofes in by_date.values()), 'Incomplete sparse OFEs')
    return rows


def quantum(token):
    return D(10) ** number(token).as_tuple().exponent / 2


def validate_sm(elements, historical):
    require(historical or all('*' not in f[11] for f in elements.values()), 'Candidate Sm must be numeric')


def particle_event(f, terminal, width):
    require(len(f) == 27 and f[0] == 'EVENT', 'EVENT token count')
    # Preserve the historical exact Decimal arithmetic and predicates.
    for t in f[3:]:
        number(t)
    width = number(str(width), True); require(width > 0, 'Particle width')
    volume = number(f[7], True)
    conc = [number(t, True) for t in f[15:20]]
    frac = [number(t, True) for t in f[20:25]]
    boundary = number(terminal[23], True) * width
    mass = volume * sum(conc)
    ftol = sum(quantum(t) for t in f[20:25])
    mtol = (quantum(f[7]) * sum(conc) + abs(volume) * sum(quantum(t) for t in f[15:20])
            + quantum(f[7]) * sum(quantum(t) for t in f[15:20]) + quantum(terminal[23]) * width)
    causes = []
    if sum(conc) and abs(sum(frac) - 1) > ftol:
        causes.append('fraction_sum')
    if abs(mass - boundary) > mtol:
        causes.append('class_bulk_mass')
    if any(x > 1 for x in frac):
        causes.append('fraction_above_one')
    return dict(causes=causes, fraction_sum=str(sum(frac)), fraction_residual=str(sum(frac) - 1),
                fraction_bound=str(ftol), class_mass_kg=str(mass), bulk_mass_kg=str(boundary),
                mass_residual_kg=str(mass - boundary), mass_bound_kg=str(mtol),
                class_mass_fraction_residual_proxy_kg=str(mass * (sum(frac) - 1)),
                terminal_bulk_fraction_residual_proxy_kg=str(boundary * (sum(frac) - 1)),
                pass_tokens=f, element_tokens=terminal)


def particles(text, elements, dates, width):
    lines = text.splitlines()
    years_count, first = map(int, lines[2].split())
    require(first == min(y for y, j in dates) and years_count == len({y for y, j in dates}), 'PASS calendar header')
    events, subevents, clocks = {}, {}, set()
    i = 6
    while i < len(lines):
        f = lines[i].split(); i += 1
        if not f or f[0] not in ('EVENT', 'SUBEVENT'):
            continue
        expected = 27 if f[0] == 'EVENT' else 9
        while len(f) < expected and i < len(lines):
            f += lines[i].split(); i += 1
        require(len(f) == expected, 'PASS framing')
        y, j = map(int, f[1:3]); clock = (y, j, 3)
        require((y, j) in dates and clock not in clocks, 'PASS duplicate/invalid clock')
        clocks.add(clock)
        for t in f[3:]:
            number(t)
        if f[0] == 'EVENT':
            require(clock in elements, 'Missing EVENT terminal join')
            events[clock] = particle_event(f, elements[clock], width)
        else:
            subevents[clock] = f
    no_event = {k: f for k, f in elements.items() if k[2] == 3 and k not in events and number(f[23]) != 0}
    return dict(events=events, subevents=subevents, no_event=no_event)


def certificate_applicable(old_identity, new_identity, exact_state_certificate=False):
    return exact_state_certificate and old_identity == new_identity


def loss(text, width, years):
    require(text.count('ANNUAL AVERAGE SUMMARIES') == 1, 'Loss summary count')
    before, summary = text.split('ANNUAL AVERAGE SUMMARIES')
    counts = re.findall(r'Number of years\s+(\d+)', summary)
    require(counts == [str(len(years))], 'Loss year count')
    average = re.findall(r'\n\s*(' + NUM + r')\s+kg/m of width', summary)
    require(len(average) == 1, 'Loss average export')
    annual = {}
    pieces = re.split(r'HILLSLOPE\s+1\s+YEARLY SUMMARY FOR\s+(\d+)', before)
    for i in range(1, len(pieces), 2):
        matches = re.findall(r'SEDIMENT LEAVING PROFILE for year\s+\d+\s+(' + NUM + r')\s*kg/m', pieces[i+1])
        require(len(matches) == 1, 'Loss annual export')
        insert(annual, int(pieces[i]), float(number(matches[0])) * width)
    # Loss yearly clock follows printed simulation years, even when source is 2000+.
    require(set(annual) == set(range(1, len(years) + 1)), 'Loss annual calendar')
    average = float(number(average[0])) * width
    delta = sum(annual.values()) / len(years) - average
    require(abs(delta) <= max(.0011 * width, 1e-6 * abs(average)), 'Loss annual/average reconciliation')
    return average, {years[0] + y - 1: x for y, x in annual.items()}


def transition(old_value, new_value, reference):
    before, after = within(old_value, reference), within(new_value, reference)
    return dict(regressed=before and not after, recovered=not before and after)


def within(value, reference):
    require(math.isfinite(reference) and reference >= 0, 'Invalid reference')
    return value is not None and math.isfinite(value) and (.1 <= value / reference <= 10 if reference > 1 else value <= max(1, 10 * reference))


def scores(rows):
    def rate(rs, threshold):
        n = len(rs); count = sum(r['within'] for r in rs)
        return dict(cases=n, passing=count, fraction=count / n if n else None, threshold=threshold,
                    passed=count / n >= threshold if n else True)
    result = {}
    for label, subset in [('all', rows), ('meaningful', [r for r in rows if r['reference'] > 1]), ('small', [r for r in rows if r['reference'] <= 1])]:
        groups = {k: {v: rate([r for r in subset if r['case'][k] == v], .9) for v in values if any(r['case'][k] == v for r in subset)} for k, values in zip(KEYS, VALUES)}
        result[label] = dict(overall=rate(subset, .95), groups=groups)
    return result


def water_comparison(old, new, areas):
    require(old.keys() == new.keys(), 'Water comparison calendar')
    result = []
    for ofe in (1, 2, 3):
        ks = sorted(k for k in old if k[2] == ofe)
        for i, field in enumerate(WAT[3:]):
            a = [old[k][i] for k in ks]; b = [new[k][i] for k in ks]
            delta = [y-x for x, y in zip(a, b)]
            low, high = min(range(len(ks)), key=delta.__getitem__), max(range(len(ks)), key=delta.__getitem__)
            row = dict(ofe=ofe, field=field, unit='m2' if field == 'Area' else 'mm',
                       kind='flux' if field in FLUXES else 'geometry' if field in ('Area', 'ProfileDepth') else 'stock_or_capacity',
                       changed=sum(x != y for x, y in zip(a, b)), negative_old=sum(x < 0 for x in a), negative_new=sum(x < 0 for x in b),
                       minimum_delta=delta[low], minimum_witness=ks[low], maximum_delta=delta[high], maximum_witness=ks[high],
                       old_min=min(a), old_max=max(a), new_min=min(b), new_max=max(b),
                       first_old=a[0], first_new=b[0], last_old=a[-1], last_new=b[-1])
            if field in FLUXES:
                area = sum(areas[:ofe]) if field == 'Q' else areas[ofe-1]
                row.update(old_total_mm=math.fsum(a), new_total_mm=math.fsum(b),
                           old_total_m3=math.fsum(a)*area/1000, new_total_m3=math.fsum(b)*area/1000,
                           delta_total_m3=math.fsum(delta)*area/1000, applied_area_m2=area)
            result.append(row)
    return result


def sparse_changes(old, new, kind):
    fields = ELEMENT if kind == 'element' else EBE
    changes = []; sm = Counter()
    for k in sorted(old.keys() | new.keys()):
        a, b = old.get(k), new.get(k)
        if a is None or b is None:
            changes.append(dict(clock=k, presence='new' if a is None else 'disappeared', old=a, new=b))
            continue
        deltas = []
        for i in range(4 if kind == 'element' else 3, len(fields)):
            if kind == 'element' and i == 11:
                for lane, token in [('old', a[i]), ('new', b[i])]:
                    sm[lane + '_missing' if '*' in token else lane + '_precision_' + str(number(token).as_tuple().exponent)] += 1
                if '*' in a[i] or '*' in b[i]:
                    deltas.append(dict(index=i, field='Sm', old=a[i], new=b[i], kind='missing_display', delta=None))
                    continue
            if number(a[i]) != number(b[i]):
                deltas.append(dict(index=i, field=fields[i], old=a[i], new=b[i], delta=str(number(b[i]) - number(a[i]))))
            elif a[i] != b[i]:
                sm['numeric_equal_token_changed_' + fields[i]] += 1
        if deltas:
            changes.append(dict(clock=k, presence='both', fields=deltas))
    return changes, dict(sm)


def reconcile(elements, ebe, width, years, average, annual):
    terminal = {k: number(f[23]) for k, f in elements.items() if k[2] == 3}
    require(terminal, 'Empty terminal history')
    require(all(k in terminal for k in ebe), 'EBE missing terminal')
    require(all(v == 0 or k in ebe for k, v in terminal.items()), 'Missing sparse sediment event')
    mismatches = []
    for k, f in ebe.items():
        value = number(f[12]); delta = value - terminal[k]
        bound = D('.0505') + abs(value) * D('0.000001')
        if abs(delta) > bound:
            mismatches.append(dict(clock=k, delta_kg_m=str(delta), bound_kg_m=str(bound)))
    mean = float(sum(terminal.values())) * width / len(years)
    bound = (len(terminal) * .0005 / len(years) + .0005) * width + abs(average) * 1e-6
    annual_rows = []
    for y in years:
        values = [float(v)*width for k, v in terminal.items() if k[0] == y]
        annual_bound = (len(values)*.0005 + .0005)*width + abs(annual[y])*1e-6
        annual_rows.append(dict(year=y, element_kg=math.fsum(values), loss_kg=annual[y],
                                loss_bound_kg=annual_bound, reconciled=abs(math.fsum(values)-annual[y]) <= annual_bound,
                                ebe_kg=math.fsum(float(number(f[12]))*width for k, f in ebe.items() if k[0] == y),
                                loss_delta_kg=math.fsum(values)-annual[y]))
    return dict(element_mean_kg_yr=mean, loss_mean_kg_yr=average, delta_kg_yr=mean-average,
                bound_kg_yr=bound, reconciled=abs(mean-average) <= bound and not mismatches and all(r['reconciled'] for r in annual_rows),
                ebe_mismatches=mismatches, annual=annual_rows,
                negative_terminal=[dict(clock=k, kg_m=str(v)) for k, v in terminal.items() if v < 0])


def output_scan(path):
    for line in path.open():
        for token in line.split():
            require(not ('*' in token and re.match(r'^[-+0-9.]', token)), 'Mixed numeric overflow star')
            if token and set(token) == {'*'}:
                if path.name == 'H1.loss.dat':
                    text = line.strip()
                    require(text == '*** CAUTION ***' or (token == '**' and text.startswith(('** Soil Loss (', '** Maximum Soil Loss ', '** Soil Deposition (', '** Maximum Soil Deposition ')) and text.endswith(' **')), 'Unknown loss star')
                else:
                    require(path.name == 'H1.element.dat', 'Star outside Sm')
            try:
                value = float(token.replace('D', 'E'))
            except ValueError:
                continue
            require(math.isfinite(value), f'Nonfinite output {path}')


def load_lane(record, dates, years, bindings, receipt_name):
    folder = Path(record['folder'])
    p = bindings.bind(folder / receipt_name)
    require(json.loads(p.read_text()) == record, 'Aggregate/case receipt drift')
    for section, sub in [('inputs', 'runs'), ('outputs', 'output')]:
        for name, digest in record[section].items():
            require(Path(name).name == name, 'Nonlocal filename')
            bindings.bind(folder / sub / name, digest)
    complete = record.get('status', 'completed' if record['returncode'] == 0 else 'failed') == 'completed'
    if not complete:
        return None
    require(set(record['outputs']) == OUTPUTS, 'Seven-file inventory')
    require({p.name for p in (folder/'output').glob('*.dat')} == OUTPUTS, 'Actual seven-file inventory')
    areas, emitted_width = geometry((folder/'runs/p1.slp').read_text(), record['width_m'], record['profile_length_m'], return_width=True)
    management = (folder/'runs/p1.man').read_text()
    no_contours(management)
    for name in OUTPUTS:
        output_scan(folder/'output'/name)
    water = wat((folder/'output/H1.wat.dat').read_text(), dates, areas)
    element = sparse((folder/'output/H1.element.dat').read_text(), 'element', dates, years[0])
    validate_sm(element, receipt_name == 'record.json')
    event = sparse((folder/'output/H1.ebe.dat').read_text(), 'ebe', dates, years[0])
    loss_text = (folder/'output/H1.loss.dat').read_text()
    receipt_average, _ = loss(loss_text, record['width_m'], years)
    require(receipt_average == record['metrics']['sediment_export_kg_yr'], 'Receipt/report export mismatch')
    average, annual = loss(loss_text, emitted_width, years)
    return dict(areas=areas, emitted_width_m=emitted_width, receipt_width_m=record['width_m'], water=water, element=element, ebe=event, average=average, frozen_score_export=receipt_average,
                reconcile=reconcile(element, event, emitted_width, years, average, annual),
                particle=particles((folder/'output/H1.pass.dat').read_text(), element, dates, emitted_width))


def write_json(path, obj):
    with path.open('x') as f:
        json.dump(obj, f, indent=2, allow_nan=False); f.write('\n')


def read_pair(payload):
    """Pure worker: return results and read bindings; never write files."""
    row, old, task = payload
    bindings = Bindings()
    k = key(row); reference = task['reference_kg_yr']
    dates, years = climate(Path(old['folder'], 'runs/p1.cli').read_text())
    require(set(map(tuple, task['calendar']['dates'])) == dates, 'Declared climate identity')
    score_rows = {}; sparse_rows = []
    oldlane = load_lane(old, dates, years, bindings, 'record.json')
    newlane = load_lane(row, dates, years, bindings, 'receipt.json')
    comp = dict(case=row['case'], old_complete=oldlane is not None, new_complete=newlane is not None, reference=reference,
                capacity_certificate='pending; ordinary outputs do not expose negative-capacity state',
                old_particle_certificate_reused=False)
    for label, lane in [('old', oldlane), ('new', newlane)]:
        value = None if lane is None else lane['frozen_score_export']
        score_rows[label] = dict(case=row['case'], reference=reference, within=within(value, reference), export=value)
        if lane is not None:
            p = lane['particle']; flags = [dict(clock=clock, **f) for clock, f in p['events'].items() if f['causes']]
            comp[label] = dict(frozen_score_export_kg_yr=lane['frozen_score_export'], emitted_width_m=lane['emitted_width_m'], receipt_width_m=lane['receipt_width_m'], reconciliation=lane['reconcile'],
                negative_element_fields=[dict(clock=clock, field=ELEMENT[i], token=f[i]) for clock, f in lane['element'].items() for i in range(4, 26) if '*' not in f[i] and number(f[i]) < 0],
                signed_negative_ebe_fields=[dict(clock=clock, index=i, field=EBE[i], token=f[i], expected_signed_deposition=i in (9, 10)) for clock, f in lane['ebe'].items() for i in range(3, 14) if number(f[i]) < 0],
                particle=dict(events=len(p['events']), subevents=len(p['subevents']), flags=flags,
                no_event_exports=[dict(clock=clock, tokens=f, is_subevent=clock in p['subevents']) for clock, f in p['no_event'].items()]))
    comp.update(transition(None if oldlane is None else oldlane['frozen_score_export'], None if newlane is None else newlane['frozen_score_export'], reference))
    if oldlane and newlane:
        require(oldlane['areas'] == newlane['areas'], 'Geometry lane mismatch')
        comp['water'] = water_comparison(oldlane['water'], newlane['water'], newlane['areas'])
        comp['sparse'] = {}
        for kind in ('element', 'ebe'):
            changes, sm = sparse_changes(oldlane[kind], newlane[kind], kind)
            comp['sparse'][kind] = dict(old_rows=len(oldlane[kind]), new_rows=len(newlane[kind]), changed_rows=len(changes),
                                      presence=dict(Counter(c['presence'] for c in changes)), display=sm)
            for c in changes:
                sparse_rows.append(dict(case=k, output=kind, **c))
        a, b = oldlane['average'], newlane['average']
        comp.update(old_export_kg_yr=a, new_export_kg_yr=b, delta_kg_yr=b-a,
                    relative_change=(b-a)/a if a else None, zero_reference_export=a == 0)
    return comp, score_rows, sparse_rows, bindings.entries


def run():
    # Controls execute without creating files or invoking native code.
    from check_roads_final_readback import controls
    control_results = controls()
    require((ROOT/'results.json').is_file() and (ROOT/'receipt.json').is_file(), 'Aggregate pending: no partial readback')
    bindings = Bindings()
    for p in (Path(__file__), HERE/'check_roads_final_readback.py', HERE/'R02-postrun-readback-scope.md'):
        bindings.bind(p)
    declaration_path = bindings.bind(ROOT/'declaration.json')
    declaration = json.loads(declaration_path.read_text())
    approval = json.loads(bindings.bind(ROOT/'approval.json').read_text())
    require(approval['declaration_sha256'] == sha(declaration_path), 'Approved declaration identity')
    for p, digest in approval['reviews'].items():
        bindings.bind(p, digest)
    for p, digest in declaration['dependencies'].items():
        bindings.bind(p, digest)
    rows = json.loads(bindings.bind(ROOT/'results.json').read_text())
    bindings.bind(ROOT/'receipt.json')
    oldrows = json.loads(bindings.bind(OLD/'roads-results.json').read_text())
    coverage(rows); coverage(oldrows); coverage([t['old'] for t in declaration['tasks']])
    oldmap = {key(r): r for r in oldrows}; tasks = {key(t['old']): t for t in declaration['tasks']}
    # Parent binds every case before workers read; workers return observations only.
    payloads = []
    for row in rows:
        k = key(row); old = oldmap[k]; task = tasks[k]
        require(task['old'] == old and row['inputs'] == old['inputs'], 'Conditioned input identity')
        require(row['binary_sha256'] == task['binary_sha256'], 'Final binary identity')
        bindings.bind(declaration['binary'], row['binary_sha256'])
        reference = task['reference_kg_yr']; require(reference >= 0 and math.isfinite(reference), 'Invalid reference')
        ref_paths = [p for p, h in declaration['dependencies'].items() if h == task['reference_record_sha256'] and p.endswith('/record.json')]
        require(len(ref_paths) == 1, 'Frozen reference binding')
        ref = json.loads(Path(ref_paths[0]).read_text())
        require(ref['metrics']['sediment_export_kg_yr'] == reference, 'Frozen reference metric')
        require(all(ref['inputs'][n] == old['inputs'][n] for n in ('p1.cli', 'p1.man', 'p1.slp')), 'Frozen reference forcing')
        for record, receipt in ((old, 'record.json'), (row, 'receipt.json')):
            folder = Path(record['folder'])
            bindings.bind(folder / receipt)
            for section, sub in [('inputs', 'runs'), ('outputs', 'output')]:
                for name, digest in record[section].items():
                    require(Path(name).name == name, 'Nonlocal filename')
                    bindings.bind(folder / sub / name, digest)
        payloads.append((row, old, task))
    dest = RAW/'R02-readback-v1'; dest.mkdir(exist_ok=False)
    write_json(dest/'controls.json', control_results)
    comparisons = []; score_rows = {'old': [], 'new': []}
    with (dest/'sparse-changes.jsonl').open('x') as stream, ProcessPoolExecutor(max_workers=4) as pool:
        # map preserves declaration/aggregate order despite worker scheduling.
        for comp, pair_scores, sparse_rows, observed in pool.map(read_pair, payloads, chunksize=1):
            require(all(bindings.entries.get(p) == entry for p, entry in observed.items()), 'Worker binding drift')
            for label in ('old', 'new'):
                score_rows[label].append(pair_scores[label])
            for item in sparse_rows:
                stream.write(json.dumps(item, allow_nan=False)+'\n')
            comparisons.append(comp)
            if len(comparisons) % 20 == 0:
                print(f'Read {len(comparisons)}/840', flush=True)
    bindings.check()
    write_json(dest/'case-comparisons.json', comparisons)
    write_json(dest/'bindings.json', bindings.entries)
    write_json(dest/'receipt.json', dict(completed=True, read_workers=4, deterministic_order='aggregate order via pool.map', cases=len(comparisons), failed_old=sum(not r['old_complete'] for r in comparisons),
        failed_new=sum(not r['new_complete'] for r in comparisons), scores={k: scores(v) for k, v in score_rows.items()},
        increased=sum(r.get('delta_kg_yr', 0)>0 for r in comparisons), decreased=sum(r.get('delta_kg_yr', 0)<0 for r in comparisons),
        regressed=sum(r.get('regressed', False) for r in comparisons), recovered=sum(r.get('recovered', False) for r in comparisons),
        capacity_certification='pending', particle_certificate_reuse=False, candidate_admitted=False,
        scientific_flags={lane: dict(reconciliation_failures=sum(not r[lane]['reconciliation']['reconciled'] for r in comparisons if lane in r),
            strict_particle_flags=sum(len(r[lane]['particle']['flags']) for r in comparisons if lane in r),
            negative_water_fields=sum(w['negative_' + lane] > 0 for r in comparisons for w in r.get('water', []))) for lane in ('old', 'new')},
        limitations=['Ordinary-output regression only; no universal water closure or calibration claim.', 'Strict particle flags retained, source-derived disposition pending.', 'Capacity census and exact-state applicability pending.'],
        output_hashes={p.name: sha(p) for p in dest.iterdir() if p.is_file()}))


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    run()
