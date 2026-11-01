"""Independent fresh whole-hillslope response readback; never runs WEPP.

Additive to the frozen failed-isolation reader: active upstream response is
reported, while protected fields and predicted null histories remain exact."""
import argparse
import calendar
from collections import Counter, defaultdict
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import re
import struct
import sys
sys.dont_write_bytecode = True

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
NULL = {'underprediction_less_supply', 'underprediction_not_less_supply',
        'underprediction_other_geometry'}
OUTPUTS = {f'H1.{x}.dat' for x in ('loss', 'soil', 'pass', 'plot', 'wat', 'element', 'ebe')}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def bits(value):
    return struct.unpack('i', struct.pack('f', value))[0]


def load_local(name):
    path = HERE / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_keys(task):
    yield from ((0, 0, 0, ip) for ip in (1, 2, 3))
    for year in range(task['calendar_first_year'], task['calendar_last_year'] + 1):
        for day in range(1, 366 + calendar.isleap(year)):
            for ip in (1, 2, 3):
                yield 1, year, day, ip


def contract_frames(path, task):
    """Validate sequential complete calendar ownership without holding the trace."""
    def lines():
        with path.open() as stream:
            for number, line in enumerate(stream, 1):
                fields = line.split()
                assert len(fields) == 13, (path, number)
                phase, year, day, ip, index, mode = map(int, fields[1:7])
                values = tuple(map(float, fields[7:]))
                assert all(math.isfinite(v) for v in values), (path, number)
                assert mode == task['mode']
                yield (phase, year, day, ip), fields[0], index, values
    anchors = {}
    actual = itertools.groupby(lines(), key=lambda row: row[0])
    sentinel = object()
    for expected, group in itertools.zip_longest(expected_keys(task), actual, fillvalue=sentinel):
        assert expected is not sentinel and group is not sentinel, ('calendar extent', path)
        key, rows = group
        assert key == expected, ('calendar ordering/ownership', key, expected)
        phase, year, day, ip = key
        frame = {}
        for _, tag, index, values in rows:
            assert (tag, index) not in frame, ('duplicate state row', key, tag, index)
            frame[tag, index] = values
        required = {('RRC_STATE', 0), ('RRC_BITS', 0), ('RRC_DENSITY', 1),
                    ('RRC_DENSITY', 2), ('RRC_DRIVERS', 0), ('RRC_CONTEXT', 0)}
        if phase:
            required.add(('RRC_RESIDUE', 0))
        assert required <= frame.keys()
        assert frame.keys() <= required | ({('RRC_DECAY', 1), ('RRC_DECAY', 2)} if phase else set())
        state, encoded = frame['RRC_STATE', 0], frame['RRC_BITS', 0]
        assert all(v == int(v) for v in encoded)
        assert tuple(bits(v) for v in state[:5]) == encoded[:5]
        if not phase:
            assert len(set(encoded[:5])) == 1
            anchors[ip] = encoded[2]
        assert encoded[2] == anchors[ip]
        context = frame['RRC_CONTEXT', 0]
        assert context[:3] == (3, 1, 1)
        assert context[4] == (0 if phase else -1)
        assert frame['RRC_DRIVERS', 0][4] == 0  # configured IRSYST
        if ip == 3:
            assert context[3] == 0 and encoded[3] == encoded[4]
            if task['mode'] == 1:
                assert encoded[1] == encoded[2]
            if task['expected_null']:
                assert encoded[0] == encoded[2], ('predicted null failed', key)
        if task['mode'] == 0 or ip != 3:
            assert encoded[0] == encoded[1], ('undeclared assignment', key)
        yield key, frame


