"""Independent readback of declared changes and provenance after execution."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
from wepppy.wepp.soils.utils import WeppSoilUtil

ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
HERE = Path(__file__).resolve().parent

def digest(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    legacy_path = ROOT / 'legacy-soil-control-v2/results.json'
    assert digest(legacy_path) == 'f73d411cb83a7d269a69e6544da96be9eb76636778ab2a5b1c306e3e5fee0231'
    legacy = {'-'.join(r['case'].values()): r for r in json.loads(legacy_path.read_text())}
    counts = {}
    for study in ('erosion', 'runtime'):
        root = ROOT / f'{study}-ablation-v1'
        declaration = json.loads((root / 'declaration.json').read_text())
        assert digest(root / 'executed-study.py') == declaration['script_sha256']
        rows = json.loads((root / 'results.json').read_text())
        assert len(rows) == len(declaration['tasks'])
        for row, task in zip(rows, declaration['tasks']):
            assert row['lane'] == task['lane'] and row['original_case'] == task['case']
            name = '-'.join(task['case'].values())
            folder = root / row['lane'] / name
            source = Path(task['source'])
            assert digest(source / 'record.json') == task['source_record_sha256']
            for category, subdir in (('inputs', 'runs'), ('outputs', 'output')):
                for filename, sha in row[category].items():
                    assert digest(folder / subdir / filename) == sha
            before = WeppSoilUtil(str(source / 'runs/p1.sol')).obj
            actual = WeppSoilUtil(str(folder / 'runs/p1.sol')).obj
            expected = deepcopy(before)
            if study == 'erosion':
                for index in {'fill': (1,), 'buffer': (2,), 'both': (1, 2)}[row['lane']]:
                    for field in ('ki', 'kr', 'shcrit'):
                        expected['ofes'][index][field] = legacy[name]['soil_readback'][index][field]
                assert row['physical_pass'] and row['water_output_unchanged']
                assert digest(folder / 'output/H1.wat.dat') == digest(source / 'output/H1.wat.dat')
            assert actual == expected
        counts[study] = len(rows)
    receipt = dict(verified_cases=counts, legacy_anchor_results_sha256=digest(legacy_path),
                   exact_soil_changes=True, all_recorded_input_output_hashes_verified=True,
                   erosion_water_byte_parity=333, verifier_sha256=digest(Path(__file__)))
    (HERE / 'role-runtime-verification-v1.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
