"""Actual RQ execution rejection with an isolated queue and real filesystem fence."""
from uuid import uuid4

import pytest
import redis
from rq import Queue
from rq.registry import FailedJobRegistry

from tests.rq.test_declarative_dem import definition, project  # noqa: F401
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("runtime_redis_credentials")]


def test_worker_refusal_uses_failed_registry(project, monkeypatch):
    from wepppy.rq import rq_worker
    from wepppy.rq.project_rq import fetch_dem_rq
    wd, admission = project
    connection = redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ))
    connection.ping()
    queue = Queue('declarative-denial-' + uuid4().hex, connection=connection)
    monkeypatch.setenv('WEPPPY_PROJECT_COMMIT_MODE', 'disabled')
    monkeypatch.setattr(rq_worker, 'get_wd', lambda runid: str(wd))
    job = queue.enqueue(fetch_dem_rq, admission['runid'], [-116.10, 46.70, -116.09, 46.71], None, None)
    try:
        rq_worker.WepppyRqWorker([queue], connection=connection).work(burst=True, logging_level='WARNING')
        assert job.get_status(refresh=True).value == 'failed'
        assert job.id in FailedJobRegistry(queue=queue).get_job_ids()
        assert not (wd / 'dem').exists()
        job.refresh()
        assert 'ProtectedProjectError' in job.exc_info
    finally:
        job.delete()
        queue.delete(delete_jobs=True)
        connection.close()