def compare_contracts(off, on):
    paths = [Path(t['folder']) / 'observations/roughness-contract.txt' for t in (off, on)]
    counts = Counter()
    responses = defaultdict(lambda: {'different_calls': 0, 'first_difference': None,
                                     'maximum_absolute_difference': 0.0})
    sentinel = object()
    for left, right in itertools.zip_longest(contract_frames(paths[0], off), contract_frames(paths[1], on), fillvalue=sentinel):
        assert left is not sentinel and right is not sentinel
        key, a = left
        other, b = right
        assert key == other
        phase, year, day, ip = key
        counts['calls'] += 1
        counts['daily_calls' if phase else 'initialization_calls'] += 1
        if on['expected_null']:
            assert a == b, ('predicted-null state drift', key)
        for tag in ('RRC_DENSITY', 'RRC_DRIVERS', 'RRC_CONTEXT'):
            assert {k: v for k, v in a.items() if k[0] == tag} == {k: v for k, v in b.items() if k[0] == tag}, ('protected state/driver', key, tag)
        counts['changed_buffer_restores'] += int(ip == 3 and b['RRC_BITS', 0][0] != b['RRC_BITS', 0][1])
        # Record every supported field in all OFEs; never impute a missing
        # conditional producer as zero. Values retain the frozen map's units.
        for frame_key in sorted(a.keys() | b.keys()):
            tag, index = frame_key
            av, bv = a.get(frame_key), b.get(frame_key)
            if av is None or bv is None:
                counts[f'ofe{ip}_{tag}_{index}_only_{"on" if av is None else "off"}'] += 1
                continue
            for field, (x, y) in enumerate(zip(av, bv), 1):
                if x == y:
                    continue
                label = f'ofe{ip}:{tag}:{index}:v{field}'
                row = responses[label]
                row['different_calls'] += 1
                if row['first_difference'] is None:
                    row['first_difference'] = {'key': key, 'off': x, 'on': y}
                row['maximum_absolute_difference'] = max(row['maximum_absolute_difference'], abs(y-x))
    assert counts['initialization_calls'] == 3
    if not on['expected_null']:
        assert counts['changed_buffer_restores'] > 0
    return {'counts': dict(counts), 'endogenous_and_treatment_responses': dict(responses),
            'trace_sha256': [sha(p) for p in paths]}


def published_upstream(path):
    """OFE is the isolated first integer in these three native output families."""
    result = []
    for line in path.read_bytes().splitlines(keepends=True):
        match = re.match(rb'^\s+([123])\s+\d', line)
        if match and int(match[1]) < 3:
            result.append(line)
    assert result, path
    return result


def published_table_delta(left_path, right_path, expected_null):
    """Canonical parsed fields retain printed units and numeric unavailability."""
    maps = []
    columns = None
    for path in (left_path, right_path):
        table = pq.read_table(path)
        assert columns is None or columns == table.column_names
        columns = table.column_names
        rows = [r for r in table.to_pylist() if r['OFE'] in (1, 2)]
        values = {}
        for row in rows:
            key = row['year'], row['julian'], row['OFE']
            assert key not in values, ('duplicate published support', path, key)
            assert all(v is None or not isinstance(v, float) or math.isfinite(v) for v in row.values())
            values[key] = row
        assert values, path
        maps.append(values)
    a, b = maps
    common = sorted(set(a).intersection(b))
    changed = [k for k in common if a[k] != b[k]]
    fields = {}
    for name in columns:
        different = [k for k in changed if a[k][name] != b[k][name]]
        if not different:
            continue
        numeric = [abs(b[k][name] - a[k][name]) for k in different
                   if isinstance(a[k][name], (int, float)) and isinstance(b[k][name], (int, float))]
        first = different[0]
        fields[name] = dict(changed_rows=len(different),
            first=dict(key=list(first), off=a[first][name], on=b[first][name]),
            maximum_absolute_difference=max(numeric) if numeric else None,
            availability_changes=sum(a[k][name] is None or b[k][name] is None for k in different))
    only_off, only_on = sorted(set(a)-set(b)), sorted(set(b)-set(a))
    result = dict(off_rows=len(a), on_rows=len(b), common_rows=len(common), changed_common_rows=len(changed),
        only_off_rows=len(only_off), only_on_rows=len(only_on),
        first_only_off=list(only_off[0]) if only_off else None,
        first_only_on=list(only_on[0]) if only_on else None,
        first_changed_key=list(changed[0]) if changed else None,
        fields=fields, exact=not (changed or only_off or only_on))
    if expected_null:
        assert result['exact'], ('predicted-null published drift', left_path, right_path)
    return result


