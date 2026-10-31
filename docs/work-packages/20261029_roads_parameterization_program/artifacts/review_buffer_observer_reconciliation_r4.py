"""Independent printed-boundary and class-sign review of accepted O3 traces."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import struct

import pyarrow.parquet as pq


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def single(value):
    return struct.unpack('f', struct.pack('f', value))[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--observer', type=Path, required=True)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--independent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    own = read(args.independent)
    assert own['runtime_and_exact_output_readback_passed'] and own['lanes'] == 18
    for path, expected in own['evidence_sha256'].items():
        assert sha(path) == expected
    declaration = read(args.analysis / 'declaration.json')
    for path, expected in declaration['dependencies'].items():
        assert sha(path) == expected
    analysis = read(args.analysis / 'results.json')
    reconciliation = read(args.analysis / 'reconciliation.json')
    assert sha(args.analysis / 'results.json') == reconciliation['results_sha256']
    indexed = {(r['stratum'], r['lane']): r for r in analysis}
    own_indexed = {(r['stratum'], r['lane']): r for r in own['results']}
    sediment_checks = []
    water_checks = []
    missing = []
    counts = Counter()
    minima = defaultdict(lambda: math.inf)
    target_rows = []
    double_sum_order_differences = []
    for task in read(args.observer / 'execution-declaration.json')['tasks']:
        key = (task['stratum'], task['lane'])
        ours = own_indexed[key]
        theirs = indexed[key]
        folder = Path(task['folder'])
        ledger_path = args.ledger / 'cases' / task['event']['case_id'] / f"{task['lane']}-daily-ofe.parquet"
        selected = {(r['julian'], r['OFE']): r for r in pq.read_table(ledger_path).to_pylist()
                    if r['year'] == task['event']['year']
                    and r['julian'] in (task['event']['julian'] - 1, task['event']['julian'])}
        water = {}
        for line in (folder / 'output/H1.wat.dat').read_text().splitlines():
            fields = line.split()
            if fields and fields[0].isdigit() and int(fields[2]) == task['event']['year']:
                pair = int(fields[1]), int(fields[0])
                if pair in selected:
                    assert pair not in water
                    water[pair] = fields[5]
        assert len(selected) == len(water) == 6
        for row, other in zip(ours['day_ofe'], theirs['day_ofe'], strict=True):
            day, ofe = row['day'], row['ofe']
            assert (day, ofe) == (other['day'], other['ofe'])
            raw = row['raw_operands']
            end = raw['BP_OFE_END'][0]['values']
            geometry = raw['BP_GEOMETRY'][0]['values']
            ledger = selected[(day, ofe)]
            if ledger['element_present']:
                residual = Decimal.from_float(end[2]) - Decimal(str(ledger['sediment_out_kg_m']))
                assert abs(residual) <= Decimal('.0005')
                sediment_checks.append({'stratum': key[0], 'lane': key[1], 'day': day, 'ofe': ofe,
                                        'difference_kg_m': str(residual), 'bound_kg_m': '.0005'})
            else:
                missing.append({'stratum': key[0], 'lane': key[1], 'day': day, 'ofe': ofe,
                                'field': 'ELEMENT absent', 'native_observed_kg_m': end[2]})
            irs = raw.get('BP_IRS_OUT', [])
            if irs:
                # Native REAL operation order of the published cumulative Q.
                q = single(single(single(end[1] * 1000.0) * irs[0]['values'][3]) / geometry[2])
            else:
                assert end[1] == 0.0
                q = 0.0
            token = Decimal(water[(day, ofe)])
            bound = Decimal(5).scaleb(token.as_tuple().exponent - 1)
            residual = Decimal.from_float(q) - token
            assert abs(residual) <= bound
            water_checks.append({'stratum': key[0], 'lane': key[1], 'day': day, 'ofe': ofe,
                                 'difference_mm': str(residual), 'printed_bound_mm': str(bound),
                                 'matches_printing_interval': True})
            assert len(row['ga_capacity']) == len(other['ga_capacity'])
            for left, right in zip(row['ga_capacity'], other['ga_capacity'], strict=True):
                assert left['observed_storage_m'] == right['observed_storage_m']
                reconstructed = math.fsum(
                    c['available_capacity_m_double_reconstruction'] * c['length_m']
                    for c in left['contributors']) / left['effective_length_m']
                assert reconstructed == right['double_reconstructed_storage_m']
                if reconstructed != left['reconstructed_storage_m_double']:
                    double_sum_order_differences.append({
                        'stratum': key[0], 'lane': key[1], 'day': day, 'ofe': ofe,
                        'sequential_minus_compensated_double_m':
                            left['reconstructed_storage_m_double'] - reconstructed})
            if day == task['event']['julian'] and ofe == 3:
                target_rows.append({'stratum': key[0], 'lane': key[1], 'day': day,
                                    'raw_operands': raw, 'capacity': row['ga_capacity'],
                                    'sediment_handoff': row['sediment_handoff']})
        trace = folder / 'observations/buffer-observation.txt'
        assert sha(trace) == ours['trace_sha256'] == theirs['trace_sha256']
        for line in trace.read_text().splitlines():
            fields = line.split()
            tag = fields[0]
            if tag in ('BP_CLASS_IN', 'BP_ROUTE_OUT_CLASS', 'BP_SLOSS_OUT_CLASS',
                       'BP_ENRICH_CLASS', 'BP_ENRICH_FINAL'):
                value = float(fields[5])
                assert math.isfinite(value) and value >= 0.0
                counts[tag] += 1
                minima[tag] = min(minima[tag], value)
    assert sediment_checks == reconciliation['sediment'] and len(sediment_checks) == 90
    assert water_checks == reconciliation['water'] and len(water_checks) == 108
    assert missing == reconciliation['unavailable'] and len(missing) == 18
    caps = [c for r in own['results'] for g in r['day_ofe'] for c in g['ga_capacity']]
    assert len(caps) == reconciliation['reconstructed_grna_calls'] == 76
    assert max(abs(c['residual_m']) for c in caps) == reconciliation['max_storage_double_reconstruction_residual_m']
    for path, expected in declaration['dependencies'].items():
        assert sha(path) == expected
    files = [args.independent, args.analysis / 'declaration.json', args.analysis / 'results.json',
             args.analysis / 'reconciliation.json', Path(__file__).resolve()]
    result = {'passed': True, 'scope': 'Independent printed-boundary, source-capacity and observed class-sign review; no native runs or parameter acceptance.',
              'sediment_print_checks': len(sediment_checks), 'water_print_checks': len(water_checks),
              'absent_element_rows_preserved': len(missing), 'capacity_frames': len(caps),
              'class_observation_counts': dict(counts), 'class_observation_minima': dict(minima),
              'negative_observed_class_values': 0, 'target_buffer_frames': target_rows,
              'double_sum_order_differences': double_sum_order_differences,
              'limitations': ['Class signs cover bounded observed branches only, not all full-period internal states.',
                              'Grid exchange is net, not gross subgrid production/deposition.',
                              'Native floating-point reconstruction residuals are diagnostic; no tolerance changes.'],
              'evidence_sha256': {str(p): sha(p) for p in files}}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'passed': True, 'sediment': 90, 'water': 108, 'absent': 18,
                      'negative_observed_class_values': 0}))


if __name__ == '__main__':
    main()
