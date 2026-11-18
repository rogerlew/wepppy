"""Read-only admission checks on retained project artifacts using final source."""
from pathlib import Path
import hashlib
import json
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

root = Path('/workdir/wepppy')
package = root/'docs/work-packages/20261117_roads_code_quality_refactor/artifacts'
projects = json.loads((package/'candidate_project_comparison.json').read_text())['projects']
results = []
for project in projects:
    candidates = [Path(path) for path in project['roots'] if 'candidate-' in str(path)]
    assert len(candidates) == 1
    path = candidates[0]
    state = path/'roads.nodb'
    before = hashlib.sha256(state.read_bytes()).hexdigest()
    expected = project['design'] != 'unrutted-negative'
    admitted = lifecycle.available(path)
    assert admitted == expected, (project['design'], admitted)
    if expected:
        receipt = lifecycle.require_current(path)
        assert receipt
    assert hashlib.sha256(state.read_bytes()).hexdigest() == before
    results.append({'design': project['design'], 'root':str(path), 'current':admitted,
                    'roads_nodb_sha256':before, 'durable_state_unchanged':True})
output=Path('/tmp/roads-refactor-validation/final-project-admission.json')
output.write_text(json.dumps({'final_constants_sha256':hashlib.sha256((root/'wepppy/nodb/mods/roads/_constants.py').read_bytes()).hexdigest(), 'projects':results},indent=2)+'\n')
print('Final-source readback: four successful projects current; negative project unavailable; all durable state unchanged')
