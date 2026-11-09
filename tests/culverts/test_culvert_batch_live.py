"""Opt-in forest admission → parallel workers → authenticated artifact regression.

Requires CULVERT_BATCH_TEST_ORIGIN, CULVERT_BATCH_TEST_PAYLOAD and
CULVERT_BATCH_TEST_TOKEN_FILE. Run inside the stack with its mounted culvert root.
The token file contains a service JWT with culvert:batch:submit scope. Each test
submits a NEW batch and retains it, including failures; it never retries children.
"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile

import numpy as np
import pyarrow.parquet as pq
import pytest
import requests

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.requires_network]


def _sha(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def _assert_parallel_children(jobs, expected_count):
    children = [job for job in jobs
                if job.func_name == 'wepppy.rq.culvert_rq.run_culvert_run_rq']
    assert len(children) == expected_count
    events = []
    for job in children:
        assert job.started_at is not None and job.ended_at is not None
        assert job.started_at < job.ended_at
        events.extend(((job.started_at, 1), (job.ended_at, -1)))
    active = peak = 0
    # End events sort before starts at the same instant: touching is not overlap.
    for _, change in sorted(events):
        active += change
        peak = max(peak, active)
    assert peak >= 2, 'live regression requires overlapping sibling jobs'
    return peak


def test_real_culvert_batch_finishes_without_retries_and_exports_valid_outputs(tmp_path):
    names = ('CULVERT_BATCH_TEST_ORIGIN', 'CULVERT_BATCH_TEST_PAYLOAD', 'CULVERT_BATCH_TEST_TOKEN_FILE')
    configured = [os.environ.get(name) for name in names]
    if not any(configured):
        pytest.skip('live culvert admission is explicitly opt-in; see module documentation')
    assert all(configured), 'all live culvert test settings must be supplied'
    origin, payload_name, token_name = configured
    origin = origin.rstrip('/')
    payload = Path(payload_name)
    with payload.open('rb') as stream:
        payload_sha = _sha(stream)
    with zipfile.ZipFile(payload) as archive:
        features = json.loads(archive.read('culverts/watersheds.geojson'))['features']
    expected = {str(feature['properties']['Point_ID']) for feature in features}
    assert len(expected) == len(features) >= 2, 'fixture must contain independent sibling culverts'
    headers = {'Authorization': 'Bearer ' + Path(token_name).read_text().strip()}
    host = os.environ.get('CULVERT_BATCH_TEST_HOST')
    if host:
        headers.update({'Host': host, 'X-Forwarded-Proto': 'https'})
    with payload.open('rb') as stream:
        response = requests.post(origin + '/rq-engine/api/culverts-wepp-batch/', headers=headers,
            files={'file': ('payload.zip', stream, 'application/zip')},
            data={'zip_sha256': payload_sha, 'total_bytes': str(payload.stat().st_size)}, timeout=180)
    assert response.status_code == 200, f'admission HTTP {response.status_code}'
    admission = response.json()
    batch = admission['culvert_batch_uuid']
    print(f'live batch={batch} root_job={admission["job_id"]}', flush=True)
    # Persist credentials privately for diagnosis; never include them in assertions.
    private = tmp_path / 'admission-private.json'
    fd = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(admission, stream)
    root = Path(os.environ.get('CULVERTS_ROOT', '/wc1/culverts')) / batch
    identities = {}
    deadline = time.monotonic() + float(os.environ.get('CULVERT_BATCH_TEST_TIMEOUT', '7200'))
    while not (root / 'batch_summary.json').exists():
        assert time.monotonic() < deadline, f'batch {batch} did not finish before deadline'
        for wd in [root / '_base', *root.glob('runs/*')]:
            marker = wd / '_query_engine/refresh/incarnation.json'
            if marker.exists():
                identities[str(wd.relative_to(root))] = json.loads(marker.read_text())
        time.sleep(1)
    summary = json.loads((root / 'batch_summary.json').read_text())
    failures = {p.parent.name: json.loads(p.read_text()).get('error')
                for p in root.glob('runs/*/run_metadata.json')
                if json.loads(p.read_text()).get('status') == 'failed'}
    assert summary == {'culvert_batch_uuid': batch, 'total': len(expected),
                       'succeeded': len(expected), 'failed': 0, 'skipped_no_outlet': 0}, failures
    (tmp_path / 'identities.json').write_text(json.dumps(identities, indent=2))
    assert set(identities) == {'_base', *(f'runs/{run}' for run in expected)}
    assert len({item['incarnation'] for item in identities.values()}) == len(expected) + 1
    assert len({item['scope_id'] for item in identities.values()}) == len(expected) + 1
    assert {p.name for p in (root / 'runs').iterdir()} == expected
    counts = Counter()
    for run in sorted(expected):
        wd = root / 'runs' / run
        metadata = json.loads((wd / 'run_metadata.json').read_text())
        assert metadata['status'] == 'success' and metadata['point_id'] == run
        hills = pq.read_table(wd / 'watershed/hillslopes.parquet')
        ids = set(hills['topaz_id'].to_pylist())
        assert len(ids) == hills.num_rows > 0
        for name in ('landuse/landuse.parquet', 'soils/soils.parquet'):
            assert set(pq.read_table(wd / name)['topaz_id'].to_pylist()) == ids
        areas = np.asarray(hills['area'].to_pylist())
        assert np.isfinite(areas).all() and (areas > 0).all()
        counts['hillslopes'] += hills.num_rows
        for name, columns in (
            ('totalwatsed3.parquet', ['year', 'sim_day_index', 'P', 'runvol', 'sed_del']),
            ('ebe_pw0.parquet', ['year', 'runoff_volume', 'peak_runoff', 'sediment_yield']),
        ):
            table = pq.read_table(wd / 'wepp/output/interchange' / name, columns=columns)
            assert table.num_rows > 0
            for column in columns:
                assert table[column].null_count == 0
                assert np.isfinite(np.asarray(table[column].to_pylist())).all(), (run, name, column)
            if name == 'totalwatsed3.parquet':
                assert table['sim_day_index'].to_pylist() == list(range(1, table.num_rows + 1))
        for path in wd.rglob('*.parquet'):
            assert pq.ParquetFile(path).metadata.num_rows >= 0
            counts['parquet_files'] += 1
    # Summary publication precedes final archive completion: wait for the real finalizer.
    import redis
    from rq.job import Job
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    # The repository autouse fixture replaces redis.Redis; this opt-in gate
    # must inspect the real queue without mutating the shared test fixture.
    connection = redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ))
    parent = Job.fetch(admission['job_id'], connection=connection)
    children = [value for key, value in parent.meta.items() if key.startswith('jobs:')]
    assert len(children) == len(expected) + 1
    while True:
        jobs = Job.fetch_many(children, connection=connection)
        states = {job.id: job.get_status().value for job in jobs}
        assert not set(states.values()) & {'failed', 'stopped', 'canceled'}, states
        if set(states.values()) == {'finished'}:
            break
        assert time.monotonic() < deadline, states
        time.sleep(1)
    assert parent.get_status().value == 'finished'
    peak_concurrency = _assert_parallel_children(jobs, len(expected))
    connection.close()
    headers['Authorization'] = 'Bearer ' + admission['browse_token']
    url = origin + f'/weppcloud/culverts/{batch}'
    browse = requests.get(url + '/browse/', headers=headers, timeout=60, allow_redirects=False)
    assert browse.status_code == 200
    downloaded = tmp_path / 'skeletons.zip'
    with requests.get(url + '/download/weppcloud_run_skeletons.zip', headers=headers,
                      stream=True, timeout=(30, 600), allow_redirects=False) as response:
        assert response.status_code == 200
        with downloaded.open('wb') as stream:
            for block in response.iter_content(1024 * 1024):
                stream.write(block)
    with downloaded.open('rb') as stream, (root / 'weppcloud_run_skeletons.zip').open('rb') as source:
        archive_sha = _sha(stream)
        assert archive_sha == _sha(source)
    with zipfile.ZipFile(downloaded) as archive:
        members = archive.namelist()
        assert len(members) == len(set(members))
        assert {str(Path(name).parent.name) for name in members
                if name.startswith('runs/') and name.endswith('/run_metadata.json')} == expected
        for name in members:
            with archive.open(name) as stream, (root / name).open('rb') as source:
                assert _sha(stream) == _sha(source), name
    evidence = {'batch': batch, 'root_job': admission['job_id'], 'summary': summary,
                'identities': identities, 'counts': dict(counts), 'jobs': states,
                'payload_sha256': payload_sha, 'archive_sha256': archive_sha,
                'archive_members': len(members), 'peak_child_concurrency': peak_concurrency}
    (tmp_path / 'evidence.json').write_text(json.dumps(evidence, indent=2))
    print(json.dumps({key: value for key, value in evidence.items()
                      if key not in ('identities', 'jobs')}), flush=True)
