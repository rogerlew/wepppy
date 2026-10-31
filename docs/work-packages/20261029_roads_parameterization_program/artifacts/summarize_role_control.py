"""Compact readback of the declared diagnostic control, without candidate selection."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
SOURCE = Path('/workdir/wepppy/out/roads-parameterization-program-20261031/legacy-soil-control-v2/results.json')


def main():
    rows = json.loads(SOURCE.read_text())
    summary = json.loads((HERE / 'legacy-soil-control-r2-summary.json').read_text())
    sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert sha == summary['results_sha256'] and len(rows) == 111
    assert all(row['status'] == 'completed' and row['physical_pass'] for row in rows)
    failed = [r for r in rows if not r['within']]
    signature = lambda r: tuple(sorted(r['inputs'].items()))
    result = dict(source=str(SOURCE), results_sha256=sha,
                  unique_input_sets=len({signature(r) for r in rows}),
                  remaining_failures=len(failed), remaining_unique_inputs=len({signature(r) for r in failed}),
                  original_misses_within=sum(r['within'] for r in rows if r['group'] in ('meaningful_high', 'meaningful_low', 'small_exceedance')),
                  rows=[dict(case=r['case'], original_group=r['group'],
                             reference_kg_yr=r['reference_kg_yr'], generated_kg_yr=r['generated_kg_yr'],
                             same_engine_legacy_kg_yr=r['metrics']['sediment_export_kg_yr'],
                             control_within=r['within'], physical_pass=r['physical_pass'],
                             control_ofe_budgets=r['audit']['sediment']['ofes']) for r in rows])
    (HERE / 'legacy-soil-control-r2-comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