def annual_report(path, width):
    text = path.read_text()
    matches = re.findall(r'AVERAGE ANNUAL SEDIMENT LEAVING PROFILE\s+([\d.Ee+\-]+)\s+kg/m of width', text)
    assert len(matches) == 1
    annual = re.findall(r'SEDIMENT LEAVING PROFILE for year\s+(\d+)\s+([\d.Ee+\-]+)\s+kg/m', text)
    assert len(annual) == 16 and len({y for y, _ in annual}) == 16
    return float(matches[0]) * width


def envelope(value, reference):
    assert value >= 0 and reference >= 0 and math.isfinite(value + reference)
    return 0.1 * reference <= value <= 10 * reference if reference > 1 else value <= max(1, 10 * reference)


def friction_phases(group):
    """Separate IRS-era observations from the owned CONTIN sediment call."""
    owners = [r for r in group if r['tag'] == 'BP_OWNER']
    params = [r for r in group if r['tag'] == 'BP_PARAM_ENTER']
    assert len(owners) == 1 and len(params) <= 1
    friction = [r for r in group if r['tag'] == 'RP_FRICTION']
    early = [r for r in friction if r['line'] < owners[0]['line']]
    late = [r for r in friction if r['line'] > owners[0]['line']]
    assert len(late) == len(params), 'CONTIN-owned friction coverage'
    if params:
        assert owners[0]['line'] < late[0]['line'] < params[0]['line']
    return {'before_CONTIN_owner': len(early), 'CONTIN_sediment_call': len(late),
            'scope': 'Earlier rows retain hydrology-stage friction; individual IRS callsites are not distinguished by this tag.'}


