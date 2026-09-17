"""Read-only real export planning + verification, including duplicate entries."""
import json
from pathlib import Path
from time import perf_counter, sleep
from unittest.mock import patch
from wepppy.all_your_base.file_digest import _digest, _observed_at, sha256_file
from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.dependency_tracker import build_dependency_snapshot

root = Path('/wc1/runs/th/thespian-cleanness')
manifest = json.loads((root / 'export/features/artifacts/a41d267b33ad4105ac0fbc5142fd36a8/manifest.json').read_text())
payload = manifest['request']['resolved']
started = perf_counter()
submission = service.prepare_export_submission(root, payload)
initial = perf_counter() - started
started = perf_counter()
metadata = build_dependency_snapshot(submission.plan, submission.catalog, root, nodb_ref_resolver=service._resolve_nodb_ref_relpath)
resolver = perf_counter() - started
original_snapshot = service.build_dependency_snapshot

def metadata_snapshot(*args, **kwargs):
    return original_snapshot(*args, **{**kwargs, "content_hash_mode": "none"})

with patch.object(service, 'build_dependency_snapshot', side_effect=metadata_snapshot):
    started = perf_counter()
    for _ in range(5):
        service.prepare_export_submission(root, payload)
    baseline_prepare = (perf_counter() - started) / 5
paths = [root / e.relpath for e in submission.dependency_snapshot.entries if e.content_hash_marker == 'sha256']
_digest.cache_clear(); _observed_at.cache_clear()
started = perf_counter()
for path in paths:
    sha256_file(path)
hash_seconds = perf_counter() - started
_digest.cache_clear(); _observed_at.cache_clear()
started = perf_counter()
submission = service.prepare_export_submission(root, payload)
verification, failure = service._verify_export_submission(root, submission)
cold = perf_counter() - started
assert failure is None
sleep(1.01)
service.prepare_export_submission(root, payload)
before = _digest.cache_info()
started = perf_counter()
for _ in range(10):
    submission = service.prepare_export_submission(root, payload)
    _, failure = service._verify_export_submission(root, submission)
    assert failure is None
warm = (perf_counter() - started) / 10
misses = _digest.cache_info().misses - before.misses
print(json.dumps({'root': str(root), 'entries': len(submission.dependency_snapshot.entries),
    'hash_entries_including_repeats': len(paths), 'unique_files': len(set(paths)),
    'first_prepare_seconds': initial, 'metadata_resolver_seconds': resolver,
    'single_snapshot_hash_seconds': hash_seconds, 'cold_prepare_and_verify_seconds': cold,
    'baseline_metadata_prepare_seconds': baseline_prepare,
    'budget_seconds': 2 * (hash_seconds + baseline_prepare), 'settled_prepare_and_verify_seconds': warm,
    'settled_digest_misses': misses, 'verification': verification}, indent=2))
assert misses == 0
assert cold <= 2 * (hash_seconds + baseline_prepare)
