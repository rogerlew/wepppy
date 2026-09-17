"""Read-only byte attribution for the completed canary archive restore.

No SQLite connection, source write, checkpoint or freshness acceptance mutation.
Compares all seven manifest-bound soil inputs, original accepted main/WAL copies,
and physical source main/WAL/SHM against their actual archive members.
"""
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

from runtime_project_copy import digest_file

artifacts = Path(__file__).parent
destination = artifacts / 'runtime_restore_soil_attribution_qa.json'
if destination.exists():
    raise FileExistsError('Preserve the existing attribution evidence')
root = Path('/wc1/runs/qa/qa-freshness-runtime-7e24c8d1')
diagnosis = json.loads((artifacts / 'runtime_restore_freshness_diagnosis.json').read_text())
accepted = root / 'postfire_debris_flow/attempts' / diagnosis['accepted_result']
manifest = json.loads((accepted / 'predictors/soil/manifest.json').read_text())
zip_record = json.loads((artifacts / 'runtime_archive_live_zip.json').read_text())
record = {'uid': os.getuid(), 'gid': os.getgid(), 'root': str(root),
          'accepted_result': diagnosis['accepted_result'], 'scope': __doc__,
          'soil_sources': {}, 'physical_cache': {}, 'accepted_snapshot_comparison': {},
          'all_match': False}
try:
    for path, expected in manifest['sources_sha256'].items():
        selected = Path(path)
        if root not in selected.parents or selected.resolve() != selected:
            raise ValueError('Unexpected soil source path')
        actual = digest_file(selected)
        record['soil_sources'][str(selected.relative_to(root))] = {
            'sha256': actual['sha256'], 'accepted_sha256': expected,
            'match': actual['sha256'] == expected, 'bytes': actual['bytes']}
    with ZipFile(zip_record['path']) as archive:
        for suffix in ('', '-wal', '-shm'):
            relative = 'soils/ssurgo_tabular_cache.sqlite' + suffix
            actual = digest_file(root / relative)
            checksum = hashlib.sha256()
            with archive.open(relative) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    checksum.update(block)
            record['physical_cache'][relative] = {'sha256': actual['sha256'],
                'archive_sha256': checksum.hexdigest(), 'bytes': actual['bytes'],
                'match': actual['sha256'] == checksum.hexdigest()}
            if suffix != '-shm':
                original = digest_file(accepted / ('predictors/soil/snapshots/initial/cache.sqlite' + suffix))
                record['accepted_snapshot_comparison'][suffix or 'main'] = {
                    'source_sha256': actual['sha256'], 'accepted_copy_sha256': original['sha256'],
                    'match': actual['sha256'] == original['sha256']}
    record['all_match'] = all(item['match'] for section in
        ('soil_sources', 'physical_cache', 'accepted_snapshot_comparison')
        for item in record[section].values())
    assert record['all_match'], 'An actual soil byte difference requires separate attribution'
finally:
    destination.write_text(json.dumps(record, indent=2) + '\n')
print('Read-only archive soil attribution:', record['all_match'], flush=True)