def lane_readback(task, declaration, observer, particles):
    folder = Path(task['folder'])
    record = read(folder / 'record.json')
    assert all(record[k] == v for k, v in task.items())
    assert record['binary_sha256'] == declaration['binary_sha256']
    assert record['completed'] and record['returncode'] == 0 and record['physical_pass']
    assert record['audit']['physical_pass'] and record['coverage']['passed'] and record['state_contract']['passed']
    original_path = Path(task['source_record'])
    assert sha(original_path) == task['source_record_sha256']
    original = read(original_path)
    assert original['outputs'] == task['reference_outputs']
    assert set(record['outputs']) == OUTPUTS
    for n, h in record['outputs'].items():
        assert sha(folder / 'output' / n) == h
        assert sha(original_path.parent / 'output' / n) == original['outputs'][n]
    must_equal = task['mode'] == 0 or task['expected_null']
    parity = record['outputs'] == original['outputs']
    assert record['ordinary_output_parity'] == parity
    if must_equal:
        assert parity and record['metrics'] == original['metrics'] and record['audit'] == original['audit']
    for n, h in (task['inputs'] | task['auxiliary_inputs']).items():
        assert sha(folder / 'runs' / n) == sha(original_path.parent / 'runs' / n) == h
    for n, h in record['execution_logs'].items():
        assert sha(folder / 'runs' / n) == h
    assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (folder / 'runs/stdout').read_text()
    for n, h in record['observer_files'].items():
        assert sha(folder / 'observations' / n) == h
    assert (folder / 'observations/roughness-control.txt').read_text() == f"{task['mode']} 3\n"
    particle = particles.audit(folder / 'record.json')
    assert particle == read(folder / 'particle-audit.json') and particle['passed'] and not particle['flags']
    rows = observer.trace_rows(folder / 'observations/buffer-observation.txt', task)
    groups = defaultdict(list)
    for row in rows:
        if row['ofe']:
            groups[row['day'], row['ofe']].append(row)
    assert set(groups) == {(d, ip) for d in (task['event']['julian']-1, task['event']['julian']) for ip in (1, 2, 3)}
    summaries = []
    for key, group in sorted(groups.items()):
        summary = observer.summarize_group(group, groups, *key)
        counts = Counter(r['tag'] for r in group)
        assert counts['RP_CTCARR'] == 1
        assert counts['RP_CRUST_ACTIVE'] + counts['RP_CRUST_INACTIVE'] == 1
        assert counts['RP_IR_DELIVERY'] == counts['BP_PARAM']
        assert counts['RP_IR_CLASS'] == 5 * counts['RP_IR_DELIVERY']
        summary['friction_phase_coverage'] = friction_phases(group)
        summary['roughness_consumer_rows'] = [r for r in group if r['tag'].startswith('RP_')]
        summaries.append(summary)
    metric = annual_report(folder / 'output/H1.loss.dat', task['width_m'])
    assert metric == record['metrics']['sediment_export_kg_yr']
    return {'record': record, 'annual_sediment_kg_yr': metric, 'bounded_process': summaries,
            'trace_rows': len(rows), 'particle_event_count': particle.get('event_count'),
            'bindings': {str(p.resolve()): sha(p) for p in (folder/'record.json', folder/'particle-audit.json',
                folder/'observations/roughness-contract.txt', folder/'observations/buffer-observation.txt', original_path)}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--first-pair', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    root = args.root.resolve()
    reader_declaration_path = HERE/'buffer-roughness-hillslope-response-r4-u2-independent-reader-declaration.json'
    reader_declaration = read(reader_declaration_path)
    assert root == Path(reader_declaration['execution_root']).resolve()
    for p,h in reader_declaration['bindings'].items():
        assert sha(p) == h, p
    declaration = read(root/'execution-declaration.json')
    build = read(root/'build-receipt.json')
    assert build['returncode'] == 0
    assert sha(root/'build/src/wepp') == declaration['binary_sha256'] == build['binary_sha256'] == '08ad4c67150a01e7487fda677ffd2fe6d3d39e297b820bb875fbb6de13404a14'
    for p, h in declaration['dependencies'].items():
        assert sha(p) == h, p
    assert {str(p.relative_to(root/'build/src')) for p in (root/'build/src').rglob('*') if p.is_file()} == set(build['postbuild_inventory'])
    for n, h in build['postbuild_inventory'].items():
        assert sha(root/'build/src'/n) == h
    seeds = read(root.parent/'seeds.json')['seeds']
    assert len(seeds) == 9
    by_seed = {s['stratum']: s for s in seeds}
    gate = root/('preflight.json' if args.first_pair else 'verification.json')
    gate_data = read(gate)
    assert gate_data['passed']
    assert gate_data['execution_declaration_sha256'] == sha(root/'execution-declaration.json')
    tasks = declaration['tasks'][:4] if args.first_pair else declaration['tasks']
    assert len(tasks) == (4 if args.first_pair else 36)
    selected_seeds = seeds[:1] if args.first_pair else seeds
    assert {(t['stratum'], t['lane'], t['mode']) for t in tasks} == {(s['stratum'], lane, mode) for s in selected_seeds for lane in ('legacy', 'modern') for mode in (0, 1)}
    observer = load_local('review_buffer_observer_runtime_r4.py')
    particles = load_local('audit_particle_closure_v2.py')
    results, bindings = [], {}
    for index in range(0, len(tasks), 2):
        off, on = tasks[index:index+2]
        assert off['mode'] == 0 and on['mode'] == 1
        assert (off['stratum'], off['lane']) == (on['stratum'], on['lane'])
        seed = by_seed[off['stratum']]
        expected_null = off['lane'] == 'legacy' or off['stratum'] in NULL
        assert off['expected_null'] == on['expected_null'] == expected_null
        for task in (off, on):
            assert task['event'] == seed['event']
            assert task['calendar_first_year'] == seed['calendar_first_year']
            assert task['calendar_last_year'] == seed['calendar_last_year']
            assert task['calendar_last_year']-task['calendar_first_year'] == 15
            assert task['source_record_sha256'] == seed['input_records'][task['lane']]['sha256']
        lr = [lane_readback(t, declaration, observer, particles) for t in (off, on)]
        states = compare_contracts(off, on)
        a, b = map(lambda t: Path(t['folder']), (off, on))
        upstream = {}
        paired = [p for p in gate_data['pairs'] if (p['stratum'], p['lane']) == (off['stratum'], off['lane'])]
        assert len(paired) == 1 and paired[0]['passed']
        paired = paired[0]
        expected_paths = {str((folder/relative).resolve()) for folder in (a,b) for relative in
            ('output/interchange/H.wat.parquet','output/interchange/H.element.parquet','derived/H.soil.parquet')}
        actual_paths = {str(Path(p).resolve()):h for p,h in paired['table_bindings'].items()}
        assert set(actual_paths) == expected_paths
        for p,h in actual_paths.items():
            assert sha(p) == h
            bindings[p] = h
        for kind, relative, native in (
            ('WAT','output/interchange/H.wat.parquet','H1.wat.dat'),
            ('ELEMENT','output/interchange/H.element.parquet','H1.element.dat'),
            ('SOIL','derived/H.soil.parquet','H1.soil.dat')):
            delta = published_table_delta(a/relative,b/relative,expected_null)
            assert delta == paired['upstream_response']['published_tables'][kind]
            raw_off, raw_on = published_upstream(a/'output'/native), published_upstream(b/'output'/native)
            if expected_null:
                assert raw_off == raw_on
            upstream[kind] = dict(canonical_fields=delta, raw_upstream_rows_off_on=[len(raw_off),len(raw_on)],
                raw_upstream_rows_exact=raw_off==raw_on,
                units='Canonical printed units; ELEMENT Ki/Kr retain native printed scale, SOIL Ki/Kr are adjustment factors.')
        if expected_null:
            assert sha(a/'observations/buffer-observation.txt') == sha(b/'observations/buffer-observation.txt')
        reference = seed['case_summary']['reference_kg_yr']
        annual = [r['annual_sediment_kg_yr'] for r in lr]
        results.append({'stratum': off['stratum'], 'lane': off['lane'], 'expected_null': expected_null,
            'state_contract': states, 'upstream_responses': upstream, 'reference_kg_yr': reference,
            'annual_off_on_kg_yr': annual, 'annual_delta_kg_yr': annual[1]-annual[0],
            'original_envelope_off_on_pass': [envelope(v, reference) for v in annual],
            'bounded_process_off_on': [r['bounded_process'] for r in lr],
            'bounded_trace_row_counts': [r['trace_rows'] for r in lr]})
        for r in lr:
            bindings.update(r['bindings'])
    for p, h in declaration['dependencies'].items():
        assert sha(p) == h
    for p in (root/'execution-declaration.json', root/'build-receipt.json', root.parent/'seeds.json', gate,
              Path(__file__).resolve(), HERE/'review_buffer_observer_runtime_r4.py', HERE/'audit_particle_closure_v2.py'):
        bindings[str(p.resolve())] = sha(p)
    bindings[str(reader_declaration_path.resolve())] = sha(reader_declaration_path)
    for p,h in reader_declaration['bindings'].items():
        assert sha(p) == h, p
    modern = [r for r in results if r['lane'] == 'modern']
    recovery = [r['stratum'] for r in modern if r['original_envelope_off_on_pass'] == [False, True]]
    regressions = [r['stratum'] for r in modern if r['original_envelope_off_on_pass'] == [True, False]]
    report = {'independent_runtime_readback_passed': True, 'accepted_causal_interpretation': False,
        'accepted_parameterization': False, 'full_period_runs': len(tasks), 'pairs': results,
        'modern_envelope_recoveries': recovery, 'modern_envelope_regressions': regressions,
        'selected_panel_improvement_criterion': None if args.first_pair else bool(recovery) and not regressions,
        'accepted_original_isolation': False,
        'scope': 'Fresh whole-hillslope response contract. Native model never executed by reviewer. Active upstream modeled responses allowed and reported; all null and BD/POR/driver controls exact. Canonical numeric unavailability is not zero. Net grid exchange is not gross production or tagged provenance. No physical routing validation.',
        'bindings': bindings}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'passed': True, 'runs': len(tasks), 'recoveries': recovery, 'regressions': regressions}))


if __name__ == '__main__':
    main()
