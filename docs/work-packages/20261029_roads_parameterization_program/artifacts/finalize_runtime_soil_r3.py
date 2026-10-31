"""Bind reused and new records to frozen inventories and summarize dispositions."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
PARENT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
ROOT = PARENT / 'soil-hourly-r3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    declaration = json.loads((ROOT / 'declaration.json').read_text())
    legacy_path = PARENT / 'legacy-soil-control-r3/results.json'
    bridge_path = PARENT / 'runtime-bridge-r3/results.json'
    assert sha(legacy_path) == declaration['legacy_results_sha256']
    assert sha(bridge_path) == declaration['bridge_results_sha256']
    bridge = json.loads(bridge_path.read_text())
    cache = {str(PARENT / 'runtime-bridge-r3' / r['lane'] / '-'.join(r['original_case'].values())): r for r in bridge}
    new = json.loads((ROOT / 'results.json').read_text())
    assert len(new) == 196 and all(r['physical_pass'] for r in new)
    for r in new:
        assert json.loads((ROOT / 'cases' / r['input_signature'] / 'record.json').read_text()) == r
    for cell in declaration['cells']:
        if cell['origin'] == 'retained_bridge':
            assert json.loads((Path(cell['destination']) / 'record.json').read_text()) == cache[cell['destination']]
    path = HERE / 'soil-hourly-r3-analysis.json'; analysis = json.loads(path.read_text())
    assert analysis['results_sha256'] == sha(ROOT / 'results.json')
    assert analysis['declaration_sha256'] == sha(ROOT / 'declaration.json')
    assert analysis['labeled_physical_pass'] == len(analysis['rows']) == 464
    summary = {}
    for lane in ('generated-on', 'generated-off', 'legacy-on', 'legacy-off'):
        rows = [r for r in analysis['rows'] if r['lane'] == lane]
        misses = [r for r in rows if r['original_group'] in ('meaningful_high', 'meaningful_low', 'small_exceedance')]
        controls = [r for r in rows if r['original_group'] in ('meaningful_pass', 'small_pass')]
        assert len(misses) == 96 and len(controls) == 20
        summary[lane] = dict(recovered_misses=sum(r['within'] for r in misses), miss_cases=96,
                             controls_retained=sum(r['within'] for r in controls), controls=20,
                             physical_pass=sum(r['physical_pass'] for r in rows))
    result = dict(analysis_sha256=sha(path), frozen_reused_records_verified=True,
                  new_record_inventory_verified=196, labeled_cells=464, summary=summary,
                  generated_daily_regressions=[r for r in analysis['rows'] if r['lane'] == 'generated-off' and r['original_group'] in ('meaningful_pass', 'small_pass') and not r['within']],
                  legacy_daily_residuals=[r for r in analysis['rows'] if r['lane'] == 'legacy-off' and not r['within']],
                  disposition='Reject global hourly-off promotion. Continue role-specific generated hydraulic/state audit with existing runtime fixed; no parameter defaults or withheld/UI changes.',
                  verifier_sha256=sha(Path(__file__)))
    (HERE / 'runtime-soil-r3-disposition.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
