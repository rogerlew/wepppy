"""Run the candidate on a separate forest copy, retaining exact input provenance."""
from pathlib import Path
import hashlib
import json
import shutil

SOURCE = Path('/wc1/runs/mi/misty-eyed-divorcee')
ROOT = Path('/wc1/runs/ru/rupc-misty-validation')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(root):
    return {str(p.relative_to(root)): digest(p) for folder in ('wepp/runs', 'wepp/output', 'roads')
            for p in (root / folder).rglob('*') if p.is_file()}

def rebase(value):
    if isinstance(value, dict):
        return {k: rebase(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rebase(v) for v in value]
    if isinstance(value, str) and (value == str(SOURCE) or value.startswith(str(SOURCE) + '/')):
        return str(ROOT) + value[len(str(SOURCE)):]
    return value

if __name__ == '__main__':
    from wepppy.nodb.mods.roads import Roads
    if ROOT.exists():
        raise RuntimeError('Validation destination already exists; inspect it instead of overwriting evidence.')
    before = inventory(SOURCE)
    shutil.copytree(SOURCE, ROOT, ignore=shutil.ignore_patterns('_query_engine', '_logs', 'export', '*.log'))
    for path in ROOT.glob('*.nodb'):
        path.write_text(json.dumps(rebase(json.loads(path.read_text()))))
    (ROOT/'validation-source-before.json').write_text(json.dumps(before, indent=2))
    data = json.loads((ROOT/'roads/roads.uploaded.geojson').read_text())
    # Explicit synthetic fixture values from tests/roads/roads_project.py, NOT
    # measured Marta site data and NOT runtime defaults. Missing original values
    # remain an independent operator input issue.
    values = dict(FILL_LENGTH_M=30., FILL_SLOPE_PCT=10., BUFFER_LENGTH_M=30., BUFFER_SLOPE_PCT=10.)
    for feature in data['features']:
        feature['properties'].update(values)
    path = ROOT/'validation-input.geojson'
    path.write_text(json.dumps(data))
    (ROOT/'validation-provenance.json').write_text(json.dumps({
        'source':str(SOURCE), 'purpose':'synthetic geometry/execution acceptance, not site prediction',
        'synthetic_parameters':values, 'input_sha256':digest(path)}, indent=2))
    controller = Roads.getInstance(str(ROOT))
    controller.set_uploaded_geojson(str(path))
    prepared = controller.prepare_segments()
    print('PREPARED', json.dumps(prepared), flush=True)
    result = controller.run_roads_wepp()
    (ROOT/'validation-result.json').write_text(json.dumps(result, indent=2))
    assert inventory(SOURCE) == before, 'Source baseline/upload changed'
    print('RESULT',json.dumps(result),flush=True)
