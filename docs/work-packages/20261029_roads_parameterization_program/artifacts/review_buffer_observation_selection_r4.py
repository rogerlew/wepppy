"""Independent selection readback; no selector import or native execution."""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--seeds', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    seeds = json.loads(args.seeds.read_text())
    summary = json.loads((args.ledger / 'case-summary.json').read_text())
    by_case = {row['case_id']: row for row in summary}
    tasks = {row['case_id']: row for row in json.loads(
        (args.ledger / 'declaration.json').read_text())['tasks']}
    assert len(by_case) == 116 and len(seeds['seeds']) == 9
    zero = {key for key, row in by_case.items() if row['surface'] == 'paved'
            and all(row['lanes'][lane]['ofes'][0]['sediment_out_kg'] == 0
                    for lane in ('legacy', 'modern'))}
    signature = {key for key, row in by_case.items()
                 if row['group'] == 'meaningful_pass'
                 and row['lanes']['modern']['ofes'][1]['sediment_out_kg']
                 < row['lanes']['legacy']['ofes'][1]['sediment_out_kg']
                 and row['lanes']['modern']['ofes'][2]['sediment_out_kg']
                 > row['lanes']['legacy']['ofes'][2]['sediment_out_kg']}
    assert len(zero) == 37 and len(signature) == 13
    db = duckdb.connect()
    db.execute('SET threads=2')
    db.execute('CREATE TABLE t AS SELECT * FROM read_parquet(?)',
               [str(args.ledger / 'cases/*/paired-terminal.parquet')])
    # Rebuild the eligibility decisions from the stated scientific strata.
    # Do not execute SQL stored by the selector or consult its ranked list.
    rows = db.execute('''SELECT case_id,year,julian,width_m,
        legacy_sediment_in_kg,modern_sediment_in_kg,
        legacy_sediment_out_kg,modern_sediment_out_kg,
        legacy_surface_in_m3,modern_surface_in_m3,legacy_surface_out_m3
        FROM t WHERE legacy_element_present AND modern_element_present
        AND abs(modern_sediment_out_kg-legacy_sediment_out_kg)>.001*width_m
        ''').fetchall()
    seen = set()
    checks = []
    for index, seed in enumerate(seeds['seeds']):
        candidates = []
        for row in rows:
            key, year, day, width, li, mi, lo, mo, lq, mq, lout = row
            if key in seen:
                continue
            case = by_case[key]
            group = case['group']
            difference = mo - lo
            positive = difference > .001 * width
            negative = difference < -.001 * width
            lower_supply = li - mi > .001 * width
            conditions = (
                group == 'small_exceedance' and key in zero and lout == 0
                    and lower_supply and positive,
                group == 'small_exceedance' and case['surface'] == 'gravel'
                    and mq < lq and lower_supply and positive,
                group == 'small_exceedance' and case['surface'] == 'gravel'
                    and lout == 0 and lower_supply and positive,
                group == 'meaningful_pass' and key in signature and positive,
                group == 'meaningful_low' and lower_supply and negative,
                group == 'meaningful_low' and mi >= li and negative,
                group == 'small_pass' and key in zero and positive,
                group == 'meaningful_high' and positive,
                group == 'meaningful_low' and case['design'] != 'outunrut'
                    and negative,
            )
            if conditions[index]:
                candidates.append((difference, key, year, day, width))
        assert candidates
        ascending = index in (4, 5, 8)
        candidates.sort(key=lambda r: (r[0] if ascending else -r[0], *r[1:4]))
        difference, key, year, day, width = candidates[0]
        event = seed['event']
        assert (key, year, day) == (event['case_id'], event['year'], event['julian'])
        assert difference == event['delta_reported_sediment_out_kg']
        assert seed['native_year_index'] == year - tasks[key]['first_year'] + 1
        assert seed['case_summary'] == by_case[key]
        assert seed['input_records'] == tasks[key]['records']
        assert digest(args.ledger / 'cases' / key / 'paired-terminal.parquet') == seed['paired_terminal_sha256']
        for record in seed['input_records'].values():
            assert digest(record['path']) == record['sha256']
        road_checks = []
        if key in zero:
            for lane in ('legacy', 'modern'):
                path = args.ledger / 'cases' / key / f'{lane}-daily-ofe.parquet'
                road = db.execute('''SELECT count(sediment_out_kg),
                    min(sediment_out_kg),max(sediment_out_kg),sum(sediment_out_kg)
                    FROM read_parquet(?) WHERE ofe=1''', [str(path)]).fetchone()
                assert road[0] > 0 and road[1:] == (0.0, 0.0, 0.0)
                road_checks.append({'lane': lane, 'observed_rows': road[0],
                                    'all_observed_road_exports_zero': True})
        checks.append({'stratum': seed['stratum'], 'case_id': key,
                       'year': year, 'julian': day,
                       'eligible_distinct_case_days': len(candidates),
                       'difference_kg': difference,
                       'combined_print_interval_kg': .001 * width,
                       'absolute_difference_in_print_intervals': abs(difference) / (.001 * width),
                       'zero_road_checks': road_checks})
        seen.add(key)
    result = {'passed': True, 'reviewer': 'Independent AI scientific review',
              'method': 'Recomputed eligibility and ordering from complete paired ledger; no selector import or stored selection SQL execution.',
              'pairs': len(checks), 'full_period_runs': 18,
              'actual_zero_road_cases_in_panel': sum(bool(c['zero_road_checks']) for c in checks),
              'checks': checks, 'evidence_sha256': {
                  str(args.seeds): digest(args.seeds),
                  str(args.ledger / 'case-summary.json'): digest(args.ledger / 'case-summary.json'),
                  str(args.ledger / 'declaration.json'): digest(args.ledger / 'declaration.json'),
                  str(Path(__file__).resolve()): digest(__file__)}}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'passed': True, 'pairs': len(checks), 'receipt': str(args.output)}))


if __name__ == '__main__':
    main()
