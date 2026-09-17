"""Verify accepted aliases, downloaded artifacts, runtime fingerprints and CSV bytes."""
from pathlib import Path
import hashlib
import json

out = Path(__file__).parent
root = Path('/wc1/runs/ne/nervous-mesquite')
state = json.loads((root / 'postfire_debris_flow.nodb').read_text())['py/state']['_state']
attempt = state['last_successful_run']['id']
browser = out / 'browser/nervous-mesquite'
records = json.loads((browser / 'evidence.json').read_text())
checks = []
for record in records:
    if record.get('stage') != 'artifact':
        continue
    name = record['name']
    accepted = root / 'postfire_debris_flow/attempts' / attempt / 'results' / name
    if name == 'valid_mask.tif':
        accepted = root / 'postfire_debris_flow/attempts' / attempt / 'predictors' / name
    published = root / 'postfire_debris_flow' / name
    digest = hashlib.sha256(accepted.read_bytes()).hexdigest()
    assert digest == record['sha256'], name
    assert hashlib.sha256(published.read_bytes()).hexdigest() == digest, name
    checks.append(name)
assert (browser / 'downloaded-curve.csv').read_bytes() == (browser / 'curve-english.csv').read_bytes()
engine = state['run_attempt']['snapshot']['inputs']['selections']['engine_sha256']
module = Path('/workdir/wepppy/wepppy/nodb/mods/postfire_debris_flow')
for name, digest in engine.items():
    assert hashlib.sha256((module / name).read_bytes()).hexdigest() == digest, name
result = dict(attempt_id=attempt, published_and_downloaded=checks,
              runtime_engine_files_verified=len(engine), downloaded_csv_matches=True)
(out / 'publication_validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
