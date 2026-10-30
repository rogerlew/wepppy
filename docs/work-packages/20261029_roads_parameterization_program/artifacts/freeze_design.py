"""Freeze acceptance and unused material groups before parameter selection."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
ROOT=Path('/wc1/runs/ro/roads-parameterization-program-20261029')
VALIDATION_IDS=('1718472','53975','1718476','665770','2711196','658566')
DEVELOPMENT_IDS=('1718465','2711184','2711250','1718510','1856573','53949','1718494')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inventory=json.loads((ROOT/'inventory.json').read_text())
    rows={r['mukey']:r for r in inventory['profiles']}
    validation=[rows[k] for k in VALIDATION_IDS]
    if any(r['material_seen_in_prior_studies'] for r in validation):
        raise ValueError('Validation specimen already used')
    if len({r['material_sha256'] for r in validation})!=len(validation):
        raise ValueError('Validation material duplicated')
    declaration=dict(version=1,numerical_gate_status='Working assumption under delegated experimental judgment; operator may explicitly steer',
        overall_pass_fraction=.95,minimum_group_pass_fraction=.90,ratio_interval=[.1,10.],
        meaningful_reference_kg_yr=1.,small_load_upper='max(1 kg/year, 10 * reference kg/year)',
        no_small_load_lower_bound=True,physical_gate='No negative sediment flux, nonfinite/incomplete output or unexplained accounting discrepancy',
        reference='FSWEPP2 Roads / WEPP2010',modern_binary='wepp_261026',
        modern_sha256='a6351d371030f702be5eb0d727d8e7181eeb9d60e9ddf6ce05d9616e5d759d48',
        development=[rows[k] for k in DEVELOPMENT_IDS],withheld_validation=validation,
        reserve_other_materials=True,withheld_native_outcomes_inspected=False,
        source_inventory_sha256=digest(ROOT/'inventory.json'),acceptance_sha256=digest(HERE.parent/'acceptance.md'),
        script_sha256=digest(Path(__file__)),
        comparison_layers=['Matched FSWEPP outlet and geometry','Actual production builder/direct and routed arrangements','Disposable full-project workflow'],
        candidate_search_start='Restore configuration semantics and native UI-mode/runtime provenance before tuning',
        production_changes_allowed_only_after_contract_checkpoint=True)
    target=ROOT/'design-v1';target.mkdir(exist_ok=False)
    (target/'manifest.json').write_text(json.dumps(declaration,indent=2,allow_nan=False)+'\n')
    shutil.copy2(HERE.parent/'acceptance.md',target/'acceptance.md')
    shutil.copy2(HERE.parent/'autonomy.md',target/'autonomy.md')
    shutil.copy2(__file__,target/'executed-freeze-design.py')
    shutil.copy2(target/'manifest.json',HERE/'design-v1.json')
    print('Frozen 7 development and 6 distinct withheld profiles; no withheld native outputs inspected')


if __name__=='__main__':main()
