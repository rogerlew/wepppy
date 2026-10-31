"""Independent observer readback; never executes WEPP or imports its runner."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def trace_rows(path, task):
    rows = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split()
        assert len(fields) == 11, (path, line_number)
        year, day, ofe, index = map(int, fields[1:5])
        values = list(map(float, fields[5:]))
        assert all(math.isfinite(value) for value in values)
        assert year == task['event']['year']
        assert day in (task['event']['julian'] - 1, task['event']['julian'])
        assert ofe in (0, 1, 2, 3)
        rows.append({'tag': fields[0], 'year': year, 'day': day,
                     'ofe': ofe, 'index': index, 'values': values,
                     'line': line_number})
    return rows


def summarize_group(rows, all_groups, day, ofe):
    by = defaultdict(list)
    for row in rows:
        by[row['tag']].append(row)
    for tag in ('BP_OWNER', 'BP_OFE_END', 'BP_GEOMETRY', 'BP_OWNER_FORCING'):
        assert len(by[tag]) == 1, (day, ofe, tag)
    for tag in ('BP_WBH_ALLOC', 'BP_WBH_SOURCE', 'BP_WBH_FLUX', 'BP_WBH_RETURN'):
        assert sorted(r['index'] for r in by[tag]) == list(range(1, 25)), (day, ofe, tag)
    for stem in ('BP_SOIL', 'BP_DAY_END', 'BP_WBH_BEFORE', 'BP_WBH_AFTER'):
        left = [r['index'] for r in by[stem + '_W']]
        right = [r['index'] for r in by[stem + '_K']]
        assert left and left == right and len(left) == len(set(left))

    # Reconstruct the represented GRNA storage from its consumed raw operands.
    # Residuals are diagnostics, not a new acceptance tolerance or soil budget.
    capacities = []
    pending = []
    for row in rows:
        if row['tag'] in ('BP_GA_LOCAL_LAYER', 'BP_GA_UP_LAYER'):
            pending.append(row)
        if row['tag'] == 'BP_GA_STORAGE':
            assert pending and len(by['BP_EQUIV']) == 1
            efflen = by['BP_EQUIV'][0]['values'][2]
            assert efflen > 0
            contributors = defaultdict(list)
            for item in pending:
                contributor, layer = divmod(item['index'], 100)
                assert layer in (1, 2)
                contributors[contributor].append(item)
            weighted = 0.0
            detail = []
            for contributor, layers in sorted(contributors.items()):
                assert sorted(r['index'] % 100 for r in layers) == [1, 2]
                length = layers[0]['values'][4]
                assert length > 0 and all(r['values'][4] == length for r in layers)
                capacity = math.fsum(max(r['values'][5] - r['values'][0], 0.0) for r in layers)
                weighted += length * capacity
                detail.append({'ofe': contributor, 'length_m': length,
                               'available_capacity_m_double_reconstruction': capacity,
                               'consumed_layers': layers})
            reconstructed = weighted / efflen
            capacities.append({'observed_storage_m': row['values'][0],
                               'reconstructed_storage_m_double': reconstructed,
                               'residual_m': row['values'][0] - reconstructed,
                               'effective_length_m': efflen,
                               'sum_contributor_lengths_m': math.fsum(x['length_m'] for x in detail),
                               'percolation_coefficient_m_s': row['values'][1],
                               'contributors': detail})
            pending = []
    assert not pending
    assert len(capacities) == len(by['BP_GA_OUT'])

    decision = by['BP_ROUTE_DECISION']
    assert len(decision) <= 1
    routed = bool(decision and decision[0]['values'][0] == 1)
    for tag in ('BP_ROUTE_IN_SCALE', 'BP_ROUTE_OUT_SCALE', 'BP_SLOSS_OUT_SCALE'):
        assert len(by[tag]) == int(routed), (day, ofe, tag)
    handoff = None
    if routed:
        entering = by['BP_ROUTE_IN_SCALE'][0]['values']
        leaving = by['BP_SLOSS_OUT_SCALE'][0]['values']
        flow = by['BP_SLOSS_OUT_FLOW'][0]['values']
        norm, tcend, rill_width, spacing, duration, incoming_rate = entering
        assert spacing > 0 and duration >= 0
        event_scale = duration * tcend * rill_width / spacing
        entering_event = norm * event_scale
        outgoing_event = flow[3] * event_scale
        class_rows = by['BP_CLASS_IN']
        incoming_classes = None
        if class_rows:
            assert sorted(r['index'] for r in class_rows) == [1, 2, 3, 4, 5]
            incoming_classes = [{'class': r['index'], 'fraction': r['values'][0],
                                 'rate_kg_m_s': r['values'][0] * r['values'][1]}
                                for r in class_rows]
        upstream_end = None
        if ofe > 1:
            upstream = [r for r in all_groups[(day, ofe - 1)] if r['tag'] == 'BP_OFE_END']
            assert len(upstream) == 1
            upstream_end = upstream[0]['values'][2]
        grid = by['BP_GRID']
        assert sorted(r['index'] for r in grid) == list(range(2, 102))
        grid_sorted = sorted(grid, key=lambda r: r['index'])
        assert all(left['values'][3] == right['values'][2]
                   for left, right in zip(grid_sorted, grid_sorted[1:]))
        diffs = [r['values'][3] - r['values'][2] for r in grid_sorted]
        handoff = {'incoming_scale_raw': entering, 'outgoing_scale_raw': leaving,
                   'incoming_rate_kg_m_s': incoming_rate,
                   'incoming_class_rates': incoming_classes,
                   'incoming_event_using_current_duration_kg_m': entering_event,
                   'upstream_published_event_kg_m': upstream_end,
                   'incoming_event_minus_upstream_event_kg_m': None if upstream_end is None else entering_event - upstream_end,
                   'normalized_outgoing_event_kg_m_double_reconstruction': outgoing_event,
                   'observed_outgoing_event_kg_m': by['BP_OFE_END'][0]['values'][2],
                   'grid_first_event_kg_m': grid_sorted[0]['values'][2],
                   'grid_last_event_kg_m': grid_sorted[-1]['values'][3],
                   'grid_positive_net_exchange_kg_m': math.fsum(max(v, 0.0) for v in diffs),
                   'grid_negative_net_exchange_kg_m': math.fsum(min(v, 0.0) for v in diffs),
                   'grid_net_exchange_kg_m': math.fsum(diffs),
                   'warning': 'Grid signs are resolved net exchange, not gross subgrid production/deposition. Incoming receiving-duration mass and upstream published event mass are distinct support quantities.'}
    scalar_tags = ('BP_OWNER', 'BP_OFE_END', 'BP_GEOMETRY', 'BP_OWNER_FORCING',
                   'BP_IRS_LOCAL', 'BP_EQUIV', 'BP_RUNON_CAP', 'BP_ROCHEK_ENTER',
                   'BP_ROCHEK_OUT', 'BP_GA_OUT', 'BP_IRS_OUT', 'BP_ROUTE_DECISION',
                   'BP_SOIL_DENSITY', 'BP_SOIL_ROUGH', 'BP_SOIL_DECAY',
                   'BP_SOIL_DECAY_OUT', 'BP_PARAM', 'BP_ERODIBILITY', 'BP_STRESS')
    return {'day': day, 'ofe': ofe, 'route_entered': routed,
            'raw_operands': {tag: by[tag] for tag in scalar_tags if by[tag]},
            'ga_capacity': capacities, 'sediment_handoff': handoff,
            'hourly_local_depth_sums_m': {
                'allocated_fin': math.fsum(r['values'][0] for r in by['BP_WBH_ALLOC']),
                'outgoing_surface_return': math.fsum(r['values'][0] for r in by['BP_WBH_FLUX']),
                'outgoing_lateral': math.fsum(r['values'][1] for r in by['BP_WBH_FLUX']),
                'deep_percolation': math.fsum(r['values'][4] for r in by['BP_WBH_FLUX'])},
            'hourly_upstream_depth_sums_m': {
                'incoming_surface_return': math.fsum(r['values'][0] for r in by['BP_WBH_SOURCE']),
                'incoming_lateral': math.fsum(r['values'][1] for r in by['BP_WBH_SOURCE'])}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--first-pair', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    declaration = read(args.root / 'execution-declaration.json')
    build = read(args.root / 'build-receipt.json')
    assert build['returncode'] == 0
    assert declaration['binary_sha256'] == build['binary_sha256'] == sha(args.root / 'build/src/wepp')
    for name, expected in declaration['dependencies'].items():
        assert sha(name) == expected, name
    tasks = declaration['tasks'][:2] if args.first_pair else declaration['tasks']
    assert len(tasks) == (2 if args.first_pair else 18)
    if args.first_pair:
        assert read(args.root / 'preflight.json')['passed']
    results = []
    output_count = 0
    bound = {}
    for task in tasks:
        folder = Path(task['folder'])
        record_path = folder / 'record.json'
        record = read(record_path)
        assert all(record[key] == value for key, value in task.items())
        assert record['completed'] and record['returncode'] == 0
        assert record['physical_pass'] and record['ordinary_output_parity'] and record['coverage']['passed']
        source_path = Path(task['source_record'])
        assert sha(source_path) == task['source_record_sha256']
        source = read(source_path)
        assert record['metrics'] == source['metrics'] and record['audit'] == source['audit']
        assert source['outputs'] == task['reference_outputs'] == record['outputs']
        assert len(record['outputs']) == 7
        for name, expected in record['outputs'].items():
            assert sha(folder / 'output' / name) == expected
            assert sha(source_path.parent / 'output' / name) == expected
            output_count += 1
        for name, expected in (task['inputs'] | task['auxiliary_inputs']).items():
            assert sha(folder / 'runs' / name) == expected
            assert sha(source_path.parent / 'runs' / name) == expected
        for name, expected in record['execution_logs'].items():
            assert sha(folder / 'runs' / name) == expected
        assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (folder / 'runs/stdout').read_text()
        for name, expected in record['observer_files'].items():
            assert sha(folder / 'observations' / name) == expected
        particle = read(folder / 'particle-audit.json')
        assert particle['passed'] and not particle['flags']
        trace = folder / 'observations/buffer-observation.txt'
        assert sha(trace) == record['coverage']['trace_sha256']
        groups = defaultdict(list)
        rows = trace_rows(trace, task)
        for row in rows:
            if row['ofe']:
                groups[(row['day'], row['ofe'])].append(row)
        expected_groups = {(day, ofe) for day in (task['event']['julian'] - 1, task['event']['julian'])
                           for ofe in (1, 2, 3)}
        assert set(groups) == expected_groups
        summaries = [summarize_group(group, groups, *key) for key, group in sorted(groups.items())]
        results.append({'stratum': task['stratum'], 'lane': task['lane'],
                        'trace_rows': len(rows), 'trace_sha256': sha(trace), 'day_ofe': summaries})
        for path in (record_path, source_path, trace, folder / 'particle-audit.json'):
            bound[str(path)] = sha(path)
    for name, expected in declaration['dependencies'].items():
        assert sha(name) == expected, name
    for path in (args.root / 'execution-declaration.json', args.root / 'build-receipt.json',
                 args.root / 'observer-map.json', Path(__file__).resolve()):
        bound[str(path)] = sha(path)
    report = {'runtime_and_exact_output_readback_passed': True,
              'accepted_mechanistic_interpretation': False,
              'scope': 'Independent structural/hash readback and diagnostic operand reconstruction; no native runs. Derived residuals are not new acceptance tolerances.',
              'lanes': len(tasks), 'ordinary_output_pairs_rehashed': output_count,
              'results': results, 'evidence_sha256': bound}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'passed': True, 'lanes': len(tasks), 'ordinary_outputs': output_count}))


if __name__ == '__main__':
    main()