@pytest.mark.parametrize('fault', [None, 'source', 'checkpoint', 'finalization', 'drift', 'manifest', 'cancel', 'initialize', 'invalid_grid'])
@pytest.mark.parametrize('module_main', [False, True])
def test_adapter_full_lifecycle_with_fixture_runtime_identity(tmp_path, definition, monkeypatch, fault, module_main):
    """Real RQ/NoDb/Git/read-only/view flow; source and Pod evidence are fixtures."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from wepppy.declarative import adapter, records, schema
    from wepppy.nodb.core import Ron
    from wepppy.rq import rq_worker, project_rq, exception_logging
    from wepppy.weppcloud.utils import helpers
    from wepppy.weppcloud import user_preferences
    from wepppy.microservices.elevationquery import _sample_dem

    if module_main:
        # python -m defines these functions in __main__; RQ rejects function
        # objects from that module. Exercise the actual queue validation path.
        monkeypatch.setattr(adapter.execute_dem, '__module__', '__main__')
        monkeypatch.setattr(adapter.finalize_dem, '__module__', '__main__')

    connection = redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ))
    connection.ping()
    runid, queue_name = schema.identities(definition['submission_id'])
    wd = tmp_path / runid
    uid = str(uuid4())
    evidence = {'namespace': 'weppcloud', 'pod_name': 'fixture-only', 'pod_uid': uid,
                'container': 'worker', 'container_id': 'fixture-only-container',
                'image': definition['image'], 'image_id': definition['image'],
                'restart_count': 0, 'platform': 'linux/amd64', 'node_name': 'fixture-node',
                'observed_at': records.utcnow()}
    approval = {definition['image']: {'schema': schema.SCHEMA, 'protocol': schema.PROTOCOL,
                                     'platform': 'linux/amd64', 'operation': 'fetch_dem_rq'}}
    for key, value in {'DECLARATIVE_SUBMISSION_ID': definition['submission_id'], 'DECLARATIVE_POD_UID': uid,
                       'DECLARATIVE_POD_NAME': 'fixture-only', 'DECLARATIVE_NAMESPACE': 'weppcloud',
                       'DECLARATIVE_CONTAINER': 'worker', 'WEPPPY_PROJECT_COMMIT_MODE': 'disabled'}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(adapter, 'connection', lambda: connection)
    monkeypatch.setattr(adapter, 'approvals', lambda: approval)
    monkeypatch.setattr(adapter, 'location', lambda submission: (runid, wd))
    monkeypatch.setattr(adapter, '_validate_owner', lambda owner: None)
    monkeypatch.setattr(user_preferences, 'register_owned_run', lambda *args: None)
    for module in (helpers, rq_worker, project_rq, exception_logging):
        monkeypatch.setattr(module, 'get_wd', lambda runid: str(wd))

    def acquired_fixture(ron):
        if fault == 'source':
            raise OSError('fixture source failure')
        with rasterio.open(ron.dem_fn, 'w', driver='GTiff', height=ron.map.num_rows,
                           width=ron.map.num_cols, count=1, dtype='float32',
                           crs=f'EPSG:{ron.map.srid}',
                           transform=from_origin(ron.map.ul_x + (300 if fault == 'invalid_grid' else 0),
                                                 ron.map.ul_y, ron.map.cellsize, ron.map.cellsize)) as ds:
            ds.write(np.full((ron.map.num_rows, ron.map.num_cols), 123.0, dtype='float32'), 1)
    monkeypatch.setattr(Ron, 'fetch_dem', acquired_fixture)
    def failure(*args, **kwargs):
        raise OSError('fixture publication failure')
    if fault == 'initialize':
        monkeypatch.setattr(user_preferences, 'register_owned_run', failure)
    real_checkpoint = records.checkpoint
    def checkpoint(wd, attempt_id, paths):
        if fault == 'checkpoint' and 'declarative.json' in paths:
            # Exercise recovery from initialized Git with no committed refs.
            records._git(wd / 'provenance', 'init', '--quiet')
            raise OSError('fixture Git failure')
        return real_checkpoint(wd, attempt_id, paths)
    monkeypatch.setattr(records, 'checkpoint', checkpoint)
    monkeypatch.setattr('wepppy.declarative.observations.checkpoint', checkpoint)
    queue = Queue(queue_name, connection=connection)
    admission = None
    try:
        payload = {'definition': definition, 'owner_id': 7, 'evidence': evidence}
        if fault == 'initialize':
            with pytest.raises(OSError):
                adapter.submit(payload)
            assert len(queue) == 0
        else:
            initial = adapter.submit(payload)
            assert initial['processing'] == 'admitted'
            assert len(queue) == 1
        assert adapter.submit(payload)['runid'] == runid
        assert len(queue) == (0 if fault == 'initialize' else 1)
        admission = records.marker(wd)
        if fault == 'cancel':
            adapter.cancel(definition['submission_id'])
        rq_worker.WepppyRqWorker([queue], connection=connection, name=uid).work(burst=True, logging_level='WARNING')
        if fault not in {'source', 'checkpoint', 'cancel', 'initialize', 'invalid_grid'}:
            assert adapter.status(definition['submission_id'])['processing'] == 'succeeded'
        if fault == 'drift':
            (wd / 'dem/dem.tif').write_bytes(b'changed after acquisition')
        if fault == 'manifest':
            monkeypatch.setattr(records, 'protected_manifest', failure)
        if fault == 'finalization':
            # Keep the actual READONLY transition and rollback boundary in the test.
            monkeypatch.setattr('wepppy.microservices.browse.create_manifest', failure)
        adapter.finalize(definition['submission_id'], evidence)
        rq_worker.WepppyRqWorker([queue], connection=connection, name=uid).work(burst=True, logging_level='WARNING')
        if fault in {'drift', 'manifest', 'finalization'}:
            result = adapter.status(definition['submission_id'])
            assert result['protection'] == 'failed'
            assert result['error']['code'] == 'protection_failed'
            assert result['verified'] is False
            if fault == 'finalization':
                assert (wd / 'READONLY').is_file()
                before = (wd / 'provenance/build.json').read_bytes()
                adapter.finalize(definition['submission_id'], evidence)
                assert len(queue) == 0
                assert (wd / 'provenance/build.json').read_bytes() == before
            return
        result = adapter.complete(definition['submission_id'], evidence)
        if fault:
            assert result['verified'] is False
            assert result['processing'] == ('canceled' if fault == 'cancel' else 'failed')
            assert result['protection'] == 'readonly'
            assert (wd / 'READONLY').is_file()
            if fault == 'invalid_grid':
                record = records.read(wd, f"provenance/attempts/{admission['attempt_id']}.json")
                assert record['outcome'] == 'failed'
                assert record['error']['code'] == 'invalid_dem_evidence'
                assert record['inputs']['source'] == 'ned1/2024'
                assert (wd / 'dem/dem.tif').is_file()
            return
        assert result['verified'] is True  # fixture verifier only; never cluster evidence
        before = records.protected_manifest(wd)
        state_before = (wd / 'provenance/build.json').read_bytes()
        assert _sample_dem(wd / 'dem/dem.tif', -116.095, 46.705) == 123.0
        assert records.protected_manifest(wd) == before
        adapter.complete(definition['submission_id'], evidence)
        assert (wd / 'provenance/build.json').read_bytes() == state_before
        assert (wd / 'manifest.db').is_file()
        assert (wd / 'READONLY').is_file()
    finally:
        if admission:
            from rq.job import Job
            for key in ('attempt_id', 'finalizer_id'):
                if Job.exists(admission[key], connection=connection):
                    Job.fetch(admission[key], connection=connection).delete()
        queue.delete(delete_jobs=True)
        connection.close()
