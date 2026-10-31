"""Independent readback of the frozen published SOIL context; no model run."""
import argparse
import calendar
import hashlib
import importlib
import json
from pathlib import Path

import pyarrow.parquet as pq

from wepppy.wepp.interchange._rust_interchange import require_wepppyo3_interchange


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--seeds', type=Path, required=True)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    declaration = json.loads((args.root / 'declaration.json').read_text())
    results = json.loads((args.root / 'results.json').read_text())
    previous = json.loads((args.previous / 'results.json').read_text())
    seeds = json.loads(args.seeds.read_text())
    assert sha(args.seeds) == declaration['seeds_sha256']
    assert sha(args.script) == declaration['script_sha256']
    assert sha(args.root / 'declaration.json') == results['declaration_sha256']
    for name in ('reader', 'native_reader', 'wrapper'):
        assert sha(declaration[name]) == declaration[name + '_sha256']
    facade = require_wepppyo3_interchange('independent SOIL readback',
                                         'hillslope_soil_files_to_parquet')
    native = importlib.import_module(facade.hillslope_soil_files_to_parquet.__module__)
    assert Path(native.__file__).resolve() == Path(declaration['native_reader']).resolve()
    assert str(native.__file__).endswith('.so')
    rows_checked = 0
    checks = []
    for seed, pair, old in zip(seeds['seeds'], results['pairs'], previous['pairs'], strict=True):
        assert pair['stratum'] == old['stratum'] == seed['stratum']
        expected = {(year, day, ofe)
                    for year in range(seed['calendar_first_year'], seed['calendar_last_year'] + 1)
                    for day in range(1, 366 + calendar.isleap(year))
                    for ofe in (1, 2, 3)}
        for lane in ('legacy', 'modern'):
            entry = pair['lanes'][lane]
            old_entry = old['lanes'][lane]
            assert {k: v for k, v in entry.items() if k != 'parquet_sha256'} == {
                k: v for k, v in old_entry.items() if k != 'parquet_sha256'}
            record = Path(entry['record']['path'])
            assert sha(record) == entry['record']['sha256']
            raw = record.parent / 'output/H1.soil.dat'
            assert sha(raw) == entry['raw_sha256'] == json.loads(record.read_text())['outputs'][raw.name]
            name = f"{pair['stratum']}-{lane}.parquet"
            table = pq.read_table(args.root / name)
            assert sha(args.root / name) == entry['parquet_sha256']
            assert sha(args.previous / name) == old_entry['parquet_sha256']
            assert table.equals(pq.read_table(args.previous / name), check_metadata=True)
            rows = table.to_pylist()
            keys = [(r['year'], r['julian'], r['OFE']) for r in rows]
            assert len(keys) == len(set(keys)) and set(keys) == expected
            assert len(rows) == entry['rows']
            for index, ofe in enumerate((1, 2, 3)):
                subset = sorted((r for r in rows if r['OFE'] == ofe),
                                key=lambda r: (r['year'], r['julian']))
                values = [r['Rough'] for r in subset if r['Rough'] is not None]
                changed = next((r for r in subset if r['Rough'] != subset[0]['Rough']), None)
                actual = {'first': subset[0]['Rough'], 'minimum': min(values),
                          'maximum': max(values), 'missing': len(subset) - len(values),
                          'first_changed': None if changed is None else {
                              k: changed[k] for k in ('year', 'julian', 'Rough')}}
                assert actual == entry['ofes'][index]['roughness_mm']
            rows_checked += len(rows)
            checks.append({'stratum': pair['stratum'], 'lane': lane,
                           'rows': len(rows), 'buffer_roughness_mm': entry['ofes'][2]['roughness_mm'],
                           'parquet_sha256': entry['parquet_sha256']})
    assert len(checks) == 18 and rows_checked == 315576
    result = {'passed': True, 'scope': 'Independent descriptive SOIL-context readback only; no causal test or native runs.',
              'rows': rows_checked, 'logical_table_pairs_equal': len(checks),
              'actual_callable_module': native.__name__,
              'native_reader_sha256': sha(native.__file__),
              'checks': checks,
              'evidence_sha256': {str(p): sha(p) for p in (
                  args.root / 'declaration.json', args.root / 'results.json',
                  args.root / 'logical-replay-verification.json', args.previous / 'results.json',
                  args.seeds, args.script, Path(__file__).resolve())}}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'passed': True, 'rows': rows_checked, 'lanes': len(checks)}))


if __name__ == '__main__':
    main()
