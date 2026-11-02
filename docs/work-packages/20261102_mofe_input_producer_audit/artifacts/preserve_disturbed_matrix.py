"""Retain fresh benchmark at a new durable root and verify manifest readback."""
from pathlib import Path
import hashlib
import json
import shutil

src = Path('/tmp/mipa-disturbed-final-20261102/disturbed_matrix0')
dst = Path('/wc1/holdouts/mipa-disturbed-producer-20261102/disturbed_matrix0')
repo = Path('/workdir/wepppy')
provenance = repo / 'tests/disturbed/analysis_results_current.provenance.json'
evidence = repo / 'docs/work-packages/20261102_mofe_input_producer_audit/artifacts'
size = sum(p.stat().st_size for p in src.rglob('*') if p.is_file())
assert shutil.disk_usage('/wc1/holdouts').free > size * 2
# A pre-existing root is not disposable evidence; a retry must use a new root.
dst.parent.mkdir(parents=True, exist_ok=False)
shutil.copytree(src, dst)
metadata = json.loads(provenance.read_text())
for case in metadata['cases']:
    for section, directory in [('inputs', 'runs'), ('outputs', 'output')]:
        for name, expected in case[section].items():
            assert hashlib.sha256((dst / directory / name).read_bytes()).hexdigest() == expected
metadata['evidence_root'] = str(dst)
for name in ['wepppy/wepp/soils/utils/wepp_soil_util.py', 'wepppy/wepp/soils/horizon_boundary.py',
             'wepppy/wepp/soils/utils/utils.py']:
    metadata['sources'][name] = hashlib.sha256((repo / name).read_bytes()).hexdigest()
provenance.write_text(json.dumps(metadata, indent=2)+'\n')
receipt = {'source': str(src), 'durable': str(dst), 'bytes': size,
           'input_entries_verified': sum(len(c['inputs']) for c in metadata['cases']),
           'output_entries_verified': sum(len(c['outputs']) for c in metadata['cases'])}
(evidence/'disturbed_matrix_durable.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
